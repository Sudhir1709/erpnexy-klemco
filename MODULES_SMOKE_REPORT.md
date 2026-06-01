# Klemco ERP — Platform Module Smoke Test

| | |
|---|---|
| **Report date** | 2026-06-01 |
| **Environment** | `http://localhost:8080` · site `mysite.localhost` |
| **Driver** | `modules_smoke_runner.py` |
| **Scope** | Breadth smoke across the ERPNext + ancillary app suite (not deep functional) |

---

## 1. Summary — 13 / 13 PASS

Each module was exercised by creating **one representative document** (master or draft, so it runs
its validations) on the live site, then cleaning it up. This confirms each module is installed,
configured, and accepts valid input. (Deep functional behavior of the CS Module is covered by the
phase reports; this is a platform-breadth smoke.)

| # | Module | Representative check | Result |
|---|---|---|---|
| 1 | **Frappe CRM** | CRM Lead + CRM Deal (Lead→Deal) | ✅ |
| 2 | **GST India** (india_compliance) | e-waybill enabled; HSN master (18,687); company GSTIN set | ✅ |
| 3 | **Organization** (HR) | Designation + Department | ✅ |
| 4 | **Accounting** | Journal Entry (balanced) draft | ✅ |
| 5 | **Assets** | Asset Category (with GL accounts) + Asset doctype | ✅ |
| 6 | **Buying** | Supplier + Purchase Order draft | ✅ |
| 7 | **Manufacturing** | BOM draft (FG + raw material) | ✅ |
| 8 | **Projects** | Project + Task | ✅ |
| 9 | **Quality** | Quality Goal | ✅ |
| 10 | **Selling** | Quotation draft | ✅ |
| 11 | **Stock** | Material Request draft | ✅ |
| 12 | **Subcontracting** | Subcontracting Order / Receipt / BOM doctypes present | ✅ |
| 13 | **Frappe HR** (hrms) | Employee | ✅ |

All created records were deleted; post-run check confirmed **0 residue**.

---

## 2. Notes & Limits

- This is a **breadth smoke** — it verifies each module installs, validates input, and creates its
  core documents. It is **not** a deep functional/UAT test of each ERP module's workflows.
- **Assets:** full Asset Category requires company GL accounts (fixed-asset, accumulated-
  depreciation, depreciation-expense); these were resolved from the demo CoA.
- **Subcontracting:** verified at doctype level (a full subcontracting flow needs supplier +
  service items + subcontracting BOM — out of smoke scope).
- **GST India e-waybill:** configuration verified; live generation needs NIC/GSP credentials.
- Documents were created as **drafts/masters** to avoid submit-time GST/stock/GL coupling; the
  full submit chain for the CS flow is proven separately (E2E, Phase 2).

---

## 3. Reproduction
```bash
docker exec frappe_docker-backend-1 \
  bash -lc 'cd /home/frappe/frappe-bench && ./env/bin/python modules_smoke_runner.py'
# → 13/13 passed
```

---

## 4. Conclusion

Every requested platform module (Frappe CRM, GST India, Organization, Accounting, Assets, Buying,
Manufacturing, Projects, Quality, Selling, Stock, Subcontracting, Frappe HR) is **installed and
functional at the smoke level** on the 8080 stack. For any specific module that needs deep
functional/UAT coverage, a targeted scenario suite can be added (as was done for the CS Module).
