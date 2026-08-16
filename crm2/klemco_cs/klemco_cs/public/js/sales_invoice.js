// Sales Invoice — Klemco CS client script (BRD v1.3)
//   CR-13 / FR-DP-11  COD cheque capture is shown only for COD customers, after the invoice exists.

// Dispatch-documents checklist (goods invoices) — must match events/sales_invoice.py DISPATCH_CHECKLIST.
const DISPATCH_CHECKLIST = [
    ['Photos of boxes', 1], ['MTC for all parts', 1], ['Raw material MTC of all', 1],
    ['Traceability report', 1], ['E-way bill Part A', 1], ['Packaging List', 1],
    ['LR copy', 1], ['Weight Receipt', 1], ['Vehicle photo at dispatch', 0],
];

frappe.ui.form.on('Sales Invoice', {
    refresh(frm) {
        _cust_picker(frm);
        _seed_dispatch_ui(frm);
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
        // Dispatch-documents checklist reminder (goods invoices; rows seeded live once goods are added).
        if (frm.doc.docstatus === 0 && (frm.doc.cs_dispatch_documents || []).length
            && frm.doc.cs_dispatch_docs_status === 'Incomplete') {
            frm.dashboard.set_headline_alert(
                __('Dispatch documents incomplete — tick every required document (attach the file if you have it) before submitting.'),
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

    cs_add_pf(frm) { _pf_note(frm); },
    cs_pf_rate(frm) { _pf_note(frm); },

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

// Packaging & Forwarding is applied server-side on Save (it restructures the tax rows so GST is
// charged on it); nudge the user so they know to Save.
function _pf_note(frm) {
    if (frm.doc.cs_add_pf) {
        frappe.show_alert({message: __('Packaging & Forwarding ({0}%) will be added before tax when you Save.',
            [frm.doc.cs_pf_rate || 1.5]), indicator: 'blue'}, 5);
    }
}

// Attaching a file to a checklist row marks that document as Provided automatically.
frappe.ui.form.on('CS Dispatch Document', {
    file(frm, cdt, cdn) {
        const row = locals[cdt][cdn];
        if (row.file && !row.is_provided) {
            frappe.model.set_value(cdt, cdn, 'is_provided', 1);
        }
    },
});

// Seed the dispatch checklist live once the invoice has goods (a stock item) — before Save.
frappe.ui.form.on('Sales Invoice Item', {
    item_code(frm) { _seed_dispatch_ui(frm); },
});

function _seed_dispatch_ui(frm) {
    if (frm.doc.docstatus !== 0 || frm.doc.is_return || frm.doc.is_pos) return;
    if ((frm.doc.cs_dispatch_documents || []).length) return;   // already seeded — never duplicate
    const codes = [...new Set((frm.doc.items || []).map((i) => i.item_code).filter(Boolean))];
    if (!codes.length) return;
    frappe.db.get_list('Item', {
        filters: { name: ['in', codes], is_stock_item: 1 }, fields: ['name'], limit: 1,
    }).then((rows) => {
        if (!rows || !rows.length) return;                        // service-only invoice → no checklist
        if ((frm.doc.cs_dispatch_documents || []).length) return; // race guard
        DISPATCH_CHECKLIST.forEach(([document_name, mandatory]) => {
            frm.add_child('cs_dispatch_documents', { document_name, mandatory, is_provided: 0 });
        });
        frm.refresh_field('cs_dispatch_documents');
    });
}

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

// Sales-team users pick the customer from a "Name + State"-only list (klemcoIsSalesTeam from the bundle).
function _cust_picker(frm) {
    frm.set_query('customer', () =>
        (window.klemcoIsSalesTeam && window.klemcoIsSalesTeam())
            ? { query: 'klemco_cs.queries.customer_state_query' }
            : {});
}
