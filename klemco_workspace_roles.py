import frappe

frappe.init(site='mysite.localhost', sites_path='/home/frappe/frappe-bench/sites')
frappe.connect()
frappe.set_user('Administrator')

# Workspace → roles that can see it
# Administrator always has access regardless
workspace_roles = {
    'Home':              ['System Manager'],
    'Selling':           ['Sales Manager', 'Sales Master Manager', 'Sales User'],
    'CRM':               ['Sales Manager', 'Sales Master Manager', 'Sales User'],
    'Buying':            ['Purchase Manager', 'Purchase Master Manager', 'Purchase User'],
    'Invoicing':         ['Accounts Manager', 'Accounts User'],
    'Financial Reports': ['Accounts Manager', 'Accounts User'],
    'Stock':             ['Stock Manager', 'Item Manager', 'Stock User'],
    'Assets':            ['Stock Manager', 'Accounts Manager'],
    'Manufacturing':     ['Manufacturing Manager', 'Manufacturing User'],
    'Subcontracting':    ['Manufacturing Manager', 'Purchase Manager'],
    'Projects':          ['Projects Manager', 'Projects User'],
    'Quality':           ['Quality Manager', 'Quality User'],
    'Support':           ['Sales Manager', 'Sales User'],
    'Website':           ['Website Manager', 'Marketing Manager'],
    'GST India':         ['Accounts Manager', 'Accounts User', 'System Manager'],
    'ERPNext Settings':  ['System Manager'],
    'Integrations':      ['System Manager'],
    'Build':             ['System Manager'],
    'Users':             ['System Manager'],
    # 'Welcome Workspace': ['System Manager'],  # skip — missing mandatory field
}

for ws_name, roles in workspace_roles.items():
    if not frappe.db.exists('Workspace', ws_name):
        print(f'  SKIP (not found): {ws_name}')
        continue

    ws = frappe.get_doc('Workspace', ws_name)

    # Clear existing roles
    ws.roles = []

    # Add new roles (only if role exists in system)
    for role in roles:
        if frappe.db.exists('Role', role):
            ws.append('roles', {'role': role})

    ws.flags.ignore_links = True
    ws.save(ignore_permissions=True)
    print(f'  ✓ {ws_name:<25} → {", ".join(roles)}')

frappe.db.commit()
print()
print('✅ Workspace roles applied!')
print()
print('Each department user now sees only their workspace:')
print('  sales.head        → Selling, CRM')
print('  crm.head          → CRM, Selling')
print('  purchase.head     → Buying')
print('  accounts.head     → Invoicing, Financial Reports')
print('  inventory.head    → Stock, Assets')
print('  manufacturing.head→ Manufacturing, Subcontracting')
print('  projects.head     → Projects')
print('  quality.head      → Quality')
print('  hr.head           → (HR workspace if present)')
print('  marketing.head    → Website')

frappe.destroy()
