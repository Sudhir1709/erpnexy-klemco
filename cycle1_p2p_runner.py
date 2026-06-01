"""Deep cycle 1 — Procure-to-Pay (Buying + Stock + Quality + Accounting).
MR -> PO -> Purchase Receipt (+ Quality Inspection) -> Purchase Invoice -> Payment Entry,
with stock-ledger and GL assertions. Creates real submitted docs, then cleans up.
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
ITEM = "SKU007"; WH = "Stores - KID"
if not frappe.db.exists("Warehouse", WH):
    WH = frappe.db.get_value("Warehouse", {"company": COMPANY, "is_group": 0}, "name")
if HSN and not frappe.db.get_value("Item", ITEM, "gst_hsn_code"):
    frappe.db.set_value("Item", ITEM, "gst_hsn_code", HSN)

def bin_qty():
    return flt(frappe.db.get_value("Bin", {"item_code": ITEM, "warehouse": WH}, "actual_qty"))

orig_insp = frappe.db.get_value("Item", ITEM, "inspection_required_before_purchase")
try:
    # supplier (unregistered → no GSTIN needed)
    sg = frappe.db.get_value("Supplier Group", {"is_group": 0}, "name")
    sup = track(frappe.get_doc({"doctype": "Supplier", "supplier_name": "P2P Smoke Supplier",
                                "supplier_group": sg, "gst_category": "Unregistered"}).insert())

    # 1) Material Request
    mr = frappe.get_doc({"doctype": "Material Request", "material_request_type": "Purchase", "company": COMPANY,
                         "transaction_date": nowdate(),
                         "items": [{"item_code": ITEM, "qty": 10, "schedule_date": add_days(nowdate(), 5), "warehouse": WH}]})
    mr.insert(); track(mr); mr.submit()
    step("1. Material Request submitted", mr.docstatus == 1, mr.name)

    # 2) Purchase Order from MR
    from erpnext.stock.doctype.material_request.material_request import make_purchase_order
    po = make_purchase_order(mr.name)
    po.supplier = sup.name
    for it in po.items:
        it.rate = 100; it.warehouse = WH; it.schedule_date = add_days(nowdate(), 5)
    po.insert(); track(po); po.submit()
    step("2. Purchase Order submitted (from MR)", po.docstatus == 1, f"{po.name}, grand_total={po.grand_total}")

    # 3) Quality Inspection on receipt + Purchase Receipt
    frappe.db.set_value("Item", ITEM, "inspection_required_before_purchase", 1)
    from erpnext.buying.doctype.purchase_order.purchase_order import make_purchase_receipt
    pr = make_purchase_receipt(po.name)
    for it in pr.items:
        it.warehouse = WH
    pr.insert(); track(pr)
    qi = frappe.get_doc({"doctype": "Quality Inspection", "inspection_type": "Incoming",
                         "reference_type": "Purchase Receipt", "reference_name": pr.name,
                         "item_code": ITEM, "sample_size": 1, "inspected_by": "Administrator",
                         "status": "Accepted"})
    qi.insert(); track(qi); qi.submit()
    pr.reload()  # QI submit back-links to the PR item
    if not pr.items[0].get("quality_inspection"):
        for it in pr.items:
            it.quality_inspection = qi.name
        pr.save(); pr.reload()
    before = bin_qty()
    pr.submit()
    after = bin_qty()
    step("3. Purchase Receipt + Quality Inspection submitted", pr.docstatus == 1 and qi.docstatus == 1, f"{pr.name}, QI={qi.name}")
    step("   Stock ledger increased by received qty", round(after - before, 2) == 10, f"bin {before} -> {after}")

    # 4) Purchase Invoice from PR
    from erpnext.stock.doctype.purchase_receipt.purchase_receipt import make_purchase_invoice
    pi = make_purchase_invoice(pr.name)
    pi.bill_no = "SUP-BILL-001"; pi.bill_date = nowdate()
    pi.insert(); track(pi); pi.submit()
    gl = frappe.db.count("GL Entry", {"voucher_type": "Purchase Invoice", "voucher_no": pi.name})
    step("4. Purchase Invoice submitted (from PR)", pi.docstatus == 1, f"{pi.name}, outstanding={pi.outstanding_amount}")
    step("   GL entries created for Purchase Invoice", gl >= 2, f"{gl} GL entries")

    # 5) Payment Entry against PI
    from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry
    pe = get_payment_entry("Purchase Invoice", pi.name)
    pe.reference_no = "PAY-001"; pe.reference_date = nowdate()
    if not pe.paid_from:
        pe.paid_from = frappe.db.get_value("Account", {"company": COMPANY, "account_type": "Bank", "is_group": 0}, "name") \
            or frappe.db.get_value("Account", {"company": COMPANY, "account_type": "Cash", "is_group": 0}, "name")
    pe.insert(); track(pe); pe.submit()
    pi.reload()
    step("5. Payment Entry submitted; invoice cleared", pe.docstatus == 1 and flt(pi.outstanding_amount) == 0,
         f"{pe.name}; PI outstanding={pi.outstanding_amount}")
except Exception as e:
    step("Procure-to-Pay cycle", False, f"{type(e).__name__}: {str(e)[:170]}")
finally:
    frappe.db.set_value("Item", ITEM, "inspection_required_before_purchase", orig_insp or 0)

# cleanup (reverse: cancel submitted, delete)
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
print(f"\n================ CYCLE 1 PROCURE-TO-PAY: {p}/{len(RESULTS)} passed ================")
frappe.destroy()
