// Address — auto-fill the sales Zone from the State (live). Server validate is the backstop.
frappe.ui.form.on('Address', {
    refresh(frm) { _restrict_for_sales(frm); },
    gst_state(frm) { _fill_zone(frm); },
    state(frm) { if (!frm.doc.gst_state) _fill_zone(frm); },
});

// Sales-team users see only Customer Name + State when they OPEN a saved address (creating a new one
// is unaffected, so they can still add a ship-to). UI view-hide — hides every other field + surfaces
// the linked customer name in the form intro.
function _restrict_for_sales(frm) {
    if (frm.is_new()) return;
    if (!(window.klemcoIsSalesTeam && window.klemcoIsSalesTeam())) return;
    const keep = ['gst_state', 'state'];
    (frm.meta.fields || []).forEach((f) => {
        if (!keep.includes(f.fieldname)) frm.set_df_property(f.fieldname, 'hidden', 1);
    });
    frm.set_df_property('gst_state', 'read_only', 1);
    frm.set_df_property('state', 'read_only', 1);
    const st = frm.doc.gst_state || frm.doc.state || '-';
    const cust = (frm.doc.links || []).find((l) => l.link_doctype === 'Customer');
    const show = (name) => frm.set_intro(
        __('Customer: {0}   |   State: {1}', [name || frm.doc.address_title || '-', st]), 'blue');
    if (cust && cust.link_name) {
        frappe.db.get_value('Customer', cust.link_name, 'customer_name')
            .then((r) => show(r && r.message && r.message.customer_name));
    } else {
        show(null);
    }
}

function _fill_zone(frm) {
    if (frm.doc.zone) return;   // don't overwrite a manual choice
    const st = frm.doc.gst_state || frm.doc.state;
    if (!st) return;
    frappe.xcall('klemco_cs.events.address.zone_for_state', { state: st }).then((z) => {
        if (z && !frm.doc.zone) frm.set_value('zone', z);
    });
}
