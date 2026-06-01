"""KM Order tests — CR-11 (create-from-SO), BR-KM-01 (link required), BR-KM-02 (item gate).

Created docs are tracked and cleaned up (Item inserts commit, so rollback won't undo them).
"""
import frappe
from frappe.tests.utils import FrappeTestCase

from klemco_cs.customer_service.doctype.km_order.km_order import make_km_order


class TestKMOrder(FrappeTestCase):
    def setUp(self):
        self.so = frappe.db.get_value("Sales Order", {}, "name")
        self._created = []  # list of (doctype, name) to remove on cleanup
        self.addCleanup(self._cleanup)

    def _track(self, doc):
        self._created.append((doc.doctype, doc.name))
        return doc

    def _cleanup(self):
        for dt, name in reversed(self._created):
            if not frappe.db.exists(dt, name):
                continue
            try:
                d = frappe.get_doc(dt, name)
                if getattr(d, "docstatus", 0) == 1:
                    d.cancel()
                frappe.delete_doc(dt, name, force=True, ignore_permissions=True)
            except Exception:
                pass
        frappe.db.commit()

    # ── BR-KM-01 ──
    def test_km_order_requires_linked_sales_order(self):
        doc = frappe.new_doc("KM Order")
        self.assertRaises(frappe.ValidationError, doc.run_method, "validate")

    # ── CR-11 / FR-KM-08 ──
    def test_make_km_order_maps_qty_from_so(self):
        if not self.so:
            self.skipTest("no Sales Order in demo data")
        km = make_km_order(self.so)
        self.assertEqual(km.linked_sales_order, self.so)
        self.assertGreaterEqual(len(km.items), 1)
        for row in km.items:
            self.assertEqual(row.km_qty, row.so_qty)
            self.assertEqual(row.matches_so, 1)

    def test_matches_so_flag_recomputed_on_edit(self):
        if not self.so:
            self.skipTest("no Sales Order in demo data")
        km = make_km_order(self.so)
        km.items[0].km_qty = (km.items[0].so_qty or 0) + 7
        km.run_method("validate")
        self.assertEqual(km.items[0].matches_so, 0)

    def test_happy_submit_sets_confirmed(self):
        if not self.so:
            self.skipTest("no Sales Order in demo data")
        km = make_km_order(self.so)
        km.naming_series = "KMPO-.YYYY.-"
        km.insert()
        self._track(km)
        km.submit()
        self.assertEqual(km.status, "KM Confirmed")

    # ── BR-KM-02 ──
    def test_unapproved_km_item_blocks_submit(self):
        if not self.so:
            self.skipTest("no Sales Order in demo data")
        item_group = frappe.db.get_value("Item Group", {"is_group": 0}, "name")
        hsn = frappe.db.get_value("GST HSN Code", {}, "name") if frappe.db.exists("DocType", "GST HSN Code") else None
        item_code = f"KL-TEST-KMUNAPP-{self._testMethodName}"[:140]
        if not frappe.db.exists("Item", item_code):
            data = {
                "doctype": "Item", "item_code": item_code, "item_name": item_code,
                "item_group": item_group, "stock_uom": "Nos", "is_stock_item": 0,
                "custom_km_managed": 1, "disabled": 1,
            }
            if hsn:
                data["gst_hsn_code"] = hsn
            self._track(frappe.get_doc(data).insert())

        customer = frappe.db.get_value("Sales Order", self.so, "customer")
        km = frappe.get_doc({
            "doctype": "KM Order",
            "naming_series": "KMPO-.YYYY.-",
            "linked_sales_order": self.so,
            "customer": customer,
            "items": [{"item_code": item_code, "so_qty": 1, "km_qty": 1, "uom": "Nos"}],
        })
        km.insert()
        self._track(km)
        self.assertRaises(frappe.ValidationError, km.submit)
