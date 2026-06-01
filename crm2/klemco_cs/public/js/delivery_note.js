// Delivery Note — Klemco CS client script (BRD v1.3)
//   CR-15 / FR-DP-12  Warehouse can download test certificates attached to the linked SO
//   CR-16             Delivery instructions (carried from SO) are visible on the Challan

frappe.ui.form.on('Delivery Note', {
    refresh(frm) {
        if (frm.is_new()) return;
        _render_test_certificates(frm);
    },
});

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
