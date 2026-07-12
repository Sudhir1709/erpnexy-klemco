// Payment Terms Template — klemco simplification.
// The stock section confuses CS/accounts users (a master-link column, discount
// block and advanced fields — property setters already hide those). Here we make
// a new template usable immediately: pre-seed one term at 100% of the invoice due
// "Day(s) after invoice date", so the user only sets Credit Days (e.g. 30).
frappe.ui.form.on('Payment Terms Template', {
    refresh: seed_default_term,
});

frappe.ui.form.on('Payment Terms Template Detail', {
    // The due date auto-picks the "days after invoice date" basis as soon as Credit
    // Days is entered — the user only supplies the number of days. A blank portion
    // fills to the whole invoice (100%). (Server before_validate is the safety net.)
    credit_days(frm, cdt, cdn) {
        const row = locals[cdt][cdn];
        if (row.credit_days && !row.due_date_based_on) {
            frappe.model.set_value(cdt, cdn, 'due_date_based_on', 'Day(s) after invoice date');
        }
        if (!row.invoice_portion) {
            frappe.model.set_value(cdt, cdn, 'invoice_portion', 100);
        }
    },
});

function seed_default_term(frm) {
    if (!frm.is_new()) return;
    if ((frm.doc.terms || []).length) return;
    // invoice_portion defaults to 100 at the field level (Property Setter), so the
    // new row is already at 100% — we only default the due-date basis here.
    const row = frm.add_child('terms', {due_date_based_on: 'Day(s) after invoice date'});
    frm.refresh_field('terms');
    frm.set_intro(
        __('Set the % of the invoice due and after how many days it is payable. ' +
           'For a simple template, keep one row at 100% and enter the Credit Days.'),
        'blue'
    );
}
