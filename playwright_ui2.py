"""Phase 4 — interactive UI flows (Playwright). Verifies client-script behaviors and
record-backed UI via cur_frm state, DOM, and the print view. Reads ui_fixtures.json."""
import json, sys
from playwright.sync_api import sync_playwright

BASE = "http://localhost:8080"
fx = json.load(open("ui_fixtures.json"))
RESULTS = []
def check(name, ok, detail=""):
    RESULTS.append((name, ok, detail)); print(f"{'PASS' if ok else 'FAIL'} | {name} | {detail}")

with sync_playwright() as p:
    browser = p.chromium.launch()
    ctx = browser.new_context(base_url=BASE, viewport={"width": 1400, "height": 1000})
    page = ctx.new_page()
    page.set_default_timeout(40000)

    # login
    page.goto(f"{BASE}/login"); page.fill("#login_email", "Administrator"); page.fill("#login_password", "admin")
    page.locator(".btn-login").first.click(); page.wait_for_selector(".navbar", timeout=60000); page.wait_for_timeout(1500)
    check("Login", "/login" not in page.url, page.url)

    def open_form(slug, name, dt):
        page.goto(f"{BASE}/app/{slug}/{name}")
        page.wait_for_function("dt => window.cur_frm && cur_frm.doctype===dt && cur_frm.doc", arg=dt, timeout=40000)
        page.wait_for_timeout(1200)

    # 1) Deviation SO — Approve/Reject buttons + banner (CR-10)
    try:
        open_form("sales-order", fx["dev_so"], "Sales Order")
        btns = page.evaluate("Object.keys(cur_frm.custom_buttons || {})")
        flag = page.evaluate("cur_frm.doc.custom_rc_deviation")
        body = page.inner_text("body")
        ok = ("Approve Deviation" in btns) and ("Reject Deviation" in btns) and ("Conditional Deviation" in body)
        check("Deviation SO: Approve/Reject buttons + banner", ok, f"buttons={btns}; rc_deviation={flag}")
    except Exception as e:
        check("Deviation SO: Approve/Reject buttons + banner", False, str(e)[:140])

    # 2) KM Order — review grid (SO Qty / KM Qty / Matches SO) (CR-11)
    try:
        open_form("km-order", fx["km"], "KM Order")
        grid_text = page.inner_text("[data-fieldname='items']")
        nrows = page.evaluate("(cur_frm.doc.items || []).length")
        ok = ("KM Qty" in grid_text) and ("Matches SO" in grid_text) and ("SO Qty" in grid_text) and nrows >= 1
        check("KM Order: SO-vs-KM review grid", ok, f"rows={nrows}")
    except Exception as e:
        check("KM Order: SO-vs-KM review grid", False, str(e)[:140])

    # 3) Delivery Challan print output (CR-12 + CR-16)
    try:
        page.goto(f"{BASE}/printview?doctype=Delivery%20Note&name={fx['dn']}&format=Delivery%20Challan&trigger_print=0&_lang=en")
        page.wait_for_timeout(3500)
        body = page.inner_text("body")
        ok = ("Delivery Challan" in body) and ("Unload by forklift" in body) and ("SKU007" in body)
        check("Delivery Challan print: heading + instructions + items", ok)
    except Exception as e:
        check("Delivery Challan print output", False, str(e)[:140])

    # 4) 3PL "Others" makes the note mandatory (CR-14, client script) — set via cur_frm to fire the trigger
    try:
        open_form("sales-order", "new", "Sales Order")
        reqd = page.evaluate("""async () => {
            await cur_frm.set_value('custom_preferred_3pl', 'Others (not yet decided)');
            return cur_frm.fields_dict.custom_3pl_note.df.reqd; }""")
        check("3PL 'Others' makes Specify/Note mandatory", bool(reqd), f"note.reqd={reqd}")
    except Exception as e:
        check("3PL 'Others' makes Specify/Note mandatory", False, str(e)[:140])

    # 5) Complaint auto-assignee + routing table (FR-CM-11, client script)
    try:
        open_form("cs-complaint", "new", "CS Complaint")
        picked = page.evaluate("""async () => {
            const opts = (cur_frm.fields_dict.complaint_type.df.options || '').split('\\n');
            const t = opts.find(o => /Product.*Quality/.test(o));
            await cur_frm.set_value('complaint_type', t);
            return t; }""")
        page.wait_for_timeout(1200)
        suggested = page.evaluate("cur_frm.doc.algorithm_suggested")
        body = page.inner_text("body")
        ok = (suggested == "QC Head") and ("Routing Logic" in body)
        check("Complaint: auto-assignee by category + routing table", ok, f"type='{picked}' suggested={suggested}")
    except Exception as e:
        check("Complaint: auto-assignee + routing table", False, str(e)[:140])

    # 6) Tablet responsiveness (NFR §9) — list renders at tablet width
    try:
        page.set_viewport_size({"width": 820, "height": 1180})
        page.goto(f"{BASE}/app/sales-order")
        page.wait_for_selector(".list-row, .frappe-list, .no-result", timeout=40000)
        check("Tablet viewport: Sales Order list renders", True, "820x1180")
    except Exception as e:
        check("Tablet viewport: Sales Order list renders", False, str(e)[:140])

    browser.close()

passed = sum(1 for _, o, _ in RESULTS if o)
print(f"\n================ PHASE 4 INTERACTIVE UI: {passed}/{len(RESULTS)} passed ================")
