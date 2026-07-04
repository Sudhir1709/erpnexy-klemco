// KM Order — client script (FR-KM-08 guided review)
frappe.ui.form.on('KM Order', {
    refresh(frm) {
        if (frm.doc.linked_sales_order) {
            frm.add_custom_button(__('View Full SO'), () => {
                frappe.set_route('Form', 'Sales Order', frm.doc.linked_sales_order);
            });
        }
        if (frm.is_new()) {
            const intro = frm.doc.linked_sales_order
                ? __('Review the SO items and quantities below, then submit to "Confirm & Create KM Order" (FR-KM-08).')
                : __('Standalone Klemco Order: select the customer and add items, then submit to "Confirm & Create KM Order". Optionally link a parent Sales Order to pull its items.');
            frm.set_intro(intro, 'orange');
        }
        _flag_mismatches(frm);
    },

    validate(frm) {
        _flag_mismatches(frm);
    },
});

frappe.ui.form.on('KM Order Item', {
    km_qty(frm, cdt, cdn) {
        const row = locals[cdt][cdn];
        frappe.model.set_value(cdt, cdn, 'matches_so', (row.km_qty === row.so_qty) ? 1 : 0);
        _flag_mismatches(frm);
    },
});

function _flag_mismatches(frm) {
    // Only meaningful when the KM order was mapped from a parent Sales Order.
    if (!frm.doc.linked_sales_order) return;
    const mismatched = (frm.doc.items || []).filter(r => (r.km_qty || 0) !== (r.so_qty || 0));
    if (mismatched.length) {
        frm.dashboard.clear_comment();
        frm.dashboard.set_headline_alert(
            __('{0} line(s) differ from the SO quantity — confirm this is intentional before creating the KM order.',
               [mismatched.length]),
            'orange'
        );
    }
}
