# Klemco CRM — CS Module · Test Strategy

**Application under test:** ERPNext v16 + `klemco_cs` (Customer Service Module v1.3) and the
ancillary apps on the stack (`india_compliance`, `hrms`, `crm`).
**Primary environment:** `http://localhost:8080` → site `mysite.localhost`.
**Reference spec:** `CRM_CS_BRD_PRD_v1.3` (FR-/BR-/CR- IDs are cited throughout).

---

## 1. Objectives & Quality Goals

| Goal | Measure |
|---|---|
| Every BRD functional requirement behaves as specified | 100% of FR-* have ≥1 passing test |
| Every business rule is enforced (and can't be bypassed) | 100% of BR-* covered by a negative + positive test |
| v1.3 feedback items work end-to-end | CR-09…CR-18 each verified |
| No regression in core ERPNext order→invoice→dispatch flow | Happy-path E2E green |
| Role-based access is correct | RBAC matrix (§11) verified per role |
| NFR targets met | Page load, save, notification latency within §9 budgets |

**Definition of Done (per requirement):** positive test passes, negative/validation test passes,
the relevant BRD acceptance criterion (§x.10) is demonstrated, and it's traceable in the matrix (§7).

---

## 2. Scope

**In scope**
- `klemco_cs` customizations: Sales Order, Delivery Note, Sales Invoice, Item custom fields + `doc_events`
- KM Order doctype + "Create KM Order from SO" flow
- CS Complaint module (intake, routing, SLA, escalation, closure)
- Cross-document flows: SO → Delivery Challan → Invoice → (e-waybill) → POD; SO → KM Order
- Business rules & approval gates (discount/RC deviation, COD cheque, KM triple approval)
- RBAC for CS roles
- Notifications (acknowledgement, dispatch, complaint) — content/trigger, with email captured in test mode

**Out of scope (or mocked/stubbed)**
- External integrations exercised only at the boundary: GST e-waybill NIC API, SMS gateway, 3PL tracking APIs, WMS — verified via contract/mocks, not live third parties
- Core ERPNext internals already covered by upstream tests (we test our *use* of them, not the framework)
- Load/scale beyond a smoke-level NFR check (full perf test is a separate effort)

---

## 3. Test Levels

| Level | What | How | Owner |
|---|---|---|---|
| **Unit** | Pure functions / validations in isolation (e.g. `_validate_delivery_dates`, `_flag_rc_deviation`) | Frappe `FrappeTestCase` / pytest, mocked docs | Dev |
| **Integration** | doc_events firing on real docs; cross-doctype effects (SO→DN field carry, KM Order from SO) | `bench run-tests --app klemco_cs` against a test DB | Dev |
| **System / E2E** | Full business flows across modules via the API/UI | REST API scripts + UI automation | QA |
| **UAT** | Persona-based scenarios from the BRD (Priya/Rajesh/Meera) | Manual scripted test cases | Business |
| **Regression** | Re-run the automated suite on every change/migrate | CI / `bench run-tests` | Dev/CI |

---

## 4. Test Types & Coverage

1. **Functional (FR-*)** — each requirement's happy path.
2. **Business-rule / validation (BR-*)** — each rule blocks the disallowed action (negative) and permits the allowed one (positive).
3. **Workflow / approval** — RC discount deviation → Sales Head; COD cheque gate; KM item triple approval; complaint SLA escalation.
4. **RBAC** — the §11 access matrix: each (role × action) cell allowed/denied.
5. **Notifications & alerts** — correct trigger, recipient, and template; **no delivery date** in the SO acknowledgement (FR-SO-09).
6. **Negative / boundary** — back-dated dates, missing mandatory docs, over-limit credit, missing cheque, unapproved KM item.
7. **Data integrity / linkage** — SO↔KM Order↔Invoice link trail; complaint↔order link.
8. **Non-functional (§9)** — page-load < 2s (P95), order save < 3s, notification < 60s, smoke concurrency.
9. **Security** — auth required, RBAC enforced server-side (not just UI), no privilege escalation, audit trail present.
10. **Compatibility / UI** — desk forms render; client scripts (date-picker bound, deviation buttons, KM review, cheque section, test-cert download) behave on a modern browser.

---

## 5. Environment & Test Data

- **Target:** 8080 stack, `mysite.localhost`, Administrator/admin; department users (`*.head@klemcoindia.com` / `Klemco@2024`).
- **Automated tests** run against an **isolated test database** (`bench run-tests` auto-creates/uses `test_*`), so they never pollute demo data and are repeatable.
- **Seed/fixtures:** a known baseline — 1 RC customer, 1 COD customer, 1 regular customer; items (in-stock, low-stock, OOS); a KM-managed item (approved + unapproved); price list/contract. Created via test `setUp` or a seed script, not by hand.
- **Email:** Frappe test mode captures outbound mail (`frappe.flags`/`frappe.local.flags.in_test`) so we assert on content without sending.
- **External APIs:** stub e-waybill / SMS / 3PL responses.

---

## 6. Tooling

| Need | Tool |
|---|---|
| Server unit/integration | Frappe `FrappeTestCase` (`bench run-tests --app klemco_cs [--module ...]`) |
| API / E2E | Python `requests` or Postman/newman against REST (`/api/resource`, `/api/method`) |
| UI / client-script | Playwright (or Cypress) headless against the desk |
| Coverage | `bench run-tests --coverage` |
| Reporting | JUnit XML from test runs + a traceability matrix (this doc §7) |

---

## 7. Requirements Traceability Matrix

**Automated server suite (Phase 1) — last run: 52 tests, all passing** via
`bench --site mysite.localhost run-tests --app klemco_cs` on the 8080 stack.
Tests live in `klemco_cs/klemco_cs/tests/` and `klemco_cs/.../doctype/*/test_*.py`.

| Req ID | Module | Test module | Status |
|---|---|---|---|
| schema | All | `test_customizations` (4) — custom fields, KM doctypes, print format, roles | ✅ |
| FR-SO-16 / CR-09 | Sales Order | `test_sales_order` — back-date hdr+line blocked; today/future allowed | ✅ |
| FR-SO-04 / CR-14 | Sales Order | `test_sales_order` — 3PL "Others" needs note; configured passes | ✅ |
| FR-SO-06 / BR-SO-01 / CR-10 | Sales Order | `test_sales_order` — RC discount flags deviation + Sales Head gate; non-RC/zero no gate; decision role-gated | ✅ |
| FR-SO-09 / CR-17 | Sales Order | `test_sales_order` — ack email sent, **no** delivery date | ✅ |
| (wiring) | Sales Order | `test_sales_order` — validate/before_submit/on_submit hooks registered | ✅ |
| FR-DP-11 / BR-DP-06 / CR-13 | Sales Invoice | `test_sales_invoice` — COD detect; blocked w/o full cheque; passes w/ cheque; non-COD no gate | ✅ |
| CR-16 | Delivery Note | `test_delivery_note` — instructions carried SO→DN; skip-if-set; SO resolution | ✅ |
| FR-DP-12 / CR-15 | Delivery Note | `test_delivery_note` — warehouse lists/downloads SO test certs | ✅ |
| BR-KM-02 / CR-18 | Item | `test_item_km_approval` — unapproved can't enable; pending save; 3-approved enables; role gate blocks | ✅ |
| BR-KM-01 | KM Order | `test_km_order` — KM Order without SO blocked | ✅ |
| FR-KM-08 / CR-11 | KM Order | `test_km_order` — create-from-SO maps qty; matches-flag recompute; happy submit → KM Confirmed | ✅ |
| BR-KM-02 | KM Order | `test_km_order` — unapproved KM item blocks submit | ✅ |
| BR-CM-01 | Complaint | `test_cs_complaint` — requires linked SO | ✅ |
| FR-8-02 | Complaint | `test_cs_complaint` — SLA hours by priority; deadline set | ✅ |
| FR-CM-11 | Complaint | `test_cs_complaint` — auto-assignee by category | ✅ |
| BR-CM-06 | Complaint | `test_cs_complaint` — override without reason blocked | ✅ |
| BR-CM-05 | Complaint | `test_cs_complaint` — escalate at ≥80% SLA; no escalation when fresh | ✅ |
| FR-8-08 | Complaint | `test_cs_complaint` — CSAT survey flag on closure | ✅ |
| CR-12 | Dispatch | "Delivery Challan" print format exists/default — schema test ✅; visual render | ⏳ Phase 4 (UI) |
| §11 matrix | All | role × action allow/deny | ⏳ Phase 3 (not selected this round) |
| FR-OE-08 / FR-DP-08 notifications | All | dispatch/complaint notification content | ⏳ Phase 3 |
| §9 NFR | All | load/save/notification latency | ⏳ Phase 5 |
| E2E flows | All | SO→Challan→Invoice→POD; SO→KM Order; complaint lifecycle | ⏳ Phase 2 (API, not selected) |

### Run report (Phase 1)
- **Scope chosen:** automated server suite, comprehensive depth.
- **Result:** 52/52 passing, ~3s, isolated (item-creating tests self-clean since ERPNext Item inserts commit).
- **Approach notes:** validation logic is unit-tested by invoking the hooked functions directly; hook
  *registration* is asserted separately; KM Order / Complaint / Item use real docs (existing demo Sales
  Orders are reused for anything needing an SO, avoiding GST/stock scaffolding).
- **Re-run:** `docker exec frappe_docker-backend-1 bench --site mysite.localhost run-tests --app klemco_cs`
- **Defects found:** none in app logic. Two robustness fixes applied while testing — `naming_series`
  defaults added to KM Order & CS Complaint so code-created docs don't crash on insert.
- **Not yet executed (future phases):** API E2E, RBAC matrix, notifications, UI/client-script, NFR, UAT.

---

## 8. Entry / Exit Criteria

**Entry:** app installed & migrated on 8080; test DB available; baseline fixtures defined; this strategy agreed.
**Exit (per cycle):** all P1/P2 cases executed; 0 open P1 (blocker) / P2 (critical) defects; ≥95% P3 pass;
traceability matrix complete; test run report published.

---

## 9. Defect Management

| Severity | Definition | Example |
|---|---|---|
| P1 Blocker | Core flow broken / data loss / security hole | Cannot save SO; RBAC bypass |
| P2 Critical | A business rule not enforced | RC deviation submits without approval |
| P3 Major | Functional gap, workaround exists | Ack email missing a field |
| P4 Minor | Cosmetic / copy | Label typo |

Each defect: steps, expected vs actual, env, severity, screenshot/log, linked Req ID.

---

## 10. Execution Plan (phased)

1. **Phase 0 – Setup:** test-DB fixtures + harness; smoke that the app loads. *(fast)*
2. **Phase 1 – Unit/Integration (automated):** all FR-/BR- for klemco_cs via `bench run-tests`. *(highest ROI; regression-safe)*
3. **Phase 2 – E2E (API):** SO→Challan→Invoice→POD, SO→KM Order, complaint lifecycle.
4. **Phase 3 – RBAC + Notifications.**
5. **Phase 4 – UI / client-script** automation (or scripted manual).
6. **Phase 5 – NFR smoke + Security checks.**
7. **Phase 6 – UAT** persona scenarios (business sign-off).
8. **Report:** traceability matrix + run summary + defect list.

---

## 11. Risks

| Risk | Mitigation |
|---|---|
| External APIs unavailable for E2E | Stub/mocks; test the boundary contract |
| Test data pollution in demo site | Use isolated `bench run-tests` DB |
| Custom fields/print format drift after migrate | Assert schema in Phase 0; re-run on every migrate |
| Flaky UI automation | Prefer API assertions; keep UI tests thin & data-seeded |
