# Klemco CRM — CS Module · Phase 3 Report (RBAC + Notifications)

| | |
|---|---|
| **Report date** | 2026-06-01 |
| **Cycle** | Phase 3 — Role-based access (submission & approval) + notifications |
| **Environment** | `http://localhost:8080` · site `mysite.localhost` |
| **Driver** | `rbac_runner.py` (clean single-role test users; gates executed AS each role) |

---

## 1. Executive Summary

| Metric | Result |
|---|---|
| Checks executed | **48** |
| Passed | **48 (100%)** |
| Failed | **0** |

**Verdict: PASS.** Submission and approval rights are correctly separated by role. Employees
(CS Executive) can submit operational documents but **cannot approve**; approvals are restricted
to the designated approver roles. Two coverage observations are noted in §5.

---

## 2. Submission vs Approval — by role (the key question)

| Action | Employee (CS Executive) | Manager (CS Manager) | Approver (Sales Head) | KM Plant Head | Supply Chain | Finance | Warehouse |
|---|:--:|:--:|:--:|:--:|:--:|:--:|:--:|
| **Create/Submit KM Order** | ✅ | ✅ | — | ❌ | ❌ | ❌ | ❌ |
| **Create CS Complaint** | ✅ | ✅ | — | — | — | ❌ | ❌ |
| **Delete CS Complaint** | ❌ | ✅ | — | — | — | — | — |
| **Approve RC discount deviation** | ❌ | ❌ | ✅ | — | — | ❌ | — |
| **Grant KM item — CS Supervisor approval** | ❌ | — | — | ❌ | ❌ | — | — |
| **Grant KM item — KM Plant Head approval** | ❌ | — | — | ✅ | ❌ | — | — |
| **Grant KM item — Supply Chain approval** | ❌ | — | — | ❌ | ✅ | — | — |
| **Create Sales Invoice** | ❌ | — | — | — | — | ✅ | — |
| **Submit Delivery Note (dispatch)** | ❌ | — | — | — | — | ❌ | ✅ |

> The headline result: **an employee can submit, but only the approver role can approve.** The RC
> discount deviation is approvable **only by Sales Head** — not by a CS Manager or Finance — and
> each KM-item approval can be granted **only by its specific role** (CS Supervisor / KM Plant Head /
> Supply Chain Lead), so the triple-approval cannot be self-completed by one person.

---

## 3. Permission Matrix (verified via `has_permission`)

| Doctype | Action | Allowed roles (verified) |
|---|---|---|
| Sales Order | create | Sales User / Sales Manager (core) — **not** CS Executive/Manager/Sales Head/Finance directly |
| KM Order | create / submit | CS Executive, CS Manager, CS Supervisor (✅); KM Plant Head, Supply Chain, Finance, Warehouse (❌) |
| CS Complaint | create | CS Executive, CS Manager, CS Supervisor (✅); Warehouse, Finance (❌) |
| CS Complaint | delete | CS Manager only |
| Sales Invoice | create | Accounts Manager (✅); CS Executive, Warehouse (❌) |
| Delivery Note | submit | Stock User (✅); CS Executive, Finance (❌) |

All 30 matrix assertions matched expectations.

---

## 4. Approval Gates (executed AS each role)

| Gate | Employee (CS Exec) | Manager (CS Mgr) | Finance | Approver |
|---|:--:|:--:|:--:|:--:|
| RC discount deviation (`set_deviation_decision`) | ❌ denied | ❌ denied | ❌ denied | ✅ Sales Head |
| KM item triple approval | ❌ none | — | — | ✅ only the matching role per check |

All 13 approval-gate assertions matched expectations (denied for non-approvers; allowed only for the
designated role).

---

## 5. Notifications

| Check | Result |
|---|---|
| SO acknowledgement email — trigger + content (no delivery date, FR-SO-09/CR-17) | ✅ correct recipient & content |
| Configured `Notification` records for CS doctypes (SO/KM/Complaint/DN/Invoice) | **0 found** |

**Observation (P3 — coverage gap):** Only the **Sales Order acknowledgement email** is implemented
(in code). The broader BRD notification set — dispatch SMS/email (FR-OE-08/FR-DP-08), complaint
logged / SLA-breach / closed (FR-8.8 §8.8), credit-block, etc. — is **not yet configured** as
Notification records or code. These are functionally absent today.

---

## 6. Findings & Recommendations

| # | Severity | Finding | Recommendation |
|---|---|---|---|
| 1 | P3 | `CS Executive` role alone lacks **Sales Order create** permission (BRD §11 lists CS Exec as SO creator). Mitigated today because demo department users also hold **Sales User**. | Either grant the CS roles explicit SO perms, or formally document that CS staff carry Sales User. |
| 2 | P3 | BRD notifications largely **unimplemented** (only SO acknowledgement exists). | Implement the §x.8 notification matrix as Frappe Notification records / hooks before go-live; then re-run this phase. |
| — | — | Submission/approval **role separation is correct and enforced server-side.** | — |

---

## 7. Reproduction
```bash
docker exec frappe_docker-backend-1 \
  bash -lc 'cd /home/frappe/frappe-bench && ./env/bin/python rbac_runner.py'
# → 48/48 checks passed
```
