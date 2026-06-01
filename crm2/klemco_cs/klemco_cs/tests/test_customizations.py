"""Phase 0 — schema/customizations smoke test.

Confirms the v1.3 layer is actually applied on the site under test (custom fields,
KM Order doctypes, Delivery Challan print format, roles). Fast, no transactions.
"""
import frappe
from frappe.tests.utils import FrappeTestCase

CUSTOM_FIELDS = [
    ("Customer", "custom_klemco_customer_type"),
    ("Sales Order", "custom_preferred_3pl"),
    ("Sales Order", "custom_3pl_note"),
    ("Sales Order", "custom_rc_deviation"),
    ("Sales Order", "custom_deviation_approval_status"),
    ("Sales Order", "custom_delivery_instructions"),
    ("Delivery Note", "custom_delivery_instructions"),
    ("Sales Invoice", "custom_is_cod"),
    ("Sales Invoice", "custom_cheque_no"),
    ("Sales Invoice", "custom_cheque_amount"),
    ("Item", "custom_km_managed"),
    ("Item", "custom_km_approved_cs_supervisor"),
    ("Item", "custom_km_approved_plant_head"),
    ("Item", "custom_km_approved_supply_chain"),
]

ROLES = ["CS Executive", "CS Manager", "CS Supervisor", "Sales Head", "KM Plant Head", "Supply Chain Lead"]


class TestCustomizations(FrappeTestCase):
    def test_km_order_doctypes_exist(self):
        self.assertTrue(frappe.db.exists("DocType", "KM Order"))
        self.assertTrue(frappe.db.exists("DocType", "KM Order Item"))

    def test_delivery_challan_print_format(self):
        self.assertTrue(frappe.db.exists("Print Format", "Delivery Challan"))

    def test_custom_fields_present(self):
        for dt, fn in CUSTOM_FIELDS:
            self.assertTrue(
                frappe.db.exists("Custom Field", {"dt": dt, "fieldname": fn}),
                msg=f"missing custom field {dt}.{fn}",
            )

    def test_roles_present(self):
        for role in ROLES:
            self.assertTrue(frappe.db.exists("Role", role), msg=f"missing role {role}")
