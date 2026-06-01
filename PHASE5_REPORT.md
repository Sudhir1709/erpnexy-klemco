# Klemco CRM — CS Module · Phase 5 Report (NFR + Security)

| | |
|---|---|
| **Report date** | 2026-06-01 |
| **Cycle** | Phase 5 — Non-functional (smoke) + security |
| **Environment** | `http://localhost:8080` · site `mysite.localhost` |
| **Drivers** | `phase5_runner.py` (server-side) + HTTP latency/auth probes |

---

## 1. Executive Summary

| Metric | Result |
|---|---|
| Checks executed | **12** (8 server-side + 4 HTTP) |
| Passed | **12 (100%)** |
| Failed | **0** |

**Verdict: PASS (smoke).** All measured NFR targets are met with wide margin, and security is
enforced **server-side** (ORM permissions, business-rule gates, unauthenticated access blocked,
audit trail captured). Full load/scale testing remains a separate exercise (see §4).

---

## 2. Non-Functional (BRD §9 targets)

| Requirement | Target | Measured | Result |
|---|---|---|---|
| Sales Order list query (P95) | < 2 s | 1 ms (server) / **62 ms** (HTTP API) | ✅ |
| CS Complaint list query (P95) | < 2 s | 1 ms (server) / **20 ms** (HTTP API) | ✅ |
| KM Order list query (P95) | < 2 s | 1 ms (server) | ✅ |
| Desk page `/app/sales-order` (server response, P95) | < 2 s | **1,688 ms** | ✅ (near budget) |
| Order save & confirm (KM Order create+submit) | < 3 s | **400 ms** | ✅ |
| Notification dispatch (SO acknowledgement) | < 60 s | < 1 ms (enqueued) | ✅ |

> The desk SPA shell page is the slowest at ~1.7 s server response (within the 2 s budget but the
> closest to it); list/API/data operations are sub-100 ms. Browser-side render adds to page load and
> should be confirmed in the UI phase.

---

## 3. Security

| Check | Expected | Result |
|---|---|---|
| Unauthenticated access to a protected resource (`/api/resource/Sales Order`) | denied | ✅ **403 Forbidden** |
| RBAC enforced at the ORM (Stock User creating a KM Order) | denied | ✅ blocked server-side (`PermissionError`) — not just UI |
| Business-rule gate cannot be bypassed at submit (unapproved RC deviation) | blocked | ✅ blocked |
| Audit trail on tracked doctype (CS Complaint change) | ≥1 version | ✅ 2 versions captured |

Confirms permission checks are enforced by the framework/ORM (a malicious API call cannot bypass
the desk UI), the v1.3 approval gates hold server-side, and changes are auditable.

---

## 4. Out of Scope / Notes

- **Load & concurrency** (§9: 500+ concurrent users) — this is a **smoke** measurement of single-request
  latency, not a load test. A dedicated load test (e.g., Locust/k6 with concurrent virtual users) is
  recommended before go-live to validate the concurrency target and P95 under load.
- **Browser render time** is additive to the server response measured here; confirm full page-load in
  the UI phase (Playwright).
- **Encryption/SSO/MFA** (§9 security NFRs) are deployment/infrastructure concerns (TLS termination,
  identity provider) — out of scope for application testing.

---

## 5. Reproduction
```bash
# server-side NFR + security
docker exec frappe_docker-backend-1 bash -lc 'cd /home/frappe/frappe-bench && ./env/bin/python phase5_runner.py'
# HTTP latency + unauth check: login via /api/method/login then time /api/method/frappe.client.get_list
```

---

## 6. Recommendation

NFR and security smoke pass with margin. Before go-live: run a proper **load test** for the
concurrency target, and confirm **browser page-load** in the UI phase. Security posture is sound at
the application layer; ensure TLS/SSO/MFA at the infrastructure layer per §9.
