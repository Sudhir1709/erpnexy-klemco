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

    update_stock(frm) {
        // Direct billing (no Delivery Note): when the user ticks "Update Stock" the
        // Set Source Warehouse field appears. Default it to the company's Finished Goods
        // warehouse so they aren't left with a blank picker; setting it cascades to the rows.
        if (!frm.doc.update_stock || frm.doc.set_warehouse || !frm.doc.company) return;
        frappe.db.get_list('Warehouse', {
            filters: {company: frm.doc.company, is_group: 0, warehouse_name: 'Finished Goods'},
            limit: 1,
        }).then((rows) => {
            const wh = rows && rows[0] && rows[0].name;
            if (wh) {
                frm.set_value('set_warehouse', wh);
                frappe.show_alert(
                    {message: __('Billing will reduce stock from {0} — change it if needed.', [wh]),
                     indicator: 'blue'}, 6);
            }
        });
    },
});
