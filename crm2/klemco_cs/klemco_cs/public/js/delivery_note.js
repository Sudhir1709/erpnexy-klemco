// Delivery Note — Klemco CS client script (BRD v1.3)
//   CR-15 / FR-DP-12  Warehouse can download test certificates attached to the linked SO
//   CR-16             Delivery instructions (carried from SO) are visible on the Challan

frappe.ui.form.on('Delivery Note', {
    refresh(frm) {
        _cust_picker(frm);
        if (frm.doc.customer) {
            frm.add_custom_button(__('New Delivery Address'), () => _new_delivery_address(frm), __('Create'));
        }
        if (frm.is_new()) return;
        frm.add_custom_button(__('Proforma Invoice'), () => _open_proforma(frm, 'Proforma Invoice (Delivery Note)'));
        _render_test_certificates(frm);
    },
});

// Open the print view of this document with the given (Proforma) print format preselected.
function _open_proforma(frm, format_name) {
    const url = '/printview?doctype=' + encodeURIComponent(frm.doctype) +
        '&name=' + encodeURIComponent(frm.doc.name) +
        '&format=' + encodeURIComponent(format_name) + '&no_letterhead=0';
    window.open(url, '_blank');
}

// Create a new Shipping address for the customer (quick-entry) and set it on this document.
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

function _render_test_certificates(frm) {
    frappe.call({
        method: 'klemco_cs.events.delivery_note.get_so_test_certificates',
        args: { delivery_note: frm.doc.name },
        callback: (r) => {
            const files = r.message || [];
            if (!files.length) return;

            const rows = files.map(f => `
                <div style="display:flex;justify-content:space-between;align-items:center;
                            border:1px solid #d5d8dc;border-radius:4px;padding:5px 9px;margin-bottom:5px;font-size:12px;">
                    <span>📄 ${frappe.utils.escape_html(f.file_name)}</span>
                    <a class="btn btn-default btn-xs" href="${f.file_url}" download target="_blank">⬇ Download</a>
                </div>`).join('');

            const html = `
                <div style="background:#FFFDF5;border:1px dashed #F39C12;border-radius:6px;padding:12px 14px;">
                    <div style="font-weight:700;color:#B07309;margin-bottom:8px;">
                        Test Certificates (from SO) — downloadable by warehouse (FR-DP-12)
                    </div>
                    ${rows}
                </div>`;

            frm.dashboard.add_section(html, __('Test Certificates'));
        },
    });
}

// Sales-team users pick the customer from a "Name + State"-only list (klemcoIsSalesTeam from the bundle).
function _cust_picker(frm) {
    frm.set_query('customer', () =>
        (window.klemcoIsSalesTeam && window.klemcoIsSalesTeam())
            ? { query: 'klemco_cs.queries.customer_state_query' }
            : {});
}
