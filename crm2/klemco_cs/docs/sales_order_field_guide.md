# Sales Order — Field Guide

A plain-language reference for the fields on a Sales Order.

- The **Details** tab is the order itself — who's buying, what, from where, and for how much.
- The **More Info** tab holds the Klemco Customer-Service workflow fields plus optional ERPNext extras.

Each field is tagged:

- **You fill** — you enter or attach it.
- **System-set** — filled automatically (read-only).
- **Optional** — only if you use that feature.

> **Rule of thumb:** A normal order needs only Company (Klemco India), Customer, the Items, a Delivery Date,
> and the source Warehouse. Tax now fills in by itself. If a field is *System-set* or *Optional* and you're
> unsure, leave it — it won't hold up the order. Cheat-sheet at the end.

---

## Part A — Details tab (the order)

### Order header
| Field | Tag | Purpose |
|---|---|---|
| **Company** | You fill | Which Klemco entity is selling. **Use "Klemco India"** — it holds the GSTIN, so tax auto-applies. ("Klemco India (Demo)" has no GSTIN and won't auto-tax.) |
| **Series** | System-set | The order-number format (SAL-ORD-YYYY-#####). Auto-assigned on save. |
| **Customer** | You fill | Who's buying. Pulls their price list, addresses, tax info and the Rate-Contract flag. |
| **Order Type** | Optional | ERPNext's classification — *Sales* / Maintenance / Shopping Cart. Leave on **Sales**. (Different from the Klemco "Order Type" on More Info, which is One-Shot vs Phased.) |
| **Date** | System-set | Order date — defaults to today; editable. |
| **Delivery Date** | You fill | When the customer expects the goods. Can't be back-dated (FR-SO-16). |
| **Tax Id** | System-set | The customer's GSTIN, pulled from their record. |
| **Skip Delivery Note** | Optional | Tick for orders with **no physical shipment** (services). Leave off for goods. |

### Accounting Dimensions
| Field | Tag | Purpose |
|---|---|---|
| **Cost Center** | System-set | The cost centre revenue is booked against — usually defaults from the company. |
| **Project** | Optional | Link the order to a Project for revenue/cost tracking. You can create a Project inline here. Leave blank if not project work. |

### Currency & Price List
| Field | Tag | Purpose |
|---|---|---|
| **Currency / Exchange Rate** | System-set | Order currency (INR) and conversion rate — from the customer / price list. |
| **Price List** | You fill | Which price list supplies item rates. Defaults from the customer; change to switch the whole order. |

### Items & Warehouse
| Field | Tag | Purpose |
|---|---|---|
| **Items table** | You fill | The heart of the order — each line: **Item Code**, **Delivery Date**, **Quantity**, Rate. Add via *Add row* / *Add multiple*, or *Get Items From* a Quotation. |
| **Scan Barcode** | Optional | Add items by scanning instead of typing the code. |
| **Set Source Warehouse** | You fill | The warehouse the goods ship **from**. Setting it here applies it to **every item row**. Drives the stock check, reservation, the Delivery Note source, and the Klemco low-stock/backorder warning. For finished goods, pick **Finished Goods**. |
| **Reserve Stock** | Optional | Earmark on-hand stock for this order (needs stock reservation enabled). Off for normal orders. |

### Taxes
| Field | Tag | Purpose |
|---|---|---|
| **Tax Category** | System-set | **In-State** (CGST+SGST) vs **Out-State** (IGST) — **auto-picked** from the plant state (company GSTIN) vs the customer's delivery state. Override only for a special case. |
| **Sales Taxes and Charges Template** | System-set | The GST template applied (Output GST In-state / Out-state), filled from the Tax Category. The rows below show the CGST/SGST/IGST lines. |
| **Shipping Rule** | Optional | Auto-adds a freight/handling charge from a predefined rule. Blank = no freight. |
| **Incoterm / Named Place** | Optional | International delivery terms (EXW, FOB, CIF…) and where they apply. Exports only. |

### Totals & Discount
| Field | Tag | Purpose |
|---|---|---|
| **Total / Net Total / Grand Total** | System-set | Item total, taxes, and the final Grand Total (with Rounded Total and In Words). All calculated. |
| **Advance Paid** | System-set | Advance received against the order, from linked Payment Entries. |
| **Additional Discount** | Optional | An **order-level** discount (% or amount) on the Net/Grand Total, plus an optional Coupon Code. (Line discounts are blocked for Rate-Contract customers — BR-SO-01.) |

---

## Part B — More Info tab · Built for Klemco
The Customer-Service workflow — order type, approvals, credit & dispatch documents.

### Customer Service
| Field | Purpose |
|---|---|
| **Order Type** | *One-Shot* = whole order in one delivery. *Open (Phased Delivery)* = staggered delivery against a plan, each line with its own required date. Pick **One-Shot** for a normal order. |
| **Rate Contract Customer** | Pulled from the Customer master. When ticked, **discounts are blocked** on every line (BR-SO-01). Not set here. |

### Order Execution
| Field | Purpose |
|---|---|
| **Delivery Instructions** | Special handling — unloading, time windows, safety notes. Printed on the Delivery Challan. |
| **Preferred 3PL Partner** | The courier to use (Mahindra, DTDC, Blue Dart, Delhivery, EcomExpress, FedEx India, Other). |

### Discount Approval *(mostly system-set by the approval workflow)*
| Field | Purpose |
|---|---|
| **Discount Approval Status** | Not Required / Discount Approval — Sales Head / Approved / Rejected. Auto from discount vs threshold. |
| **Approved By / Timestamp** | Who approved the extra discount, and when. |
| **Discount Threshold (%)** | Limit above which an order needs **Sales Head approval** (BR-OE-01). |
| **Approval / Rejection Remarks** | Notes left by the approver. |

### Credit Control *(system-maintained)*
| Field | Purpose |
|---|---|
| **Credit Hold Status** | *Clear* or *On Hold*. On hold when the customer breaches credit terms; Finance releases it. |
| **Hold Reason** | Why the order is on hold. |
| **Released By** | The Finance user who cleared the hold. |

### Mandate Documents
| Field | Purpose |
|---|---|
| **Customer PO Copy** | Scanned/digital PO from the customer (BR-SO-02). |
| **Test Certificates** | Quality/test certificates. Supports multiple files or a ZIP. |

### Dispatch & Tracking
| Field | Purpose |
|---|---|
| **Docket / LR #** | The transporter's docket / lorry-receipt number. |
| **Tracking URL** | Link to the courier's tracking page. |
| **Proof of Delivery (POD)** | Photo, signature, or GPS confirmation of delivery (FR-4-09). |
| **Client Order Confirmation** | A **Word document (.docx/.doc only)** from the customer mapping their SKUs to Klemco SKUs — the warehouse needs it during packing. On save it's **auto-attached to the linked Delivery Note** (FR-SO-15 / BR-SO-08). |

---

## Part C — More Info tab · Standard ERPNext
Stock features that ship with ERPNext. Most are optional.

- **Status** — read-only lifecycle + `% Delivered / % Amount Billed / % Picked`. ERPNext maintains these.
- **Commission** — pay an external **Sales Partner/agent** (`sales_partner`, `commission_rate`, `total_commission`). Blank if none.
- **Sales Team** — split internal credit across your own salespeople (Sales Person + contribution %). Optional.
- **Auto Repeat** — make the order recurring (`from/to date`, `auto_repeat`). For standing/subscription orders only.
- **Print Settings** — printed-PDF cosmetics (letter head, print heading, language, group same items). Defaults fine.
- **UTM Analytics** — marketing attribution (source/medium/campaign/content). Only if you track campaigns.
- **Additional Info** — customer PO no./date; inter-company fields (used only for company-to-company orders).

---

## Billing & the warehouse (Sales Invoice)

A Sales Invoice shows **no warehouse** by default — on purpose:

- **Normal flow** — Order → **Delivery Note** (dispatch, where you pick the warehouse) → **Sales Invoice**
  (billing). The warehouse was already set on the Delivery Note and stock moved there, so the invoice just
  bills for what shipped — no warehouse needed.
- **Direct billing** (no Delivery Note) — tick **Update Stock** on the invoice. The **Set Source Warehouse**
  field then appears (pre-filled with the company's Finished Goods warehouse); pick where the stock comes
  from, and billing reduces that stock. Don't use Update Stock when a Delivery Note already moved the stock —
  ERPNext hides the option once invoice items come from a DN, to avoid deducting the same stock twice.

---

## Cheat-sheet — what do I actually fill in?

| You fill in | The system handles |
|---|---|
| **Company** (Klemco India) & **Customer** | **Series, Totals, Grand Total** — computed |
| **Items** — code, qty, delivery date | **Tax** — In-State/Out-State from plant vs delivery state |
| **Set Source Warehouse** — usually Finished Goods | **Status** & the % Delivered/Billed/Picked meters |
| **Klemco Order Type** (One-Shot) + delivery notes / 3PL | **Discount Approval, Credit Control, Rate Contract** flag |
| **Customer PO / Test Certs / Client Order Confirmation**, if required | **Commission, Sales Team, Auto Repeat, UTM** — only if used |
