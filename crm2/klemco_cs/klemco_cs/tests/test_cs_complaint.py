"""CS Complaint tests — SLA, routing/auto-assignee, override gate, escalation, CSAT (BRD §8)."""
import frappe
from unittest.mock import patch
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_to_date, now_datetime

import klemco_cs.customer_service.doctype.cs_complaint.cs_complaint as cmp


class TestCSComplaint(FrappeTestCase):
    def setUp(self):
        self.so = frappe.db.get_value("Sales Order", {}, "name")
        if not self.so:
            self.skipTest("no Sales Order in demo data (complaint requires a linked SO)")
        self.customer = frappe.db.get_value("Sales Order", self.so, "customer")

    def _make(self, ctype="Product — Quality / Damage", priority="Medium", override_reason="UT override", status="Open"):
        return frappe.get_doc({
            "doctype": "CS Complaint", "naming_series": "CMP-.YYYY.-",
            "complaint_type": ctype,
            "priority": priority,
            "status": status,
            "customer": self.customer,
            "linked_sales_order": self.so,
            "assigned_to": "Administrator",
            "description": "<p>unit test complaint</p>",
            "override_reason": override_reason,
        }).insert()

    # ── BR-CM-01 ──
    def test_requires_linked_sales_order(self):
        doc = frappe.get_doc({
            "doctype": "CS Complaint", "naming_series": "CMP-.YYYY.-", "complaint_type": "Non-Product — Service", "priority": "Low",
            "status": "Open", "customer": self.customer, "assigned_to": "Administrator",
            "description": "<p>x</p>", "override_reason": "x",
        })
        self.assertRaises(frappe.ValidationError, doc.insert)

    # ── FR-8-02 — SLA by priority ──
    def test_sla_hours_by_priority(self):
        self.assertEqual(self._make(priority="Critical").sla_hours_total, 24)
        self.assertEqual(self._make(priority="Low").sla_hours_total, 72)
        self.assertEqual(self._make(priority="High").sla_hours_total, 48)

    def test_sla_deadline_set(self):
        c = self._make(priority="Medium")
        self.assertTrue(c.sla_deadline)

    # ── FR-CM-11 — routing / auto-assignee ──
    def test_algorithm_suggested_by_type(self):
        self.assertEqual(self._make(ctype="Product — Quality / Damage").algorithm_suggested, "QC Head")
        self.assertEqual(self._make(ctype="Non-Product — Billing / Invoice").algorithm_suggested, "Finance Lead")
        self.assertEqual(self._make(ctype="Product — Short Delivery").algorithm_suggested, "Supply Chain Lead")

    # ── BR-CM-06 — override needs reason ──
    def test_override_without_reason_blocked(self):
        doc = frappe.get_doc({
            "doctype": "CS Complaint", "naming_series": "CMP-.YYYY.-", "complaint_type": "Product — Quality / Damage", "priority": "Medium",
            "status": "Open", "customer": self.customer, "linked_sales_order": self.so,
            "assigned_to": "Administrator", "description": "<p>x</p>", "override_reason": "",
        })
        # assigned_to (Administrator) != suggested (QC Head) and no reason -> blocked
        self.assertRaises(frappe.ValidationError, doc.insert)

    # ── BR-CM-05 — escalation at >=80% SLA ──
    def test_escalation_when_sla_mostly_consumed(self):
        c = self._make(priority="Medium")  # 48h
        frappe.db.set_value("CS Complaint", c.name, "creation", add_to_date(now_datetime(), hours=-45))
        with patch.object(cmp.frappe.db, "commit"):  # keep test isolated
            cmp.escalate_overdue_complaints()
        self.assertEqual(frappe.db.get_value("CS Complaint", c.name, "status"), "Escalated")

    def test_no_escalation_when_fresh(self):
        c = self._make(priority="Low")  # 72h, just created
        with patch.object(cmp.frappe.db, "commit"):
            cmp.escalate_overdue_complaints()
        self.assertNotEqual(frappe.db.get_value("CS Complaint", c.name, "status"), "Escalated")

    # ── FR-8-08 — CSAT on closure ──
    # NOTE: a "CS Complaint Workflow" governs the Open->Closed *transition*; that's separate
    # from our CSAT trigger. We verify the trigger (on_update logic) directly.
    def test_csat_survey_on_close(self):
        c = self._make(status="Open")
        c.status = "Closed"
        c.run_method("on_update")
        self.assertEqual(frappe.db.get_value("CS Complaint", c.name, "csat_survey_sent"), 1)
