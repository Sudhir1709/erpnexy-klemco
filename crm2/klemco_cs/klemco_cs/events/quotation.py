# Quotation server-side events.
from klemco_cs.events.pf import reconcile_pf


def before_validate(doc, method=None):
    # Optional Packaging & Forwarding charge (1.5% before tax, GST-inclusive).
    reconcile_pf(doc)
