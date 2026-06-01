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

        // CR-11: raise a KM Order after reviewing this SO (submitted orders only).
        if (frm.doc.docstatus === 1) {
            frm.add_custom_button(__('KM Order'), () => {
                frappe.model.open_mapped_doc({
                    method: 'klemco_cs.customer_service.doctype.km_order.km_order.make_km_order',
                    frm: frm,
                });
            }, __('Create'));
        }
    },

    onload(frm) {
        _bound_delivery_dates(frm);
        _toggle_3pl_note(frm);
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

// CR-14 — show + require the 3PL note only when "Others (not yet decided)" is chosen.
// (Done in JS instead of a declarative depends_on, which can't safely hold the parenthesised value.)
function _toggle_3pl_note(frm) {
    const others = frm.doc.custom_preferred_3pl === 'Others (not yet decided)';
    frm.set_df_property('custom_3pl_note', 'reqd', others ? 1 : 0);
    frm.set_df_property('custom_3pl_note', 'hidden', others ? 0 : 1);
}

// CR-09 — bound both the header and the per-line Required Delivery Date pickers to today.
function _bound_delivery_dates(frm) {
    const today = frappe.datetime.get_today();
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
