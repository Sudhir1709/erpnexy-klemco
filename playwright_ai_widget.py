"""Browser check for the AI Help floating bubble on the ERPNext desk."""
import sys
from playwright.sync_api import sync_playwright

BASE = "http://localhost:8080"
R = []
def check(name, ok, detail=""): R.append(ok); print(f"{'PASS' if ok else 'FAIL'} | {name} | {detail}")

with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    pg = b.new_page()
    pg.goto(f"{BASE}/login", wait_until="networkidle")
    pg.fill("#login_email", "Administrator")
    pg.fill("#login_password", "admin")
    pg.locator(".btn-login").first.click()
    pg.wait_for_load_state("networkidle")
    pg.goto(f"{BASE}/app/home", wait_until="networkidle")

    btn = pg.wait_for_selector("#kai-btn", timeout=30000)
    check("Floating AI bubble renders on desk", btn is not None)

    btn.click()
    pg.wait_for_selector("#kai-panel.open", timeout=5000)
    check("Chat panel opens on click", pg.locator("#kai-panel.open").count() == 1)

    # status badge resolves to live/demo
    pg.wait_for_timeout(1500)
    status = pg.inner_text("#kai-status")
    check("Status badge resolved", "live" in status or "demo" in status, status)

    pg.fill("#kai-q", "How many customers do we have?")
    pg.click("#kai-send")
    # wait for a bot reply that is no longer the 'thinking…' placeholder
    reply = ""
    for _ in range(40):
        pg.wait_for_timeout(500)
        bots = pg.locator("#kai-log .kai-m.bot")
        if bots.count():
            t = bots.last.inner_text()
            if t and "thinking" not in t.lower():
                reply = t; break
    check("Assistant returns a reply in the bubble", bool(reply) and "thinking" not in reply.lower(), reply[:120])
    b.close()

print(f"\n==== AI WIDGET UI: {sum(R)}/{len(R)} passed ====")
sys.exit(0 if all(R) else 1)
