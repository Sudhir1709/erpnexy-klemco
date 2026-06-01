// Sales Invoice — Klemco CS client script (BRD v1.3)
//   CR-13 / FR-DP-11  COD cheque capture is shown only for COD customers, after the invoice exists.

frappe.ui.form.on('Sales Invoice', {
    refresh(frm) {
        if (frm.doc.custom_is_cod && frm.doc.docstatus === 0) {
            frm.set_intro(
                __('COD customer — capture cheque details (No., Bank, Date, Amount) before submitting (FR-DP-11 / BR-DP-06).'),
                'orange'
            );
        }
    },

    customer(frm) {
        if (!frm.doc.customer) return;
        frappe.db.get_value('Customer', frm.doc.customer, 'custom_klemco_customer_type', (r) => {
            frm.set_value('custom_is_cod', (r && r.custom_klemco_customer_type === 'COD') ? 1 : 0);
        });
    },
});
