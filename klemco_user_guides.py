import frappe, json, uuid

frappe.init(site='mysite.localhost', sites_path='/home/frappe/frappe-bench/sites')
frappe.connect()
frappe.set_user('Administrator')

def uid():
    return uuid.uuid4().hex[:10]

def guide_blocks(title, intro, steps, tips):
    blocks = [
        {
            "id": uid(), "type": "header",
            "data": {"text": f"📘 {title}", "col": 12}
        },
        {
            "id": uid(), "type": "paragraph",
            "data": {"text": f"<p>{intro}</p>", "col": 12}
        },
        {
            "id": uid(), "type": "header",
            "data": {"text": "🚀 Quick Start Steps", "col": 12}
        },
        {
            "id": uid(), "type": "paragraph",
            "data": {
                "text": "<ol>" + "".join(f"<li><b>{s[0]}</b> — {s[1]}</li>" for s in steps) + "</ol>",
                "col": 12
            }
        },
        {
            "id": uid(), "type": "header",
            "data": {"text": "💡 Tips", "col": 12}
        },
        {
            "id": uid(), "type": "paragraph",
            "data": {
                "text": "<ul>" + "".join(f"<li>{t}</li>" for t in tips) + "</ul>",
                "col": 12
            }
        },
        {"id": uid(), "type": "spacer", "data": {"col": 12}},
    ]
    return blocks

guides = {
    "Selling": {
        "title": "Sales Department — User Guide",
        "intro": "Welcome to the Klemco India Sales workspace. You manage the complete order-to-dispatch cycle — from quotations to sales orders and delivery notes.",
        "steps": [
            ("Create a Lead", "Go to CRM → Lead → New. Fill in company name, contact, and source."),
            ("Convert to Opportunity", "Open the Lead → click 'Create Opportunity'. Set expected value and closing date."),
            ("Send a Quotation", "Opportunity → Create Quotation. Add Klemco items (KL-SC, KL-PH etc.), rates auto-fill from Standard Selling price list."),
            ("Confirm Sales Order", "Once customer approves → open Quotation → Create Sales Order. Submit it."),
            ("Create Delivery Note", "From Sales Order → Create Delivery Note when goods are dispatched."),
            ("Raise Sales Invoice", "From Delivery Note or Sales Order → Create Sales Invoice → Submit."),
        ],
        "tips": [
            "Always check stock availability before confirming a Sales Order.",
            "Use 'Standard Selling' price list — rates are pre-loaded for all KL-* items.",
            "Tag territory correctly (Amritsar, Mumbai, Hyderabad etc.) for region-wise reports.",
            "For service items (KL-SV-*), uncheck 'Delivery Required' in Sales Order.",
        ]
    },
    "CRM": {
        "title": "CRM Department — User Guide",
        "intro": "Welcome to the Klemco India CRM workspace. You manage prospects, leads, opportunities, and customer communications to grow the sales pipeline.",
        "steps": [
            ("Add a Lead", "CRM → Lead → New. Enter contact name, company, phone, and lead source (Exhibition, Website, Referral etc.)."),
            ("Qualify the Lead", "Set Lead Status to 'Open' → 'Interested' → 'Replied' as you follow up."),
            ("Create an Opportunity", "Lead → Create Opportunity. Set opportunity type (Sales), expected value, and next contact date."),
            ("Log a Call / Email", "Open Opportunity → Communication tab → Add a note or log a call for audit trail."),
            ("Win or Lost", "Update Opportunity Status to 'Won' (then create Quotation) or 'Lost' (select reason)."),
            ("View Pipeline", "CRM → Pipeline view shows all open opportunities by stage and value."),
        ],
        "tips": [
            "Set 'Next Contact By' date on every opportunity — it drives your daily follow-up list.",
            "Customer segments are pre-loaded: MEP Contractors, HVAC, Data Centers, Hospitals, Metro & Rail etc.",
            "Use the Notes field on Lead to record meeting minutes.",
            "Monthly CRM report: CRM → Reports → Lead Details / Opportunity Summary.",
        ]
    },
    "Buying": {
        "title": "Purchase Department — User Guide",
        "intro": "Welcome to the Klemco India Purchase workspace. You manage supplier sourcing, purchase orders, and goods receipt for raw materials and traded goods.",
        "steps": [
            ("Create Material Request", "Stock → Material Request → New. Select 'Purchase' type, add items and required quantity."),
            ("Get Supplier Quotes", "Material Request → Create Request for Quotation → send to Tata Steel, JSW, Henkel etc."),
            ("Create Purchase Order", "Buying → Purchase Order → New. Select supplier, add items, confirm rates and delivery date."),
            ("Receive Goods", "Purchase Order → Create Purchase Receipt when goods arrive at Amritsar or Thane warehouse."),
            ("Book Invoice", "Purchase Receipt → Create Purchase Invoice → Submit for payment processing."),
            ("Pay Supplier", "Accounts → Payment Entry → select supplier and match against purchase invoice."),
        ],
        "tips": [
            "Pre-loaded suppliers: Tata Steel, JSW Steel, Henkel Adhesives, Hilti India, Fischer Fixings.",
            "Always select correct warehouse (Amritsar Main Store or Thane Branch Store).",
            "For chemical anchors and adhesives, check expiry and batch info on receipt.",
            "Purchase price should be ~65% of selling price for standard items.",
        ]
    },
    "Invoicing": {
        "title": "Accounts Department — User Guide",
        "intro": "Welcome to the Klemco India Accounts workspace. You manage customer invoicing, supplier payments, and financial reporting for Klemco India.",
        "steps": [
            ("Post Sales Invoice", "Accounts → Sales Invoice → New. Or create from Sales Order / Delivery Note. Submit to post to ledger."),
            ("Collect Payment", "Sales Invoice → Create Payment Entry. Select bank account and posting date."),
            ("Post Purchase Invoice", "Accounts → Purchase Invoice → New. Match against Purchase Receipt. Submit."),
            ("Pay Supplier", "Purchase Invoice → Create Payment Entry. Set mode (NEFT/RTGS/Cheque)."),
            ("Reconcile Bank", "Accounts → Bank Reconciliation → match bank statement entries to system entries."),
            ("View Reports", "Financial Reports → Profit & Loss / Balance Sheet / Cash Flow / Accounts Receivable."),
        ],
        "tips": [
            "GST is applicable — ensure GSTIN is set on customer and supplier masters before invoicing.",
            "All Klemco items have HSN codes pre-loaded (73269099, 84839000 etc.).",
            "Period closing: run Accounts → Period Closing Voucher at month end.",
            "Two companies: 'Klemco India' (Amritsar) — ensure company is selected correctly on each transaction.",
        ]
    },
    "Stock": {
        "title": "Inventory Department — User Guide",
        "intro": "Welcome to the Klemco India Stock workspace. You manage inventory across Amritsar and Thane warehouses — receipts, transfers, adjustments, and stock reports.",
        "steps": [
            ("Receive Stock", "Stock → Purchase Receipt (from Purchase Order). Select Amritsar Main Store or Thane Branch Store."),
            ("Issue to Production", "Stock → Material Issue → select Raw Material Store → issue to Manufacturing."),
            ("Transfer Between Warehouses", "Stock → Stock Entry → Transfer. Select source and target warehouse."),
            ("Adjust Stock", "Stock → Stock Reconciliation → enter actual physical count to correct system stock."),
            ("Check Stock Levels", "Stock → Stock Balance report — filter by item group (Strut Channels, Anchors etc.)."),
            ("Set Reorder Levels", "Item → Reorder Levels tab → set minimum stock level and reorder quantity."),
        ],
        "tips": [
            "Warehouses: Amritsar Main Store, Thane Branch Store, Raw Material Store, Inspection Hold.",
            "All KL-SC (Strut), KL-PH (Pipe Hangers), KL-CA (Chemical Anchors) items are stock items.",
            "Service items (KL-SV-*) are non-stock — do not create stock entries for them.",
            "Run Stock Ageing report monthly to identify slow-moving items.",
        ]
    },
    "Manufacturing": {
        "title": "Manufacturing Department — User Guide",
        "intro": "Welcome to the Klemco India Manufacturing workspace. You manage Bills of Materials, production orders, and work-in-progress for fabricated fixing systems.",
        "steps": [
            ("Create Bill of Materials", "Manufacturing → BOM → New. Select finished item, add raw material items and quantities."),
            ("Raise Production Order", "Manufacturing → Work Order → New. Link BOM, set quantity and target warehouse."),
            ("Issue Raw Materials", "Work Order → Material Transfer for Manufacture. Issues from Raw Material Store."),
            ("Record Manufacture", "Work Order → Manufacture. Moves finished goods to Finished Goods warehouse."),
            ("Quality Inspection", "Work Order → Quality Inspection before transfer to Finished Goods."),
            ("Close Work Order", "Once complete, submit and close the Work Order."),
        ],
        "tips": [
            "Pre-fabrication of strut assemblies (KL-SC series) is the primary manufacturing activity.",
            "Always do a Quality Inspection before moving goods to sellable stock.",
            "Use Subcontracting module for outsourced assembly work.",
            "Scrap generated during cutting goes to 'Scrap - KI' warehouse.",
        ]
    },
    "Projects": {
        "title": "Projects Department — User Guide",
        "intro": "Welcome to the Klemco India Projects workspace. You manage site installation projects, track tasks, and coordinate between sales, inventory, and on-site teams.",
        "steps": [
            ("Create a Project", "Projects → Project → New. Link to Customer (e.g. L&T, Apollo Hospitals). Set expected start and end date."),
            ("Add Tasks", "Project → Tasks tab → Add tasks (Site Survey, Design, Supply, Installation, Handover)."),
            ("Assign Team Members", "Each task → Assign To field. Assign to department users."),
            ("Log Timesheets", "Projects → Timesheet → New. Log hours against project and task."),
            ("Track Materials", "Material Request from Project → links stock consumption to the project."),
            ("Close Project", "Mark project Status as 'Completed' when all tasks done and invoice raised."),
        ],
        "tips": [
            "Project phases match Klemco's 5-step process: Consultation → Design → Customization → Supply → Support.",
            "Link Sales Order to Project for revenue tracking.",
            "Use 'Expected End Date' carefully — it drives the project completion dashboard.",
            "Service items KL-SV-001 to KL-SV-005 are used for billable project services.",
        ]
    },
    "Quality": {
        "title": "Quality Department — User Guide",
        "intro": "Welcome to the Klemco India Quality workspace. You manage inspection checklists, non-conformance reports, and quality procedures for all products.",
        "steps": [
            ("Create Quality Inspection", "Quality → Quality Inspection → New. Link to Purchase Receipt or Work Order. Select inspection template."),
            ("Record Readings", "Fill in measurement readings for each parameter (dimensions, material grade, finish etc.)."),
            ("Pass or Fail", "Set Status to 'Accepted' or 'Rejected'. Rejected items go to Inspection Hold warehouse."),
            ("Raise Non-Conformance", "Quality → Non Conformance → New if a batch fails. Assign corrective action."),
            ("Review Corrective Actions", "Quality → Corrective Action → track resolution status."),
            ("Quality Reports", "Quality → Quality Review to see pass/fail trends by item group."),
        ],
        "tips": [
            "Chemical anchors (KL-CA) and Fire Stop items (KL-FS) require mandatory inspection on receipt.",
            "UL, FM, and ISI certifications must be verified on supplier documents during inward QC.",
            "Rejected stock in 'Inspection Hold - KI' warehouse must be resolved within 7 days.",
            "Create inspection templates per item group for consistent QC checklists.",
        ]
    },
}

# Map workspace name to guide key
workspace_map = {
    "Selling":           "Selling",
    "CRM":               "CRM",
    "Buying":            "Buying",
    "Invoicing":         "Invoicing",
    "Stock":             "Stock",
    "Manufacturing":     "Manufacturing",
    "Projects":          "Projects",
    "Quality":           "Quality",
}

for ws_name, guide_key in workspace_map.items():
    if guide_key not in guides:
        continue
    if not frappe.db.exists('Workspace', ws_name):
        print(f'  SKIP (not found): {ws_name}')
        continue

    g = guides[guide_key]
    ws = frappe.get_doc('Workspace', ws_name)

    existing = json.loads(ws.content) if ws.content else []

    # Remove any previously added guide blocks (by checking for our header pattern)
    filtered = [b for b in existing if not (
        b.get('type') == 'header' and '📘' in (b.get('data', {}).get('text', ''))
    )]

    new_blocks = guide_blocks(g['title'], g['intro'], g['steps'], g['tips'])
    ws.content = json.dumps(new_blocks + filtered)

    ws.flags.ignore_links = True
    ws.save(ignore_permissions=True)
    print(f'  ✓ Guide added to workspace: {ws_name}')

frappe.db.commit()
print()
print('✅ User guides added to all department workspaces!')
frappe.destroy()
