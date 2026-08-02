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
        if (frm.doc.customer) {
            frm.add_custom_button(__('New Delivery Address'), () => _new_delivery_address(frm), __('Create'));
        }
        if (!frm.is_new()) {
            frm.add_custom_button(__('Proforma Invoice'), () => _open_proforma(frm, 'Proforma Invoice (Sales Invoice)'));
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

// Create a new Shipping address for the customer (quick-entry) and set it on this invoice.
// Open the print view of this document with the given (Proforma) print format preselected.
function _open_proforma(frm, format_name) {
    const url = '/printview?doctype=' + encodeURIComponent(frm.doctype) +
        '&name=' + encodeURIComponent(frm.doc.name) +
        '&format=' + encodeURIComponent(format_name) + '&no_letterhead=0';
    window.open(url, '_blank');
}

function _new_delivery_address(frm) {
    frappe.ui.form.make_quick_entry(
        'Address',
        (addr) => {
            if (addr && addr.name) {
                frm.set_value('shipping_address_name', addr.name);
                frappe.show_alert({message: __('Delivery address {0} set.', [addr.name]), indicator: 'green'}, 5);
            }
        },
        null,
        {
            address_type: 'Shipping',
            is_shipping_address: 1,
            links: [{link_doctype: 'Customer', link_name: frm.doc.customer}],
        }
    );
}
