// Item — Klemco CS client script (BRD v1.3)
//   CR-18 / BR-KM-02  KM-managed items: show the triple-approval progress and gate each check
//                     so only the matching role can grant its approval.

const KM_APPROVALS = [
    { field: 'custom_km_approved_cs_supervisor', role: 'CS Supervisor', label: 'CS Supervisor' },
    { field: 'custom_km_approved_plant_head', role: 'KM Plant Head', label: 'KM Plant Head' },
    { field: 'custom_km_approved_supply_chain', role: 'Supply Chain Lead', label: 'Supply Chain Lead' },
];

frappe.ui.form.on('Item', {
    refresh(frm) {
        if (!frm.doc.custom_km_managed) return;

        const roles = frappe.user_roles || [];
        // Only let a user tick the approval that matches their role.
        KM_APPROVALS.forEach(a => {
            const allowed = roles.includes(a.role) || roles.includes('System Manager');
            frm.set_df_property(a.field, 'read_only', allowed ? 0 : 1);
        });

        const done = KM_APPROVALS.filter(a => frm.doc[a.field]).map(a => a.label);
        const pending = KM_APPROVALS.filter(a => !frm.doc[a.field]).map(a => a.label);
        if (pending.length) {
            frm.dashboard.set_headline_alert(
                __('KM item triple approval pending: {0}. Approved: {1}.',
                   [pending.join(', '), done.join(', ') || '—']),
                'orange'
            );
        } else {
            frm.dashboard.set_headline_alert(__('KM item fully approved (CS Supervisor + KM Plant Head + Supply Chain Lead).'), 'green');
        }
    },

    custom_km_managed(frm) {
        frm.refresh();
    },
});
