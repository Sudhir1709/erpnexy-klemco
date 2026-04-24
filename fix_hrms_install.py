import frappe
frappe.init(site='mysite.localhost', sites_path='/home/frappe/frappe-bench/sites')
frappe.connect()
frappe.set_user('Administrator')

# Fix stale DocType module references that block HRMS install
# These doctypes existed in frappe core but now belong to hrms
hrms_doctypes = [
    'Expense Claim Type',
    'Expense Claim',
    'Expense Claim Detail',
    'Expense Taxes and Charges',
    'Leave Type',
    'Leave Allocation',
    'Leave Application',
    'Attendance',
    'Salary Slip',
    'Salary Component',
    'Payroll Entry',
    'Job Opening',
    'Job Applicant',
]

for dt in hrms_doctypes:
    current = frappe.db.get_value('DocType', dt, ['module', 'app'], as_dict=True)
    if current:
        print(f"Found {dt}: module={current.module}, app={current.app}")
        if current.module in ('Core', 'Frappe') or current.app == 'frappe':
            frappe.db.set_value('DocType', dt, 'module', 'HR')
            print(f"  -> Fixed module to HR")
    else:
        print(f"NOT FOUND: {dt}")

frappe.db.commit()
print("\nDone fixing module references.")
frappe.destroy()
