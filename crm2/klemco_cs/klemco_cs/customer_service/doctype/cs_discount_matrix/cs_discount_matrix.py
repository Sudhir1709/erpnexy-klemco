# CS Discount Matrix — configurable maximum line discount by customer type / item group.
# The Sales Order discount gate (events.sales_order) reads this to decide when an order
# needs Sales Head approval (BR-OE-01), replacing the old flat 10% threshold.

import frappe
from frappe.model.document import Document


class CSDiscountMatrix(Document):
    def validate(self):
        if self.max_discount_percent is None or self.max_discount_percent < 0 or self.max_discount_percent > 100:
            frappe.throw("Max Discount (%) must be between 0 and 100.")


def get_max_discount(customer_type, item_group=None):
    """Most-specific active limit for a (customer_type, item_group) pair.
    Precedence: exact type + item_group > exact type + (all items) > All + item_group >
    All + (all items). Returns a float % or None if the matrix has no applicable row."""
    ct = customer_type or "All"
    blank = ["in", [None, ""]]
    attempts = []
    if item_group:
        attempts.append({"customer_type": ct, "item_group": item_group})
    attempts.append({"customer_type": ct, "item_group": blank})
    if item_group:
        attempts.append({"customer_type": "All", "item_group": item_group})
    attempts.append({"customer_type": "All", "item_group": blank})

    for filters in attempts:
        filters["active"] = 1
        val = frappe.db.get_value("CS Discount Matrix", filters, "max_discount_percent")
        if val is not None:
            return frappe.utils.flt(val)
    return None
