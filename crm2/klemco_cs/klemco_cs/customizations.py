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

# CS operational roles allowed to create/link Projects inline from the Sales Order
# (Accounting Dimensions → Project). Frappe only offers the "+ Create a new Project"
# quick-entry in the link picker to users who hold create permission on Project.
PROJECT_PERM_ROLES = ["CS Executive", "CS Supervisor", "CS Manager"]

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
    # Show the Unit of Measure (UOM) as a column in the Sales Order items grid.
    {
        "doctype_or_field": "Field",
        "doctype": "Sales Order Item",
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


def _ensure_billing_controls():
    """A Sales Invoice must originate from a Sales Order — no billing for un-ordered goods.
    ERPNext enforces this via Selling Settings.so_required (so_dn_required); POS is exempt."""
    if frappe.db.get_single_value("Selling Settings", "so_required") != "Yes":
        frappe.db.set_single_value("Selling Settings", "so_required", "Yes")


def _ensure_roles():
    for role in REQUIRED_ROLES:
        if not frappe.db.exists("Role", role):
            frappe.get_doc({"doctype": "Role", "role_name": role}).insert(ignore_permissions=True)


def _ensure_project_permissions():
    """Let CS users create/link Projects inline from the Sales Order (Accounting Dimensions).
    Adds a Custom DocPerm on Project for each CS operational role — idempotent, re-applied on
    every migrate. Without create permission Frappe hides the "+ Create a new Project" quick-entry."""
    for role in PROJECT_PERM_ROLES:
        if not frappe.db.exists("Role", role):
            continue
        add_permission("Project", role, 0)  # creates a Custom DocPerm (read=1) if absent
        for ptype in ("read", "write", "create"):
            update_permission_property("Project", role, 0, ptype, 1, validate=False)


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
