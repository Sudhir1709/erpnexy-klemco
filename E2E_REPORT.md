# Klemco CRM — CS Module · End-to-End (Phase 2) Report

| | |
|---|---|
| **Report date** | 2026-06-01 |
| **Cycle** | Phase 2 — API end-to-end + GST document chain |
| **Environment** | `http://localhost:8080` · site `mysite.localhost` |
| **Driver** | `e2e_runner.py` (real document chains on the live site) |

---

## 1. Executive Summary

| Metric | Result |
|---|---|
| E2E steps executed | **6** |
| Passed | **6 (100%)** |
| Failed | **0** |
| Full GST chain | SO → Delivery Challan → **GST Sales Invoice** verified |

**Verdict: PASS.** The complete order-to-invoice flow works end-to-end on real documents,
with the `klemco_cs` customizations behaving correctly in-flow. One environment defect was
found and fixed (server scripts disabled — see §4).

---

## 2. Flows Executed (all PASS)

| Step | Flow | Evidence |
|---|---|---|
| E2E-1.1 | Create + submit **Sales Order** (in-stock item, future date) | SO submitted, status "To Deliver and Bill" |
| E2E-1.2 | Create + submit **Delivery Challan** (Delivery Note) | DN submitted; **CR-16** delivery instructions carried from SO onto the challan |
| E2E-1.3 | Create + submit **GST Sales Invoice** | INV submitted, grand total ₹1,000 (GST applied) |
| E2E-1.4 | **Linked trail** SO → DN → Invoice | both DN and Invoice link back to the SO |
| E2E-2 | **RC deviation** on a real SO: flagged → submit **blocked** → Sales Head **approves** → submits | full approval cycle on a live submittable SO (`set_deviation_decision`) |
| E2E-3 | **KM Order** from the real SO → confirm | KM Order created from SO, submitted → "KM Confirmed" |

All created documents were cancelled + deleted afterwards; post-run checks confirmed the demo
returned to baseline (11 SOs / 5 invoices / 0 DNs / 0 KM orders; SKU007 stock restored to 190).

---

## 3. GST Enablement Performed

To exercise the GST document chain on the demo:
- Confirmed the company **is GST-registered** — company address GSTIN `03AALCK8220C1ZX` (Punjab).
- Set `gst_hsn_code` on the items used (`SKU007`, `KL-SH-003`) — demo items shipped without HSN.
- Enabled `server_script_enabled` (see §4).

> The **e-waybill** step (FR-4-07 / FR-7-05) calls the external NIC GST portal API and is **out of
> scope** for automated execution. Its prerequisite — a valid GST invoice — is verified (E2E-1.3).
> e-waybill is best validated manually against the NIC sandbox or via the boundary contract.

---

## 4. Findings

| # | Type | Severity | Finding | Action |
|---|---|---|---|---|
| 1 | Environment/config | **P2** | `server_script_enabled` was **off**, so the demo's `CS SO Discount Check` server script raised `ServerScriptNotEnabled` — **blocking every Sales Order save** (UI and API). | **Fixed:** enabled `server_script_enabled` (site + global). **Recommend persisting** it in the deployment site config so SO creation works on a fresh bring-up. |
| 2 | Data | P4 | Demo items lack `gst_hsn_code`; required by india_compliance to create GST documents. | Set HSN on the two items used; recommend back-filling HSN across the item master before GST go-live. |
| — | App-logic | — | None — `klemco_cs` behaved correctly throughout the chain. | — |

**Note on POD (FR-DP-09):** ERPNext's Delivery Note has no standard "Proof of Delivery"
upload; the DN submission is the dispatch/challan milestone. If digital POD (signature/photo/GPS)
is required, add a custom field/flow — not present today.

---

## 5. Reproduction

```bash
docker exec frappe_docker-backend-1 \
  bash -lc 'cd /home/frappe/frappe-bench && ./env/bin/python e2e_runner.py'
# → 6/6 steps passed
```
Prereq on a fresh site: `bench --site mysite.localhost set-config server_script_enabled 1`
and ensure the items used carry `gst_hsn_code`.

---

## 6. Recommendation

Order-to-invoice works end-to-end with the CS customizations intact. Before go-live:
1. **Persist `server_script_enabled`** in the deployment config (P2 — otherwise SO creation is blocked).
2. **Back-fill item HSN** and customer GSTINs for full GST/e-waybill operation.
3. UAT the **e-waybill** path against the NIC sandbox (external).
4. Decide on a **POD capture** mechanism if digital proof of delivery is required.
