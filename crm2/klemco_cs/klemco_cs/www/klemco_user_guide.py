import frappe


def get_context(context):
    # Readable by any logged-in ERP user; guests are sent to login and back.
    # NOTE: controller filename MUST use underscores — Frappe resolves the www
    # controller for "klemco-user-guide.html" as "klemco_user_guide.py". A hyphenated
    # name silently skips this gate (see the ai_help.py security fix).
    if frappe.session.user == "Guest":
        frappe.local.flags.redirect_location = "/login?redirect-to=/klemco-user-guide"
        raise frappe.Redirect
    context.no_cache = 1
    context.user = frappe.session.user
