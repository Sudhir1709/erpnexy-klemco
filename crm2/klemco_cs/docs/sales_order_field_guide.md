# Sales Order → "More Info" tab — Field Guide

A plain-language reference for every section on the **More Info** tab of a Sales Order.

The tab has two kinds of sections:

- **Klemco Customer-Service sections** — built for the Klemco CS workflow (order type, approvals, credit
  control, dispatch documents). These drive real business rules.
- **Standard ERPNext sections** — stock features that ship with ERPNext (Status, Commission, Sales Team,
  Auto Repeat, Print Settings, UTM Analytics, Additional Info). Most are optional.

> **Rule of thumb:** For a normal customer order you only need to set the order type and attach the mandate
> documents. If you're unsure about a *standard* ERPNext field, **leave it blank** — it won't hold up the
> order. See the cheat-sheet at the end.

---

## Part 1 — Klemco Customer-Service sections

### Customer Service
| Field | Purpose |
|---|---|
| **Order Type** | *One-Shot* = the whole order ships in a single delivery. *Open (Phased Delivery)* = staggered/phased delivery against a delivery plan (each line can carry its own required-delivery date). Pick **One-Shot** for a normal order. |
| **Rate Contract Customer** | Read-only flag pulled from the Customer master. When ticked, **discounts are blocked** on every line (BR-SO-01). You don't set this here — it comes from the customer. |

### Order Execution
| Field | Purpose |
|---|---|
| **Delivery Instructions** | Free text for special handling — unloading requirements, delivery time windows, safety requirements. Printed on the Delivery Challan for the warehouse/transporter. |
| **Preferred 3PL Partner** | The courier/transporter to use (Mahindra Logistics, DTDC Freight, Blue Dart, Delhivery, EcomExpress, FedEx India, or Other). Optional routing hint for dispatch. |

### Discount Approval
Mostly **system-maintained** — you rarely type here directly; the approval workflow fills it in.

| Field | Purpose |
|---|---|
| **Discount Approval Status** | *Not Required / Discount Approval — Sales Head / Approved / Rejected.* Auto-set based on the discount given vs the threshold. |
| **Approved By** / **Approval Timestamp** | Who approved the extra discount and when (read-only, set by the system). |
| **Discount Threshold (%)** | The limit above which an order needs **Sales Head approval** (BR-OE-01). A line discount over this % routes the order for approval before it can proceed. |
| **Approval / Rejection Remarks** | Notes the approver leaves when approving or rejecting. |

### Credit Control
**System-maintained** by the credit-check logic — informational for the sales user.

| Field | Purpose |
|---|---|
| **Credit Hold Status** | *Clear* or *On Hold.* An order goes *On Hold* when the customer breaches their credit terms; Finance must release it. |
| **Hold Reason** | Why the order is on credit hold (read-only). |
| **Released By** | The Finance user who cleared the hold (read-only). |

### Mandate Documents
The compliance documents that must accompany the order.

| Field | Purpose |
|---|---|
| **Customer PO Copy** | Scanned/digital purchase order from the customer (BR-SO-02). Some customers require this before the order can proceed. |
| **Test Certificates** | Quality/test certificates for the goods. Supports multiple files / a ZIP (CR-03). |

### Dispatch & Tracking
Populated during/after dispatch.

| Field | Purpose |
|---|---|
| **Docket / LR #** | The transporter's docket / lorry-receipt number for the consignment. |
| **Tracking URL** | Link to the courier's live tracking page. |
| **Proof of Delivery (POD)** | Photo, signature, or GPS confirmation that the goods were delivered (FR-4-09). |
| **Client Order Confirmation** | A **Word document (.docx / .doc only)** supplied by the customer that maps *their* internal SKUs to Klemco SKUs — the warehouse needs it during packing. On save it is **auto-attached to the linked Delivery Note** (FR-SO-15 / BR-SO-08). |

---

## Part 2 — Standard ERPNext sections

### Status
Read-only progress indicators that **ERPNext maintains automatically** as the order moves through delivery
and billing. Nothing to fill in here.

| Field | Meaning |
|---|---|
| **Status** | Where the order is in its lifecycle (Draft → To Deliver and Bill → Completed → Closed/Cancelled). |
| **% Delivered** | How much of the ordered quantity has shipped (via Delivery Notes). |
| **% Amount Billed** | How much of the order value has been invoiced (via Sales Invoices). |
| **% Picked** | How much has been picked in the warehouse (via Pick Lists), if you use picking. |

*(Delivery Status / Billing Status / Advance Payment Status are hidden helper fields.)*

### Commission
Use this **only if an external agent / sales partner earns a commission** on the order.

| Field | Purpose |
|---|---|
| **Sales Partner** | The external agent/broker/dealer for this deal. |
| **Commission Rate** / **Total Commission** | The % and the resulting commission amount payable to that partner. |
| **Amount Eligible for Commission** | The order value the commission is calculated on (read-only). |

Leave the whole section blank if there is no external sales partner.

### Sales Team
Split **internal** credit/incentive across your *own* salespeople (for reporting and incentive tracking).
Add rows of **Sales Person + contribution %** (must total 100%). Optional — leave empty if you don't track
per-salesperson attribution.

### Auto Repeat
Turn this order into a **recurring order**. ERPNext will automatically create a fresh copy of it on a
schedule.

| Field | Purpose |
|---|---|
| **From Date / To Date** | The active window for the recurrence. |
| **Auto Repeat** | Links to the schedule (daily/weekly/monthly…) that regenerates the order. |
| **Update Auto Repeat Reference** | Button to re-link if the schedule changes. |

Use only for standing/subscription orders that repeat on a fixed cadence. Ignore for one-off orders.

### Print Settings
Cosmetic controls for the **printed PDF** of the order — they don't change the order data.

| Field | Purpose |
|---|---|
| **Letter Head** | Which company letterhead appears on the print. |
| **Print Heading** | An alternate title for the printed document. |
| **Print Language** | Language of the printout. |
| **Group same items** | Merge duplicate item rows on the print. |

Defaults are usually fine.

### UTM Analytics
**Marketing attribution** — records which marketing campaign produced this order (used by the CRM).

| Field | Purpose |
|---|---|
| **Source / Medium / Campaign / Content** | The marketing channel/campaign the order can be traced back to. |

Relevant only if you track marketing campaigns in the CRM; otherwise leave blank.

### Additional Info
Miscellaneous references.

| Field | Purpose |
|---|---|
| **Customer's Purchase Order** / **…Order Date** | The customer's PO number and date. *(Klemco also captures the actual PO file under **Mandate Documents → Customer PO Copy**.)* |
| **Is Internal Customer** / **Represents Company** / **Inter Company Order Reference** | Only used for **inter-company** orders — one group company selling to another. Ignore for external customers. |

---

## Cheat-sheet — what do I actually fill for a normal customer order?

| Do fill | Leave to the system / blank |
|---|---|
| **Customer Service → Order Type** (usually *One-Shot*) | Status (auto) |
| **Order Execution → Delivery Instructions / 3PL** (if any) | Discount Approval & Credit Control (workflow-set) |
| **Mandate Documents → Customer PO Copy / Test Certificates** (if required) | Commission, Sales Team (only if you track them) |
| **Dispatch & Tracking → Client Order Confirmation** (the customer's .docx SKU map) | Auto Repeat (only for recurring orders) |
| | Print Settings (defaults fine), UTM Analytics, Additional Info |

*Rate Contract Customer, approval statuses, credit-hold and the % Delivered/Billed indicators are all set
automatically — you don't type them in.*
