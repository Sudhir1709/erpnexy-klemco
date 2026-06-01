# Klemco CRM — CS Module · Phase 4 Report (UI / Client-Script)

| | |
|---|---|
| **Report date** | 2026-06-01 |
| **Cycle** | Phase 4 — front-end / client-script |
| **Environment** | `http://localhost:8080` · site `mysite.localhost` |
| **Deliverables** | `UI_TEST_CHECKLIST.md` (manual) + `playwright_ui.py` (automated) |

---

## 1. Executive Summary

| Track | Result |
|---|---|
| Automated UI (Playwright, headless Chromium) | **8/8 checks passed** on the live desk |
| Manual UI checklist | Produced — 25 cases across all 5 modules for business sign-off |

**Verdict: PASS (automated render/presence) + checklist ready for interactive sign-off.**
Every v1.3 customization **renders on the real desk forms**; the interactive behaviors
(clicks, pickers, print output) are scripted in the manual checklist for a business walkthrough.

---

## 2. Automated UI checks (Playwright)

Logged into the desk and asserted the customizations render on the actual forms:

| Check | Result |
|---|---|
| Login to desk | ✅ |
| Sales Order — custom fields render (3PL, note, delivery instructions, deviation status) | ✅ |
| Sales Order — Preferred 3PL offers **"Others (not yet decided)"** | ✅ |
| KM Order — form renders (linked SO + items grid) | ✅ |
| Item — KM-managed approval field renders | ✅ |
| CS Complaint — form renders (assignee + algorithm suggestion) | ✅ |
| Delivery Challan print format exists/opens | ✅ |
| Customer Service workspace loads | ✅ |

**Setup note:** the container ships Python 3.14 (unsupported by Playwright) and no Node, so the
automation runs from **host Python 3.12** (`pip install playwright` + `playwright install chromium`)
driving Chromium against `localhost:8080`. The desk home redirects to `/desk`; forms open via
`/app/<doctype>/new`.

**Reproduction:**
```bash
python -m pip install playwright && python -m playwright install chromium
python playwright_ui.py    # → 8/8 checks passed
```

---

## 3. Manual checklist (interactive behaviors)

`UI_TEST_CHECKLIST.md` covers the behaviors automation can't reliably assert headless — to be run
by a business user with the relevant role logins:
- date-picker bounded to today; deviation **Approve/Reject** buttons (Sales Head only) + banner;
- 3PL "Others" makes the note mandatory; KM review pane SO-vs-KM qty + "Matches SO";
- per-role KM approval checkboxes; COD cheque section + submit gate;
- Delivery Challan **print output** (instructions + items); complaint routing table + auto-assignee,
  override-reason prompt, SLA colour transitions, CSAT-on-close; cross-cutting RBAC menu visibility
  and tablet responsiveness.

---

## 4. Recommendation

Automated render coverage is green. Complete the **manual checklist** walkthrough (especially the
print output and the role-gated buttons) for full UI sign-off. The Playwright script can be extended
toward interactive flows and wired into CI later if desired.
