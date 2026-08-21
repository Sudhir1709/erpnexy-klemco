import frappe


def get_context(context):
    # Readable by any logged-in ERP user; guests are sent to login and back.
    if frappe.session.user == "Guest":
        frappe.local.flags.redirect_location = "/login?redirect-to=/klemco-guide"
        raise frappe.Redirect
    context.no_cache = 1
    context.user = frappe.session.user
