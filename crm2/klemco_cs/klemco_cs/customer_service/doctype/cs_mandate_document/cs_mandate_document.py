# CS Mandate Document — one customer-mandated file (PO copy / test cert / client order
# confirmation / other) attached to a Sales Order. A child row so an order can carry many files.
import frappe
from frappe.model.document import Document


class CSMandateDocument(Document):
    pass
