import frappe, random
from frappe.utils import today, add_days

frappe.init(site='mysite.localhost', sites_path='/home/frappe/frappe-bench/sites')
frappe.connect()
frappe.set_user('Administrator')

COMPANY = 'Klemco India'
ABBR = 'KI'
PRICE_LIST = 'Standard Selling'

# ── TERRITORIES ───────────────────────────────────────────────────────────────
territories = [
    ('India', 'All Territories'), ('Punjab', 'India'), ('Amritsar', 'Punjab'),
    ('Maharashtra', 'India'), ('Thane', 'Maharashtra'), ('Mumbai', 'Maharashtra'),
    ('Delhi NCR', 'India'), ('Karnataka', 'India'), ('Bangalore', 'Karnataka'),
    ('Telangana', 'India'), ('Hyderabad', 'Telangana'),
    ('Tamil Nadu', 'India'), ('Chennai', 'Tamil Nadu'),
    ('Gujarat', 'India'), ('Ahmedabad', 'Gujarat'),
    ('UAE', 'All Territories'),
]
for name, parent in territories:
    if not frappe.db.exists('Territory', name):
        frappe.get_doc({'doctype': 'Territory', 'territory_name': name, 'parent_territory': parent}).insert(ignore_permissions=True)
print('Territories done')

# ── CUSTOMER GROUPS ───────────────────────────────────────────────────────────
cgroups = [
    ('MEP Contractors', 'All Customer Groups'),
    ('HVAC & Refrigeration', 'All Customer Groups'),
    ('Data Centers', 'All Customer Groups'),
    ('Metro & Rail', 'All Customer Groups'),
    ('Hospitals & Healthcare', 'All Customer Groups'),
    ('Hotels & Hospitality', 'All Customer Groups'),
    ('Industrial', 'All Customer Groups'),
    ('Commercial Real Estate', 'All Customer Groups'),
    ('Residential Builders', 'All Customer Groups'),
    ('Government & PSU', 'All Customer Groups'),
    ('Distributors', 'All Customer Groups'),
    ('Exporters', 'All Customer Groups'),
]
for name, parent in cgroups:
    if not frappe.db.exists('Customer Group', name):
        frappe.get_doc({'doctype': 'Customer Group', 'customer_group_name': name, 'parent_customer_group': parent}).insert(ignore_permissions=True)
print('Customer Groups done')

# ── SUPPLIER GROUPS ───────────────────────────────────────────────────────────
sgroups = [
    ('Steel & Metal Suppliers', 'All Supplier Groups'),
    ('Chemical Suppliers', 'All Supplier Groups'),
    ('Packaging Suppliers', 'All Supplier Groups'),
    ('OEM & Trading', 'All Supplier Groups'),
    ('Logistics Providers', 'All Supplier Groups'),
]
for name, parent in sgroups:
    if not frappe.db.exists('Supplier Group', name):
        frappe.get_doc({'doctype': 'Supplier Group', 'supplier_group_name': name, 'parent_supplier_group': parent}).insert(ignore_permissions=True)
print('Supplier Groups done')

# ── ITEM GROUPS ───────────────────────────────────────────────────────────────
igroups = [
    ('Fixing Technology', 'All Item Groups'),
    ('Pipe Hangers and Clamps', 'Fixing Technology'),
    ('Strut Channels and Accessories', 'Fixing Technology'),
    ('Anchors', 'Fixing Technology'),
    ('Chemical Anchors', 'Anchors'),
    ('Mechanical Anchors', 'Anchors'),
    ('Fire Stop Solutions', 'Fixing Technology'),
    ('Wire Rope Suspension Systems', 'Fixing Technology'),
    ('Vibration Controls', 'Fixing Technology'),
    ('Seismic Supports', 'Fixing Technology'),
    ('Saddle Shoes', 'Fixing Technology'),
    ('Engineering Services', 'Services'),
    ('Installation Services', 'Services'),
]
for name, parent in igroups:
    if not frappe.db.exists('Item Group', name):
        frappe.get_doc({'doctype': 'Item Group', 'item_group_name': name, 'parent_item_group': parent}).insert(ignore_permissions=True)
print('Item Groups done')

# ── ITEMS + PRICES ────────────────────────────────────────────────────────────
items = [
    ('KL-SC-001', 'Strut Channel 41x41mm Standard', 'Strut Channels and Accessories', 'Nos', 850, '84839000', 1),
    ('KL-SC-002', 'Strut Channel 41x21mm Shallow', 'Strut Channels and Accessories', 'Nos', 620, '84839000', 1),
    ('KL-SC-003', 'Strut Channel 41x41mm Pre-Galvanized', 'Strut Channels and Accessories', 'Nos', 950, '84839000', 1),
    ('KL-SC-004', '2 Hole Short 90 Assembly', 'Strut Channels and Accessories', 'Nos', 120, '73269099', 1),
    ('KL-SC-005', '3 Hole Z Fitting Assembly', 'Strut Channels and Accessories', 'Nos', 145, '73269099', 1),
    ('KL-SC-006', 'Girder Cleat HT', 'Strut Channels and Accessories', 'Nos', 280, '73269099', 1),
    ('KL-SC-007', 'Corner Connector 4D Type S Assembly', 'Strut Channels and Accessories', 'Nos', 320, '73269099', 1),
    ('KL-SC-008', 'Girder Cleat LT Assembly', 'Strut Channels and Accessories', 'Nos', 190, '73269099', 1),
    ('KL-SC-009', '5 Hole Connector Plate Assembly', 'Strut Channels and Accessories', 'Nos', 165, '73269099', 1),
    ('KL-SC-010', 'Vario Saddle', 'Strut Channels and Accessories', 'Nos', 210, '73269099', 1),
    ('KL-SC-011', 'Corner Connector 3D Type FV Assembly', 'Strut Channels and Accessories', 'Nos', 295, '73269099', 1),
    ('KL-SC-012', 'Angle Connector 90 2+2 Type S Assembly', 'Strut Channels and Accessories', 'Nos', 275, '73269099', 1),
    ('KL-SC-013', '4 Hole Long 90 Reinforced Assembly', 'Strut Channels and Accessories', 'Nos', 340, '73269099', 1),
    ('KL-SC-014', 'Length Wise Saddle D Profile', 'Strut Channels and Accessories', 'Nos', 225, '73269099', 1),
    ('KL-PH-001', 'Clevis Hanger 1/2 inch', 'Pipe Hangers and Clamps', 'Nos', 95, '73269099', 1),
    ('KL-PH-002', 'Clevis Hanger 1 inch', 'Pipe Hangers and Clamps', 'Nos', 110, '73269099', 1),
    ('KL-PH-003', 'Clevis Hanger 2 inch', 'Pipe Hangers and Clamps', 'Nos', 145, '73269099', 1),
    ('KL-PH-004', 'Split Ring Hanger 3/4 inch', 'Pipe Hangers and Clamps', 'Nos', 85, '73269099', 1),
    ('KL-PH-005', 'Split Ring Hanger 2 inch', 'Pipe Hangers and Clamps', 'Nos', 125, '73269099', 1),
    ('KL-PH-006', 'Pipe Strap Galvanized 1/2 inch', 'Pipe Hangers and Clamps', 'Nos', 45, '73269099', 1),
    ('KL-PH-007', 'Pipe Clamp Heavy Duty 4 inch', 'Pipe Hangers and Clamps', 'Nos', 310, '73269099', 1),
    ('KL-PH-008', 'Riser Clamp 2 inch', 'Pipe Hangers and Clamps', 'Nos', 220, '73269099', 1),
    ('KL-PH-009', 'U-Bolt Pipe Clamp 1 inch', 'Pipe Hangers and Clamps', 'Nos', 75, '73269099', 1),
    ('KL-PH-010', 'Beam Clamp Flange Type', 'Pipe Hangers and Clamps', 'Nos', 185, '73269099', 1),
    ('KL-CA-001', 'Chemical Anchor Capsule M12 Standard', 'Chemical Anchors', 'Nos', 380, '38244000', 1),
    ('KL-CA-002', 'Chemical Anchor Capsule M16 High Strength', 'Chemical Anchors', 'Nos', 520, '38244000', 1),
    ('KL-CA-003', 'Chemical Anchor Injectable Resin 300ml', 'Chemical Anchors', 'Nos', 1250, '38244000', 1),
    ('KL-CA-004', 'Chemical Anchor Injectable Resin 500ml', 'Chemical Anchors', 'Nos', 1850, '38244000', 1),
    ('KL-CA-005', 'Anchor Mixing Nozzle Pack of 10', 'Chemical Anchors', 'Box', 450, '39259090', 1),
    ('KL-MA-001', 'Expansion Anchor M10 Wedge Type', 'Mechanical Anchors', 'Nos', 65, '73181500', 1),
    ('KL-MA-002', 'Expansion Anchor M12 Wedge Type', 'Mechanical Anchors', 'Nos', 85, '73181500', 1),
    ('KL-MA-003', 'Sleeve Anchor M10x100', 'Mechanical Anchors', 'Nos', 72, '73181500', 1),
    ('KL-MA-004', 'Sleeve Anchor M12x120', 'Mechanical Anchors', 'Nos', 98, '73181500', 1),
    ('KL-MA-005', 'Undercut Anchor M16 High Load', 'Mechanical Anchors', 'Nos', 245, '73181500', 1),
    ('KL-MA-006', 'Screw Anchor M6x50mm', 'Mechanical Anchors', 'Nos', 28, '73181500', 1),
    ('KL-FS-001', 'Fire Stop Collar DN50 2hr Rating', 'Fire Stop Solutions', 'Nos', 1850, '38140000', 1),
    ('KL-FS-002', 'Fire Stop Collar DN110 2hr Rating', 'Fire Stop Solutions', 'Nos', 2450, '38140000', 1),
    ('KL-FS-003', 'Fire Stop Sealant 600ml Grey', 'Fire Stop Solutions', 'Nos', 980, '38140000', 1),
    ('KL-FS-004', 'Fire Stop Pillow 100x100x50mm', 'Fire Stop Solutions', 'Nos', 650, '38140000', 1),
    ('KL-FS-005', 'Fire Stop Mortar 5kg Pail', 'Fire Stop Solutions', 'Nos', 1450, '38140000', 1),
    ('KL-WR-001', 'Wire Rope Hanger Kit Light Duty 1.5m', 'Wire Rope Suspension Systems', 'Set', 385, '73121090', 1),
    ('KL-WR-002', 'Wire Rope Hanger Kit Medium Duty 2m', 'Wire Rope Suspension Systems', 'Set', 520, '73121090', 1),
    ('KL-WR-003', 'Wire Rope Gripper Clip', 'Wire Rope Suspension Systems', 'Nos', 95, '73121090', 1),
    ('KL-WR-004', 'Ceiling Anchor for Wire Rope', 'Wire Rope Suspension Systems', 'Nos', 75, '73269099', 1),
    ('KL-VC-001', 'Anti-Vibration Mount Type A 10kg', 'Vibration Controls', 'Nos', 450, '40169390', 1),
    ('KL-VC-002', 'Anti-Vibration Mount Type B 25kg', 'Vibration Controls', 'Nos', 680, '40169390', 1),
    ('KL-VC-003', 'Spring Hanger Isolator 50kg', 'Vibration Controls', 'Nos', 1250, '84839000', 1),
    ('KL-SS-001', 'Seismic Brace Kit 4-Way', 'Seismic Supports', 'Set', 4500, '73089090', 1),
    ('KL-SS-002', 'Seismic Clevis Brace 12mm Rod', 'Seismic Supports', 'Nos', 850, '73089090', 1),
    ('KL-SH-001', 'Insulated Saddle Shoe 2 inch', 'Saddle Shoes', 'Nos', 320, '73269099', 1),
    ('KL-SH-002', 'Insulated Saddle Shoe 4 inch', 'Saddle Shoes', 'Nos', 490, '73269099', 1),
    ('KL-SH-003', 'MSS Pipe Saddle 6 inch', 'Saddle Shoes', 'Nos', 780, '73269099', 1),
    ('KL-SV-001', 'Engineering Design and Drawing', 'Engineering Services', 'Hour', 2500, '998312', 0),
    ('KL-SV-002', 'Site Survey and Consultation', 'Engineering Services', 'Hour', 2000, '998312', 0),
    ('KL-SV-003', 'BIM Coordination Service', 'Engineering Services', 'Hour', 3000, '998312', 0),
    ('KL-SV-004', 'Installation and Supervision', 'Installation Services', 'Hour', 1500, '998311', 0),
    ('KL-SV-005', 'Pre-Fabrication Service', 'Installation Services', 'Hour', 1800, '998311', 0),
]
for code, name, group, uom, rate, hsn, is_stock in items:
    if not frappe.db.exists('Item', code):
        frappe.get_doc({
            'doctype': 'Item', 'item_code': code, 'item_name': name,
            'item_group': group, 'stock_uom': uom, 'is_stock_item': is_stock,
            'gst_hsn_code': hsn, 'description': name,
        }).insert(ignore_permissions=True)
    if not frappe.db.exists('Item Price', {'item_code': code, 'price_list': PRICE_LIST}):
        frappe.get_doc({
            'doctype': 'Item Price', 'item_code': code,
            'price_list': PRICE_LIST, 'price_list_rate': rate, 'currency': 'INR',
        }).insert(ignore_permissions=True)
frappe.db.commit()
print('Items + Prices done')

# ── CUSTOMERS ─────────────────────────────────────────────────────────────────
customers = [
    ('Larsen and Toubro Ltd.', 'MEP Contractors', 'Mumbai'),
    ('Tata Projects Ltd.', 'MEP Contractors', 'Hyderabad'),
    ('Shapoorji Pallonji and Co.', 'Commercial Real Estate', 'Mumbai'),
    ('Thermax Ltd.', 'Industrial', 'Mumbai'),
    ('Blue Star Ltd.', 'HVAC & Refrigeration', 'Mumbai'),
    ('Voltas Ltd.', 'HVAC & Refrigeration', 'Mumbai'),
    ('Carrier Midea India', 'HVAC & Refrigeration', 'Delhi NCR'),
    ('DMRC Delhi Metro', 'Metro & Rail', 'Delhi NCR'),
    ('Mumbai Metro One', 'Metro & Rail', 'Mumbai'),
    ('Apollo Hospitals', 'Hospitals & Healthcare', 'Chennai'),
    ('Fortis Healthcare', 'Hospitals & Healthcare', 'Delhi NCR'),
    ('IHG Hotels India', 'Hotels & Hospitality', 'Bangalore'),
    ('Hyatt Hotels India', 'Hotels & Hospitality', 'Mumbai'),
    ('CtrlS Datacenters', 'Data Centers', 'Hyderabad'),
    ('Nxtdigital Data Center', 'Data Centers', 'Mumbai'),
    ('Godrej Properties', 'Commercial Real Estate', 'Mumbai'),
    ('DLF Ltd.', 'Commercial Real Estate', 'Delhi NCR'),
    ('Brigade Group', 'Residential Builders', 'Bangalore'),
    ('Prestige Group', 'Residential Builders', 'Bangalore'),
    ('NTPC Ltd.', 'Government & PSU', 'Delhi NCR'),
    ('ONGC Ltd.', 'Government & PSU', 'Mumbai'),
    ('Rite Fix Solutions', 'Distributors', 'Amritsar'),
    ('Punjab Building Supplies', 'Distributors', 'Amritsar'),
    ('Gulf MEP Trading LLC', 'Exporters', 'UAE'),
]
for cname, cgroup, city in customers:
    if not frappe.db.exists('Customer', cname):
        territory = city if frappe.db.exists('Territory', city) else 'India'
        frappe.get_doc({
            'doctype': 'Customer', 'customer_name': cname,
            'customer_group': cgroup, 'territory': territory, 'customer_type': 'Company',
        }).insert(ignore_permissions=True)
frappe.db.commit()
print('Customers done')

# ── SUPPLIERS ─────────────────────────────────────────────────────────────────
suppliers = [
    ('Tata Steel Ltd.', 'Steel & Metal Suppliers'),
    ('JSW Steel Ltd.', 'Steel & Metal Suppliers'),
    ('Jindal Steel and Power', 'Steel & Metal Suppliers'),
    ('Hilti India Pvt. Ltd.', 'OEM & Trading'),
    ('Fischer Fixings India', 'OEM & Trading'),
    ('Henkel Adhesives India', 'Chemical Suppliers'),
    ('BASF India Ltd.', 'Chemical Suppliers'),
    ('Supreme Packaging', 'Packaging Suppliers'),
    ('Blue Dart Express', 'Logistics Providers'),
    ('VRL Logistics', 'Logistics Providers'),
]
for sname, sgroup in suppliers:
    if not frappe.db.exists('Supplier', sname):
        frappe.get_doc({
            'doctype': 'Supplier', 'supplier_name': sname,
            'supplier_group': sgroup, 'country': 'India',
        }).insert(ignore_permissions=True)
frappe.db.commit()
print('Suppliers done')

# ── WAREHOUSES ────────────────────────────────────────────────────────────────
wh_root = f'All Warehouses - {ABBR}'
for wname in ['Amritsar Main Store', 'Thane Branch Store', 'Raw Material Store', 'Inspection Hold']:
    full = f'{wname} - {ABBR}'
    if not frappe.db.exists('Warehouse', full):
        frappe.get_doc({
            'doctype': 'Warehouse', 'warehouse_name': wname,
            'parent_warehouse': wh_root, 'company': COMPANY,
        }).insert(ignore_permissions=True)
frappe.db.commit()
print('Warehouses done')

# ── HELPER ────────────────────────────────────────────────────────────────────
def rate(code):
    return frappe.db.get_value('Item Price', {'item_code': code, 'price_list': PRICE_LIST}, 'price_list_rate') or 100

# ── QUOTATIONS ────────────────────────────────────────────────────────────────
quotes = [
    ('Larsen and Toubro Ltd.', [('KL-SC-001', 100), ('KL-PH-003', 50), ('KL-MA-003', 200)]),
    ('Blue Star Ltd.', [('KL-VC-001', 20), ('KL-WR-001', 30), ('KL-SC-004', 40)]),
    ('Apollo Hospitals', [('KL-FS-001', 15), ('KL-FS-003', 10), ('KL-CA-003', 5)]),
    ('DMRC Delhi Metro', [('KL-SS-001', 25), ('KL-SS-002', 40), ('KL-SC-001', 60)]),
    ('Voltas Ltd.', [('KL-PH-001', 80), ('KL-SC-003', 60), ('KL-VC-002', 10)]),
    ('Godrej Properties', [('KL-CA-001', 40), ('KL-FS-004', 20), ('KL-WR-001', 15)]),
    ('CtrlS Datacenters', [('KL-WR-002', 25), ('KL-SC-011', 50), ('KL-SV-003', 10)]),
]
for cust, lines in quotes:
    try:
        frappe.get_doc({
            'doctype': 'Quotation', 'quotation_to': 'Customer', 'party_name': cust,
            'transaction_date': add_days(today(), -random.randint(5, 30)),
            'valid_till': add_days(today(), 30),
            'selling_price_list': PRICE_LIST, 'currency': 'INR', 'company': COMPANY,
            'items': [{'item_code': ic, 'qty': qty, 'rate': rate(ic)} for ic, qty in lines],
        }).insert(ignore_permissions=True)
        print(f'  Quotation: {cust}')
    except Exception as e:
        print(f'  Quotation SKIP {cust}: {e}')
frappe.db.commit()

# ── SALES ORDERS ──────────────────────────────────────────────────────────────
orders = [
    ('Tata Projects Ltd.', [('KL-SC-001', 200), ('KL-SC-002', 150), ('KL-MA-001', 500)]),
    ('Voltas Ltd.', [('KL-PH-001', 100), ('KL-PH-002', 80), ('KL-VC-002', 15)]),
    ('Godrej Properties', [('KL-CA-001', 50), ('KL-CA-002', 30), ('KL-FS-001', 20)]),
    ('CtrlS Datacenters', [('KL-WR-001', 40), ('KL-WR-002', 20), ('KL-SC-011', 80)]),
    ('Apollo Hospitals', [('KL-FS-002', 10), ('KL-FS-005', 8), ('KL-SV-004', 16)]),
    ('NTPC Ltd.', [('KL-SS-001', 30), ('KL-SC-003', 100), ('KL-MA-005', 60)]),
]
for cust, lines in orders:
    try:
        ddate = add_days(today(), random.randint(7, 21))
        frappe.get_doc({
            'doctype': 'Sales Order', 'customer': cust,
            'transaction_date': add_days(today(), -random.randint(10, 45)),
            'delivery_date': ddate,
            'selling_price_list': PRICE_LIST, 'currency': 'INR', 'company': COMPANY,
            'items': [{'item_code': ic, 'qty': qty, 'rate': rate(ic), 'delivery_date': ddate} for ic, qty in lines],
        }).insert(ignore_permissions=True)
        print(f'  Sales Order: {cust}')
    except Exception as e:
        print(f'  SO SKIP {cust}: {e}')
frappe.db.commit()

# ── PURCHASE ORDERS ───────────────────────────────────────────────────────────
pos = [
    ('Tata Steel Ltd.', [('KL-SC-001', 1000), ('KL-SC-002', 500)]),
    ('Henkel Adhesives India', [('KL-CA-003', 50), ('KL-CA-004', 30)]),
    ('JSW Steel Ltd.', [('KL-SC-003', 800), ('KL-MA-001', 2000)]),
    ('Hilti India Pvt. Ltd.', [('KL-MA-005', 100), ('KL-SS-002', 50)]),
]
for supp, lines in pos:
    try:
        sdate = add_days(today(), random.randint(7, 30))
        frappe.get_doc({
            'doctype': 'Purchase Order', 'supplier': supp,
            'transaction_date': add_days(today(), -random.randint(15, 60)),
            'schedule_date': sdate, 'currency': 'INR', 'company': COMPANY,
            'items': [{'item_code': ic, 'qty': qty, 'rate': round(rate(ic) * 0.65, 2), 'schedule_date': sdate} for ic, qty in lines],
        }).insert(ignore_permissions=True)
        print(f'  Purchase Order: {supp}')
    except Exception as e:
        print(f'  PO SKIP {supp}: {e}')
frappe.db.commit()

print()
print('ALL DONE - Klemco India demo data seeded!')
frappe.destroy()
