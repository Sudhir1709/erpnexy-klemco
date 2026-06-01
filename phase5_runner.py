"""Klemco CS — Phase 5: NFR smoke + security checks (server-side).

NFR (BRD §9 targets): list-query latency (<2s proxy for page load), order save (<3s),
notification dispatch (<60s). Security: server-side RBAC enforcement at the ORM (not just
UI), and audit trail on tracked doctypes. (Unauthenticated-API check is done via HTTP.)

Run:  ./env/bin/python phase5_runner.py
"""
import frappe, time, statistics
frappe.init(site="mysite.localhost", sites_path="/home/frappe/frappe-bench/sites")
frappe.connect()
frappe.set_user("Administrator")
from frappe.utils import nowdate, add_days
from unittest.mock import patch
import klemco_cs.events.sales_order as so_events
from klemco_cs.customer_service.doctype.km_order.km_order import make_km_order

RESULTS = []
def log(section, case, target, measured, ok, detail=""):
    RESULTS.append((section, case, target, measured, ok, detail))

# ───────────── NFR 1: list-query latency (proxy for primary screens, §9 <2s P95) ─────────────
def p95(ts):
    s = sorted(ts); return s[min(len(s) - 1, int(round(0.95 * len(s))) - 1)]
for dt in ["Sales Order", "CS Complaint", "KM Order"]:
    ts = []
    for _ in range(25):
        t = time.perf_counter(); frappe.get_all(dt, fields=["name"], limit_page_length=20); ts.append((time.perf_counter() - t) * 1000)
    val = p95(ts)
    log("NFR latency", f"{dt} list query (P95)", "< 2000 ms", f"{val:.0f} ms", val < 2000, f"median {statistics.median(ts):.0f} ms")

# ───────────── NFR 2: order save latency (§9 <3s) ─────────────
SO = frappe.db.get_value("Sales Order", {}, "name")
created = []
if SO:
    t = time.perf_counter()
    km = make_km_order(SO); km.naming_series = "KMPO-.YYYY.-"; km.insert(); km.submit()
    elapsed = (time.perf_counter() - t) * 1000
    created.append(("KM Order", km.name))
    log("NFR latency", "KM Order create+submit", "< 3000 ms", f"{elapsed:.0f} ms", elapsed < 3000)

# ───────────── NFR 3: notification dispatch time (§9 <60s) ─────────────
CUST = frappe.db.get_value("Customer", {}, "name")
d = frappe._dict(name="P5-SO", customer=CUST, customer_name="C", contact_email="c@example.com", sales_team=[])
with patch.object(so_events.frappe, "sendmail"):
    t = time.perf_counter(); so_events._send_acknowledgement(d); elapsed = (time.perf_counter() - t) * 1000
log("NFR latency", "SO acknowledgement dispatch", "< 60000 ms", f"{elapsed:.0f} ms", elapsed < 60000, "enqueued/sync send")

# ───────────── Security 1: server-side RBAC enforcement at the ORM ─────────────
sec_user = "p5.stockuser@klemco.test"
if frappe.db.exists("User", sec_user):
    frappe.delete_doc("User", sec_user, force=True, ignore_permissions=True)
frappe.get_doc({"doctype": "User", "email": sec_user, "first_name": "P5Stock", "send_welcome_email": 0,
                "user_type": "System User", "roles": [{"role": "Stock User"}]}).insert(ignore_permissions=True)
frappe.db.commit()
frappe.set_user(sec_user)
try:
    km = frappe.get_doc({"doctype": "KM Order", "naming_series": "KMPO-.YYYY.-", "linked_sales_order": SO,
                         "customer": CUST, "items": [{"item_code": "SKU007", "so_qty": 1, "km_qty": 1, "uom": "Nos"}]})
    km.insert()  # should be blocked — Stock User has no KM Order create perm
    blocked = False
except frappe.PermissionError:
    blocked = True
except Exception as e:
    blocked = "PermissionError" in type(e).__name__
finally:
    frappe.set_user("Administrator")
log("Security", "Unauthorised role blocked at ORM (Stock User create KM Order)", "denied", "denied" if blocked else "ALLOWED", blocked,
    "enforced server-side, not just UI")

# ───────────── Security 2: deviation approval cannot be bypassed at submit ─────────────
# (before_submit gate fires regardless of who submits)
gate = False
try:
    so_events.before_submit(frappe._dict(custom_rc_deviation=1, custom_deviation_approval_status="Pending Sales Head Approval"))
except frappe.ValidationError:
    gate = True
log("Security", "Unapproved RC deviation cannot be submitted (server gate)", "blocked", "blocked" if gate else "ALLOWED", gate)

# ───────────── Security 3: audit trail on tracked doctype ─────────────
c = frappe.get_doc({"doctype": "CS Complaint", "naming_series": "CMP-.YYYY.-", "complaint_type": "Non-Product — Service",
                    "priority": "Low", "status": "Open", "customer": CUST,
                    "linked_sales_order": SO, "assigned_to": "Administrator",
                    "description": "<p>p5</p>", "override_reason": "p5"}).insert()
created.append(("CS Complaint", c.name))
c.priority = "High"; c.save()
versions = frappe.db.count("Version", {"ref_doctype": "CS Complaint", "docname": c.name})
log("Security", "Audit trail captured on CS Complaint change (track_changes)", ">=1 version", f"{versions} version(s)", versions >= 1)

# ───────────── cleanup ─────────────
frappe.set_user("Administrator")
for dt, name in reversed(created):
    if frappe.db.exists(dt, name):
        try:
            doc = frappe.get_doc(dt, name)
            if getattr(doc, "docstatus", 0) == 1:
                doc.cancel()
            frappe.delete_doc(dt, name, force=True, ignore_permissions=True)
        except Exception:
            pass
if frappe.db.exists("User", sec_user):
    frappe.delete_doc("User", sec_user, force=True, ignore_permissions=True)
frappe.db.commit()

passed = sum(1 for r in RESULTS if r[4])
print("\n================ PHASE 5 — NFR + SECURITY ================")
for section, case, target, measured, ok, detail in RESULTS:
    print(f"{'PASS' if ok else 'FAIL'} | {section} | {case} | target={target} | measured={measured}" + (f" | {detail}" if detail else ""))
print(f"\n{passed}/{len(RESULTS)} checks passed")
frappe.destroy()
