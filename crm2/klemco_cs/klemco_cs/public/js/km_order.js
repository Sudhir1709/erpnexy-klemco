// KM Order — client script (FR-KM-08 guided review)
frappe.ui.form.on('KM Order', {
    refresh(frm) {
        if (frm.doc.linked_sales_order) {
            frm.add_custom_button(__('View Full SO'), () => {
                frappe.set_route('Form', 'Sales Order', frm.doc.linked_sales_order);
            });
        }
        _stage_button(frm);
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

    linked_sales_order(frm) {
        // Auto-fill the customer + items from the chosen Sales Order (FR-KM-08),
        // mirroring the server-side make_km_order mapper. so_qty is the read-only SO
        // reference; km_qty defaults to it for the CS reviewer to edit.
        if (!frm.doc.linked_sales_order) return;

        const pull = () => {
            frappe.db.get_doc('Sales Order', frm.doc.linked_sales_order).then(so => {
                if (so.customer) frm.set_value('customer', so.customer);
                frm.clear_table('items');
                (so.items || []).forEach(it => {
                    const row = frm.add_child('items');
                    row.item_code = it.item_code;
                    row.item_name = it.item_name;
                    row.so_qty = it.qty;
                    row.km_qty = it.qty;
                    row.uom = it.uom;
                    row.matches_so = 1;
                });
                frm.refresh_field('items');
                _flag_mismatches(frm);
                frappe.show_alert(
                    {message: __('Pulled {0} item(s) from {1}', [(so.items || []).length, so.name]), indicator: 'green'}, 5);
            });
        };

        const has_rows = (frm.doc.items || []).some(r => r.item_code);
        if (has_rows) {
            frappe.confirm(
                __('Replace the current items with the linked Sales Order\'s items?'),
                pull,
                () => {}  // keep existing items
            );
        } else {
            pull();
        }
    },
});

frappe.ui.form.on('KM Order Item', {
    km_qty(frm, cdt, cdn) {
        const row = locals[cdt][cdn];
        frappe.model.set_value(cdt, cdn, 'matches_so', (row.km_qty === row.so_qty) ? 1 : 0);
        _flag_mismatches(frm);
    },
});

// Guided production lifecycle — one forward button for the next stage on a submitted order.
// The Status field is read-only, so this is the only way to advance a KM Order through
// In Production → Inward Complete → Transfer Billing Done (server enforces forward-only + roles).
function _stage_button(frm) {
    if (frm.doc.docstatus !== 1) return;
    const NEXT = {
        'KM Confirmed':   ['In Production',        __('Start Production')],
        'In Production':  ['Inward Complete',      __('Mark Inward Complete')],
        'Inward Complete':['Transfer Billing Done', __('Mark Transfer & Billing Done')],
    };
    const step = NEXT[frm.doc.status];
    if (!step) return;  // final stage or cancelled — nothing to advance
    const [next, label] = step;
    frm.add_custom_button(label, () => {
        frappe.confirm(__('Move this Klemco Order to "{0}"?', [next]), () => {
            frappe.call({
                method: 'klemco_cs.customer_service.doctype.km_order.km_order.advance_status',
                args: { km_order: frm.doc.name, to_status: next },
                freeze: true,
                callback: () => {
                    frappe.show_alert({ message: __('Production status: {0}', [next]), indicator: 'green' }, 5);
                    frm.reload_doc();
                },
            });
        });
    });
}

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
