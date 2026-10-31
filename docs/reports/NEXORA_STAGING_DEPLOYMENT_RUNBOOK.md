# NEXORA ISP — STAGING DEPLOYMENT RUNBOOK
**Target Environment:** Ubuntu 24.04 LTS (x86_64 / ARM64) VPS  
**Platform Version:** Nexora ISP (Batch 1 → Batch 15 Verified Baseline)  
**Mode:** Operational Documentation & Step-by-Step Deployment Guide  
**Standard:** Current Repository Codebase, Django 6.0.7, Next.js 16.2.10, PostgreSQL 15+, Redis 7+  

---

## 1. Server Prerequisites & Architecture Sizing

### A. Minimum Hardware Requirements (Staging / QA)
- **Operating System:** Ubuntu 24.04 LTS (or Ubuntu 22.04 LTS)
- **CPU:** 2 vCPU cores ($\ge 2.0\text{ GHz}$)
- **RAM:** 4 GB System Memory ($\ge 2\text{ GB}$ Swap recommended)
- **Storage:** 25 GB NVMe / SSD Storage
- **Network:** 1 Public IPv4 Address, 100 Mbps+ Port

### B. Production Hardware Sizing Guidelines (Estimates)
- **Small ISP ($\le 1,000$ Subscribers):** 4 vCPU, 8 GB RAM, 50 GB NVMe
- **Medium ISP ($1,000 - 10,000$ Subscribers):** 8 vCPU, 16 GB RAM, 150 GB NVMe
- **Large ISP ($10,000+$ Subscribers):** 16+ vCPU, 32+ GB RAM, Dedicated Managed Database

### C. Network & Firewall Port Allocation
| Port | Protocol | Source | Destination | Purpose |
|:---:|:---:|:---:|:---:|---|
| **22** | TCP | Admin IPs / Bastion | VPS | SSH Management |
| **80** | TCP | Public Internet | Nginx | HTTP (Redirects to 443) |
| **443** | TCP | Public Internet | Nginx | HTTPS Production / Staging Traffic |
| **3000** | TCP | `127.0.0.1` Only | Next.js | Frontend Internal Server |
| **8000** | TCP | `127.0.0.1` Only | Gunicorn | Backend DRF API Internal Server |
| **5432** | TCP | `127.0.0.1` Only | PostgreSQL | Internal Relational Database |
| **6379** | TCP | `127.0.0.1` Only | Redis | Internal Cache & Celery Broker |

> **Security Mandate:** Ports `3000`, `8000`, `5432`, and `6379` **must never** be exposed to the public internet.

---

## 2. Server Base Provisioning

Execute the following commands on a freshly deployed Ubuntu 24.04 LTS server as `root` or a `sudo`-enabled user:

```bash
# ------------------------------------------------------------------------------
# 1. Update OS Package Index
# ------------------------------------------------------------------------------
sudo apt update && sudo apt upgrade -y

# ------------------------------------------------------------------------------
# 2. Install Essential Tools, Python, PostgreSQL, Redis, and Nginx
# ------------------------------------------------------------------------------
sudo apt install -y \
    curl \
    git \
    ufw \
    build-essential \
    libpq-dev \
    python3-dev \
    python3-pip \
    python3-venv \
    postgresql \
    postgresql-contrib \
    redis-server \
    nginx \
    certbot \
    python3-certbot-nginx

# ------------------------------------------------------------------------------
# 3. Install Node.js 20 LTS via NodeSource
# ------------------------------------------------------------------------------
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs

# Verify runtimes
python3 --version   # Expected: Python 3.12.x
node --version      # Expected: v20.x.x
npm --version       # Expected: 10.x.x
```

---

## 3. Firewall Configuration (UFW)

```bash
# Set default policies
sudo ufw default deny incoming
sudo ufw default allow outgoing

# Allow SSH and Web Traffic
sudo ufw allow 22/tcp comment 'SSH'
sudo ufw allow 80/tcp comment 'HTTP'
sudo ufw allow 443/tcp comment 'HTTPS'

# Enable Firewall
sudo ufw --force enable
sudo ufw status verbose
```

---

## 4. PostgreSQL Database Setup

```bash
# ------------------------------------------------------------------------------
# Configure Staging Database and Dedicated Role
# ------------------------------------------------------------------------------
sudo -u postgres psql << 'EOF'
CREATE DATABASE nexora_staging;
CREATE USER nexora_user WITH ENCRYPTED PASSWORD 'generate_a_secure_password_here';
GRANT ALL PRIVILEGES ON DATABASE nexora_staging TO nexora_user;
ALTER DATABASE nexora_staging OWNER TO nexora_user;
\c nexora_staging
GRANT ALL ON SCHEMA public TO nexora_user;
EOF

# Ensure PostgreSQL service is active
sudo systemctl enable postgresql
sudo systemctl restart postgresql
```

---

## 5. Redis In-Memory Cache & Broker Setup

```bash
# Enable and start Redis service
sudo systemctl enable redis-server
sudo systemctl restart redis-server

# Verify Redis connection
redis-cli ping   # Expected output: PONG
```

---

## 6. Project Deployment & Directory Structure

Recommended staging deployment layout:

```text
/var/www/nexora/
├── backend/                   # Django REST Framework backend
│   ├── venv/                  # Python virtual environment
│   ├── .env                   # Staging backend environment variables
│   ├── media/                 # Customer payment receipts & ticket attachments
│   └── staticfiles/           # Collected static assets
└── nexora-isp/                # Next.js 16 frontend
    ├── .env.local             # Staging frontend environment variables
    └── node_modules/          # Locked node dependencies
```

### Cloning and File Ownership Setup
```bash
sudo mkdir -p /var/www/nexora
sudo chown -R $USER:$USER /var/www/nexora
cd /var/www/nexora

# Clone repository
git clone <YOUR_GIT_REPOSITORY_URL> .
```

---

## 7. Backend Environment Configuration

Create `/var/www/nexora/backend/.env`:

```ini
# ------------------------------------------------------------------------------
# NEXORA BACKEND STAGING CONFIGURATION
# ------------------------------------------------------------------------------
DJANGO_SECRET_KEY=generate_a_random_50_character_secret_string_here
DJANGO_DEBUG=False

# Database Settings
DB_NAME=nexora_staging
DB_USER=nexora_user
DB_PASSWORD=your_postgresql_password_from_step_4
DB_HOST=127.0.0.1
DB_PORT=5432

# Redis & Celery Settings
REDIS_URL=redis://127.0.0.1:6379/1
CELERY_BROKER_URL=redis://127.0.0.1:6379/0
CELERY_RESULT_BACKEND=redis://127.0.0.1:6379/0
CELERY_TASK_ALWAYS_EAGER=False

# Host & Security Origins (Update with your actual staging domain)
ALLOWED_HOSTS=staging.nexora.isp,staging-api.nexora.isp,127.0.0.1
CORS_ALLOWED_ORIGINS=https://staging.nexora.isp
CSRF_TRUSTED_ORIGINS=https://staging.nexora.isp

# HTTPS Cookie Protection
SECURE_SSL_REDIRECT=False
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True
SECURE_HSTS_SECONDS=31536000

# Transactional Email (Optional for Staging)
DEFAULT_FROM_EMAIL=notifications@staging.nexora.isp

# JWT Lifetimes
JWT_ACCESS_TOKEN_LIFETIME_MINUTES=15
JWT_REFRESH_TOKEN_LIFETIME_DAYS=1
```

---

## 8. Backend Dependencies, Migrations & Static Collection

```bash
cd /var/www/nexora/backend

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Upgrade pip and install pinned requirements
pip install --upgrade pip
pip install -r requirements.txt

# Run database migrations
python manage.py migrate --noinput

# Collect static files into backend/staticfiles/
python manage.py collectstatic --noinput

# Create required media upload directories
mkdir -p media/payment_receipts media/complaints
chmod -R 775 media
```

---

## 9. Frontend Environment & Production Build

Create `/var/www/nexora/nexora-isp/.env.local`:

```ini
# ------------------------------------------------------------------------------
# NEXORA FRONTEND STAGING CONFIGURATION
# ------------------------------------------------------------------------------
NEXT_PUBLIC_API_BASE_URL=https://staging.nexora.isp/api/v1
```

Build the Next.js application:

```bash
cd /var/www/nexora/nexora-isp

# Install locked dependencies
npm ci

# Compile production bundle (App Router Turbopack)
npm run build
```

---

## 10. Systemd Production Daemon Services

Create the system service units below under `/etc/systemd/system/`:

### A. Backend Gunicorn Service: `/etc/systemd/system/nexora-backend.service`
```ini
[Unit]
Description=Nexora ISP Django Gunicorn WSGI Server
After=network.target postgresql.service redis-server.service

[Service]
User=www-data
Group=www-data
WorkingDirectory=/var/www/nexora/backend
EnvironmentFile=/var/www/nexora/backend/.env
ExecStart=/var/www/nexora/backend/venv/bin/gunicorn config.wsgi:application \
    --workers 4 \
    --bind 127.0.0.1:8000 \
    --timeout 60 \
    --access-logfile /var/log/nexora/backend-access.log \
    --error-logfile /var/log/nexora/backend-error.log

Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

### B. Frontend Next.js Service: `/etc/systemd/system/nexora-frontend.service`
```ini
[Unit]
Description=Nexora ISP Next.js Frontend Server
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/var/www/nexora/nexora-isp
Environment=NODE_ENV=production
Environment=PORT=3000
ExecStart=/usr/bin/npm run start -- -p 3000

Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

### C. Celery Worker Service: `/etc/systemd/system/nexora-celery-worker.service`
```ini
[Unit]
Description=Nexora ISP Celery Background Worker Pool
After=network.target postgresql.service redis-server.service

[Service]
User=www-data
Group=www-data
WorkingDirectory=/var/www/nexora/backend
EnvironmentFile=/var/www/nexora/backend/.env
ExecStart=/var/www/nexora/backend/venv/bin/celery -A config worker \
    --loglevel=INFO \
    --concurrency=4 \
    --logfile=/var/log/nexora/celery-worker.log

Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

### D. Celery Beat Service: `/etc/systemd/system/nexora-celery-beat.service`
```ini
[Unit]
Description=Nexora ISP Celery Beat Periodic Task Scheduler
After=network.target redis-server.service

[Service]
User=www-data
Group=www-data
WorkingDirectory=/var/www/nexora/backend
EnvironmentFile=/var/www/nexora/backend/.env
ExecStart=/var/www/nexora/backend/venv/bin/celery -A config beat \
    --loglevel=INFO \
    --logfile=/var/log/nexora/celery-beat.log

Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

### Enable and Start All Daemons
```bash
# Create log directory and set permissions
sudo mkdir -p /var/log/nexora
sudo chown -R www-data:www-data /var/log/nexora
sudo chown -R www-data:www-data /var/www/nexora

# Reload systemd and start all services
sudo systemctl daemon-reload
sudo systemctl enable --now nexora-backend
sudo systemctl enable --now nexora-frontend
sudo systemctl enable --now nexora-celery-worker
sudo systemctl enable --now nexora-celery-beat
```

---

## 11. Nginx Reverse Proxy & SSL Configuration

Create `/etc/nginx/sites-available/nexora.conf`:

```nginx
# HTTP to HTTPS Redirect
server {
    listen 80;
    server_name staging.nexora.isp;
    return 301 https://$host$request_uri;
}

# Main Application Server
server {
    listen 443 ssl http2;
    server_name staging.nexora.isp;

    # SSL Certificates (Configured by Certbot)
    ssl_certificate /etc/letsencrypt/live/staging.nexora.isp/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/staging.nexora.isp/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    # Maximum file upload size for receipts & ticket attachments
    client_max_body_size 25M;

    # Static Assets (Directly served by Nginx)
    location /static/ {
        alias /var/www/nexora/backend/staticfiles/;
        expires 30d;
        add_header Cache-Control "public, no-transform";
    }

    # Media Uploads (Receipts and attachments)
    location /media/ {
        alias /var/www/nexora/backend/media/;
        expires 7d;
        add_header Cache-Control "public, no-transform";
    }

    # Backend DRF API and Django Admin
    location ~ ^/(api|admin)/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto https;
        proxy_read_timeout 90;
        proxy_connect_timeout 90;
    }

    # Frontend Next.js Web Application
    location / {
        proxy_pass http://127.0.0.1:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }
}
```

Enable virtual host and obtain SSL certificate:

```bash
sudo ln -s /etc/nginx/sites-available/nexora.conf /etc/nginx/sites-enabled/
sudo nginx -t

# Obtain Let's Encrypt SSL Certificate
sudo certbot --nginx -d staging.nexora.isp

# Reload Nginx
sudo systemctl restart nginx
```

---

## 12. SUPERADMIN ACCOUNT & ACCESS

### SuperAdmin Creation

The SuperAdmin account in Nexora ISP uses the custom user model (`accounts.models.User` extending `AbstractUser`) with `is_superuser = True` and `is_active = True`. The primary authentication identifier is the administrator's **email address** (`USERNAME_FIELD = "email"`).

To create the SuperAdmin account on the staging/production server:

```bash
cd /var/www/nexora/backend
source venv/bin/activate

# Execute the interactive Django superuser creation command
python manage.py createsuperuser
```

When prompted by the CLI, provide the required parameters:
1. **Email:** Unique administrator email address (e.g., `admin@nexora.isp`). This will be the login username.
2. **Username:** Administrative handle/identifier (e.g., `superadmin`).
3. **First name:** Administrator's given name (e.g., `Platform`).
4. **Last name:** Administrator's family name (e.g., `Admin`).
5. **Password:** Strong administrator password (minimum 8 characters, alphanumeric + symbols).

> **Important Configuration Note:** No manual database manipulation, seed script, or organization membership assignment is required. The custom `accounts.models.User` model automatically sets `is_staff = True`, `is_superuser = True`, and `is_active = True`. Platform SuperAdmins operate globally and are decoupled from individual tenant organizations.

---

### SuperAdmin Login

Nexora provides a dedicated, security-isolated SuperAdmin portal in the Next.js frontend, separate from tenant workspace sign-in.

- **SuperAdmin Login URL:**  
  `https://staging.nexora.isp/superadmin/login`  
  *(Format: `https://YOUR-DOMAIN/superadmin/login`)*

- **SuperAdmin Dashboard URL:**  
  `https://staging.nexora.isp/superadmin`  
  *(Format: `https://YOUR-DOMAIN/superadmin`)*

- **Portal Distinction Reference:**
  | Portal | URL Path | Intended User / Role | Authentication Mechanism |
  |---|---|---|---|
  | **SuperAdmin Portal** | `/superadmin/login` | Platform SuperUser | Global Email + Password (`/api/v1/onboarding/superadmin/login/`) |
  | **Tenant ISP Sign In** | `/` | ISP Owner, Operator, Staff | Email + Password + Organization Code (`/api/v1/auth/login/`) |
  | **New ISP Registration**| `/signup` | Public ISP Customers | Self-service registration form (`/api/v1/onboarding/register/`) |
  | **Payment & Status** | `/registration/[token]` | Unverified Registrant | Token-based access (`/api/v1/onboarding/registration/<token>/`) |
  | **Django Admin (Core)**| `/admin/` | Platform Engineer | Django Session Auth (`is_staff = True` required) |

---

### SuperAdmin Capabilities

The Nexora SuperAdmin dashboard (`/superadmin`) provides complete oversight and governance of the ISP onboarding lifecycle:

1. **Pending Registration Queue:**
   - Real-time list of all incoming ISP registrations with status `PENDING_VERIFICATION`.
   - Displays ISP Company Name, Owner Name, Owner Email, Organization Code, and Due Amount.
   - Powered by backend endpoint: `GET /api/v1/onboarding/superadmin/registrations/?status=PENDING_VERIFICATION`.

2. **Payment Receipt Inspection:**
   - Visual preview of customer-uploaded deposit slips, wire confirmations, and payment screenshots via an in-browser modal.
   - Streamed securely from backend endpoint: `GET /api/v1/onboarding/superadmin/registrations/<id>/receipt/`.

3. **Atomic Tenant Activation (Approval):**
   - Single-click verification and activation of the new ISP organization.
   - Transitions `ISPRegistration.status` to `ACTIVE`.
   - Records verification timestamp (`verified_at`) and admin actor (`verified_by`).
   - Atomically activates the `Organization` (`is_active = True`).
   - Atomically activates the owner `User` account (`is_active = True`, `email_verified = True`).
   - Atomically activates the `OrganizationMembership` (`is_active = True`, `role = OWNER`).
   - Dispatches an automated activation email to the ISP owner containing their permanent Organization Code.
   - Powered by backend endpoint: `POST /api/v1/onboarding/superadmin/registrations/<id>/approve/`.

4. **Registration Rejection with Audit Reason:**
   - Rejects invalid or unconfirmed payment submissions with an explicit reason prompt.
   - Sets `ISPRegistration.status` to `REJECTED` and records `rejection_reason`.
   - Tenant user and organization remain inactive and blocked from logging in.
   - Allows customer to view the rejection feedback on `/registration/[token]` and re-upload a valid receipt.
   - Powered by backend endpoint: `POST /api/v1/onboarding/superadmin/registrations/<id>/reject/`.

5. **Global Payment Configuration Management:**
   - SuperAdmin can view and update the default registration setup fee details shown to all new signups:
     - Bank Name (e.g., `HBL`)
     - Account Title (e.g., `Muhammad Nabeel`)
     - Account Number (e.g., `17877900894403`)
     - IBAN
     - Registration Setup Fee Amount (PKR)
     - Custom Deposit Instructions
   - Powered by backend endpoints: `GET / PUT /api/v1/onboarding/superadmin/payment-settings/`.

---

### ISP Payment Verification Lifecycle

The end-to-end payment verification and onboarding workflow operates as follows:

```text
[ISP Customer]
       │
       ▼
1. Signup Form (/signup)
       │ Creates Organization & Owner User (is_active = False)
       │ Status: PENDING_PAYMENT
       ▼
2. Payment Instructions (/registration/[token])
       │ Customer views Bank Details (HBL, Account No, Title)
       │ Uses Copy buttons to transfer registration fee
       ▼
3. Receipt Upload (/registration/[token])
       │ Customer uploads bank transfer receipt / slip
       │ Status: PENDING_VERIFICATION
       ▼
[SuperAdmin]
       │
       ▼
4. SuperAdmin Review (/superadmin)
       │ SuperAdmin inspects receipt modal
       │ Matches payment with bank statement
       │
       ├─────────────────────────────────┐
       │ [Approve]                       │ [Reject]
       ▼                                 ▼
5a. Atomic Activation             5b. Rejection with Reason
   - Status -> ACTIVE                - Status -> REJECTED
   - Organization -> is_active=True  - Reason logged
   - Owner User -> is_active=True    - Customer sees rejection note
   - Activation email sent           - Customer re-uploads receipt
       │                                 │
       ▼                                 └───► Loops back to Step 3
6. ISP Sign In (/)
   - Owner logs in with Org Code
   - Accesses full Command Center
```

---

### Security Notes

1. **Strict SuperUser Authorization:**
   - All backend administrative endpoints are protected by [`IsSuperAdmin`](backend/onboarding/views.py), requiring `request.user.is_authenticated and request.user.is_superuser`.
   - Non-superuser accounts (including tenant owners, staff members, and unauthenticated requests) are strictly rejected with `HTTP 401 Unauthorized` or `HTTP 403 Forbidden`.

2. **Decoupled from Tenant Scope:**
   - SuperAdmin users do not belong to any specific tenant organization, preventing any unintended cross-tenant data pollution.

3. **Receipt Media Security:**
   - Payment receipts are stored in `/var/www/nexora/backend/media/payment_receipts/` and streamed exclusively through authenticated SuperAdmin endpoints (`FileResponse`).
   - Unauthorized users and unauthenticated sessions cannot list or download receipt attachments.

4. **Session Token Storage:**
   - SuperAdmin JWT credentials (`access` and `refresh` tokens) are managed independently under `nexora_superadmin_access` and `nexora_superadmin_refresh` storage keys, preventing session overlap with tenant operator sessions.


---

## 13. Staging Smoke Test Plan (26-Step Validation)

| # | Step | Action | Expected Output |
|:---:|---|---|---|
| **1** | Web Connectivity | Open `https://staging.nexora.isp` in browser | Landing page loads with zero HTTP/console errors |
| **2** | ISP Signup | Click "Create ISP Account" → Submit registration form | Organization & User created (inactive); redirected to `/registration/[token]` |
| **3** | Payment Instructions | Inspect displayed bank details on `/registration/[token]` | Bank Name, Account Title, Account Number, and IBAN rendered |
| **4** | Receipt Upload | Select sample payment image → Click "Submit Receipt" | State updates to `PENDING_VERIFICATION`; login disabled notice shown |
| **5** | SuperAdmin Login | Open `/superadmin/login` → Enter SuperAdmin credentials | Authentication succeeds; redirected to `/superadmin` dashboard |
| **6** | Receipt Review | Locate registration in queue → Click "Receipt" | Receipt image modal opens and previews uploaded image blob |
| **7** | Admin Approval | Click "Approve" in SuperAdmin portal | Status transitions to `ACTIVE`; Organization & User activated |
| **8** | ISP Owner Sign In | Open `/` → Log in with approved owner credentials | JWT tokens issued; redirected to `/command-center` |
| **9** | Command Center | Inspect operational dashboard metrics | KPI metrics, active subscribers, and charts render live data |
| **10**| Geographic Master | Navigate to Settings → Create City & Area | Area record saved and available in dropdowns |
| **11**| Package Creation | Navigate to Packages → Create Internet Package | Speed profiles (Mbps) and pricing saved |
| **12**| Customer Onboarding | Open `/customers/new` → Complete provisioning wizard | Customer, Service Account, Billing Profile, and Initial Invoice created atomically |
| **13**| Customer 360 | Open newly created Customer profile | All 5 tabs (Network, Custody, Billing, Tickets, Profile) load real API data |
| **14**| Serialized Custody | Inventory → Assign ONT/Router to customer | Device state transitions to `CUSTOMER_CUSTODY` with MAC/Serial linked |
| **15**| POS Retail Sale | Open `/pos` → Complete cash sale for inventory item | Real-time stock deducted; thermal receipt generated; GL journal entry posted |
| **16**| Recurring Invoicing | Open `/billing` → Trigger monthly billing run | Idempotent invoice created with line items; duplicate runs skipped |
| **17**| Payment Recording | Open `/invoices` → Record payment against invoice | FIFO allocation applied; balance reduced; GL entry posted ($\text{Debits} == \text{Credits}$) |
| **18**| Service Suspension | Open Customer Connection tab → Click "Suspend" | Service marked `SUSPENDED`; deprovisioning request enqueued |
| **19**| Service Restoration | Click "Restore" or record payment clearing balance | Service restored to `ACTIVE`; restoration provisioning enqueued |
| **20**| Support Ticket | Open `/support` → Create new complaint ticket | Ticket registered with SLA timer countdown |
| **21**| Ticket Lifecycle | Transition ticket `OPEN → ASSIGNED → RESOLVED` | Status updates smoothly with audit history note |
| **22**| Field Work Order | Open `/field-operations` → Create technician dispatch | Work order linked to ticket and customer location |
| **23**| Recovery Allocation | Open `/defaulters` → Assign overdue case to officer | Recovery case created and tracked |
| **24**| Accounting GL | Open `/accounting` → View Trial Balance & Reports | Invariant $\sum \text{Debits} == \sum \text{Credits}$ verified across all transactions |
| **25**| Audit Logs | Open `/settings` → Audit Logs | Full audit trail of previous actions logged with actor, timestamp, and IP |
| **26**| Session Invalidation | Click "Sign Out" → Attempt authenticated API call | Refresh token blacklisted; unauthorized requests rejected with `401` |

---

## 14. Backup & Disaster Recovery Verification

### Executing an Automated Database Backup
```bash
cd /var/www/nexora/backend
source venv/bin/activate
python scripts/backup_db.py
# Backup archive created: /var/www/nexora/backend/backups/nexora_staging_<timestamp>.sql.gz
```

### Restoring from Backup (Cold-Standby)
```bash
# 1. Terminate active database connections
sudo -u postgres psql -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname='nexora_staging';"

# 2. Drop and recreate clean database
sudo -u postgres dropdb nexora_staging
sudo -u postgres createdb -O nexora_user nexora_staging

# 3. Restore compressed archive
gunzip -c /var/www/nexora/backend/backups/nexora_staging_<timestamp>.sql.gz | sudo -u postgres psql -d nexora_staging

# 4. Verify data integrity
python manage.py showmigrations
```

---

## 15. Troubleshooting Reference

### 1. Nginx 502 Bad Gateway
- **Cause:** Backend Gunicorn or Next.js service is not running.
- **Diagnostics:**
  ```bash
  sudo systemctl status nexora-backend
  sudo systemctl status nexora-frontend
  sudo tail -n 50 /var/log/nexora/backend-error.log
  ```
- **Resolution:** Restart the dead service: `sudo systemctl restart nexora-backend`.

### 2. Database Connection Refused
- **Cause:** PostgreSQL service stopped or credentials in `.env` incorrect.
- **Diagnostics:** `sudo systemctl status postgresql` or test connection with `psql -U nexora_user -h 127.0.0.1 -d nexora_staging`.
- **Resolution:** Start PostgreSQL (`sudo systemctl start postgresql`) and verify `DB_PASSWORD` in `.env`.

### 3. Redis / Celery Tasks Stalled
- **Cause:** Redis service is down or Celery worker crashed.
- **Diagnostics:**
  ```bash
  redis-cli ping
  sudo systemctl status nexora-celery-worker
  sudo tail -n 50 /var/log/nexora/celery-worker.log
  ```
- **Resolution:** Restart Redis and Celery: `sudo systemctl restart redis-server nexora-celery-worker`.

### 4. CORS / CSRF Errors on API Calls
- **Cause:** `CORS_ALLOWED_ORIGINS` or `CSRF_TRUSTED_ORIGINS` in `.env` does not match the frontend domain.
- **Resolution:** Update `CORS_ALLOWED_ORIGINS=https://staging.nexora.isp` in `backend/.env` and reload: `sudo systemctl restart nexora-backend`.

### 5. Static Assets Missing / 404
- **Cause:** `collectstatic` was not executed or Nginx alias path is incorrect.
- **Resolution:** Run `python manage.py collectstatic --noinput` inside `backend/` and verify permissions.

---

## 16. Production Pilot Configuration (External Hardware & Gateways)

The following integrations are bound during customer-specific ISP onboarding:

1. **MikroTik RouterOS API:** Input Router IP, Port (8728/8729), API Username, and Password in Network Settings.
2. **FreeRADIUS AAA:** Enter RADIUS database connection string in Network Settings.
3. **GPON OLT:** Enter Huawei/ZTE OLT chassis management IP and SNMP community strings in Network Settings.
4. **WhatsApp Cloud API:** Enter Meta Business System User Token and Phone Number ID in Communication Settings.
5. **SMS Gateway:** Enter SMS aggregator API URL and credentials in Communication Settings.
6. **Payment Gateways:** Enter merchant credentials for Easypaisa, JazzCash, 1BILL, and Raast in Billing Settings.

---

## 17. Concise Technician Deployment Command Sequence

```bash
# 1. System Packages
sudo apt update && sudo apt install -y python3-venv python3-pip postgresql redis-server nginx nodejs npm git certbot python3-certbot-nginx
sudo ufw allow 22/tcp && sudo ufw allow 80/tcp && sudo ufw allow 443/tcp && sudo ufw --force enable

# 2. Database & Redis
sudo -u postgres psql -c "CREATE DATABASE nexora_staging;"
sudo -u postgres psql -c "CREATE USER nexora_user WITH ENCRYPTED PASSWORD 'staging_password';"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE nexora_staging TO nexora_user;"
sudo systemctl enable --now postgresql redis-server

# 3. Backend Setup
cd /var/www/nexora/backend
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate --noinput
python manage.py collectstatic --noinput
python manage.py createsuperuser

# 4. Frontend Setup
cd /var/www/nexora/nexora-isp
npm ci && npm run build

# 5. Service Daemons & Nginx
sudo systemctl daemon-reload
sudo systemctl enable --now nexora-backend nexora-frontend nexora-celery-worker nexora-celery-beat
sudo certbot --nginx -d staging.nexora.isp
sudo systemctl restart nginx
```
