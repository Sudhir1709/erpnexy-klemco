// Sales Order — Klemco CS client script (BRD v1.3)
//   CR-09  Required Delivery Date picker bounded to today onwards
//   CR-10  RC Conditional Deviation — Sales Head approve/reject buttons + banner
//   CR-11  "Create KM Order" guided review from the SO
//   CR-14  Preferred 3PL "Others" note hint

frappe.ui.form.on('Sales Order', {
    refresh(frm) {
        _bound_delivery_dates(frm);
        _toggle_3pl_note(frm);
        _connections_prefill(frm);
        _cust_picker(frm);

        // CR-11: raise a KM Order after reviewing this SO (submitted orders only).
        if (frm.doc.docstatus === 1) {
            frm.add_custom_button(__('KM Order'), () => {
                frappe.model.open_mapped_doc({
                    method: 'klemco_cs.customer_service.doctype.km_order.km_order.make_km_order',
                    frm: frm,
                });
            }, __('Create'));
        }

        // Proforma Invoice (advance/approval — not a tax invoice). Printable from a saved order.
        if (!frm.is_new()) {
            frm.add_custom_button(__('Proforma Invoice'), () => _open_proforma(frm, 'Proforma Invoice'));
        }

        // Add a fresh delivery address (linked to the customer) without leaving the order,
        // and set it as this order's shipping address.
        if (frm.doc.customer) {
            frm.add_custom_button(__('New Delivery Address'), () => _new_delivery_address(frm), __('Create'));
        }

        _discount_approval_ui(frm);
        _credit_hold_ui(frm);
        _sitc_ui(frm);
        _km_production_ui(frm);
        _mandate_docs_ui(frm);
        _import_items_ui(frm);

        // Once billed, item lines are frozen — hide "Update Items" (server also blocks it).
        if ((frm.doc.per_billed || 0) > 0) {
            frm.remove_custom_button(__('Update Items'));
            frm.dashboard.add_comment(
                __('This order has been billed — item lines are locked.'), 'blue', true);
        }

        _colour_processed_rows(frm);
    },

    onload(frm) {
        _bound_delivery_dates(frm);
        _toggle_3pl_note(frm);
        _connections_prefill(frm);
    },

    custom_preferred_3pl(frm) {
        _toggle_3pl_note(frm);
    },

    cs_project_type(frm) {
        _sitc_ui(frm);
    },

    cs_add_pf(frm) { _pf_note(frm); },
    cs_pf_rate(frm) { _pf_note(frm); },

    validate(frm) {
        _client_validate_dates(frm);
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

// Import Items from a plain Excel (.xlsx) or CSV (Item Code + Qty, optional Rate / Warehouse /
// Delivery Date) — a friendly alternative to the native grid Upload, which needs the exact 7-row
// Download template. Rows are appended; Item Name / Rate fill server-side on Save.
function _import_items_ui(frm) {
    frm.add_custom_button(__('Import Items'), () => {
        new frappe.ui.FileUploader({
            allow_multiple: false,
            restrictions: { allowed_file_types: ['.csv', '.xlsx', '.xls'] },
            on_success(file) {
                frappe.call({
                    method: 'klemco_cs.item_import.parse_items_file',
                    args: { file_url: file.file_url },
                    freeze: true,
                    freeze_message: __('Reading the file…'),
                    callback(r) { _apply_item_rows(frm, r.message || []); },
                });
            },
        });
    }, __('Get Items From'));
}

// Normalise a spreadsheet date cell to YYYY-MM-DD: ISO datetime (real Excel date) → date part;
// dd.mm.yyyy / dd-mm-yyyy / dd/mm/yyyy (day-first) → yyyy-mm-dd; yyyy-mm-dd passes through.
function _norm_date(v) {
    if (!v) return '';
    v = v.toString().trim();
    if (v.length >= 10 && v[10] === 'T') return v.slice(0, 10);
    let m = v.match(/^(\d{1,2})[.\-/](\d{1,2})[.\-/](\d{4})$/);
    if (m) return m[3] + '-' + m[2].padStart(2, '0') + '-' + m[1].padStart(2, '0');
    return v;   // yyyy-mm-dd or anything else — let ERPNext validate
}

// Map header columns (Item Code / Qty / Rate / Warehouse / Delivery Date) and append a row per line.
// The header can be on any row (blank rows above it are tolerated); data starts on the next row.
function _apply_item_rows(frm, rows) {
    rows = rows || [];
    let hIdx = -1, col = null;
    for (let i = 0; i < rows.length; i++) {
        const head = (rows[i] || []).map((h) => (h == null ? '' : h).toString().trim().toLowerCase());
        const find = (re) => head.findIndex((h) => re.test(h));
        const item = find(/item.?code|^item$/);
        if (item >= 0) {
            hIdx = i;
            col = { item, qty: find(/qty|quantity/), rate: find(/rate|price/),
                    wh: find(/warehouse/), dd: find(/delivery.?date/) };
            break;
        }
    }
    if (hIdx < 0) {
        frappe.throw(__("The file needs an 'Item Code' column (plus Qty; Rate / Warehouse / Delivery Date optional)."));
    }
    const cell = (r, i) => (i >= 0 && r[i] != null ? r[i].toString().trim() : '');
    let added = 0, skipped = 0;
    for (let i = hIdx + 1; i < rows.length; i++) {
        const r = rows[i] || [];
        const code = cell(r, col.item);
        if (!code) {
            if (r.some((v) => v != null && v.toString().trim())) skipped++;   // non-empty row, no item code
            continue;
        }
        const c = frm.add_child('items');
        c.item_code = code;
        c.qty = flt(cell(r, col.qty)) || 1;
        if (cell(r, col.rate)) c.rate = flt(cell(r, col.rate));
        if (cell(r, col.wh)) c.warehouse = cell(r, col.wh);
        const dd = _norm_date(cell(r, col.dd));
        if (dd) c.delivery_date = dd;
        added++;
    }
    frm.refresh_field('items');
    frm.dirty();
    frappe.show_alert({
        message: __('Imported {0} item(s){1}. Save to fetch names/rates.',
            [added, skipped ? __(' ({0} row(s) skipped — no item code)', [skipped]) : '']),
        indicator: added ? 'green' : 'orange',
    }, 7);
}

// Mandate Documents — "Upload Documents" button: pick a Type once, then select several files at
// once; each uploaded file is added as a row in the cs_mandate_documents grid. (Manual "Add Row"
// in the grid still works for one-offs.)
function _mandate_docs_ui(frm) {
    frm.add_custom_button(__('Upload Documents'), () => {
        frappe.prompt(
            [{
                fieldname: 'document_type', label: __('Document Type'), fieldtype: 'Select', reqd: 1,
                options: ['Customer PO Copy', 'Test Certificate', 'Client Order Confirmation', 'Other'].join('\n'),
                default: 'Customer PO Copy',
            }],
            ({ document_type }) => {
                new frappe.ui.FileUploader({
                    allow_multiple: true,
                    doctype: frm.doctype,
                    docname: frm.docname,
                    folder: 'Home/Attachments',
                    on_success(file_doc) {
                        const row = frm.add_child('cs_mandate_documents', {
                            document_type, file: file_doc.file_url,
                        });
                        frm.refresh_field('cs_mandate_documents');
                        frm.dirty();
                    },
                });
            },
            __('Upload Documents'), __('Choose Files')
        );
    }, __('Documents'));
}

// SITC / Project order (usually carried from the quotation): drop in the ready-made lump-sum
// "SITC Works (as per BOQ)" line if the grid is empty, so the order needs no 30-40 BOQ rows.
function _sitc_ui(frm) {
    if (frm.doc.cs_project_type !== 'SITC / Project') return;
    frm.set_intro(__('SITC / Project order — the scope + BOQ carry from the quotation; the lump-sum is on '
        + 'the "SITC Works" line.'), 'blue');
    if (!(frm.doc.items || []).length) {
        const row = frm.add_child('items', { item_code: 'KL-SITC-001', qty: 1 });
        frm.script_manager.trigger('item_code', row.doctype, row.name);
        frm.refresh_field('items');
    }
}

frappe.ui.form.on('Sales Order Item', {
    items_add(frm) {
        _bound_delivery_dates(frm);
    },
});

// Connections tab "+" should pre-fill from THIS Sales Order (customer + items + rates), not open
// a near-blank form. Frappe's make_new() runs a mapper only when the doctype is in frm.make_methods
// (checked first) or custom_make_buttons; otherwise it copies just same-named link fields. ERPNext's
// SO defines no make_methods, so we wire the doctypes that have a clean SO mapper here. can_create
// still gates the "+" for submittable targets on a draft (so Delivery Note / Sales Invoice stay
// "submit first"); this only changes what happens once the "+" is actually clickable. Purchase Order
// / Work Order / Payment keep ERPNext's own dialog-based flows. Subcontracting Inward Order is left
// to ERPNext's default — its mapper only applies to subcontracting service items and errors otherwise.
function _connections_prefill(frm) {
    const map = (method) => () => frappe.model.open_mapped_doc({ method, frm });
    const P = 'erpnext.selling.doctype.sales_order.sales_order.';
    frm.make_methods = Object.assign({}, frm.make_methods, {
        'Delivery Note': map(P + 'make_delivery_note'),
        'Sales Invoice': map(P + 'make_sales_invoice'),
        'Pick List': map(P + 'create_pick_list'),
        'Material Request': map(P + 'make_material_request'),
        'Project': map(P + 'make_project'),
    });
}

// Show the linked Klemco (KM) Order production status right on the Sales Order — always live
// (queried each refresh), so you can see "under production" without opening the Connections tab.
// A single SO can spawn several KM Orders, so all are listed.
function _km_production_ui(frm) {
    if (frm.is_new()) return;
    const COLOR = {
        'Draft': 'gray', 'KM Confirmed': 'blue', 'In Production': 'orange',
        'Inward Complete': 'green', 'Transfer Billing Done': 'green', 'Cancelled': 'red',
    };
    frappe.db.get_list('KM Order', {
        filters: { linked_sales_order: frm.doc.name },
        fields: ['name', 'status'],
        order_by: 'creation',
        limit: 20,
    }).then(rows => {
        rows = (rows || []).filter(r => r.status !== 'Cancelled');
        if (!rows.length) return;
        const badges = rows.map(r => {
            const c = COLOR[r.status] || 'blue';
            return `<span class="indicator-pill ${c}" style="margin-right:8px;">`
                 + `${frappe.utils.escape_html(r.name)}: <b>${frappe.utils.escape_html(r.status)}</b></span>`;
        }).join('');
        frm.dashboard.set_headline_alert(
            `<span style="margin-right:6px;">🏭 Plant production:</span>${badges}`);
        // one-click open of the linked KM order(s)
        frm.add_custom_button(rows.length === 1 ? __('Klemco Order') : __('Klemco Orders'), () => {
            if (rows.length === 1) frappe.set_route('Form', 'KM Order', rows[0].name);
            else frappe.set_route('List', 'KM Order', { linked_sales_order: frm.doc.name });
        }, __('View'));
    });
}

// BR-OE-01 — Discount approval: when an over-cap discount is pending, show the status and
// (for Sales Head / Sales Manager) Approve / Reject buttons.
function _discount_approval_ui(frm) {
    if (frm.is_new()) return;
    if (frm.doc.cs_discount_approval_status !== 'Discount Approval — Sales Head') return;

    const max_disc = Math.max(0, ...(frm.doc.items || []).map(i => i.discount_percentage || 0));
    frm.dashboard.set_headline_alert(
        __('⏳ Discount {0}% pending Sales-Head approval (cap {1}%). Cannot be submitted until approved.',
           [max_disc.toFixed(1), frm.doc.cs_discount_threshold || 0]),
        'orange'
    );

    const roles = frappe.user_roles || [];
    const can_approve = roles.includes('Sales Head') || roles.includes('Sales Manager') || roles.includes('System Manager');
    if (!can_approve) return;

    const decide = (decision) => frappe.call({
        method: 'klemco_cs.events.sales_order.set_discount_decision',
        args: {sales_order: frm.doc.name, decision},
        callback() {
            frappe.show_alert({message: __('Discount {0}.', [decision]), indicator: decision === 'Approved' ? 'green' : 'red'}, 5);
            frm.reload_doc();
        },
    });
    frm.add_custom_button(__('Approve Discount'), () => decide('Approved'), __('Discount'));
    frm.add_custom_button(__('Reject Discount'), () => decide('Rejected'), __('Discount'));
}

// BR-OE-02 — Credit hold: show status + a Finance-only "Release Credit Hold" button.
function _credit_hold_ui(frm) {
    if (frm.is_new()) return;
    if (frm.doc.cs_credit_hold_status !== 'On Hold') return;

    frm.dashboard.set_headline_alert(
        __('🔴 Credit Hold — {0}', [frm.doc.cs_credit_hold_reason || 'Finance release required.']),
        'red'
    );

    const roles = frappe.user_roles || [];
    const is_finance = roles.includes('Accounts Manager') || roles.includes('System Manager');
    if (is_finance) {
        frm.add_custom_button(__('Release Credit Hold'), () => {
            frappe.confirm(__('Release the credit hold on this order?'), () => {
                frappe.call({
                    method: 'klemco_cs.events.sales_order.release_credit_hold',
                    args: {sales_order: frm.doc.name},
                    callback() {
                        frappe.show_alert({message: __('Credit hold released.'), indicator: 'green'}, 5);
                        frm.reload_doc();
                    },
                });
            });
        }, __('Credit'));
    }
}

// Create a new Shipping address for the customer via the quick-entry dialog, then set it
// as this order's Shipping Address. (You can also type a new name in the Shipping Address
// field itself and pick "Create a new Address".)
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

// Open the print view of the current doc with the Proforma Invoice format preselected.
function _open_proforma(frm, format_name) {
    const url = '/printview?doctype=' + encodeURIComponent(frm.doctype) +
        '&name=' + encodeURIComponent(frm.doc.name) +
        '&format=' + encodeURIComponent(format_name) + '&no_letterhead=0';
    window.open(url, '_blank');
}

// CR-14 — show + require the 3PL note only when "Others (not yet decided)" is chosen.
// (Done in JS instead of a declarative depends_on, which can't safely hold the parenthesised value.)
function _toggle_3pl_note(frm) {
    const others = frm.doc.custom_preferred_3pl === 'Others (not yet decided)';
    frm.set_df_property('custom_3pl_note', 'reqd', others ? 1 : 0);
    frm.set_df_property('custom_3pl_note', 'hidden', others ? 0 : 1);
}

// CR-09 — bound both the header and the per-line Required Delivery Date pickers to today.
function _bound_delivery_dates(frm) {
    // min_date must be a native Date object: Frappe's grid datepicker (AirDatepicker) calls
    // .getFullYear() on it, so a "YYYY-MM-DD" string throws and aborts the row's inline-edit
    // render — freezing Delivery Date / Required Delivery Date / Quantity. str_to_obj() returns
    // a native Date. (_client_validate_dates below keeps a string, for date-string comparison.)
    const today = frappe.datetime.str_to_obj(frappe.datetime.get_today());
    frm.set_df_property('delivery_date', 'min_date', today);
    const grid = frm.fields_dict.items && frm.fields_dict.items.grid;
    if (grid) {
        grid.update_docfield_property('delivery_date', 'min_date', today);
    }
}

function _client_validate_dates(frm) {
    const today = frappe.datetime.get_today();
    if (frm.doc.delivery_date && frm.doc.delivery_date < today) {
        frappe.throw(__('Delivery Date cannot be in the past (FR-SO-16).'));
    }
    (frm.doc.items || []).forEach(row => {
        if (row.delivery_date && row.delivery_date < today) {
            frappe.throw(__('Row #{0}: Required Delivery Date cannot be back-dated (FR-SO-16).', [row.idx]));
        }
    });
}

// Sales-team users pick the customer from a "Name + State"-only list (klemcoIsSalesTeam from the bundle).
function _cust_picker(frm) {
    frm.set_query('customer', () =>
        (window.klemcoIsSalesTeam && window.klemcoIsSalesTeam())
            ? { query: 'klemco_cs.queries.customer_state_query' }
            : {});
}

// One-time stylesheet that colours the grid CELLS (the visible area) for frozen/partial rows. Cells
// must be targeted (not the row's inner .data-row) with !important, else they cover the colour.
function _inject_freeze_css() {
    if (document.getElementById('klemco-freeze-css')) return;
    const s = document.createElement('style');
    s.id = 'klemco-freeze-css';
    s.textContent = `
      .grid-row.klemco-frozen  .grid-static-col { background-color:#dfe3e6 !important; color:#6c757d !important; }
      .grid-row.klemco-frozen  .grid-static-col a { color:#6c757d !important; }
      .grid-row.klemco-partial .grid-static-col { background-color:#fde7c9 !important; }`;
    (document.head || document.documentElement).appendChild(s);
}

// Colour item rows by fulfilment so "done" lines are visually frozen: fully delivered AND fully
// billed → grey (frozen); partly delivered or billed → amber (in progress). ERPNext already blocks
// reducing a billed line; this is the visual cue. Colours the row wrapper via a CSS class.
function _colour_processed_rows(frm) {
    _inject_freeze_css();
    const grid = frm.fields_dict.items && frm.fields_dict.items.grid;
    if (!grid || frm.is_new()) return;
    const paint = () => {
        let any_frozen = false;
        (grid.grid_rows || []).forEach((gr) => {
            const d = gr && gr.doc;
            if (!d || !gr.wrapper) return;
            const qty = flt(d.qty), del = flt(d.delivered_qty);
            const amt = flt(d.amount), bill = flt(d.billed_amt);
            const frozen = qty > 0 && del >= qty && amt > 0 && bill >= amt;
            const partial = !frozen && (del > 0 || bill > 0);
            if (frozen) any_frozen = true;
            gr.wrapper.toggleClass('klemco-frozen', frozen).toggleClass('klemco-partial', partial);
            const tip = frozen ? __('Delivered & invoiced — line frozen')
                : (partial ? __('Partially delivered / invoiced') : '');
            if (tip) { gr.wrapper.attr('title', tip); } else { gr.wrapper.removeAttr('title'); }
        });
        if (any_frozen && !frm._cs_freeze_legend) {
            frm._cs_freeze_legend = true;
            frm.dashboard.add_comment(
                __('Grey rows are delivered &amp; invoiced (frozen); amber rows are partially processed.'),
                'blue', true);
        }
    };
    paint();
    setTimeout(paint, 400);   // re-apply after the grid finishes rendering
}
