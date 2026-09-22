# SAP-style "Document Flow" — the whole connected sales/plant transaction chain for a document,
# discovered from any node and returned as a tree. Curated edges (not the generic linked-doc engine),
# so the tree is the meaningful lifecycle:
#   Sales Enquiry -> Quotation -> Sales Order -> {Delivery Note, Sales Invoice, Payment Entry,
#                                                 Plant Order -> Purchase Invoice}
# Each node carries its status + date + amount; every node is permission-filtered.

import frappe
from frappe import _

# Stage rank per doctype — used to root the tree at the earliest stage and order children.
_RANK = {
    "Sales Enquiry": 0, "Quotation": 1, "Sales Order": 2,
    "Plant Order": 3, "KM Order": 3, "Delivery Note": 3,
    "Purchase Invoice": 4, "Sales Invoice": 4, "Payment Entry": 5,
}
_DATE_FIELD = {
    "Sales Enquiry": "enquiry_date", "Quotation": "transaction_date", "Sales Order": "transaction_date",
    "Delivery Note": "posting_date", "Sales Invoice": "posting_date", "Purchase Invoice": "posting_date",
    "Payment Entry": "posting_date", "KM Order": "creation",
}
_MAX_NODES = 200
_LABEL = {"KM Order": "Plant Order"}   # user-facing name differs from the internal doctype


def _key(dt, name):
    return dt + "::" + name


def _neighbours(dt, name):
    """Both-direction curated edges from (dt, name) -> list of (doctype, name). Best-effort per edge."""
    out = []

    def add(edt, enames):
        for en in enames:
            if en:
                out.append((edt, en))

    def child_parents(child_dt, field, value, parent_type):
        # parents whose child row's `field` == value
        rows = frappe.get_all(child_dt, filters={field: value, "parenttype": parent_type},
                              fields=["parent"], pluck="parent")
        return list(dict.fromkeys(rows))

    try:
        if dt == "Sales Enquiry":
            add("Quotation", frappe.get_all("Quotation", filters={"cs_sales_enquiry": name}, pluck="name"))

        elif dt == "Quotation":
            se = frappe.db.get_value("Quotation", name, "cs_sales_enquiry")
            add("Sales Enquiry", [se])
            add("Sales Order", child_parents("Sales Order Item", "prevdoc_docname", name, "Sales Order"))

        elif dt == "Sales Order":
            # up: source quotations
            add("Quotation", frappe.get_all("Sales Order Item",
                filters={"parent": name, "prevdoc_docname": ["!=", ""]}, pluck="prevdoc_docname"))
            # down
            add("Delivery Note", child_parents("Delivery Note Item", "against_sales_order", name, "Delivery Note"))
            add("Sales Invoice", child_parents("Sales Invoice Item", "sales_order", name, "Sales Invoice"))
            add("KM Order", frappe.get_all("KM Order", filters={"linked_sales_order": name}, pluck="name"))
            add("Payment Entry", _payments_for("Sales Order", name))

        elif dt == "Delivery Note":
            add("Sales Order", frappe.get_all("Delivery Note Item",
                filters={"parent": name, "against_sales_order": ["!=", ""]}, pluck="against_sales_order"))
            add("Sales Invoice", child_parents("Sales Invoice Item", "delivery_note", name, "Sales Invoice"))

        elif dt == "Sales Invoice":
            add("Sales Order", frappe.get_all("Sales Invoice Item",
                filters={"parent": name, "sales_order": ["!=", ""]}, pluck="sales_order"))
            add("Delivery Note", frappe.get_all("Sales Invoice Item",
                filters={"parent": name, "delivery_note": ["!=", ""]}, pluck="delivery_note"))
            add("Payment Entry", _payments_for("Sales Invoice", name))

        elif dt == "KM Order":
            add("Sales Order", [frappe.db.get_value("KM Order", name, "linked_sales_order")])
            add("Purchase Invoice", frappe.get_all("Purchase Invoice", filters={"cs_plant_order": name}, pluck="name"))

        elif dt == "Purchase Invoice":
            add("KM Order", [frappe.db.get_value("Purchase Invoice", name, "cs_plant_order")])

        elif dt == "Payment Entry":
            refs = frappe.get_all("Payment Entry Reference",
                filters={"parent": name, "reference_doctype": ["in", ["Sales Order", "Sales Invoice"]]},
                fields=["reference_doctype", "reference_name"])
            for r in refs:
                add(r.reference_doctype, [r.reference_name])
    except Exception:
        frappe.log_error(frappe.get_traceback(), "Klemco document_flow neighbours failed")

    return [(edt, en) for edt, en in out if en]


def _payments_for(ref_dt, ref_name):
    return list(dict.fromkeys(frappe.get_all("Payment Entry Reference",
        filters={"reference_doctype": ref_dt, "reference_name": ref_name, "docstatus": ["<", 2]},
        fields=["parent"], pluck="parent")))


def _node(dt, name):
    """One node's display data — permission-checked; returns None if the user can't read it."""
    if not frappe.has_permission(dt, "read", doc=name):
        return None
    meta = frappe.get_meta(dt)
    fields = ["name", "docstatus"]
    for f in ("status", _DATE_FIELD.get(dt, "creation"), "grand_total"):
        if f not in fields and meta.get_field(f):
            fields.append(f)
    row = frappe.db.get_value(dt, name, fields, as_dict=True) or {}
    docstatus = row.get("docstatus") or 0
    return {
        "doctype": dt,
        "name": name,
        "label": _LABEL.get(dt, dt),
        "status": row.get("status") or {0: "Draft", 1: "Submitted", 2: "Cancelled"}.get(docstatus, ""),
        "docstatus": docstatus,
        "date": frappe.format(row.get(_DATE_FIELD.get(dt, "creation")), {"fieldtype": "Date"}) if row.get(_DATE_FIELD.get(dt, "creation")) else "",
        "amount": frappe.utils.fmt_money(row.get("grand_total")) if row.get("grand_total") else "",
        "rank": _RANK.get(dt, 9),
    }


@frappe.whitelist()
def get_document_flow(doctype, name):
    """Discover the whole connected chain from (doctype, name) and return {nodes, edges, anchor}.
    Nodes are permission-filtered; edges are parent->child by stage rank. The client renders the tree."""
    if not doctype or not name:
        return {}
    if not frappe.has_permission(doctype, "read", doc=name):
        frappe.throw(_("Not permitted to read {0} {1}").format(doctype, name), frappe.PermissionError)

    # BFS over both-direction edges to collect the connected set (cycle-safe, capped).
    seen, queue, nodes = set(), [(doctype, name)], {}
    while queue and len(seen) < _MAX_NODES:
        dt, nm = queue.pop(0)
        k = _key(dt, nm)
        if k in seen:
            continue
        seen.add(k)
        for edt, en in _neighbours(dt, nm):
            if _key(edt, en) not in seen:
                queue.append((edt, en))

    # Build permission-filtered node map.
    for k in seen:
        dt, nm = k.split("::", 1)
        n = _node(dt, nm)
        if n:
            nodes[k] = n

    # Directed edges (lower rank -> higher rank) between surviving nodes.
    edges = []
    for k in nodes:
        dt, nm = k.split("::", 1)
        for edt, en in _neighbours(dt, nm):
            ek = _key(edt, en)
            if ek in nodes and nodes[k]["rank"] < nodes[ek]["rank"]:
                edges.append([k, ek])

    return {
        "anchor": _key(doctype, name),
        "nodes": nodes,
        "edges": edges,
    }
