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
    def before_insert(self):
        # Frappe's new_doc/server-side inserts don't default a Series field, so a programmatic
        # insert can miss naming_series (the UI form sets it). Default it so autoname never fails.
        if not self.get("naming_series"):
            self.naming_series = "PLO-.YYYY.-"

    def validate(self):
        # A KM (Klemco) Order may be raised standalone or from a parent Sales Order.
        # When linked to an SO, the customer is derived from it; otherwise it must be
        # entered directly (UAT 01-Jul — restores the standalone "Klemco Order" flow).
        if self.linked_sales_order:
            self.customer = frappe.db.get_value("Sales Order", self.linked_sales_order, "customer")
        elif not self.customer:
            frappe.throw(_("Select a Customer, or link a parent Sales Order to derive it."))

        if not self.items:
            frappe.throw(_("Add at least one item to the Plant Order."))

        for row in self.items:
            # so_qty is only meaningful when the KM order was mapped from an SO.
            row.matches_so = 1 if self.linked_sales_order and (row.km_qty or 0) == (row.so_qty or 0) else 0

    def before_submit(self):
        # The submit action is the explicit "Confirm & Create KM Order" step (FR-KM-08).
        for row in self.items:
            if not frappe.db.exists("Item", row.item_code):
                frappe.throw(_(
                    "Row #{0}: Item {1} is not in the KM master. Create it via the New Item "
                    "workflow (triple approval, BR-KM-02) before raising the Plant Order."
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
        # on_cancel runs AFTER the save, so a plain `self.status = ...` never persists — write it
        # directly so the list/report shows "Cancelled" instead of the stale "KM Confirmed".
        self.db_set("status", "Cancelled")


# Production lifecycle after the order is confirmed (submitted). The plant advances the status
# one forward stage at a time via the guided buttons on the form (km_order.js) — the Status field
# itself is read-only, so there's no way to skip stages or move it backwards.
KM_STATUS_FLOW = ["KM Confirmed", "In Production", "Inward Complete", "Transfer Billing Done"]
KM_STATUS_ROLES = {"KM Plant Head", "CS Manager", "CS Supervisor", "System Manager"}

# Stock model: the goods enter Klemco stock when the PURCHASE BILL is done (bill = receipt) — the
# Generate Purchase Bill posts a Purchase Invoice that receives the produced qty into Finished Goods
# at the purchase rate. The production stages below only track status (they move no stock).
KM_COMPANY = "Klemco India"
KM_RECEIVE_WAREHOUSE = "Finished Goods - KI"

# transfer_billing_status reflects where the order is in the inward/transfer sub-flow.
KM_TB_STATUS = {
    "In Production": "Pending Inward",
    "Inward Complete": "Not Yet",       # inward done, plant→store transfer not yet
    "Transfer Billing Done": "TB Done",
}


@frappe.whitelist()
def advance_status(km_order, to_status):
    """Move a submitted KM Order to the NEXT production stage (forward-only, role-gated).

    Status-only: the stages move no stock — the goods enter Finished Goods when the purchase bill
    is submitted (see make_purchase_bill)."""
    doc = frappe.get_doc("KM Order", km_order)
    if doc.docstatus != 1:
        frappe.throw(_("Only a submitted Plant Order can be advanced."))
    if not (KM_STATUS_ROLES & set(frappe.get_roles())):
        frappe.throw(_("You are not permitted to advance the Plant production status."))
    if doc.status not in KM_STATUS_FLOW:
        frappe.throw(_("Cannot advance from status {0}.").format(doc.status))
    i = KM_STATUS_FLOW.index(doc.status)
    nxt = KM_STATUS_FLOW[i + 1] if i + 1 < len(KM_STATUS_FLOW) else None
    if to_status != nxt:
        frappe.throw(_("The next step after {0} is {1}.").format(doc.status, nxt or _("(final)")))

    doc.db_set("status", to_status)  # db_set persists on a submitted doc
    if to_status in KM_TB_STATUS:
        doc.db_set("transfer_billing_status", KM_TB_STATUS[to_status])
    doc.add_comment("Info", _("Production status: {0} → {1}").format(KM_STATUS_FLOW[i], to_status))
    return to_status


KM_PURCHASE_PRICE_LIST = "Standard Buying"
KM_DEFAULT_SUPPLIER = "Klemco Manufacturing"


def _km_purchase_rate(item_code):
    """The item's purchase rate = its most recent Standard Buying price. None if not defined."""
    rows = frappe.get_all(
        "Item Price",
        filters={"item_code": item_code, "price_list": KM_PURCHASE_PRICE_LIST},
        fields=["price_list_rate"],
        order_by="valid_from desc, modified desc",
        limit=1,
    )
    return rows[0].price_list_rate if rows else None


@frappe.whitelist()
def make_purchase_bill(source_name, target_doc=None):
    """Build a draft Purchase Invoice for a KM Order that RECEIVES the goods into Finished Goods at
    the PURCHASE rate (Standard Buying) — the bill IS the receipt: submitting it adds the produced
    qty to Finished Goods stock at cost AND records the payable to the plant supplier, in one linked
    document. Distinct from the customer's Sales Invoice at the sales rate. Opened via open_mapped_doc."""
    doc = frappe.get_doc("KM Order", source_name)
    if doc.docstatus != 1:
        frappe.throw(_("Submit the Plant Order before generating its purchase bill."))

    supplier = doc.get("supplier") or KM_DEFAULT_SUPPLIER
    if not frappe.db.exists("Supplier", supplier):
        frappe.throw(_("Supplier {0} not found — set a Manufacturing Supplier on the Plant Order.").format(supplier))

    pi = frappe.new_doc("Purchase Invoice")
    pi.supplier = supplier
    pi.company = KM_COMPANY
    pi.update_stock = 1  # bill = receipt: goods enter Finished Goods on submit
    pi.set_warehouse = KM_RECEIVE_WAREHOUSE
    pi.remarks = _("Auto-generated from Plant Order {0} — receives goods into {1} at purchase rate.").format(
        doc.name, KM_RECEIVE_WAREHOUSE)

    missing = []
    for it in doc.items:
        if not it.item_code or (it.km_qty or 0) <= 0:
            continue
        rate = _km_purchase_rate(it.item_code)
        if rate is None:
            missing.append(it.item_code)
            continue
        row = pi.append("items", {})
        row.item_code = it.item_code
        row.qty = it.km_qty
        row.uom = it.uom
        row.rate = rate
        row.price_list_rate = rate
        if frappe.get_cached_value("Item", it.item_code, "is_stock_item"):
            row.warehouse = KM_RECEIVE_WAREHOUSE

    if missing:
        frappe.throw(_(
            "Set a Purchase rate ({0} price) for: {1} — then generate the bill."
        ).format(KM_PURCHASE_PRICE_LIST, ", ".join(dict.fromkeys(missing))))

    return pi


@frappe.whitelist()
def make_km_order(source_name, target_doc=None):
    """Build a draft KM Order from a Sales Order for CS review (FR-KM-08)."""

    def set_missing(source, target):
        target.linked_sales_order = source.name
        target.customer = source.customer
        # Carry the customer's required delivery date so the plant can plan production against it.
        target.km_delivery_date = source.delivery_date

    def update_item(source_row, target_row, source_parent):
        # KM qty defaults to the SO qty; CS reviews/edits before confirming.
        target_row.so_qty = source_row.qty
        target_row.km_qty = source_row.qty
        target_row.uom = source_row.uom
        target_row.delivery_date = source_row.delivery_date  # per-line required date for planning
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
