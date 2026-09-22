// Sales Enquiry — client script. Pre-Quotation capture; convert to a Quotation or close it.
frappe.ui.form.on('Sales Enquiry', {
    refresh(frm) {
        if (frm.is_new()) {
            frm.set_intro(__('Log the enquiry, then use "Create Quotation" to convert it — the '
                + 'Quotation number/value/date fill in here automatically. Close it if it does not convert.'),
                'blue');
            return;
        }
        const status = frm.doc.status;
        if (status === 'Open' || status === 'Quotation Created') {
            frm.add_custom_button(__('Create Quotation'), () => {
                frappe.model.open_mapped_doc({
                    method: 'klemco_cs.customer_service.doctype.sales_enquiry.sales_enquiry.make_quotation',
                    frm: frm,
                });
            }, __('Create'));
        }
        if (status === 'Open' || status === 'Quotation Created') {
            frm.add_custom_button(__('Close Enquiry'), () => {
                frappe.prompt(
                    { fieldname: 'reason', label: __('Reason it did not convert'), fieldtype: 'Small Text', reqd: 1 },
                    (v) => frappe.call({
                        method: 'klemco_cs.customer_service.doctype.sales_enquiry.sales_enquiry.close_enquiry',
                        args: { sales_enquiry: frm.doc.name, reason: v.reason },
                        freeze: true,
                        callback: () => {
                            frappe.show_alert({ message: __('Enquiry closed.'), indicator: 'orange' }, 4);
                            frm.reload_doc();
                        },
                    }),
                    __('Close Enquiry'), __('Close'));
            });
        }
        if (frm.doc.quotation) {
            frm.add_custom_button(__('View Quotation'), () => {
                frappe.set_route('Form', 'Quotation', frm.doc.quotation);
            });
        }
    },

    // Fill the Zone from the raiser's Sales Office when it's blank.
    raised_by(frm) {
        if (frm.doc.raised_by && !frm.doc.zone) {
            frappe.db.get_value('User', frm.doc.raised_by, 'cs_sales_office').then((r) => {
                const office = r && r.message && r.message.cs_sales_office;
                if (office && !frm.doc.zone) frm.set_value('zone', office);
            });
        }
    },
});
