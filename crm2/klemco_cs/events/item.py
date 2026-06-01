# Item server-side events — BRD v1.3
#   CR-18 / BR-KM-02  New KM-master items require TRIPLE approval before they can be enabled:
#                     CS Supervisor + KM Plant Head + Supply Chain Lead.

import frappe
from frappe import _

# approval field -> role allowed to grant it
KM_APPROVALS = (
    ("custom_km_approved_cs_supervisor", "CS Supervisor"),
    ("custom_km_approved_plant_head", "KM Plant Head"),
    ("custom_km_approved_supply_chain", "Supply Chain Lead"),
)


def validate(doc, method=None):
    if not doc.get("custom_km_managed"):
        doc.custom_km_approval_status = None
        return

    _enforce_role_for_each_approval(doc)

    all_approved = all(doc.get(field) for field, _role in KM_APPROVALS)
    doc.custom_km_approval_status = "Approved" if all_approved else "Pending Approvals"

    # A KM-managed item may not be Active (disabled = 0) until all three approve.
    if not all_approved and not doc.get("disabled"):
        frappe.throw(_(
            "KM-managed Item requires triple approval — CS Supervisor + KM Plant Head + "
            "Supply Chain Lead — before it can be enabled (BR-KM-02 / CR-18). Keep it "
            "'Disabled' until all three approvals are granted."
        ))


def _enforce_role_for_each_approval(doc):
    before = doc.get_doc_before_save()
    roles = set(frappe.get_roles())
    privileged = "System Manager" in roles

    for field, role in KM_APPROVALS:
        was = before.get(field) if before else 0
        now = doc.get(field)
        if now and not was and not privileged and role not in roles:
            frappe.throw(_(
                "Only the {0} role can grant the '{0}' approval for KM-managed items (BR-KM-02)."
            ).format(role))
