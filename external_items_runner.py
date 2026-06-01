"""External item — e-waybill JSON generation (creds-free path; the live NIC API needs GSP creds).
Builds a B2C invoice with transport details and tries generate_e_waybill_json, reporting the
exact outcome (JSON produced, or the precise master-data requirement)."""
import frappe
frappe.init(site="mysite.localhost", sites_path="/home/frappe/frappe-bench/sites")
frappe.connect(); frappe.set_user("Administrator")
from frappe.utils import nowdate, add_days

RESULTS = []; CLEANUP = []
def step(name, ok, detail=""): RESULTS.append((name, ok, detail)); print(f"{'PASS' if ok else 'FAIL'} | {name} | {detail}")
def track(d): CLEANUP.append((d.doctype, d.name)); return d
COMPANY = frappe.defaults.get_global_default("company") or frappe.db.get_value("Company", {}, "name")
HSN = frappe.db.get_value("GST HSN Code", {"name": ["not like", "99%"]}, "name")  # goods HSN (e-waybill is for goods)
ITEM = "SKU007"; WH = "Finished Goods - KID"
orig_hsn = frappe.db.get_value("Item", ITEM, "gst_hsn_code")
if HSN:
    frappe.db.set_value("Item", ITEM, "gst_hsn_code", HSN)
CUST = frappe.db.get_value("Customer", {"disabled": 0}, "name")
GST_TPL = frappe.db.get_value("Sales Taxes and Charges Template", {"company": COMPANY, "name": ["like", "%GST%"]}, "name")
COMPANY_ADDR = (frappe.db.get_value("Address", {"is_your_company_address": 1, "gstin": ["is", "set"]}, "name")
                or frappe.db.get_value("Address", {"is_your_company_address": 1}, "name"))
orig_type = frappe.db.get_value("Customer", CUST, "custom_klemco_customer_type")
orig_pin = frappe.db.get_value("Address", COMPANY_ADDR, "pincode") if COMPANY_ADDR else None
added_link = False
if COMPANY_ADDR:
    if not orig_pin:
        frappe.db.set_value("Address", COMPANY_ADDR, "pincode", "143001")  # company from-pincode
    # demo gap: company address has no Dynamic Link to the Company — e-waybill needs it
    if not frappe.db.exists("Dynamic Link", {"parent": COMPANY_ADDR, "link_doctype": "Company", "link_name": COMPANY}):
        ad = frappe.get_doc("Address", COMPANY_ADDR)
        ad.append("links", {"link_doctype": "Company", "link_name": COMPANY})
        ad.save(); added_link = True
addr_name = None
try:
    frappe.db.set_value("Customer", CUST, "custom_klemco_customer_type", "Regular")
    # ship-to address with pincode + state (B2C e-waybill needs to-pincode + distance)
    addr = frappe.get_doc({"doctype": "Address", "address_title": "EWB ShipTo", "address_type": "Shipping",
                           "address_line1": "Plot 1, MIDC", "city": "Pune", "state": "Maharashtra",
                           "pincode": "411001", "country": "India", "gst_state": "Maharashtra",
                           "links": [{"link_doctype": "Customer", "link_name": CUST}]})
    addr.insert(); track(addr); addr_name = addr.name

    si = frappe.get_doc({"doctype": "Sales Invoice", "customer": CUST, "company": COMPANY,
                         "posting_date": nowdate(), "due_date": add_days(nowdate(), 30),
                         "customer_address": addr.name, "shipping_address_name": addr.name,
                         **({"company_address": COMPANY_ADDR} if COMPANY_ADDR else {}),
                         **({"taxes_and_charges": GST_TPL} if GST_TPL else {}),
                         "items": [{"item_code": ITEM, "qty": 200, "rate": 500, "warehouse": WH}]})
    si.insert(); track(si); si.submit()
    step("Sales Invoice for e-waybill (>₹50k) submitted", si.docstatus == 1, f"{si.name}, total={si.grand_total}")

    from india_compliance.gst_india.utils.e_waybill import generate_e_waybill_json
    try:
        data = generate_e_waybill_json("Sales Invoice", si.name,
                                       values={"mode_of_transport": "Road", "vehicle_no": "PB01AB1234", "distance": 50})
        ok = bool(data) and "billLists" in data
        step("e-waybill JSON generated (creds-free)", ok, f"json_len={len(data) if data else 0}")
    except Exception as e:
        # not a defect — documents the exact master-data requirement for e-waybill
        step("e-waybill JSON generation requirement", False, f"needs: {type(e).__name__}: {str(e)[:160]}")
except Exception as e:
    step("e-waybill setup", False, f"{type(e).__name__}: {str(e)[:160]}")
finally:
    frappe.db.set_value("Customer", CUST, "custom_klemco_customer_type", orig_type)
    frappe.db.set_value("Item", ITEM, "gst_hsn_code", orig_hsn)
    if COMPANY_ADDR and not orig_pin:
        frappe.db.set_value("Address", COMPANY_ADDR, "pincode", None)
    if added_link:
        for dl in frappe.get_all("Dynamic Link", {"parent": COMPANY_ADDR, "link_doctype": "Company", "link_name": COMPANY}, pluck="name"):
            frappe.delete_doc("Dynamic Link", dl, force=True, ignore_permissions=True)

for dt, name in reversed(CLEANUP):
    if frappe.db.exists(dt, name):
        try:
            d = frappe.get_doc(dt, name)
            if getattr(d, "docstatus", 0) == 1: d.cancel()
            frappe.delete_doc(dt, name, force=True, ignore_permissions=True)
        except Exception as e:
            print("CLEANUP skip", dt, name, str(e)[:80])
frappe.db.commit()
print(f"\n================ EXTERNAL: e-waybill ================")
frappe.destroy()
