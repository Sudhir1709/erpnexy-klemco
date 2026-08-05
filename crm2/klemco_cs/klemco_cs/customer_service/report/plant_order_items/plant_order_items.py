# Plant Order Items — every Plant Order (KM Order) with its item lines (one row per item), so the
# list can be grouped by Plant Order (a collapsible dropdown of items under each order number),
# shows Created By, and exports order+item detail to Excel.

import frappe
from frappe import _


def execute(filters=None):
    filters = filters or {}
    conds = ["ko.docstatus < 2"]
    vals = {}
    if filters.get("status"):
        conds.append("ko.status = %(status)s")
        vals["status"] = filters["status"]
    if filters.get("customer"):
        conds.append("ko.customer = %(customer)s")
        vals["customer"] = filters["customer"]
    where = " AND ".join(conds)

    data = frappe.db.sql(
        """
        SELECT ko.name AS plant_order, ko.owner AS created_by, ko.customer AS customer,
               ko.status AS status, ko.linked_sales_order AS sales_order,
               koi.item_code AS item_code, koi.item_name AS item_name, koi.km_qty AS qty,
               koi.uom AS uom, koi.delivery_date AS delivery_date,
               koi.cs_available_date AS available_date, koi.cs_plant_date_status AS plant_response
        FROM `tabKM Order` ko
        JOIN `tabKM Order Item` koi ON koi.parent = ko.name
        WHERE {where}
        ORDER BY ko.creation DESC, koi.idx
        """.format(where=where),
        vals, as_dict=True,
    )

    columns = [
        {"label": _("Plant Order"), "fieldname": "plant_order", "fieldtype": "Link", "options": "KM Order", "width": 150},
        {"label": _("Created By"), "fieldname": "created_by", "fieldtype": "Data", "width": 160},
        {"label": _("Customer"), "fieldname": "customer", "fieldtype": "Link", "options": "Customer", "width": 160},
        {"label": _("Status"), "fieldname": "status", "fieldtype": "Data", "width": 120},
        {"label": _("Sales Order"), "fieldname": "sales_order", "fieldtype": "Link", "options": "Sales Order", "width": 150},
        {"label": _("Item Code"), "fieldname": "item_code", "fieldtype": "Link", "options": "Item", "width": 140},
        {"label": _("Item Name"), "fieldname": "item_name", "fieldtype": "Data", "width": 180},
        {"label": _("Qty"), "fieldname": "qty", "fieldtype": "Float", "width": 80},
        {"label": _("UOM"), "fieldname": "uom", "fieldtype": "Data", "width": 70},
        {"label": _("Delivery Date"), "fieldname": "delivery_date", "fieldtype": "Date", "width": 110},
        {"label": _("Available Date"), "fieldname": "available_date", "fieldtype": "Date", "width": 110},
        {"label": _("Plant Response"), "fieldname": "plant_response", "fieldtype": "Data", "width": 130},
    ]
    return columns, data
