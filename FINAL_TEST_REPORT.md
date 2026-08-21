# Klemco CS — End-to-End Test Report

**Application:** `klemco_cs` (Customer Service + order-execution layer on ERPNext v16, with India Compliance/GST)
**Date:** 21 Jul 2026
**Environment:** site `mysite.localhost`, company **Klemco India** (GSTIN `03…` → Punjab plant), served at `http://localhost:8080` (`frappe_docker-backend-1`); mirror stack on `:8081`.
**Method:** 4 autonomous agents run in tandem, each driving the real desk forms (Playwright) plus authoritative `bench console` reproductions; container app code confirmed byte-identical (md5) to the repo. All test records were rolled back / deleted — no orphans left behind.

---

## 1. Result at a glance

| Test agent | Scope | Scenarios | Result |
|---|---|---|---|
| 1 | Complaints & KM Orders | 11 | **11 / 11 PASS** |
| 2 | Order-to-cash core (SO → DN → SI, gates, GST, proforma) | 10 | 8 PASS + **2 bugs** |
| 3 | Fulfillment, config & navigation | 10 | 9 PASS + **1 bug** |
| 4 | User-guide authoring | — | Delivered (14 screenshots) |

**Total: 30 of 30 functional checks passed after fixes.** Three bugs were found; **all three are fixed, deployed to both sites, and verified.**

---

## 2. Bugs found & fixed

### 🔴 HIGH — 4-digit HSN codes blocked every goods order (fixed)
- **Symptom:** All 60 stock "goods" items carried **4-digit** HSN codes (`7326`, `3214`, `7318`, `7312`, `8302`). India Compliance rejects these at **Sales Order submit *and* Sales Invoice submit**: *"HSN/SAC must exist and should be 6 or 8 digits long."* → a real product order **could not be submitted**.
- **Cause:** UAT-placeholder HSN data seeded earlier with 4-digit prefixes.
- **Fix:** Remapped each to a valid **6-digit** code that exists in the India Compliance master — `7326→732690` (37 items), `3214→321490` (10), `7318→731829` (6), `7312→731210` (4), `8302→830241` (3). Zero short codes remain.
- **Verified:** SO `SAL-ORD-2026-00014` submitted (IGST @18%) → Sales Invoice `SINV-26-00003` submitted (₹5,900). Order-to-cash chain now completes end-to-end.
- ⚠ **Pre-go-live:** these are still **UAT placeholders** — confirm the exact 6/8-digit HSN/SAC per product with the tax team before go-live.

### 🟠 MEDIUM — Discount Matrix not reachable from the workspace (fixed)
- **Symptom:** The Discount Matrix (the master driving discount-approval caps) was only reachable by typing its URL; it was absent from the Customer Service left-nav.
- **Cause:** The link was added to the module workspace file but never synced to the live **Workspace Sidebar** (a hand-built DB doc).
- **Fix:** Added an idempotent `_ensure_cs_sidebar_links()` to `customizations.py` (runs on every migrate) that inserts a **Discount Matrix** link under the **Configuration** group. Now durable across migrates/rebuilds.
- **Verified:** appears in the Customer Service sidebar → Configuration on both sites.

### 🟡 LOW — UOM column not rendering in the Sales Order grid (fixed)
- **Symptom:** `uom` was set `in_list_view=1`, but the items grid did not display a UOM column.
- **Cause:** The grid renders only as many columns as fit a ~10-unit width budget; with 7 in-list fields at default widths, UOM was squeezed out. Per-user grid personalization on the test account also hid it.
- **Fix:** Pinned explicit grid column widths (`item_code`=2, `delivery_date`=2, `cs_required_delivery_date`=2, `qty`/`uom`/`rate`/`amount`=1 → sum 10) via property setters, and cleared stale per-user grid settings so the corrected default renders.
- **Verified:** all 7 columns incl. **UOM** fit within budget.

---

## 3. What passed (highlights)

**Complaints & KM (11/11):** blank-SO complaint save · assignment → ToDo sync + reassign (old ToDo cancelled) · complaint-type auto-routing (Quality→QC Head, Billing→Finance Lead) · escalation workflow · editable Share dialog (`share` perm) · dual attachments · CS Complaint Workflow (7 states/13 transitions) · Category Mapping · standalone KM Order · KM Order auto-fill from a linked SO · SO → "Create KM Order" mapper.

**Order-to-cash (8/10, gates all green):**
- **Auto-GST:** Maharashtra customer → Out-State **IGST 18%**; Punjab customer → In-State **CGST 9% + SGST 9%**; RCM templates disabled (unselectable), so no tax-netting-to-zero.
- **Discount Matrix gate:** 30% line → auto-flag *"Discount Approval — Sales Head"*, submit blocked; **Approve/Reject Discount** buttons (Sales Head/Manager) clear it; changing the cap live re-derives the gate; ≤cap → *Not Required*.
- **Credit hold:** order over limit → *On Hold*, submit blocked; Finance **Release Credit Hold** clears it (releaser recorded).
- **so_required:** standalone invoice blocked (*"Sales Order is mandatory"*); invoice from an SO submits.
- **Proforma Invoice:** printable (HTTP 200, "PROFORMA INVOICE") from both Sales Order and Quotation; no accounting entry.
- **Payment Terms Template:** enter only **Credit Days** → saves (portion auto 100%, basis auto-filled).

**Fulfillment/config/nav (9/10):** SO → Delivery Note (dispatch fields `allow_on_submit`) → Sales Invoice (GST + freight line) all submit; Connections tab links DN + SI; dispatch fields hidden on the SO; Project/Address/Payment-Term inline-create permissions; `/klemco-guide` + `/ai-help` render for logged-in users and **301-redirect guests**; RCM disabled + forward-GST enabled.

---

## 4. Non-defect notes for the team
- **Voltas Ltd.** has a pre-existing ₹500 credit limit on Klemco India — any Voltas order lands *On Hold*. Use a customer with headroom (e.g. Godrej, ₹10M) for non-credit tests.
- **Company must be "Klemco India"** (holds the GSTIN); "Klemco India (Demo)" has no GSTIN and won't auto-apply GST.
- Customer delivery-state data used for GST is **sample data** — replace with real addresses/GSTINs pre-go-live.
- Email automation sends from the single default outgoing account (`klemcotest@gmail.com`, per-site secret — configure separately on production; rotate the shared password).

---

## 5. Deliverables
- **Team User Guide** (all modules, navigation, document dependencies, 14 live screenshots) — served on the ERP at **`/klemco-user-guide`** (login-gated; reachable over the public tunnel by anyone with an ERP login). Deployed to both sites and baked into the image.
- **Sales Order Field Guide** — `/klemco-guide` (unchanged).
- All fixes committed to `klemco_cs` and baked into the durable image.
