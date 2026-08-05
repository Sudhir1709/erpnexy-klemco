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
    # Optional Packaging & Forwarding charge (before tax, GST-inclusive) — after GST rows exist.
    from klemco_cs.events.pf import reconcile_pf
    reconcile_pf(doc)


def validate(doc, method=None):
    _validate_delivery_dates(doc)
    _validate_3pl(doc)
    _flag_rc_deviation(doc)
    _flag_discount_approval(doc)
    _check_credit_hold(doc)


def before_submit(doc, method=None):
    # BR-SO-01: an RC discount deviation cannot be submitted until the Sales Head approves.
    if doc.get("custom_rc_deviation") and doc.get("custom_deviation_approval_status") != "Approved":
        frappe.throw(_(
            "This order applies a discount on a Rate Contract customer and is flagged as a "
            "Conditional Deviation. It needs Sales Head approval before submission (BR-SO-01 / FR-SO-06)."
        ))
    # BR-OE-01: an over-cap discount must be Approved (by Sales Head / Sales Manager) before submit.
    status = doc.get("cs_discount_approval_status")
    if status == "Discount Approval — Sales Head":
        frappe.throw(_(
            "This order is <b>pending Sales-Head approval</b> for its discount and cannot be "
            "submitted yet (BR-OE-01)."
        ))
    if status == "Rejected":
        frappe.throw(_(
            "The discount on this order was <b>Rejected</b>. Revise the discount within the allowed "
            "limit (or get it approved) before submitting (BR-OE-01)."
        ))
    # BR-OE-02: an order on credit hold cannot be submitted until Finance releases it.
    if doc.get("cs_credit_hold_status") == "On Hold":
        frappe.throw(_(
            "This order is on <b>Credit Hold</b>. {0} Finance must release it before it can be "
            "submitted (BR-OE-02)."
        ).format(doc.get("cs_credit_hold_reason") or ""))


# ── BR-OE-01  Discount Matrix ─────────────────────────────────────────────────
def _doc_customer(doc):
    """The customer of a Sales Order (customer) or a Quotation (party_name when quotation_to=Customer)."""
    if doc.get("customer"):
        return doc.get("customer")
    if doc.get("quotation_to") == "Customer" and doc.get("party_name"):
        return doc.get("party_name")
    return None


def _customer_type(doc):
    cust = _doc_customer(doc)
    return (cust and frappe.db.get_value("Customer", cust, "custom_klemco_customer_type")) or "Regular"


DISCOUNT_APPROVERS = {"Sales Head", "Sales Manager", "System Manager"}
_PENDING = "Discount Approval — Sales Head"


def _apply_discount_matrix(doc):
    """Set cs_discount_threshold from the Discount Matrix for this customer type so the
    order shows the configured maximum. Enforcement is via _flag_discount_approval +
    before_submit (the blocking CS Sales Order Workflow is retired in favour of this
    field-based approval, mirroring the RC-deviation flow)."""
    try:
        if not _doc_customer(doc):
            return
        from klemco_cs.customer_service.doctype.cs_discount_matrix.cs_discount_matrix import get_max_discount
        general = get_max_discount(_customer_type(doc), None)
        if general is not None:
            doc.cs_discount_threshold = general
    except Exception:
        frappe.log_error(frappe.get_traceback(), "Klemco discount matrix threshold failed")


def _flag_discount_approval(doc):
    """Auto-flag the order for Sales-Head approval when a line discount exceeds the matrix
    cap. The order still SAVES (draft); submission is blocked until it's Approved. Explicit
    Approved / Rejected decisions are preserved (only cleared when the discount is brought
    back within the cap)."""
    try:
        status = doc.get("cs_discount_approval_status")
        if _lines_exceeding_matrix(doc):
            if status not in ("Approved", "Rejected"):
                doc.cs_discount_approval_status = _PENDING
        else:
            # within the cap now — clear any auto/pending flag
            if status in (None, "", _PENDING):
                doc.cs_discount_approval_status = "Not Required"
                doc.cs_discount_approved_by = None
    except Exception:
        frappe.log_error(frappe.get_traceback(), "Klemco discount approval flag failed")


@frappe.whitelist()
def set_discount_decision(sales_order, decision):
    """Sales Head / Sales Manager approves or rejects an over-cap discount (BR-OE-01)."""
    if decision not in ("Approved", "Rejected"):
        frappe.throw(_("Invalid decision."))
    if not (DISCOUNT_APPROVERS & set(frappe.get_roles())):
        frappe.throw(_("Only a Sales Head or Sales Manager can approve/reject a discount."))

    doc = frappe.get_doc("Sales Order", sales_order)
    if doc.get("cs_discount_approval_status") != _PENDING:
        frappe.throw(_("This order is not pending discount approval."))

    doc.db_set("cs_discount_approval_status", decision)
    doc.db_set("cs_discount_approved_by", frappe.session.user)
    if doc.meta.has_field("cs_discount_approval_time"):
        doc.db_set("cs_discount_approval_time", frappe.utils.now_datetime())
    doc.add_comment("Comment", _("Discount {0} by {1}.").format(decision, frappe.session.user))
    from klemco_cs.notifications import notify_decision
    notify_decision(doc.name, "discount", decision, frappe.session.user)
    return decision


def _lines_exceeding_matrix(doc):
    """Item codes whose line discount exceeds their (customer-type, item-group) cap."""
    try:
        if not _doc_customer(doc):
            return []
        from klemco_cs.customer_service.doctype.cs_discount_matrix.cs_discount_matrix import get_max_discount
        ctype = _customer_type(doc)
        general = get_max_discount(ctype, None)
        over = []
        for row in doc.get("items", []):
            line_disc = flt(row.get("discount_percentage"))
            if line_disc <= 0:
                continue
            ig = frappe.db.get_value("Item", row.item_code, "item_group") if row.item_code else None
            cap = get_max_discount(ctype, ig)
            if cap is None:
                cap = general
            if cap is not None and line_disc > cap:
                over.append(row.item_code)
        return over
    except Exception:
        frappe.log_error(frappe.get_traceback(), "Klemco discount matrix check failed")
        return []


# ── BR-OE-02  Credit hold detection ───────────────────────────────────────────
def _check_credit_hold(doc):
    """Put the order On Hold when outstanding + this order's value exceeds the customer's
    credit limit for the company. A hold already set stays until Finance releases it."""
    try:
        if not (doc.get("customer") and doc.get("grand_total")):
            return
        limit = frappe.db.get_value(
            "Customer Credit Limit",
            {"parent": doc.customer, "company": doc.company},
            "credit_limit",
        )
        if not limit:
            return
        outstanding = frappe.db.sql(
            """SELECT IFNULL(SUM(outstanding_amount), 0) FROM `tabSales Invoice`
               WHERE customer=%s AND company=%s AND docstatus=1 AND outstanding_amount > 0""",
            (doc.customer, doc.company),
        )[0][0] or 0
        if flt(outstanding) + flt(doc.grand_total) > flt(limit):
            doc.cs_credit_hold_status = "On Hold"
            doc.cs_credit_hold_reason = _(
                "Outstanding {0} + Order {1} exceeds credit limit {2}. Finance release required. (BR-OE-02)"
            ).format(fmt_money(outstanding), fmt_money(doc.grand_total), fmt_money(limit))
        elif doc.get("cs_credit_hold_status") != "On Hold":
            doc.cs_credit_hold_status = "Clear"
    except Exception:
        frappe.log_error(frappe.get_traceback(), "Klemco credit-hold check failed")


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
    from klemco_cs.notifications import notify_decision
    notify_decision(doc.name, "credit", "Released", frappe.session.user)
    return "Clear"


def on_submit(doc, method=None):
    _send_acknowledgement(doc)
    _mark_source_quotations_accepted(doc)


def _mark_source_quotations_accepted(doc):
    """When a Sales Order is confirmed, mark the quotation(s) it was created from as 'Accepted'
    (the Quotation conversion-status field). Best-effort; never blocks the submit."""
    try:
        quos = {i.get("prevdoc_docname") for i in (doc.get("items") or [])
                if i.get("prevdoc_docname")}
        for q in quos:
            if frappe.db.exists("Quotation", q) and \
                    frappe.db.get_value("Quotation", q, "cs_conversion_status") != "Accepted":
                frappe.db.set_value("Quotation", q, "cs_conversion_status", "Accepted")
    except Exception:
        frappe.log_error(frappe.get_traceback(), "Klemco quotation auto-accept failed")


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


@frappe.whitelist()
def update_child_qty_rate(parent_doctype, trans_items, parent_doctype_name, child_docname="items"):
    """Wraps ERPNext's 'Update Items' handler (via override_whitelisted_methods) to freeze a Sales
    Order's item lines once it has been billed — no qty/rate/add/remove after invoicing. Any other
    doctype (Purchase Order, etc.) passes straight through to the original."""
    from erpnext.controllers.accounts_controller import update_child_qty_rate as _erp_update
    if parent_doctype == "Sales Order" and flt(
        frappe.db.get_value("Sales Order", parent_doctype_name, "per_billed")
    ) > 0:
        frappe.throw(_("This Sales Order has been billed — its item lines are frozen and can't be changed."))
    return _erp_update(parent_doctype, trans_items, parent_doctype_name, child_docname)
