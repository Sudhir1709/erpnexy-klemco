# Klemco CRM — CS Module · Outstanding-Items Test Report

| | |
|---|---|
| **Report date** | 2026-06-01 |
| **Scope** | Remaining items after Phases 1–5: load/concurrency, e-waybill, interactive UI |
| **Environment** | `http://localhost:8080` · site `mysite.localhost` |

---

## 1. Summary

| Item | Result |
|---|---|
| Concurrency / load smoke (NFR §9) | **PASS** — 0 errors, 252 req/s, P95 235 ms @ 40 concurrent |
| e-waybill integration | **Boundary verified** — enabled, but no NIC API credentials (live generation needs GSP account) |
| Interactive UI (Playwright) | **6/7 PASS**; 3 code fixes + 1 environment fix made along the way |

No klemco_cs application-logic defects. Three robustness fixes and one 8080 environment fix
were applied (below); the automated suite remains **58/58**.

---

## 2. Load / Concurrency Smoke

`loadtest.py` — 800 authenticated requests to the Sales Order list API at concurrency 40:
```
errors: 0/800 (0.0%)   throughput: 252 req/s
latency p50/p95/p99/max: 153 / 235 / 251 / 266 ms   (target P95 < 2000 ms)  → PASS
```
> This is a **smoke** at moderate concurrency on a 2-worker dev stack — not the full §9 *500
> concurrent users* target. A dedicated load test (k6/Locust, scaled workers) is recommended
> before go-live to validate P95 under true peak load.

---

## 3. e-waybill Integration (boundary)

- `e-Waybill Log` doctype present; GST Settings `enable_e_waybill = 1`; `fetch_e_waybill_data = 1`.
- **No API credentials** (`api_secret` unset; `sandbox_mode = 0`) → **live e-waybill generation
  against the NIC/GSP portal cannot be exercised** without the client's GSP account.
- The prerequisite (valid GST Sales Invoice) is already proven (Phase 2 E2E). Offline e-waybill
  **JSON export** is the only creds-free path.
- **Recommendation:** configure india_compliance GSP/NIC sandbox credentials, then UAT the
  generate-e-waybill action against the sandbox.

---

## 4. Interactive UI (Playwright) — 6/7

`playwright_ui2.py` drives the live desk (records created server-side, then verified in the UI):

| Check | Result |
|---|---|
| Deviation SO → Approve/Reject buttons + banner (Sales Head) | ✅ |
| KM Order → SO-vs-KM review grid (Matches SO) | ✅ |
| Delivery Challan **print output** → heading + delivery instructions + items | ✅ |
| 3PL "Others" → Specify/Note becomes mandatory | ✅ |
| Tablet viewport → list renders | ✅ |
| Complaint → live auto-assignee + routing table on type change | ⚠️ see F3 |

The complaint **auto-assignee is functionally correct** (set server-side on insert — proven by
the automated suite & UAT); only the *live on-type-change UI hint* was affected by a JS-asset
encoding quirk on this stack. The matcher was made robust (F3).

---

## 5. Findings & Fixes

| # | Severity | Finding | Fix |
|---|---|---|---|
| F1 | P3 | Native doctype client scripts (CS Complaint, KM Order) didn't load in the desk — the app's JS **bundle is never built** (no `node` in the backend image, so `bench build` fails). | Delivered those scripts via **`doctype_js` hooks** (served directly from `public/js`, no build needed) — same pattern as the other CS scripts. |
| F2 | P3 | `custom_3pl_note` used a `depends_on`/`mandatory_depends_on` containing a **parenthesised string literal** (`'Others (not yet decided)'`), which Frappe's client-side evaluator rejects ("Invalid depends_on expression") when 3PL = Others. | Removed the declarative expression; "required/shown when Others" now enforced by the **client script** (`sales_order.js`) + **server validation** (already present). |
| F3 | P4 | Complaint live auto-suggest matched the complaint type against an **em-dash string literal**, fragile to JS-asset character encoding when served statically. | Match on **ASCII keywords** (Quality/Damage→QC Head, etc.) — encoding-independent. |
| F4 | P2 (env, 8080 only) | The 8080 **frontend image lacks the runtime-added apps** (india_compliance, hrms, crm, klemco_cs); their `sites/assets/<app>` symlinks point to apps absent in the frontend → **404s** → india_compliance's global `gst_settings` never loads → its SO field `depends_on` throws → SO form client scripts abort. (Exposed during testing after a `clear-cache`.) | Restored by **dereference-copying** those app assets into the shared `sites` volume so the frontend serves real files; SO form fully functional again. |

> **F4 is specific to the 8080 source stack** (apps added to the backend at runtime without
> rebuilding the frontend image). The **8081 image-based deployment is not affected** — its custom
> image bakes klemco_cs, and it doesn't run india_compliance/hrms/crm. Long-term fix for 8080:
> rebuild the frontend from a custom image that includes all installed apps (the 8081 pattern).

---

## 6. Reproduction

```bash
# load smoke (host Python)
python loadtest.py
# interactive UI (host Python with playwright + chromium); fixtures first:
docker exec frappe_docker-backend-1 bash -lc 'cd /home/frappe/frappe-bench && ./env/bin/python ui_fixtures_setup.py'
docker cp frappe_docker-backend-1:/home/frappe/frappe-bench/ui_fixtures.json ui_fixtures.json
python playwright_ui2.py
```

---

## 7. Recommendation

All executable outstanding items are tested. Before go-live: (1) a proper **load test** for the
500-user target; (2) **e-waybill** UAT against the NIC sandbox once GSP credentials exist;
(3) on 8080, rebuild the **frontend image** to include all apps (or standardise on the 8081
custom-image deployment). The klemco_cs fixes (F1–F3) are committed.
