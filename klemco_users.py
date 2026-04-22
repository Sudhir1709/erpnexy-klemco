import frappe
from frappe.utils import today

frappe.init(site='mysite.localhost', sites_path='/home/frappe/frappe-bench/sites')
frappe.connect()
frappe.set_user('Administrator')

COMPANY = 'Klemco India'
DOMAIN = 'klemcoindia.com'

# Department → (full name, email prefix, roles)
departments = [
    {
        'dept':     'Sales',
        'name':     'Sales Head',
        'email':    'sales.head',
        'roles':    ['Sales Manager', 'Sales Master Manager', 'CRM Manager' if frappe.db.exists('Role','CRM Manager') else 'Sales Manager'],
        'extra_roles': ['Sales User', 'Stock User', 'Accounts User'],
    },
    {
        'dept':     'Purchase',
        'name':     'Purchase Head',
        'email':    'purchase.head',
        'roles':    ['Purchase Manager', 'Purchase Master Manager'],
        'extra_roles': ['Purchase User', 'Stock User', 'Accounts User'],
    },
    {
        'dept':     'Accounts',
        'name':     'Accounts Head',
        'email':    'accounts.head',
        'roles':    ['Accounts Manager'],
        'extra_roles': ['Accounts User', 'Sales User', 'Purchase User'],
    },
    {
        'dept':     'Inventory',
        'name':     'Inventory Head',
        'email':    'inventory.head',
        'roles':    ['Stock Manager', 'Item Manager'],
        'extra_roles': ['Stock User', 'Purchase User'],
    },
    {
        'dept':     'HR',
        'name':     'HR Head',
        'email':    'hr.head',
        'roles':    ['HR Manager'],
        'extra_roles': ['HR User', 'Leave Approver', 'Expense Approver'],
    },
    {
        'dept':     'Projects',
        'name':     'Projects Head',
        'email':    'projects.head',
        'roles':    ['Projects Manager'],
        'extra_roles': ['Projects User', 'Sales User', 'Stock User'],
    },
    {
        'dept':     'Manufacturing',
        'name':     'Manufacturing Head',
        'email':    'manufacturing.head',
        'roles':    ['Manufacturing Manager'],
        'extra_roles': ['Manufacturing User', 'Stock User', 'Item Manager'],
    },
    {
        'dept':     'Quality',
        'name':     'Quality Head',
        'email':    'quality.head',
        'roles':    ['Quality Manager'],
        'extra_roles': ['Quality User', 'Stock User'],
    },
    {
        'dept':     'CRM',
        'name':     'CRM Manager',
        'email':    'crm.head',
        'roles':    ['Sales Manager', 'Sales Master Manager'],
        'extra_roles': ['Sales User', 'Accounts User', 'Report Manager'],
    },
    {
        'dept':     'Marketing',
        'name':     'Marketing Head',
        'email':    'marketing.head',
        'roles':    ['Marketing Manager'],
        'extra_roles': ['Sales User', 'Website Manager'],
    },
]

PASSWORD = 'Klemco@2024'

print(f'Creating {len(departments)} department users...')
print(f'Password for all: {PASSWORD}')
print()

created = []
skipped = []

for d in departments:
    email = f"{d['email']}@{DOMAIN}"

    if frappe.db.exists('User', email):
        skipped.append(email)
        print(f'  SKIP (exists): {email}')
        continue

    # Deduplicate roles
    all_roles = list(dict.fromkeys(d['roles'] + d['extra_roles']))
    # Filter to only roles that actually exist
    valid_roles = [r for r in all_roles if frappe.db.exists('Role', r)]

    user = frappe.get_doc({
        'doctype':          'User',
        'first_name':       d['name'],
        'email':            email,
        'enabled':          1,
        'user_type':        'System User',
        'new_password':     PASSWORD,
        'send_welcome_email': 0,
        'department':       d['dept'],
        'roles': [{'role': r} for r in valid_roles],
    })
    user.insert(ignore_permissions=True)
    frappe.db.commit()

    created.append({'dept': d['dept'], 'email': email, 'roles': valid_roles})
    print(f"  ✓ {d['dept']:20s}  {email:40s}  roles: {', '.join(valid_roles)}")

frappe.db.commit()

print()
print('=' * 70)
print('KLEMCO INDIA — DEPARTMENT USER CREDENTIALS')
print('=' * 70)
print(f'{"Department":<20} {"Email":<40} {"Password"}')
print('-' * 70)
for u in created:
    print(f"{u['dept']:<20} {u['email']:<40} {PASSWORD}")
if skipped:
    print()
    print('Already existed (skipped):', skipped)
print('=' * 70)
print()
print(f'Total created: {len(created)}  |  Skipped: {len(skipped)}')

frappe.destroy()
