# Sales Enquiry — a pre-Quotation enquiry-capture stage (Klemco sales flow).
# Salesperson logs an enquiry; a Quotation can be created from it (auto-linked so the
# Quotation number/value/date backfill here), or it can be closed if it never converts.

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.model.mapper import get_mapped_doc

# Roles allowed to close an enquiry.
ENQUIRY_ROLES = {"CS Executive", "CS Supervisor", "CS Manager", "Sales Manager", "System Manager"}


class SalesEnquiry(Document):
    def validate(self):
        if not (self.customer or self.party_name):
            frappe.throw(_("Enter an existing Customer or a Prospect Name."))
        if not self.status:
            self.status = "Open"
        if self.status == "Closed — Lost" and not self.close_reason:
            frappe.throw(_("Enter a Close Reason when the enquiry is Closed — Lost."))


@frappe.whitelist()
def make_quotation(source_name, target_doc=None):
    """Build a draft Quotation from a Sales Enquiry, linked back so its number/value/date
    backfill onto the enquiry when the Quotation is saved (see events.quotation.on_update)."""

    def set_missing(source, target):
        target.cs_sales_enquiry = source.name
        # Only pre-fill the party when an existing Customer is linked; a free-text prospect
        # has no Customer master yet, so leave it for the user to pick/create on the Quotation.
        if source.customer:
            target.quotation_to = "Customer"
            target.party_name = source.customer
        if source.type_of_enquiry == "SITC":
            target.cs_project_type = "SITC / Project"
            scope = _("Project: {0}").format(source.project_name or "")
            if source.project_location:
                scope += "\n" + source.project_location
            target.cs_scope_of_work = scope

    return get_mapped_doc(
        "Sales Enquiry",
        source_name,
        {"Sales Enquiry": {"doctype": "Quotation"}},
        target_doc,
        set_missing,
    )


@frappe.whitelist()
def close_enquiry(sales_enquiry, reason):
    """Mark an enquiry Closed — Lost (it did not convert to a quotation). Role-gated."""
    if not (ENQUIRY_ROLES & set(frappe.get_roles())):
        frappe.throw(_("You are not permitted to close an enquiry."))
    if not reason:
        frappe.throw(_("A reason is required to close the enquiry."))
    doc = frappe.get_doc("Sales Enquiry", sales_enquiry)
    if doc.status == "Converted":
        frappe.throw(_("This enquiry already converted to an order and cannot be closed."))
    doc.status = "Closed — Lost"
    doc.close_reason = reason
    doc.save()
    doc.add_comment("Info", _("Enquiry closed — Lost: {0}").format(reason))
    return doc.status
