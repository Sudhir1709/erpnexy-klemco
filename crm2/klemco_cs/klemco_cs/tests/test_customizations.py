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

    # ── Klemco Sales Order print format + suppressed "Enter Company Details" prompt ──
    def test_sales_order_print_format_exists(self):
        pf = frappe.db.get_value(
            "Print Format", "Klemco Sales Order",
            ["doc_type", "print_format_type", "custom_format"], as_dict=True,
        )
        self.assertIsNotNone(pf, "Klemco Sales Order print format not seeded")
        self.assertEqual(pf.doc_type, "Sales Order")
        self.assertEqual(pf.print_format_type, "Jinja")
        self.assertEqual(pf.custom_format, 1)

    def test_sales_order_default_print_format(self):
        frappe.clear_cache(doctype="Sales Order")
        self.assertEqual(frappe.get_meta("Sales Order").default_print_format, "Klemco Sales Order")

    def test_company_details_prompt_suppressed(self):
        from klemco_cs.printing import get_missing_company_details

        target = frappe.override_whitelisted_method(
            "erpnext.controllers.accounts_controller.get_missing_company_details"
        )
        self.assertEqual(target, "klemco_cs.printing.get_missing_company_details")
        frappe.is_whitelisted(frappe.get_attr(target))  # must not raise
        self.assertIsNone(get_missing_company_details("Sales Order", "SO-DOES-NOT-MATTER"))

    def test_sales_order_print_format_renders(self):
        from frappe.www.printview import get_html_and_style

        name = frappe.db.get_value("Sales Order", {"docstatus": ["<", 2]}, "name")
        if not name:
            self.skipTest("no Sales Order in site to render")
        html = get_html_and_style(
            doc="Sales Order", name=name, print_format="Klemco Sales Order", no_letterhead=1
        )["html"]
        self.assertIn("SALES ORDER", html)
        self.assertIn(name, html)
        self.assertNotIn("no such element", html)   # DebugUndefined leak from an unguarded field
        self.assertNotIn("letter-head", html)       # custom Jinja formats are self-contained

    # ── Mandate Documents: standard types pre-filled on a new order, file optional ──
    def test_mandate_document_types(self):
        meta = frappe.get_meta("CS Mandate Document")
        self.assertEqual(
            meta.get_field("document_type").options.split("\n"),
            ["Customer PO Copy", "Client Order Confirmation", "Test Certificate",
             "Technical Drawing / Specification", "Other"],
        )
        self.assertEqual(meta.get_field("file").reqd, 0, "placeholder rows must be saveable without a file")
