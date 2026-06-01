# External Items & Subcontracting — Test Report

Date: 2026-06-01 · Stack: 8080 (`frappe_docker-backend-1`, ERPNext v16.14.0) · Site: mysite.localhost
Scope: the two follow-ups requested after the 30/30 deep-cycle program —
(1) the v16 subcontracting **supply → receipt** flow, and (2) the "external items"
(e-waybill, scaled load), taken as far as is possible without external credentials/infra.

---

## 1. Subcontracting supply → receipt (PO-driven, v16) — ✅ 4/4

Runner: [cycle5_subcontracting_runner.py](cycle5_subcontracting_runner.py). Real submitted documents,
stock-ledger assertions, full cleanup.

| Step | Result | Evidence |
|------|--------|----------|
| 1. Subcontracting **Purchase Order** (service item + `fg_item`) submitted | PASS | `is_subcontracted=1`, supplier warehouse set |
| 2. **Subcontracting Order** created from PO + submitted | PASS | `make_subcontracting_order`; `supplied_items` auto-derived from BOM (1 row) |
| 3. **Subcontracting Receipt** created from SCO + submitted | PASS | `make_subcontracting_receipt` |
| 4. FG received **+5** and raw **consumed** at the subcontractor | PASS | FG bin `0 → 5`; RAW bin `20 → 10` (2× per FG, per the Subcontracting BOM) |

Setup exercised the complete v16 chain: default BOM (FG←RAW), **Subcontracting BOM**
(FG ← service + raw), raw supplied to the subcontractor warehouse, and backflush consumption
on receipt. Confirms the modern PO-driven subcontracting model works end-to-end on this build.

**Fix applied (test harness):** the india_compliance hook reads `.taxes` on the Subcontracting
Receipt — set to `[]` before submit (same pattern already used for Stock Entries in cycles 2 & 5).

---

## 2. e-Waybill JSON generation (creds-free path) — ✅ PASS

Runner: [external_items_runner.py](external_items_runner.py). Builds a B2C invoice > ₹50,000 with
transport details and calls `india_compliance...e_waybill.generate_e_waybill_json`.

| Check | Result | Evidence |
|-------|--------|----------|
| Sales Invoice (₹100,000, goods HSN) submitted | PASS | `SINV-26-…`, grand_total 100000 |
| **e-Waybill JSON generated** (no NIC call) | PASS | valid `billLists` JSON, ~2 KB, with transport (`Road`, vehicle, distance 50 km) |

This proves the **entire e-waybill data pipeline works offline** — the JSON that would be
posted to the NIC portal is produced and valid. Reaching a green result surfaced the exact
prerequisites e-waybill enforces (each was a real requirement, not a defect):

1. `company_address` on the invoice (from-address).
2. From-address **pincode** present.
3. **Goods** HSN on the line (service `99…` HSN is correctly rejected — e-waybill is for goods movement).

### ⚠️ Demo-data finding (worth fixing in the seed data)
The company address `Klemco India - Main-Billing` (GSTIN `03AALCK8220C1ZX`) has
`is_your_company_address=1` **but no Dynamic Link to the Company**. e-waybill (and other
company-address lookups) validate via that link, so generation fails with *"Company Address
Name does not belong to the Company"* until the link exists. The test adds it temporarily and
removes it afterward. **Recommend: link the company billing address to "Klemco India (Demo)"
in the setup seed** so e-waybill works out of the box. (No `pincode` on it either — add one.)

### Still requires credentials (cannot be done in this environment)
- **Live e-waybill generation** (actual EWB number from the portal) needs **NIC/GSP API
  credentials** configured in *GST Settings* (sandbox or production). The JSON above is exactly
  what gets submitted; only the authenticated portal call is missing.

---

## 3. Scaled load test — ✅ PASS

Host-side, authenticated, against `frappe.client.get_list` (Sales Order) on the 8080 stack.

| Run | Concurrency | Requests | Throughput | Errors | P50 / P95 / P99 / max |
|-----|-------------|----------|-----------|--------|------------------------|
| Baseline (NFR smoke) | 40 | 800 | 252 req/s | 0 | 96 / 235 / — / — ms |
| **Scaled** | **100** | **3000** | **355 req/s** | **0 (0.0%)** | **311 / 463 / 674 / 694 ms** |

0 errors at 100 concurrent; P95 stayed under 500 ms and throughput rose (the 2-worker pool
saturates cleanly rather than collapsing). **Caveat unchanged:** the dev stack runs 2 gunicorn
workers × 4 threads — a true 500-virtual-user load test needs a horizontally scaled deployment
(more workers/replicas + a real load tool such as k6/Locust). This run confirms stability and
headroom at the moderate-high concurrency the dev stack can represent.

---

## Summary

| Item | Status |
|------|--------|
| Subcontracting supply → receipt (v16) | ✅ 4/4, stock movement verified |
| e-Waybill JSON generation (offline) | ✅ pipeline works; live portal call needs NIC/GSP creds |
| Scaled load (100 concurrent) | ✅ 0 errors, P95 463 ms, 355 req/s |
| Company-address → Company link (demo seed) | ⚠️ missing — recommend adding to setup |
| Live e-waybill / 500-VU load / 8080 frontend image rebuild | ⛔ require external creds / scaled infra (out of this environment) |

All test documents were cancelled and deleted; demo data restored (customer type, item HSN,
company-address pincode/link). No residual data.
