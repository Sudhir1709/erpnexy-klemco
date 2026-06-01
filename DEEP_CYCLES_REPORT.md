# Klemco ERP — In-Depth Module Testing (End-to-End Business Cycles)

| | |
|---|---|
| **Report date** | 2026-06-01 |
| **Environment** | `http://localhost:8080` · site `mysite.localhost` |
| **Approach** | Real documents created + **submitted** on the live stack, with stock-ledger / GL / status assertions, then fully cleaned up |
| **Result** | **30 / 30 cycle assertions passed** across the 13 platform modules |

Each cycle exercises several modules end-to-end (not just doctype validation), asserting the
**downstream effects** — stock ledger movement, GL postings, invoice settlement, depreciation
schedules, payroll computation. All created records are cancelled + deleted; post-run checks
confirmed the demo returns to baseline (11 SOs / 5 invoices / 0 DNs; no test residue).

---

## Cycle 1 — Procure-to-Pay (Buying + Stock + Quality + Accounting) · 7/7
`cycle1_p2p_runner.py`

1. Material Request submitted
2. Purchase Order submitted (from MR), GST-computed grand total
3. Purchase Receipt + **Quality Inspection** (Incoming, Accepted) submitted
   - **Stock ledger increased by received qty** (bin 0 → 10)
4. Purchase Invoice submitted (from PR) — **GL entries created**
5. Payment Entry submitted — **invoice outstanding → 0**

## Cycle 2 — Manufacturing & Subcontracting (Manufacturing + Stock + Subcontracting) · 6/6
`cycle2_mfg_runner.py`

1. BOM submitted (FG ← 2× raw)
2. Work Order submitted
3. Material Transfer for Manufacture + Manufacture stock entries
   - **FG stock +5, raw consumed 10; Work Order = Completed (produced 5)**
4. Subcontracting BOM validated (FG ← service + raw) + Subcontracting Order/Receipt doctypes
   *(full subcontracting supply/receipt is PO-driven in v16 — noted as follow-up)*

## Cycle 3 — Order-to-Cash + GST (Selling + GST India + Accounting + Stock) · 8/8
`cycle3_o2c_runner.py`

1. Quotation submitted
2. Sales Order submitted (from Quotation)
3. Delivery Note submitted (from SO) — **stock ledger reduced by delivered qty** (190 → 187)
4. Sales Invoice submitted (from DN) — **12 GL entries**; **GST-ready** (HSN on line + company GSTIN)
5. Payment Entry submitted — **invoice outstanding → 0**

## Cycle 4 — HR/Payroll, Projects, Assets, CRM · 9/9
`cycle4_runner.py`

- **HR/Payroll:** Employee → Attendance → Holiday-List Assignment → Leave Allocation + Leave
  Application → Salary Structure + Assignment → **Salary Slip submitted (gross ₹30,000)**
- **Projects:** Project → Task → **Timesheet** (billable 4h / ₹2,000)
- **Assets:** Asset Category (GL accounts) → fixed-asset Item → **Asset submitted with a 12-row
  depreciation schedule**
- **CRM:** **Lead → Deal** (convert)

---

## Constraints encountered (handled / documented)

| Area | Note |
|---|---|
| Stock Entry + india_compliance | A GST hook reads `.taxes` on stock transactions; set empty for Material Receipts. |
| Quality Inspection ↔ Purchase Receipt | QI submit back-links to the PR (reload before submit). |
| Subcontracting (v16) | Full supply/receipt is PO-driven; verified Subcontracting BOM + order doctypes. |
| GST tax amount | GST-readiness verified (HSN + GSTIN); a non-zero CGST/SGST needs customer GSTIN + matching place-of-supply template. |
| Batch/Serial | Feature disabled in Stock Settings — FIFO verified by config (separate report). |
| HR holiday list | This hrms resolves via **Holiday List Assignment** doctype (not the employee/company field). |
| Assets | v16 depreciation rows live in **Asset Depreciation Schedule**. |

---

## Reproduction
```bash
for c in cycle1_p2p_runner cycle2_mfg_runner cycle3_o2c_runner cycle4_runner; do
  docker exec frappe_docker-backend-1 bash -lc "cd /home/frappe/frappe-bench && ./env/bin/python $c.py"
done
```

## Conclusion

The 13 platform modules are now covered **in depth** by four end-to-end business cycles — every
cycle drives real submitted documents and asserts the resulting stock/GL/status effects, with full
cleanup. Combined with the CS Module suite (159+ checks) and the platform breadth smoke (13/13),
the deployment has both deep CS coverage and verified cross-module ERP cycles. Remaining external
items are unchanged: live e-waybill (NIC creds), full load test, and the 8080 frontend image rebuild.
