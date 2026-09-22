"""Print-page behaviour shared by every Klemco document (Sales Order, Quotation, Sales Invoice,
Delivery Note, Purchase Order ...).

ERPNext ships ``erpnext/public/js/print.js`` as ``page_js["print"]``. On the print page it calls
``erpnext.controllers.accounts_controller.get_missing_company_details`` whenever the selected
print format is a stock "... Standard" / "... with Item Image" format *or* the letter head is the
stock "Company Letterhead" / "Company Letterhead - Grey", and pops an "Enter Company Details"
dialog (logo / website / phone / email / address) when the Company master lacks any of them.

Klemco prints use self-contained branded Jinja formats ("Klemco Sales Order", "Klemco Quotation",
"Klemco Tax Invoice", "Delivery Challan") that are picked automatically, and company details are
maintained on the Company master by an administrator, not via a print-time prompt. The method is
therefore replaced through ``override_whitelisted_methods`` (hooks.py) with this no-op.
"""
import frappe


@frappe.whitelist()
def get_missing_company_details(doctype=None, docname=None):
    """Replaces ERPNext's stock check so the "Enter Company Details" dialog never opens.

    Keeps the ``(doctype, docname)`` signature ``print.js`` passes as kwargs. Returning ``None``
    means ``r.message`` is absent on the client, which is the branch that opens no dialog.
    """
    return None
