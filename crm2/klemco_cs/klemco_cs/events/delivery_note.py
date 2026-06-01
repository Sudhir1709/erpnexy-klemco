# Delivery Note server-side events — BRD v1.3
#   CR-16          Delivery Instructions carried from the Sales Order onto the Challan
#   CR-15 FR-DP-12 Warehouse can download test certificates attached to the linked SO

import frappe


def validate(doc, method=None):
    _carry_delivery_instructions(doc)


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
