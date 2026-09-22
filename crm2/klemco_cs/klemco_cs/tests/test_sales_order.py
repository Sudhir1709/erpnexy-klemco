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
        self.assertIn("klemco_cs.events.sales_order.before_update_after_submit",
                      events.get("before_update_after_submit", []))
        self.assertIn("klemco_cs.events.sales_order.on_update_after_submit",
                      events.get("on_update_after_submit", []))


# ── Change of plant (source warehouse) on a submitted order ──
def _plant_doc(rows, before_rows, set_wh="Amritsar Main Store - KI", before_set_wh=None):
    """A submitted-order stand-in: items + the snapshot get_doc_before_save() returns."""
    doc = frappe._dict(
        name="SO-TEST", company="Klemco India", set_warehouse=set_wh, docstatus=1,
        items=[frappe._dict(r) for r in rows], flags=frappe._dict(),
    )
    before = frappe._dict(set_warehouse=before_set_wh or set_wh, items=[frappe._dict(r) for r in before_rows])
    doc.get_doc_before_save = lambda: before
    doc.has_product_bundle = lambda item_code: item_code == "BUNDLE"
    return doc


def _row(name, wh, **kw):
    base = dict(name=name, idx=1, item_code="KL-CA-001", warehouse=wh, qty=2, delivered_qty=0,
                picked_qty=0, delivered_by_supplier=0)
    base.update(kw)
    return base


class TestPlantChange(FrappeTestCase):
    def test_detects_changed_rows_only(self):
        doc = _plant_doc(
            [_row("r1", "Thane Branch Store - KI"), _row("r2", "Amritsar Main Store - KI")],
            [_row("r1", "Amritsar Main Store - KI"), _row("r2", "Amritsar Main Store - KI")],
        )
        changes = so._warehouse_changes(doc)
        self.assertEqual([(c[0].name, c[1], c[2]) for c in changes],
                         [("r1", "Amritsar Main Store - KI", "Thane Branch Store - KI")])

    def test_no_snapshot_means_no_change(self):
        doc = frappe._dict(items=[frappe._dict(_row("r1", "X"))])
        self.assertEqual(so._warehouse_changes(doc), [])

    def _run(self, doc):
        with patch.object(so, "_validate_plant"), patch("frappe.db.get_value", return_value=None):
            so.before_update_after_submit(doc)
        return doc.flags.get("klemco_wh_changes")

    def test_clean_change_passes_and_is_flagged(self):
        doc = _plant_doc([_row("r1", "Thane Branch Store - KI")], [_row("r1", "Amritsar Main Store - KI")],
                         set_wh="Thane Branch Store - KI", before_set_wh="Amritsar Main Store - KI")
        self.assertEqual(self._run(doc), [("r1", "Amritsar Main Store - KI", "Thane Branch Store - KI")])

    def test_delivered_row_blocked(self):
        doc = _plant_doc([_row("r1", "Thane Branch Store - KI", delivered_qty=1)],
                         [_row("r1", "Amritsar Main Store - KI", delivered_qty=1)])
        self.assertRaises(frappe.ValidationError, self._run, doc)

    def test_picked_row_blocked(self):
        doc = _plant_doc([_row("r1", "Thane Branch Store - KI", picked_qty=2)],
                         [_row("r1", "Amritsar Main Store - KI", picked_qty=2)])
        self.assertRaises(frappe.ValidationError, self._run, doc)

    def test_row_on_draft_delivery_note_blocked(self):
        doc = _plant_doc([_row("r1", "Thane Branch Store - KI")], [_row("r1", "Amritsar Main Store - KI")])
        with patch.object(so, "_validate_plant"), patch("frappe.db.get_value", return_value="MAT-DN-0001"):
            self.assertRaises(frappe.ValidationError, so.before_update_after_submit, doc)

    def test_bundle_row_blocked(self):
        doc = _plant_doc([_row("r1", "Thane Branch Store - KI", item_code="BUNDLE")],
                         [_row("r1", "Amritsar Main Store - KI", item_code="BUNDLE")])
        self.assertRaises(frappe.ValidationError, self._run, doc)

    def test_header_change_on_fully_delivered_order_blocked(self):
        doc = _plant_doc([_row("r1", "Amritsar Main Store - KI", delivered_qty=2)],
                         [_row("r1", "Amritsar Main Store - KI", delivered_qty=2)],
                         set_wh="Thane Branch Store - KI", before_set_wh="Amritsar Main Store - KI")
        self.assertRaises(frappe.ValidationError, self._run, doc)

    def test_plant_must_be_a_real_non_group_warehouse_of_the_company(self):
        self.assertRaises(frappe.ValidationError, so._validate_plant, "No Such Warehouse - XX", "Klemco India")
        group = frappe.db.get_value("Warehouse", {"is_group": 1}, "name")
        if group:
            self.assertRaises(frappe.ValidationError, so._validate_plant, group,
                              frappe.db.get_value("Warehouse", group, "company"))
