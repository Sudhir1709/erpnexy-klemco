// Address — auto-fill the sales Zone from the State (live). Server validate is the backstop.
frappe.ui.form.on('Address', {
    gst_state(frm) { _fill_zone(frm); },
    state(frm) { if (!frm.doc.gst_state) _fill_zone(frm); },
});

function _fill_zone(frm) {
    if (frm.doc.zone) return;   // don't overwrite a manual choice
    const st = frm.doc.gst_state || frm.doc.state;
    if (!st) return;
    frappe.xcall('klemco_cs.events.address.zone_for_state', { state: st }).then((z) => {
        if (z && !frm.doc.zone) frm.set_value('zone', z);
    });
}
