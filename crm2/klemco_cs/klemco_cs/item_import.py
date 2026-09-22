# Parse an uploaded Excel (.xlsx) or CSV into rows for the "Import Items" button on Sales Order and
# Quotation (public/js/item_import.js), so a user can upload a plain spreadsheet of Item Code + Qty
# instead of the grid's 7-row template. Column mapping happens client-side; this only returns rows.

import frappe
from frappe import _

MAX_ROWS = 5000   # same ceiling as Frappe's stock grid upload


@frappe.whitelist()
def parse_items_file(file_url):
    """Return the file's rows as a list of lists (header row included). Supports .xlsx and .csv.
    The File record must be readable by the caller — normally their own fresh upload."""
    if not file_url:
        return []
    lname = file_url.lower()
    if not lname.endswith((".csv", ".xlsx")):
        frappe.throw(_("Upload a .csv or .xlsx file (legacy .xls is not supported — save it as .xlsx)."))

    fdoc = _get_readable_file(file_url)
    if lname.endswith(".xlsx"):
        from frappe.utils.xlsxutils import read_xlsx_file_from_attached_file
        rows = read_xlsx_file_from_attached_file(filepath=fdoc.get_full_path())
    else:
        from frappe.utils.csvutils import read_csv_content
        content = fdoc.get_content()
        if isinstance(content, bytes):
            content = content.decode("utf-8-sig", errors="replace")
        rows = read_csv_content(content.lstrip("﻿"))

    rows = rows or []
    if len(rows) > MAX_ROWS:
        frappe.throw(_("Cannot import a file with more than {0} rows.").format(MAX_ROWS))
    return rows


def _get_readable_file(file_url):
    """One file_url can belong to several File records (content de-duplication) — return one the
    current user may read, else refuse. Stops a logged-in user reading arbitrary private files by URL."""
    for name in frappe.get_all("File", filters={"file_url": file_url}, pluck="name"):
        fdoc = frappe.get_doc("File", name)
        if fdoc.has_permission("read"):
            return fdoc
    frappe.throw(_("You do not have access to this file."), frappe.PermissionError)
