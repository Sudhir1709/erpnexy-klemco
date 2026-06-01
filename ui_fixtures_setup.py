"""Create UI fixtures for interactive Playwright checks; write names to ui_fixtures.json."""
import frappe, json
frappe.init(site="mysite.localhost", sites_path="/home/frappe/frappe-bench/sites")
frappe.connect(); frappe.set_user("Administrator")
from frappe.utils import nowdate, add_days
from erpnext.selling.doctype.sales_order.sales_order import make_delivery_note
from klemco_cs.customer_service.doctype.km_order.km_order import make_km_order

ITEM = "SKU007"; WH = "Finished Goods - KID"
COMPANY = frappe.defaults.get_global_default("company") or frappe.db.get_value("Company", {}, "name")
HSN = frappe.db.get_value("GST HSN Code", {}, "name")
if HSN and not frappe.db.get_value("Item", ITEM, "gst_hsn_code"):
    frappe.db.set_value("Item", ITEM, "gst_hsn_code", HSN)
custs = frappe.get_all("Customer", filters={"disabled": 0}, pluck="name")
custA, custB = custs[0], custs[1] if len(custs) > 1 else custs[0]
cleanup = []
fx = {}

# 1) Deviation SO (RC customer + discount), draft — for Approve button + banner
origA = frappe.db.get_value("Customer", custA, "custom_klemco_customer_type")
frappe.db.set_value("Customer", custA, "custom_klemco_customer_type", "RC (Rate Contract)")
dev = frappe.get_doc({"doctype": "Sales Order", "customer": custA, "company": COMPANY,
                      "transaction_date": nowdate(), "delivery_date": add_days(nowdate(), 8),
                      "items": [{"item_code": ITEM, "qty": 1, "rate": 500, "discount_percentage": 5, "warehouse": WH, "delivery_date": add_days(nowdate(), 8)}]})
dev.insert(); cleanup.append(["Sales Order", dev.name]); fx["dev_so"] = dev.name
frappe.db.set_value("Customer", custA, "custom_klemco_customer_type", origA)  # restore; flag already saved

# 2) Happy SO (+instructions) -> Delivery Note (submitted) for Challan print
happy = frappe.get_doc({"doctype": "Sales Order", "customer": custB, "company": COMPANY,
                        "transaction_date": nowdate(), "delivery_date": add_days(nowdate(), 7),
                        "custom_delivery_instructions": "Unload by forklift; call site manager before arrival",
                        "items": [{"item_code": ITEM, "qty": 2, "rate": 500, "warehouse": WH, "delivery_date": add_days(nowdate(), 7)}]})
happy.insert(); happy.submit(); cleanup.append(["Sales Order", happy.name]); fx["happy_so"] = happy.name
dn = make_delivery_note(happy.name); dn.insert(); dn.submit(); cleanup.append(["Delivery Note", dn.name]); fx["dn"] = dn.name

# 3) KM Order (draft) from the happy SO — for review grid
km = make_km_order(happy.name); km.naming_series = "KMPO-.YYYY.-"; km.insert(); cleanup.append(["KM Order", km.name]); fx["km"] = km.name

fx["cleanup"] = cleanup
frappe.db.commit()
with open("/home/frappe/frappe-bench/ui_fixtures.json", "w") as f:
    json.dump(fx, f)
print("FIXTURES", json.dumps(fx))
frappe.destroy()
