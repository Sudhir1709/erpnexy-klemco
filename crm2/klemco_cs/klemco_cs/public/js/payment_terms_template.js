// Payment Terms Template — klemco simplification.
// The stock section confuses CS/accounts users (a master-link column, discount
// block and advanced fields — property setters already hide those). Here we make
// a new template usable immediately: pre-seed one term at 100% of the invoice due
// "Day(s) after invoice date", so the user only sets Credit Days (e.g. 30).
frappe.ui.form.on('Payment Terms Template', {
    refresh: seed_default_term,
    onload: seed_default_term,
});

function seed_default_term(frm) {
    if (!frm.is_new()) return;
    if ((frm.doc.terms || []).length) return;
    const row = frm.add_child('terms');
    row.invoice_portion = 100;
    row.due_date_based_on = 'Day(s) after invoice date';
    frm.refresh_field('terms');
    frm.set_intro(
        __('Set the % of the invoice due and after how many days it is payable. ' +
           'For a simple template, keep one row at 100% and enter the Credit Days.'),
        'blue'
    );
}
