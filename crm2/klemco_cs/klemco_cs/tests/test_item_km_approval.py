"""Item KM triple-approval tests — CR-18 / BR-KM-02.

Tests run as Administrator (has System Manager), so the role gate permits granting
approvals; an explicit non-privileged-role case verifies the gate blocks others.

NOTE: ERPNext Item inserts commit, so FrappeTestCase rollback won't undo them — each
test uses a unique item code and deletes it on cleanup to stay isolated and tidy.
"""
import frappe
from unittest.mock import patch
from frappe.tests.utils import FrappeTestCase

import klemco_cs.events.item as item_events


class TestKMItemApproval(FrappeTestCase):
    def setUp(self):
        self.item_group = frappe.db.get_value("Item Group", {"is_group": 0}, "name")
        self.hsn = frappe.db.get_value("GST HSN Code", {}, "name") if frappe.db.exists("DocType", "GST HSN Code") else None
        if not self.item_group:
            self.skipTest("no leaf Item Group in site")
        self.item_code = f"KL-TEST-KM-{self._testMethodName}"[:140]
        self._delete_item()
        self.addCleanup(self._delete_item)

    def _delete_item(self):
        if frappe.db.exists("Item", self.item_code):
            frappe.delete_doc("Item", self.item_code, force=True, ignore_permissions=True)
            frappe.db.commit()

    def _new_km_item(self, disabled=1, approvals=None):
        data = {
            "doctype": "Item",
            "item_code": self.item_code,
            "item_name": self.item_code,
            "item_group": self.item_group,
            "stock_uom": "Nos",
            "is_stock_item": 0,
            "custom_km_managed": 1,
            "disabled": disabled,
        }
        if self.hsn:
            data["gst_hsn_code"] = self.hsn
        data.update(approvals or {})
        return frappe.get_doc(data)

    def test_unapproved_km_item_cannot_be_enabled(self):
        doc = self._new_km_item(disabled=0)  # enabled, zero approvals
        self.assertRaises(frappe.ValidationError, doc.insert)

    def test_disabled_km_item_saves_as_pending(self):
        doc = self._new_km_item(disabled=1)
        doc.insert()
        self.assertEqual(doc.custom_km_approval_status, "Pending Approvals")

    def test_fully_approved_km_item_enables(self):
        doc = self._new_km_item(disabled=0, approvals={
            "custom_km_approved_cs_supervisor": 1,
            "custom_km_approved_plant_head": 1,
            "custom_km_approved_supply_chain": 1,
        })
        doc.insert()
        self.assertEqual(doc.custom_km_approval_status, "Approved")

    def test_role_gate_blocks_unauthorized_approval(self):
        doc = self._new_km_item(disabled=1)
        doc.insert()
        doc.custom_km_approved_cs_supervisor = 1
        with patch.object(item_events.frappe, "get_roles", return_value=["CS Executive"]):
            self.assertRaises(frappe.ValidationError, doc.save)

    def test_hooks_registered(self):
        events = frappe.get_hooks("doc_events").get("Item", {})
        self.assertIn("klemco_cs.events.item.validate", events.get("validate", []))
