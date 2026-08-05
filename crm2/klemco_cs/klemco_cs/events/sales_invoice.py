# Sales Invoice server-side events — BRD v1.3
#   CR-13 / FR-DP-11  COD cheque capture (no., bank, date, amount, copy) linked to the invoice
#   BR-DP-06          For COD customers the cheque details are mandatory before submit
#                     (the dispatch-confirmation gate, enforced at the invoice that triggers COD)

import frappe
from frappe import _

COD_TYPE = "COD"

# Dispatch-documents checklist (goods invoices). (name, mandatory) — 8 mandatory + 1 optional.
DISPATCH_CHECKLIST = [
    ("Photos of boxes", 1),
    ("MTC for all parts", 1),
    ("Raw material MTC of all", 1),
    ("Traceability report", 1),
    ("E-way bill Part A", 1),
    ("Packaging List", 1),
    ("LR copy", 1),
    ("Weight Receipt", 1),
    ("Vehicle photo at dispatch", 0),
]


def validate(doc, method=None):
    doc.custom_is_cod = 1 if _is_cod(doc) else 0
    _require_so_for_stock_items(doc)
    _seed_dispatch_checklist(doc)
    _set_dispatch_status(doc)


def _require_so_for_stock_items(doc):
    """A Sales Invoice must originate from a Sales Order for STOCK items (goods) — no billing for
    un-ordered goods. Non-stock service/charge items (freight, installation, SITC, …) are added at
    billing time once goods are loaded, so they're exempt. Returns and POS invoices are exempt
    entirely. Replaces Selling Settings.so_required (native so_dn_required), which has no per-item
    exemption and can't tell goods from services."""
    if doc.get("is_return") or doc.get("is_pos"):
        return
    missing = [
        d.item_code for d in doc.get("items") or []
        if d.item_code and not d.get("sales_order")
        and frappe.get_cached_value("Item", d.item_code, "is_stock_item")
    ]
    if missing:
        frappe.throw(_(
            "Sales Order is mandatory for Item {0} — bill goods only from a Sales Order. "
            "(Freight and other services can be added without one.)"
        ).format(", ".join(dict.fromkeys(missing))))


def before_submit(doc, method=None):
    _require_dispatch_docs(doc)
    _require_cod_cheque(doc)


def _require_cod_cheque(doc):
    if not _is_cod(doc):
        return
    missing = [
        label for field, label in (
            ("custom_cheque_no", _("Cheque No.")),
            ("custom_cheque_date", _("Cheque Date")),
            ("custom_cheque_amount", _("Cheque Amount")),
        ) if not doc.get(field)
    ]
    if missing:
        frappe.throw(_(
            "COD customer: capture cheque details before submitting — missing {0} "
            "(FR-DP-11 / BR-DP-06)."
        ).format(", ".join(missing)))


# ── Dispatch-documents checklist ────────────────────────────────────────────────────────────────
def _dispatch_applicable(doc):
    """Applies only to invoices that ship goods — not returns, not POS, and only when at least one
    line is a stock item (a pure service/freight invoice has nothing to photograph/pack)."""
    if doc.get("is_return") or doc.get("is_pos"):
        return False
    return any(
        d.item_code and frappe.get_cached_value("Item", d.item_code, "is_stock_item")
        for d in doc.get("items") or []
    )


def _seed_dispatch_checklist(doc):
    """Populate the checklist rows on a fresh goods invoice (server-side safety net; the client
    seeds them too for immediate visibility). No-op if rows already exist or not applicable."""
    if not _dispatch_applicable(doc) or doc.get("cs_dispatch_documents"):
        return
    for name, mandatory in DISPATCH_CHECKLIST:
        doc.append("cs_dispatch_documents", {"document_name": name, "mandatory": mandatory})


def _missing_dispatch_docs(doc):
    return [
        r.document_name for r in doc.get("cs_dispatch_documents") or []
        if r.mandatory and not r.is_provided
    ]


def _set_dispatch_status(doc):
    if not _dispatch_applicable(doc):
        doc.cs_dispatch_docs_status = "Complete"
        return
    doc.cs_dispatch_docs_status = "Incomplete" if _missing_dispatch_docs(doc) else "Complete"


def _require_dispatch_docs(doc):
    if not _dispatch_applicable(doc):
        return
    missing = _missing_dispatch_docs(doc)
    if missing:
        frappe.throw(_(
            "Dispatch documents incomplete — provide/tick these before submitting: {0}."
        ).format(", ".join(missing)))


def _is_cod(doc):
    if not doc.get("customer"):
        return False
    return frappe.db.get_value("Customer", doc.customer, "custom_klemco_customer_type") == COD_TYPE
