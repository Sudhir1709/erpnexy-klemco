"""Klemco CRM AI Assistant — feasibility PoC.

A whitelisted chat endpoint that answers both *how-to* questions and *live data*
questions about the CRM. Live data is reached through Claude tool-use, and every
data tool runs as the logged-in user via `frappe.get_list` so the assistant can
only ever see what that user is permitted to see (role + user permissions enforced).

Configuration (site_config.json or env):
    anthropic_api_key   : the Anthropic API key (required for live answers)
    anthropic_model     : model id (default: claude-sonnet-4-6)

Without a key the endpoint runs in a clearly-labelled DEMO mode that still exercises
the data tools, so the UI + permission-safe data path can be demonstrated end-to-end.
"""

import json
import os

import frappe
import requests

ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"
DEFAULT_MODEL = "claude-sonnet-4-6"
MAX_TOOL_TURNS = 6
LIST_CAP = 50

# Doctypes the assistant is allowed to read. Scopes the surface to CRM + customer
# service + the directly-related selling/stock documents — NOT all 1029 doctypes.
ALLOWED_DOCTYPES = {
    "Customer": "customer_name",
    "Contact": "first_name",
    "CRM Lead": "lead_name",
    "CRM Deal": "organization",
    "Lead": "lead_name",
    "Opportunity": "title",
    "Prospect": "company_name",
    "Quotation": "title",
    "Sales Order": "customer",
    "Sales Invoice": "customer",
    "Delivery Note": "customer",
    "Item": "item_name",
    "CS Complaint": "subject",
    "KM Order": "customer",
}


def _api_key():
    return frappe.conf.get("anthropic_api_key") or os.environ.get("ANTHROPIC_API_KEY")


def _model():
    return frappe.conf.get("anthropic_model") or DEFAULT_MODEL


# ───────────────────────── data tools (permission-safe) ─────────────────────────
def _guard(doctype):
    if doctype not in ALLOWED_DOCTYPES:
        frappe.throw(f"Doctype '{doctype}' is not available to the assistant.")


def tool_count_records(doctype, filters=None):
    """Count records the current user can see, optionally filtered."""
    _guard(doctype)
    rows = frappe.get_list(doctype, filters=filters or {}, fields=["name"],
                           limit_page_length=0, ignore_permissions=False)
    return {"doctype": doctype, "filters": filters or {}, "count": len(rows)}


def tool_list_records(doctype, filters=None, fields=None, limit=10):
    """List records (perm-safe) with a few fields."""
    _guard(doctype)
    title = ALLOWED_DOCTYPES[doctype]
    fields = fields or ["name", title]
    fields = [f for f in dict.fromkeys(["name"] + fields)]  # ensure name, dedupe
    limit = min(int(limit or 10), LIST_CAP)
    rows = frappe.get_list(doctype, filters=filters or {}, fields=fields,
                           limit_page_length=limit, ignore_permissions=False,
                           order_by="modified desc")
    return {"doctype": doctype, "filters": filters or {}, "rows": rows, "returned": len(rows)}


TOOLS_IMPL = {"count_records": tool_count_records, "list_records": tool_list_records}

TOOLS_SPEC = [
    {
        "name": "count_records",
        "description": "Count how many records of a CRM doctype the user can see, optionally filtered. Use for 'how many ...' questions.",
        "input_schema": {
            "type": "object",
            "properties": {
                "doctype": {"type": "string", "enum": sorted(ALLOWED_DOCTYPES)},
                "filters": {"type": "object", "description": "Frappe filter dict, e.g. {\"status\": \"Open\"}"},
            },
            "required": ["doctype"],
        },
    },
    {
        "name": "list_records",
        "description": "List records of a CRM doctype the user can see (most recent first). Use for 'show me ...' / 'list ...' questions.",
        "input_schema": {
            "type": "object",
            "properties": {
                "doctype": {"type": "string", "enum": sorted(ALLOWED_DOCTYPES)},
                "filters": {"type": "object", "description": "Frappe filter dict"},
                "fields": {"type": "array", "items": {"type": "string"}, "description": "Fieldnames to return"},
                "limit": {"type": "integer", "description": "Max rows (<=50)"},
            },
            "required": ["doctype"],
        },
    },
]


def _system_prompt():
    return (
        "You are the Klemco CRM Assistant, embedded in an ERPNext/Frappe CRM. "
        "Help users two ways: (1) answer how-to and process questions about using the CRM "
        "(leads, deals, customers, quotations, sales orders, invoices, deliveries, customer-service "
        "complaints, KM orders); (2) answer questions about their live data by calling the provided tools. "
        "Always use a tool for data questions (counts, lists, status) rather than guessing. "
        "The tools already enforce the user's permissions, so only report what they return. "
        f"Available data doctypes: {', '.join(sorted(ALLOWED_DOCTYPES))}. "
        "Be concise. If a request is outside the CRM, say so politely."
    )


# ───────────────────────── Claude agent loop ─────────────────────────
def _anthropic(messages):
    headers = {
        "x-api-key": _api_key(),
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    payload = {
        "model": _model(),
        "max_tokens": 1024,
        "system": _system_prompt(),
        "tools": TOOLS_SPEC,
        "messages": messages,
    }
    r = requests.post(ANTHROPIC_URL, headers=headers, json=payload, timeout=60)
    if r.status_code != 200:
        frappe.log_error(f"{r.status_code}: {r.text[:500]}", "Klemco AI Assistant")
        frappe.throw(f"Assistant error ({r.status_code}). Check the Anthropic API key / quota.")
    return r.json()


def _run_agent(history, message):
    messages = list(history or [])
    messages.append({"role": "user", "content": message})
    for _ in range(MAX_TOOL_TURNS):
        resp = _anthropic(messages)
        blocks = resp.get("content", [])
        messages.append({"role": "assistant", "content": blocks})
        if resp.get("stop_reason") == "tool_use":
            tool_results = []
            for b in blocks:
                if b.get("type") == "tool_use":
                    try:
                        out = TOOLS_IMPL[b["name"]](**(b.get("input") or {}))
                    except Exception as e:
                        out = {"error": str(e)}
                    tool_results.append({
                        "type": "tool_result", "tool_use_id": b["id"],
                        "content": json.dumps(out, default=str),
                    })
            messages.append({"role": "user", "content": tool_results})
            continue
        return "".join(b.get("text", "") for b in blocks if b.get("type") == "text")
    return "I wasn't able to complete that — too many steps. Please rephrase."


# ───────────────────────── demo mode (no API key) ─────────────────────────
def _demo(message):
    m = (message or "").lower()
    prefix = "🟡 *Demo mode — no Anthropic API key configured. This proves the data pipeline; add a key for full natural-language answers.*\n\n"
    try:
        if "complaint" in m:
            filt = {"status": "Open"} if "open" in m else {}
            if any(w in m for w in ("how many", "count", "number")):
                c = tool_count_records("CS Complaint", filt)["count"]
                return prefix + f"You have **{c}** CS Complaint(s){' with status Open' if filt else ''}."
            rows = tool_list_records("CS Complaint", filt, ["name", "subject", "status"], 10)["rows"]
            return prefix + _fmt("CS Complaints", rows)
        if "customer" in m:
            if any(w in m for w in ("how many", "count", "number")):
                c = tool_count_records("Customer")["count"]
                return prefix + f"There are **{c}** customers you can access."
            rows = tool_list_records("Customer", {}, ["name", "customer_name", "customer_group"], 10)["rows"]
            return prefix + _fmt("Customers", rows)
        if "sales order" in m or "order" in m:
            c = tool_count_records("Sales Order")["count"]
            return prefix + f"There are **{c}** Sales Orders you can access. Ask 'list sales orders' for details."
    except Exception as e:
        return prefix + f"(tool error: {e})"
    return (prefix + "I can answer questions like: *how many open complaints?*, *list customers*, "
            "*how many sales orders?*. With an API key I also handle free-form how-to and data questions.")


def _fmt(title, rows):
    if not rows:
        return f"No {title.lower()} found."
    lines = [f"**{title}** ({len(rows)}):"]
    for r in rows:
        vals = " · ".join(str(v) for k, v in r.items() if v is not None)
        lines.append(f"- {vals}")
    return "\n".join(lines)


# ───────────────────────── public endpoint ─────────────────────────
@frappe.whitelist()
def chat(message, history=None):
    """Answer a CRM question. `history` = JSON list of prior {role, content} turns."""
    if frappe.session.user == "Guest":
        frappe.throw("Please log in to use the assistant.")
    message = (message or "").strip()
    if not message:
        return {"reply": "Ask me anything about your CRM.", "mode": "idle"}
    if isinstance(history, str):
        try:
            history = json.loads(history)
        except Exception:
            history = []
    # keep only clean text turns for the model
    clean = [{"role": h["role"], "content": h["content"]} for h in (history or [])
             if h.get("role") in ("user", "assistant") and isinstance(h.get("content"), str)][-10:]

    if not _api_key():
        return {"reply": _demo(message), "mode": "demo"}
    reply = _run_agent(clean, message)
    return {"reply": reply, "mode": "live", "model": _model()}


def install_menu():
    """Idempotently add an 'AI Help' entry to the desk navbar Help dropdown (-> /ai-help).
    Runs on every migrate; safe to call repeatedly."""
    try:
        nav = frappe.get_single("Navbar Settings")
        if any((row.get("route") == "/ai-help") for row in nav.help_dropdown):
            return
        nav.append("help_dropdown", {"item_label": "AI Help", "item_type": "Route",
                                     "route": "/ai-help", "is_standard": 1})
        nav.save(ignore_permissions=True)
    except Exception:
        frappe.log_error(frappe.get_traceback(), "Klemco AI: install_menu")


@frappe.whitelist()
def status():
    """Quick health/config check for the assistant."""
    return {
        "configured": bool(_api_key()),
        "model": _model(),
        "doctypes": sorted(ALLOWED_DOCTYPES),
        "user": frappe.session.user,
    }
