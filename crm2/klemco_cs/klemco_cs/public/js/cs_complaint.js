// CS Complaint — Client Script
// BRD §8: Algorithm-suggested assignment (FR-8-11, CR-07), SLA display (FR-8-04)

const ROUTING = [
    {type: 'Product — Quality / Damage',     dept: 'QC Head',           sla: '48h'},
    {type: 'Product — Short Delivery',       dept: 'Supply Chain Lead', sla: '48h'},
    {type: 'Non-Product — Delivery Delay',   dept: 'Supply Chain Lead', sla: '72h'},
    {type: 'Non-Product — Billing / Invoice',dept: 'Finance Lead',      sla: '72h'},
    {type: 'Non-Product — Service',          dept: 'CS Manager',        sla: '72h'},
];

const SLA_HOURS = {Critical: 24, High: 48, Medium: 48, Low: 72};

frappe.ui.form.on('CS Complaint', {

    refresh(frm) {
        render_routing_table(frm);
        render_sla_banner(frm);

        if (frm.is_new()) {
            frm.set_intro(
                'Select the complaint type — the system will auto-suggest the correct assignee based on the routing table.', 'blue');
        }
        if (frm.doc.status === 'Closed') {
            frm.set_intro('Complaint closed. CSAT survey has been triggered.', 'green');
        }
    },

    complaint_type(frm) {
        suggest_assignee(frm);
        update_sla_label(frm);
    },

    priority(frm) {
        update_sla_label(frm);
    },

    assigned_to(frm) {
        if (frm.doc.algorithm_suggested && frm.doc.assigned_to
                && !frm.doc.assigned_to.includes(frm.doc.algorithm_suggested)) {
            frm.set_df_property('override_reason', 'reqd', 1);
            frm.set_df_property('override_reason', 'description',
                'You are overriding the algorithm suggestion. Provide a reason (BR-CM06).');
        } else {
            frm.set_df_property('override_reason', 'reqd', 0);
            frm.set_df_property('override_reason', 'description', '');
        }
    }
});

// Match on ASCII keywords (not the em-dash literal) so it is immune to JS-asset
// character-encoding differences when the static file is served.
function dept_for(complaint_type) {
    const t = (complaint_type || '').toLowerCase();
    if (t.includes('quality') || t.includes('damage')) return 'QC Head';
    if (t.includes('short delivery')) return 'Supply Chain Lead';
    if (t.includes('delivery delay')) return 'Supply Chain Lead';
    if (t.includes('billing') || t.includes('invoice')) return 'Finance Lead';
    return 'CS Manager';  // Service / Other
}

function suggest_assignee(frm) {
    if (!frm.doc.complaint_type) return;
    const dept = dept_for(frm.doc.complaint_type);
    frm.set_value('algorithm_suggested', dept);
    frm.set_df_property('assigned_to', 'description',
        'Auto-suggested: ' + dept + ' (based on complaint type routing)');
    frappe.show_alert({message: 'Suggested assignee: ' + dept, indicator: 'blue'}, 4);
}

function update_sla_label(frm) {
    const hours = SLA_HOURS[frm.doc.priority] || 48;
    frm.set_df_property('sla_hours_total', 'description',
        hours + 'h SLA based on ' + (frm.doc.priority || 'Medium') + ' priority');
}

function render_sla_banner(frm) {
    if (frm.is_new() || !frm.doc.sla_deadline) return;

    const deadline  = moment(frm.doc.sla_deadline);
    const now       = moment();
    const total_h   = frm.doc.sla_hours_total || 48;
    const elapsed_h = now.diff(moment(frm.doc.creation), 'hours', true);
    const pct       = Math.min(100, Math.round((elapsed_h / total_h) * 100));
    const remaining = deadline.diff(now, 'hours', true);

    let color = '#27AE60', label = 'On Track';
    if      (pct >= 80) { color = '#C0392B'; label = 'SLA Breach Risk'; }
    else if (pct >= 50) { color = '#E67E22'; label = 'At Risk';          }

    const rem_str = remaining > 0
        ? remaining.toFixed(1) + 'h remaining'
        : Math.abs(remaining).toFixed(1) + 'h overdue';

    const html = [
        '<div style="background:#f8fafc;border:1px solid #ddd;border-radius:6px;padding:12px 16px;margin-bottom:12px;">',
        '<div style="display:flex;justify-content:space-between;margin-bottom:6px;">',
        '<span style="font-weight:600;font-size:13px;">SLA Status: <span style="color:' + color + '">' + label + '</span></span>',
        '<span style="font-size:12px;color:#888;">' + rem_str + ' &nbsp;·&nbsp; Deadline: ' + deadline.format('DD MMM YYYY, h:mm A') + '</span>',
        '</div>',
        '<div style="height:8px;background:#e0e0e0;border-radius:4px;overflow:hidden;">',
        '<div style="height:100%;width:' + pct + '%;background:' + color + ';border-radius:4px;"></div>',
        '</div>',
        '<div style="font-size:11px;color:#888;margin-top:4px;">' + pct + '% of SLA used (' + elapsed_h.toFixed(1) + 'h / ' + total_h + 'h)</div>',
        '</div>'
    ].join('');

    const target = frm.fields_dict['complaint_type'] && frm.fields_dict['complaint_type'].$wrapper;
    if (target && !frm._sla_banner) {
        frm._sla_banner = $(html).insertBefore(target.closest('.form-section'));
    }
}

function render_routing_table(frm) {
    const rows = ROUTING.map(function(r, i) {
        const bg = i % 2 === 0 ? '#fff' : '#F0F8FF';
        return '<tr style="background:' + bg + '">'
            + '<td style="padding:5px 10px;color:#1C2833;">' + r.type + '</td>'
            + '<td style="padding:5px 10px;font-weight:600;color:#1A5276;">' + r.dept + '</td>'
            + '<td style="padding:5px 10px;color:#27AE60;font-weight:600;">' + r.sla + '</td>'
            + '</tr>';
    }).join('');

    const html = [
        '<div style="background:#EBF5FB;border:1px solid #A8D8EA;border-radius:6px;padding:12px 16px;margin-top:8px;">',
        '<div style="font-weight:700;font-size:12px;color:#1A5276;margin-bottom:8px;text-transform:uppercase;letter-spacing:.5px;">',
        'Complaint Routing Logic (auto-assignment rules)',
        '</div>',
        '<table style="width:100%;font-size:12px;border-collapse:collapse;">',
        '<thead><tr style="background:#D6EAF8;">',
        '<th style="padding:6px 10px;text-align:left;">Complaint Type</th>',
        '<th style="padding:6px 10px;text-align:left;">Assigned To</th>',
        '<th style="padding:6px 10px;text-align:left;">SLA</th>',
        '</tr></thead>',
        '<tbody>' + rows + '</tbody>',
        '</table></div>'
    ].join('');

    const field = frm.get_field('algorithm_suggested');
    if (field && field.$wrapper && !frm._routing_table) {
        frm._routing_table = $(html).insertAfter(field.$wrapper);
    }
}
