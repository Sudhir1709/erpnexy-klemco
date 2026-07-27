# Item Stock & Open Orders — for a specific item at a specific plant (warehouse), show the stock
# on hand alongside the open Sales Orders demanding that item there (supply vs. committed demand).

import frappe
from frappe import _
from frappe.utils import flt


def execute(filters=None):
    filters = filters or {}
    item = filters.get("item_code")
    warehouse = filters.get("warehouse")
    if not item or not warehouse:
        return [], [], None, None, None

    bin_row = frappe.db.get_value(
        "Bin", {"item_code": item, "warehouse": warehouse},
        ["actual_qty", "reserved_qty", "ordered_qty", "projected_qty"], as_dict=True,
    ) or frappe._dict()

    data = frappe.db.sql(
        """
        SELECT so.name AS sales_order,
               so.customer_name AS customer,
               soi.qty AS ordered_qty,
               soi.delivered_qty AS delivered_qty,
               (soi.qty - soi.delivered_qty) AS pending_qty,
               soi.delivery_date AS delivery_date,
               so.status AS status
        FROM `tabSales Order Item` soi
        JOIN `tabSales Order` so ON so.name = soi.parent
        WHERE soi.item_code = %(item)s
          AND soi.warehouse = %(warehouse)s
          AND so.docstatus = 1
          AND soi.qty > soi.delivered_qty
          AND so.status NOT IN ('Closed', 'Completed')
        ORDER BY soi.delivery_date
        """,
        {"item": item, "warehouse": warehouse}, as_dict=True,
    )

    columns = [
        {"label": _("Sales Order"), "fieldname": "sales_order", "fieldtype": "Link",
         "options": "Sales Order", "width": 160},
        {"label": _("Customer"), "fieldname": "customer", "fieldtype": "Data", "width": 200},
        {"label": _("Ordered"), "fieldname": "ordered_qty", "fieldtype": "Float", "width": 90},
        {"label": _("Delivered"), "fieldname": "delivered_qty", "fieldtype": "Float", "width": 90},
        {"label": _("Pending"), "fieldname": "pending_qty", "fieldtype": "Float", "width": 90},
        {"label": _("Delivery Date"), "fieldname": "delivery_date", "fieldtype": "Date", "width": 120},
        {"label": _("Status"), "fieldname": "status", "fieldtype": "Data", "width": 150},
    ]

    total_pending = sum(flt(r.pending_qty) for r in data)
    report_summary = [
        {"label": _("In Stock (On Hand)"), "value": flt(bin_row.get("actual_qty")),
         "indicator": "Green", "datatype": "Float"},
        {"label": _("Reserved for SO"), "value": flt(bin_row.get("reserved_qty")),
         "indicator": "Orange", "datatype": "Float"},
        {"label": _("Projected Qty"), "value": flt(bin_row.get("projected_qty")),
         "indicator": "Blue", "datatype": "Float"},
        {"label": _("Open Orders — Pending Qty"), "value": total_pending,
         "indicator": "Red", "datatype": "Float"},
    ]

    return columns, data, None, None, report_summary
