import os
import subprocess
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv


load_dotenv();
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")


required = {
    "DB_HOST": DB_HOST,
    "DB_NAME": DB_NAME,
    "DB_USER": DB_USER,
    "DB_PASSWORD": DB_PASSWORD,
}

for key, value in required.items():
    if not value:
        raise ValueError(f"Missing environment variable: {key}")

backup_dir = Path("backups")
backup_dir.mkdir(exist_ok=True)
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
backup_file = backup_dir / f"{DB_NAME}_{timestamp}.dump"

env = os.environ.copy()
env["PGPASSWORD"] = DB_PASSWORD

command = [
    "pg_dump",
    "-h", DB_HOST,
    "-p", DB_PORT,
    "-U", DB_USER,
    "-d", DB_NAME,

    "-F","c",
    "--schema=public",
    "-f",str(backup_file)
]

print("=" * 50)
print("DATABASE BACKUP")
print("=" * 50)

print(f"Database : {DB_NAME}")
print(f"Host     : {DB_HOST}")
print(f"Backup  : {backup_file}")


try: 
    subprocess.run(
        command,
        env=env,
        check=True
    )
    print("\n Backup completed successfully.")
    print(f"File: {backup_file}")
except subprocess.CalledProcessError as e:
    print("\n Backup failed")
    print(e)