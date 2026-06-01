"""Klemco CS — Phase 3: RBAC (role x action) + approval/submission gates + notifications.

Creates clean single-role test users, then:
  - builds the permission matrix via has_permission (submission/create/delete per role),
  - executes the approval gates AS each role (employee vs manager vs approver):
      * discount-deviation approval (Sales Head only)
      * KM item triple approval (each check only by its role)
  - checks notification trigger/content (SO acknowledgement; configured Notifications).
Cleans up users and docs afterwards.

Run:  ./env/bin/python rbac_runner.py
"""
import frappe
frappe.init(site="mysite.localhost", sites_path="/home/frappe/frappe-bench/sites")
frappe.connect()
frappe.set_user("Administrator")
from frappe.utils import nowdate, add_days
import klemco_cs.events.sales_order as so_events
import klemco_cs.events.item as item_events

RESULTS = []
def log(section, case, expected, actual, ok, detail=""):
    RESULTS.append((section, case, expected, actual, ok, detail))

CLEANUP_USERS = []
ROLE_USERS = {
    "CS Executive":     "uat.csexec@klemco.test",
    "CS Manager":       "uat.csmgr@klemco.test",
    "CS Supervisor":    "uat.cssup@klemco.test",
    "Sales Head":       "uat.saleshead@klemco.test",
    "KM Plant Head":    "uat.kmplant@klemco.test",
    "Supply Chain Lead":"uat.supplychain@klemco.test",
    "Accounts Manager": "uat.finance@klemco.test",
    "Stock User":       "uat.warehouse@klemco.test",
}

def ensure_user(role, email):
    if frappe.db.exists("User", email):
        frappe.delete_doc("User", email, force=True, ignore_permissions=True)
    u = frappe.get_doc({
        "doctype": "User", "email": email, "first_name": role.replace(" ", "") + "Test",
        "send_welcome_email": 0, "user_type": "System User",
        "roles": [{"role": role}],
    }).insert(ignore_permissions=True)
    CLEANUP_USERS.append(email)
    return email

USERS = {role: ensure_user(role, email) for role, email in ROLE_USERS.items()}
frappe.db.commit()

# ───────────────────────── A. Permission matrix (submission/create/delete) ─────────────────────────
MATRIX = [
    # (doctype, ptype, {role: expected_allowed})
    ("Sales Order", "create", {"CS Executive": False, "CS Manager": False, "Sales Head": False, "Accounts Manager": False}),
    ("KM Order", "create", {"CS Executive": True, "CS Manager": True, "CS Supervisor": True, "KM Plant Head": False, "Supply Chain Lead": False, "Accounts Manager": False, "Stock User": False}),
    ("KM Order", "submit", {"CS Executive": True, "CS Manager": True, "KM Plant Head": False, "Supply Chain Lead": False, "Stock User": False}),
    ("CS Complaint", "create", {"CS Executive": True, "CS Manager": True, "CS Supervisor": True, "Stock User": False, "Accounts Manager": False}),
    ("CS Complaint", "delete", {"CS Executive": False, "CS Manager": True, "CS Supervisor": False}),
    ("Sales Invoice", "create", {"Accounts Manager": True, "CS Executive": False, "Stock User": False}),
    ("Delivery Note", "submit", {"Stock User": True, "CS Executive": False, "Accounts Manager": False}),
]
for dt, ptype, expects in MATRIX:
    for role, expected in expects.items():
        user = USERS[role]
        actual = frappe.has_permission(dt, ptype, user=user)
        log("Permission matrix", f"{role} can {ptype} {dt}", expected, bool(actual), bool(actual) == expected)

# ───────────────────────── B. Discount-deviation approval gate (approval role) ─────────────────────────
# Build a real draft SO flagged as an RC deviation (as Administrator).
ITEM = "SKU007"; WH = "Finished Goods - KID"
HSN = frappe.db.get_value("GST HSN Code", {}, "name")
COMPANY = frappe.defaults.get_global_default("company") or frappe.db.get_value("Company", {}, "name")
CUST = frappe.db.get_value("Customer", {"disabled": 0}, "name")
if HSN and not frappe.db.get_value("Item", ITEM, "gst_hsn_code"):
    frappe.db.set_value("Item", ITEM, "gst_hsn_code", HSN)
orig_type = frappe.db.get_value("Customer", CUST, "custom_klemco_customer_type")
dev_so = None
try:
    frappe.db.set_value("Customer", CUST, "custom_klemco_customer_type", "RC (Rate Contract)")
    d = frappe.get_doc({
        "doctype": "Sales Order", "customer": CUST, "company": COMPANY,
        "transaction_date": nowdate(), "delivery_date": add_days(nowdate(), 8),
        "items": [{"item_code": ITEM, "qty": 1, "rate": 500, "discount_percentage": 5, "warehouse": WH, "delivery_date": add_days(nowdate(), 8)}],
    })
    d.insert(); dev_so = d.name
finally:
    frappe.db.set_value("Customer", CUST, "custom_klemco_customer_type", orig_type)

def try_approve(role):
    frappe.set_user(USERS[role])
    try:
        so_events.set_deviation_decision(dev_so, "Approved")
        return True
    except frappe.ValidationError:
        return False
    finally:
        frappe.set_user("Administrator")
        # reset status for next role
        frappe.db.set_value("Sales Order", dev_so, "custom_deviation_approval_status", "Pending Sales Head Approval")

if dev_so:
    for role, expected in [("CS Executive", False), ("CS Manager", False), ("Accounts Manager", False), ("Sales Head", True)]:
        actual = try_approve(role)
        log("Deviation approval", f"{role} approves RC discount deviation", expected, actual, actual == expected,
            "employee/other-manager denied; only Sales Head approves")

# ───────────────────────── C. KM item triple-approval per-role gate ─────────────────────────
item_group = frappe.db.get_value("Item Group", {"is_group": 0}, "name")
km_item = "UAT-RBAC-KM-ITEM"
if frappe.db.exists("Item", km_item):
    frappe.delete_doc("Item", km_item, force=True, ignore_permissions=True)
data = {"doctype": "Item", "item_code": km_item, "item_name": km_item, "item_group": item_group,
        "stock_uom": "Nos", "is_stock_item": 0, "custom_km_managed": 1, "disabled": 1}
if HSN:
    data["gst_hsn_code"] = HSN
frappe.get_doc(data).insert(); frappe.db.commit()

APPROVAL_FIELD = {
    "CS Supervisor": "custom_km_approved_cs_supervisor",
    "KM Plant Head": "custom_km_approved_plant_head",
    "Supply Chain Lead": "custom_km_approved_supply_chain",
}
# Each role may set only its own approval; others are blocked (validate role-gate).
for acting_role in ["CS Supervisor", "KM Plant Head", "Supply Chain Lead", "CS Executive"]:
    for owner_role, field in APPROVAL_FIELD.items():
        frappe.set_user(USERS[acting_role])
        doc = frappe.get_doc("Item", km_item)
        before = {f: doc.get(f) for f in APPROVAL_FIELD.values()}
        doc.set(field, 1)
        try:
            item_events.validate(doc)
            allowed = True
        except frappe.ValidationError:
            allowed = False
        finally:
            for f, v in before.items():
                doc.set(f, v)
            frappe.set_user("Administrator")
        expected = (acting_role == owner_role)
        log("KM item approval gate", f"{acting_role} grants '{owner_role}' approval", expected, allowed, allowed == expected)

# ───────────────────────── D. Notifications ─────────────────────────
# SO acknowledgement (CR-17): trigger + content (no delivery date)
from unittest.mock import patch
d = frappe._dict(name="RBAC-SO", customer=CUST, customer_name="Cust", contact_email="c@example.com", sales_team=[])
with patch.object(so_events.frappe, "sendmail") as m:
    so_events._send_acknowledgement(d)
    msg = (m.call_args.kwargs.get("message") or "").lower() if m.called else ""
ok = m.called and "initiated order execution" in msg and "delivery" not in msg
log("Notifications", "SO acknowledgement email (recipient+content, no delivery date)", True, ok, ok)
# enumerate configured Notification records relevant to CS doctypes
notifs = frappe.get_all("Notification", filters={"document_type": ["in", ["Sales Order", "KM Order", "CS Complaint", "Delivery Note", "Sales Invoice"]]},
                        fields=["name", "document_type", "event", "enabled"])
log("Notifications", "configured Notification records (CS doctypes)", "(info)", str(notifs), True, f"{len(notifs)} configured")

# ───────────────────────── cleanup ─────────────────────────
frappe.set_user("Administrator")
if dev_so and frappe.db.exists("Sales Order", dev_so):
    frappe.delete_doc("Sales Order", dev_so, force=True, ignore_permissions=True)
if frappe.db.exists("Item", km_item):
    frappe.delete_doc("Item", km_item, force=True, ignore_permissions=True)
for email in CLEANUP_USERS:
    if frappe.db.exists("User", email):
        frappe.delete_doc("User", email, force=True, ignore_permissions=True)
frappe.db.commit()

passed = sum(1 for r in RESULTS if r[4])
print("\n================ PHASE 3 RBAC + NOTIFICATIONS ================")
for section, case, expected, actual, ok, detail in RESULTS:
    print(f"{'PASS' if ok else 'FAIL'} | {section} | {case} | expected={expected} actual={actual}" + (f" | {detail}" if not ok or section == 'Notifications' else ""))
print(f"\n{passed}/{len(RESULTS)} checks passed")
frappe.destroy()
