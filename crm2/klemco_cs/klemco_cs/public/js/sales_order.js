// Sales Order — Klemco CS client script (BRD v1.3)
//   CR-09  Required Delivery Date picker bounded to today onwards
//   CR-10  RC Conditional Deviation — Sales Head approve/reject buttons + banner
//   CR-11  "Create KM Order" guided review from the SO
//   CR-14  Preferred 3PL "Others" note hint

frappe.ui.form.on('Sales Order', {
    refresh(frm) {
        _bound_delivery_dates(frm);
        _toggle_3pl_note(frm);
        _deviation_ui(frm);
        _connections_prefill(frm);

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
    },

    onload(frm) {
        _bound_delivery_dates(frm);
        _toggle_3pl_note(frm);
        _connections_prefill(frm);
    },

    custom_preferred_3pl(frm) {
        _toggle_3pl_note(frm);
    },

    validate(frm) {
        _client_validate_dates(frm);
    },
});

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

// CR-10 — surface deviation status and give the Sales Head an inline decision.
function _deviation_ui(frm) {
    if (!frm.doc.custom_rc_deviation) return;

    const status = frm.doc.custom_deviation_approval_status;
    const colour = status === 'Approved' ? 'green' : (status === 'Rejected' ? 'red' : 'orange');
    frm.dashboard.set_headline_alert(
        __('RC Conditional Deviation — discount applied on a Rate Contract customer. Status: {0}', [status]),
        colour
    );

    const is_sales_head = (frappe.user_roles || []).some(r => ['Sales Head', 'System Manager'].includes(r));
    if (is_sales_head && status === 'Pending Sales Head Approval') {
        frm.add_custom_button(__('Approve Deviation'), () => _decide(frm, 'Approved'), __('Deviation'));
        frm.add_custom_button(__('Reject Deviation'), () => _decide(frm, 'Rejected'), __('Deviation'));
    }
}

function _decide(frm, decision) {
    frappe.call({
        method: 'klemco_cs.events.sales_order.set_deviation_decision',
        args: { sales_order: frm.doc.name, decision: decision },
        freeze: true,
        callback: () => {
            frappe.show_alert({ message: __('Deviation {0}', [decision]), indicator: 'blue' });
            frm.reload_doc();
        },
    });
}
