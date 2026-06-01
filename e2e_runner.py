"""Klemco CS — end-to-end flow runner (Phase 2).

Drives real document chains on the live 8080 site:
  E2E-1  Happy path: SO -> Delivery Challan (DN) -> Sales Invoice -> linked trail
  E2E-2  RC discount deviation gate on a real SO -> Sales Head approval -> submit
  E2E-3  KM Order from a real submitted SO -> confirm
Exercises klemco_cs customizations in-flow. Cleans up all created docs afterwards.

Run:  ./env/bin/python e2e_runner.py
"""
import frappe
frappe.init(site="mysite.localhost", sites_path="/home/frappe/frappe-bench/sites")
frappe.connect()
frappe.set_user("Administrator")
from frappe.utils import nowdate, add_days
from erpnext.selling.doctype.sales_order.sales_order import make_delivery_note, make_sales_invoice
import klemco_cs.events.sales_order as so_events
from klemco_cs.customer_service.doctype.km_order.km_order import make_km_order

RESULTS = []
CREATED = []  # (doctype, name)

def log(step, ok, detail=""):
    RESULTS.append((step, ok, detail))
    print(f"{'PASS' if ok else 'FAIL'} | {step} | {detail}")

def track(dt, name):
    CREATED.append((dt, name)); return name

ITEM = "SKU007"
WH = "Finished Goods - KID"
COMPANY = frappe.defaults.get_global_default("company") or frappe.db.get_value("Company", {}, "name")
HSN = frappe.db.get_value("GST HSN Code", {}, "name")
CUST = frappe.db.get_value("Customer", {"disabled": 0}, "name")

if HSN and not frappe.db.get_value("Item", ITEM, "gst_hsn_code"):
    frappe.db.set_value("Item", ITEM, "gst_hsn_code", HSN)

# ───────────────────────── E2E-1 : SO -> Challan -> Invoice ─────────────────────────
so1 = None
try:
    doc = frappe.get_doc({
        "doctype": "Sales Order", "customer": CUST, "company": COMPANY,
        "transaction_date": nowdate(), "delivery_date": add_days(nowdate(), 7),
        "custom_delivery_instructions": "Unload by forklift; call site manager before arrival",
        "items": [{"item_code": ITEM, "qty": 2, "rate": 500, "warehouse": WH, "delivery_date": add_days(nowdate(), 7)}],
    })
    doc.insert(); track("Sales Order", doc.name); doc.submit()
    so1 = doc.name
    log("E2E-1.1 create+submit Sales Order", True, f"SO={so1}, status={doc.status}")
except Exception as e:
    log("E2E-1.1 create+submit Sales Order", False, f"{type(e).__name__}: {str(e)[:140]}")

if so1:
    try:
        dn = make_delivery_note(so1)
        dn.insert(); track("Delivery Note", dn.name)
        carried = dn.get("custom_delivery_instructions")
        dn.submit()
        ok = carried == "Unload by forklift; call site manager before arrival"
        log("E2E-1.2 create+submit Delivery Challan (CR-16 instructions carried)", ok,
            f"DN={dn.name}; instructions='{carried}'")
    except Exception as e:
        log("E2E-1.2 create+submit Delivery Challan", False, f"{type(e).__name__}: {str(e)[:140]}")

    try:
        si = make_sales_invoice(so1)
        si.insert(); track("Sales Invoice", si.name); si.submit()
        log("E2E-1.3 create+submit GST Sales Invoice", True, f"INV={si.name}; grand_total={si.grand_total}")
    except Exception as e:
        log("E2E-1.3 create+submit GST Sales Invoice", False, f"{type(e).__name__}: {str(e)[:140]}")

    # linked-document trail
    try:
        dns = frappe.get_all("Delivery Note Item", filters={"against_sales_order": so1}, fields=["parent"])
        sis = frappe.get_all("Sales Invoice Item", filters={"sales_order": so1}, fields=["parent"])
        ok = bool(dns) and bool(sis)
        log("E2E-1.4 linked trail SO->DN->Invoice", ok, f"DN(s)={set(d.parent for d in dns)}; INV(s)={set(s.parent for s in sis)}")
    except Exception as e:
        log("E2E-1.4 linked trail", False, str(e)[:140])

# ───────────────────────── E2E-2 : RC deviation approval on a real SO ─────────────────────────
orig_type = frappe.db.get_value("Customer", CUST, "custom_klemco_customer_type")
try:
    frappe.db.set_value("Customer", CUST, "custom_klemco_customer_type", "RC (Rate Contract)")
    doc = frappe.get_doc({
        "doctype": "Sales Order", "customer": CUST, "company": COMPANY,
        "transaction_date": nowdate(), "delivery_date": add_days(nowdate(), 9),
        "items": [{"item_code": ITEM, "qty": 1, "rate": 500, "discount_percentage": 5,
                   "warehouse": WH, "delivery_date": add_days(nowdate(), 9)}],
    })
    doc.insert(); track("Sales Order", doc.name)
    flagged = doc.get("custom_rc_deviation") == 1 and doc.get("custom_deviation_approval_status") == "Pending Sales Head Approval"
    # submit must be blocked while pending
    try:
        doc.submit(); blocked = False
    except frappe.ValidationError:
        blocked = True
    # Sales Head approves (Administrator has System Manager -> allowed by the gate)
    so_events.set_deviation_decision(doc.name, "Approved")
    doc.reload()
    doc.submit()
    approved_submits = doc.docstatus == 1
    log("E2E-2 RC deviation: flagged -> blocked -> Sales Head approves -> submits", flagged and blocked and approved_submits,
        f"flagged={flagged}; blocked_pre_approval={blocked}; submitted_after_approval={approved_submits}; SO={doc.name}")
except Exception as e:
    log("E2E-2 RC deviation approval", False, f"{type(e).__name__}: {str(e)[:140]}")
finally:
    frappe.db.set_value("Customer", CUST, "custom_klemco_customer_type", orig_type)

# ───────────────────────── E2E-3 : KM Order from real SO ─────────────────────────
if so1:
    try:
        km = make_km_order(so1)
        km.naming_series = "KMPO-.YYYY.-"
        km.insert(); track("KM Order", km.name)
        km.submit()
        log("E2E-3 KM Order from SO -> confirm", km.status == "KM Confirmed", f"KM={km.name}; status={km.status}")
    except Exception as e:
        log("E2E-3 KM Order from SO", False, f"{type(e).__name__}: {str(e)[:140]}")

# ───────────────────────── cleanup ─────────────────────────
for dt, name in reversed(CREATED):
    if frappe.db.exists(dt, name):
        try:
            d = frappe.get_doc(dt, name)
            if getattr(d, "docstatus", 0) == 1:
                d.cancel()
            frappe.delete_doc(dt, name, force=True, ignore_permissions=True)
        except Exception as e:
            print("CLEANUP skip", dt, name, str(e)[:80])
frappe.db.commit()

passed = sum(1 for r in RESULTS if r[1])
print(f"\n================ E2E RESULTS: {passed}/{len(RESULTS)} steps passed ================")
frappe.destroy()
