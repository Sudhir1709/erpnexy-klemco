# Klemco CRM — CS Module · UAT Report

| | |
|---|---|
| **Report date** | 2026-06-01 |
| **Cycle** | User Acceptance Testing — all modules (v1.3) |
| **Application** | `klemco_cs` v1.3 on ERPNext v16.14.0 / Frappe v16.16.0 |
| **Environment** | `http://localhost:8080` · site `mysite.localhost` (8080 stack) |
| **Build** | `main` @ latest |
| **Driver** | `uat_runner.py` (scenario-driven execution against the live site) |
| **Personas** | Priya (CS Executive), Rajesh (Sales Head), Meera (Finance), CS Manager, KM Plant Head, Supply Chain, Warehouse, Customer |

---

## 1. Executive Summary

| Metric | Result |
|---|---|
| Scenarios executed | **17** |
| Passed | **17 (100%)** |
| Failed | **0** |
| Modules covered | Sales Order, Order Execution, KM Manufacturing, Dispatch & Logistics, Complaint Management |

**Verdict: ACCEPTED (conditional).** Every v1.3 acceptance scenario behaves as the BRD
specifies when exercised end-to-end on the live application. Sign-off is recommended subject
to the front-end and GST items in §4–§5 (UI confirmation + GST master data), which a
server-driven UAT cannot fully cover.

---

## 2. Approach

- Each scenario was **executed against the running 8080 site**, performing the real business
  action on live documents (creating KM Orders & complaints, attaching files, invoking the
  validation/approval/SLA logic), not mocks.
- **Personas** were simulated by switching the active roles (e.g., Sales Head approving a
  deviation, a non-authorised user attempting a KM approval).
- **Existing seeded Sales Orders** were reused for flows needing an SO (KM order, complaint
  linkage, delivery-instruction carry-over).
- Created records were **cleaned up** and mutated seeded records **restored**; post-run checks
  confirmed no residual UAT data.

Re-run: `docker exec frappe_docker-backend-1 bash -lc 'cd /home/frappe/frappe-bench && ./env/bin/python uat_runner.py'`

---

## 3. Scenario Results (all PASS)

| ID | Module | Persona | Acceptance scenario | Result / evidence |
|---|---|---|---|---|
| UAT-SO-01 | Sales Order | Priya | Required Delivery Date cannot be back-dated (future allowed) | back-date blocked; future allowed |
| UAT-SO-02 | Sales Order | Priya | 3PL "Others (not yet decided)" requires a note | blocked without note; OK with note |
| UAT-SO-03 | Order Execution | Priya + Rajesh | RC-customer discount flagged as Conditional Deviation; cannot proceed until Sales Head approves | flagged + blocked pre-approval; allowed after Sales Head approval |
| UAT-SO-04 | Sales Order | Customer | Order acknowledgement email omits a (premature) delivery date | email sent; "initiated order execution"; no delivery date |
| UAT-KM-01 | KM Manufacturing | Priya | Standalone KM order (no parent SO) is not permitted | creation blocked |
| UAT-KM-02 | KM Manufacturing | Priya | "Create KM Order from SO" mirrors SO items/qty for review, then confirms | items mirrored (matches-SO); status → KM Confirmed |
| UAT-KM-03 | KM Manufacturing | CS Supervisor + KM Plant Head + Supply Chain | New KM item needs triple approval; unapproved item can't be enabled or ordered | pending; cannot enable; blocks KM confirm |
| UAT-DP-01 | Dispatch | Warehouse | Delivery instructions from the SO appear on the Delivery Challan | instructions carried through |
| UAT-DP-02 | Dispatch | Warehouse | Warehouse can download test certificates attached to the SO | cert listed/downloadable |
| UAT-DP-03 | Dispatch | Meera (Finance) | COD invoice cannot be submitted without cheque details | COD detected; blocked w/o cheque; allowed with cheque |
| UAT-DP-04 | Dispatch | CS Exec | Delivery Form/Note/Challan consolidated to a single "Delivery Challan" | print format exists & is the DN default |
| UAT-CM-01 | Complaint | Priya | A complaint must be linked to an order | creation blocked without SO |
| UAT-CM-02 | Complaint | Priya | Complaint auto-routes by category | Quality→QC Head; Billing→Finance Lead |
| UAT-CM-03 | Complaint | Priya | SLA deadline assigned by priority | Critical 24h; Low 72h |
| UAT-CM-04 | Complaint | CS Manager | Auto-escalation at ≥80% SLA consumed | escalated at ~94% |
| UAT-CM-05 | Complaint | Priya | Reassigning away from the suggested owner needs a reason | blocked without reason |
| UAT-CM-06 | Complaint | Priya | Closing a complaint triggers a CSAT survey | survey flagged on close |

**17 / 17 passed.**

---

## 4. Front-end Items for Manual UAT Confirmation

Server-driven UAT verifies behavior and rules but not the rendered desk UI. Recommend a quick
business walkthrough of these client-side acceptance points (logic already verified server-side):

- Date picker is visually bounded to today onward (UAT-SO-01).
- "Approve / Reject Deviation" buttons appear for the Sales Head; deviation status banner shows (UAT-SO-03).
- KM Order review pane shows SO vs KM qty with a "Matches SO" indicator before confirm (UAT-KM-02).
- COD "Record Cheque Details" section appears next to Record POD, only for COD customers (UAT-DP-03).
- Delivery Challan **prints** with the instructions block and test-cert download links (UAT-DP-01/02/04).
- Complaint intake shows the routing table and the "🤖 Auto: …" suggested assignee (UAT-CM-02/05).

---

## 5. Environment Caveats / Out of Scope

- **GST not configured in the demo:** company has no GSTIN, customers/items lack GSTIN/HSN. Therefore
  **new** GST documents (fresh Sales Invoice / e-waybill) and the GST-dependent acceptance criteria
  (e-waybill generation, HSN-on-invoice) were **not exercised**; existing seeded SOs/invoices were used
  as evidence for linkage. To UAT the GST/e-waybill path, populate company GSTIN + item HSN + customer
  GSTIN first.
- **External integrations** (SMS gateway, 3PL tracking, NIC e-waybill API) are out of scope — tested only
  at the boundary; live third-party calls were not made.
- **Full physical fulfilment chain** (pick/pack/QC → e-waybill → POD) requires stock + GST setup and is
  best covered in the API E2E phase (Strategy §10, Phase 2).

---

## 6. Defects

**None.** No application-logic defects were observed during UAT. (The earlier `naming_series`
robustness fix from Phase 1 is already merged; code-created KM Orders/Complaints behaved correctly here.)

---

## 7. Recommendation

The CS Module v1.3 **meets its acceptance criteria** across all five modules for the logic and
workflows exercised. Recommended before go-live sign-off:
1. Business walkthrough of the §4 front-end items (UI confirmation).
2. Populate GST master data and UAT the e-waybill / GST-invoice path (§5).
3. Execute Strategy Phases 2–3 (API E2E + RBAC/notifications) for full end-to-end assurance.
