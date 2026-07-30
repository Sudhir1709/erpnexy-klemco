# Sales Invoice server-side events — BRD v1.3
#   CR-13 / FR-DP-11  COD cheque capture (no., bank, date, amount, copy) linked to the invoice
#   BR-DP-06          For COD customers the cheque details are mandatory before submit
#                     (the dispatch-confirmation gate, enforced at the invoice that triggers COD)

import frappe
from frappe import _

COD_TYPE = "COD"


def validate(doc, method=None):
    doc.custom_is_cod = 1 if _is_cod(doc) else 0
    _require_so_for_stock_items(doc)


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


def _is_cod(doc):
    if not doc.get("customer"):
        return False
    return frappe.db.get_value("Customer", doc.customer, "custom_klemco_customer_type") == COD_TYPE
