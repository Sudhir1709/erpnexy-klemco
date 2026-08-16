// Quotation list — show the discount-approval state in the Status column instead of a plain "Draft".
// Wraps (doesn't replace) ERPNext's list settings; klemco_cs loads after erpnext so this runs last.
(() => {
    const orig = frappe.listview_settings['Quotation'] || {};
    frappe.listview_settings['Quotation'] = Object.assign({}, orig, {
        add_fields: [...(orig.add_fields || []), 'cs_discount_approval_status'],
        get_indicator(doc) {
            if (doc.cs_discount_approval_status === 'Discount Approval — Sales Head') {
                return [__('Pending Discount Approval'), 'orange',
                    'cs_discount_approval_status,=,Discount Approval — Sales Head'];
            }
            if (doc.cs_discount_approval_status === 'Rejected') {
                return [__('Discount Rejected'), 'red', 'cs_discount_approval_status,=,Rejected'];
            }
            return orig.get_indicator ? orig.get_indicator(doc) : undefined;
        },
    });
})();
