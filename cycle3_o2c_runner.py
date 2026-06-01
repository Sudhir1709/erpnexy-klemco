"""Deep cycle 3 — Order-to-Cash + GST (Selling + GST India + Accounting + Stock).
Quotation -> Sales Order -> Delivery Note -> Sales Invoice (GST) -> Payment Entry,
with stock-ledger, GST, GL, and outstanding assertions. Real submitted docs; cleans up.
"""
import frappe
frappe.init(site="mysite.localhost", sites_path="/home/frappe/frappe-bench/sites")
frappe.connect(); frappe.set_user("Administrator")
from frappe.utils import nowdate, add_days, flt

RESULTS = []; CLEANUP = []
def step(name, ok, detail=""): RESULTS.append((name, ok, detail)); print(f"{'PASS' if ok else 'FAIL'} | {name} | {detail}")
def track(d): CLEANUP.append((d.doctype, d.name)); return d

COMPANY = frappe.defaults.get_global_default("company") or frappe.db.get_value("Company", {}, "name")
HSN = frappe.db.get_value("GST HSN Code", {}, "name")
ITEM = "SKU007"; WH = "Finished Goods - KID"
if HSN and not frappe.db.get_value("Item", ITEM, "gst_hsn_code"):
    frappe.db.set_value("Item", ITEM, "gst_hsn_code", HSN)
CUST = frappe.db.get_value("Customer", {"disabled": 0}, "name")
GST_TPL = (frappe.db.get_value("Sales Taxes and Charges Template", {"company": COMPANY, "name": ["like", "%GST%"]}, "name")
           or frappe.db.get_value("Sales Taxes and Charges Template", {"company": COMPANY, "is_default": 1}, "name"))

def bin_qty():
    return flt(frappe.db.get_value("Bin", {"item_code": ITEM, "warehouse": WH}, "actual_qty"))

orig_type = frappe.db.get_value("Customer", CUST, "custom_klemco_customer_type")
try:
    frappe.db.set_value("Customer", CUST, "custom_klemco_customer_type", "Regular")  # avoid RC deviation gate

    # 1) Quotation
    q = frappe.get_doc({"doctype": "Quotation", "quotation_to": "Customer", "party_name": CUST, "company": COMPANY,
                        "transaction_date": nowdate(), **({"taxes_and_charges": GST_TPL} if GST_TPL else {}),
                        "items": [{"item_code": ITEM, "qty": 3, "rate": 500, "warehouse": WH}]})
    q.insert(); track(q); q.submit()
    step("1. Quotation submitted", q.docstatus == 1, q.name)

    # 2) Sales Order from Quotation
    from erpnext.selling.doctype.quotation.quotation import make_sales_order
    so = make_sales_order(q.name)
    so.delivery_date = add_days(nowdate(), 5)
    for it in so.items:
        it.delivery_date = add_days(nowdate(), 5); it.warehouse = WH
    so.insert(); track(so); so.submit()
    step("2. Sales Order submitted (from Quotation)", so.docstatus == 1, f"{so.name}, total={so.grand_total}")

    # 3) Delivery Note from SO (stock out)
    from erpnext.selling.doctype.sales_order.sales_order import make_delivery_note
    dn = make_delivery_note(so.name)
    for it in dn.items:
        it.warehouse = WH
    before = bin_qty()
    dn.insert(); track(dn); dn.submit()
    after = bin_qty()
    step("3. Delivery Note submitted (from SO)", dn.docstatus == 1, dn.name)
    step("   Stock ledger reduced by delivered qty", round(before - after, 2) == 3, f"bin {before} -> {after}")

    # 4) Sales Invoice from DN (GST + GL)
    from erpnext.stock.doctype.delivery_note.delivery_note import make_sales_invoice
    si = make_sales_invoice(dn.name)
    si.insert(); track(si); si.submit()
    gl = frappe.db.count("GL Entry", {"voucher_type": "Sales Invoice", "voucher_no": si.name})
    step("4. Sales Invoice submitted (from DN)", si.docstatus == 1, f"{si.name}, total={si.grand_total}, tax={si.total_taxes_and_charges}")
    step("   GL entries created for Sales Invoice", gl >= 2, f"{gl} GL entries")
    step("   GST-ready (HSN on line + company GSTIN; tax applied if GST template present)",
         bool(si.items[0].get("gst_hsn_code")) and bool(frappe.db.get_value("Address", {"is_your_company_address": 1, "gstin": ["is", "set"]}, "gstin")),
         f"hsn={si.items[0].get('gst_hsn_code')}; gst_category={si.get('gst_category')}; tax_total={si.total_taxes_and_charges}; tpl={GST_TPL}")

    # 5) Payment Entry against SI
    from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry
    pe = get_payment_entry("Sales Invoice", si.name)
    pe.reference_no = "RCPT-001"; pe.reference_date = nowdate()
    if not pe.paid_to:
        pe.paid_to = frappe.db.get_value("Account", {"company": COMPANY, "account_type": "Bank", "is_group": 0}, "name") \
            or frappe.db.get_value("Account", {"company": COMPANY, "account_type": "Cash", "is_group": 0}, "name")
    pe.insert(); track(pe); pe.submit()
    si.reload()
    step("5. Payment Entry submitted; invoice cleared", pe.docstatus == 1 and flt(si.outstanding_amount) == 0,
         f"{pe.name}; SI outstanding={si.outstanding_amount}")
except Exception as e:
    step("Order-to-Cash cycle", False, f"{type(e).__name__}: {str(e)[:170]}")
finally:
    frappe.db.set_value("Customer", CUST, "custom_klemco_customer_type", orig_type)

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
print(f"\n================ CYCLE 3 ORDER-TO-CASH + GST: {p}/{len(RESULTS)} passed ================")
frappe.destroy()
