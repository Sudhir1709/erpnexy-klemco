import frappe
from frappe.model.document import Document
from frappe.utils import now_datetime, add_to_date, get_datetime

SLA_HOURS = {'Critical': 24, 'High': 48, 'Medium': 48, 'Low': 72}
ROUTING = {
    'Product — Quality / Damage':      'QC Head',
    'Product — Short Delivery':        'Supply Chain Lead',
    'Non-Product — Billing / Invoice': 'Finance Lead',
    'Non-Product — Delivery Delay':    'Supply Chain Lead',
    'Non-Product — Service':           'CS Manager',
}

class CSComplaint(Document):
    def before_insert(self):
        self._set_sla()
        self._suggest_assignee()

    def validate(self):
        # Linked Sales Order is optional (UAT 01-Jul): a complaint can be logged
        # before an SO is identified. The algorithm suggestion is now advisory only
        # (it maps a complaint type to a department *title*, not to the assigned User),
        # so it no longer gates saving with a mandatory Override Reason.
        pass

    def on_update(self):
        self._update_elapsed()
        self._sync_assignment()
        if self.status == 'Closed' and not self.csat_survey_sent:
            self.db_set('csat_survey_sent', 1)
            frappe.msgprint(f'CSAT survey triggered for {self.name}', alert=True)
            from klemco_cs.notifications import complaint_closed_csat
            complaint_closed_csat(self)

    def _sync_assignment(self):
        """Mirror the business 'Assigned To' field into Frappe's ToDo assignment
        so the assignee sees the complaint in 'Assigned to Me' (UAT 12-Jul). The
        custom field stays the source of truth; setting/changing it keeps the
        framework assignment in sync. Best-effort — never blocks the save."""
        from frappe.desk.form.assign_to import add as _assign_add, remove as _assign_remove

        prev = self.get_doc_before_save()
        old = prev.assigned_to if prev else None
        new = self.assigned_to

        # on reassignment (or clearing), drop the previous auto-assignment
        if old and old != new:
            try:
                _assign_remove('CS Complaint', self.name, old, ignore_permissions=True)
            except Exception:
                pass

        if not new:
            return

        current = frappe.parse_json(self.get('_assign') or '[]')
        if new in current:
            return
        try:
            _assign_add({
                'assign_to': [new],
                'doctype': 'CS Complaint',
                'name': self.name,
                'description': f'Complaint {self.name} — {self.complaint_type} for {self.customer}',
            }, ignore_permissions=True)
        except Exception:
            frappe.log_error(frappe.get_traceback(), 'CS auto-assign failed')

    def _set_sla(self):
        hours = SLA_HOURS.get(self.priority, 48)
        self.sla_hours_total = hours
        self.sla_deadline = add_to_date(now_datetime(), hours=hours)

    def _suggest_assignee(self):
        self.algorithm_suggested = ROUTING.get(self.complaint_type, 'CS Manager')

    def _update_elapsed(self):
        if self.creation:
            diff = get_datetime() - get_datetime(self.creation)
            self.db_set('sla_hours_elapsed', round(diff.total_seconds() / 3600, 2), update_modified=False)


def escalate_overdue_complaints():
    overdue = frappe.db.get_all(
        'CS Complaint',
        filters={'status': ['not in', ['Closed', 'Escalated', 'Resolution Sent']]},
        fields=['name', 'sla_hours_total', 'creation']
    )
    escalated = []
    for c in overdue:
        total_h = c.sla_hours_total or 48
        elapsed_h = (get_datetime() - get_datetime(c.creation)).total_seconds() / 3600
        if elapsed_h / total_h >= 0.8:
            frappe.db.set_value('CS Complaint', c.name, 'status', 'Escalated')
            escalated.append(c.name)
    if overdue:
        frappe.db.commit()
    # notify CS Manager(s) of each freshly escalated complaint (FR-8.8)
    from klemco_cs.notifications import complaint_escalated
    for name in escalated:
        cust, ctype = frappe.db.get_value('CS Complaint', name, ['customer', 'complaint_type'])
        complaint_escalated(name, cust, ctype)
    return escalated
