import frappe

def after_install():
    create_roles()
    frappe.db.commit()

def create_roles():
    for role in ['CS Executive', 'CS Manager', 'CS Supervisor']:
        if not frappe.db.exists('Role', role):
            frappe.get_doc({'doctype': 'Role', 'role_name': role}).insert(ignore_permissions=True)
            print(f'  Created role: {role}')
