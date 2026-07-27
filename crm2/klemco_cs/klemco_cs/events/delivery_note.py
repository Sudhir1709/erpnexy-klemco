# Delivery Note server-side events — BRD v1.3
#   CR-16          Delivery Instructions carried from the Sales Order onto the Challan
#   CR-15 FR-DP-12 Warehouse can download test certificates attached to the linked SO

import frappe
from frappe import _
from frappe.utils import flt


def validate(doc, method=None):
    _carry_delivery_instructions(doc)
    _check_stock_availability(doc)


def _check_stock_availability(doc):
    """Block creating (saving) a delivery challan when the source warehouse doesn't have the stock.
    ERPNext already blocks this on SUBMIT when negative stock is off; this brings the guard forward to
    save time so an un-deliverable draft can't even be created. Returns and non-stock items are exempt,
    and it respects Stock Settings.allow_negative_stock (negatives-off ⇒ enforced at save + submit)."""
    if doc.get("is_return"):
        return
    if frappe.db.get_single_value("Stock Settings", "allow_negative_stock"):
        return  # negatives explicitly allowed — don't block

    required = {}   # (item_code, warehouse) -> qty needed in stock UOM
    for row in doc.get("items", []):
        wh = row.get("warehouse")
        if not wh or not row.get("item_code"):
            continue
        if not frappe.get_cached_value("Item", row.item_code, "is_stock_item"):
            continue
        qty = flt(row.get("stock_qty")) or flt(row.get("qty")) * (flt(row.get("conversion_factor")) or 1)
        if qty <= 0:
            continue
        required[(row.item_code, wh)] = required.get((row.item_code, wh), 0) + qty

    shortages = []
    for (item_code, wh), need in required.items():
        available = flt(frappe.db.get_value("Bin", {"item_code": item_code, "warehouse": wh}, "actual_qty"))
        if need > available:
            item_name = frappe.get_cached_value("Item", item_code, "item_name") or item_code
            # Where IS this item in stock? Naming the other warehouses makes the block actionable
            # ("in stock, just not in the dispatch warehouse").
            elsewhere = frappe.db.sql(
                """SELECT warehouse, actual_qty FROM `tabBin`
                   WHERE item_code=%s AND actual_qty > 0 AND warehouse != %s
                   ORDER BY actual_qty DESC""",
                (item_code, wh), as_dict=True,
            )
            if elsewhere:
                where = _("In stock elsewhere: {0}.").format(
                    ", ".join("{0} ({1})".format(e.warehouse, flt(e.actual_qty)) for e in elsewhere))
            else:
                where = _("No stock in any warehouse.")
            shortages.append(
                _("&bull; {0} ({1}): need {2} in {3} ({4} available). {5}").format(
                    item_code, item_name, need, wh, available, where)
            )

    if shortages:
        frappe.throw(
            _("Cannot create this delivery challan — insufficient stock:<br>{0}<br><br>"
              "Receive or transfer that stock into the dispatch warehouse, or ship from the warehouse "
              "that has it.").format("<br>".join(shortages)),
            title=_("Insufficient Stock"),
        )


def _carry_delivery_instructions(doc):
    if doc.get("custom_delivery_instructions"):
        return
    so = _linked_sales_order(doc)
    if not so:
        return
    instructions = frappe.db.get_value("Sales Order", so, "custom_delivery_instructions")
    if instructions:
        doc.custom_delivery_instructions = instructions


def _linked_sales_order(doc):
    for row in doc.get("items", []):
        if row.get("against_sales_order"):
            return row.against_sales_order
    return None


@frappe.whitelist()
def get_so_test_certificates(delivery_note):
    """Return test-certificate files attached to the SO linked to this Delivery Note so the
    warehouse role can download them from the dispatch panel (FR-DP-12)."""
    doc = frappe.get_doc("Delivery Note", delivery_note)
    so = _linked_sales_order(doc)
    if not so:
        return []
    return frappe.get_all(
        "File",
        filters={"attached_to_doctype": "Sales Order", "attached_to_name": so},
        fields=["file_name", "file_url", "file_size"],
        order_by="file_name asc",
    )
