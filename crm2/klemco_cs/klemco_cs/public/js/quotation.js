// Quotation — Klemco CS client script.
// Proforma Invoice (advance/approval — not a tax invoice), printable from a saved quotation.
frappe.ui.form.on('Quotation', {
    refresh(frm) {
        if (!frm.is_new()) {
            frm.add_custom_button(__('Proforma Invoice'), () => {
                const url = '/printview?doctype=' + encodeURIComponent(frm.doctype) +
                    '&name=' + encodeURIComponent(frm.doc.name) +
                    '&format=' + encodeURIComponent('Proforma Invoice (Quotation)') + '&no_letterhead=0';
                window.open(url, '_blank');
            });
        }
        _sitc_ui(frm);
    },
    cs_project_type(frm) {
        _sitc_ui(frm);
    },
});

// SITC / Project quote: attach the BOQ + enter ONE lump-sum line instead of 30-40 rows. When the type
// is set to SITC and the grid is empty, drop in the ready-made "SITC Works (as per BOQ)" line so the
// salesperson only types the amount.
function _sitc_ui(frm) {
    if (frm.doc.cs_project_type !== 'SITC / Project') {
        frm.set_intro('');
        return;
    }
    frm.set_intro(__('SITC / Project quote — write the Scope of Work, attach the BOQ file, and enter the '
        + 'lump-sum amount on the "SITC Works" line below. No need to enter every BOQ item.'), 'blue');
    if (!(frm.doc.items || []).length) {
        const row = frm.add_child('items', { item_code: 'KL-SITC-001', qty: 1 });
        frm.script_manager.trigger('item_code', row.doctype, row.name);
        frm.refresh_field('items');
    }
}
