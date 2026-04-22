import frappe
from frappe.utils import today, add_days, add_months, nowdate
import random

def run():
    frappe.set_user("Administrator")

    # ── 1. COMPANY ──────────────────────────────────────────────────────────
    if not frappe.db.exists("Company", "Klemco India Pvt. Ltd."):
        company = frappe.get_doc({
            "doctype": "Company",
            "company_name": "Klemco India Pvt. Ltd.",
            "abbr": "KIPL",
            "default_currency": "INR",
            "country": "India",
            "phone_no": "+91-7973288056",
            "email": "info@klemcoindia.com",
            "website": "https://klemcoindia.com",
            "company_description": "40+ years in fixing technology. Precision. Innovation. Excellence.",
        })
        company.insert(ignore_permissions=True)
        print("✓ Company created")
    else:
        print("  Company already exists")

    company_name = "Klemco India Pvt. Ltd."

    # ── 2. TERRITORIES ──────────────────────────────────────────────────────
    territories = [
        ("India", "All Territories"),
        ("Punjab", "India"),
        ("Amritsar", "Punjab"),
        ("Maharashtra", "India"),
        ("Thane", "Maharashtra"),
        ("Mumbai", "Maharashtra"),
        ("Delhi NCR", "India"),
        ("Karnataka", "India"),
        ("Bangalore", "Karnataka"),
        ("Telangana", "India"),
        ("Hyderabad", "Telangana"),
        ("Tamil Nadu", "India"),
        ("Chennai", "Tamil Nadu"),
        ("Gujarat", "India"),
        ("Ahmedabad", "Gujarat"),
        ("USA", "All Territories"),
        ("Missouri", "USA"),
        ("Saint Louis", "Missouri"),
        ("Middle East", "All Territories"),
        ("UAE", "Middle East"),
    ]
    for name, parent in territories:
        if not frappe.db.exists("Territory", name):
            frappe.get_doc({"doctype": "Territory", "territory_name": name, "parent_territory": parent}).insert(ignore_permissions=True)
    print("✓ Territories created")

    # ── 3. CUSTOMER GROUPS ──────────────────────────────────────────────────
    customer_groups = [
        ("MEP Contractors", "All Customer Groups"),
        ("HVAC & Refrigeration", "All Customer Groups"),
        ("Data Centers", "All Customer Groups"),
        ("Metro & Rail", "All Customer Groups"),
        ("Hospitals & Healthcare", "All Customer Groups"),
        ("Hotels & Hospitality", "All Customer Groups"),
        ("Industrial", "All Customer Groups"),
        ("Commercial Real Estate", "All Customer Groups"),
        ("Residential Builders", "All Customer Groups"),
        ("Government & PSU", "All Customer Groups"),
        ("Distributors", "All Customer Groups"),
        ("Exporters", "All Customer Groups"),
    ]
    for name, parent in customer_groups:
        if not frappe.db.exists("Customer Group", name):
            frappe.get_doc({"doctype": "Customer Group", "customer_group_name": name, "parent_customer_group": parent}).insert(ignore_permissions=True)
    print("✓ Customer Groups created")

    # ── 4. SUPPLIER GROUPS ──────────────────────────────────────────────────
    supplier_groups = [
        ("Raw Material Suppliers", "All Supplier Groups"),
        ("Steel & Metal Suppliers", "All Supplier Groups"),
        ("Chemical Suppliers", "All Supplier Groups"),
        ("Packaging Suppliers", "All Supplier Groups"),
        ("OEM & Trading", "All Supplier Groups"),
        ("Logistics Providers", "All Supplier Groups"),
    ]
    for name, parent in supplier_groups:
        if not frappe.db.exists("Supplier Group", name):
            frappe.get_doc({"doctype": "Supplier Group", "supplier_group_name": name, "parent_supplier_group": parent}).insert(ignore_permissions=True)
    print("✓ Supplier Groups created")

    # ── 5. ITEM GROUPS ──────────────────────────────────────────────────────
    item_groups = [
        ("Fixing Technology", "All Item Groups"),
        ("Pipe Hangers and Clamps", "Fixing Technology"),
        ("Strut Channels and Accessories", "Fixing Technology"),
        ("Anchors", "Fixing Technology"),
        ("Chemical Anchors", "Anchors"),
        ("Mechanical Anchors", "Anchors"),
        ("Fire Stop Solutions", "Fixing Technology"),
        ("Wire Rope Suspension Systems", "Fixing Technology"),
        ("Vibration Controls", "Fixing Technology"),
        ("Seismic Supports", "Fixing Technology"),
        ("Saddle Shoes", "Fixing Technology"),
        ("Services", "All Item Groups"),
        ("Engineering Services", "Services"),
        ("Installation Services", "Services"),
    ]
    for name, parent in item_groups:
        if not frappe.db.exists("Item Group", name):
            frappe.get_doc({"doctype": "Item Group", "item_group_name": name, "parent_item_group": parent}).insert(ignore_permissions=True)
    print("✓ Item Groups created")

    # ── 6. UOM ───────────────────────────────────────────────────────────────
    for uom in ["Nos", "Box", "Set", "Kg", "Meter", "Hour"]:
        if not frappe.db.exists("UOM", uom):
            frappe.get_doc({"doctype": "UOM", "uom_name": uom}).insert(ignore_permissions=True)

    # ── 7. ITEMS ─────────────────────────────────────────────────────────────
    items = [
        # Strut Channels
        ("KL-SC-001", "Strut Channel - 41x41mm Standard", "Strut Channels and Accessories", "Nos", 850, "84839000"),
        ("KL-SC-002", "Strut Channel - 41x21mm Shallow", "Strut Channels and Accessories", "Nos", 620, "84839000"),
        ("KL-SC-003", "Strut Channel - 41x41mm Pre-Galvanized", "Strut Channels and Accessories", "Nos", 950, "84839000"),
        ("KL-SC-004", "2 Hole Short 90 Assembly", "Strut Channels and Accessories", "Nos", 120, "73269099"),
        ("KL-SC-005", "3 Hole Z Fitting Assembly", "Strut Channels and Accessories", "Nos", 145, "73269099"),
        ("KL-SC-006", "Girder Cleat HT", "Strut Channels and Accessories", "Nos", 280, "73269099"),
        ("KL-SC-007", "Corner Connector 4D Type S Assembly", "Strut Channels and Accessories", "Nos", 320, "73269099"),
        ("KL-SC-008", "Girder Cleat LT Assembly", "Strut Channels and Accessories", "Nos", 190, "73269099"),
        ("KL-SC-009", "5 Hole Connector Plate Assembly", "Strut Channels and Accessories", "Nos", 165, "73269099"),
        ("KL-SC-010", "Vario Saddle", "Strut Channels and Accessories", "Nos", 210, "73269099"),
        ("KL-SC-011", "Corner Connector 3D Type FV Assembly", "Strut Channels and Accessories", "Nos", 295, "73269099"),
        ("KL-SC-012", "Angle Connector 90 2+2 Type S Assembly", "Strut Channels and Accessories", "Nos", 275, "73269099"),
        ("KL-SC-013", "4 Hole Long 90 Reinforced Assembly", "Strut Channels and Accessories", "Nos", 340, "73269099"),
        ("KL-SC-014", "Length Wise Saddle D Profile", "Strut Channels and Accessories", "Nos", 225, "73269099"),
        # Pipe Hangers and Clamps
        ("KL-PH-001", "Clevis Hanger - 1/2 inch", "Pipe Hangers and Clamps", "Nos", 95, "73269099"),
        ("KL-PH-002", "Clevis Hanger - 1 inch", "Pipe Hangers and Clamps", "Nos", 110, "73269099"),
        ("KL-PH-003", "Clevis Hanger - 2 inch", "Pipe Hangers and Clamps", "Nos", 145, "73269099"),
        ("KL-PH-004", "Split Ring Hanger - 3/4 inch", "Pipe Hangers and Clamps", "Nos", 85, "73269099"),
        ("KL-PH-005", "Split Ring Hanger - 2 inch", "Pipe Hangers and Clamps", "Nos", 125, "73269099"),
        ("KL-PH-006", "Pipe Strap - Galvanized 1/2 inch", "Pipe Hangers and Clamps", "Nos", 45, "73269099"),
        ("KL-PH-007", "Pipe Clamp Heavy Duty 4 inch", "Pipe Hangers and Clamps", "Nos", 310, "73269099"),
        ("KL-PH-008", "Riser Clamp - 2 inch", "Pipe Hangers and Clamps", "Nos", 220, "73269099"),
        ("KL-PH-009", "U-Bolt Pipe Clamp - 1 inch", "Pipe Hangers and Clamps", "Nos", 75, "73269099"),
        ("KL-PH-010", "Beam Clamp - Flange Type", "Pipe Hangers and Clamps", "Nos", 185, "73269099"),
        # Chemical Anchors
        ("KL-CA-001", "Chemical Anchor Capsule M12 - Standard", "Chemical Anchors", "Nos", 380, "38244000"),
        ("KL-CA-002", "Chemical Anchor Capsule M16 - High Strength", "Chemical Anchors", "Nos", 520, "38244000"),
        ("KL-CA-003", "Chemical Anchor Injectable Resin 300ml", "Chemical Anchors", "Nos", 1250, "38244000"),
        ("KL-CA-004", "Chemical Anchor Injectable Resin 500ml", "Chemical Anchors", "Nos", 1850, "38244000"),
        ("KL-CA-005", "Anchor Mixing Nozzle (Pack of 10)", "Chemical Anchors", "Box", 450, "39259090"),
        # Mechanical Anchors
        ("KL-MA-001", "Expansion Anchor M10 - Wedge Type", "Mechanical Anchors", "Nos", 65, "73181500"),
        ("KL-MA-002", "Expansion Anchor M12 - Wedge Type", "Mechanical Anchors", "Nos", 85, "73181500"),
        ("KL-MA-003", "Sleeve Anchor M10x100", "Mechanical Anchors", "Nos", 72, "73181500"),
        ("KL-MA-004", "Sleeve Anchor M12x120", "Mechanical Anchors", "Nos", 98, "73181500"),
        ("KL-MA-005", "Undercut Anchor M16 - High Load", "Mechanical Anchors", "Nos", 245, "73181500"),
        ("KL-MA-006", "Screw Anchor M6 x 50mm", "Mechanical Anchors", "Nos", 28, "73181500"),
        # Fire Stop
        ("KL-FS-001", "Fire Stop Collar DN50 - 2hr Rating", "Fire Stop Solutions", "Nos", 1850, "38140000"),
        ("KL-FS-002", "Fire Stop Collar DN110 - 2hr Rating", "Fire Stop Solutions", "Nos", 2450, "38140000"),
        ("KL-FS-003", "Fire Stop Sealant 600ml - Grey", "Fire Stop Solutions", "Nos", 980, "38140000"),
        ("KL-FS-004", "Fire Stop Pillow 100x100x50mm", "Fire Stop Solutions", "Nos", 650, "38140000"),
        ("KL-FS-005", "Fire Stop Mortar 5kg Pail", "Fire Stop Solutions", "Nos", 1450, "38140000"),
        # Wire Rope
        ("KL-WR-001", "Wire Rope Hanger Kit - Light Duty 1.5m", "Wire Rope Suspension Systems", "Set", 385, "73121090"),
        ("KL-WR-002", "Wire Rope Hanger Kit - Medium Duty 2m", "Wire Rope Suspension Systems", "Set", 520, "73121090"),
        ("KL-WR-003", "Wire Rope Gripper Clip", "Wire Rope Suspension Systems", "Nos", 95, "73121090"),
        ("KL-WR-004", "Ceiling Anchor for Wire Rope", "Wire Rope Suspension Systems", "Nos", 75, "73269099"),
        # Vibration Controls
        ("KL-VC-001", "Anti-Vibration Mount - Type A 10kg", "Vibration Controls", "Nos", 450, "40169390"),
        ("KL-VC-002", "Anti-Vibration Mount - Type B 25kg", "Vibration Controls", "Nos", 680, "40169390"),
        ("KL-VC-003", "Spring Hanger Isolator - 50kg", "Vibration Controls", "Nos", 1250, "84839000"),
        # Seismic
        ("KL-SS-001", "Seismic Brace Kit - 4-Way", "Seismic Supports", "Set", 4500, "73089090"),
        ("KL-SS-002", "Seismic Clevis Brace 12mm Rod", "Seismic Supports", "Nos", 850, "73089090"),
        # Saddle Shoes
        ("KL-SH-001", "Insulated Saddle Shoe - 2 inch", "Saddle Shoes", "Nos", 320, "73269099"),
        ("KL-SH-002", "Insulated Saddle Shoe - 4 inch", "Saddle Shoes", "Nos", 490, "73269099"),
        ("KL-SH-003", "MSS Pipe Saddle 6 inch", "Saddle Shoes", "Nos", 780, "73269099"),
        # Services
        ("KL-SV-001", "Engineering Design & Drawing", "Engineering Services", "Hour", 2500, "998312"),
        ("KL-SV-002", "Site Survey & Consultation", "Engineering Services", "Hour", 2000, "998312"),
        ("KL-SV-003", "BIM Coordination Service", "Engineering Services", "Hour", 3000, "998312"),
        ("KL-SV-004", "Installation & Supervision", "Installation Services", "Hour", 1500, "998311"),
        ("KL-SV-005", "Pre-Fabrication Service", "Installation Services", "Hour", 1800, "998311"),
    ]

    for item_code, item_name, group, uom, rate, hsn in items:
        if not frappe.db.exists("Item", item_code):
            is_stock = 1 if not group.endswith("Services") and group != "Engineering Services" and group != "Installation Services" else 0
            frappe.get_doc({
                "doctype": "Item",
                "item_code": item_code,
                "item_name": item_name,
                "item_group": group,
                "stock_uom": uom,
                "is_stock_item": is_stock,
                "gst_hsn_code": hsn,
                "standard_rate": rate,
                "description": item_name,
                "company": company_name,
            }).insert(ignore_permissions=True)
    print("✓ Items created")

    # ── 8. CUSTOMERS ─────────────────────────────────────────────────────────
    customers = [
        ("Larsen & Toubro Ltd.", "MEP Contractors", "Mumbai", "Maharashtra", "India"),
        ("Tata Projects Ltd.", "MEP Contractors", "Hyderabad", "Telangana", "India"),
        ("Shapoorji Pallonji & Co.", "Commercial Real Estate", "Mumbai", "Maharashtra", "India"),
        ("Thermax Ltd.", "Industrial", "Pune", "Maharashtra", "India"),
        ("Blue Star Ltd.", "HVAC & Refrigeration", "Mumbai", "Maharashtra", "India"),
        ("Voltas Ltd.", "HVAC & Refrigeration", "Mumbai", "Maharashtra", "India"),
        ("Carrier Midea India", "HVAC & Refrigeration", "Gurgaon", "Haryana", "India"),
        ("DMRC (Delhi Metro Rail Corp)", "Metro & Rail", "Delhi NCR", "Delhi", "India"),
        ("Mumbai Metro One Pvt. Ltd.", "Metro & Rail", "Mumbai", "Maharashtra", "India"),
        ("Apollo Hospitals", "Hospitals & Healthcare", "Chennai", "Tamil Nadu", "India"),
        ("Fortis Healthcare", "Hospitals & Healthcare", "Gurgaon", "Haryana", "India"),
        ("IHG Hotels & Resorts India", "Hotels & Hospitality", "Bangalore", "Karnataka", "India"),
        ("Hyatt Hotels India", "Hotels & Hospitality", "Mumbai", "Maharashtra", "India"),
        ("Nxtdigital Ltd. (Data Center)", "Data Centers", "Mumbai", "Maharashtra", "India"),
        ("CtrlS Datacenters", "Data Centers", "Hyderabad", "Telangana", "India"),
        ("Godrej Properties", "Commercial Real Estate", "Mumbai", "Maharashtra", "India"),
        ("DLF Ltd.", "Commercial Real Estate", "Delhi NCR", "Delhi", "India"),
        ("Brigade Group", "Residential Builders", "Bangalore", "Karnataka", "India"),
        ("Prestige Group", "Residential Builders", "Bangalore", "Karnataka", "India"),
        ("NTPC Ltd.", "Government & PSU", "Delhi NCR", "Delhi", "India"),
        ("ONGC Ltd.", "Government & PSU", "Mumbai", "Maharashtra", "India"),
        ("Rite Fix Solutions (Distributor)", "Distributors", "Amritsar", "Punjab", "India"),
        ("Punjab Building Supplies", "Distributors", "Ludhiana", "Punjab", "India"),
        ("Gulf MEP Trading LLC", "Exporters", "Dubai", "Dubai", "UAE"),
    ]

    for cname, cgroup, city, state, country in customers:
        if not frappe.db.exists("Customer", cname):
            c = frappe.get_doc({
                "doctype": "Customer",
                "customer_name": cname,
                "customer_group": cgroup,
                "territory": city if frappe.db.exists("Territory", city) else country,
                "customer_type": "Company",
            })
            c.insert(ignore_permissions=True)
    print("✓ Customers created")

    # ── 9. SUPPLIERS ─────────────────────────────────────────────────────────
    suppliers = [
        ("Tata Steel Ltd.", "Steel & Metal Suppliers", "Mumbai"),
        ("JSW Steel Ltd.", "Steel & Metal Suppliers", "Mumbai"),
        ("Jindal Steel & Power", "Steel & Metal Suppliers", "Delhi NCR"),
        ("Hilti India Pvt. Ltd.", "OEM & Trading", "Mumbai"),
        ("Fischer Fixings India", "OEM & Trading", "Chennai"),
        ("Henkel Adhesives India", "Chemical Suppliers", "Mumbai"),
        ("BASF India Ltd.", "Chemical Suppliers", "Mumbai"),
        ("Supreme Packaging", "Packaging Suppliers", "Amritsar"),
        ("Blue Dart Express", "Logistics Providers", "Mumbai"),
        ("DTDC Courier", "Logistics Providers", "Bangalore"),
        ("VRL Logistics", "Logistics Providers", "Hubli"),
    ]

    for sname, sgroup, city in suppliers:
        if not frappe.db.exists("Supplier", sname):
            frappe.get_doc({
                "doctype": "Supplier",
                "supplier_name": sname,
                "supplier_group": sgroup,
                "country": "India",
            }).insert(ignore_permissions=True)
    print("✓ Suppliers created")

    # ── 10. PRICE LIST ───────────────────────────────────────────────────────
    if not frappe.db.exists("Price List", "Klemco Standard Rate"):
        frappe.get_doc({
            "doctype": "Price List",
            "price_list_name": "Klemco Standard Rate",
            "currency": "INR",
            "buying": 0,
            "selling": 1,
            "enabled": 1,
        }).insert(ignore_permissions=True)

    for item_code, item_name, group, uom, rate, hsn in items:
        if frappe.db.exists("Item", item_code):
            if not frappe.db.exists("Item Price", {"item_code": item_code, "price_list": "Klemco Standard Rate"}):
                frappe.get_doc({
                    "doctype": "Item Price",
                    "item_code": item_code,
                    "price_list": "Klemco Standard Rate",
                    "price_list_rate": rate,
                    "currency": "INR",
                }).insert(ignore_permissions=True)
    print("✓ Price List created")

    # ── 11. WAREHOUSES ───────────────────────────────────────────────────────
    warehouses = [
        ("Amritsar Main Store - KIPL", "All Warehouses"),
        ("Thane Branch Store - KIPL", "All Warehouses"),
        ("Finished Goods - KIPL", "All Warehouses"),
        ("Raw Material Store - KIPL", "All Warehouses"),
        ("Inspection Hold - KIPL", "All Warehouses"),
        ("Scrap - KIPL", "All Warehouses"),
    ]
    for wname, parent in warehouses:
        if not frappe.db.exists("Warehouse", wname):
            frappe.get_doc({
                "doctype": "Warehouse",
                "warehouse_name": wname,
                "parent_warehouse": parent,
                "company": company_name,
            }).insert(ignore_permissions=True)
    print("✓ Warehouses created")

    # ── 12. SALES QUOTATIONS (sample) ────────────────────────────────────────
    sample_quotes = [
        ("Larsen & Toubro Ltd.", [("KL-SC-001", 100), ("KL-PH-003", 50), ("KL-MA-003", 200)]),
        ("Blue Star Ltd.", [("KL-VC-001", 20), ("KL-WR-001", 30), ("KL-SC-004", 40)]),
        ("Apollo Hospitals", [("KL-FS-001", 15), ("KL-FS-003", 10), ("KL-CA-003", 5)]),
        ("DMRC (Delhi Metro Rail Corp)", [("KL-SS-001", 25), ("KL-SS-002", 40), ("KL-SC-001", 60)]),
    ]

    for customer, order_items in sample_quotes:
        try:
            q = frappe.get_doc({
                "doctype": "Quotation",
                "quotation_to": "Customer",
                "party_name": customer,
                "transaction_date": add_days(today(), -random.randint(5, 30)),
                "valid_till": add_days(today(), 30),
                "selling_price_list": "Klemco Standard Rate",
                "currency": "INR",
                "items": [
                    {
                        "item_code": ic,
                        "qty": qty,
                        "rate": frappe.db.get_value("Item Price", {"item_code": ic, "price_list": "Klemco Standard Rate"}, "price_list_rate") or 100,
                    }
                    for ic, qty in order_items
                ],
            })
            q.insert(ignore_permissions=True)
        except Exception as e:
            print(f"  Quotation skip ({customer}): {e}")
    print("✓ Sample Quotations created")

    # ── 13. SALES ORDERS (sample) ─────────────────────────────────────────────
    sample_orders = [
        ("Tata Projects Ltd.", [("KL-SC-001", 200), ("KL-SC-002", 150), ("KL-MA-001", 500)]),
        ("Voltas Ltd.", [("KL-PH-001", 100), ("KL-PH-002", 80), ("KL-VC-002", 15)]),
        ("Godrej Properties", [("KL-CA-001", 50), ("KL-CA-002", 30), ("KL-FS-001", 20)]),
    ]

    for customer, order_items in sample_orders:
        try:
            so = frappe.get_doc({
                "doctype": "Sales Order",
                "customer": customer,
                "transaction_date": add_days(today(), -random.randint(10, 45)),
                "delivery_date": add_days(today(), random.randint(7, 21)),
                "selling_price_list": "Klemco Standard Rate",
                "currency": "INR",
                "company": company_name,
                "items": [
                    {
                        "item_code": ic,
                        "qty": qty,
                        "rate": frappe.db.get_value("Item Price", {"item_code": ic, "price_list": "Klemco Standard Rate"}, "price_list_rate") or 100,
                        "delivery_date": add_days(today(), random.randint(7, 21)),
                    }
                    for ic, qty in order_items
                ],
            })
            so.insert(ignore_permissions=True)
        except Exception as e:
            print(f"  Sales Order skip ({customer}): {e}")
    print("✓ Sample Sales Orders created")

    # ── 14. PURCHASE ORDERS (sample) ──────────────────────────────────────────
    sample_po = [
        ("Tata Steel Ltd.", [("KL-SC-001", 1000), ("KL-SC-002", 500)]),
        ("Henkel Adhesives India", [("KL-CA-003", 50), ("KL-CA-004", 30)]),
    ]

    for supplier, po_items in sample_po:
        try:
            po = frappe.get_doc({
                "doctype": "Purchase Order",
                "supplier": supplier,
                "transaction_date": add_days(today(), -random.randint(15, 60)),
                "schedule_date": add_days(today(), random.randint(7, 30)),
                "currency": "INR",
                "company": company_name,
                "items": [
                    {
                        "item_code": ic,
                        "qty": qty,
                        "rate": frappe.db.get_value("Item Price", {"item_code": ic, "price_list": "Klemco Standard Rate"}, "price_list_rate") or 100,
                        "schedule_date": add_days(today(), random.randint(7, 30)),
                    }
                    for ic, qty in po_items
                ],
            })
            po.insert(ignore_permissions=True)
        except Exception as e:
            print(f"  Purchase Order skip ({supplier}): {e}")
    print("✓ Sample Purchase Orders created")

    frappe.db.commit()
    print("\n✅ Klemco India seed data complete!")

run()
