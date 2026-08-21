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
# Item added so CS users can create item masters (e.g. Freight) — on this site only "Item Manager"
# had create on Item, which the CS team lacked. Also enables the "+ Create a new Item" inline picker.
INLINE_CREATE_DOCTYPES = ["Project", "Sales Person", "Item"]

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

    # ── User: capture the Sales Office at user creation ──
    "User": [
        {
            "fieldname": "cs_sales_office",
            "label": "Sales Office",
            "fieldtype": "Data",
            "insert_after": "mobile_no",
            "description": "The sales office this user belongs to (captured at user creation).",
        },
        {
            "fieldname": "cs_office_address",
            "label": "Sales Office Address",
            "fieldtype": "Link",
            "options": "Address",
            "insert_after": "cs_sales_office",
            "description": "Klemco office address printed as the seller address on this user's quotations.",
        },
    ],

    # ── Purchase Invoice: durable link back to the Plant Order that generated it (Document Flow) ──
    "Purchase Invoice": [
        {
            "fieldname": "cs_plant_order",
            "label": "Plant Order",
            "fieldtype": "Link",
            "options": "KM Order",
            "insert_after": "remarks",
            "read_only": 1,
            "print_hide": 1,
            "description": "The Plant Order this purchase bill was generated from.",
        },
    ],

    # ── Sales Person: sales geography Zone ──
    "Sales Person": [
        {
            "fieldname": "zone",
            "label": "Zone",
            "fieldtype": "Select",
            "options": "\nNorth\nSouth\nEast\nWest",
            "insert_after": "commission_rate",
            "translatable": 0,
            "in_standard_filter": 1,
            "description": "Sales zone this person covers.",
        },
    ],

    # ── Address: Zone (auto-derived from the State; editable). One field covers bill-to & ship-to. ──
    "Address": [
        {
            "fieldname": "zone",
            "label": "Zone",
            "fieldtype": "Select",
            "options": "\nNorth\nSouth\nEast\nWest",
            "insert_after": "gst_state",
            "translatable": 0,
            "in_standard_filter": 1,
            "description": "Auto-set from the State on save; editable.",
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
            # Mandate Documents as a multi-file grid: one row per customer file, tagged by Type.
            # Replaces the single-file cs_po_copy / cs_test_certificates / cs_client_order_confirmation
            # Attach fields (hidden via property setters). allow_on_submit — POs/certs/confirmations
            # can arrive after the order is submitted, and the DN auto-attach reads it post-submit.
            "fieldname": "cs_mandate_documents",
            "label": "Documents",
            "fieldtype": "Table",
            "options": "CS Mandate Document",
            "insert_after": "cs_docs_section",
            "allow_on_submit": 1,
            "description": "Upload all customer-mandated documents (PO copies, test certificates, "
                           "client order confirmation …) — add a row per file, or use the "
                           "'Upload Documents' button to attach several at once.",
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
        # Dispatch-documents checklist (goods invoices) — enforced in events/sales_invoice.py.
        {
            "fieldname": "cs_dispatch_section",
            "label": "Dispatch Documents",
            "fieldtype": "Section Break",
            "insert_after": "custom_cheque_copy",
            "collapsible": 1,
            "description": "Documents required before finalizing a goods invoice. Tick each (attach "
                           "the file if you have it). All except 'Vehicle photo at dispatch' are "
                           "mandatory before the invoice can be submitted.",
        },
        {
            "fieldname": "cs_dispatch_docs_status",
            "label": "Documents Status",
            "fieldtype": "Select",
            "options": "Incomplete\nComplete",
            "default": "Incomplete",
            "insert_after": "cs_dispatch_section",
            "read_only": 1,
            "translatable": 0,
            "in_standard_filter": 1,
            "allow_on_submit": 1,
            "description": "Auto-set: Complete when all mandatory dispatch documents are ticked.",
        },
        {
            "fieldname": "cs_dispatch_documents",
            "label": "Documents Checklist",
            "fieldtype": "Table",
            "options": "CS Dispatch Document",
            "insert_after": "cs_dispatch_docs_status",
            "allow_on_submit": 1,
            "description": "Photos of boxes, MTC for all parts, Raw material MTC, Traceability report, "
                           "E-way bill Part A, Packaging List, LR copy, Weight Receipt (mandatory) + "
                           "Vehicle photo at dispatch (optional).",
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


# ── SITC / Project (BOQ) — same fields on Quotation AND Sales Order so make_sales_order carries them ──
# For SITC (Supply, Installation, Testing & Commissioning) project quotes the salesperson writes a scope,
# attaches the BOQ, and enters ONE lump-sum line — no 30-40 rows. The fields carry to the SO for execution.
SITC_ITEM_CODE = "KL-SITC-001"
_SITC_FIELDS = [
    {
        "fieldname": "cs_sitc_section",
        "label": "SITC / Project",
        "fieldtype": "Section Break",
        "insert_after": "order_type",
        "collapsible": 1,
    },
    {
        "fieldname": "cs_project_type",
        "label": "Project Type",
        "fieldtype": "Select",
        "options": "Standard\nSITC / Project",
        "default": "Standard",
        "insert_after": "cs_sitc_section",
        "in_standard_filter": 1,
        "translatable": 0,
        "description": "Choose 'SITC / Project' for a BOQ-based quote — enter one lump-sum line and attach "
                       "the BOQ instead of 30-40 rows.",
    },
    {
        "fieldname": "cs_scope_of_work",
        "label": "Scope of Work",
        "fieldtype": "Text Editor",
        "insert_after": "cs_project_type",
        "depends_on": "eval:doc.cs_project_type=='SITC / Project'",
        "description": "Free-text scope for the SITC / project quotation.",
    },
    {
        "fieldname": "cs_boq_file",
        "label": "BOQ File",
        "fieldtype": "Attach",
        "insert_after": "cs_scope_of_work",
        "depends_on": "eval:doc.cs_project_type=='SITC / Project'",
        "mandatory_depends_on": "eval:doc.cs_project_type=='SITC / Project'",
        "description": "Attach the Bill of Quantities (Excel/PDF). Required for SITC / Project quotes.",
    },
]
CUSTOM_FIELDS["Quotation"] = list(_SITC_FIELDS)
CUSTOM_FIELDS["Sales Order"] = CUSTOM_FIELDS["Sales Order"] + list(_SITC_FIELDS)

# ── Optional Packaging & Forwarding (P&F) charge — same fields on Quotation, Sales Order and Sales
# Invoice (identical fieldnames so they ride the stock mappers). Ticking cs_add_pf adds a P&F charge
# (% of net total) BEFORE tax and restructures the GST rows so GST is charged on it — see events/pf.py.
_PF_FIELDS = [
    {
        "fieldname": "cs_add_pf",
        "label": "Add Packaging & Forwarding (P&F)",
        "fieldtype": "Check",
        "default": "1",
        "insert_after": "taxes_and_charges",
        "description": "Add a Packaging & Forwarding charge (% of net total) before tax — GST is "
                       "charged on it. On by default; uncheck to skip. Applied when you Save.",
    },
    {
        "fieldname": "cs_pf_rate",
        "label": "P&F Rate (%)",
        "fieldtype": "Percent",
        "default": "1.5",
        "insert_after": "cs_add_pf",
        "depends_on": "eval:doc.cs_add_pf",
        "description": "Packaging & Forwarding rate applied on the net total. Default 1.5%.",
    },
]
CUSTOM_FIELDS["Quotation"] = CUSTOM_FIELDS["Quotation"] + list(_PF_FIELDS)
CUSTOM_FIELDS["Sales Order"] = CUSTOM_FIELDS["Sales Order"] + list(_PF_FIELDS)
CUSTOM_FIELDS["Sales Invoice"] = CUSTOM_FIELDS["Sales Invoice"] + list(_PF_FIELDS)

# ── Quotation: conversion status — auto 'Accepted' when a Sales Order is created from it (see
# events/sales_order.on_submit); otherwise the user marks Converted / Not Converted (+ a reason). ──
_QUOTATION_STATUS_FIELDS = [
    {
        "fieldname": "cs_conversion_status",
        "label": "Conversion Status",
        "fieldtype": "Select",
        "options": "\nAccepted\nConverted\nNot Converted",
        "insert_after": "order_type",
        "translatable": 0,
        "in_standard_filter": 1,
        "allow_on_submit": 1,
        "description": "Auto-set to 'Accepted' when a Sales Order is created from this quotation; "
                       "otherwise mark it Converted or Not Converted.",
    },
    {
        "fieldname": "cs_not_converted_reason",
        "label": "Not Converted — Reason",
        "fieldtype": "Small Text",
        "insert_after": "cs_conversion_status",
        "depends_on": "eval:doc.cs_conversion_status=='Not Converted'",
        "mandatory_depends_on": "eval:doc.cs_conversion_status=='Not Converted'",
        "allow_on_submit": 1,
    },
]
CUSTOM_FIELDS["Quotation"] = CUSTOM_FIELDS["Quotation"] + list(_QUOTATION_STATUS_FIELDS)

# ── Quotation: back-link to the Sales Enquiry it was created from (set by the mapper). On save,
# events/quotation.on_update backfills the enquiry's Quotation number/value/date + status. ──
_QUOTATION_ENQUIRY_FIELDS = [
    {
        "fieldname": "cs_sales_enquiry",
        "label": "Sales Enquiry",
        "fieldtype": "Link",
        "options": "Sales Enquiry",
        "insert_after": "cs_conversion_status",
        "read_only": 1,
        "description": "The enquiry this quotation was raised from (auto-set via 'Create Quotation').",
    },
]
CUSTOM_FIELDS["Quotation"] = CUSTOM_FIELDS["Quotation"] + list(_QUOTATION_ENQUIRY_FIELDS)

# ── Quotation: Discount Matrix cap + Sales-Head approval (mirrors the Sales Order gate) ──
_QUOTATION_DISCOUNT_FIELDS = [
    {
        "fieldname": "cs_discount_threshold",
        "label": "Discount Threshold (%)",
        "fieldtype": "Percent",
        "insert_after": "cs_not_converted_reason",
        "read_only": 1,
        "description": "Maximum discount before Sales-Head approval (from the Discount Matrix for "
                       "this customer type).",
    },
    {
        "fieldname": "cs_discount_approval_status",
        "label": "Discount Approval Status",
        "fieldtype": "Select",
        "options": "\nNot Required\nDiscount Approval — Sales Head\nApproved\nRejected",
        "default": "Not Required",
        "insert_after": "cs_discount_threshold",
        "read_only": 1,
        "translatable": 0,
        "in_standard_filter": 1,
    },
    {
        "fieldname": "cs_discount_approved_by",
        "label": "Discount Approved By",
        "fieldtype": "Link",
        "options": "User",
        "insert_after": "cs_discount_approval_status",
        "read_only": 1,
    },
]
CUSTOM_FIELDS["Quotation"] = CUSTOM_FIELDS["Quotation"] + list(_QUOTATION_DISCOUNT_FIELDS)

# ── Quotation: optional Product Image on the print (manual image per line) + TDS datasheet merge ──
_QUOTATION_DOC_FIELDS = [
    {
        "fieldname": "cs_show_product_image",
        "label": "Show Product Image",
        "fieldtype": "Check",
        "insert_after": "order_type",
        "description": "Show a product image column on the quotation printout (upload the image on "
                       "each item row below).",
    },
    {
        "fieldname": "cs_add_tds",
        "label": "TDS for Quotation (attach datasheets)",
        "fieldtype": "Check",
        "insert_after": "cs_show_product_image",
        "description": "Merge the Technical Data Sheets of the quotation's items into one PDF "
                       "(use the 'Download TDS Pack' button). Set each item's TDS on the Item master.",
    },
]
CUSTOM_FIELDS["Quotation"] = CUSTOM_FIELDS["Quotation"] + list(_QUOTATION_DOC_FIELDS)

# ── Quotation: Sales Team table (like the Sales Order) — standard field + child doctype, so ERPNext
# computes each row's Contribution to Net Amount from the Contribution %. ──
_QUOTATION_SALES_TEAM_FIELDS = [
    {
        "fieldname": "cs_sales_team_section",
        "label": "Sales Team",
        "fieldtype": "Section Break",
        "insert_after": "additional_info_section",
        "collapsible": 1,
    },
    {
        "fieldname": "sales_team",
        "label": "Sales Team",
        "fieldtype": "Table",
        "options": "Sales Team",
        "insert_after": "cs_sales_team_section",
    },
]
CUSTOM_FIELDS["Quotation"] = CUSTOM_FIELDS["Quotation"] + list(_QUOTATION_SALES_TEAM_FIELDS)

# Per-line manual product image on the quotation grid.
CUSTOM_FIELDS["Quotation Item"] = [
    {
        "fieldname": "cs_product_image",
        "label": "Product Image",
        "fieldtype": "Attach Image",
        "insert_after": "image",
        "in_list_view": 0,   # Attach Image can't be a grid column — attach via the line's detail view
        "description": "Optional image for this line (open the line to attach) — shown on the quotation "
                       "printout; falls back to the Item's own Image.",
    },
    {
        "fieldname": "cs_tds_file",
        "label": "TDS (this line)",
        "fieldtype": "Attach",
        "insert_after": "cs_product_image",
        "description": "Optional TDS PDF for this line — used by 'Download TDS Pack' (falls back to the Item's "
                       "TDS on the master).",
    },
]

# Technical Data Sheet (TDS) PDF on the Item master — the 'datasheet bank'.
CUSTOM_FIELDS["Item"] = CUSTOM_FIELDS.get("Item", []) + [
    {
        "fieldname": "cs_tds_file",
        "label": "Technical Data Sheet (PDF)",
        "fieldtype": "Attach",
        "insert_after": "image",
        "description": "Product Technical Data Sheet (PDF). Merged into the TDS pack on quotations.",
    },
]

# Company-wide standard datasheet, prepended to the TDS pack (always available for download).
CUSTOM_FIELDS["Company"] = CUSTOM_FIELDS.get("Company", []) + [
    {
        "fieldname": "cs_standard_datasheet",
        "label": "Standard Datasheet (PDF)",
        "fieldtype": "Attach",
        "insert_after": "company_logo",
        "description": "Company standard datasheet (PDF), prepended to the TDS pack on quotations.",
    },
]


# Delivery Note + Sales Order: make the per-item Required Delivery Date picker reject the past
# client-side as well (server-side enforced in events). Property setter sets min on the field
# is not supported declaratively, so client scripts handle the picker bound; here we only relabel
# the Delivery Note default print format to the consolidated "Delivery Challan".
PROPERTY_SETTERS = [
    # Retired RC "Deviation" gate — hide its now-unused fields (the single Discount-Approval gate
    # covers RC customers). Fields kept in schema for existing records' audit trail.
    {"doctype_or_field": "Field", "doctype": "Sales Order", "fieldname": "custom_rc_deviation",
     "property": "hidden", "value": "1", "property_type": "Check"},
    {"doctype_or_field": "Field", "doctype": "Sales Order", "fieldname": "custom_deviation_approval_status",
     "property": "hidden", "value": "1", "property_type": "Check"},
    {"doctype_or_field": "Field", "doctype": "Sales Order", "fieldname": "custom_deviation_approved_by",
     "property": "hidden", "value": "1", "property_type": "Check"},
    {
        "doctype_or_field": "DocType",
        "doctype": "Delivery Note",
        "property": "default_print_format",
        "value": "Delivery Challan",
        "property_type": "Data",
    },
    {
        # Plant Order prints the plain "Plant Order" layout (items/qty/dates, no pricing) by default.
        "doctype_or_field": "DocType",
        "doctype": "KM Order",
        "property": "default_print_format",
        "value": "Plant Order",
        "property_type": "Data",
    },
    {
        # Sales Invoice prints the Tally-style "Klemco Tax Invoice" (GST) layout by default.
        "doctype_or_field": "DocType",
        "doctype": "Sales Invoice",
        "property": "default_print_format",
        "value": "Klemco Tax Invoice",
        "property_type": "Data",
    },
    {
        # Quotation prints the branded "Klemco Quotation" letterhead layout by default.
        "doctype_or_field": "DocType",
        "doctype": "Quotation",
        "property": "default_print_format",
        "value": "Klemco Quotation",
        "property_type": "Data",
    },
    # B2B default: new Addresses default to Registered Regular. India Compliance still derives the
    # real category from the GSTIN on save — it stays Registered when a GSTIN is entered, and reverts
    # to Unregistered (India) / Overseas gracefully when there's none (no validation error).
    {
        "doctype_or_field": "Field",
        "doctype": "Address",
        "fieldname": "gst_category",
        "property": "default",
        "value": "Registered Regular",
        "property_type": "Text",
    },
    # KM Order: clear the title field so the order number (KMPO-…) is the clickable link in the list
    # (Frappe uses `name` as the subject link when there's no title_field). Customer stays a column.
    {
        "doctype_or_field": "DocType",
        "doctype": "KM Order",
        "property": "title_field",
        "value": "",
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
     "property": "columns", "value": "3", "property_type": "Int"},
    {"doctype_or_field": "Field", "doctype": "Sales Order Item", "fieldname": "delivery_date",
     "property": "columns", "value": "2", "property_type": "Int"},
    # Required Delivery Date removed — redundant with the standard per-line Delivery Date (which is also
    # per-line and back-date-validated). Keep one date column; the Open-order rule now targets delivery_date.
    {"doctype_or_field": "Field", "doctype": "Sales Order Item", "fieldname": "cs_required_delivery_date",
     "property": "in_list_view", "value": "0", "property_type": "Check"},
    {"doctype_or_field": "Field", "doctype": "Sales Order Item", "fieldname": "cs_required_delivery_date",
     "property": "hidden", "value": "1", "property_type": "Check"},
    {"doctype_or_field": "Field", "doctype": "Sales Order Item", "fieldname": "qty",
     "property": "columns", "value": "1", "property_type": "Int"},
    {"doctype_or_field": "Field", "doctype": "Sales Order Item", "fieldname": "uom",
     "property": "columns", "value": "1", "property_type": "Int"},
    {"doctype_or_field": "Field", "doctype": "Sales Order Item", "fieldname": "rate",
     "property": "columns", "value": "1", "property_type": "Int"},
    {"doctype_or_field": "Field", "doctype": "Sales Order Item", "fieldname": "amount",
     "property": "columns", "value": "1", "property_type": "Int"},
    # Per-line discount: surface ERPNext's own `discount_percentage` as an editable grid column so a
    # discount can be customised per item (the header "Discount Threshold (%)" is only the approval CAP,
    # BR-OE-01 — not a discount that gets applied). depends_on:price_list_rate stays, so it only appears
    # once a priced item is on the row (safe — no discount against a ₹0 base). The CS client script still
    # locks it read-only for RC (Rate Contract) customers (BR-SO-01). Width 1 → grid total 9 (≤10).
    {"doctype_or_field": "Field", "doctype": "Sales Order Item", "fieldname": "discount_percentage",
     "property": "in_list_view", "value": "1", "property_type": "Check"},
    {"doctype_or_field": "Field", "doctype": "Sales Order Item", "fieldname": "discount_percentage",
     "property": "columns", "value": "1", "property_type": "Int"},
    # Show the customer's PO number in the Sales Order list. in_list_view makes it an eligible
    # column; _ensure_so_list_columns() positions it (2nd) via List View Settings, else at idx 205
    # it renders last (off-screen behind the progress columns).
    {"doctype_or_field": "Field", "doctype": "Sales Order", "fieldname": "po_no",
     "property": "in_list_view", "value": "1", "property_type": "Check"},
    # Dispatch & Tracking moved to the Delivery Note (warehouse captures it at dispatch) —
    # hide these on the Sales Order, which locks after submit. Client Order Confirmation stays.
    {"doctype_or_field": "Field", "doctype": "Sales Order", "fieldname": "cs_docket_number",
     "property": "hidden", "value": "1", "property_type": "Check"},
    {"doctype_or_field": "Field", "doctype": "Sales Order", "fieldname": "cs_tracking_url",
     "property": "hidden", "value": "1", "property_type": "Check"},
    {"doctype_or_field": "Field", "doctype": "Sales Order", "fieldname": "cs_pod_attachment",
     "property": "hidden", "value": "1", "property_type": "Check"},
    # Mandate Documents are now the multi-file cs_mandate_documents grid — hide the old single-file
    # Attach fields and the (now empty) section that held Client Order Confirmation.
    {"doctype_or_field": "Field", "doctype": "Sales Order", "fieldname": "cs_po_copy",
     "property": "hidden", "value": "1", "property_type": "Check"},
    {"doctype_or_field": "Field", "doctype": "Sales Order", "fieldname": "cs_col5",
     "property": "hidden", "value": "1", "property_type": "Check"},
    {"doctype_or_field": "Field", "doctype": "Sales Order", "fieldname": "cs_test_certificates",
     "property": "hidden", "value": "1", "property_type": "Check"},
    {"doctype_or_field": "Field", "doctype": "Sales Order", "fieldname": "cs_client_order_confirmation",
     "property": "hidden", "value": "1", "property_type": "Check"},
    {"doctype_or_field": "Field", "doctype": "Sales Order", "fieldname": "cs_dispatch_section",
     "property": "hidden", "value": "1", "property_type": "Check"},
    # Declutter the More Info tab — hide stock ERPNext sections Klemco doesn't use. Keep the Status
    # meters (% Delivered/Billed) and the Customer's PO No./Date under Additional Info.
    #   Auto Repeat (recurring/subscription orders)
    {"doctype_or_field": "Field", "doctype": "Sales Order", "fieldname": "subscription_section",
     "property": "hidden", "value": "1", "property_type": "Check"},
    {"doctype_or_field": "Field", "doctype": "Sales Order", "fieldname": "from_date",
     "property": "hidden", "value": "1", "property_type": "Check"},
    {"doctype_or_field": "Field", "doctype": "Sales Order", "fieldname": "to_date",
     "property": "hidden", "value": "1", "property_type": "Check"},
    {"doctype_or_field": "Field", "doctype": "Sales Order", "fieldname": "auto_repeat",
     "property": "hidden", "value": "1", "property_type": "Check"},
    {"doctype_or_field": "Field", "doctype": "Sales Order", "fieldname": "update_auto_repeat_reference",
     "property": "hidden", "value": "1", "property_type": "Check"},
    #   UTM Analytics (marketing attribution)
    {"doctype_or_field": "Field", "doctype": "Sales Order", "fieldname": "utm_analytics_section",
     "property": "hidden", "value": "1", "property_type": "Check"},
    {"doctype_or_field": "Field", "doctype": "Sales Order", "fieldname": "utm_source",
     "property": "hidden", "value": "1", "property_type": "Check"},
    {"doctype_or_field": "Field", "doctype": "Sales Order", "fieldname": "utm_medium",
     "property": "hidden", "value": "1", "property_type": "Check"},
    {"doctype_or_field": "Field", "doctype": "Sales Order", "fieldname": "utm_campaign",
     "property": "hidden", "value": "1", "property_type": "Check"},
    {"doctype_or_field": "Field", "doctype": "Sales Order", "fieldname": "utm_content",
     "property": "hidden", "value": "1", "property_type": "Check"},
    #   Additional Info — hide inter-company fields only (keep Customer PO No./Date)
    {"doctype_or_field": "Field", "doctype": "Sales Order", "fieldname": "is_internal_customer",
     "property": "hidden", "value": "1", "property_type": "Check"},
    {"doctype_or_field": "Field", "doctype": "Sales Order", "fieldname": "represents_company",
     "property": "hidden", "value": "1", "property_type": "Check"},
    {"doctype_or_field": "Field", "doctype": "Sales Order", "fieldname": "inter_company_order_reference",
     "property": "hidden", "value": "1", "property_type": "Check"},
    # Simplify the Delivery Note form — hide sections Klemco doesn't use. Keep Items, Taxes/Totals,
    # Dispatch & Tracking, Customer PO, Status, and the GST/Transporter sections (compliance + dispatch
    # email). Currency/Price List reqd fields auto-fill from the SO, so hiding that section is safe.
    {"doctype_or_field": "Field", "doctype": "Delivery Note", "fieldname": "accounting_dimensions_section",
     "property": "hidden", "value": "1", "property_type": "Check"},
    {"doctype_or_field": "Field", "doctype": "Delivery Note", "fieldname": "currency_and_price_list",
     "property": "hidden", "value": "1", "property_type": "Check"},
    {"doctype_or_field": "Field", "doctype": "Delivery Note", "fieldname": "section_break_49",
     "property": "hidden", "value": "1", "property_type": "Check"},
    {"doctype_or_field": "Field", "doctype": "Delivery Note", "fieldname": "sec_tax_breakup",
     "property": "hidden", "value": "1", "property_type": "Check"},
    {"doctype_or_field": "Field", "doctype": "Delivery Note", "fieldname": "section_gst_breakup",
     "property": "hidden", "value": "1", "property_type": "Check"},
    {"doctype_or_field": "Field", "doctype": "Delivery Note", "fieldname": "pricing_rule_details",
     "property": "hidden", "value": "1", "property_type": "Check"},
    {"doctype_or_field": "Field", "doctype": "Delivery Note", "fieldname": "sales_team_section_break",
     "property": "hidden", "value": "1", "property_type": "Check"},
    {"doctype_or_field": "Field", "doctype": "Delivery Note", "fieldname": "section_break1",
     "property": "hidden", "value": "1", "property_type": "Check"},
    {"doctype_or_field": "Field", "doctype": "Delivery Note", "fieldname": "subscription_section",
     "property": "hidden", "value": "1", "property_type": "Check"},
    {"doctype_or_field": "Field", "doctype": "Delivery Note", "fieldname": "printing_details",
     "property": "hidden", "value": "1", "property_type": "Check"},
    {"doctype_or_field": "Field", "doctype": "Delivery Note", "fieldname": "utm_analytics_section",
     "property": "hidden", "value": "1", "property_type": "Check"},
    {"doctype_or_field": "Field", "doctype": "Delivery Note", "fieldname": "more_info",
     "property": "hidden", "value": "1", "property_type": "Check"},
    # Quotation More-Info declutter: hide UTM Analytics + Additional Info (status auto-managed).
    {"doctype_or_field": "Field", "doctype": "Quotation", "fieldname": "utm_analytics_section",
     "property": "hidden", "value": "1", "property_type": "Check"},
    {"doctype_or_field": "Field", "doctype": "Quotation", "fieldname": "utm_source",
     "property": "hidden", "value": "1", "property_type": "Check"},
    {"doctype_or_field": "Field", "doctype": "Quotation", "fieldname": "utm_medium",
     "property": "hidden", "value": "1", "property_type": "Check"},
    {"doctype_or_field": "Field", "doctype": "Quotation", "fieldname": "utm_campaign",
     "property": "hidden", "value": "1", "property_type": "Check"},
    {"doctype_or_field": "Field", "doctype": "Quotation", "fieldname": "utm_content",
     "property": "hidden", "value": "1", "property_type": "Check"},
    {"doctype_or_field": "Field", "doctype": "Quotation", "fieldname": "additional_info_section",
     "property": "hidden", "value": "1", "property_type": "Check"},
    {"doctype_or_field": "Field", "doctype": "Quotation", "fieldname": "status",
     "property": "hidden", "value": "1", "property_type": "Check"},
    {"doctype_or_field": "Field", "doctype": "Quotation", "fieldname": "territory",
     "property": "hidden", "value": "1", "property_type": "Check"},
    {"doctype_or_field": "Field", "doctype": "Quotation", "fieldname": "opportunity",
     "property": "hidden", "value": "1", "property_type": "Check"},
    {"doctype_or_field": "Field", "doctype": "Quotation", "fieldname": "supplier_quotation",
     "property": "hidden", "value": "1", "property_type": "Check"},
    {
        "doctype_or_field": "Field",
        "doctype": "Quotation Item",
        "fieldname": "uom",
        "property": "in_list_view",
        "value": "1",
        "property_type": "Check",
    },
    # Item Name is always derived from Item Code (the server fills it on save), so it need not be a
    # mandatory field. Making it optional lets rows added via the grid Upload / Excel import (which
    # sets Item Code but not Item Name) save instead of being blocked by the client mandatory check.
    {"doctype_or_field": "Field", "doctype": "Sales Order Item", "fieldname": "item_name",
     "property": "reqd", "value": "0", "property_type": "Check"},
    {"doctype_or_field": "Field", "doctype": "Quotation Item", "fieldname": "item_name",
     "property": "reqd", "value": "0", "property_type": "Check"},
    # Product image + TDS are now fully automatic from the Item master — hide the toggles (no
    # user intervention): the image column auto-shows when any item has an image, and the TDS
    # button auto-appears when any item has a datasheet.
    {"doctype_or_field": "Field", "doctype": "Quotation", "fieldname": "cs_show_product_image",
     "property": "hidden", "value": "1", "property_type": "Check"},
    {"doctype_or_field": "Field", "doctype": "Quotation", "fieldname": "cs_add_tds",
     "property": "hidden", "value": "1", "property_type": "Check"},
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
    _ensure_stock_allocation()
    _ensure_discount_matrix()
    _ensure_ic_stock_entry_taxes_field()
    _ensure_default_company()
    _ensure_pf_accounts()
    _ensure_tax_simplification()
    _ensure_order_reports()
    _ensure_worklist_reports()
    _ensure_cs_sidebar()
    create_custom_fields(CUSTOM_FIELDS, update=True)
    _ensure_address_zones()
    _ensure_company_print_details()
    # Print formats first — a `default_print_format` property setter is skipped if its format
    # doesn't exist yet (see _apply_property_setters), so create them before applying setters.
    _ensure_delivery_challan_print_format()
    _ensure_proforma_print_formats()
    _ensure_klemco_tax_invoice()
    _ensure_quotation_print_format()
    _apply_property_setters()
    _ensure_so_list_columns()
    _ensure_sitc_item()
    _ensure_km_supplier()
    _ensure_quotation_override()
    _ensure_plant_order_labels()
    frappe.clear_cache()


def _ensure_address_zones():
    """Backfill the Zone on any Address that has a State but no Zone (idempotent — never overwrites
    a manual value). Uses the same state->zone map as the Address auto-fill event."""
    from klemco_cs.events.address import zone_for
    meta = frappe.get_meta("Address")
    state_fields = [f for f in ("gst_state", "state") if meta.has_field(f)]
    if not state_fields:  # e.g. a site without India Compliance
        return
    for a in frappe.get_all("Address",
                            filters={"zone": ["in", [None, ""]]},
                            fields=["name"] + state_fields):
        z = zone_for(a.get("gst_state") or a.get("state"))
        if z:
            frappe.db.set_value("Address", a.name, "zone", z, update_modified=False)


def _ensure_tax_simplification():
    """Hide the manual Tax Category / template pickers on Quotation, Sales Order and Sales Invoice.
    GST is applied automatically as a flat 18% split — In-State CGST 9% + SGST 9%, Out-State IGST 18%
    (events auto-GST) — so users don't pick a tax option."""
    for dt in ("Quotation", "Sales Order", "Sales Invoice"):
        for fn in ("tax_category", "taxes_and_charges"):
            make_property_setter(doctype=dt, fieldname=fn, property="hidden", value="1",
                                 property_type="Check", for_doctype=False,
                                 validate_fields_for_doctype=False)


def _ensure_pf_accounts():
    """Create a 'Packaging and Forwarding Charges' chargeable ledger per company (mirrors the existing
    'Freight and Forwarding Charges' account), so the optional P&F charge row has an account to post
    to. Idempotent; skips companies without an Indirect Expenses parent."""
    for company in frappe.get_all("Company", pluck="name"):
        abbr = frappe.get_cached_value("Company", company, "abbr")
        name = "Packaging and Forwarding Charges - %s" % abbr
        if frappe.db.exists("Account", name):
            continue
        parent = "Indirect Expenses - %s" % abbr
        if not frappe.db.exists("Account", parent):
            continue
        frappe.get_doc({
            "doctype": "Account",
            "account_name": "Packaging and Forwarding Charges",
            "parent_account": parent,
            "company": company,
            "account_type": "Chargeable",
            "root_type": "Expense",
            "is_group": 0,
        }).insert(ignore_permissions=True)


# Relabel "KM / Klemco Order" → "Plant Order" across the desk via Translation records. The internal
# DocType stays "KM Order" (table, code, links, method paths unchanged), so nothing breaks — only the
# display text is relabelled anywhere it passes through __() / _().
PLANT_ORDER_LABELS = {
    "KM Order": "Plant Order",
    "KM Orders": "Plant Orders",
    "KM Order Item": "Plant Order Item",
    "Klemco Order": "Plant Order",
    "Klemco Orders": "Plant Orders",
    "New Klemco Order": "New Plant Order",
    "All Klemco Orders": "All Plant Orders",
    "Klemco Orders — Created": "Plant Orders — Created",
    "Klemco production": "Plant production",
}


def _ensure_plant_order_labels():
    for src, tgt in PLANT_ORDER_LABELS.items():
        if not frappe.db.exists("Translation", {"source_text": src, "language": "en"}):
            frappe.get_doc({
                "doctype": "Translation", "language": "en",
                "source_text": src, "translated_text": tgt,
            }).insert(ignore_permissions=True)


def _ensure_quotation_override():
    """A Quotation is a non-binding estimate — a Sales Order may override its quantity and rate.
    - over_delivery_receipt_allowance high ⇒ SO qty is never blocked against the quoted qty (this shared
      Stock Settings knob also loosens DN over-delivery / PR over-receipt, both bounded by the stock guard).
    - maintain_same_sales_rate off ⇒ the SO rate can differ from the quotation."""
    if frappe.db.get_single_value("Stock Settings", "over_delivery_receipt_allowance") != 100000:
        frappe.db.set_single_value("Stock Settings", "over_delivery_receipt_allowance", 100000)
    if frappe.db.get_single_value("Selling Settings", "maintain_same_sales_rate"):
        frappe.db.set_single_value("Selling Settings", "maintain_same_sales_rate", 0)


def _ensure_km_supplier():
    """Default supplier billed for a KM (manufacturing) order's purchase bill."""
    name = "Klemco Manufacturing"
    if frappe.db.exists("Supplier", name):
        return
    group = None
    for g in ("Local", "Raw Material", "Services"):
        if frappe.db.exists("Supplier Group", g):
            group = g
            break
    if not group:
        picks = frappe.get_all("Supplier Group", filters={"is_group": 0}, limit=1, pluck="name")
        group = picks[0] if picks else "All Supplier Groups"
    frappe.get_doc({
        "doctype": "Supplier",
        "supplier_name": name,
        "supplier_group": group,
        "country": "India",
        "gst_category": "Unregistered",
    }).insert(ignore_permissions=True)


# Sales Order list columns (order + selection). Frappe renders list columns in field order and
# `po_no` sits last (idx 205), so a List View Settings.fields config is needed to place it up front.
# Only fields with in_list_view=1 are eligible (see the po_no property setter above). Status uses the
# sentinel fieldname "status_field"; the title field (customer_name) is the fixed subject and omitted.
# % Amount Billed (per_billed) is dropped from the list to keep the row readable with PO added.
SO_LIST_COLUMNS = [
    {"label": "Status", "fieldname": "status_field"},
    {"label": "Customer's Purchase Order", "fieldname": "po_no"},
    {"label": "Delivery Date", "fieldname": "delivery_date"},
    {"label": "Grand Total", "fieldname": "grand_total"},
    {"label": "Discount Approval Status", "fieldname": "cs_discount_approval_status"},
    {"label": "Credit Hold Status", "fieldname": "cs_credit_hold_status"},
    {"label": "% Delivered", "fieldname": "per_delivered"},
]


def _ensure_so_list_columns():
    """Put the customer's PO number on the Sales Order list, positioned right after Status."""
    import json
    fields = json.dumps(SO_LIST_COLUMNS)
    if frappe.db.exists("List View Settings", "Sales Order"):
        if frappe.db.get_value("List View Settings", "Sales Order", "fields") != fields:
            frappe.db.set_value("List View Settings", "Sales Order", "fields", fields)
    else:
        frappe.get_doc({
            "doctype": "List View Settings", "name": "Sales Order", "fields": fields,
        }).insert(ignore_permissions=True)


def _ensure_sitc_item():
    """A single lump-sum service item for SITC / Project (BOQ) quotes. Non-stock (no delivery/stock
    block; the DN stock guard exempts it) with a works/installation SAC so GST + SO/DN/Invoice submit."""
    if frappe.db.exists("Item", SITC_ITEM_CODE):
        return
    group = ("Installation Services" if frappe.db.exists("Item Group", "Installation Services")
             else ("Services" if frappe.db.exists("Item Group", "Services") else "All Item Groups"))
    item = {
        "doctype": "Item",
        "item_code": SITC_ITEM_CODE,
        "item_name": "SITC Works (as per BOQ)",
        "item_group": group,
        "stock_uom": "Nos",
        "is_stock_item": 0,
        "is_sales_item": 1,
        "is_purchase_item": 0,
        "description": "Lump-sum SITC / project works billed as per the attached BOQ.",
    }
    if frappe.db.exists("GST HSN Code", "995461"):
        item["gst_hsn_code"] = "995461"   # works/installation SAC (UAT placeholder)
    frappe.get_doc(item).insert(ignore_permissions=True)


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


def _ensure_stock_allocation():
    """Stock-allocation rule: when an order is for more than is in stock, reserve the available
    quantity to that order (FIFO — first confirmed reserves first) and backorder the shortfall.
    ERPNext's native Stock Reservation does exactly this: auto_reserve_stock earmarks available stock
    on Sales Order submit, and allow_partial_reservation reserves the available portion when short.
    Idempotent; guarded on field existence."""
    meta = frappe.get_meta("Stock Settings")
    wanted = {
        "enable_stock_reservation": 1,   # turn the feature on
        "auto_reserve_stock": 1,         # auto-reserve available stock when a Sales Order is submitted
        "allow_partial_reservation": 1,  # reserve what's available when stock is short (rest = backorder)
        "valuation_method": "FIFO",      # stock consumed on delivery/billing is costed oldest-first (FIFO)
    }
    for field, value in wanted.items():
        if not meta.get_field(field):
            continue
        if frappe.db.get_single_value("Stock Settings", field) != value:
            frappe.db.set_single_value("Stock Settings", field, value)


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


# The full Customer Service left-nav (Workspace Sidebar) — authoritative layout, enforced on every
# migrate by _ensure_cs_sidebar(). Section Break = group header; Link → its DocType/Report/URL/Workspace.
# (l = Link helper.)
# A group header is a Section Break at indent=1 with an icon (this is what renders the collapsible
# expand arrow); its member links follow at indent=0 until the next Section Break. Matches the stock
# desk sidebars (e.g. Selling → POS / Items & Pricing / Setup).
# A group is a Section Break header (child=0, indent=1, icon) followed by member Links with
# child=1 — find_nested_items() (sidebar.js) nests a link under the preceding section ONLY when
# child=1, and that nesting is what the collapse/expand arrow shows/hides. Home is a top-level
# link (child=0). Matches the stock desk sidebars.
def _sb(label, icon):
    return {"type": "Section Break", "label": label, "icon": icon,
            "indent": 1, "child": 0, "collapsible": 1}


def _l(label, link_type, link_to="", url="", child=1):
    return {"type": "Link", "label": label, "link_type": link_type, "link_to": link_to,
            "url": url, "icon": "", "indent": 0, "child": child, "collapsible": 1}


SIDEBAR_STRUCTURE = [
    _l("Home", "Workspace", "Customer Service", child=0),
    _sb("Complaint", "alert-circle"),
    _l("New Complaint", "URL", url="/desk/cs-complaint/new"),
    _l("All Complaint", "DocType", "CS Complaint"),
    _sb("Enquiries", "unread"),
    _l("New Sales Enquiry", "URL", url="/desk/sales-enquiry/new"),
    _l("All Enquiries", "DocType", "Sales Enquiry"),
    _l("Open Enquiries", "Report", "Open Sales Enquiries"),
    _l("Enquiries — Created", "Report", "Sales Enquiries — Created"),
    _sb("Order Creation", "sell"),
    _l("New Sales Order", "URL", url="/desk/sales-order/new"),
    _l("Open Sales Order", "Report", "Open Sales Orders"),
    _l("List of Sales order", "Report", "Sales Orders — Created"),
    _l("List of Delivery notes", "DocType", "Delivery Note"),
    _l("Status Delivery Notes", "Report", "Delivery Notes — Created"),
    _l("Sales Invoice List", "DocType", "Sales Invoice"),
    _l("Status Invoices", "Report", "Sales Invoices — Created"),
    _l("Proforma Invoice", "DocType", "Sales Order"),       # generated from an SO via the button
    _l("Quotations — Created", "Report", "Quotations — Created"),
    _l("Sales by Sales Person", "Report", "Sales Person Contribution"),
    _sb("Stock", "stock"),
    _l("Stock List", "Report", "Stock Balance"),
    _l("Stock Check", "Report", "Item Stock and Open Orders"),
    _sb("Approvals", "shield"),
    _l("Orders on Credit Hold", "Report", "Orders on Credit Hold"),
    _l("Pending for Discount Approval", "Report", "Pending Discount Approvals"),
    _l("Quotations — Pending Discount", "Report", "Quotations — Pending Discount Approval"),
    _l("Invoices — Docs Incomplete", "Report", "Sales Invoices — Documents Incomplete"),
    _sb("Plant Orders", "organization"),
    _l("New Plant Order", "URL", url="/desk/km-order/new"),
    _l("All Plant Orders", "DocType", "KM Order"),
    _l("Plant Orders status", "Report", "Klemco Orders — Created"),
    _l("Plant Orders — Items", "Report", "Plant Order Items"),
    _sb("Configuration", "setting"),
    _l("Category Mapping", "DocType", "CS Complaint Category Map"),
    _l("Discount Matrix", "DocType", "CS Discount Matrix"),
    _l("Item", "DocType", "Item"),
    _l("Client Scripts", "DocType", "Client Script"),
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
    # The enquiry "Report form" view: enquiry + the quotation it produced.
    "Sales Enquiries — Created": ("Sales Enquiry",
        ["project_name", "customer", "party_name", "type_of_enquiry", "zone", "status",
         "quotation", "quotation_value"]),
}


def _ensure_report(name, dt, cols, filters=None, widths=None):
    """Create one durable Report-Builder report (idempotent). `cols` are business columns
    (missing ones skipped); Created On + Created By are always appended. `filters` is a list of
    [doctype, fieldname, operator, value] rows for a worklist view. `widths` is an optional
    {column_id: px} map (report_view applies column_widths[column.id])."""
    import json as _json
    if not frappe.db.exists("DocType", dt) or frappe.db.exists("Report", name):
        return
    meta = frappe.get_meta(dt)
    fields = [c for c in cols if meta.get_field(c)] + ["creation", "owner"]
    pairs = [[f, dt] for f in fields]
    cfg = {
        "add_total_row": 0,
        "sort_by": "%s.creation" % dt, "sort_order": "desc",
        "sort_by_next": None, "sort_order_next": "desc",
        "filters": filters or [],
        "columns": pairs,            # newer report-view key
        "fields": pairs,             # older key — set both for loader compatibility
        "order_by": "`tab%s`.`creation` desc" % dt,
    }
    if widths:
        cfg["column_widths"] = widths
    frappe.get_doc({
        "doctype": "Report",
        "report_name": name,
        "ref_doctype": dt,
        "report_type": "Report Builder",
        "is_standard": "No",
        "module": "Customer Service",
        "json": _json.dumps(cfg),
    }).insert(ignore_permissions=True)


def _ensure_order_reports():
    for name, (dt, cols) in ORDER_REPORTS.items():
        # Widen the order-number (name) column on the KM Order report so the full KMPO-… shows.
        widths = {"name": 200} if dt == "KM Order" else None
        _ensure_report(name, dt, cols, widths=widths)


# Approval worklists — the "what's stuck?" lists for discount / credit sign-off.
WORKLIST_REPORTS = {
    "Pending Discount Approvals": ("Sales Order",
        ["customer_name", "grand_total", "cs_discount_threshold", "transaction_date"],
        [["Sales Order", "cs_discount_approval_status", "=", "Discount Approval — Sales Head"]]),
    "Orders on Credit Hold": ("Sales Order",
        ["customer_name", "grand_total", "cs_credit_hold_reason", "transaction_date"],
        [["Sales Order", "cs_credit_hold_status", "=", "On Hold"]]),
    # Every order that isn't finished — drafts + pending fulfilment (not Completed/Cancelled/Closed).
    "Open Sales Orders": ("Sales Order",
        ["customer_name", "status", "transaction_date", "delivery_date", "grand_total",
         "per_delivered", "per_billed"],
        [["Sales Order", "status", "not in", ["Completed", "Cancelled", "Closed"]]]),
    # Draft invoices still missing mandatory dispatch documents (goods invoices).
    "Sales Invoices — Documents Incomplete": ("Sales Invoice",
        ["customer_name", "grand_total", "posting_date", "cs_dispatch_docs_status"],
        [["Sales Invoice", "cs_dispatch_docs_status", "=", "Incomplete"],
         ["Sales Invoice", "docstatus", "=", 0]]),
    # Draft quotations waiting for Sales-Head discount approval.
    "Quotations — Pending Discount Approval": ("Quotation",
        ["party_name", "grand_total", "cs_discount_threshold", "transaction_date"],
        [["Quotation", "cs_discount_approval_status", "=", "Discount Approval — Sales Head"],
         ["Quotation", "docstatus", "=", 0]]),
    # Enquiries still open (not yet quoted, converted or closed).
    "Open Sales Enquiries": ("Sales Enquiry",
        ["project_name", "customer", "party_name", "sales_person", "type_of_enquiry", "enquiry_date"],
        [["Sales Enquiry", "status", "=", "Open"]]),
}


def _ensure_worklist_reports():
    for name, (dt, cols, filters) in WORKLIST_REPORTS.items():
        _ensure_report(name, dt, cols, filters)


def _ensure_cs_sidebar():
    """Enforce the Customer Service left-nav (Workspace Sidebar) = SIDEBAR_STRUCTURE. Authoritative +
    idempotent: rewrites the items only when they differ. Links whose DocType/Report target is missing
    (e.g. a report absent on 8081) are skipped. Wrapped so a nav tweak never blocks a migrate."""
    try:
        if not frappe.db.exists("Workspace Sidebar", "Customer Service"):
            return
        rows = []
        for it in SIDEBAR_STRUCTURE:
            if it["type"] == "Link" and it["link_type"] in ("DocType", "Report") \
                    and not frappe.db.exists(it["link_type"], it["link_to"]):
                continue
            rows.append(it)
        sb = frappe.get_doc("Workspace Sidebar", "Customer Service")
        current = [(i.type, i.label, i.get("link_type") or "", i.get("link_to") or "", i.get("url") or "",
                    i.get("indent") or 0, i.get("icon") or "", i.get("child") or 0) for i in sb.items]
        desired = [(r["type"], r["label"], r.get("link_type", ""), r.get("link_to", ""), r.get("url", ""),
                    r.get("indent", 0), r.get("icon", ""), r.get("child", 0)) for r in rows]
        if current == desired:
            return
        sb.set("items", [])
        for idx, r in enumerate(rows, start=1):
            row = sb.append("items", {
                "type": r["type"], "label": r["label"],
                "link_type": r.get("link_type", ""), "link_to": r.get("link_to", ""), "url": r.get("url", ""),
                "indent": r.get("indent", 0), "icon": r.get("icon", ""),
                "child": r.get("child", 0), "collapsible": r.get("collapsible", 1),
            })
            row.idx = idx
        sb.save(ignore_permissions=True)
    except Exception:
        frappe.log_error(title="klemco_cs: CS sidebar")


def _ensure_billing_controls():
    """A Sales Invoice must originate from a Sales Order for GOODS — no billing for un-ordered
    stock. Enforcement lives in klemco (events.sales_invoice._require_so_for_stock_items), which
    requires an SO for stock items but exempts non-stock service/charge items (freight,
    installation …) added at billing. ERPNext's own Selling Settings.so_required has no per-item
    exemption, so it's turned OFF here in favour of the klemco gate."""
    if frappe.db.get_single_value("Selling Settings", "so_required") != "No":
        frappe.db.set_single_value("Selling Settings", "so_required", "No")
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
    Date: {{ frappe.format(doc.get("transaction_date") or doc.get("posting_date"), {"fieldtype":"Date"}) }}
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
    "Proforma Invoice (Delivery Note)": "Delivery Note",
    "Proforma Invoice (Sales Invoice)": "Sales Invoice",
}

# Plain printout for a Plant Order (no customer pricing on its lines — items/qty/dates only).
PLANT_ORDER_HTML = """
<div style="text-align:center;margin-bottom:6px;">
  <h2 style="margin:0;letter-spacing:1px;">PLANT ORDER</h2>
</div>
<table style="width:100%;font-size:12px;margin-bottom:8px;"><tr>
  <td style="vertical-align:top;">
    <strong>{{ doc.name }}</strong><br>
    Customer: {{ doc.customer or "" }}<br>
    Supplier: {{ doc.supplier or "" }}
  </td>
  <td style="vertical-align:top;text-align:right;">
    Linked Sales Order: {{ doc.linked_sales_order or "-" }}<br>
    Goods Available Date: {{ frappe.format(doc.km_tat_date, {"fieldtype":"Date"}) if doc.km_tat_date else "-" }}<br>
    Status: {{ doc.status }}
  </td>
</tr></table>
<table class="table table-bordered" style="font-size:12px;">
  <thead><tr>
    <th>#</th><th>Item</th><th>Item Name</th><th>Delivery Date</th>
    <th class="text-right">Qty</th><th>UOM</th>
  </tr></thead>
  <tbody>
  {% for row in doc.items %}
    <tr>
      <td>{{ loop.index }}</td>
      <td>{{ row.item_code }}</td>
      <td>{{ row.item_name }}</td>
      <td>{{ frappe.format(row.delivery_date, {"fieldtype":"Date"}) if row.delivery_date else "-" }}</td>
      <td class="text-right">{{ row.km_qty }}</td>
      <td>{{ row.uom }}</td>
    </tr>
  {% endfor %}
  </tbody>
</table>
<p style="font-size:11px;color:#666;margin-top:14px;border-top:1px solid #ddd;padding-top:6px;">
  Internal Plant Order — production instruction. Not a customer invoice.
</p>
""".strip()


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
    # Plant Order printout (no pricing) + make it the default print for a Plant Order.
    if not frappe.db.exists("Print Format", "Plant Order"):
        frappe.get_doc({
            "doctype": "Print Format",
            "name": "Plant Order",
            "doc_type": "KM Order",
            "module": "Customer Service",
            "standard": "No",
            "custom_format": 1,
            "print_format_type": "Jinja",
            "html": PLANT_ORDER_HTML,
        }).insert(ignore_permissions=True)


# ── Klemco Tax Invoice (GST) — Tally-style Sales Invoice print format ────────────────────────────
# Replicates Klemco's current Tally Prime "Tax Invoice / e-Invoice" layout while reusing India
# Compliance's GST data helpers for correctness: doc.gst_breakup_table (HSN-wise tax summary, auto
# IGST vs CGST+SGST), doc.in_words (amount in words), and the guarded IRN/Ack/QR block (blank until
# e-invoicing is enabled + IRP credentials added — the sample's IRN/QR come from Klemco's live Tally,
# which is IRP-connected; ERPNext leaves them empty here, so the block is hidden when doc.irn is unset).
# Seller footer data (UDYAM / CIN / PAN / bank) is read from the Company "…_for_printing" tables,
# seeded by _ensure_company_print_details().
KLEMCO_TAX_INVOICE_HTML = """
{%- set _company = frappe.get_doc("Company", doc.company) %}
<div style="font-size:11px;color:#000;">
  <table style="width:100%;border-collapse:collapse;margin-bottom:4px;">
    <tr>
      <td style="width:70%;vertical-align:top;"><h3 style="margin:0;letter-spacing:1px;">Tax Invoice</h3></td>
      <td style="width:30%;vertical-align:top;text-align:right;">
        <strong>e-Invoice</strong>
        {%- if doc.irn %}
          {%- set _el = frappe.db.get_value("e-Invoice Log", doc.irn, ["invoice_data","signed_qr_code"], as_dict=True) %}
          {%- if _el %}
            {%- set _idata = frappe.parse_json(_el.invoice_data or "{}") %}
            <div><img src="data:image/png;base64,{{ get_qr_code(_el.signed_qr_code, scale=2) }}" style="width:110px;height:110px;"></div>
            <div style="font-size:9px;">IRN: {{ doc.irn }}</div>
            <div style="font-size:9px;">Ack No.: {{ _idata.get("AckNo") }}</div>
            <div style="font-size:9px;">Ack Date: {{ _idata.get("AckDt") }}</div>
          {%- endif %}
        {%- endif %}
      </td>
    </tr>
  </table>

  <table style="width:100%;border-collapse:collapse;" border="1" cellpadding="4">
    <tr>
      <td style="width:55%;vertical-align:top;">
        <strong>{{ _company.company_name }}</strong><br>
        {{ (doc.company_address_display or "") | safe }}
        <br>GSTIN/UIN: {{ doc.company_gstin or "" }}
        <br>UDYAM: UDYAM-PB-01-0113236
        <br>CIN: U46620PB2025PTC064410
        {%- if _company.phone_no %}<br>Contact: {{ _company.phone_no }}{% endif %}
        {%- if _company.email %}<br>E-Mail: {{ _company.email }}{% endif %}
      </td>
      <td style="width:45%;vertical-align:top;padding:0;">
        <table style="width:100%;border-collapse:collapse;" border="1" cellpadding="3">
          <tr><td style="width:50%;">Invoice No.<br><strong>{{ doc.name }}</strong></td>
              <td>Dated<br><strong>{{ frappe.format(doc.posting_date, {"fieldtype":"Date"}) }}</strong></td></tr>
          <tr><td>e-Way Bill No.<br>{{ doc.ewaybill or "" }}</td>
              <td>Mode/Terms of Payment<br>{{ doc.payment_terms_template or "" }}</td></tr>
          <tr><td>Buyer's Order No.<br>{{ doc.po_no or "" }}</td>
              <td>Dated<br>{{ frappe.format(doc.po_date, {"fieldtype":"Date"}) if doc.po_date else "" }}</td></tr>
          <tr><td>Dispatched through<br>{{ doc.transporter_name or "" }}</td>
              <td>Vehicle No.<br>{{ doc.vehicle_no or "" }}</td></tr>
          <tr><td colspan="2">Terms of Delivery<br>{{ doc.tc_name or "" }}</td></tr>
        </table>
      </td>
    </tr>
    <tr>
      <td style="vertical-align:top;">
        <strong>Consignee (Ship to)</strong><br>
        {{ doc.customer_name }}<br>
        {{ (doc.shipping_address or doc.address_display or "") | safe }}
      </td>
      <td style="vertical-align:top;">
        <strong>Buyer (Bill to)</strong><br>
        {{ doc.customer_name }}<br>
        {{ (doc.address_display or "") | safe }}
        {%- if doc.billing_address_gstin %}<br>GSTIN/UIN: {{ doc.billing_address_gstin }}{% endif %}
        {%- if doc.place_of_supply %}<br>Place of Supply: {{ doc.place_of_supply }}{% endif %}
      </td>
    </tr>
  </table>

  <table class="table table-bordered" style="font-size:11px;margin-top:0;margin-bottom:2px;">
    <thead><tr>
      <th style="width:4%;">Sl</th>
      <th>Description of Goods / Services</th>
      <th style="width:10%;">HSN/SAC</th>
      <th class="text-right" style="width:12%;">Quantity</th>
      <th class="text-right" style="width:14%;">Rate</th>
      <th style="width:6%;">per</th>
      <th class="text-right" style="width:16%;">Amount</th>
    </tr></thead>
    <tbody>
    {%- for row in doc.items %}
      <tr>
        <td>{{ loop.index }}</td>
        <td><strong>{{ row.item_name }}</strong>{% if row.description and row.description != row.item_name %}<br><span style="color:#555;">{{ row.description | striptags }}</span>{% endif %}</td>
        <td>{{ row.gst_hsn_code or "" }}</td>
        <td class="text-right">{{ row.qty }} {{ row.uom }}</td>
        <td class="text-right">{{ frappe.format(row.rate, {"fieldtype":"Currency"}, doc=doc) }}</td>
        <td>{{ row.uom }}</td>
        <td class="text-right">{{ frappe.format(row.amount, {"fieldtype":"Currency"}, doc=doc) }}</td>
      </tr>
    {%- endfor %}
    {%- for t in doc.taxes %}
      {%- if t.tax_amount %}
      <tr>
        <td></td>
        <td colspan="5" class="text-right"><em>{{ t.description }}</em></td>
        <td class="text-right">{{ frappe.format(t.tax_amount, {"fieldtype":"Currency"}, doc=doc) }}</td>
      </tr>
      {%- endif %}
    {%- endfor %}
      <tr>
        <td></td>
        <td colspan="3" class="text-right"><strong>Total</strong></td>
        <td class="text-right"><strong>{{ doc.total_qty }}</strong></td>
        <td></td>
        <td class="text-right"><strong>{{ frappe.format(doc.grand_total, {"fieldtype":"Currency"}, doc=doc) }}</strong></td>
      </tr>
    </tbody>
  </table>

  <div style="margin-bottom:6px;">Amount Chargeable (in words): <strong>{{ doc.in_words or "" }}</strong>
    <span style="float:right;">E. &amp; O.E</span></div>

  {%- if doc.gst_breakup_table %}
  <div style="margin-bottom:4px;">{{ doc.gst_breakup_table | safe }}</div>
  {%- endif %}
  {%- if doc.total_taxes_and_charges %}
  <div style="margin-bottom:6px;">Tax Amount (in words): <strong>{{ frappe.utils.money_in_words(doc.total_taxes_and_charges, doc.currency) }}</strong></div>
  {%- endif %}

  <table style="width:100%;border-collapse:collapse;" border="1" cellpadding="4">
    <tr>
      <td style="width:55%;vertical-align:top;">
        {%- if doc.remarks and doc.remarks != "No Remarks" %}Remarks: {{ doc.remarks }}<br>{% endif %}
        {%- if _company.pan %}Company's PAN: <strong>{{ _company.pan }}</strong><br>{% endif %}
        <div style="margin-top:6px;"><u>Declaration</u><br>
          We declare that this invoice shows the actual price of the goods/services described and that all
          particulars are true and correct.</div>
      </td>
      <td style="width:45%;vertical-align:top;">
        <strong>Company's Bank Details</strong><br>
        Bank Name: ICICI Bank Ltd<br>
        A/c Name: KLEMCO India Private Limited<br>
        A/c No.: 777705148127<br>
        Branch &amp; IFSC: Amritsar &amp; ICIC0000066<br>
        SWIFT: ICICINBB
        <div style="margin-top:18px;text-align:right;">for <strong>{{ _company.company_name }}</strong><br><br>
          Authorised Signatory</div>
      </td>
    </tr>
  </table>

  <div style="text-align:center;margin-top:6px;font-size:10px;">SUBJECT TO AMRITSAR JURISDICTION</div>
  <div style="text-align:center;font-size:10px;color:#555;">This is a Computer Generated Invoice</div>
</div>
""".strip()


# ── Klemco Quotation — branded letterhead print format ──────────────────────────────────────────
# Klemco logo + company block, Bill-To, items (with an optional product-image column when
# cs_show_product_image is on), taxes (incl. P&F + GST), amount in words, a TDS note, the Terms &
# Conditions (doc.terms), and a signature footer.
KLEMCO_QUOTATION_HTML = """
{%- set _company = frappe.get_doc("Company", doc.company) %}
{%- set _oa = frappe.db.get_value("User", doc.owner, "cs_office_address") %}
{%- set _oaddr = frappe.get_doc("Address", _oa) if _oa else None %}
<div style="font-size:11px;color:#000;">
  <table style="width:100%;border-collapse:collapse;margin-bottom:6px;">
    <tr>
      <td style="width:60%;vertical-align:middle;">
        {%- if _company.company_logo %}<img src="{{ _company.company_logo }}" style="max-height:64px;max-width:240px;">
        {%- else %}<strong style="font-size:18px;letter-spacing:1px;">{{ _company.company_name }}</strong>{% endif %}
      </td>
      <td style="width:40%;vertical-align:top;text-align:right;">
        <h2 style="margin:0;letter-spacing:2px;">QUOTATION</h2>
        <div><strong>{{ doc.name }}</strong></div>
        <div>Date: {{ frappe.format(doc.transaction_date, {"fieldtype":"Date"}) }}</div>
        {%- if doc.valid_till %}<div>Valid Till: {{ frappe.format(doc.valid_till, {"fieldtype":"Date"}) }}</div>{% endif %}
      </td>
    </tr>
  </table>

  <table style="width:100%;border-collapse:collapse;" border="1" cellpadding="4">
    <tr>
      <td style="width:55%;vertical-align:top;">
        <strong>{{ _company.company_name }}</strong><br>
        {%- if _oaddr %}
          {{ _oaddr.address_line1 or "" }}{% if _oaddr.address_line2 %}, {{ _oaddr.address_line2 }}{% endif %}<br>
          {{ _oaddr.city or "" }}{% if _oaddr.gst_state or _oaddr.state %} , {{ _oaddr.gst_state or _oaddr.state }}{% endif %} {{ _oaddr.pincode or "" }}
          <br>GSTIN/UIN: {{ _oaddr.gstin or doc.company_gstin or "" }}
        {%- else %}
          {{ (doc.company_address_display or "") | safe }}
          <br>GSTIN/UIN: {{ doc.company_gstin or "" }}
        {%- endif %}
        <br>UDYAM: UDYAM-PB-01-0113236 &nbsp; CIN: U46620PB2025PTC064410
      </td>
      <td style="width:45%;vertical-align:top;">
        <strong>Quotation To</strong><br>
        {{ doc.customer_name or doc.party_name }}<br>
        {{ (doc.address_display or "") | safe }}
      </td>
    </tr>
  </table>

  {#- Auto-show the Image column when it's forced on, or when any line has an image (line or item). -#}
  {%- set _ns = namespace(show=doc.cs_show_product_image) %}
  {%- for row in doc.items %}{% if not _ns.show and (row.cs_product_image or frappe.db.get_value("Item", row.item_code, "image")) %}{% set _ns.show = true %}{% endif %}{% endfor %}
  <table class="table table-bordered" style="font-size:11px;margin-top:0;margin-bottom:2px;">
    <thead><tr>
      <th style="width:4%;">Sl</th>
      {%- if _ns.show %}<th style="width:12%;">Image</th>{% endif %}
      <th>Description</th>
      <th style="width:10%;">HSN/SAC</th>
      <th class="text-right" style="width:12%;">Qty</th>
      <th class="text-right" style="width:14%;">Rate</th>
      <th class="text-right" style="width:16%;">Amount</th>
    </tr></thead>
    <tbody>
    {%- for row in doc.items %}
      <tr>
        <td>{{ loop.index }}</td>
        {%- if _ns.show %}
          {%- set img = row.cs_product_image or frappe.db.get_value("Item", row.item_code, "image") %}
          <td>{% if img %}<img src="{{ img }}" style="max-width:70px;max-height:70px;">{% endif %}</td>
        {%- endif %}
        <td><strong>{{ row.item_name }}</strong>{% if row.description and row.description != row.item_name %}<br><span style="color:#555;">{{ row.description | striptags }}</span>{% endif %}</td>
        <td>{{ row.gst_hsn_code or "" }}</td>
        <td class="text-right">{{ row.qty }} {{ row.uom }}</td>
        <td class="text-right">{{ frappe.format(row.rate, {"fieldtype":"Currency"}, doc=doc) }}</td>
        <td class="text-right">{{ frappe.format(row.amount, {"fieldtype":"Currency"}, doc=doc) }}</td>
      </tr>
    {%- endfor %}
    </tbody>
  </table>

  <table style="width:100%;font-size:11px;margin-bottom:4px;">
    <tr><td style="text-align:right;">Net Total</td>
        <td style="text-align:right;width:160px;">{{ frappe.format(doc.net_total, {"fieldtype":"Currency"}, doc=doc) }}</td></tr>
    {%- for t in doc.taxes %}{% if t.tax_amount %}
    <tr><td style="text-align:right;">{{ t.description }}</td>
        <td style="text-align:right;">{{ frappe.format(t.tax_amount, {"fieldtype":"Currency"}, doc=doc) }}</td></tr>
    {% endif %}{% endfor %}
    <tr><td style="text-align:right;"><strong>Grand Total</strong></td>
        <td style="text-align:right;"><strong>{{ frappe.format(doc.grand_total, {"fieldtype":"Currency"}, doc=doc) }}</strong></td></tr>
  </table>
  <div style="margin-bottom:6px;">Amount in words: <strong>{{ doc.in_words or "" }}</strong></div>

  {%- if doc.cs_add_tds %}
  <div class="note" style="border:1px solid #ddd;padding:6px;margin-bottom:6px;font-size:10px;">
    Technical Data Sheets for the quoted items are attached / available on request (TDS pack).
  </div>
  {%- endif %}

  {%- if doc.terms %}
  <div style="margin-top:8px;"><u>Terms &amp; Conditions</u><div style="font-size:10px;">{{ doc.terms | safe }}</div></div>
  {%- endif %}

  <table style="width:100%;margin-top:24px;"><tr>
    <td style="font-size:10px;color:#555;">This is a computer-generated quotation.</td>
    <td style="text-align:right;">for <strong>{{ _company.company_name }}</strong><br><br>Authorised Signatory</td>
  </tr></table>
</div>
""".strip()


def _ensure_quotation_print_format():
    """Create (or refresh on change) the branded 'Klemco Quotation' letterhead print format."""
    name = "Klemco Quotation"
    if frappe.db.exists("Print Format", name):
        pf = frappe.get_doc("Print Format", name)
        if (pf.html or "") != KLEMCO_QUOTATION_HTML:
            pf.html = KLEMCO_QUOTATION_HTML
            pf.save(ignore_permissions=True)
        return
    frappe.get_doc({
        "doctype": "Print Format",
        "name": name,
        "doc_type": "Quotation",
        "module": "Customer Service",
        "standard": "No",
        "custom_format": 1,
        "print_format_type": "Jinja",
        "html": KLEMCO_QUOTATION_HTML,
    }).insert(ignore_permissions=True)


def _ensure_klemco_tax_invoice():
    """Create (or update on change) the Tally-style 'Klemco Tax Invoice' Sales Invoice print format.
    Unlike the proforma seeder, this refreshes the html when it drifts so template tweaks redeploy
    cleanly on the next apply_customizations()."""
    name = "Klemco Tax Invoice"
    if frappe.db.exists("Print Format", name):
        pf = frappe.get_doc("Print Format", name)
        if (pf.html or "") != KLEMCO_TAX_INVOICE_HTML:
            pf.html = KLEMCO_TAX_INVOICE_HTML
            pf.save(ignore_permissions=True)
        return
    frappe.get_doc({
        "doctype": "Print Format",
        "name": name,
        "doc_type": "Sales Invoice",
        "module": "Customer Service",
        "standard": "No",
        "custom_format": 1,
        "print_format_type": "Jinja",
        "html": KLEMCO_TAX_INVOICE_HTML,
    }).insert(ignore_permissions=True)


def _ensure_company_print_details():
    """Set Klemco India's PAN so the Tax Invoice footer's 'Company's PAN' line renders. The seller's
    UDYAM / CIN and the bank block are static Klemco facts embedded in KLEMCO_TAX_INVOICE_HTML (this
    IC build has no Company '…_for_printing' tables — no Table fields on Company at all). Idempotent."""
    company = "Klemco India"
    if not frappe.db.exists("Company", company):
        return
    if not frappe.db.get_value("Company", company, "pan"):
        frappe.db.set_value("Company", company, "pan", "AALCK8220C")
