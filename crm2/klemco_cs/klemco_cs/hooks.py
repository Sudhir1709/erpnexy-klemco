app_name = 'klemco_cs'
app_title = 'Klemco CS'
app_publisher = 'Klemco India'
app_description = 'Customer Service Module — Sales Order, Order Execution, KM Orders, Dispatch, Complaints'
app_version = '1.3.0'
app_icon = 'headset'
app_color = '#1A5276'
app_email = 'admin@klemcoindia.com'
app_license = 'MIT'

# Floating AI Help bubble on every desk page. Registered as a bundle name so the desk's
# boot loader picks it up (raw asset paths are dropped). The bundle is plain browser-ready
# JS (no transpile), so it's published to assets.json by install_widget_bundle() on migrate.
app_include_js = ["klemco_cs.bundle.js"]

fixtures = [
    {'dt': 'Workspace', 'filters': [['app', '=', 'klemco_cs']]},
    {'dt': 'Role', 'filters': [['name', 'in', [
        'CS Executive', 'CS Manager', 'CS Supervisor',
        'Sales Head', 'KM Plant Head', 'Supply Chain Lead',
    ]]]},
    # ── DB-only objects codified so a fresh site rebuilds the full module ──
    # Workflow dependencies must be listed before the Workflow itself (import order).
    {'dt': 'Workflow State', 'filters': [['name', 'in', [
        'Open', 'Under Review', 'Awaiting Customer Response', 'Escalated',
        'Reverse Pickup Arranged', 'Resolution Sent', 'Closed',
    ]]]},
    {'dt': 'Workflow Action Master', 'filters': [['name', 'in', [
        'Start Review', 'Escalate', 'Await Customer', 'Arrange Pickup',
        'Send Resolution', 'Resume Review', 'De-escalate', 'Close Complaint', 'Reopen',
    ]]]},
    {'dt': 'Workflow', 'filters': [['name', 'in', ['CS Complaint Workflow']]]},
    # v16 per-workspace sidebar nav (bugs 1 & 6) — not stored in the Workspace itself.
    {'dt': 'Workspace Sidebar', 'filters': [['name', 'in', ['Customer Service']]]},
    # Server Scripts + the Sales Order client script (previously only in the site DB).
    {'dt': 'Server Script', 'filters': [['name', 'in', [
        'CS SO Discount Check', 'CS DN Attach Client Order Confirmation',
    ]]]},
    {'dt': 'Client Script', 'filters': [['name', 'in', ['CS Sales Order Client Script']]]},
]

after_install = 'klemco_cs.setup.after_install'
# Re-apply custom fields / property setters / print format on every migrate (idempotent).
after_migrate = ['klemco_cs.customizations.apply_customizations',
                 'klemco_cs.ai_assistant.api.install_widget_bundle',
                 'klemco_cs.ai_assistant.api.install_menu',
                 'klemco_cs.ai_assistant.api.install_crm_spa_widget']

# Form (client) scripts attached to stock doctypes for the v1.3 wireframe changes.
doctype_js = {
    'Sales Order': 'public/js/sales_order.js',
    'Delivery Note': 'public/js/delivery_note.js',
    'Sales Invoice': 'public/js/sales_invoice.js',
    'Item': 'public/js/item.js',
    'CS Complaint': 'public/js/cs_complaint.js',
    'KM Order': 'public/js/km_order.js',
    'Payment Terms Template': 'public/js/payment_terms_template.js',
}

# Server-side validation / automation for the v1.3 feedback items.
doc_events = {
    'Sales Order': {
        'validate': 'klemco_cs.events.sales_order.validate',
        'before_submit': 'klemco_cs.events.sales_order.before_submit',
        'on_submit': 'klemco_cs.events.sales_order.on_submit',
    },
    'Delivery Note': {
        'validate': 'klemco_cs.events.delivery_note.validate',
        'on_submit': 'klemco_cs.notifications.order_dispatched',
    },
    'Sales Invoice': {
        'validate': 'klemco_cs.events.sales_invoice.validate',
        'before_submit': 'klemco_cs.events.sales_invoice.before_submit',
    },
    'Item': {
        'validate': 'klemco_cs.events.item.validate',
    },
    'CS Complaint': {
        'after_insert': 'klemco_cs.notifications.complaint_logged',
    },
    'Payment Terms Template': {
        'before_validate': 'klemco_cs.events.payment_terms_template.before_validate',
    },
}
