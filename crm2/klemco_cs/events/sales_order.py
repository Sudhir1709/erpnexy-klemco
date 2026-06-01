# Sales Order server-side events — BRD v1.3
#   CR-09 / FR-SO-16  Required Delivery Date must be >= today (no back-dating)
#   CR-14 / FR-SO-04  Preferred 3PL "Others (not yet decided)" needs a note
#   CR-10 / FR-SO-06  RC discount = Conditional Deviation -> Sales Head approval gate
#   CR-17 / FR-SO-09  Simplified acknowledgement email (no delivery date)

import frappe
from frappe import _
from frappe.utils import getdate, nowdate, formatdate

OTHERS_3PL = "Others (not yet decided)"
RC_TYPE = "RC (Rate Contract)"


def validate(doc, method=None):
    _validate_delivery_dates(doc)
    _validate_3pl(doc)
    _flag_rc_deviation(doc)


def before_submit(doc, method=None):
    # BR-SO-01: an RC discount deviation cannot be submitted until the Sales Head approves.
    if doc.get("custom_rc_deviation") and doc.get("custom_deviation_approval_status") != "Approved":
        frappe.throw(_(
            "This order applies a discount on a Rate Contract customer and is flagged as a "
            "Conditional Deviation. It needs Sales Head approval before submission (BR-SO-01 / FR-SO-06)."
        ))


def on_submit(doc, method=None):
    _send_acknowledgement(doc)


# ── CR-09 / FR-SO-16 ──────────────────────────────────────────────────────────
def _validate_delivery_dates(doc):
    today = getdate(nowdate())

    if doc.get("delivery_date") and getdate(doc.delivery_date) < today:
        frappe.throw(_(
            "Delivery Date {0} cannot be in the past. Future dates are allowed "
            "(including for out-of-stock items) — FR-SO-16."
        ).format(formatdate(doc.delivery_date)))

    for row in doc.get("items", []):
        if row.get("delivery_date") and getdate(row.delivery_date) < today:
            frappe.throw(_(
                "Row #{0} ({1}): Required Delivery Date {2} cannot be back-dated (FR-SO-16)."
            ).format(row.idx, row.item_code, formatdate(row.delivery_date)))


# ── CR-14 / FR-SO-04 ──────────────────────────────────────────────────────────
def _validate_3pl(doc):
    if doc.get("custom_preferred_3pl") == OTHERS_3PL and not (doc.get("custom_3pl_note") or "").strip():
        frappe.throw(_(
            "Preferred 3PL is 'Others (not yet decided)'. Add a Specify / Note value; the "
            "partner must be finalised at dispatch (FR-SO-04)."
        ))


# ── CR-10 / FR-SO-06 ──────────────────────────────────────────────────────────
def _flag_rc_deviation(doc):
    customer_type = (
        frappe.db.get_value("Customer", doc.customer, "custom_klemco_customer_type")
        if doc.get("customer") else None
    )
    is_rc = customer_type == RC_TYPE
    has_discount = (
        any((row.get("discount_percentage") or 0) > 0 or (row.get("discount_amount") or 0) > 0
            for row in doc.get("items", []))
        or (doc.get("additional_discount_percentage") or 0) > 0
        or (doc.get("discount_amount") or 0) > 0
    )

    if is_rc and has_discount:
        doc.custom_rc_deviation = 1
        if doc.get("custom_deviation_approval_status") not in ("Approved", "Rejected"):
            doc.custom_deviation_approval_status = "Pending Sales Head Approval"
    else:
        doc.custom_rc_deviation = 0
        # Reset only auto-set states; keep an explicit Approved/Rejected audit trail.
        if doc.get("custom_deviation_approval_status") in (None, "", "Pending Sales Head Approval"):
            doc.custom_deviation_approval_status = "Not Required"
            doc.custom_deviation_approved_by = None


@frappe.whitelist()
def set_deviation_decision(sales_order, decision):
    """Called from the Sales Order form by a Sales Head to approve/reject an RC deviation."""
    if decision not in ("Approved", "Rejected"):
        frappe.throw(_("Invalid decision."))

    roles = set(frappe.get_roles())
    if not ({"Sales Head", "System Manager"} & roles):
        frappe.throw(_("Only the Sales Head can decide on an RC discount deviation."))

    doc = frappe.get_doc("Sales Order", sales_order)
    if not doc.get("custom_rc_deviation"):
        frappe.throw(_("This order has no RC discount deviation to act on."))

    doc.db_set("custom_deviation_approval_status", decision)
    doc.db_set("custom_deviation_approved_by", frappe.session.user)
    doc.add_comment(
        "Comment",
        _("RC discount Conditional Deviation {0} by {1}.").format(decision, frappe.session.user),
    )
    return decision


# ── CR-17 / FR-SO-09 ──────────────────────────────────────────────────────────
def _send_acknowledgement(doc):
    """Simple 'order execution initiated' email — deliberately NO delivery date (FR-SO-09)."""
    try:
        recipients = _ack_recipients(doc)
        if not recipients:
            return

        message = _(
            "Dear {0},<br><br>Thank you for your order <b>{1}</b>. "
            "We have initiated order execution and will keep you updated on dispatch."
            "<br><br>— Team Klemco"
        ).format(doc.customer_name or doc.customer, doc.name)

        frappe.sendmail(
            recipients=list(set(recipients)),
            subject=_("Order {0} received — execution initiated").format(doc.name),
            message=message,
            reference_doctype="Sales Order",
            reference_name=doc.name,
        )
    except Exception:
        # Never block order submission on a notification failure.
        frappe.log_error(frappe.get_traceback(), "Klemco SO acknowledgement email failed")


def _ack_recipients(doc):
    recipients = []
    if doc.get("contact_email"):
        recipients.append(doc.contact_email)
    else:
        cust_email = frappe.db.get_value("Customer", doc.customer, "email_id") if doc.get("customer") else None
        if cust_email:
            recipients.append(cust_email)

    # Assigned sales person (first row of the Sales Team), resolved via Employee -> user email.
    if doc.get("sales_team"):
        sp = doc.sales_team[0].sales_person
        employee = frappe.db.get_value("Sales Person", sp, "employee") if sp else None
        if employee:
            email = frappe.db.get_value("Employee", employee, "user_id") or frappe.db.get_value(
                "Employee", employee, "company_email"
            )
            if email:
                recipients.append(email)
    return recipients
