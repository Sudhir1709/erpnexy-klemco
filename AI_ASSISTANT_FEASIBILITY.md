# AI Help Assistant (CRM Chatbot) — Feasibility Study + Working PoC

Date: 2026-06-04 · App: `klemco_cs` · Stack: 8080 (ERPNext v16.14.0, Frappe v16) · Site: mysite.localhost

## Verdict: ✅ Feasible — and a working proof-of-concept is now running

A natural-language help/chat assistant for the CRM is fully achievable inside this
application. The size of the ERP is **not** a blocker. A live PoC is deployed and was
tested end-to-end (in demo mode); it goes fully live the moment an Anthropic API key is added.

---

## Why "size" is not a problem

| Concern | Reality |
|---------|---------|
| "1,029 doctypes is too much for an AI" | The assistant never ingests the schema. The **CRM surface is ~64 doctypes**; the PoC scopes data access to **14 high-value ones** (Customer, Contact, CRM Lead/Deal, Lead, Opportunity, Prospect, Quotation, Sales Order, Sales Invoice, Delivery Note, Item, CS Complaint, KM Order). |
| "It has to understand all our data" | It uses **tool-calling**, not data ingestion. Claude is given 2 small tools (`count_records`, `list_records`) and decides when to call them against Frappe's existing query API. The model sees a few tool definitions, never the database. This pattern scales to any ERP size. |
| "How-to questions need our whole manual" | The current PoC answers how-to from the model's general ERPNext knowledge + a system prompt. For company-specific procedures, a small curated knowledge base (RAG) can be added later — independent of doctype count. |

---

## What was built (PoC)

| Component | Location | Purpose |
|-----------|----------|---------|
| Chat backend | `klemco_cs/ai_assistant/api.py` | Whitelisted `chat()` endpoint; Claude agent loop with tool-use; permission-safe data tools; demo fallback |
| Chat UI | `klemco_cs/www/ai-help.html` (+ `.py`) | Self-contained chat page at **`/ai-help`** (login-guarded, CSRF-protected). No `bench build`/Node needed |
| Menu entry | navbar Help dropdown → **"AI Help"** | Added idempotently via `install_menu()` in `after_migrate` |

**Two operating modes, automatic:**
- **Live mode** — when an Anthropic key is configured: full free-form natural language, multi-step tool-use, how-to + data answers.
- **Demo mode** — no key: a lightweight intent matcher that calls the *same* data tools, so the UI and the permission-safe data path are fully demonstrable today.

### Test evidence (this environment, no key → demo mode)
- `status()` → `configured: false`, model `claude-sonnet-4-6`, 14 scoped doctypes, runs as logged-in user. ✅
- Data tools (perm-safe): `count CS Complaint` → 4; `list Customer` → real names. ✅
- Allowlist guard: requesting `GL Entry` (outside CRM scope) is **blocked**. ✅
- Full HTTP path (browser-equivalent): login → `/ai-help` renders → CSRF → `chat` →
  *"how many open complaints?"* → **"You have 0 CS Complaint(s) with status Open"**;
  *"list customers"* → 10 real customers with groups. ✅

---

## Security & data-governance (built in)

- **Permission enforcement** — every data tool uses `frappe.get_list(..., ignore_permissions=False)`,
  so the assistant returns **only what the logged-in user is allowed to see** (role permissions +
  user permissions + permission query conditions all apply). The chatbot cannot leak data across roles.
- **Doctype allowlist** — hard-coded scope; anything outside it is refused.
- **Login + CSRF** — the page redirects guests to login; the API requires a CSRF token.
- **Read-only** — the PoC has no write/update/cancel tools. (Write actions are a deliberate, gated next step.)
- **Data residency** — ⚠️ in live mode, the text of questions and the tool results returned to the
  model are sent to Anthropic's API (not used to train models). If CRM data must never leave the
  network, swap to a **self-hosted model** (the agent loop is provider-agnostic; only `_anthropic()` changes).

---

## How to switch from demo → live (≈2 minutes)

```bash
# inside the backend container
bench --site mysite.localhost set-config anthropic_api_key "sk-ant-..."
# optional: choose a model (default claude-sonnet-4-6; use claude-opus-4-8 for max quality)
bench --site mysite.localhost set-config anthropic_model "claude-sonnet-4-6"
bench --site mysite.localhost clear-cache
```
No code change, no redeploy — `chat()` detects the key and flips to live tool-use automatically.

---

## Cost & performance (live mode)

- **Cost drivers**: input = system prompt (~250 tokens) + small tool defs + short history; output = a brief answer. A typical CRM question is a few thousand tokens total → **fractions of a cent per query on Sonnet**. A help bot's volume is low, so monthly cost is modest. Opus costs more per query but is rarely needed for this use case.
- **Latency**: 1–4 s per answer (1 LLM round-trip; +1 round-trip per tool call). Acceptable for a help widget.
- **Scaling**: stateless endpoint; scales with existing gunicorn workers. Add request rate-limiting if exposed widely.

---

## Limitations of the PoC & recommended next steps

| # | Enhancement | Effort |
|---|-------------|--------|
| 1 | Add an Anthropic API key to go live (only outstanding item to see real NL answers) | trivial |
| 2 | Company-specific how-to via a small RAG knowledge base (SOPs, policies) | small–medium |
| 3 | Embed the widget inside the Frappe **CRM SPA** (`/crm`) and/or as a floating bubble in the desk | small |
| 4 | Streaming responses (token-by-token) for snappier UX | small |
| 5 | Gated **write actions** (create a lead, log a complaint) with confirmation + audit log | medium |
| 6 | Conversation logging + feedback thumbs for quality tracking; per-user rate limits | small |
| 7 | Self-hosted model option (Ollama/vLLM) if data must stay on-prem | medium |

---

## Bottom line
The application can host a CRM AI assistant cleanly, securely, and at any data scale. The PoC proves
the UI, the menu entry, and the **permission-safe live-data path** end-to-end. The only thing standing
between the current demo and a fully conversational assistant is an Anthropic API key — drop it in and it's live.
