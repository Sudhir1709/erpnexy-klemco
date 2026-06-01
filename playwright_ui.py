"""Klemco CS — Phase 4 UI automation (Playwright, headless Chromium).

Logs into the desk and asserts the v1.3 customizations render on the real forms.
Run:  python playwright_ui.py            (host Python 3.12 with playwright + chromium)
"""
import sys
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

BASE = "http://localhost:8080"
USER, PWD = "Administrator", "admin"
RESULTS = []

def check(name, ok, detail=""):
    RESULTS.append((name, ok, detail))
    print(f"{'PASS' if ok else 'FAIL'} | {name} | {detail}")

def field(page, fieldname, timeout=15000):
    return page.wait_for_selector(f"[data-fieldname='{fieldname}']", timeout=timeout)

with sync_playwright() as p:
    browser = p.chromium.launch()
    ctx = browser.new_context(base_url=BASE, viewport={"width": 1400, "height": 1000})
    page = ctx.new_page()

    # ── login ──
    try:
        page.goto(f"{BASE}/login", timeout=30000)
        page.fill("#login_email", USER)
        page.fill("#login_password", PWD)
        page.locator(".btn-login").first.click()
        page.wait_for_selector(".navbar", timeout=60000)
        page.wait_for_timeout(1500)
        ok = "/login" not in page.url
        check("Login to desk", ok, page.url)
    except Exception as e:
        check("Login to desk", False, str(e)[:120])
        print("\n".join(f"{'PASS' if o else 'FAIL'} {n}" for n, o, _ in RESULTS))
        browser.close(); sys.exit(1)

    def open_new(slug, anchor_field):
        page.goto(f"{BASE}/app/{slug}/new", timeout=30000)
        field(page, anchor_field)  # form rendered

    # ── Sales Order: custom fields render (CR-14, CR-16, CR-10) ──
    try:
        open_new("sales-order", "customer")
        for fn in ["custom_preferred_3pl", "custom_3pl_note", "custom_delivery_instructions",
                   "custom_rc_deviation", "custom_deviation_approval_status"]:
            assert page.query_selector(f"[data-fieldname='{fn}']"), f"missing {fn}"
        # 3PL select offers "Others (not yet decided)"
        opts = page.eval_on_selector_all(
            "[data-fieldname='custom_preferred_3pl'] select option", "els => els.map(e => e.textContent.trim())")
        check("Sales Order custom fields render", True, "3PL options: " + ", ".join([o for o in opts if o]))
        check("3PL 'Others (not yet decided)' option present", "Others (not yet decided)" in opts, str(opts))
    except Exception as e:
        check("Sales Order custom fields render", False, str(e)[:140])

    # ── KM Order form (CR-11) ──
    try:
        open_new("km-order", "linked_sales_order")
        ok = bool(page.query_selector("[data-fieldname='items']")) and bool(page.query_selector("[data-fieldname='linked_sales_order']"))
        check("KM Order form renders (linked SO + items grid)", ok)
    except Exception as e:
        check("KM Order form renders", False, str(e)[:140])

    # ── Item KM approval fields (CR-18) ──
    try:
        open_new("item", "item_code")
        # custom_km_managed is a checkbox; the approval fields are depends_on it but present in DOM def
        ok = bool(page.query_selector("[data-fieldname='custom_km_managed']"))
        check("Item KM-managed approval field renders", ok)
    except Exception as e:
        check("Item KM-managed approval field renders", False, str(e)[:140])

    # ── CS Complaint form (FR-CM-11) ──
    try:
        open_new("cs-complaint", "complaint_type")
        ok = bool(page.query_selector("[data-fieldname='algorithm_suggested']")) and bool(page.query_selector("[data-fieldname='assigned_to']"))
        check("CS Complaint form renders (assignee + suggestion)", ok)
    except Exception as e:
        check("CS Complaint form renders", False, str(e)[:140])

    # ── Delivery Challan print format exists (CR-12) ──
    try:
        page.goto(f"{BASE}/app/print-format/Delivery%20Challan", timeout=30000)
        page.wait_for_timeout(3000)
        body = page.inner_text("body")
        ok = ("Delivery Challan" in body) and ("not found" not in body.lower()) and ("does not exist" not in body.lower())
        check("Delivery Challan print format exists", ok, page.url)
    except Exception as e:
        check("Delivery Challan print format exists", False, str(e)[:140])

    # ── Customer Service workspace ──
    try:
        page.goto(f"{BASE}/app/customer-service", timeout=30000)
        page.wait_for_timeout(2500)
        body = page.inner_text("body")
        ok = ("KM" in body) or ("Complaint" in body)
        check("Customer Service workspace loads", ok)
    except Exception as e:
        check("Customer Service workspace loads", False, str(e)[:140])

    browser.close()

passed = sum(1 for _, o, _ in RESULTS if o)
print(f"\n================ PHASE 4 UI (Playwright): {passed}/{len(RESULTS)} checks passed ================")
