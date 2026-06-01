"""Notification layer tests (BRD §x.8) — content/recipient/trigger, with sendmail mocked."""
import frappe
from unittest.mock import patch
from frappe.tests.utils import FrappeTestCase

import klemco_cs.notifications as N


class TestNotifications(FrappeTestCase):
    def test_safe_sendmail_skips_without_recipients(self):
        with patch.object(N.frappe, "sendmail") as m:
            sent = N._safe_sendmail([], "s", "m")
        self.assertFalse(sent)
        self.assertFalse(m.called)

    def test_complaint_logged_emails_assignee(self):
        doc = frappe._dict(name="CMP-T-1", complaint_type="Product — Quality / Damage",
                           customer="C", priority="High", sla_deadline="2026-06-10")
        with patch.object(N, "_user_email", return_value="qc@example.com"), patch.object(N.frappe, "sendmail") as m:
            N.complaint_logged(doc)
        self.assertTrue(m.called)
        self.assertIn("qc@example.com", m.call_args.kwargs["recipients"])
        self.assertIn("CMP-T-1", m.call_args.kwargs["subject"])

    def test_complaint_closed_csat_emails_customer(self):
        doc = frappe._dict(name="CMP-T-2", customer="C")
        with patch.object(N, "_customer_email", return_value="cust@example.com"), patch.object(N.frappe, "sendmail") as m:
            N.complaint_closed_csat(doc)
        self.assertTrue(m.called)
        self.assertIn("cust@example.com", m.call_args.kwargs["recipients"])
        self.assertIn("resolved", m.call_args.kwargs["subject"].lower())

    def test_order_dispatched_emails_customer(self):
        doc = frappe._dict(name="DN-T-1", customer="C", customer_name="Cust", lr_no="DKT-9")
        with patch.object(N, "_customer_email", return_value="cust@example.com"), patch.object(N.frappe, "sendmail") as m:
            N.order_dispatched(doc)
        self.assertTrue(m.called)
        self.assertIn("dispatched", m.call_args.kwargs["subject"].lower())
        self.assertIn("DKT-9", m.call_args.kwargs["message"])

    def test_complaint_escalated_emails_managers(self):
        with patch.object(N, "_cs_manager_emails", return_value=["mgr@example.com"]), patch.object(N.frappe, "sendmail") as m:
            N.complaint_escalated("CMP-T-3", "C", "Product — Quality / Damage")
        self.assertTrue(m.called)
        self.assertIn("mgr@example.com", m.call_args.kwargs["recipients"])
        self.assertIn("SLA", m.call_args.kwargs["subject"])

    def test_hooks_registered(self):
        de = frappe.get_hooks("doc_events")
        self.assertIn("klemco_cs.notifications.complaint_logged", de.get("CS Complaint", {}).get("after_insert", []))
        self.assertIn("klemco_cs.notifications.order_dispatched", de.get("Delivery Note", {}).get("on_submit", []))
