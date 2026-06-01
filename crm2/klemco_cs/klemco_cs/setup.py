import frappe

# Roles used across the CS CRM. CS Supervisor/Executive/Manager existed in v1.0; the
# v1.3 approval flows add Sales Head (RC deviation), KM Plant Head + Supply Chain Lead
# (KM item triple approval, BR-KM-02 / CR-18).
ROLES = [
    'CS Executive',
    'CS Manager',
    'CS Supervisor',
    'Sales Head',
    'KM Plant Head',
    'Supply Chain Lead',
]


def after_install():
    create_roles()
    from klemco_cs.customizations import apply_customizations
    apply_customizations()
    frappe.db.commit()


def create_roles():
    for role in ROLES:
        if not frappe.db.exists('Role', role):
            frappe.get_doc({'doctype': 'Role', 'role_name': role}).insert(ignore_permissions=True)
            print(f'  Created role: {role}')
