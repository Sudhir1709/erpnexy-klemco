# Klemco CRM — CS Module · Test Execution Report

| | |
|---|---|
| **Report date** | 2026-06-01 |
| **Cycle** | Phase 1 — Automated server suite (comprehensive) |
| **Application** | `klemco_cs` v1.3 on ERPNext v16.14.0 / Frappe v16.16.0 |
| **Other apps on stack** | india_compliance, hrms, crm |
| **Environment** | `http://localhost:8080` · site `mysite.localhost` (8080 stack) |
| **Build under test** | `main` @ `35814b3` (PRs #2–#6) |
| **Tooling** | Frappe `FrappeTestCase` via `bench run-tests --app klemco_cs` |
| **Reference spec** | CRM_CS_BRD_PRD_v1.3 |

---

## 1. Executive Summary

| Metric | Result |
|---|---|
| Test cases executed | **52** |
| Passed | **52 (100%)** |
| Failed / Errored | **0** |
| Duration | ~2.9 s |
| App-logic defects | **0** |
| Robustness fixes applied | **1** (naming_series defaults) |
| Requirements verified | All v1.3 feedback items CR-09…CR-18 + supporting BR-/FR- |

**Verdict:** PASS. All in-scope functional requirements and business-rule gates for the
CS Module v1.3 behave as specified. No defects in application logic were found. The suite
is committed and repeatable (regression-safe) and leaves the database clean.

---

## 2. Scope & Approach

**In scope (this cycle):** server-side unit + integration tests of the `klemco_cs`
customizations — Sales Order, Sales Invoice, Delivery Note, Item, KM Order, CS Complaint.

**Approach:**
- Validation logic exercised by invoking the hooked functions directly with realistic docs.
- Hook *registration* asserted separately (proves the handlers are wired to each doctype).
- KM Order / Complaint / Item use real documents; existing demo Sales Orders are reused for
  anything needing an SO, avoiding GST/stock transaction scaffolding.
- Item-creating tests self-clean (ERPNext Item inserts commit, bypassing test rollback).

**Isolation:** runs against the site DB with per-test rollback; the few committing paths
(Item insert) are explicitly cleaned up. Post-run verification confirmed **0 leftover test
records**.

---

## 3. Results by Module

| Module | Test file | Cases | Pass | Requirements covered |
|---|---|---:|---:|---|
| Schema/customizations | `test_customizations.py` | 4 | 4 | custom fields, KM doctypes, Delivery Challan PF, roles |
| Sales Order | `test_sales_order.py` | 16 | 16 | CR-09/FR-SO-16, CR-14/FR-SO-04, CR-10/FR-SO-06/BR-SO-01, CR-17/FR-SO-09 |
| Sales Invoice | `test_sales_invoice.py` | 8 | 8 | CR-13/FR-DP-11/BR-DP-06 |
| Delivery Note | `test_delivery_note.py` | 6 | 6 | CR-16, CR-15/FR-DP-12 |
| Item (KM approval) | `test_item_km_approval.py` | 5 | 5 | CR-18/BR-KM-02 |
| KM Order | `test_km_order.py` | 5 | 5 | CR-11/FR-KM-08, BR-KM-01, BR-KM-02 |
| CS Complaint | `test_cs_complaint.py` | 8 | 8 | BR-CM-01, FR-8-02, FR-CM-11, BR-CM-06, BR-CM-05, FR-8-08 |
| **Total** | | **52** | **52** | |

---

## 4. Detailed Test Inventory (all PASS)

**Schema (4):** custom_fields_present · delivery_challan_print_format · km_order_doctypes_exist · roles_present

**Sales Order (16):** backdated_header_blocked · backdated_line_blocked · future_date_allowed · today_allowed ·
3pl_others_without_note_blocked · 3pl_others_with_note_ok · 3pl_configured_ok · rc_discount_flags_deviation ·
rc_zero_discount_no_deviation · non_rc_discount_no_deviation · before_submit_blocks_unapproved_deviation ·
before_submit_allows_approved_deviation · deviation_decision_requires_sales_head · deviation_decision_rejects_invalid ·
ack_email_sent_without_delivery_date · hooks_registered

**Sales Invoice (8):** is_cod_true_for_cod_customer · is_cod_false_for_regular · validate_sets_is_cod_flag ·
cod_blocked_without_cheque · cod_partial_cheque_still_blocked · cod_passes_with_full_cheque · non_cod_has_no_gate ·
hooks_registered

**Delivery Note (6):** carry_instructions_from_so · carry_skips_when_already_set · linked_sales_order_resolution ·
get_so_test_certificates_lists_attached_files · get_so_test_certificates_empty_without_so · hooks_registered

**Item — KM approval (5):** unapproved_km_item_cannot_be_enabled · disabled_km_item_saves_as_pending ·
fully_approved_km_item_enables · role_gate_blocks_unauthorized_approval · hooks_registered

**KM Order (5):** km_order_requires_linked_sales_order · make_km_order_maps_qty_from_so ·
matches_so_flag_recomputed_on_edit · happy_submit_sets_confirmed · unapproved_km_item_blocks_submit

**CS Complaint (8):** requires_linked_sales_order · sla_hours_by_priority · sla_deadline_set ·
algorithm_suggested_by_type · override_without_reason_blocked · escalation_when_sla_mostly_consumed ·
no_escalation_when_fresh · csat_survey_on_close

---

## 5. Requirements Coverage

| Item (BRD v1.3) | Requirement | Verified |
|---|---|---|
| CR-09 | FR-SO-16 — Required Delivery Date not back-dated | ✅ |
| CR-10 | FR-SO-06 / BR-SO-01 — RC discount = conditional deviation → Sales Head | ✅ |
| CR-11 | FR-KM-08 — Create KM Order from SO (guided review) | ✅ |
| CR-12 | Delivery Challan consolidation (print format exists/default) | ✅ schema · ⏳ visual render (Phase 4) |
| CR-13 | FR-DP-11 / BR-DP-06 — COD cheque capture + gate | ✅ |
| CR-14 | FR-SO-04 — Preferred 3PL "Others" + note | ✅ |
| CR-15 | FR-DP-12 — Warehouse test-certificate download | ✅ |
| CR-16 | Delivery instructions on the Challan | ✅ |
| CR-17 | FR-SO-09 — Simplified acknowledgement (no delivery date) | ✅ |
| CR-18 | BR-KM-02 — KM item triple approval (+ Supply Chain) | ✅ |
| — | BR-KM-01 — KM Order must link a parent SO | ✅ |
| — | BR-CM-01/05/06, FR-8-02/8-08, FR-CM-11 — Complaint SLA/routing/escalation/CSAT | ✅ |

---

## 6. Defects & Observations

| # | Type | Severity | Description | Status |
|---|---|---|---|---|
| 1 | Robustness | P3 | KM Order & CS Complaint had no `naming_series` default → code-created docs crashed on insert (UI unaffected). | **Fixed** — defaults added (PR #6) |
| — | App-logic defects | — | None found. | — |

**Test-environment notes (not product defects):**
- ERPNext `Item` inserts commit mid-transaction → handled with unique codes + explicit cleanup.
- A `CS Complaint Workflow` governs the status transition; the CSAT *trigger* is verified directly.
- Real Sales Order/Invoice creation requires GST (india_compliance) + stock scaffolding → deferred to the API E2E phase.

---

## 7. Not Executed This Cycle (future phases)

Per the agreed scope (automated server suite only), these remain open and are planned in
[TEST_STRATEGY.md](TEST_STRATEGY.md) §10:

- **Phase 2 — API E2E:** SO → Delivery Challan → Invoice → POD; SO → KM Order; complaint lifecycle.
- **Phase 3 — RBAC (§11 matrix) + notifications** (recipient/content, incl. dispatch & complaint).
- **Phase 4 — UI / client-script:** date-picker bound, deviation buttons, KM review pane, cheque section, test-cert download, Delivery Challan print render.
- **Phase 5 — NFR smoke + security checks.**
- **Phase 6 — UAT** persona scenarios (business sign-off).

---

## 8. Reproduction

```bash
docker exec frappe_docker-backend-1 \
  bench --site mysite.localhost run-tests --app klemco_cs
# → Ran 52 tests … OK
```

Single module, e.g.:
```bash
docker exec frappe_docker-backend-1 \
  bench --site mysite.localhost run-tests --app klemco_cs --module klemco_cs.tests.test_sales_order
```

---

## 9. Conclusion

The CS Module v1.3 passes a comprehensive automated server-side test suite (52/52) with no
application-logic defects. The suite is committed under `klemco_cs/klemco_cs/tests/` and runs
in ~3 seconds, providing a regression safety net for future changes. Recommend proceeding to
Phase 2 (API E2E) and Phase 3 (RBAC + notifications) for full end-to-end and access-control
assurance before go-live.
