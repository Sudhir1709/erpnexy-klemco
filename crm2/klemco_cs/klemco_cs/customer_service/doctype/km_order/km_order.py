# KM (Klemco Manufacturing) Order — BRD v1.3 §6
#   CR-11 / FR-KM-08  Guided "Create KM Order from SO": CS reviews the linked SO's items/qty
#                     before the KM PO is raised (mirrors the Save & Create Delivery Challan flow).
#   BR-KM-01          Standalone KM orders are not permitted — must link a parent SO.
#   BR-KM-02 / CR-18  A KM-managed Item must be triple-approved before it can be ordered.

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.model.mapper import get_mapped_doc


class KMOrder(Document):
    def validate(self):
        if not self.linked_sales_order:
            frappe.throw(_("KM Order must be linked to a parent Sales Order (BR-KM-01)."))

        if not self.customer:
            self.customer = frappe.db.get_value("Sales Order", self.linked_sales_order, "customer")

        if not self.items:
            frappe.throw(_("Add at least one item to the KM Order."))

        for row in self.items:
            row.matches_so = 1 if (row.km_qty or 0) == (row.so_qty or 0) else 0

    def before_submit(self):
        # The submit action is the explicit "Confirm & Create KM Order" step (FR-KM-08).
        for row in self.items:
            if not frappe.db.exists("Item", row.item_code):
                frappe.throw(_(
                    "Row #{0}: Item {1} is not in the KM master. Create it via the New Item "
                    "workflow (triple approval, BR-KM-02) before raising the KM order."
                ).format(row.idx, row.item_code))

            km_managed, status = frappe.db.get_value(
                "Item", row.item_code, ["custom_km_managed", "custom_km_approval_status"]
            ) or (0, None)
            if km_managed and status != "Approved":
                frappe.throw(_(
                    "Row #{0}: Item {1} is a KM-managed item still pending triple approval "
                    "(CS Supervisor + KM Plant Head + Supply Chain Lead) — BR-KM-02."
                ).format(row.idx, row.item_code))

        self.status = "KM Confirmed"

    def on_cancel(self):
        self.status = "Cancelled"


@frappe.whitelist()
def make_km_order(source_name, target_doc=None):
    """Build a draft KM Order from a Sales Order for CS review (FR-KM-08)."""

    def set_missing(source, target):
        target.linked_sales_order = source.name
        target.customer = source.customer

    def update_item(source_row, target_row, source_parent):
        # KM qty defaults to the SO qty; CS reviews/edits before confirming.
        target_row.so_qty = source_row.qty
        target_row.km_qty = source_row.qty
        target_row.uom = source_row.uom
        target_row.matches_so = 1

    doc = get_mapped_doc(
        "Sales Order",
        source_name,
        {
            "Sales Order": {
                "doctype": "KM Order",
            },
            "Sales Order Item": {
                "doctype": "KM Order Item",
                "field_map": {"item_code": "item_code", "item_name": "item_name"},
                "postprocess": update_item,
            },
        },
        target_doc,
        set_missing,
    )
    return doc
