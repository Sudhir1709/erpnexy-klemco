# Klemco CS — core-doctype customizations
# Applied programmatically on after_install / after_migrate so the whole CRM CS
# layer lives in version-controlled app code (Custom Fields + Property Setters).
#
# Implements BRD v1.3 wireframe-review feedback (CR-09 … CR-18):
#   CR-09 FR-SO-16  Back-dated delivery date blocked            -> validation only (no field)
#   CR-10 FR-SO-06  RC discount editable + conditional deviation -> Sales Order fields
#   CR-12           Delivery Form/Note/Challan consolidated      -> "Delivery Challan" print format
#   CR-13 FR-DP-11  COD cheque capture                           -> Sales Invoice fields
#   CR-14 FR-SO-04  Preferred 3PL "Others"                       -> Sales Order fields
#   CR-15 FR-DP-12  WH test-certificate download                 -> client + helper (no field)
#   CR-16           Delivery Instructions on the Challan         -> Sales Order + Delivery Note fields
#   CR-18 BR-KM-02  KM item triple approval                      -> Item fields

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
from frappe.custom.doctype.property_setter.property_setter import make_property_setter
from frappe.permissions import add_permission, update_permission_property

# Roles the CS CRM relies on. Auto-created on every migrate so the v1.3 approval flows
# (Sales Head RC deviation; KM Plant Head + Supply Chain Lead triple approval) always exist —
# fixtures only import from exported JSON, which we don't ship.
REQUIRED_ROLES = [
    "CS Executive",
    "CS Manager",
    "CS Supervisor",
    "Sales Head",
    "KM Plant Head",
    "Supply Chain Lead",
]

# CS operational roles allowed to create/link master records inline from the Sales Order —
# Accounting Dimensions → Project, and Sales Team → Sales Person. Frappe only offers the
# "+ Create a new X" quick-entry in the link picker to users who hold create permission on X;
# stock ERPNext restricts these to Projects Manager / Sales Master Manager, which CS users lack.
INLINE_CREATE_ROLES = ["CS Executive", "CS Supervisor", "CS Manager"]
INLINE_CREATE_DOCTYPES = ["Project", "Sales Person"]

KLEMCO_CUSTOMER_TYPES = "\nRegular\nRC (Rate Contract)\nCOD"
THREE_PL_OPTIONS = "\nMahindra Logistics\nDTDC Freight\nBlue Dart\nOthers (not yet decided)"
DEVIATION_STATUSES = "Not Required\nPending Sales Head Approval\nApproved\nRejected"
KM_APPROVAL_STATUSES = "\nPending Approvals\nApproved"


CUSTOM_FIELDS = {
    # ── Customer: classification drives RC-deviation (FR-SO-06) and COD cheque (FR-DP-11) ──
    "Customer": [
        {
            "fieldname": "custom_klemco_customer_type",
            "label": "Klemco Customer Type",
            "fieldtype": "Select",
            "options": KLEMCO_CUSTOMER_TYPES,
            "insert_after": "customer_type",
            "translatable": 0,
            "description": "Regular / RC (Rate Contract) / COD. Drives RC discount deviation "
                           "routing (FR-SO-06) and COD cheque capture (FR-DP-11).",
        },
    ],

    # ── Sales Order: 3PL Others (CR-14), delivery instructions (CR-16), RC deviation (CR-10) ──
    "Sales Order": [
        {
            "fieldname": "custom_klemco_cs_sb",
            "label": "Klemco CS — Logistics & Deviations",
            "fieldtype": "Section Break",
            "insert_after": "po_date",
            "collapsible": 1,
        },
        {
            "fieldname": "custom_preferred_3pl",
            "label": "Preferred 3PL",
            "fieldtype": "Select",
            "options": THREE_PL_OPTIONS,
            "insert_after": "custom_klemco_cs_sb",
            "translatable": 0,
            "description": "FR-SO-04: choose a configured partner or 'Others (not yet decided)'.",
        },
        {
            "fieldname": "custom_3pl_note",
            "label": "3PL — Specify / Note",
            "fieldtype": "Small Text",
            "insert_after": "custom_preferred_3pl",
            # No declarative depends_on/mandatory_depends_on: a parenthesised string literal
            # ("Others (not yet decided)") breaks Frappe's client-side depends_on evaluator
            # ("Invalid depends_on expression"). The "required when Others" rule is enforced by
            # the client script (sales_order.js toggles reqd) AND server validation
            # (events/sales_order._validate_3pl).
            "depends_on": "",
            "mandatory_depends_on": "",
            "description": "Specify the logistics partner when 3PL is 'Others (not yet decided)'; "
                           "confirmed at dispatch.",
        },
        {
            "fieldname": "custom_delivery_instructions",
            "label": "Delivery Instructions",
            "fieldtype": "Small Text",
            "insert_after": "custom_3pl_note",
            "description": "Carried to the Delivery Challan for the warehouse (CR-16).",
        },
        {
            "fieldname": "custom_deviation_cb",
            "fieldtype": "Column Break",
            "insert_after": "custom_delivery_instructions",
        },
        {
            "fieldname": "custom_rc_deviation",
            "label": "RC Conditional Deviation",
            "fieldtype": "Check",
            "insert_after": "custom_deviation_cb",
            "read_only": 1,
            "description": "Set automatically when a discount is applied on a Rate Contract customer (FR-SO-06).",
        },
        {
            "fieldname": "custom_deviation_approval_status",
            "label": "Deviation Approval Status",
            "fieldtype": "Select",
            "options": DEVIATION_STATUSES,
            "default": "Not Required",
            "insert_after": "custom_rc_deviation",
            "read_only": 1,
            "translatable": 0,
            "in_standard_filter": 1,
        },
        {
            "fieldname": "custom_deviation_approved_by",
            "label": "Deviation Approved By",
            "fieldtype": "Link",
            "options": "User",
            "insert_after": "custom_deviation_approval_status",
            "read_only": 1,
        },
    ],

    # ── Delivery Note: instructions on the Challan (CR-16) ──
    "Delivery Note": [
        {
            "fieldname": "custom_delivery_instructions",
            "label": "Delivery Instructions",
            "fieldtype": "Small Text",
            "insert_after": "customer_name",
            "description": "Auto-carried from the Sales Order (CR-16). Shown on the Delivery Challan.",
        },
        # Dispatch & Tracking — captured by the warehouse at dispatch (moved off the Sales Order,
        # which locks after submit). Stock User/Manager have write access to the Delivery Note.
        {
            "fieldname": "cs_dispatch_section",
            "label": "Dispatch & Tracking",
            "fieldtype": "Section Break",
            "insert_after": "custom_delivery_instructions",
            "collapsible": 1,
        },
        {
            "fieldname": "cs_docket_number",
            "label": "Docket / LR #",
            "fieldtype": "Data",
            "insert_after": "cs_dispatch_section",
            "allow_on_submit": 1,
            "description": "Transporter's docket / lorry-receipt number for the consignment.",
        },
        {
            "fieldname": "cs_tracking_url",
            "label": "Tracking URL",
            "fieldtype": "Data",
            "insert_after": "cs_docket_number",
            "allow_on_submit": 1,
            "description": "Link to the courier's live tracking page.",
        },
        {
            "fieldname": "cs_dispatch_col",
            "fieldtype": "Column Break",
            "insert_after": "cs_tracking_url",
        },
        {
            "fieldname": "cs_pod_attachment",
            "label": "Proof of Delivery (POD)",
            "fieldtype": "Attach",
            "insert_after": "cs_dispatch_col",
            "allow_on_submit": 1,
            "description": "Photo, signature, or GPS confirmation of delivery (FR-4-09).",
        },
    ],

    # ── Sales Invoice: COD cheque capture (FR-DP-11 / BR-DP-06) ──
    "Sales Invoice": [
        {
            "fieldname": "custom_cod_section",
            "label": "COD Cheque Details",
            "fieldtype": "Section Break",
            "insert_after": "customer_name",
            "collapsible": 1,
            "depends_on": "eval:doc.custom_is_cod",
            "description": "FR-DP-11: capture cheque details for COD customers. Visible to Finance.",
        },
        {
            "fieldname": "custom_is_cod",
            "label": "Is COD",
            "fieldtype": "Check",
            "insert_after": "custom_cod_section",
            "read_only": 1,
            "description": "Set automatically from the customer's Klemco Customer Type = COD.",
        },
        {
            "fieldname": "custom_cheque_no",
            "label": "Cheque No.",
            "fieldtype": "Data",
            "insert_after": "custom_is_cod",
        },
        {
            "fieldname": "custom_cheque_bank",
            "label": "Drawer Bank",
            "fieldtype": "Data",
            "insert_after": "custom_cheque_no",
        },
        {
            "fieldname": "custom_cod_cb",
            "fieldtype": "Column Break",
            "insert_after": "custom_cheque_bank",
        },
        {
            "fieldname": "custom_cheque_date",
            "label": "Cheque Date",
            "fieldtype": "Date",
            "insert_after": "custom_cod_cb",
        },
        {
            "fieldname": "custom_cheque_amount",
            "label": "Cheque Amount",
            "fieldtype": "Currency",
            "insert_after": "custom_cheque_date",
        },
        {
            "fieldname": "custom_cheque_copy",
            "label": "Cheque Copy",
            "fieldtype": "Attach",
            "insert_after": "custom_cheque_amount",
        },
    ],

    # ── Item: KM-managed triple approval (BR-KM-02 / CR-18) ──
    "Item": [
        {
            "fieldname": "custom_km_section",
            "label": "KM Manufacturing Approval",
            "fieldtype": "Section Break",
            "insert_after": "disabled",
            "collapsible": 1,
        },
        {
            "fieldname": "custom_km_managed",
            "label": "KM-Managed Item",
            "fieldtype": "Check",
            "insert_after": "custom_km_section",
            "description": "New KM-master items need triple approval before they can be enabled (BR-KM-02).",
        },
        {
            "fieldname": "custom_km_approval_status",
            "label": "KM Approval Status",
            "fieldtype": "Select",
            "options": KM_APPROVAL_STATUSES,
            "insert_after": "custom_km_managed",
            "read_only": 1,
            "translatable": 0,
            "depends_on": "eval:doc.custom_km_managed",
        },
        {
            "fieldname": "custom_km_approved_cs_supervisor",
            "label": "Approved — CS Supervisor",
            "fieldtype": "Check",
            "insert_after": "custom_km_approval_status",
            "depends_on": "eval:doc.custom_km_managed",
            "description": "Settable only by the CS Supervisor role.",
        },
        {
            "fieldname": "custom_km_approved_plant_head",
            "label": "Approved — KM Plant Head",
            "fieldtype": "Check",
            "insert_after": "custom_km_approved_cs_supervisor",
            "depends_on": "eval:doc.custom_km_managed",
            "description": "Settable only by the KM Plant Head role.",
        },
        {
            "fieldname": "custom_km_approved_supply_chain",
            "label": "Approved — Supply Chain Lead",
            "fieldtype": "Check",
            "insert_after": "custom_km_approved_plant_head",
            "depends_on": "eval:doc.custom_km_managed",
            "description": "Settable only by the Supply Chain Lead role (added in BR-KM-02 v1.3 / CR-18).",
        },
    ],
}


# Delivery Note + Sales Order: make the per-item Required Delivery Date picker reject the past
# client-side as well (server-side enforced in events). Property setter sets min on the field
# is not supported declaratively, so client scripts handle the picker bound; here we only relabel
# the Delivery Note default print format to the consolidated "Delivery Challan".
PROPERTY_SETTERS = [
    {
        "doctype_or_field": "DocType",
        "doctype": "Delivery Note",
        "property": "default_print_format",
        "value": "Delivery Challan",
        "property_type": "Data",
    },
    # ── Payment Terms Template: streamline the section (declutter) ──────────────
    # Stock ERPNext exposes a master-link column + a discount block + advanced
    # fields that confuse CS/accounts users ("couldn't create a payment term").
    # Reduce the grid to the essentials — Invoice Portion / Due Date Based On /
    # Credit Days — and tuck the rest into the row detail or hide the advanced bits.
    {
        "doctype_or_field": "Field",
        "doctype": "Payment Terms Template",
        "fieldname": "allocate_payment_based_on_payment_terms",
        "property": "hidden",
        "value": "1",
        "property_type": "Check",
    },
    {
        "doctype_or_field": "Field",
        "doctype": "Payment Terms Template Detail",
        "fieldname": "payment_term",
        "property": "in_list_view",
        "value": "0",
        "property_type": "Check",
    },
    {
        # A new term row defaults to the full invoice — the common single-term
        # template is valid immediately; multi-row users just adjust the split.
        "doctype_or_field": "Field",
        "doctype": "Payment Terms Template Detail",
        "fieldname": "invoice_portion",
        "property": "default",
        "value": "100",
        "property_type": "Text",
    },
    # Neither Invoice Portion nor Due Date Based On should be user-mandatory — sensible
    # values are auto-filled (default 100% + server before_validate) so a user only needs
    # to enter Credit Days. Due Date Based On defaults to the "days after invoice date"
    # basis, which is exactly what Credit Days feeds.
    {
        "doctype_or_field": "Field",
        "doctype": "Payment Terms Template Detail",
        "fieldname": "invoice_portion",
        "property": "reqd",
        "value": "0",
        "property_type": "Check",
    },
    {
        "doctype_or_field": "Field",
        "doctype": "Payment Terms Template Detail",
        "fieldname": "due_date_based_on",
        "property": "reqd",
        "value": "0",
        "property_type": "Check",
    },
    {
        "doctype_or_field": "Field",
        "doctype": "Payment Terms Template Detail",
        "fieldname": "due_date_based_on",
        "property": "default",
        "value": "Day(s) after invoice date",
        "property_type": "Text",
    },
    {
        "doctype_or_field": "Field",
        "doctype": "Payment Terms Template Detail",
        "fieldname": "description",
        "property": "in_list_view",
        "value": "0",
        "property_type": "Check",
    },
    {
        "doctype_or_field": "Field",
        "doctype": "Payment Terms Template Detail",
        "fieldname": "mode_of_payment",
        "property": "hidden",
        "value": "1",
        "property_type": "Check",
    },
    {
        "doctype_or_field": "Field",
        "doctype": "Payment Terms Template Detail",
        "fieldname": "credit_months",
        "property": "hidden",
        "value": "1",
        "property_type": "Check",
    },
    {
        "doctype_or_field": "Field",
        "doctype": "Payment Terms Template Detail",
        "fieldname": "discount_type",
        "property": "hidden",
        "value": "1",
        "property_type": "Check",
    },
    {
        "doctype_or_field": "Field",
        "doctype": "Payment Terms Template Detail",
        "fieldname": "discount",
        "property": "hidden",
        "value": "1",
        "property_type": "Check",
    },
    {
        "doctype_or_field": "Field",
        "doctype": "Payment Terms Template Detail",
        "fieldname": "discount_validity_based_on",
        "property": "hidden",
        "value": "1",
        "property_type": "Check",
    },
    {
        "doctype_or_field": "Field",
        "doctype": "Payment Terms Template Detail",
        "fieldname": "discount_validity",
        "property": "hidden",
        "value": "1",
        "property_type": "Check",
    },
    # Sales Invoice: make the "Update Stock" option (which reveals Set Source Warehouse)
    # discoverable for direct billing without a Delivery Note.
    {
        "doctype_or_field": "Field",
        "doctype": "Sales Invoice",
        "fieldname": "update_stock",
        "property": "description",
        "value": (
            "Tick to also reduce stock at billing — for a direct invoice raised without a "
            "Delivery Note. The Set Source Warehouse field then appears. Leave off when a "
            "Delivery Note already moved the stock."
        ),
        "property_type": "Text",
    },
    # Show the Unit of Measure (UOM) as a column in the sales-transaction item grids.
    {
        "doctype_or_field": "Field",
        "doctype": "Sales Order Item",
        "fieldname": "uom",
        "property": "in_list_view",
        "value": "1",
        "property_type": "Check",
    },
    # Pin explicit grid column widths on the Sales Order items grid. The grid renders only
    # as many in_list_view columns as fit a ~10-unit budget and drops the overflow — with 7
    # in-list fields (item_code, delivery_date, cs_required_delivery_date, qty, uom, rate,
    # amount) at their default widths the total exceeds the budget and UOM was being squeezed
    # out of the rendered grid. These widths sum to 10 so every column (incl. UOM) shows.
    {"doctype_or_field": "Field", "doctype": "Sales Order Item", "fieldname": "item_code",
     "property": "columns", "value": "2", "property_type": "Int"},
    {"doctype_or_field": "Field", "doctype": "Sales Order Item", "fieldname": "delivery_date",
     "property": "columns", "value": "2", "property_type": "Int"},
    {"doctype_or_field": "Field", "doctype": "Sales Order Item", "fieldname": "cs_required_delivery_date",
     "property": "columns", "value": "2", "property_type": "Int"},
    {"doctype_or_field": "Field", "doctype": "Sales Order Item", "fieldname": "qty",
     "property": "columns", "value": "1", "property_type": "Int"},
    {"doctype_or_field": "Field", "doctype": "Sales Order Item", "fieldname": "uom",
     "property": "columns", "value": "1", "property_type": "Int"},
    {"doctype_or_field": "Field", "doctype": "Sales Order Item", "fieldname": "rate",
     "property": "columns", "value": "1", "property_type": "Int"},
    {"doctype_or_field": "Field", "doctype": "Sales Order Item", "fieldname": "amount",
     "property": "columns", "value": "1", "property_type": "Int"},
    # Dispatch & Tracking moved to the Delivery Note (warehouse captures it at dispatch) —
    # hide these on the Sales Order, which locks after submit. Client Order Confirmation stays.
    {"doctype_or_field": "Field", "doctype": "Sales Order", "fieldname": "cs_docket_number",
     "property": "hidden", "value": "1", "property_type": "Check"},
    {"doctype_or_field": "Field", "doctype": "Sales Order", "fieldname": "cs_tracking_url",
     "property": "hidden", "value": "1", "property_type": "Check"},
    {"doctype_or_field": "Field", "doctype": "Sales Order", "fieldname": "cs_pod_attachment",
     "property": "hidden", "value": "1", "property_type": "Check"},
    {"doctype_or_field": "Field", "doctype": "Sales Order", "fieldname": "cs_dispatch_section",
     "property": "label", "value": "Client Order Confirmation", "property_type": "Data"},
    {
        "doctype_or_field": "Field",
        "doctype": "Quotation Item",
        "fieldname": "uom",
        "property": "in_list_view",
        "value": "1",
        "property_type": "Check",
    },
    {
        "doctype_or_field": "Field",
        "doctype": "Sales Invoice Item",
        "fieldname": "uom",
        "property": "in_list_view",
        "value": "1",
        "property_type": "Check",
    },
    {
        "doctype_or_field": "Field",
        "doctype": "Delivery Note Item",
        "fieldname": "uom",
        "property": "in_list_view",
        "value": "1",
        "property_type": "Check",
    },
]


DELIVERY_CHALLAN_PRINT_FORMAT = "Delivery Challan"


def apply_customizations():
    """Idempotent — safe to run on every migrate."""
    _ensure_roles()
    _ensure_project_permissions()
    _ensure_billing_controls()
    _ensure_discount_matrix()
    _ensure_ic_stock_entry_taxes_field()
    _ensure_default_company()
    _ensure_order_reports()
    _ensure_cs_sidebar_links()
    create_custom_fields(CUSTOM_FIELDS, update=True)
    _apply_property_setters()
    _ensure_delivery_challan_print_format()
    _ensure_proforma_print_formats()
    frappe.clear_cache()


# Default max line discount (%) by customer type — the seed rows of the Discount Matrix
# (BR-OE-01). Editable by Sales Head / CS Manager afterwards. RC customers get 0 (discounts
# are blocked); the "All" fallback catches anything not otherwise listed.
DISCOUNT_MATRIX_DEFAULTS = [
    ("RC (Rate Contract)", 0.0),
    ("Regular", 10.0),
    ("COD", 5.0),
    ("All", 10.0),
]


def _ensure_discount_matrix():
    if not frappe.db.exists("DocType", "CS Discount Matrix"):
        return  # doctype not migrated yet
    for customer_type, max_pct in DISCOUNT_MATRIX_DEFAULTS:
        exists = frappe.db.exists(
            "CS Discount Matrix",
            {"customer_type": customer_type, "item_group": ["in", [None, ""]]},
        )
        if exists:
            continue
        frappe.get_doc({
            "doctype": "CS Discount Matrix",
            "customer_type": customer_type,
            "max_discount_percent": max_pct,
            "active": 1,
        }).insert(ignore_permissions=True)


def _ensure_default_company():
    """Default new documents to the GST-registered operating company (Klemco India), not the
    demo company. New Sales Orders / Delivery Notes / Invoices otherwise defaulted to
    'Klemco India (Demo)' — which has no GSTIN and no real stock — so GST didn't auto-calculate
    and stock lookups came up empty. Saving Global Defaults (not a bare set_single_value) is what
    propagates the framework default. Guarded so it's a no-op where the company is absent (8081)."""
    company = "Klemco India"
    if not frappe.db.exists("Company", company) or frappe.db.get_value("Company", company, "is_group"):
        return
    if frappe.db.get_single_value("Global Defaults", "default_company") != company:
        gd = frappe.get_doc("Global Defaults")
        gd.default_company = company
        gd.save(ignore_permissions=True)
    # Global Defaults.on_update doesn't always sync the framework-level default that new_doc reads;
    # set it directly so a new Sales Order / Delivery Note / Invoice defaults to this company.
    if frappe.defaults.get_global_default("company") != company:
        frappe.db.set_default("company", company)


def _ensure_ic_stock_entry_taxes_field():
    """Repair a partial India Compliance install that makes EVERY Stock Entry unsaveable.

    india_compliance defines a field group for ("Subcontracting Order", "Subcontracting Receipt",
    "Stock Entry") in gst_india/constants/custom_fields.py. On this site every field in that group
    installed EXCEPT the `taxes` child table, yet its hooks (hooks.py -> subcontracting_transaction)
    run on every Stock Entry save: validate() calls CustomTaxController(...).set_taxes_and_totals()
    before any subcontracting bail-out, and before_save() iterates `doc.taxes`. With the field
    missing that raises "'StockEntry' object has no attribute 'taxes'", so no Stock Entry — not even
    a plain Material Receipt — can be saved. (Symptom: zero Stock Entries existed on the site.)

    Recreate just that one field, exactly as india_compliance declares it. Idempotent; no-op where
    india_compliance isn't installed.
    """
    if not frappe.db.exists("DocType", "India Compliance Taxes and Charges"):
        return  # india_compliance not installed on this site
    create_custom_fields(
        {
            ("Subcontracting Order", "Subcontracting Receipt", "Stock Entry"): [
                {
                    "fieldname": "taxes",
                    "label": "Estimated Taxes",
                    "fieldtype": "Table",
                    "options": "India Compliance Taxes and Charges",
                    "insert_after": "taxes_and_charges",
                },
            ]
        },
        update=True,
    )


# Extra links surfaced in the Customer Service left-nav (Workspace Sidebar). Each is inserted
# after an existing anchor item so it lands in the right group, and only if its target exists.
CS_SIDEBAR_LINKS = [
    {"label": "Discount Matrix", "link_type": "DocType", "link_to": "CS Discount Matrix",
     "after": "Category Mapping", "requires": ("DocType", "CS Discount Matrix")},
    # "What's in stock?" — the report users actually need; otherwise it's buried in the Stock module.
    {"label": "Stock Balance", "link_type": "Report", "link_to": "Stock Balance",
     "after": "Sales Invoices", "requires": ("Report", "Stock Balance")},
    # Order lists that also show Created On + Created By (see _ensure_order_reports). The desk List
    # view can't show those system fields as columns, so these are Report-view reports.
    {"label": "Sales Orders — Created", "link_type": "Report", "link_to": "Sales Orders — Created",
     "after": "All Sales Orders", "requires": ("Report", "Sales Orders — Created")},
    {"label": "Delivery Notes — Created", "link_type": "Report", "link_to": "Delivery Notes — Created",
     "after": "Delivery Notes", "requires": ("Report", "Delivery Notes — Created")},
    {"label": "Sales Invoices — Created", "link_type": "Report", "link_to": "Sales Invoices — Created",
     "after": "Sales Invoices", "requires": ("Report", "Sales Invoices — Created")},
    {"label": "Klemco Orders — Created", "link_type": "Report", "link_to": "Klemco Orders — Created",
     "after": "All Klemco Orders", "requires": ("Report", "Klemco Orders — Created")},
    {"label": "Quotations — Created", "link_type": "Report", "link_to": "Quotations — Created",
     "after": "New Klemco Order", "requires": ("Report", "Quotations — Created")},
]


# Order lists with a "who created it, and when" view. The desk List view can only show in_list_view
# docfields as columns, and `creation` (Created On) / `owner` (Created By) are standard fields, not
# docfields — so they can never be List columns. Report view renders any field, so we ship a
# Report-Builder report per order doctype: its business columns + Created On + Created By, newest first.
ORDER_REPORTS = {
    "Sales Orders — Created": ("Sales Order",
        ["customer_name", "status", "transaction_date", "delivery_date", "grand_total",
         "cs_discount_approval_status", "cs_credit_hold_status"]),
    "Delivery Notes — Created": ("Delivery Note",
        ["customer_name", "status", "posting_date", "grand_total", "cs_docket_number"]),
    "Sales Invoices — Created": ("Sales Invoice",
        ["customer_name", "status", "posting_date", "grand_total", "outstanding_amount"]),
    "Quotations — Created": ("Quotation",
        ["party_name", "status", "transaction_date", "valid_till", "grand_total"]),
    "Klemco Orders — Created": ("KM Order",
        ["customer", "status", "linked_sales_order"]),
}


def _ensure_order_reports():
    import json as _json
    for name, (dt, cols) in ORDER_REPORTS.items():
        if not frappe.db.exists("DocType", dt) or frappe.db.exists("Report", name):
            continue
        meta = frappe.get_meta(dt)
        # keep only business columns that actually exist, then append the audit columns
        fields = [c for c in cols if meta.get_field(c)] + ["creation", "owner"]
        pairs = [[f, dt] for f in fields]
        cfg = {
            "add_total_row": 0,
            "sort_by": "%s.creation" % dt, "sort_order": "desc",
            "sort_by_next": None, "sort_order_next": "desc",
            "filters": [],
            "columns": pairs,            # newer report-view key
            "fields": pairs,             # older key — set both for loader compatibility
            "order_by": "`tab%s`.`creation` desc" % dt,
        }
        frappe.get_doc({
            "doctype": "Report",
            "report_name": name,
            "ref_doctype": dt,
            "report_type": "Report Builder",
            "is_standard": "No",
            "module": "Customer Service",
            "json": _json.dumps(cfg),
        }).insert(ignore_permissions=True)


def _ensure_cs_sidebar_links():
    """Surface key screens in the Customer Service left-nav (Workspace Sidebar). The sidebar is a
    hand-built DB doc, so add any missing links idempotently on every migrate — otherwise they are
    only reachable by typing a URL. Wrapped defensively so a nav tweak never blocks a migrate."""
    try:
        if not frappe.db.exists("Workspace Sidebar", "Customer Service"):
            return
        sb = frappe.get_doc("Workspace Sidebar", "Customer Service")
        existing = {i.label for i in sb.items} | {i.link_to for i in sb.items if i.link_to}

        pending = [
            l for l in CS_SIDEBAR_LINKS
            if l["label"] not in existing
            and l["link_to"] not in existing
            and frappe.db.exists(l["requires"][0], l["requires"][1])
        ]
        if not pending:
            return

        # Rebuild the child table, dropping each new link in after its anchor; anything whose
        # anchor is missing is appended at the end.
        rows = []
        for i in sb.items:
            rows.append({"label": i.label, "link_type": i.link_type, "link_to": i.link_to,
                         "url": i.get("url"), "type": i.type})
            for l in list(pending):
                if i.label == l["after"]:
                    rows.append({"label": l["label"], "link_type": l["link_type"],
                                 "link_to": l["link_to"], "url": "", "type": "Link"})
                    pending.remove(l)
        for l in pending:  # anchor not found — append
            rows.append({"label": l["label"], "link_type": l["link_type"],
                         "link_to": l["link_to"], "url": "", "type": "Link"})

        sb.set("items", [])
        for idx, r in enumerate(rows, start=1):
            row = sb.append("items", r)
            row.idx = idx
        sb.save(ignore_permissions=True)
    except Exception:
        frappe.log_error(title="klemco_cs: CS sidebar links")


def _ensure_billing_controls():
    """A Sales Invoice must originate from a Sales Order — no billing for un-ordered goods.
    ERPNext enforces this via Selling Settings.so_required (so_dn_required); POS is exempt."""
    if frappe.db.get_single_value("Selling Settings", "so_required") != "Yes":
        frappe.db.set_single_value("Selling Settings", "so_required", "Yes")
    _ensure_rcm_templates_disabled()


def _ensure_rcm_templates_disabled():
    """Reverse-charge sales are not used here (GST Settings.enable_reverse_charge_in_sales is
    off), so disable the RCM output tax templates. An accidentally-selected RCM template adds
    GST and subtracts it back — netting to zero ("tax not getting calculated"). If reverse
    charge is turned on later, this leaves the templates enabled."""
    if not frappe.db.exists("DocType", "GST Settings"):
        return  # india_compliance not installed on this site
    if frappe.db.get_single_value("GST Settings", "enable_reverse_charge_in_sales"):
        return
    rcm = frappe.get_all(
        "Sales Taxes and Charges Template",
        filters={"tax_category": ["in", ["Reverse Charge In-State", "Reverse Charge Out-State"]],
                 "disabled": 0},
        pluck="name",
    )
    for t in rcm:
        frappe.db.set_value("Sales Taxes and Charges Template", t, "disabled", 1)


def _ensure_roles():
    for role in REQUIRED_ROLES:
        if not frappe.db.exists("Role", role):
            frappe.get_doc({"doctype": "Role", "role_name": role}).insert(ignore_permissions=True)


def _ensure_project_permissions():
    """Let CS users create/link master records inline from the Sales Order — Project (Accounting
    Dimensions) and Sales Person (Sales Team). Adds a Custom DocPerm for each CS operational role —
    idempotent, re-applied on every migrate. Without create permission Frappe hides the
    "+ Create a new X" quick-entry (Sales Person is a tree doctype; a persona can also be added
    from the Sales Person Tree once the role has create)."""
    for dt in INLINE_CREATE_DOCTYPES:
        if not frappe.db.exists("DocType", dt):
            continue
        for role in INLINE_CREATE_ROLES:
            if not frappe.db.exists("Role", role):
                continue
            add_permission(dt, role, 0)  # creates a Custom DocPerm (read=1) if absent
            for ptype in ("read", "write", "create"):
                update_permission_property(dt, role, 0, ptype, 1, validate=False)


def _apply_property_setters():
    for ps in PROPERTY_SETTERS:
        # Skip the default-print-format setter until the print format exists.
        if ps["property"] == "default_print_format" and not frappe.db.exists(
            "Print Format", ps["value"]
        ):
            continue
        make_property_setter(
            doctype=ps["doctype"],
            fieldname=ps.get("fieldname"),
            property=ps["property"],
            value=ps["value"],
            property_type=ps.get("property_type", "Data"),
            for_doctype=(ps["doctype_or_field"] == "DocType"),
            validate_fields_for_doctype=False,
        )


def _ensure_delivery_challan_print_format():
    """CR-12: one consolidated artefact. The single 'Delivery Note' document is printed as a
    'Delivery Challan' that also surfaces the delivery instructions carried from the SO (CR-16)."""
    if frappe.db.exists("Print Format", DELIVERY_CHALLAN_PRINT_FORMAT):
        return

    html = """
<div class="print-heading"><h2>Delivery Challan</h2></div>
<div style="margin-bottom:8px;">
  <strong>{{ doc.name }}</strong> &middot; {{ frappe.format(doc.posting_date, {"fieldtype":"Date"}) }}<br>
  <strong>Customer:</strong> {{ doc.customer_name }}<br>
  {% if doc.shipping_address %}<strong>Ship To:</strong><br>{{ doc.shipping_address }}{% endif %}
</div>
{% if doc.custom_delivery_instructions %}
<div style="border:1px solid #F39C12;background:#FFF8E1;border-radius:6px;padding:8px 10px;margin:8px 0;">
  <strong>Delivery Instructions:</strong> {{ doc.custom_delivery_instructions }}
</div>
{% endif %}
<table class="table table-bordered">
  <thead><tr>
    <th>#</th><th>Item</th><th>Description</th><th class="text-right">Qty</th><th>UOM</th>
  </tr></thead>
  <tbody>
  {% for row in doc.items %}
    <tr>
      <td>{{ loop.index }}</td>
      <td>{{ row.item_code }}</td>
      <td>{{ row.item_name }}</td>
      <td class="text-right">{{ row.qty }}</td>
      <td>{{ row.uom }}</td>
    </tr>
  {% endfor %}
  </tbody>
</table>
<p style="font-size:11px;color:#888;margin-top:12px;">
  Consolidated Delivery Challan (CR-12) — supersedes the earlier Delivery Form / Delivery Note artefacts.
</p>
""".strip()

    frappe.get_doc({
        "doctype": "Print Format",
        "name": DELIVERY_CHALLAN_PRINT_FORMAT,
        "doc_type": "Delivery Note",
        "module": "Customer Service",
        "standard": "No",
        "custom_format": 1,
        "print_format_type": "Jinja",
        "html": html,
    }).insert(ignore_permissions=True)

    # Now that it exists, set it as the default print format for Delivery Note.
    make_property_setter(
        doctype="Delivery Note",
        fieldname=None,
        property="default_print_format",
        value=DELIVERY_CHALLAN_PRINT_FORMAT,
        property_type="Data",
        for_doctype=True,
        validate_fields_for_doctype=False,
    )


# ── Proforma Invoice — a preliminary, NON-tax bill printable from Quotation / SO ──
# One Jinja template renders both doctypes (shared fields). Two Print Format records
# because a format is bound to one doctype. No accounting entry — it's just a print.
PROFORMA_HTML = """
<div style="text-align:center;margin-bottom:6px;">
  <h2 style="margin:0;letter-spacing:1px;">PROFORMA INVOICE</h2>
  <div style="font-size:11px;color:#b00;">This is a Proforma Invoice — not a tax invoice and not a demand for payment.</div>
</div>
<table style="width:100%;font-size:12px;margin-bottom:8px;"><tr>
  <td style="vertical-align:top;">
    <strong>{{ doc.company }}</strong><br>
    {%- set caddr = frappe.db.get_value("Address", {"is_your_company_address":1, "gstin":["!=",""]}, ["address_line1","city","gst_state","gstin"], as_dict=True) %}
    {%- if caddr %}{{ caddr.address_line1 }}, {{ caddr.city }} ({{ caddr.gst_state }})<br>GSTIN: {{ caddr.gstin }}{% endif %}
  </td>
  <td style="vertical-align:top;text-align:right;">
    <strong>{{ doc.name }}</strong><br>
    Date: {{ frappe.format(doc.transaction_date, {"fieldtype":"Date"}) }}
  </td>
</tr></table>
<table style="width:100%;font-size:12px;margin-bottom:8px;"><tr>
  <td style="vertical-align:top;"><strong>Bill To:</strong><br>{{ doc.customer_name }}<br>{{ doc.address_display or "" }}</td>
  <td style="vertical-align:top;"><strong>Ship To:</strong><br>{{ doc.shipping_address_name and doc.shipping_address or (doc.address_display or "") }}</td>
</tr></table>
<table class="table table-bordered" style="font-size:12px;">
  <thead><tr>
    <th>#</th><th>Item</th><th>Description</th><th class="text-right">Qty</th><th>UOM</th>
    <th class="text-right">Rate</th><th class="text-right">Amount</th>
  </tr></thead>
  <tbody>
  {% for row in doc.items %}
    <tr>
      <td>{{ loop.index }}</td>
      <td>{{ row.item_code }}</td>
      <td>{{ row.item_name }}</td>
      <td class="text-right">{{ row.qty }}</td>
      <td>{{ row.uom }}</td>
      <td class="text-right">{{ frappe.format(row.rate, {"fieldtype":"Currency"}, doc=doc) }}</td>
      <td class="text-right">{{ frappe.format(row.amount, {"fieldtype":"Currency"}, doc=doc) }}</td>
    </tr>
  {% endfor %}
  </tbody>
</table>
<table style="width:100%;font-size:12px;">
  <tr><td style="text-align:right;">Net Total</td>
      <td style="text-align:right;width:150px;">{{ frappe.format(doc.net_total, {"fieldtype":"Currency"}, doc=doc) }}</td></tr>
  {% for t in doc.taxes %}
  <tr><td style="text-align:right;">{{ t.description }}</td>
      <td style="text-align:right;">{{ frappe.format(t.tax_amount, {"fieldtype":"Currency"}, doc=doc) }}</td></tr>
  {% endfor %}
  <tr><td style="text-align:right;"><strong>Grand Total</strong></td>
      <td style="text-align:right;"><strong>{{ frappe.format(doc.grand_total, {"fieldtype":"Currency"}, doc=doc) }}</strong></td></tr>
</table>
<div style="font-size:11px;margin-top:6px;">Amount in words: <strong>{{ doc.in_words or "" }}</strong></div>
<p style="font-size:11px;color:#666;margin-top:14px;border-top:1px solid #ddd;padding-top:6px;">
  Proforma Invoice for advance/approval only. Goods/services will be billed on a tax invoice raised against
  the confirmed Sales Order. Bank details for advance payment available on request.
</p>
""".strip()

PROFORMA_FORMATS = {
    "Proforma Invoice": "Sales Order",
    "Proforma Invoice (Quotation)": "Quotation",
}


def _ensure_proforma_print_formats():
    for name, dt in PROFORMA_FORMATS.items():
        if frappe.db.exists("Print Format", name):
            continue
        frappe.get_doc({
            "doctype": "Print Format",
            "name": name,
            "doc_type": dt,
            "module": "Customer Service",
            "standard": "No",
            "custom_format": 1,
            "print_format_type": "Jinja",
            "html": PROFORMA_HTML,
        }).insert(ignore_permissions=True)
