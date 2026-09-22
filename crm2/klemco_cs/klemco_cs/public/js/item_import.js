// Shared "Import Items" (Excel .xlsx / CSV) for Sales Order and Quotation.
//
// Loaded through hooks.doctype_js ahead of each doctype's own script, so it runs once per doctype
// Form (Frappe wraps the concatenated doctype script in its own function). It therefore only
// exports helpers on `window.klemco_item_import` — it must NOT register frappe.ui.form.on handlers
// itself (they would be registered once per doctype and fire twice). Each doctype script calls
// `klemco_item_import.setup(frm)` from its `refresh`.
//
// setup(frm) does two things on a draft document:
//   1. adds "Get Items From → Import Items";
//   2. re-routes the items grid's stock "Upload" button to the same importer. The stock button only
//      accepts .csv and needs Frappe's exact 7-row Download template — users who click it with an
//      Excel file got "skipped because of invalid file type";
//   3. re-routes the grid's "Download" button to a simple Excel template (Item Code / Qty / Rate /
//      Warehouse [/ Delivery Date] + a "How to" sheet) served by klemco_cs.item_import.download_template,
//      instead of Frappe's 7-row CSV bulk-edit template (which Upload still accepts).
// The file is uploaded as a File record, parsed server-side (klemco_cs.item_import.parse_items_file)
// and the rows are appended to `items`: Item Code (required), Qty (default 1), optional Rate /
// Warehouse / Delivery Date (only fields the child doctype actually has are set). The header may
// be on any row, and a file made from the grid's own Download button also works (its fieldname /
// help / "------" scaffold rows are skipped). Each row runs ERPNext's item_code handler, so Item
// Name / UOM / price-list rate are fetched on import (an imported Rate overrides the price list).
(function () {
    if (window.klemco_item_import) return;

    const ALLOWED_FILE_TYPES = ['.csv', '.xlsx'];   // legacy .xls can't be read server-side (openpyxl)

    function open_uploader(frm) {
        new frappe.ui.FileUploader({
            allow_multiple: false,
            restrictions: { allowed_file_types: ALLOWED_FILE_TYPES },
            on_success(file) {
                frappe.call({
                    method: 'klemco_cs.item_import.parse_items_file',
                    args: { file_url: file.file_url },
                    freeze: true,
                    freeze_message: __('Reading the file…'),
                    callback(r) { apply_rows(frm, r.message || []); },
                });
            },
        });
    }

    function add_button(frm) {
        frm.add_custom_button(__('Import Items'), () => open_uploader(frm), __('Get Items From'));
    }

    // The stock handler is bound once, directly on the button, when the grid is built (Grid.make →
    // setup_allow_bulk_edit), and the grid is never rebuilt for a live Form — so a single
    // .off('click').on('click') per button element is enough. The marker lives on the element, so a
    // brand-new Form (page reload) gets rebound by the next refresh.
    function bind_grid_upload(frm) {
        const grid = frm.fields_dict.items && frm.fields_dict.items.grid;
        if (!grid || !grid.wrapper) return;
        const $btn = $(grid.wrapper).find('.grid-upload');
        if (!$btn.length || $btn.data('klemcoImport')) return;
        $btn.data('klemcoImport', 1).off('click').on('click', (e) => {
            e.preventDefault();
            open_uploader(frm);
            return false;
        });
    }

    function bind_grid_download(frm) {
        const grid = frm.fields_dict.items && frm.fields_dict.items.grid;
        if (!grid || !grid.wrapper) return;
        const $btn = $(grid.wrapper).find('.grid-download');
        if (!$btn.length || $btn.data('klemcoImport')) return;
        $btn.data('klemcoImport', 1).off('click').on('click', (e) => {
            e.preventDefault();
            window.open('/api/method/klemco_cs.item_import.download_template?doctype='
                + encodeURIComponent(frm.doctype), '_blank');
            return false;
        });
    }

    function setup(frm) {
        if (frm.doc.docstatus !== 0) return;
        add_button(frm);
        bind_grid_upload(frm);
        bind_grid_download(frm);
    }

    // Normalise a spreadsheet date cell to YYYY-MM-DD: ISO datetime (real Excel date) → date part;
    // dd.mm.yyyy / dd-mm-yyyy / dd/mm/yyyy (day-first) → yyyy-mm-dd; yyyy-mm-dd passes through.
    function norm_date(v) {
        if (!v) return '';
        v = v.toString().trim();
        if (v.length >= 10 && v[10] === 'T') return v.slice(0, 10);
        const m = v.match(/^(\d{1,2})[.\-/](\d{1,2})[.\-/](\d{4})$/);
        if (m) return m[3] + '-' + m[2].padStart(2, '0') + '-' + m[1].padStart(2, '0');
        return v;   // yyyy-mm-dd or anything else — let ERPNext validate
    }

    // Exact labels win (the grid's Download template also carries "Price List Rate", "Stock Qty" …),
    // then a fuzzy match for hand-made sheets ("Quantity (Nos)", "Unit Price").
    const EXACT = {
        item: /^item ?code$|^item_code$|^item$/,
        qty: /^qty$|^quantity$/,
        rate: /^rate$/,
        wh: /^warehouse$/,
        dd: /^delivery ?date$|^delivery_date$/,
    };
    const FUZZY = {
        item: /item.?code/,
        qty: /qty|quantity/,
        rate: /rate|price/,
        wh: /warehouse/,
        dd: /delivery.?date/,
    };

    function find_columns(head) {
        const find = (key) => {
            let i = head.findIndex((h) => EXACT[key].test(h));
            if (i < 0) i = head.findIndex((h) => FUZZY[key].test(h));
            return i;
        };
        const item = find('item');
        if (item < 0) return null;
        return { item, qty: find('qty'), rate: find('rate'), wh: find('wh'), dd: find('dd') };
    }

    function apply_rows(frm, rows) {
        rows = rows || [];
        const norm = (r) => (r || []).map((h) => (h == null ? '' : h).toString().trim().toLowerCase());

        // Header = first row with an Item Code-like label (title / blank rows above are tolerated).
        let hIdx = -1, col = null;
        for (let i = 0; i < rows.length; i++) {
            col = find_columns(norm(rows[i]));
            if (col) { hIdx = i; break; }
        }
        if (hIdx < 0) {
            frappe.throw(__("The file needs an 'Item Code' column (plus Qty; Rate / Warehouse / Delivery Date optional)."));
        }

        // Frappe's grid "Download" template: labels row, then a fieldnames row, three help rows and a
        // "------" separator before the data starts.
        let start = hIdx + 1;
        if (norm(rows[hIdx + 1])[col.item] === 'item_code') start = hIdx + 6;

        const child_dt = frappe.meta.get_docfield(frm.doctype, 'items').options;
        const has = (fieldname) => frappe.meta.has_field(child_dt, fieldname);
        const cell = (r, i) => (i >= 0 && r[i] != null ? r[i].toString().trim() : '');

        const parsed = [];
        let skipped = 0;
        for (let i = start; i < rows.length; i++) {
            const r = rows[i] || [];
            const code = cell(r, col.item);
            if (!code) {
                if (r.some((v) => v != null && v.toString().trim())) skipped++;   // non-empty row, no item code
                continue;
            }
            parsed.push({
                item_code: code,
                qty: flt(cell(r, col.qty)) || 1,
                rate: cell(r, col.rate),
                warehouse: cell(r, col.wh),
                delivery_date: norm_date(cell(r, col.dd)),
            });
        }

        const toast = () => frappe.show_alert({
            message: parsed.length
                ? __('Imported {0} item(s){1}.',
                    [parsed.length, skipped ? __(' ({0} row(s) skipped — no item code)', [skipped]) : ''])
                : __("No item rows found under the 'Item Code' header — check the file{0}.",
                    [skipped ? __(' ({0} row(s) had no item code)', [skipped]) : '']),
            indicator: parsed.length ? 'green' : 'orange',
        }, 7);
        if (!parsed.length) { toast(); return; }

        // Drop the blank starter row a new document carries (and any other empty lines), so the
        // mandatory-Item-Code check doesn't block Save afterwards. Rows are otherwise appended.
        (frm.doc.items || []).filter((d) => !d.item_code)
            .forEach((d) => frappe.model.clear_doc(d.doctype, d.name));

        // Set item_code through frappe.model.set_value so ERPNext's own item_code handler runs and
        // fetches Item Name / UOM / conversion factor / price-list rate for the row — a plain
        // add_child + assignment leaves UOM empty and the mandatory check blocks Save. Rows go one
        // after another (each is a server call); an imported Rate is applied after the fetch so it
        // wins over the price list.
        frappe.dom.freeze(__('Importing {0} item(s)…', [parsed.length]));
        parsed.reduce((chain, p) => chain.then(() => {
            const c = frm.add_child('items');
            c.qty = p.qty;
            if (p.warehouse && has('warehouse')) c.warehouse = p.warehouse;
            return frappe.model.set_value(c.doctype, c.name, 'item_code', p.item_code).then(() => {
                // ERPNext's Sales Order item_code handler copies the header / first-row delivery date
                // onto the row, so the file's own date is assigned afterwards (plain assignment — the
                // delivery_date trigger would otherwise propagate it to every row).
                if (p.delivery_date && has('delivery_date')) c.delivery_date = p.delivery_date;
                if (p.rate) return frappe.model.set_value(c.doctype, c.name, 'rate', flt(p.rate));
            });
        }), Promise.resolve()).then(() => {
            frm.refresh_field('items');
            frm.dirty();
            toast();
        }).finally(() => frappe.dom.unfreeze());
    }

    window.klemco_item_import = { setup, open_uploader, apply_rows };
})();
