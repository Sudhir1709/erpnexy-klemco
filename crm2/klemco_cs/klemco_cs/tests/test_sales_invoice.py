"""Sales Invoice COD cheque tests — CR-13 / FR-DP-11 / BR-DP-06."""
import frappe
from frappe.tests.utils import FrappeTestCase

import klemco_cs.events.sales_invoice as si


class TestSalesInvoiceCOD(FrappeTestCase):
    def setUp(self):
        self.customer = frappe.db.get_value("Customer", {}, "name")
        self.assertIsNotNone(self.customer)

    def _set_type(self, t):
        frappe.db.set_value("Customer", self.customer, "custom_klemco_customer_type", t)

    def test_is_cod_true_for_cod_customer(self):
        self._set_type("COD")
        self.assertTrue(si._is_cod(frappe._dict(customer=self.customer)))

    def test_is_cod_false_for_regular(self):
        self._set_type("Regular")
        self.assertFalse(si._is_cod(frappe._dict(customer=self.customer)))

    def test_validate_sets_is_cod_flag(self):
        self._set_type("COD")
        d = frappe._dict(customer=self.customer)
        si.validate(d)
        self.assertEqual(d.custom_is_cod, 1)

    def test_cod_blocked_without_cheque(self):
        self._set_type("COD")
        d = frappe._dict(customer=self.customer, custom_cheque_no=None, custom_cheque_date=None, custom_cheque_amount=None)
        self.assertRaises(frappe.ValidationError, si.before_submit, d)

    def test_cod_partial_cheque_still_blocked(self):
        self._set_type("COD")
        d = frappe._dict(customer=self.customer, custom_cheque_no="123", custom_cheque_date=None, custom_cheque_amount=None)
        self.assertRaises(frappe.ValidationError, si.before_submit, d)

    def test_cod_passes_with_full_cheque(self):
        self._set_type("COD")
        d = frappe._dict(customer=self.customer, custom_cheque_no="123456", custom_cheque_date="2026-06-30", custom_cheque_amount=5000)
        si.before_submit(d)  # must not raise

    def test_non_cod_has_no_gate(self):
        self._set_type("Regular")
        si.before_submit(frappe._dict(customer=self.customer))  # must not raise

    def test_hooks_registered(self):
        events = frappe.get_hooks("doc_events").get("Sales Invoice", {})
        self.assertIn("klemco_cs.events.sales_invoice.validate", events.get("validate", []))
        self.assertIn("klemco_cs.events.sales_invoice.before_submit", events.get("before_submit", []))
