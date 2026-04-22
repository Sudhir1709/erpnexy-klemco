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

### 3. Start the Stack
```bash
docker compose -f compose.yaml -f overrides/compose.mariadb.yaml -f overrides/compose.redis.yaml -f overrides/compose.noproxy.yaml --env-file .env up -d
```

### 4. Create Site
```bash
docker exec frappe_docker-backend-1 bench new-site mysite.localhost \
  --mariadb-root-password your_password \
  --admin-password admin \
  --install-app erpnext
docker exec frappe_docker-backend-1 bench use mysite.localhost
```

### 5. Seed Klemco Demo Data
```bash
docker cp klemco_seed2.py frappe_docker-backend-1:/home/frappe/frappe-bench/
docker exec frappe_docker-backend-1 bash -c \
  "mkdir -p /home/frappe/frappe-bench/mysite.localhost/logs && \
   cd /home/frappe/frappe-bench && source env/bin/activate && \
   python klemco_seed2.py"
```

### 6. Create Department Users
```bash
docker cp klemco_users.py frappe_docker-backend-1:/home/frappe/frappe-bench/
docker exec frappe_docker-backend-1 bash -c \
  "cd /home/frappe/frappe-bench && source env/bin/activate && python klemco_users.py"
```

### 7. Apply Workspace Role Restrictions
```bash
docker cp klemco_workspace_roles.py frappe_docker-backend-1:/home/frappe/frappe-bench/
docker exec frappe_docker-backend-1 bash -c \
  "cd /home/frappe/frappe-bench && source env/bin/activate && python klemco_workspace_roles.py"
```

### 8. Add Department User Guides
```bash
docker cp klemco_user_guides.py frappe_docker-backend-1:/home/frappe/frappe-bench/
docker exec frappe_docker-backend-1 bash -c \
  "cd /home/frappe/frappe-bench && source env/bin/activate && python klemco_user_guides.py"
```

### 9. Clear Cache
```bash
docker exec frappe_docker-backend-1 bench --site mysite.localhost clear-cache
docker exec frappe_docker-redis-cache-1 redis-cli FLUSHALL
```

---

## Access
- **Local:** http://localhost:8080
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

## ngrok (External Access)
```bash
ngrok config add-authtoken YOUR_TOKEN
ngrok http 8080
```
To run permanently, register as Windows scheduled task:
```powershell
$action = New-ScheduledTaskAction -Execute "ngrok" -Argument "start --all"
$trigger = New-ScheduledTaskTrigger -AtLogOn
Register-ScheduledTask -TaskName "Klemco ERPNext ngrok" -Action $action -Trigger $trigger -Force
```
