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
