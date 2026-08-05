// KM Order — client script (FR-KM-08 guided review)
frappe.ui.form.on('KM Order', {
    refresh(frm) {
        // Linked Sales Order picker shows only the entered customer's orders (when a customer is set;
        // otherwise all, so the link-first flow — which then fills the customer — still works).
        frm.set_query('linked_sales_order', () => ({
            filters: frm.doc.customer ? { customer: frm.doc.customer } : {},
        }));
        if (frm.doc.linked_sales_order) {
            frm.add_custom_button(__('View Full SO'), () => {
                frappe.set_route('Form', 'Sales Order', frm.doc.linked_sales_order);
            });
        }
        _stage_button(frm);
        _attachments_ui(frm);
        // Download the item lines as Excel.
        if (!frm.is_new()) {
            frm.add_custom_button(__('Download Items (Excel)'), () => {
                window.open('/api/method/klemco_cs.customer_service.doctype.km_order.km_order.download_items_excel?km_order='
                    + encodeURIComponent(frm.doc.name), '_blank');
            });
        }
        // Generate the KM order's purchase bill (Purchase Invoice at the item PURCHASE rate).
        if (frm.doc.docstatus === 1) {
            frm.add_custom_button(__('Generate Purchase Bill'), () => {
                frappe.model.open_mapped_doc({
                    method: 'klemco_cs.customer_service.doctype.km_order.km_order.make_purchase_bill',
                    frm: frm,
                });
            }, __('Create'));
        }
        if (frm.is_new()) {
            const intro = frm.doc.linked_sales_order
                ? __('Review the SO items and quantities below, then submit to "Confirm & Create Plant Order" (FR-KM-08).')
                : __('Standalone Plant Order: select the customer and add items, then submit to "Confirm & Create Plant Order". Optionally link a parent Sales Order to pull its items.');
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
                // Carry the SO's delivery date so the plant can plan production against it.
                if (so.delivery_date) frm.set_value('km_delivery_date', so.delivery_date);
                frm.clear_table('items');
                (so.items || []).forEach(it => {
                    const row = frm.add_child('items');
                    row.item_code = it.item_code;
                    row.item_name = it.item_name;
                    row.so_qty = it.qty;
                    row.km_qty = it.qty;
                    row.uom = it.uom;
                    row.delivery_date = it.delivery_date;  // per-line required date for planning
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
    // Stages only track status — the goods enter Finished Goods via the Generate Purchase Bill.
    const note = next === 'Transfer Billing Done'
        ? '<br><span class="text-muted">' + __('Generate the Purchase Bill to add the goods to Finished Goods at cost.') + '</span>'
        : '';
    frm.add_custom_button(label, () => {
        frappe.confirm(__('Move this Plant Order to "{0}"?', [next]) + note, () => {
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

// Attachments — "Upload Files" button: select several files at once; each is added as a row in
// the cs_attachments grid (any file type). Manual "Add Row" in the grid also works.
function _attachments_ui(frm) {
    frm.add_custom_button(__('Upload Files'), () => {
        new frappe.ui.FileUploader({
            allow_multiple: true,
            doctype: frm.doctype,
            docname: frm.docname,
            folder: 'Home/Attachments',
            on_success(file_doc) {
                frm.add_child('cs_attachments', { file: file_doc.file_url, title: file_doc.file_name });
                frm.refresh_field('cs_attachments');
                frm.dirty();
            },
        });
    }, __('Attachments'));
}

function _flag_mismatches(frm) {
    // Only meaningful when the KM order was mapped from a parent Sales Order.
    if (!frm.doc.linked_sales_order) return;
    const mismatched = (frm.doc.items || []).filter(r => (r.km_qty || 0) !== (r.so_qty || 0));
    if (mismatched.length) {
        frm.dashboard.clear_comment();
        frm.dashboard.set_headline_alert(
            __('{0} line(s) differ from the SO quantity — confirm this is intentional before creating the Plant Order.',
               [mismatched.length]),
            'orange'
        );
    }
}
