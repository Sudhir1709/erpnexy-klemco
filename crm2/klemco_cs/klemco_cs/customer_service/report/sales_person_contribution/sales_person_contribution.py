# Sales Person Contribution — each Sales-Team member's share of Quotations / Sales Orders / Sales
# Invoices, with the document value split by their Contribution % (allocated_percentage). One row per
# (document, sales person). Value split is computed directly (grand_total * pct/100) so it's correct
# even before the stored allocated_amount is recalculated.

import frappe
from frappe import _

# doctype -> (date field). All three carry the standard `sales_team` (Sales Team) child.
_SOURCES = {
    "Quotation": "transaction_date",
    "Sales Order": "transaction_date",
    "Sales Invoice": "posting_date",
}


def execute(filters=None):
    filters = filters or {}
    want = filters.get("document_type")
    parts, vals = [], {}

    for dt, datefield in _SOURCES.items():
        if want and want != dt:
            continue
        conds = ["d.docstatus < 2"]
        if filters.get("sales_person"):
            conds.append("st.sales_person = %(sales_person)s")
            vals["sales_person"] = filters["sales_person"]
        if filters.get("from_date"):
            conds.append("d.`{0}` >= %(from_date)s".format(datefield))
            vals["from_date"] = filters["from_date"]
        if filters.get("to_date"):
            conds.append("d.`{0}` <= %(to_date)s".format(datefield))
            vals["to_date"] = filters["to_date"]
        where = " AND ".join(conds)
        parts.append(
            """
            SELECT st.sales_person AS sales_person, '{dt}' AS document_type, d.name AS document,
                   COALESCE(d.customer_name, {party}) AS customer, d.`{datefield}` AS date,
                   d.status AS status, d.grand_total AS value,
                   st.allocated_percentage AS contribution_pct,
                   d.grand_total * st.allocated_percentage / 100 AS contribution_value,
                   d.owner AS created_by
            FROM `tabSales Team` st
            JOIN `tab{dt}` d ON d.name = st.parent AND st.parenttype = '{dt}'
            WHERE {where}
            """.format(
                dt=dt, datefield=datefield, where=where,
                party="d.party_name" if dt == "Quotation" else "''",
            )
        )

    data = []
    if parts:
        sql = " UNION ALL ".join(parts) + " ORDER BY sales_person, date DESC"
        data = frappe.db.sql(sql, vals, as_dict=True)

    columns = [
        {"label": _("Sales Person"), "fieldname": "sales_person", "fieldtype": "Link", "options": "Sales Person", "width": 160},
        {"label": _("Type"), "fieldname": "document_type", "fieldtype": "Data", "width": 110},
        {"label": _("Document"), "fieldname": "document", "fieldtype": "Dynamic Link", "options": "document_type", "width": 160},
        {"label": _("Customer"), "fieldname": "customer", "fieldtype": "Data", "width": 180},
        {"label": _("Date"), "fieldname": "date", "fieldtype": "Date", "width": 100},
        {"label": _("Status"), "fieldname": "status", "fieldtype": "Data", "width": 110},
        {"label": _("Value"), "fieldname": "value", "fieldtype": "Currency", "width": 130},
        {"label": _("Contribution %"), "fieldname": "contribution_pct", "fieldtype": "Percent", "width": 110},
        {"label": _("Contribution Value"), "fieldname": "contribution_value", "fieldtype": "Currency", "width": 150},
        {"label": _("Created By"), "fieldname": "created_by", "fieldtype": "Data", "width": 160},
    ]
    return columns, data
