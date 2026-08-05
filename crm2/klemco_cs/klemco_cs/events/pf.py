# Optional "Packaging & Forwarding (P&F)" charge — a % of Net Total added BEFORE tax, so GST is
# computed on (items + P&F). Klemco's GST rows are "On Net Total", which ignore every other charge,
# so the only way to tax P&F is to switch the GST rows to "On Previous Row Total" referencing the
# P&F row (India Compliance then apportions P&F into each item's taxable_value). P&F is optional, so
# this structure is applied only when cs_add_pf is on and reverted when off. Shared by Quotation,
# Sales Order and Sales Invoice via each doctype's before_validate.

import frappe
from frappe import _
from frappe.utils import flt

PF_DESC = "Packaging & Forwarding (P&F)"
DEFAULT_PF_RATE = 1.5
_PF_DOCTYPES = ("Quotation", "Sales Order", "Sales Invoice")


def _gst_accounts(company):
    if not company:
        return set()
    try:
        from india_compliance.gst_india.utils import get_all_gst_accounts
        return set(get_all_gst_accounts(company) or [])
    except Exception:
        return set()


def _pf_account(company):
    """The Packaging & Forwarding charge ledger for the company (created by
    customizations._ensure_pf_accounts); falls back to the Freight ledger."""
    if not company:
        return None
    abbr = frappe.get_cached_value("Company", company, "abbr")
    for name in ("Packaging and Forwarding Charges - %s" % abbr,
                 "Freight and Forwarding Charges - %s" % abbr):
        if frappe.db.exists("Account", name):
            return name
    return None


def _row_input(t):
    """Copy just the input fields of a Sales Taxes and Charges row (amounts recompute on validate)."""
    return {
        "charge_type": t.get("charge_type"),
        "account_head": t.get("account_head"),
        "description": t.get("description"),
        "rate": t.get("rate"),
        "row_id": t.get("row_id"),
        "cost_center": t.get("cost_center"),
        "included_in_print_rate": t.get("included_in_print_rate"),
    }


def _rewrite(doc, row_dicts):
    doc.set("taxes", [])
    for i, d in enumerate(row_dicts):
        row = doc.append("taxes", d)
        row.idx = i + 1


def reconcile_pf(doc):
    """Add/refresh (or remove) the P&F charge row and restructure GST so it's charged on (net + P&F).
    Idempotent; a no-op for orders without P&F, and safe when the row/flag carry through the mappers."""
    if doc.doctype not in _PF_DOCTYPES:
        return

    gst_accts = _gst_accounts(doc.get("company"))
    existing = doc.get("taxes") or []
    rows = [t for t in existing if (t.get("description") or "").strip() != PF_DESC]

    if not doc.get("cs_add_pf"):
        # Revert any GST rows we previously switched back to the standard "On Net Total".
        reverted = False
        for t in rows:
            if t.account_head in gst_accts and t.charge_type == "On Previous Row Total":
                t.charge_type = "On Net Total"
                t.row_id = 0
                reverted = True
        if reverted or len(rows) != len(existing):
            _rewrite(doc, [_row_input(t) for t in rows])
        return

    account = _pf_account(doc.get("company"))
    if not account:
        frappe.msgprint(_("No Packaging & Forwarding charge account found — P&F not applied."), alert=True)
        return

    rate = flt(doc.get("cs_pf_rate")) or DEFAULT_PF_RATE
    pf = {"charge_type": "On Net Total", "account_head": account,
          "description": PF_DESC, "rate": rate, "included_in_print_rate": 0}

    ordered = [pf]
    for t in rows:
        d = _row_input(t)
        if t.account_head in gst_accts:
            # tax the P&F: compute GST on (net + P&F), i.e. the running total up to the P&F row (idx 1)
            d["charge_type"] = "On Previous Row Total"
            d["row_id"] = 1
        ordered.append(d)
    _rewrite(doc, ordered)
