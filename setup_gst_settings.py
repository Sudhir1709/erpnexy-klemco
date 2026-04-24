import frappe

frappe.init(site='mysite.localhost', sites_path='/home/frappe/frappe-bench/sites')
frappe.connect()
frappe.set_user('Administrator')

company = 'Klemco India'
gstin = '03AALCK8220C1ZX'

# Step 1: Update company GST category
comp = frappe.get_doc('Company', company)
comp.gst_category = 'Registered Regular'
comp.flags.ignore_mandatory = True
comp.flags.ignore_links = True
comp.save(ignore_permissions=True)
print(f"Company GST category set to: Registered Regular")

# Step 2: Create GSTIN record
if not frappe.db.exists('GSTIN', gstin):
    gstin_doc = frappe.new_doc('GSTIN')
    gstin_doc.gstin = gstin
    gstin_doc.status = 'Active'
    gstin_doc.flags.ignore_mandatory = True
    gstin_doc.flags.ignore_links = True
    try:
        gstin_doc.insert(ignore_permissions=True)
        print(f"Created GSTIN: {gstin}")
    except Exception as e:
        print(f"GSTIN note: {e}")
else:
    print(f"GSTIN already exists: {gstin}")

# Step 3: Configure GST Settings — one row per company with all account types
gst = frappe.get_single('GST Settings')

# Remove any existing rows for this company
gst.gst_accounts = [r for r in gst.gst_accounts if r.company != company]

# Find accounts
def get_account(keywords, exclude=None):
    accounts = frappe.db.sql("""
        SELECT name FROM `tabAccount`
        WHERE company = %s AND is_group = 0
        AND account_type = 'Tax'
        AND ({})
        ORDER BY name LIMIT 1
    """.format(
        ' OR '.join(f"account_name LIKE %s" for _ in keywords)
    ), [company] + [f'%{k}%' for k in keywords], as_dict=True)
    return accounts[0].name if accounts else None

cgst_out = get_account(['Output Tax CGST'])
sgst_out = get_account(['Output Tax SGST'])
igst_out = get_account(['Output Tax IGST'])
cgst_in  = get_account(['Input Tax CGST'])
sgst_in  = get_account(['Input Tax SGST'])
igst_in  = get_account(['Input Tax IGST'])
cgst_rcm = get_account(['CGST RCM'])
sgst_rcm = get_account(['SGST RCM'])
igst_rcm = get_account(['IGST RCM'])

print(f"\nGST Accounts found:")
print(f"  Output CGST: {cgst_out}")
print(f"  Output SGST: {sgst_out}")
print(f"  Output IGST: {igst_out}")
print(f"  Input CGST:  {cgst_in}")
print(f"  Input SGST:  {sgst_in}")
print(f"  Input IGST:  {igst_in}")

row = gst.append('gst_accounts', {
    'company': company,
    'cgst_account': cgst_out,
    'sgst_account': sgst_out,
    'igst_account': igst_out,
    'input_cgst_account': cgst_in,
    'input_sgst_account': sgst_in,
    'input_igst_account': igst_in,
    'reverse_charge_cgst_account': cgst_rcm,
    'reverse_charge_sgst_account': sgst_rcm,
    'reverse_charge_igst_account': igst_rcm,
})

gst.flags.ignore_mandatory = True
gst.flags.ignore_links = True
try:
    gst.save(ignore_permissions=True)
    print("\nGST Settings saved successfully.")
except Exception as e:
    print(f"\nGST Settings error: {e}")
    # Try minimal save with just output accounts
    gst2 = frappe.get_single('GST Settings')
    gst2.gst_accounts = [r for r in gst2.gst_accounts if r.company != company]
    gst2.append('gst_accounts', {
        'company': company,
        'cgst_account': cgst_out,
        'sgst_account': sgst_out,
        'igst_account': igst_out,
    })
    gst2.flags.ignore_mandatory = True
    gst2.flags.ignore_links = True
    gst2.save(ignore_permissions=True)
    print("GST Settings saved (minimal).")

# Step 4: Link GSTIN to company address
addrs = frappe.db.sql("""
    SELECT dl.parent FROM `tabDynamic Link` dl
    JOIN `tabAddress` a ON a.name = dl.parent
    WHERE dl.link_doctype = 'Company' AND dl.link_name = %s
    LIMIT 5
""", company, as_dict=True)
print(f"\nCompany addresses: {[a.parent for a in addrs]}")

if addrs:
    addr = frappe.get_doc('Address', addrs[0].parent)
    addr.gstin = gstin
    addr.gst_state = 'Punjab'
    addr.gst_state_number = '03'
    addr.flags.ignore_mandatory = True
    addr.save(ignore_permissions=True)
    print(f"GSTIN set on address: {addr.name}")
else:
    # Create a company address
    addr = frappe.new_doc('Address')
    addr.address_title = f'{company} - Main'
    addr.address_type = 'Billing'
    addr.address_line1 = 'Amritsar'
    addr.city = 'Amritsar'
    addr.state = 'Punjab'
    addr.country = 'India'
    addr.pincode = '143001'
    addr.gstin = gstin
    addr.gst_state = 'Punjab'
    addr.gst_state_number = '03'
    addr.is_primary_address = 1
    addr.append('links', {'link_doctype': 'Company', 'link_name': company})
    addr.flags.ignore_mandatory = True
    addr.insert(ignore_permissions=True)
    print(f"Created company address with GSTIN: {addr.name}")

frappe.db.commit()
print("\nDone. GSTIN configured for Klemco India.")
frappe.destroy()
