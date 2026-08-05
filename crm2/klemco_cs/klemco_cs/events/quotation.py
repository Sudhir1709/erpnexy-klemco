# Quotation server-side events.
import frappe
from frappe import _
from klemco_cs.events.pf import reconcile_pf
from klemco_cs.events.sales_order import (
    _auto_gst_tax_category, _apply_discount_matrix, _flag_discount_approval,
    DISCOUNT_APPROVERS, _PENDING,
)


def before_validate(doc, method=None):
    # Auto-GST: 18% split — In-State (CGST+SGST) or Out-State (IGST) from the delivery state.
    _auto_gst_tax_category(doc)
    # BR-OE-01: set the discount cap from the Discount Matrix for this customer type.
    _apply_discount_matrix(doc)
    # Optional Packaging & Forwarding charge (1.5% before tax, GST-inclusive) — after GST rows exist.
    reconcile_pf(doc)


def validate(doc, method=None):
    # Flag the quotation for Sales-Head approval when a line discount exceeds the matrix cap.
    _flag_discount_approval(doc)


def before_submit(doc, method=None):
    status = doc.get("cs_discount_approval_status")
    if status == _PENDING:
        frappe.throw(_(
            "This quotation is <b>pending Sales-Head approval</b> for its discount and cannot be "
            "submitted yet (BR-OE-01)."
        ))
    if status == "Rejected":
        frappe.throw(_(
            "The discount on this quotation was <b>Rejected</b>. Revise it within the allowed limit "
            "before submitting (BR-OE-01)."
        ))


@frappe.whitelist()
def set_discount_decision(quotation, decision):
    """Sales Head / Sales Manager approves or rejects an over-cap discount on a Quotation (BR-OE-01)."""
    if decision not in ("Approved", "Rejected"):
        frappe.throw(_("Invalid decision."))
    if not (DISCOUNT_APPROVERS & set(frappe.get_roles())):
        frappe.throw(_("Only a Sales Head or Sales Manager can approve/reject a discount."))
    doc = frappe.get_doc("Quotation", quotation)
    if doc.get("cs_discount_approval_status") != _PENDING:
        frappe.throw(_("This quotation is not pending discount approval."))
    doc.db_set("cs_discount_approval_status", decision)
    if doc.meta.has_field("cs_discount_approved_by"):
        doc.db_set("cs_discount_approved_by", frappe.session.user)
    doc.add_comment("Comment", _("Discount {0} by {1}.").format(decision, frappe.session.user))
    return decision
