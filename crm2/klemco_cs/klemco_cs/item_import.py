# Parse an uploaded Excel (.xlsx) or CSV into rows for the Sales Order "Import Items" button, so a
# user can upload a plain spreadsheet of Item Code + Qty instead of the 7-row grid template.

import frappe
from frappe import _


@frappe.whitelist()
def parse_items_file(file_url):
    """Return the file's rows as a list of lists (first row = header). Supports .xlsx and .csv."""
    if not file_url:
        return []
    name = (file_url or "").lower()
    if name.endswith((".xlsx", ".xls")):
        from frappe.utils.xlsxutils import read_xlsx_file_from_attached_file
        return read_xlsx_file_from_attached_file(file_url=file_url)

    # CSV (or any text) — read the File's content and split.
    from frappe.utils.csvutils import read_csv_content
    fdoc = frappe.get_doc("File", {"file_url": file_url})
    content = fdoc.get_content()
    if isinstance(content, bytes):
        content = content.decode("utf-8-sig", errors="replace")
    return read_csv_content(content)
