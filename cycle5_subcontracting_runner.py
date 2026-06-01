"""Deep cycle 5 — Subcontracting supply -> receipt (v16, PO-driven).
PO (subcontracted) -> Subcontracting Order -> raw supplied to subcontractor -> Subcontracting
Receipt (FG in, raw consumed). Real submitted docs + stock assertions; cleans up.
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
IG = frappe.db.get_value("Item Group", {"is_group": 0}, "name")
FGW = "Finished Goods - KID"; SUPW = "Work In Progress - KID"
for w in [FGW, SUPW]:
    if not frappe.db.exists("Warehouse", w):
        FGW = SUPW = frappe.db.get_value("Warehouse", {"company": COMPANY, "is_group": 0}, "name"); break

def mk_item(code, **extra):
    if frappe.db.exists("Item", code): frappe.delete_doc("Item", code, force=True, ignore_permissions=True)
    d = {"doctype": "Item", "item_code": code, "item_name": code, "item_group": IG, "stock_uom": "Nos", "is_stock_item": 1}
    if HSN: d["gst_hsn_code"] = HSN
    d.update(extra)
    return track(frappe.get_doc(d).insert())

def receipt(item, qty, wh):
    se = frappe.get_doc({"doctype": "Stock Entry", "stock_entry_type": "Material Receipt", "company": COMPANY,
                         "items": [{"item_code": item, "qty": qty, "t_warehouse": wh, "basic_rate": 50}]})
    se.taxes = []; se.insert(); track(se); se.submit(); return se

def bin_qty(item, wh): return flt(frappe.db.get_value("Bin", {"item_code": item, "warehouse": wh}, "actual_qty"))

try:
    fg = mk_item("C5-FG", is_sales_item=1, is_sub_contracted_item=1)
    raw = mk_item("C5-RAW", is_purchase_item=1)
    svc = mk_item("C5-SERVICE", is_stock_item=0, is_purchase_item=1)
    # default BOM (FG <- RAW) required by subcontracting
    dbom = frappe.get_doc({"doctype": "BOM", "item": "C5-FG", "quantity": 1, "company": COMPANY,
                           "is_active": 1, "is_default": 1, "with_operations": 0,
                           "items": [{"item_code": "C5-RAW", "qty": 2, "rate": 50}]})
    dbom.insert(); track(dbom); dbom.submit()
    sbom = frappe.get_doc({"doctype": "Subcontracting BOM", "finished_good": "C5-FG", "finished_good_qty": 1,
                           "service_item": "C5-SERVICE", "service_item_qty": 1,
                           "items": [{"item_code": "C5-RAW", "qty": 2}]})
    sbom.insert(); track(sbom)
    sg = frappe.db.get_value("Supplier Group", {"is_group": 0}, "name")
    sup = track(frappe.get_doc({"doctype": "Supplier", "supplier_name": "C5 Subcontractor",
                                "supplier_group": sg, "gst_category": "Unregistered"}).insert())
    # raw available at the subcontractor warehouse
    receipt("C5-RAW", 20, SUPW)

    # 1) Subcontracting PO (service item + fg_item)
    po = frappe.get_doc({"doctype": "Purchase Order", "supplier": sup.name, "company": COMPANY,
                         "is_subcontracted": 1, "transaction_date": nowdate(), "supplier_warehouse": SUPW,
                         "items": [{"item_code": "C5-SERVICE", "qty": 5, "rate": 30, "schedule_date": add_days(nowdate(), 5),
                                    "fg_item": "C5-FG", "fg_item_qty": 5, "warehouse": FGW}]})
    po.insert(); track(po); po.submit()
    step("1. Subcontracting PO submitted", po.docstatus == 1, f"{po.name}")

    # 2) Subcontracting Order from PO
    from erpnext.buying.doctype.purchase_order.purchase_order import make_subcontracting_order
    sco = make_subcontracting_order(po.name)
    sco.supplier_warehouse = SUPW
    for it in sco.items:
        it.warehouse = FGW
    sco.insert(); track(sco); sco.submit()
    step("2. Subcontracting Order submitted (from PO)", sco.docstatus == 1, f"{sco.name}; supplied_items={len(sco.supplied_items)}")

    # 3) Subcontracting Receipt (FG in, raw consumed)
    from erpnext.subcontracting.doctype.subcontracting_order.subcontracting_order import make_subcontracting_receipt
    fg_before = bin_qty("C5-FG", FGW); raw_before = bin_qty("C5-RAW", SUPW)
    scr = make_subcontracting_receipt(sco.name)
    scr.taxes = []  # india_compliance hook reads .taxes
    for it in scr.items:
        it.warehouse = FGW
    scr.insert(); track(scr); scr.submit()
    fg_after = bin_qty("C5-FG", FGW); raw_after = bin_qty("C5-RAW", SUPW)
    step("3. Subcontracting Receipt submitted", scr.docstatus == 1, f"{scr.name}")
    step("   FG received +5 and raw consumed at subcontractor", round(fg_after - fg_before, 2) == 5 and raw_after < raw_before,
         f"FG {fg_before}->{fg_after}; RAW {raw_before}->{raw_after}")
except Exception as e:
    step("Subcontracting supply->receipt", False, f"{type(e).__name__}: {str(e)[:180]}")

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
print(f"\n================ CYCLE 5 SUBCONTRACTING: {p}/{len(RESULTS)} passed ================")
frappe.destroy()
