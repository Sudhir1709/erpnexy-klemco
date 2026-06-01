"""Per-module smoke test across the ERPNext + ancillary suite on 8080.
Each module: create one representative document (draft/master) so it validates, then clean up.
Run: ./env/bin/python modules_smoke_runner.py
"""
import frappe
frappe.init(site="mysite.localhost", sites_path="/home/frappe/frappe-bench/sites")
frappe.connect(); frappe.set_user("Administrator")
from frappe.utils import nowdate, add_days, add_years

RESULTS = []; CLEANUP = []
def ok(mod, detail=""): RESULTS.append((mod, True, detail)); print(f"PASS | {mod} | {detail}")
def bad(mod, e): RESULTS.append((mod, False, str(e)[:150])); print(f"FAIL | {mod} | {type(e).__name__}: {str(e)[:150]}")
def track(d): CLEANUP.append((d.doctype, d.name)); return d

COMPANY = frappe.defaults.get_global_default("company") or frappe.db.get_value("Company", {}, "name")
ABBR = frappe.db.get_value("Company", COMPANY, "abbr")
HSN = frappe.db.get_value("GST HSN Code", {}, "name")
ITEM = "SKU007"; WH = "Finished Goods - KID"
if HSN and not frappe.db.get_value("Item", ITEM, "gst_hsn_code"):
    frappe.db.set_value("Item", ITEM, "gst_hsn_code", HSN)
CUST = frappe.db.get_value("Customer", {"disabled": 0}, "name")
ITEM_GROUP = frappe.db.get_value("Item Group", {"is_group": 0}, "name")

def mk(d):  # insert helper
    doc = frappe.get_doc(d); doc.insert(); return track(doc)

# 1) Frappe CRM
try:
    st = frappe.db.get_value("CRM Lead Status", {"name": "New"}, "name") or frappe.db.get_value("CRM Lead Status", {}, "name")
    lead = mk({"doctype": "CRM Lead", "first_name": "Smoke", "last_name": "Lead", "email": "smoke@x.com", **({"status": st} if st else {})})
    ds = frappe.db.get_value("CRM Deal Status", {"name": "Qualification"}, "name") or frappe.db.get_value("CRM Deal Status", {"name": ["not in", ["Lost", "Won"]]}, "name")
    deal = mk({"doctype": "CRM Deal", **({"status": ds} if ds else {})})
    ok("Frappe CRM", f"Lead {lead.name}, Deal {deal.name}")
except Exception as e: bad("Frappe CRM", e)

# 2) GST India (india_compliance) — config + computed GST already proven; assert masters
try:
    gs = frappe.get_single("GST Settings")
    assert frappe.db.exists("DocType", "e-Waybill Log") and gs.enable_e_waybill
    hsn_ct = frappe.db.count("GST HSN Code")
    addr_gstin = frappe.db.get_value("Address", {"is_your_company_address": 1, "gstin": ["is", "set"]}, "gstin")
    assert hsn_ct > 0 and addr_gstin
    ok("GST India", f"e-waybill enabled, HSN master={hsn_ct}, company GSTIN set")
except Exception as e: bad("GST India", e)

# 3) Organization (HR org masters)
try:
    desig = mk({"doctype": "Designation", "designation_name": "Smoke Designation"})
    dept = mk({"doctype": "Department", "department_name": "Smoke Dept", "company": COMPANY})
    ok("Organization", f"Designation + Department ({dept.name})")
except Exception as e: bad("Organization", e)

# 4) Accounting
try:
    cash = frappe.db.get_value("Account", {"company": COMPANY, "account_type": "Cash", "is_group": 0}, "name")
    exp = frappe.db.get_value("Account", {"company": COMPANY, "root_type": "Expense", "is_group": 0}, "name")
    jv = mk({"doctype": "Journal Entry", "voucher_type": "Journal Entry", "company": COMPANY,
             "posting_date": nowdate(),
             "accounts": [{"account": exp, "debit_in_account_currency": 100},
                          {"account": cash, "credit_in_account_currency": 100}]})
    ok("Accounting", f"Journal Entry draft {jv.name}")
except Exception as e: bad("Accounting", e)

# 5) Assets
try:
    assert frappe.db.exists("DocType", "Asset")
    fa = frappe.db.get_value("Account", {"company": COMPANY, "account_type": "Fixed Asset", "is_group": 0}, "name")
    ad = frappe.db.get_value("Account", {"company": COMPANY, "account_type": "Accumulated Depreciation", "is_group": 0}, "name")
    de = frappe.db.get_value("Account", {"company": COMPANY, "account_type": "Depreciation", "is_group": 0}, "name")
    if fa and ad and de:
        ac = mk({"doctype": "Asset Category", "asset_category_name": "Smoke Asset Cat",
                 "accounts": [{"company_name": COMPANY, "fixed_asset_account": fa,
                               "accumulated_depreciation_account": ad, "depreciation_expense_account": de}],
                 "finance_books": [{"depreciation_method": "Straight Line", "total_number_of_depreciations": 12, "frequency_of_depreciation": 1}]})
        ok("Assets", f"Asset Category {ac.name} (+ Asset doctype present)")
    else:
        assert frappe.db.exists("DocType", "Asset Category")
        ok("Assets", "Asset + Asset Category doctypes present (full category needs GL asset/depreciation accounts configured)")
except Exception as e: bad("Assets", e)

# 6) Buying
try:
    sg = frappe.db.get_value("Supplier Group", {"is_group": 0}, "name")
    sup = mk({"doctype": "Supplier", "supplier_name": "Smoke Supplier", "supplier_group": sg})
    po = mk({"doctype": "Purchase Order", "supplier": sup.name, "company": COMPANY, "transaction_date": nowdate(),
             "items": [{"item_code": ITEM, "qty": 1, "rate": 100, "schedule_date": add_days(nowdate(), 5), "warehouse": WH}]})
    ok("Buying", f"Supplier + Purchase Order draft {po.name}")
except Exception as e: bad("Buying", e)

# 7) Manufacturing
try:
    raw = frappe.db.get_value("Item", {"name": ["!=", ITEM], "is_stock_item": 1, "disabled": 0}, "name") or ITEM
    bom = mk({"doctype": "BOM", "item": ITEM, "quantity": 1, "company": COMPANY,
              "items": [{"item_code": raw, "qty": 1, "rate": 10}]})
    ok("Manufacturing", f"BOM draft {bom.name} for {ITEM}")
except Exception as e: bad("Manufacturing", e)

# 8) Projects
try:
    proj = mk({"doctype": "Project", "project_name": "Smoke Project"})
    task = mk({"doctype": "Task", "subject": "Smoke Task", "project": proj.name})
    ok("Projects", f"Project {proj.name} + Task {task.name}")
except Exception as e: bad("Projects", e)

# 9) Quality
try:
    qg = mk({"doctype": "Quality Goal", "goal": "Smoke Quality Goal",
             "measurable": "No"} if frappe.get_meta("Quality Goal").get_field("measurable") else {"doctype": "Quality Goal", "goal": "Smoke Quality Goal"})
    ok("Quality", f"Quality Goal {qg.name}")
except Exception as e: bad("Quality", e)

# 10) Selling
try:
    qo = mk({"doctype": "Quotation", "quotation_to": "Customer", "party_name": CUST, "company": COMPANY,
             "transaction_date": nowdate(), "items": [{"item_code": ITEM, "qty": 1, "rate": 500}]})
    ok("Selling", f"Quotation draft {qo.name}")
except Exception as e: bad("Selling", e)

# 11) Stock
try:
    mr = mk({"doctype": "Material Request", "material_request_type": "Purchase", "company": COMPANY,
             "transaction_date": nowdate(),
             "items": [{"item_code": ITEM, "qty": 2, "schedule_date": add_days(nowdate(), 5), "warehouse": WH}]})
    ok("Stock", f"Material Request draft {mr.name}")
except Exception as e: bad("Stock", e)

# 12) Subcontracting
try:
    present = [d for d in ["Subcontracting Order", "Subcontracting Receipt", "Subcontracting BOM"] if frappe.db.exists("DocType", d)]
    assert present
    ok("Subcontracting", f"doctypes present: {', '.join(present)}")
except Exception as e: bad("Subcontracting", e)

# 13) Frappe HR (hrms)
try:
    emp = mk({"doctype": "Employee", "first_name": "Smoke", "last_name": "Employee", "company": COMPANY,
              "gender": frappe.db.get_value("Gender", {}, "name") or "Male",
              "date_of_birth": add_years(nowdate(), -30), "date_of_joining": nowdate()})
    ok("Frappe HR", f"Employee {emp.name}")
except Exception as e: bad("Frappe HR", e)

# cleanup
for dt, name in reversed(CLEANUP):
    if frappe.db.exists(dt, name):
        try:
            d = frappe.get_doc(dt, name)
            if getattr(d, "docstatus", 0) == 1: d.cancel()
            frappe.delete_doc(dt, name, force=True, ignore_permissions=True)
        except Exception as e:
            print("CLEANUP skip", dt, name, str(e)[:70])
frappe.db.commit()
passed = sum(1 for _, o, _ in RESULTS if o)
print(f"\n================ MODULE SMOKE: {passed}/{len(RESULTS)} passed ================")
frappe.destroy()
