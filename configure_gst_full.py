import frappe

frappe.init(site='mysite.localhost', sites_path='/home/frappe/frappe-bench/sites')
frappe.connect()
frappe.set_user('Administrator')

company = 'Klemco India'

gst = frappe.get_single('GST Settings')

# ── General tab ──────────────────────────────────────────────────
gst.hsn_wise_tax_breakup            = 1
gst.validate_hsn_code               = 1
gst.min_hsn_digits                  = 6
gst.require_supplier_invoice_no     = 1
gst.enable_reverse_charge_in_sales  = 0
gst.enable_overseas_transactions    = 0
gst.enable_e_commerce               = 0
gst.round_off_gst_values            = 0
gst.reverse_charge_for_unregistered = 0

# API
gst.enable_api                      = 1
gst.sandbox_mode                    = 0
gst.retry_e_invoice_e_waybill       = 1
gst.use_fallback_api                = 1
gst.autofill_party_info             = 1
gst.validate_gstin_status           = 0
gst.archive_party_days              = 7

# e-Waybill
gst.enable_e_waybill                       = 1
gst.e_waybill_from_dn                      = 0
gst.e_waybill_from_pi                      = 0
gst.e_waybill_from_pr                      = 0
gst.e_waybill_for_sc                       = 0
gst.fetch_e_waybill_data                   = 1
gst.attach_e_waybill_print                 = 1
gst.auto_generate_e_waybill               = 1
gst.auto_cancel_e_waybill                  = 0
gst.e_waybill_cancellation_reason         = 'Data Entry Mistake'
gst.e_waybill_threshold                    = 50000

# e-Invoice
gst.enable_e_invoice                       = 0

# GSTR-1
gst.enable_gstr_1_api_features             = 1
gst.restrict_changes_after_filing          = 0
gst.compare_before_filing                  = 1

# ── Purchase Reconciliation tab ───────────────────────────────────
gst.enable_auto_reconciliation             = 1
gst.inward_supply_period                   = 2
# GST categories: B2B + CDNR
gst.gst_category_b2b   = 1
gst.gst_category_cdnr  = 1
gst.gst_category_b2ba  = 0
gst.gst_category_cdnra = 0
gst.gst_category_isd   = 0
gst.gst_category_isda  = 0
gst.gst_category_impg  = 0
gst.gst_category_impgsez = 0
# Auto reconciliation days: Tuesday + Friday
gst.auto_recon_monday    = 0
gst.auto_recon_tuesday   = 1
gst.auto_recon_wednesday = 0
gst.auto_recon_thursday  = 0
gst.auto_recon_friday    = 1
gst.auto_recon_saturday  = 0
gst.auto_recon_sunday    = 0

# ── Accounts tab — 4 rows matching cloud trial ───────────────────
def get_acc(pattern):
    result = frappe.db.sql(
        "SELECT name FROM `tabAccount` WHERE company=%s AND is_group=0 AND account_type='Tax' AND account_name LIKE %s ORDER BY name LIMIT 1",
        (company, f'%{pattern}%'), as_dict=True
    )
    return result[0].name if result else ''

gst.gst_accounts = []

account_rows = [
    {'account_type': 'Input',
     'cgst_account': get_acc('Input Tax CGST'),
     'sgst_account': get_acc('Input Tax SGST'),
     'igst_account': get_acc('Input Tax IGST')},
    {'account_type': 'Output',
     'cgst_account': get_acc('Output Tax CGST'),
     'sgst_account': get_acc('Output Tax SGST'),
     'igst_account': get_acc('Output Tax IGST')},
    {'account_type': 'Purchase Reverse Charge',
     'cgst_account': get_acc('Input Tax CGST RCM'),
     'sgst_account': get_acc('Input Tax SGST RCM'),
     'igst_account': get_acc('Input Tax IGST RCM')},
    {'account_type': 'Sales Reverse Charge',
     'cgst_account': get_acc('Output Tax CGST RCM'),
     'sgst_account': get_acc('Output Tax SGST RCM'),
     'igst_account': get_acc('Output Tax IGST RCM')},
]

for row_data in account_rows:
    row = gst.append('gst_accounts', {})
    row.company       = company
    row.account_type  = row_data['account_type']
    row.cgst_account  = row_data['cgst_account']
    row.sgst_account  = row_data['sgst_account']
    row.igst_account  = row_data['igst_account']
    print(f"  {row_data['account_type']}: CGST={row_data['cgst_account']}, SGST={row_data['sgst_account']}, IGST={row_data['igst_account']}")

gst.flags.ignore_mandatory = True
gst.flags.ignore_links     = True
gst.save(ignore_permissions=True)
frappe.db.commit()

print("\nGST Settings fully configured.")
print("Tabs: General ✓ | Accounts ✓ (4 rows) | Purchase Reconciliation ✓ | Credentials (empty — needs GSP login)")
frappe.destroy()
