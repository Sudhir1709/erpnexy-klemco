# Technical Data Sheet (TDS) pack — merge the datasheets of a quotation's items (plus the company
# standard datasheet) into one downloadable PDF. Each Item carries its TDS PDF in cs_tds_file; the
# company-wide standard datasheet is Company.cs_standard_datasheet.

import io
import frappe
from frappe import _


def _file_bytes(file_url):
    if not file_url:
        return None
    try:
        name = frappe.db.get_value("File", {"file_url": file_url}, "name")
        if not name:
            return None
        # read the raw PDF bytes from disk (File.get_content() may decode a binary file as text)
        path = frappe.get_doc("File", name).get_full_path()
        with open(path, "rb") as fh:
            return fh.read()
    except Exception:
        frappe.log_error(frappe.get_traceback(), "Klemco TDS file read failed")
    return None


@frappe.whitelist()
def tds_available(quotation):
    """True if there's any TDS to merge — company standard datasheet, a line's TDS, or an item's
    master TDS — so the client can auto-show the 'Download TDS Pack' button with no checkbox."""
    if not quotation or not frappe.has_permission("Quotation", "read", doc=quotation):
        return False
    doc = frappe.get_doc("Quotation", quotation)
    if frappe.db.get_value("Company", doc.company, "cs_standard_datasheet"):
        return True
    for it in doc.items:
        if it.get("cs_tds_file"):
            return True
        if it.item_code and frappe.db.get_value("Item", it.item_code, "cs_tds_file"):
            return True
    return False


@frappe.whitelist()
def download_tds_pack(quotation):
    """Merge the company standard datasheet + each quotation item's TDS PDF into one PDF download."""
    if not frappe.has_permission("Quotation", "read", doc=quotation):
        frappe.throw(_("Not permitted to read Quotation {0}").format(quotation), frappe.PermissionError)
    doc = frappe.get_doc("Quotation", quotation)

    urls = []
    std = frappe.db.get_value("Company", doc.company, "cs_standard_datasheet")
    if std:
        urls.append(std)
    for it in doc.items:
        # Prefer a TDS attached to this quotation line; else fall back to the Item master's TDS.
        f = it.get("cs_tds_file") or (it.item_code and frappe.db.get_value("Item", it.item_code, "cs_tds_file"))
        if f and f not in urls:   # dedupe by file URL
            urls.append(f)

    from pypdf import PdfWriter, PdfReader
    writer = PdfWriter()
    added = 0
    for url in urls:
        content = _file_bytes(url)
        if not content:
            continue
        try:
            for page in PdfReader(io.BytesIO(content)).pages:
                writer.add_page(page)
            added += 1
        except Exception:
            frappe.log_error(frappe.get_traceback(), "Klemco TDS merge: bad PDF {0}".format(url))

    if not added:
        frappe.throw(_(
            "No Technical Data Sheets found for this quotation's items. Upload a TDS PDF on the "
            "Item master (Technical Data Sheet field), or set the company standard datasheet."
        ))

    buf = io.BytesIO()
    writer.write(buf)
    frappe.local.response.filename = "TDS-{0}.pdf".format(quotation)
    frappe.local.response.filecontent = buf.getvalue()
    frappe.local.response.type = "download"
