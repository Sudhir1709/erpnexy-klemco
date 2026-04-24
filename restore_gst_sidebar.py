import frappe
frappe.init(site='mysite.localhost', sites_path='/home/frappe/frappe-bench/sites')
frappe.connect()
frappe.set_user('Administrator')

sidebar = frappe.get_doc('Workspace Sidebar', 'GST India')

# Rebuild from the fixture definition
sidebar.items = []

items = [
    {"label": "Home",                      "link_to": "GST India",                   "link_type": "Workspace", "type": "Link",          "child": 0, "indent": 0, "collapsible": 1, "keep_closed": 0, "icon": "home",        "show_arrow": 0},
    {"label": "Purchase Reconciliation ...", "link_to": "Purchase Reconciliation Tool","link_type": "DocType",   "type": "Link",          "child": 0, "indent": 0, "collapsible": 1, "keep_closed": 0, "icon": "book-check",  "show_arrow": 0},
    {"label": "Reports",                   "link_to": None,                          "link_type": "DocType",   "type": "Section Break", "child": 0, "indent": 1, "collapsible": 1, "keep_closed": 1, "icon": "sheet",       "show_arrow": 0},
    {"label": "IMS",                       "link_to": "GST Invoice Management System","link_type": "DocType",  "type": "Link",          "child": 1, "indent": 0, "collapsible": 1, "keep_closed": 0, "icon": "",            "show_arrow": 0},
    {"label": "GSTR-1",                    "link_to": "GSTR-1",                      "link_type": "DocType",   "type": "Link",          "child": 1, "indent": 0, "collapsible": 1, "keep_closed": 0, "icon": "",            "show_arrow": 0},
    {"label": "GSTR-3B",                   "link_to": "GSTR 3B Report",              "link_type": "DocType",   "type": "Link",          "child": 1, "indent": 0, "collapsible": 1, "keep_closed": 0, "icon": "",            "show_arrow": 0},
    {"label": "Settings",                  "link_to": None,                          "link_type": "DocType",   "type": "Section Break", "child": 0, "indent": 1, "collapsible": 1, "keep_closed": 1, "icon": "settings",    "show_arrow": 0},
    {"label": "GST Settings",              "link_to": "GST Settings",                "link_type": "DocType",   "type": "Link",          "child": 1, "indent": 0, "collapsible": 1, "keep_closed": 0, "icon": "",            "show_arrow": 0},
    {"label": "Miscellaneous",             "link_to": None,                          "link_type": "DocType",   "type": "Section Break", "child": 0, "indent": 1, "collapsible": 1, "keep_closed": 1, "icon": "layout-list", "show_arrow": 0},
    {"label": "India Compliance Account",  "link_to": "india-compliance-account",    "link_type": "Page",      "type": "Link",          "child": 1, "indent": 0, "collapsible": 1, "keep_closed": 0, "icon": "",            "show_arrow": 0},
]

for item in items:
    row = sidebar.append('items', {})
    row.label       = item['label']
    row.link_to     = item.get('link_to') or ''
    row.link_type   = item['link_type']
    row.type        = item['type']
    row.child       = item['child']
    row.indent      = item['indent']
    row.collapsible = item['collapsible']
    row.keep_closed = item['keep_closed']
    row.icon        = item.get('icon', '')
    row.show_arrow  = item['show_arrow']

sidebar.flags.ignore_links = True
sidebar.flags.ignore_mandatory = True
sidebar.save(ignore_permissions=True)

frappe.db.commit()
print("GST India sidebar restored:")
for item in items:
    indent = "  " * item['indent']
    print(f"  {indent}[{item['type']}] {item['label']} -> {item.get('link_to','')}")

frappe.destroy()
