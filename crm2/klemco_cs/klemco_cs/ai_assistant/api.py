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


# Doctypes the assistant may PROPOSE creating. The actual write never happens inside
# the model loop — only via confirm_create() after an explicit human click.
ALLOWED_CREATE = {"CS Complaint", "CRM Lead", "Lead"}


def tool_propose_create(doctype, values=None):
    """Propose creating a record. Does NOT write — returns a proposal for the user to confirm."""
    if doctype not in ALLOWED_CREATE:
        frappe.throw(f"The assistant cannot create '{doctype}'.")
    return {"proposed": True, "doctype": doctype, "values": values or {},
            "note": "Not created yet — awaiting explicit user confirmation in the UI."}


TOOLS_IMPL = {
    "count_records": tool_count_records,
    "list_records": tool_list_records,
    "propose_create": tool_propose_create,
}

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
    {
        "name": "propose_create",
        "description": ("Propose creating a new record (e.g. log a complaint, capture a lead). "
                        "This does NOT create anything — it drafts the record and the user must confirm. "
                        "Use when the user asks to create/log/add something. After calling, tell the user "
                        "to review and confirm; never say it has been created."),
        "input_schema": {
            "type": "object",
            "properties": {
                "doctype": {"type": "string", "enum": sorted(ALLOWED_CREATE)},
                "values": {"type": "object", "description": "Field values for the new record"},
            },
            "required": ["doctype", "values"],
        },
    },
]


def _system_prompt():
    return (
        "You are the Klemco CRM Assistant, embedded in an ERPNext/Frappe CRM. "
        "Help users two ways: (1) answer how-to and process questions about using the CRM "
        "(leads, deals, customers, quotations, sales orders, invoices, deliveries, customer-service "
        "complaints, plant orders); (2) answer questions about their live data by calling the provided tools. "
        "Always use a tool for data questions (counts, lists, status) rather than guessing. "
        "The tools already enforce the user's permissions, so only report what they return. "
        f"Available data doctypes: {', '.join(sorted(ALLOWED_DOCTYPES))}. "
        "To create/log a record (complaint, lead), call propose_create — this only DRAFTS it; "
        "the user must confirm in the UI before anything is saved, so never claim it was created. "
        f"You may propose creating: {', '.join(sorted(ALLOWED_CREATE))}. "
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
    pending = None  # a drafted create awaiting user confirmation
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
                        if b["name"] == "propose_create" and out.get("proposed"):
                            pending = {"doctype": out["doctype"], "values": out["values"]}
                    except Exception as e:
                        out = {"error": str(e)}
                    tool_results.append({
                        "type": "tool_result", "tool_use_id": b["id"],
                        "content": json.dumps(out, default=str),
                    })
            messages.append({"role": "user", "content": tool_results})
            continue
        text = "".join(b.get("text", "") for b in blocks if b.get("type") == "text")
        return text, pending
    return "I wasn't able to complete that — too many steps. Please rephrase.", pending


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
    reply, pending = _run_agent(clean, message)
    out = {"reply": reply, "mode": "live", "model": _model()}
    if pending:
        out["pending_action"] = pending
    return out


@frappe.whitelist(methods=["POST"])
def confirm_create(doctype, values):
    """Actually create a record the assistant proposed. This is the ONLY write path and it
    runs only on an explicit user click — never from inside the model loop."""
    if frappe.session.user == "Guest":
        frappe.throw("Please log in.")
    if doctype not in ALLOWED_CREATE:
        frappe.throw(f"The assistant cannot create '{doctype}'.")
    if not frappe.has_permission(doctype, "create"):
        frappe.throw(f"You don't have permission to create {doctype}.")
    if isinstance(values, str):
        values = json.loads(values or "{}")
    doc = frappe.get_doc({"doctype": doctype, **(values or {})})
    # auto-fill naming_series if the doctype names by series and the model didn't supply one
    ns = frappe.get_meta(doctype).get_field("naming_series")
    if ns and not doc.get("naming_series"):
        doc.naming_series = ns.default or (ns.options or "").split("\n")[0] or None
    doc.insert()  # runs as the logged-in user → field-level & mandatory checks apply
    # audit trail
    try:
        frappe.get_doc({"doctype": "Comment", "comment_type": "Info",
                        "reference_doctype": doctype, "reference_name": doc.name,
                        "content": f"Created via Klemco AI Assistant by {frappe.session.user}."}).insert(ignore_permissions=True)
    except Exception:
        pass
    frappe.db.commit()
    return {"created": True, "doctype": doctype, "name": doc.name}


def install_widget_bundle():
    """Publish the floating-bubble JS as a desk bundle WITHOUT a Node build. The script is
    plain browser-ready JS (no transpile), so we copy it into the assets dist folder and
    register it in assets.json under 'klemco_cs.bundle.js' (the name used in app_include_js).
    Idempotent; runs on every migrate so it survives asset refreshes."""
    import os
    import shutil
    try:
        src = frappe.get_app_path("klemco_cs", "public", "js", "ai_widget.js")
        assets = os.path.join(frappe.utils.get_bench_path(), "sites", "assets")
        dist = os.path.join(assets, "klemco_cs", "dist", "js")
        os.makedirs(dist, exist_ok=True)
        shutil.copyfile(src, os.path.join(dist, "klemco_cs.bundle.js"))
        manifest = os.path.join(assets, "assets.json")
        try:
            with open(manifest) as f:
                data = json.load(f)
        except Exception:
            data = {}
        data["klemco_cs.bundle.js"] = "/assets/klemco_cs/dist/js/klemco_cs.bundle.js"
        with open(manifest, "w") as f:
            json.dump(data, f, indent=4)
    except Exception:
        frappe.log_error(frappe.get_traceback(), "Klemco AI: install_widget_bundle")


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


def install_crm_spa_widget():
    """Inject the floating widget into the Frappe CRM SPA (/crm) by adding a <script> tag to
    the crm app's www/crm.html. This edits a third-party app file, so it is re-applied on every
    migrate (idempotent) and should be re-run after any crm app upgrade. The desk bubble
    (app_include_js) needs no such patch."""
    import os
    try:
        from crm import __file__ as crm_init
    except Exception:
        return  # crm app not installed
    path = os.path.join(os.path.dirname(crm_init), "www", "crm.html")
    if not os.path.exists(path):
        return
    try:
        with open(path) as f:
            html = f.read()
        if "ai_widget.js" in html or "</body>" not in html:
            return
        tag = '    <script src="/assets/klemco_cs/js/ai_widget.js"></script>\n  </body>'
        with open(path, "w") as f:
            f.write(html.replace("</body>", tag, 1))
    except Exception:
        frappe.log_error(frappe.get_traceback(), "Klemco AI: install_crm_spa_widget")


@frappe.whitelist()
def status():
    """Quick health/config check for the assistant."""
    return {
        "configured": bool(_api_key()),
        "model": _model(),
        "doctypes": sorted(ALLOWED_DOCTYPES),
        "user": frappe.session.user,
    }
