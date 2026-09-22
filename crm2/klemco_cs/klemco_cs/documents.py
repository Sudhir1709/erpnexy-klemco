# Feature A — list every File attached to a record (the "Documents" button), separate from the
# Connections tab. Mirrors the File query used by events/delivery_note.py::get_so_test_certificates.

import frappe
from frappe import _


@frappe.whitelist()
def list_document_files(doctype, name):
    """Return all File attachments for a given record (read-permission checked)."""
    if not doctype or not name:
        return []
    if not frappe.has_permission(doctype, "read", doc=name):
        frappe.throw(_("Not permitted to read {0} {1}").format(doctype, name), frappe.PermissionError)
    return frappe.get_all(
        "File",
        filters={"attached_to_doctype": doctype, "attached_to_name": name},
        fields=["file_name", "file_url", "file_size", "is_private", "owner", "creation"],
        order_by="creation desc",
    )
