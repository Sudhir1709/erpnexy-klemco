# Klemco CS — notification layer (BRD §x.8).
# Implements the CS notification matrix surfaced as a gap in Phase 3 testing.
# All sends are best-effort: missing recipients are skipped and failures are logged,
# never blocking the underlying document save/submit.

import frappe
from frappe import _


def _safe_sendmail(recipients, subject, message, reference_doctype=None, reference_name=None):
    recipients = [r for r in (recipients or []) if r]
    if not recipients:
        return False
    try:
        frappe.sendmail(
            recipients=list(set(recipients)),
            subject=subject,
            message=message,
            reference_doctype=reference_doctype,
            reference_name=reference_name,
        )
        return True
    except Exception:
        frappe.log_error(frappe.get_traceback(), "Klemco CS notification failed")
        return False


def _user_email(user):
    if not user:
        return None
    return frappe.db.get_value("User", user, "email") or (user if "@" in (user or "") else None)


def _customer_email(customer):
    return frappe.db.get_value("Customer", customer, "email_id") if customer else None


def _cs_manager_emails():
    users = frappe.get_all(
        "Has Role", filters={"role": "CS Manager", "parenttype": "User"}, pluck="parent"
    )
    return [e for e in (frappe.db.get_value("User", u, "email") for u in users) if e]


# ── Complaint logged → assigned owner (FR-8.8 "Complaint Logged → Process Head") ──
def complaint_logged(doc, method=None):
    _safe_sendmail(
        recipients=[_user_email(doc.get("assigned_to"))],
        subject=_("Complaint {0} logged — {1}").format(doc.name, doc.get("complaint_type")),
        message=_(
            "Complaint <b>{0}</b> ({1}) for <b>{2}</b> has been logged and assigned to you."
            "<br>Priority: {3} · SLA deadline: {4}.<br>Please review."
        ).format(doc.name, doc.get("complaint_type"), doc.get("customer"), doc.get("priority"), doc.get("sla_deadline")),
        reference_doctype="CS Complaint",
        reference_name=doc.name,
    )


# ── Complaint escalated → CS Manager (FR-8.8 "SLA Breach Approaching") ──
def complaint_escalated(doc_name, customer, complaint_type):
    _safe_sendmail(
        recipients=_cs_manager_emails(),
        subject=_("URGENT: Complaint {0} approaching SLA breach").format(doc_name),
        message=_(
            "Complaint <b>{0}</b> ({1}) for {2} has consumed ≥80% of its SLA and has been escalated. "
            "Immediate action needed."
        ).format(doc_name, complaint_type, customer),
        reference_doctype="CS Complaint",
        reference_name=doc_name,
    )


# ── Complaint closed → customer CSAT (FR-8.8 "Complaint Closed → Customer") ──
def complaint_closed_csat(doc):
    _safe_sendmail(
        recipients=[_customer_email(doc.get("customer"))],
        subject=_("Your complaint {0} has been resolved").format(doc.name),
        message=_(
            "Dear {0},<br><br>Your complaint <b>{1}</b> has been resolved. "
            "We'd appreciate your feedback on how we did.<br><br>— Team Klemco"
        ).format(doc.get("customer"), doc.name),
        reference_doctype="CS Complaint",
        reference_name=doc.name,
    )


# ── Sales Order approval alerts — discount gate & credit hold (BR-OE-01 / BR-OE-02) ──
# When an order enters discount approval or credit hold, alert everyone who can act on it via
# THREE channels — email, in-app bell notification, and a to-do assignment — and surface the
# backlog in the worklist reports. Fires once, on the transition into the pending/on-hold state.

_DISCOUNT_APPROVER_ROLES = ["Sales Head", "Sales Manager", "System Manager"]
_CREDIT_APPROVER_ROLES = ["Accounts Manager", "System Manager"]
_DISCOUNT_PENDING = "Discount Approval — Sales Head"
_RC_DEVIATION_PENDING = "Pending Sales Head Approval"


def _role_users(roles):
    """Enabled, real (non-Administrator/Guest) users holding ANY of these roles."""
    users = frappe.get_all(
        "Has Role",
        filters={"role": ["in", roles], "parenttype": "User"},
        pluck="parent",
        distinct=True,
    )
    out = []
    for u in set(users):
        if u in ("Administrator", "Guest"):
            continue
        if frappe.db.get_value("User", u, "enabled"):
            out.append(u)
    return out


def _role_user_emails(roles):
    return [e for e in (frappe.db.get_value("User", u, "email") or u for u in _role_users(roles)) if e]


# ── New customer registered → CS / Marketing team (after_insert) ──
_NEW_CUSTOMER_ALERT_ROLES = ["CS Manager", "CS Executive", "Sales Manager", "Marketing Manager"]


def customer_registered(doc, method=None):
    """Alert the CS / Marketing team when a new customer is registered — email + in-app bell.
    Best-effort: never blocks the customer save."""
    subject = _("New customer registered: {0}").format(doc.get("customer_name") or doc.name)
    body = _(
        "A new customer <b>{0}</b> ({1}) has just been registered. "
        "Please review the registration details."
    ).format(doc.get("customer_name") or doc.name, doc.name)
    _safe_sendmail(_role_user_emails(_NEW_CUSTOMER_ALERT_ROLES), subject, body, "Customer", doc.name)
    try:
        users = [u for u in _role_users(_NEW_CUSTOMER_ALERT_ROLES) if u != frappe.session.user]
        if users:
            from frappe.desk.doctype.notification_log.notification_log import enqueue_create_notification
            enqueue_create_notification(users, {
                "type": "Alert",
                "document_type": "Customer",
                "document_name": doc.name,
                "subject": subject,
                "from_user": frappe.session.user,
                "email_content": body,
            })
    except Exception:
        frappe.log_error(frappe.get_traceback(), "Klemco new-customer alert failed")


# ── New sales enquiry logged → CS / Sales / Marketing team (after_insert) ──
_ENQUIRY_ALERT_ROLES = ["CS Manager", "CS Executive", "Sales Manager", "Marketing Manager"]


def enquiry_registered(doc, method=None):
    """Alert the CS / Sales / Marketing team when a new Sales Enquiry is logged — email + bell.
    Best-effort: never blocks the enquiry save."""
    party = doc.get("customer") or doc.get("party_name") or ""
    subject = _("New sales enquiry: {0}").format(doc.get("project_name") or doc.name)
    body = _(
        "A new sales enquiry <b>{0}</b> ({1}) has been logged — type <b>{2}</b>, party {3}. "
        "Please follow up and raise a quotation."
    ).format(doc.get("project_name") or doc.name, doc.name, doc.get("type_of_enquiry") or "-", party or "-")
    _safe_sendmail(_role_user_emails(_ENQUIRY_ALERT_ROLES), subject, body, "Sales Enquiry", doc.name)
    try:
        users = [u for u in _role_users(_ENQUIRY_ALERT_ROLES) if u != frappe.session.user]
        if users:
            from frappe.desk.doctype.notification_log.notification_log import enqueue_create_notification
            enqueue_create_notification(users, {
                "type": "Alert",
                "document_type": "Sales Enquiry",
                "document_name": doc.name,
                "subject": subject,
                "from_user": frappe.session.user,
                "email_content": body,
            })
    except Exception:
        frappe.log_error(frappe.get_traceback(), "Klemco new-enquiry alert failed")


def _alert_approvers(doc, kind):
    """Email + in-app notification + to-do assignment to the approver group. Each channel is
    best-effort and isolated so a notification failure never blocks the order save."""
    if kind == "credit":
        roles, verb, action = _CREDIT_APPROVER_ROLES, "on Credit Hold", "Release Credit Hold"
        detail = doc.get("cs_credit_hold_reason") or ""
    else:  # discount / rc_deviation
        roles, verb, action = _DISCOUNT_APPROVER_ROLES, "pending discount approval", "Approve / Reject the discount"
        detail = _("Discount threshold {0}%.").format(doc.get("cs_discount_threshold"))

    users = [u for u in _role_users(roles) if u != frappe.session.user]
    if not users:
        return

    amount = frappe.utils.fmt_money(doc.get("grand_total"), currency=doc.get("currency")) \
        if doc.get("grand_total") else ""
    subject = _("Sales Order {0} is {1}").format(doc.name, verb)
    body = _(
        "Sales Order <b>{0}</b> for <b>{1}</b> ({2}) is <b>{3}</b>.<br>{4}<br><br>"
        "Open the order and use <b>{5}</b>."
    ).format(doc.name, doc.get("customer_name") or doc.get("customer"), amount, verb, detail, action)

    emails = [e for e in (frappe.db.get_value("User", u, "email") or u for u in users) if e]

    # 1) Email
    _safe_sendmail(emails, subject, body, "Sales Order", doc.name)

    # 2) In-app bell notification
    try:
        from frappe.desk.doctype.notification_log.notification_log import enqueue_create_notification
        enqueue_create_notification(users, {
            "type": "Alert",
            "document_type": "Sales Order",
            "document_name": doc.name,
            "subject": subject,
            "from_user": frappe.session.user,
            "email_content": body,
        })
    except Exception:
        frappe.log_error(frappe.get_traceback(), "Klemco approval bell-notification failed")

    # 3) To-do assignment (notify=0 — we send our own email above)
    try:
        from frappe.desk.form.assign_to import add as _assign_add
        _assign_add({
            "assign_to": users,
            "doctype": "Sales Order",
            "name": doc.name,
            "description": subject,
            "notify": 0,
        })
    except Exception:
        frappe.log_error(frappe.get_traceback(), "Klemco approval assignment failed")


def notify_approval_transitions(doc, method=None):
    """on_update: alert approvers only when the order first ENTERS a pending/on-hold state."""
    try:
        prev = doc.get_doc_before_save()
        # Discount gate
        new_d = doc.get("cs_discount_approval_status")
        old_d = prev.get("cs_discount_approval_status") if prev else None
        if new_d == _DISCOUNT_PENDING and old_d != _DISCOUNT_PENDING:
            _alert_approvers(doc, "discount")
        # RC-deviation gate (a discount deviation on a Rate-Contract customer)
        new_rc = doc.get("custom_deviation_approval_status")
        old_rc = prev.get("custom_deviation_approval_status") if prev else None
        if new_rc == _RC_DEVIATION_PENDING and old_rc != _RC_DEVIATION_PENDING:
            _alert_approvers(doc, "discount")
        # Credit hold
        new_c = doc.get("cs_credit_hold_status")
        old_c = prev.get("cs_credit_hold_status") if prev else None
        if new_c == "On Hold" and old_c != "On Hold":
            _alert_approvers(doc, "credit")
    except Exception:
        frappe.log_error(frappe.get_traceback(), "Klemco approval-transition alert failed")


def notify_decision(sales_order, kind, decision, by_user):
    """Close the loop: tell the order's creator the outcome, and clear the approval to-dos."""
    try:
        owner = frappe.db.get_value("Sales Order", sales_order, "owner")
        label = "credit hold" if kind == "credit" else "discount"
        _safe_sendmail(
            recipients=[_user_email(owner)],
            subject=_("Sales Order {0}: {1} {2}").format(sales_order, label, decision),
            message=_(
                "The {0} on Sales Order <b>{1}</b> was <b>{2}</b> by {3}."
            ).format(label, sales_order, decision, by_user),
            reference_doctype="Sales Order",
            reference_name=sales_order,
        )
        from frappe.desk.form.assign_to import close_all_assignments
        close_all_assignments("Sales Order", sales_order)
    except Exception:
        frappe.log_error(frappe.get_traceback(), "Klemco decision notification failed")


# ── Order dispatched → customer (FR-OE-08 / FR-DP-08), on Delivery Note submit ──
def order_dispatched(doc, method=None):
    docket = doc.get("lr_no") or doc.get("vehicle_no")
    _safe_sendmail(
        recipients=[_customer_email(doc.get("customer"))],
        subject=_("Your order has been dispatched — {0}").format(doc.name),
        message=_(
            "Dear {0},<br><br>Your delivery <b>{1}</b> has been dispatched.{2}"
            "<br><br>— Team Klemco"
        ).format(doc.get("customer_name") or doc.get("customer"), doc.name,
                 (_("<br>Docket / vehicle: {0}").format(docket) if docket else "")),
        reference_doctype="Delivery Note",
        reference_name=doc.name,
    )
