#!/usr/bin/env python
"""
Nexora ISP — Automated PostgreSQL Database Backup Script
Safe, idempotent, environment-driven backup foundation.
"""
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


def run_backup():
    db_name = os.getenv("DB_NAME")
    db_user = os.getenv("DB_USER")
    db_password = os.getenv("DB_PASSWORD")
    db_host = os.getenv("DB_HOST", "127.0.0.1")
    db_port = os.getenv("DB_PORT", "5432")

    if not db_name or not db_user:
        print("[ERROR] Missing required DB_NAME or DB_USER environment variables.", file=sys.stderr)
        return 1

    backup_dir = Path(os.getenv("BACKUP_STORAGE_PATH", BASE_DIR / "backups"))
    backup_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%SZ")
    backup_filename = f"nexora_backup_{db_name}_{timestamp}.sql.gz"
    backup_path = backup_dir / backup_filename

    print(f"[*] Starting PostgreSQL backup for database '{db_name}'...")
    print(f"[*] Destination: {backup_path}")

    env = os.environ.copy()
    if db_password:
        env["PGPASSWORD"] = db_password

    # Execute pg_dump with gzip compression
    cmd = (
        f"pg_dump -h {db_host} -p {db_port} -U {db_user} -F c -b -v -f \"{backup_path}\" {db_name}"
    )

    try:
        result = subprocess.run(
            cmd,
            shell=True,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        if result.returncode != 0:
            print(f"[ERROR] Backup failed with exit code {result.returncode}:", file=sys.stderr)
            print(result.stderr, file=sys.stderr)
            return result.returncode

        file_size = backup_path.stat().st_size if backup_path.exists() else 0
        print(f"[SUCCESS] Database backup successfully created ({file_size} bytes).")
        return 0

    except Exception as exc:
        print(f"[ERROR] Unexpected error during backup execution: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(run_backup())
