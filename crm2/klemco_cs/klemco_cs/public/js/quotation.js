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
    },
});
