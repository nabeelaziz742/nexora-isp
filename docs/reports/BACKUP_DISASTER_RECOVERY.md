# Nexora ISP — Backup & Disaster Recovery (DR) Runbook

## 1. Executive Summary & Recovery Objectives
- **Target RPO (Recovery Point Objective)**: $\le 1\text{ hour}$ for automated hourly backups; $\le 15\text{ minutes}$ when PostgreSQL Continuous WAL Archiving is activated.
- **Target RTO (Recovery Time Objective)**: $\le 30\text{ minutes}$ for complete cold-standby restoration.
- **Authoritative Database**: PostgreSQL 15+ / 16+.

---

## 2. Backup Strategy & Scheduling

### A. Snapshot Frequency & Retention Matrix
| Backup Type | Frequency | Retention Window | Storage Tier |
|---|---|---|---|
| **Daily Full Dump** | Every 24 hours at 02:30 UTC | 30 Days | Encrypted Local / Object Storage |
| **Weekly Snapshot** | Every Sunday at 03:00 UTC | 12 Weeks | Encrypted S3 / Cloud Bucket |
| **Monthly Snapshot** | 1st of each calendar month | 12 Months | Cold Storage / Glacier |
| **Transaction Logs (WAL)** | Continuous (every 15 min segment) | 7 Days | Streaming S3 Archive |

### B. Environment-Driven Configuration
The automated backup runner (`backend/scripts/backup_db.py`) relies exclusively on environment variables:
- `DB_NAME`: Target database name
- `DB_USER`: PostgreSQL user
- `DB_PASSWORD`: PostgreSQL user password
- `DB_HOST`: Database host (default: `127.0.0.1`)
- `DB_PORT`: Database port (default: `5432`)
- `BACKUP_STORAGE_PATH`: Directory path for local backup artifacts (default: `backend/backups`)

---

## 3. Database Restoration Procedure (Step-by-Step)

### Step 1: Pre-Restoration Verification
1. Ensure the PostgreSQL service is running and accessible.
2. Confirm adequate disk space on the target database host ($\ge 3\times$ uncompressed dump size).
3. Validate backup archive integrity:
   ```bash
   pg_restore --list /path/to/nexora_backup_<dbname>_<timestamp>.sql.gz
   ```

### Step 2: Database Re-creation (Cold Target)
```bash
# Terminate active client connections
psql -U postgres -h 127.0.0.1 -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname='nexora_isp';"

# Drop and recreate target database
dropdb -U postgres -h 127.0.0.1 --if-exists nexora_isp
createdb -U postgres -h 127.0.0.1 -O nexora_user nexora_isp
```

### Step 3: Archive Restoration
```bash
pg_restore -h 127.0.0.1 -p 5432 -U nexora_user -d nexora_isp -v -1 /path/to/nexora_backup_nexora_isp_<timestamp>.sql.gz
```

### Step 4: Post-Restore Integrity Verification
Run the automated Nexora verification suite:
```bash
python manage.py check
python manage.py showmigrations
python manage.py test tenancy accounts billing accounting
```

---

## 4. Disaster Recovery Invariants
1. **Zero Data Tampering**: Restored databases must maintain double-entry accounting balances ($\text{Debits} == \text{Credits}$).
2. **Tenant Isolation**: Verify that `OrganizationMembership` references and tenant foreign keys are intact across all tenant schemas.
3. **No Credential Exposure**: Never commit backup artifacts or unmasked database dumps to version control.
