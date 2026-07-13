# Sales Order server-side events — BRD v1.3
#   CR-09 / FR-SO-16  Required Delivery Date must be >= today (no back-dating)
#   CR-14 / FR-SO-04  Preferred 3PL "Others (not yet decided)" needs a note
#   CR-10 / FR-SO-06  RC discount = Conditional Deviation -> Sales Head approval gate
#   CR-17 / FR-SO-09  Simplified acknowledgement email (no delivery date)
#   FR-5-02           Auto-GST: default the Tax Category from plant vs delivery state
#   BR-OE-01          Discount Matrix: max line discount by customer type / item group
#   BR-OE-02          Credit hold — block submission on hold; Finance release action

import frappe
from frappe import _
from frappe.utils import getdate, nowdate, formatdate, flt, fmt_money

OTHERS_3PL = "Others (not yet decided)"
RC_TYPE = "RC (Rate Contract)"
FINANCE_ROLES = {"Accounts Manager", "System Manager"}


def before_validate(doc, method=None):
    # Safety net over India Compliance: if the tax category is still blank, derive
    # In-State / Out-State from the dispatch (plant) state vs the delivery state and
    # apply the matching GST template. Runs before validate so IC computes the amounts.
    _auto_gst_tax_category(doc)
    # BR-OE-01: set the discount threshold from the Discount Matrix for this customer type,
    # so the existing gate (Server Script + client) checks against the configured maximum.
    _apply_discount_matrix(doc)


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
    # BR-OE-02: an order on credit hold cannot be submitted until Finance releases it.
    if doc.get("cs_credit_hold_status") == "On Hold":
        frappe.throw(_(
            "This order is on <b>Credit Hold</b> — {0} Finance must release it before it can be "
            "submitted (BR-OE-02)."
        ).format(doc.get("cs_credit_hold_reason") or ""))


# ── BR-OE-01  Discount Matrix ─────────────────────────────────────────────────
def _apply_discount_matrix(doc):
    """Drive the discount-approval gate from the CS Discount Matrix. Sets the order's
    cs_discount_threshold to the configured max for this customer type (the existing
    Server Script / client gate then trips against it). Per-line item-group limits that
    are stricter also flag the order for approval directly."""
    try:
        if not doc.get("customer"):
            return
        from klemco_cs.customer_service.doctype.cs_discount_matrix.cs_discount_matrix import get_max_discount

        ctype = frappe.db.get_value("Customer", doc.customer, "custom_klemco_customer_type") or "Regular"

        # Order-level threshold = the customer type's general (all-items) limit.
        general = get_max_discount(ctype, None)
        if general is not None:
            doc.cs_discount_threshold = general

        # Per-line: flag approval if a line exceeds its (possibly stricter) item-group limit.
        exceeded = False
        for row in doc.get("items", []):
            line_disc = flt(row.get("discount_percentage"))
            if line_disc <= 0:
                continue
            ig = frappe.db.get_value("Item", row.item_code, "item_group") if row.item_code else None
            cap = get_max_discount(ctype, ig)
            if cap is None:
                cap = general
            if cap is not None and line_disc > cap:
                exceeded = True
                break

        if exceeded and doc.get("cs_discount_approval_status") != "Approved":
            doc.cs_discount_approval_status = "Discount Approval — Sales Head"
    except Exception:
        frappe.log_error(frappe.get_traceback(), "Klemco discount matrix check failed")


# ── BR-OE-02  Finance release of a credit hold ────────────────────────────────
@frappe.whitelist()
def release_credit_hold(sales_order):
    """Finance clears a credit hold so the order can proceed. Roles: Accounts Manager / System Manager."""
    if not (FINANCE_ROLES & set(frappe.get_roles())):
        frappe.throw(_("Only Finance (Accounts Manager) can release a credit hold."))

    doc = frappe.get_doc("Sales Order", sales_order)
    if doc.get("cs_credit_hold_status") != "On Hold":
        frappe.throw(_("This order is not on credit hold."))

    doc.db_set("cs_credit_hold_status", "Clear")
    doc.db_set("cs_credit_released_by", frappe.session.user)
    doc.add_comment("Comment", _("Credit hold released by {0}.").format(frappe.session.user))
    return "Clear"


def on_submit(doc, method=None):
    _send_acknowledgement(doc)


# ── FR-5-02  Auto-GST tax category ────────────────────────────────────────────
# India Compliance already auto-picks the tax when the company GSTIN (dispatch state)
# and place of supply (delivery state) are known. This is a *safety net*: it only fills
# a still-blank Tax Category, only for the plain In-State/Out-State case, and never
# overrides a value already set by the user or by India Compliance.
def _auto_gst_tax_category(doc):
    try:
        if doc.get("tax_category"):
            return  # already chosen (manually or by India Compliance) — respect it

        from_state = _dispatch_state(doc)
        to_state = _delivery_state(doc)
        if not from_state or not to_state:
            return

        category = "In-State" if from_state == to_state else "Out-State"
        doc.tax_category = category

        if not doc.get("taxes"):
            template = frappe.db.get_value(
                "Sales Taxes and Charges Template",
                {"company": doc.company, "tax_category": category, "disabled": 0},
                "name",
            )
            if template:
                doc.taxes_and_charges = template
                from erpnext.controllers.accounts_controller import get_taxes_and_charges
                for tax in get_taxes_and_charges("Sales Taxes and Charges Template", template):
                    doc.append("taxes", tax)
    except Exception:
        # Tax automation must never block a save; log and let the user pick manually.
        frappe.log_error(frappe.get_traceback(), "Klemco SO auto-GST tax category failed")


def _normalise_state(value):
    """Accept a plain state name or India Compliance's 'NN-State' place-of-supply format."""
    if not value:
        return None
    value = str(value).strip()
    if len(value) > 3 and value[2] == "-" and value[:2].isdigit():
        value = value[3:]
    return value.lower()


def _dispatch_state(doc):
    # Prefer an explicit dispatch/plant address on the order, then the company GSTIN's
    # state, then the company's default GST-registered address.
    if doc.get("company_address"):
        st = frappe.db.get_value("Address", doc.company_address, "gst_state")
        if st:
            return _normalise_state(st)
    if doc.get("company_gstin"):
        try:
            from india_compliance.gst_india.utils import get_state
            st = get_state(doc.company_gstin[:2])
            if st:
                return _normalise_state(st)
        except Exception:
            pass
    addr = frappe.db.get_value(
        "Address", {"is_your_company_address": 1, "gstin": ["!=", ""]}, ["gst_state"], as_dict=True
    )
    return _normalise_state(addr.gst_state) if addr else None


def _delivery_state(doc):
    if doc.get("place_of_supply"):
        return _normalise_state(doc.place_of_supply)
    for addr_field in ("shipping_address_name", "customer_address"):
        if doc.get(addr_field):
            st = frappe.db.get_value("Address", doc.get(addr_field), "gst_state")
            if st:
                return _normalise_state(st)
    return None


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
