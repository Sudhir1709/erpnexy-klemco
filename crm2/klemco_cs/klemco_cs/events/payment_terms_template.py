# Payment Terms Template server-side events — klemco simplification.
# Invoice Portion (%) and Due Date Based On are made non-mandatory (property setters)
# so a user only has to enter Credit Days. This before_validate fills sensible defaults
# BEFORE ERPNext's validate() runs, so its "Combined invoice portion must equal 100%"
# check passes and the due date computes from Credit Days.

from frappe.utils import flt

DEFAULT_DUE_BASIS = "Day(s) after invoice date"


def before_validate(doc, method=None):
    rows = doc.get("terms") or []
    if not rows:
        return

    # Auto-pick the due-date basis when left blank, so Credit Days drives the due date.
    for term in rows:
        if not term.due_date_based_on:
            term.due_date_based_on = DEFAULT_DUE_BASIS

    # If nobody set a split, distribute 100% evenly across the rows (single row -> 100),
    # putting any rounding remainder on the last row so the total is exactly 100.00.
    # A deliberate split (any portion already set) is left untouched.
    if flt(sum(flt(term.invoice_portion) for term in rows), 2) == 0:
        share = flt(100.0 / len(rows), 3)
        for term in rows:
            term.invoice_portion = share
        drift = flt(100 - sum(flt(term.invoice_portion) for term in rows), 3)
        rows[-1].invoice_portion = flt(rows[-1].invoice_portion + drift, 3)
