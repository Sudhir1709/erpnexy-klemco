import frappe
frappe.init(site='mysite.localhost', sites_path='/home/frappe/frappe-bench/sites')
frappe.connect()
frappe.set_user('Administrator')

# Run HRMS setup fixtures (what after_install would have done)
from hrms.setup import make_fixtures
try:
    make_fixtures()
    frappe.db.commit()
    print("HRMS fixtures created successfully.")
except Exception as e:
    frappe.db.rollback()
    print(f"Fixtures error (non-fatal): {e}")

# Verify key doctypes
key_dts = ['Employee', 'Leave Application', 'Attendance', 'Salary Slip',
           'Payroll Entry', 'Job Opening', 'Job Applicant', 'Expense Claim',
           'Leave Type', 'Leave Allocation', 'Salary Component']
print("\nKey HRMS doctypes:")
for dt in key_dts:
    exists = frappe.db.exists('DocType', dt)
    print(f"  {'✓' if exists else '✗'} {dt}")

frappe.destroy()
