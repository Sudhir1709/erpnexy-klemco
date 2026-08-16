# Link-field search queries for the sales-team "Customer Name + State" picker.
# Sales-team users (Sales User / Sales Manager, not System Manager) pick customers from a list
# showing only the customer name and its State — no group/territory/mobile/address columns.

import frappe


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def customer_state_query(doctype, txt, searchfield, start, page_len, filters):
    """Customers as [name, State] — State from the customer's primary Address (gst_state, else state)."""
    like = "%{0}%".format(txt or "")
    return frappe.db.sql(
        """
        SELECT c.name,
               COALESCE(NULLIF(a.gst_state, ''), a.state, '') AS state
        FROM `tabCustomer` c
        LEFT JOIN `tabAddress` a ON a.name = c.customer_primary_address
        WHERE c.disabled = 0
          AND (c.name LIKE %(txt)s OR c.customer_name LIKE %(txt)s)
        ORDER BY
          IF(LOCATE(%(_txt)s, c.name) > 0, LOCATE(%(_txt)s, c.name), 99999),
          c.name
        LIMIT %(start)s, %(page_len)s
        """,
        {"txt": like, "_txt": txt or "", "start": start, "page_len": page_len},
    )
