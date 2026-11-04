# Nexora ISP — Deployment Guide

This guide is for whoever deploys Nexora to production. It reflects the code as of
commit `cf0a224` (HR attendance API, network node management, MikroTik provisioning).

## 1. What gets deployed

| Part | Folder | Stack | Notes |
|---|---|---|---|
| Backend API | `backend/` | Django 6 + DRF, served by Gunicorn | `railpack.json` / `start.sh` run migrations, then Gunicorn |
| Frontend | `nexora-isp/` | Next.js 16 | Deployed as a **separate** service; it is not started by `railpack.json` |
| Database | — | PostgreSQL | Required. SQLite is not supported |
| Redis | — | Optional | Only for the cache and a real Celery worker (see §6) |

Runtime versions:

- **Python 3.11–3.13.** Python 3.14 fails to install `psycopg-binary==3.2.9`. Pin the version on the host
  (for Railway/Railpack add a `.python-version` file containing `3.13` at the repo root).
- **Node.js 20+** for the frontend.

## 2. Backend environment variables

`backend/.env.production.example` lists every value with placeholders. Never commit real values;
put them in the host's secret store (Railway → service → Variables).

| Variable | Required | Purpose |
|---|---|---|
| `DJANGO_SECRET_KEY` | **Yes** | Django signing key. The app refuses to start without it |
| `DJANGO_DEBUG` | Yes | `False` in production |
| `DATABASE_URL` | Yes* | PostgreSQL URL. *Or* set `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT` |
| `ALLOWED_HOSTS` | Yes | Backend domain(s), comma-separated |
| `CORS_ALLOWED_ORIGINS` | Yes | Frontend origin(s), e.g. `https://app.example.com` |
| `CSRF_TRUSTED_ORIGINS` | Yes | Same as the frontend origin(s) |
| `NETWORK_CREDENTIALS_KEY` | **Yes** | Encrypts router API logins and PPPoE passwords. Generate once (command below) and **never change or lose it**, otherwise stored router credentials become unreadable |
| `SECURE_SSL_REDIRECT`, `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE`, `SECURE_HSTS_*` | Recommended | HTTPS hardening; see the example file |
| `EMAIL_*`, `DEFAULT_FROM_EMAIL` | Recommended | ISP activation emails and notifications |
| `WHATSAPP_*` | Optional | Meta WhatsApp Cloud API messaging |
| `GEMINI_API_KEY` | Optional | Command Center AI Copilot; disabled without it |
| `MIKROTIK_API_TIMEOUT_SECONDS` | Optional | Router API timeout, default `10` |
| `REDIS_URL` | Optional | Shared cache; falls back to in-memory cache |
| `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND`, `CELERY_TASK_ALWAYS_EAGER` | Optional | See §6 |

Generate the keys:

```bash
python -c "import secrets; print(secrets.token_urlsafe(64))"                               # DJANGO_SECRET_KEY
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"  # NETWORK_CREDENTIALS_KEY
```

## 3. Deploy the backend

### On Railway (current setup)

1. Create a PostgreSQL service and copy its `DATABASE_URL` into the backend service variables.
2. Set the variables from §2.
3. Attach a **volume** mounted at the backend's `media/` directory (with Railpack typically
   `/app/backend/media`; confirm the path in the container). ISP payment receipts are uploaded there;
   without a volume they are lost on every redeploy.
4. Deploy. `railpack.json` runs `python manage.py migrate --noinput` and then Gunicorn on `$PORT`.

### On any other host / VPS

```bash
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate --noinput
gunicorn config.wsgi:application --bind 0.0.0.0:8000
```

Put Nginx (or similar) in front for HTTPS. `docs/reports/NEXORA_STAGING_DEPLOYMENT_RUNBOOK.md`
has a longer Ubuntu walkthrough; treat it as background, this guide takes precedence.

**Back up the database before every deploy.** Migrations run automatically on start.

## 4. Deploy the frontend

The API URL is compiled into the bundle, so set it **before** building:

```bash
cd nexora-isp
npm ci
NEXT_PUBLIC_API_BASE_URL=https://api.example.com/api/v1 npm run build
npm start            # serves on port 3000
```

On Railway or Vercel, create a separate service with root directory `nexora-isp`, set
`NEXT_PUBLIC_API_BASE_URL`, and use `npm run build` / `npm start`. Add the frontend's URL to the
backend's `CORS_ALLOWED_ORIGINS` and `CSRF_TRUSTED_ORIGINS`.

## 5. First-time setup after the first deploy

1. Create the platform super administrator (approves ISP sign-ups):
   ```bash
   cd backend && python manage.py createsuperuser
   ```
   On Railway, run it inside the backend service's shell or through the Railway CLI with the
   production variables loaded.
2. Sign in at `https://<frontend>/superadmin/login` and set the payment instructions (bank details,
   fee) that new ISPs see during sign-up.
3. Register a test ISP at `/signup`, upload a receipt, approve it from the super admin panel, then log
   in at `/` with the organization code.

## 6. Scheduled jobs (important)

Celery runs in **eager mode** by default (`CELERY_TASK_ALWAYS_EAGER=True`): tasks run inline and the
Celery beat schedule in `config/settings.py` does **not** run. That means:

- **Network provisioning** runs immediately after each activation/suspension/restore/package change.
  This works without any extra setup.
- **Daily billing automation does not run on its own.** Schedule this once per day (e.g. 01:00 PKT)
  with a Railway cron service, a host cron job, or similar:
  ```bash
  cd backend && python manage.py run_billing_automation
  ```
  It generates invoices whose billing day is today, runs collections (reminders, final warnings,
  suspension requests) and processes the communication queue.

To use real background workers instead, provision Redis, set `CELERY_TASK_ALWAYS_EAGER=False`,
`CELERY_BROKER_URL` and `CELERY_RESULT_BACKEND`, and run two extra processes:

```bash
celery -A config worker -l info
celery -A config beat -l info
```

## 7. MikroTik router integration

Nodes default to **Manual** (provisioning is recorded in Nexora only). To let Nexora control a router:

On the MikroTik router:

```
/ip service enable api                 # port 8728 (or enable api-ssl for 8729)
/ip service set api address=<backend server IP>/32
/user group add name=nexora policy=api,read,write
/user add name=nexora-api group=nexora password=<strong password>
/ppp profile add name=<profile per package>   # rate limits for each Nexora package
```

In Nexora:

1. **Packages** — set *Router PPP Profile* to the profile name on the router (blank = package code).
2. **Network → Add/Edit Node** — choose *MikroTik RouterOS API (PPPoE)*, enter the API host, port,
   username and password, save, then press **Test Router Connection**.
3. Activate a test customer on that node. Nexora creates the PPPoE secret; suspend/restore then
   disables/enables it and drops the live session.

The backend must be able to reach the router's API port over the network (public IP, VPN or
private link). Verify activate, suspend and restore on one real router before onboarding customers.

## 8. Post-deploy checklist

- [ ] Deploy logs show the migrations applying `OK` and Gunicorn starting
- [ ] `https://<backend>/api/v1/auth/me/` returns a JSON 401 (API is up)
- [ ] Frontend loads and can log in (no CORS errors in the browser console)
- [ ] Super admin can approve a test ISP registration
- [ ] A receipt uploaded before a redeploy is still viewable after it (volume works)
- [ ] `run_billing_automation` is scheduled daily
- [ ] On a MikroTik node, Test Router Connection succeeds and activate/suspend/restore work
- [ ] Each ISP has created and got approval for its WhatsApp templates in Meta (see [WHATSAPP_TEMPLATES.md](WHATSAPP_TEMPLATES.md)) and its WhatsApp provider shows Connected

## 9. Known limitations

- SMS sending is not implemented; the SMS provider reports "not configured". Email and WhatsApp work
  once configured.
- The HR attendance/leave API is live but has no frontend screens yet.
- The *AI ISP Copilot* page (`/intelligence`) and the billing-automation and notification sections of
  *Settings* still show sample data. The Command Center Copilot uses real data.
- Failed provisioning requests are not retried automatically. A failed suspension or restore puts the
  service back in its previous state, so staff can simply request it again. A failed **activation**
  cannot be re-issued from the app yet; create the PPPoE secret on the router by hand or fix the
  router settings and contact the developer.
- Static files (Django admin CSS) are not served in production (no WhiteNoise/CDN configured), so
  `/admin/` works but looks unstyled. The Nexora frontend is unaffected.
