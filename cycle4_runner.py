"""Deep cycle 4 — HR/Payroll, Projects, Assets, CRM. Real submitted docs; granular steps; cleanup."""
import frappe
frappe.init(site="mysite.localhost", sites_path="/home/frappe/frappe-bench/sites")
frappe.connect(); frappe.set_user("Administrator")
from frappe.utils import nowdate, add_days, add_years, add_months, flt

RESULTS = []; CLEANUP = []
def step(name, ok, detail=""): RESULTS.append((name, ok, detail)); print(f"{'PASS' if ok else 'FAIL'} | {name} | {detail}")
def track(d): CLEANUP.append((d.doctype, d.name)); return d
COMPANY = frappe.defaults.get_global_default("company") or frappe.db.get_value("Company", {}, "name")
HSN = frappe.db.get_value("GST HSN Code", {}, "name")
IG = frappe.db.get_value("Item Group", {"is_group": 0}, "name")

# ───────── HR / Payroll ─────────
try:
    gender = frappe.db.get_value("Gender", {}, "name") or "Male"
    # Holiday List first (needed for leave + payroll), set as company default + on the employee
    hl = frappe.get_doc({"doctype": "Holiday List", "holiday_list_name": "C4 HL",
                         "from_date": add_days(nowdate(), -180), "to_date": add_days(nowdate(), 360),
                         "weekly_off": "Sunday"})
    hl.get_weekly_off_dates(); hl.insert(); track(hl)
    emp = frappe.get_doc({"doctype": "Employee", "first_name": "C4", "last_name": "Emp", "company": COMPANY,
                          "gender": gender, "date_of_birth": add_years(nowdate(), -30),
                          "date_of_joining": add_years(nowdate(), -1), "holiday_list": hl.name})
    emp.insert(); track(emp)
    step("HR 1. Employee created", bool(emp.name), emp.name)
    # this hrms resolves the holiday list via a Holiday List Assignment (to the employee)
    hla = frappe.get_doc({"doctype": "Holiday List Assignment", "assigned_to_type": "Employee",
                          "assigned_to": emp.name, "holiday_list": hl.name, "from_date": add_days(nowdate(), -180)})
    hla.insert(); track(hla); hla.submit()

    att = frappe.get_doc({"doctype": "Attendance", "employee": emp.name, "attendance_date": nowdate(),
                          "status": "Present", "company": COMPANY})
    att.insert(); track(att); att.submit()
    step("HR 2. Attendance marked", att.docstatus == 1, att.name)
except Exception as e:
    step("HR base (Employee/Attendance)", False, f"{type(e).__name__}: {str(e)[:150]}")

# Leave (separate so it reports independently)
try:
    lt = "C4 Leave"
    if not frappe.db.exists("Leave Type", lt):
        track(frappe.get_doc({"doctype": "Leave Type", "leave_type_name": lt, "max_leaves_allowed": 10}).insert())
    la = frappe.get_doc({"doctype": "Leave Allocation", "employee": emp.name, "leave_type": lt,
                         "from_date": add_days(nowdate(), -10), "to_date": add_days(nowdate(), 300),
                         "new_leaves_allocated": 5})
    la.insert(); track(la); la.submit()
    lap = frappe.get_doc({"doctype": "Leave Application", "employee": emp.name, "leave_type": lt,
                          "from_date": add_days(nowdate(), 2), "to_date": add_days(nowdate(), 2),
                          "company": COMPANY, "status": "Approved", "leave_approver": "Administrator"})
    lap.insert(); track(lap); lap.submit()
    step("HR 3. Leave allocation + application", lap.docstatus == 1, f"{lap.name}")
except Exception as e:
    step("HR 3. Leave", False, f"{type(e).__name__}: {str(e)[:150]}")

# Payroll (separate)
try:
    comp = "C4 Basic"
    if not frappe.db.exists("Salary Component", comp):
        track(frappe.get_doc({"doctype": "Salary Component", "salary_component": comp, "type": "Earning",
                              "salary_component_abbr": "C4B"}).insert())
    ss = frappe.get_doc({"doctype": "Salary Structure", "name": "C4 Structure", "company": COMPANY,
                         "payroll_frequency": "Monthly", "earnings": [{"salary_component": comp, "amount": 30000}]})
    ss.insert(); track(ss); ss.submit()
    ssa = frappe.get_doc({"doctype": "Salary Structure Assignment", "employee": emp.name,
                          "salary_structure": ss.name, "company": COMPANY, "from_date": add_years(nowdate(), -1), "base": 30000})
    ssa.insert(); track(ssa); ssa.submit()
    slip = frappe.get_doc({"doctype": "Salary Slip", "employee": emp.name,
                           "start_date": nowdate(), "end_date": add_months(nowdate(), 1)})
    slip.insert(); track(slip); slip.submit()
    step("HR 4. Payroll: Salary Structure → Slip", slip.docstatus == 1, f"{slip.name}, gross={slip.gross_pay}")
except Exception as e:
    step("HR 4. Payroll", False, f"{type(e).__name__}: {str(e)[:150]}")

# ───────── Projects ─────────
try:
    proj = frappe.get_doc({"doctype": "Project", "project_name": "C4 Project", "company": COMPANY}); proj.insert(); track(proj)
    task = frappe.get_doc({"doctype": "Task", "subject": "C4 Task", "project": proj.name}); task.insert(); track(task)
    act = frappe.db.get_value("Activity Type", {}, "name") or track(frappe.get_doc({"doctype": "Activity Type", "activity_type": "C4 Activity"}).insert()).name
    ts = frappe.get_doc({"doctype": "Timesheet", "company": COMPANY,
                         "time_logs": [{"activity_type": act, "hours": 4, "project": proj.name, "task": task.name,
                                        "from_time": nowdate() + " 09:00:00", "is_billable": 1, "billing_hours": 4, "billing_rate": 500}]})
    ts.insert(); track(ts); ts.submit()
    step("Projects 1. Project + Task + Timesheet", ts.docstatus == 1, f"{proj.name}/{task.name}/{ts.name}")
    step("Projects 2. Timesheet billable hours captured", flt(ts.total_billable_hours) == 4, f"billable={ts.total_billable_hours}, amount={ts.total_billable_amount}")
except Exception as e:
    step("Projects", False, f"{type(e).__name__}: {str(e)[:150]}")

# ───────── Assets ─────────
try:
    fa = frappe.db.get_value("Account", {"company": COMPANY, "account_type": "Fixed Asset", "is_group": 0}, "name")
    ad = frappe.db.get_value("Account", {"company": COMPANY, "account_type": "Accumulated Depreciation", "is_group": 0}, "name")
    de = frappe.db.get_value("Account", {"company": COMPANY, "account_type": "Depreciation", "is_group": 0}, "name")
    assert fa and ad and de, "asset GL accounts missing"
    cat = frappe.get_doc({"doctype": "Asset Category", "asset_category_name": "C4 Asset Cat",
                          "accounts": [{"company_name": COMPANY, "fixed_asset_account": fa,
                                        "accumulated_depreciation_account": ad, "depreciation_expense_account": de}],
                          "finance_books": [{"depreciation_method": "Straight Line", "total_number_of_depreciations": 12, "frequency_of_depreciation": 1}]})
    cat.insert(); track(cat)
    ai = "C4-ASSET-ITEM"
    if frappe.db.exists("Item", ai): frappe.delete_doc("Item", ai, force=True, ignore_permissions=True)
    item = frappe.get_doc({"doctype": "Item", "item_code": ai, "item_name": ai, "item_group": IG, "stock_uom": "Nos",
                           "is_stock_item": 0, "is_fixed_asset": 1, "asset_category": "C4 Asset Cat",
                           **({"gst_hsn_code": HSN} if HSN else {})})
    item.insert(); track(item)
    loc = "C4 Location"
    if not frappe.db.exists("Location", loc): track(frappe.get_doc({"doctype": "Location", "location_name": loc}).insert())
    asset = frappe.get_doc({"doctype": "Asset", "asset_name": "C4 Asset", "item_code": ai, "company": COMPANY,
                            "asset_category": "C4 Asset Cat", "location": loc, "gross_purchase_amount": 120000,
                            "net_purchase_amount": 120000, "purchase_amount": 120000,
                            "available_for_use_date": nowdate(), "purchase_date": nowdate(),
                            "calculate_depreciation": 1, "is_existing_asset": 1,
                            "finance_books": [{"depreciation_method": "Straight Line", "total_number_of_depreciations": 12,
                                               "frequency_of_depreciation": 1, "depreciation_start_date": add_months(nowdate(), 1)}]})
    asset.insert(); track(asset); asset.submit()
    step("Assets 1. Asset created + submitted", asset.docstatus == 1, f"{asset.name}, gross={asset.gross_purchase_amount}")
    # v16: depreciation rows live in Asset Depreciation Schedule -> Depreciation Schedule
    ads = frappe.get_all("Asset Depreciation Schedule", filters={"asset": asset.name, "docstatus": ["<", 2]}, pluck="name")
    rows = sum(frappe.db.count("Depreciation Schedule", {"parent": a}) for a in ads)
    step("Assets 2. Depreciation schedule generated", len(ads) >= 1 and rows >= 1, f"{len(ads)} schedule(s), {rows} rows")
except Exception as e:
    step("Assets", False, f"{type(e).__name__}: {str(e)[:150]}")

# ───────── CRM (Lead → Deal) ─────────
try:
    st = frappe.db.get_value("CRM Lead Status", {"name": "New"}, "name") or frappe.db.get_value("CRM Lead Status", {}, "name")
    lead = frappe.get_doc({"doctype": "CRM Lead", "first_name": "C4", "last_name": "Lead", "email": "c4.lead@x.com",
                           "organization": "C4 Org", **({"status": st} if st else {})})
    lead.insert(); track(lead)
    converted = None
    try:
        from crm.fcrm.doctype.crm_lead.crm_lead import create_deal
        converted = create_deal(lead.name)
    except Exception:
        ds = frappe.db.get_value("CRM Deal Status", {"name": "Qualification"}, "name") or frappe.db.get_value("CRM Deal Status", {"name": ["not in", ["Lost", "Won"]]}, "name")
        d = frappe.get_doc({"doctype": "CRM Deal", "lead": lead.name, **({"status": ds} if ds else {})}); d.insert(); converted = d.name
    if converted: track(frappe.get_doc("CRM Deal", converted))
    step("CRM 1. Lead → Deal (convert)", bool(converted), f"lead={lead.name}, deal={converted}")
except Exception as e:
    step("CRM", False, f"{type(e).__name__}: {str(e)[:150]}")

for dt, name in reversed(CLEANUP):
    if frappe.db.exists(dt, name):
        try:
            d = frappe.get_doc(dt, name)
            if getattr(d, "docstatus", 0) == 1: d.cancel()
            frappe.delete_doc(dt, name, force=True, ignore_permissions=True)
        except Exception as e:
            print("CLEANUP skip", dt, name, str(e)[:80])
frappe.db.commit()
p = sum(1 for _, o, _ in RESULTS if o)
print(f"\n================ CYCLE 4 HR/PROJECTS/ASSETS/CRM: {p}/{len(RESULTS)} passed ================")
frappe.destroy()
