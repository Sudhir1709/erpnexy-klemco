# Klemco India ERPNext — Docker Setup

ERPNext v16 deployment for Klemco India Pvt. Ltd. built on [frappe_docker](https://github.com/frappe/frappe_docker).

## Quick Start

### 1. Prerequisites
- Docker Desktop installed and running
- ngrok installed (for external access)

### 2. Setup `.env`
Copy `example.env` and set your DB password:
```bash
cp example.env .env
# Edit .env and set:
# ERPNEXT_VERSION=v16.14.0
# DB_PASSWORD=your_password
# FRAPPE_SITE_NAME_HEADER=mysite.localhost
```

### 3. Get the Klemco CS image
The `klemco_cs` Customer Service app is baked into a custom image, published to GHCR.
Set these in `.env` so the stack uses it:
```
CUSTOM_IMAGE=ghcr.io/sudhir1709/erpnxt-klemco-cs
CUSTOM_TAG=v16.14.0
```
The image is pulled automatically on `up`. If the GHCR package is **private**, log in first:
```bash
echo $GITHUB_TOKEN | docker login ghcr.io -u <your-username> --password-stdin   # token needs read:packages
```
Or **build it locally** instead of pulling:
```bash
docker build -f Dockerfile.klemco --build-arg ERPNEXT_VERSION=v16.14.0 -t ghcr.io/sudhir1709/erpnxt-klemco-cs:v16.14.0 .
```

### 4. Start the Stack
```bash
docker compose -f compose.yaml -f overrides/compose.mariadb.yaml -f overrides/compose.redis.yaml -f overrides/compose.noproxy.yaml -f overrides/compose.klemco.yaml --env-file .env up -d
```
The `compose.klemco.yaml` override adjusts the backend startup to (1) self-heal the
site DB-user host grant (`klemco_db_grant.py` — resilient to container-IP churn) and
(2) run `bench migrate`, so the CS Module v1.3 customizations (Custom Fields, KM Order
doctype, Delivery Challan print format, roles) are (re)applied automatically. The app
itself ships in the image. See [CS Module](#cs-module-customer-service) below.

> If you ever recreate **only** the backend, restart the frontend so nginx re-resolves
> the backend container IP:
> `docker restart erpnxt_klemco-frontend-1 erpnxt_klemco-websocket-1`

### 5. Create Site
```bash
docker exec frappe_docker-backend-1 bench new-site mysite.localhost \
  --mariadb-root-password your_password \
  --admin-password admin \
  --install-app erpnext
docker exec frappe_docker-backend-1 bench use mysite.localhost
```

### 6. Seed Klemco Demo Data
```bash
docker cp klemco_seed2.py frappe_docker-backend-1:/home/frappe/frappe-bench/
docker exec frappe_docker-backend-1 bash -c \
  "mkdir -p /home/frappe/frappe-bench/mysite.localhost/logs && \
   cd /home/frappe/frappe-bench && source env/bin/activate && \
   python klemco_seed2.py"
```

### 7. Create Department Users
```bash
docker cp klemco_users.py frappe_docker-backend-1:/home/frappe/frappe-bench/
docker exec frappe_docker-backend-1 bash -c \
  "cd /home/frappe/frappe-bench && source env/bin/activate && python klemco_users.py"
```

### 8. Apply Workspace Role Restrictions
```bash
docker cp klemco_workspace_roles.py frappe_docker-backend-1:/home/frappe/frappe-bench/
docker exec frappe_docker-backend-1 bash -c \
  "cd /home/frappe/frappe-bench && source env/bin/activate && python klemco_workspace_roles.py"
```

### 9. Add Department User Guides
```bash
docker cp klemco_user_guides.py frappe_docker-backend-1:/home/frappe/frappe-bench/
docker exec frappe_docker-backend-1 bash -c \
  "cd /home/frappe/frappe-bench && source env/bin/activate && python klemco_user_guides.py"
```

### 10. Clear Cache
```bash
docker exec frappe_docker-backend-1 bench --site mysite.localhost clear-cache
docker exec frappe_docker-redis-cache-1 redis-cli FLUSHALL
```

---

## Access
- **Local:** http://localhost:8081
- **Admin login:** `Administrator` / `admin`

## Department Credentials
All department users use password: `Klemco@2024`

| Department | Email |
|---|---|
| Sales | sales.head@klemcoindia.com |
| CRM | crm.head@klemcoindia.com |
| Purchase | purchase.head@klemcoindia.com |
| Accounts | accounts.head@klemcoindia.com |
| Inventory | inventory.head@klemcoindia.com |
| HR | hr.head@klemcoindia.com |
| Projects | projects.head@klemcoindia.com |
| Manufacturing | manufacturing.head@klemcoindia.com |
| Quality | quality.head@klemcoindia.com |
| Marketing | marketing.head@klemcoindia.com |

## Demo Data Loaded
- **55 Items** — Strut Channels, Pipe Hangers, Anchors, Fire Stop, Wire Rope, Vibration Controls, Seismic, Services
- **24 Customers** — L&T, Tata Projects, Blue Star, Voltas, Apollo Hospitals, DMRC, Godrej, DLF, etc.
- **10 Suppliers** — Tata Steel, JSW, Henkel, Hilti, Fischer, Blue Dart, etc.
- **16 Territories** — India → State → City hierarchy
- **Sample Transactions** — Quotations, Sales Orders, Purchase Orders

## CS Module (Customer Service)

The custom `klemco_cs` app (`crm2/klemco_cs`) implements the CRM Customer Service module.
It is baked into the custom image (`Dockerfile.klemco`, step 3); `overrides/compose.klemco.yaml`
runs the DB self-heal grant + `bench migrate` on backend startup (step 4) so customizations
stay applied across restarts and recreations.

**v1.3 — wireframe/BRD review feedback (CR-09…CR-18):**

| Area | Feature |
|---|---|
| Sales Order | Required Delivery Date cannot be back-dated (future/OOS allowed) — FR-SO-16 |
| Sales Order | Discount editable for RC customers; flagged "Conditional Deviation" → Sales Head approval — FR-SO-06 |
| Sales Order | Preferred 3PL "Others (not yet decided)" + required note — FR-SO-04 |
| Sales Order | Simplified order-saved acknowledgement email (no delivery date) — FR-SO-09 |
| KM Manufacturing | `KM Order` doctype + guided "Create KM Order from SO" review — FR-KM-08 |
| KM Manufacturing | New KM items need triple approval: CS Supervisor + KM Plant Head + Supply Chain Lead — BR-KM-02 |
| Dispatch | COD cheque capture on the invoice, mandatory before submit — FR-DP-11 / BR-DP-06 |
| Dispatch | Warehouse can download SO test certificates from the Delivery Note — FR-DP-12 |
| Dispatch | Delivery instructions carried from SO onto the Delivery Challan — CR-16 |
| Docs | Delivery Form / Note / Challan consolidated into one "Delivery Challan" print format — CR-12 |

Roles auto-created on install/migrate: `CS Executive`, `CS Manager`, `CS Supervisor`,
`Sales Head`, `KM Plant Head`, `Supply Chain Lead`.

> For local app development you can instead bind-mount `./crm2/klemco_cs` over
> `apps/klemco_cs` and `pip install -e` it, skipping an image rebuild on each change.

## ngrok (External Access)
```bash
ngrok config add-authtoken YOUR_TOKEN
ngrok http 8081
```
To run permanently, register as Windows scheduled task:
```powershell
$action = New-ScheduledTaskAction -Execute "ngrok" -Argument "start --all"
$trigger = New-ScheduledTaskTrigger -AtLogOn
Register-ScheduledTask -TaskName "Klemco ERPNext ngrok" -Action $action -Trigger $trigger -Force
```
