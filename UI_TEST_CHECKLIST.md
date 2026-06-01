# Klemco CRM — CS Module · Phase 4 Manual UI Test Checklist

Front-end / client-script acceptance checks for the v1.3 CS Module. The **logic** behind each
item is already verified by the automated suite / UAT / E2E; this checklist confirms the **desk UI
renders and behaves** as designed. Run a business walkthrough and fill the Result column.

| | |
|---|---|
| **URL** | http://localhost:8080 (or 8081) · site `mysite.localhost` |
| **Admin** | `Administrator` / `admin` |
| **Approver login** | a user with the **Sales Head** role (for deviation approval) |
| **Dept users** | `*.head@klemcoindia.com` / `Klemco@2024` |
| **Browser** | latest Chrome/Edge/Firefox; also spot-check tablet width |

Result legend: **P** = pass · **F** = fail (log a defect) · **N/A**.

---

## 1. Sales Order Processing

| ID | Persona | Steps | Expected (UI) | Result |
|---|---|---|---|---|
| UI-SO-01 | CS Exec | New → Sales Order; scroll the Klemco CS section | "Preferred 3PL", "3PL — Specify / Note", "Delivery Instructions", "RC Conditional Deviation", "Deviation Approval Status" fields are present | ☐ |
| UI-SO-02 | CS Exec | In Items, open the **Required Delivery Date** picker | Calendar **cannot select a past date** (bounded to today); typing a past date is rejected on save with a clear message | ☐ |
| UI-SO-03 | CS Exec | Set **Preferred 3PL = "Others (not yet decided)"** | The **"3PL — Specify / Note"** field becomes **mandatory**; saving without it is blocked | ☐ |
| UI-SO-04 | CS Exec | Pick a **RC (Rate Contract)** customer, add an item with a **discount %**, Save | Order saves; **RC Conditional Deviation = ✓** and **Deviation Approval Status = "Pending Sales Head Approval"**; a banner indicates the deviation | ☐ |
| UI-SO-05 | CS Exec | On the pending-deviation SO, try **Submit** | Submission is **blocked** with the BR-SO-01 message | ☐ |
| UI-SO-06 | **Sales Head** | Open the same SO | **"Approve Deviation" / "Reject Deviation"** buttons appear (under an action group); clicking Approve sets status = Approved and allows submit | ☐ |
| UI-SO-07 | CS Exec | Open the same SO as a non-Sales-Head user | The Approve/Reject Deviation buttons are **not shown** | ☐ |
| UI-SO-08 | Customer mailbox | Submit an order; check the acknowledgement email | Email says order execution initiated; **no "expected delivery date"** line | ☐ |

---

## 2. Order Execution

| ID | Persona | Steps | Expected (UI) | Result |
|---|---|---|---|---|
| UI-OE-01 | CS Exec | Order list / SO header for a deviation order | The deviation status is clearly visible (status field + banner), making the pending approver obvious | ☐ |

---

## 3. KM Manufacturing

| ID | Persona | Steps | Expected (UI) | Result |
|---|---|---|---|---|
| UI-KM-01 | CS Exec | Open a submitted Sales Order → **Create ▸ KM Order** | Opens a KM Order pre-filled from the SO | ☐ |
| UI-KM-02 | CS Exec | In the KM Order, review the items grid | Each row shows **SO Qty** vs **KM Qty** with a **"Matches SO"** indicator; editing KM Qty away from SO Qty clears the match flag and raises a headline alert | ☐ |
| UI-KM-03 | CS Exec | Submit the KM Order ("Confirm & Create") | Status → **KM Confirmed** | ☐ |
| UI-KM-04 | CS Exec | New Item → tick **KM-Managed Item** | The three approval checkboxes + KM Approval Status appear; a banner lists pending approvals | ☐ |
| UI-KM-05 | CS Supervisor | On a KM-managed Item, try to tick each approval | Can tick **only** "Approved — CS Supervisor"; the Plant Head / Supply Chain checks are read-only | ☐ |
| UI-KM-06 | KM Plant Head / Supply Chain | Tick the respective approval | Each role can tick only its own check; once all three are set, the item can be **enabled** (disabled un-ticked) | ☐ |

---

## 4. Dispatch & Logistics

| ID | Persona | Steps | Expected (UI) | Result |
|---|---|---|---|---|
| UI-DP-01 | Warehouse | Open the Delivery Note (Challan) created from an SO that had Delivery Instructions | The **Delivery Instructions** from the SO are shown on the Challan | ☐ |
| UI-DP-02 | Warehouse | On the Delivery Note, view the Test Certificates panel | Test certificates attached to the SO are listed with **Download** links | ☐ |
| UI-DP-03 | Finance/CS | Create a Sales Invoice for a **COD** customer | The **COD cheque** section (No./Bank/Date/Amount/Copy) is shown; **submitting without cheque details is blocked** | ☐ |
| UI-DP-04 | CS Exec | Delivery Note → **Print** | The default print format is **"Delivery Challan"**; it shows items, ship-to, and the delivery-instructions block | ☐ |
| UI-DP-05 | Customer mailbox | Submit a Delivery Note | Customer receives a **"dispatched"** notification email | ☐ |

---

## 5. Complaint Management

| ID | Persona | Steps | Expected (UI) | Result |
|---|---|---|---|---|
| UI-CM-01 | CS Exec | New → CS Complaint; pick a Complaint Type | **Assigned/Algorithm-Suggested** updates to the mapped department (e.g. Product/Quality → QC Head); a **routing-logic table** is visible | ☐ |
| UI-CM-02 | CS Exec | Change **Assigned To** away from the suggestion, Save | An **Override Reason** is required; saving without it is blocked | ☐ |
| UI-CM-03 | CS Exec | Open an existing complaint | An **SLA banner / countdown** is shown; colour shifts Green → Amber → Red as the deadline nears | ☐ |
| UI-CM-04 | CS Exec | Set a complaint to **Closed** (via the workflow) | A **CSAT survey triggered** message appears; the customer receives the CSAT email | ☐ |
| UI-CM-05 | (data) | Leave a Medium complaint until ≥80% SLA (or use a short test SLA) | Status auto-moves to **Escalated**; CS Manager receives the escalation email | ☐ |

---

## 6. Cross-cutting

| ID | Steps | Expected | Result |
|---|---|---|---|
| UI-X-01 | Log in as each role (CS Exec, CS Manager, Sales Head, Warehouse, Finance) | Each sees only the menus/actions permitted by the §11 matrix | ☐ |
| UI-X-02 | Open the **Customer Service** workspace | Shows CS Complaint + KM Orders shortcuts/links | ☐ |
| UI-X-03 | Resize to tablet width on the Order list & Complaint list | Layout remains usable (NFR §9 responsiveness) | ☐ |

---

### Defect log (fill on any F)
| UI-ID | Severity | Observed vs expected | Screenshot/notes |
|---|---|---|---|
| | | | |
