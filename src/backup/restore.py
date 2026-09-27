import os
import subprocess
from pathlib import Path

from dotenv import load_dotenv


load_dotenv()

DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")

# Database used for recovery
RECOVERY_DB = "hm-ecommerce-recovery"

# Change File location
BACKUP_FILE = Path(
    "backups\hm-ecommerce_20260927_230941.dump"
)


if not BACKUP_FILE.exists():
    raise FileNotFoundError(
        f"Backup file not found: {BACKUP_FILE}"
    )


env = os.environ.copy()
env["PGPASSWORD"] = DB_PASSWORD


# =====================================
# Restore
# =====================================

command = [
    "pg_restore",

    "-h", DB_HOST,
    "-p", DB_PORT,
    "-U", DB_USER,
    "-d", RECOVERY_DB,

    # Don't try to restore original ownership
    "--no-owner",

    # Don't restore privileges
    "--no-acl",

    # Backup file
    str(BACKUP_FILE)
]


print("=" * 50)
print("DATABASE RECOVERY")
print("=" * 50)

print(f"Backup       : {BACKUP_FILE}")
print(f"Recovery DB  : {RECOVERY_DB}")


try:

    subprocess.run(
        command,
        env=env,
        check=True
    )

    print("\nRecovery completed successfully.")

except subprocess.CalledProcessError as e:

    print("\nRecovery failed.")
    print(e)