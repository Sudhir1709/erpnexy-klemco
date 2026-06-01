app_name = 'klemco_cs'
app_title = 'Klemco CS'
app_publisher = 'Klemco India'
app_description = 'Customer Service Module — Sales Order, Order Execution, KM Orders, Dispatch, Complaints'
app_version = '1.3.0'
app_icon = 'headset'
app_color = '#1A5276'
app_email = 'admin@klemcoindia.com'
app_license = 'MIT'

fixtures = [
    {'dt': 'Workspace', 'filters': [['app', '=', 'klemco_cs']]},
    {'dt': 'Role', 'filters': [['name', 'in', [
        'CS Executive', 'CS Manager', 'CS Supervisor',
        'Sales Head', 'KM Plant Head', 'Supply Chain Lead',
    ]]]},
]

after_install = 'klemco_cs.setup.after_install'
# Re-apply custom fields / property setters / print format on every migrate (idempotent).
after_migrate = ['klemco_cs.customizations.apply_customizations']

# Form (client) scripts attached to stock doctypes for the v1.3 wireframe changes.
doctype_js = {
    'Sales Order': 'public/js/sales_order.js',
    'Delivery Note': 'public/js/delivery_note.js',
    'Sales Invoice': 'public/js/sales_invoice.js',
    'Item': 'public/js/item.js',
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
}
