# Quotation server-side events.
from klemco_cs.events.pf import reconcile_pf
from klemco_cs.events.sales_order import _auto_gst_tax_category


def before_validate(doc, method=None):
    # Auto-GST: 18% split — In-State (CGST+SGST) or Out-State (IGST) from the delivery state.
    _auto_gst_tax_category(doc)
    # Optional Packaging & Forwarding charge (1.5% before tax, GST-inclusive) — after GST rows exist.
    reconcile_pf(doc)
