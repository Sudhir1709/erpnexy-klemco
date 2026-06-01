"""Delivery Note tests — CR-16 (delivery instructions carry-over) and CR-15 (test-cert download)."""
import frappe
from unittest.mock import patch
from frappe.tests.utils import FrappeTestCase

import klemco_cs.events.delivery_note as dn


class TestDeliveryNote(FrappeTestCase):
    def setUp(self):
        self.so = frappe.db.get_value("Sales Order", {}, "name")

    # ── CR-16 ──
    def test_carry_instructions_from_so(self):
        if not self.so:
            self.skipTest("no Sales Order in demo data")
        frappe.db.set_value("Sales Order", self.so, "custom_delivery_instructions", "Unload by forklift; gate 5 PM")
        d = frappe._dict(custom_delivery_instructions=None, items=[frappe._dict(against_sales_order=self.so)])
        dn._carry_delivery_instructions(d)
        self.assertEqual(d.custom_delivery_instructions, "Unload by forklift; gate 5 PM")

    def test_carry_skips_when_already_set(self):
        d = frappe._dict(custom_delivery_instructions="Keep dry", items=[frappe._dict(against_sales_order=self.so)])
        dn._carry_delivery_instructions(d)
        self.assertEqual(d.custom_delivery_instructions, "Keep dry")

    def test_linked_sales_order_resolution(self):
        d = frappe._dict(items=[frappe._dict(against_sales_order=None), frappe._dict(against_sales_order="SO-XYZ")])
        self.assertEqual(dn._linked_sales_order(d), "SO-XYZ")
        self.assertIsNone(dn._linked_sales_order(frappe._dict(items=[])))

    # ── CR-15 / FR-DP-12 ──
    def test_get_so_test_certificates_lists_attached_files(self):
        if not self.so:
            self.skipTest("no Sales Order in demo data")
        f = frappe.get_doc({
            "doctype": "File",
            "file_name": "TestCert_UT.txt",
            "attached_to_doctype": "Sales Order",
            "attached_to_name": self.so,
            "is_private": 0,
            "content": "unit-test-cert",
        }).insert(ignore_permissions=True)
        fake_dn = frappe._dict(items=[frappe._dict(against_sales_order=self.so)])
        with patch.object(dn.frappe, "get_doc", return_value=fake_dn):
            files = dn.get_so_test_certificates("DUMMY-DN")
        self.assertIn("TestCert_UT.txt", [x.get("file_name") for x in files])
        f.delete(ignore_permissions=True)

    def test_get_so_test_certificates_empty_without_so(self):
        fake_dn = frappe._dict(items=[])
        with patch.object(dn.frappe, "get_doc", return_value=fake_dn):
            self.assertEqual(dn.get_so_test_certificates("DUMMY-DN"), [])

    def test_hooks_registered(self):
        events = frappe.get_hooks("doc_events").get("Delivery Note", {})
        self.assertIn("klemco_cs.events.delivery_note.validate", events.get("validate", []))
