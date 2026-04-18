---
description: Sync local changes to production server (143.244.140.124)
---

# Sync to Production Server

Server: `praneeth@143.244.140.124` | Path: `/var/www/PV_enterprise_2/`

Run all commands from the repo root: `/Users/praneeth/Documents/PVenterprisedev/PV-enterprise-2`

---

## 1. Frontend — build + sync + reload nginx

```bash
cd frontend && npm run build && cd .. && rsync -avz --progress --delete frontend/dist/ praneeth@143.244.140.124:/var/www/PV_enterprise_2/frontend/dist/ && ssh praneeth@143.244.140.124 "sudo nginx -s reload"
```

---

## 2. Backend — sync all app files + restart service

```bash
rsync -avz --progress --exclude '__pycache__' --exclude '*.pyc' backend/app/ praneeth@143.244.140.124:/var/www/PV_enterprise_2/backend/app/ && ssh praneeth@143.244.140.124 "sudo systemctl restart pv-backend"
```

### 2b. Sync a single file only (replace path as needed)

```bash
rsync -avz --progress backend/app/api/v1/endpoints/dashboard.py praneeth@143.244.140.124:/var/www/PV_enterprise_2/backend/app/api/v1/endpoints/ && ssh praneeth@143.244.140.124 "sudo systemctl restart pv-backend"
```

---

## 3. Database migration — sync file + run upgrade (replace MIGRATION_FILENAME)

```bash
rsync -avz --progress backend/alembic/versions/MIGRATION_FILENAME.py praneeth@143.244.140.124:/var/www/PV_enterprise_2/backend/alembic/versions/ && ssh praneeth@143.244.140.124 "cd /var/www/PV_enterprise_2/backend && python3 -m alembic upgrade head"
```

---

## 4. Full sync — frontend + backend + migration (replace MIGRATION_FILENAME)

```bash
cd frontend && npm run build && cd .. && rsync -avz --progress --delete frontend/dist/ praneeth@143.244.140.124:/var/www/PV_enterprise_2/frontend/dist/ && rsync -avz --progress --exclude '__pycache__' --exclude '*.pyc' backend/app/ praneeth@143.244.140.124:/var/www/PV_enterprise_2/backend/app/ && rsync -avz --progress backend/alembic/versions/MIGRATION_FILENAME.py praneeth@143.244.140.124:/var/www/PV_enterprise_2/backend/alembic/versions/ && ssh praneeth@143.244.140.124 "sudo nginx -s reload && sudo systemctl restart pv-backend && cd /var/www/PV_enterprise_2/backend && python3 -m alembic upgrade head"
```

---

## 5. Check service status

```bash
ssh praneeth@143.244.140.124 "sudo systemctl status pv-backend && sudo systemctl status nginx"
```

---

## Quick Reference

| Scenario | Command |
|---|---|
| Frontend only | Step 1 |
| Backend only (no migration) | Step 2 |
| Backend + migration | Step 2 → Step 3 |
| Frontend + backend | Step 1 → Step 2 |
| Everything | Step 4 |
