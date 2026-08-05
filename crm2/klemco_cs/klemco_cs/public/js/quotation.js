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
        _discount_ui(frm);
    },
    cs_project_type(frm) {
        _sitc_ui(frm);
    },
    cs_add_pf(frm) { _pf_note(frm); },
    cs_pf_rate(frm) { _pf_note(frm); },
});

// Discount over the matrix cap → Sales-Head approval banner + Approve/Reject actions.
function _discount_ui(frm) {
    if (frm.is_new()) return;
    if (frm.doc.cs_discount_approval_status !== 'Discount Approval — Sales Head') return;
    frm.dashboard.set_headline_alert(
        __('⏳ Discount pending Sales-Head approval (cap {0}%). This quotation cannot be submitted until approved.',
           [frm.doc.cs_discount_threshold || 0]), 'orange');
    const roles = frappe.user_roles || [];
    if (['Sales Head', 'Sales Manager', 'System Manager'].some((r) => roles.includes(r))) {
        frm.add_custom_button(__('Approve Discount'), () => _decide(frm, 'Approved'), __('Discount'));
        frm.add_custom_button(__('Reject Discount'), () => _decide(frm, 'Rejected'), __('Discount'));
    }
}
function _decide(frm, decision) {
    frappe.call({
        method: 'klemco_cs.events.quotation.set_discount_decision',
        args: { quotation: frm.doc.name, decision },
        freeze: true,
        callback: () => {
            frappe.show_alert({ message: __('Discount {0}', [decision]), indicator: 'green' }, 4);
            frm.reload_doc();
        },
    });
}

// Packaging & Forwarding is applied server-side on Save (it restructures the tax rows so GST is
// charged on it); nudge the user so they know to Save.
function _pf_note(frm) {
    if (frm.doc.cs_add_pf) {
        frappe.show_alert({message: __('Packaging & Forwarding ({0}%) will be added before tax when you Save.',
            [frm.doc.cs_pf_rate || 1.5]), indicator: 'blue'}, 5);
    }
}

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
