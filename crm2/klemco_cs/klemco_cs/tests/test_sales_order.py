"""Sales Order rule tests — CR-09, CR-14, CR-10/BR-SO-01, CR-17.

Validation logic is exercised by calling the hooked functions directly with realistic
doc objects (robust, no full ERPNext transaction scaffolding); a couple of real-doc
inserts confirm the hooks are actually wired on validate.
"""
import frappe
from unittest.mock import patch
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, nowdate

import klemco_cs.events.sales_order as so


class TestSalesOrderRules(FrappeTestCase):
    def setUp(self):
        self.customer = frappe.db.get_value("Customer", {"disabled": 0}, "name") or frappe.db.get_value(
            "Customer", {}, "name"
        )
        self.assertIsNotNone(self.customer, "no Customer in site to test against")

    # ── CR-09 / FR-SO-16 — back-date validation ──
    def test_backdated_header_blocked(self):
        d = frappe._dict(delivery_date=add_days(nowdate(), -1), items=[])
        self.assertRaises(frappe.ValidationError, so._validate_delivery_dates, d)

    def test_backdated_line_blocked(self):
        d = frappe._dict(
            delivery_date=None,
            items=[frappe._dict(idx=1, item_code="X", delivery_date=add_days(nowdate(), -2))],
        )
        self.assertRaises(frappe.ValidationError, so._validate_delivery_dates, d)

    def test_future_date_allowed(self):
        d = frappe._dict(
            delivery_date=add_days(nowdate(), 5),
            items=[frappe._dict(idx=1, item_code="X", delivery_date=add_days(nowdate(), 10))],
        )
        so._validate_delivery_dates(d)  # must not raise

    def test_today_allowed(self):
        d = frappe._dict(delivery_date=nowdate(), items=[])
        so._validate_delivery_dates(d)

    # ── CR-14 / FR-SO-04 — 3PL "Others" needs a note ──
    def test_3pl_others_without_note_blocked(self):
        d = frappe._dict(custom_preferred_3pl="Others (not yet decided)", custom_3pl_note="")
        self.assertRaises(frappe.ValidationError, so._validate_3pl, d)

    def test_3pl_others_with_note_ok(self):
        d = frappe._dict(custom_preferred_3pl="Others (not yet decided)", custom_3pl_note="TBD at dispatch")
        so._validate_3pl(d)

    def test_3pl_configured_ok(self):
        d = frappe._dict(custom_preferred_3pl="Blue Dart", custom_3pl_note="")
        so._validate_3pl(d)

    # ── CR-10 / FR-SO-06 / BR-SO-01 — RC discount = conditional deviation ──
    def _dict_with_discount(self, disc):
        return frappe._dict(
            customer=self.customer,
            additional_discount_percentage=0,
            discount_amount=0,
            custom_deviation_approval_status="Not Required",
            items=[frappe._dict(discount_percentage=disc, discount_amount=0)],
        )

    def test_rc_discount_flags_deviation(self):
        frappe.db.set_value("Customer", self.customer, "custom_klemco_customer_type", "RC (Rate Contract)")
        d = self._dict_with_discount(5)
        so._flag_rc_deviation(d)
        self.assertEqual(d.custom_rc_deviation, 1)
        self.assertEqual(d.custom_deviation_approval_status, "Pending Sales Head Approval")

    def test_rc_zero_discount_no_deviation(self):
        frappe.db.set_value("Customer", self.customer, "custom_klemco_customer_type", "RC (Rate Contract)")
        d = self._dict_with_discount(0)
        so._flag_rc_deviation(d)
        self.assertFalse(d.custom_rc_deviation)

    def test_non_rc_discount_no_deviation(self):
        frappe.db.set_value("Customer", self.customer, "custom_klemco_customer_type", "Regular")
        d = self._dict_with_discount(10)
        so._flag_rc_deviation(d)
        self.assertFalse(d.custom_rc_deviation)

    def test_before_submit_blocks_unapproved_deviation(self):
        d = frappe._dict(custom_rc_deviation=1, custom_deviation_approval_status="Pending Sales Head Approval")
        self.assertRaises(frappe.ValidationError, so.before_submit, d)

    def test_before_submit_allows_approved_deviation(self):
        d = frappe._dict(custom_rc_deviation=1, custom_deviation_approval_status="Approved")
        so.before_submit(d)  # must not raise

    def test_deviation_decision_requires_sales_head(self):
        with patch.object(so.frappe, "get_roles", return_value=["CS Executive"]):
            self.assertRaises(frappe.ValidationError, so.set_deviation_decision, "SO-DUMMY", "Approved")

    def test_deviation_decision_rejects_invalid(self):
        self.assertRaises(frappe.ValidationError, so.set_deviation_decision, "SO-DUMMY", "Maybe")

    # ── CR-17 / FR-SO-09 — simplified acknowledgement, NO delivery date ──
    def test_ack_email_sent_without_delivery_date(self):
        d = frappe._dict(
            name="SO-TEST-0001",
            customer=self.customer,
            customer_name="Test Co",
            contact_email="cust@example.com",
            sales_team=[],
        )
        with patch.object(so.frappe, "sendmail") as m:
            so._send_acknowledgement(d)
            self.assertTrue(m.called, "acknowledgement email was not sent")
            kwargs = m.call_args.kwargs
            message = (kwargs.get("message") or "").lower()
            self.assertIn("initiated order execution", message)
            self.assertNotIn("delivery", message)
            self.assertNotIn("expected delivery", message)


class TestSalesOrderHookWiring(FrappeTestCase):
    """Confirm the event handlers are actually wired into Sales Order (not just present)."""

    def test_hooks_registered(self):
        events = frappe.get_hooks("doc_events").get("Sales Order", {})
        self.assertIn("klemco_cs.events.sales_order.validate", events.get("validate", []))
        self.assertIn("klemco_cs.events.sales_order.before_submit", events.get("before_submit", []))
        self.assertIn("klemco_cs.events.sales_order.on_submit", events.get("on_submit", []))
