import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import psycopg2
from psycopg2 import extensions, sql
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")

# Override with the BACKUP_DIR environment variable (default: <repo>/backups).
BACKUP_DIR = Path(os.getenv("BACKUP_DIR") or ROOT / "backups")
SCHEMAS = ("public", "star_schema")


def backup_database(schemas=SCHEMAS):
    params = {
        "DB_HOST": os.getenv("DB_HOST"),
        "DB_PORT": os.getenv("DB_PORT", "5432"),
        "DB_NAME": os.getenv("DB_NAME"),
        "DB_USER": os.getenv("DB_USER"),
        "DB_PASSWORD": os.getenv("DB_PASSWORD"),
    }
    missing = [key for key, value in params.items() if not value]
    if missing:
        raise ValueError("Missing environment variable(s): " + ", ".join(missing))

    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    started = datetime.now()
    stamp = started.strftime("%Y%m%d_%H%M%S")
    dump_file = BACKUP_DIR / f"{params['DB_NAME']}_{stamp}.dump"
    report_file = BACKUP_DIR / f"{params['DB_NAME']}_{stamp}_row_counts.txt"

    print("Database backup")
    print(f"Database : {params['DB_NAME']}")
    print(f"Host     : {params['DB_HOST']}")
    print(f"Schemas  : {', '.join(schemas)}")
    print(f"Backup   : {dump_file}")

    conn = psycopg2.connect(
        host=params["DB_HOST"], port=params["DB_PORT"], dbname=params["DB_NAME"],
        user=params["DB_USER"], password=params["DB_PASSWORD"],
        connect_timeout=20, application_name="hm_backup",
    )
    try:
        # repeatable read keeps one snapshot for the whole transaction; pg_dump joins it below
        conn.set_session(isolation_level=extensions.ISOLATION_LEVEL_REPEATABLE_READ, readonly=True)
        with conn.cursor() as cur:
            cur.execute("SELECT pg_export_snapshot()")
            snapshot = cur.fetchone()[0]

            counts = {}
            for schema in schemas:
                cur.execute(
                    "SELECT table_name FROM information_schema.tables "
                    "WHERE table_schema = %s AND table_type = 'BASE TABLE' ORDER BY table_name",
                    (schema,),
                )
                tables = [row[0] for row in cur.fetchall()]
                if not tables:
                    raise RuntimeError(f"Schema {schema!r} has no tables (or does not exist)")
                counts[schema] = {}
                for table in tables:
                    cur.execute(sql.SQL("SELECT COUNT(*) FROM {}.{}").format(
                        sql.Identifier(schema), sql.Identifier(table)))
                    counts[schema][table] = cur.fetchone()[0]
                    print(f"  counted {schema}.{table}: {counts[schema][table]:,} rows")

            command = [
                "pg_dump",
                "-h", params["DB_HOST"],
                "-p", params["DB_PORT"],
                "-U", params["DB_USER"],
                "-d", params["DB_NAME"],
                "-F", "c",
                f"--snapshot={snapshot}",
                "--strict-names",  # fail instead of silently skipping a missing schema
                *[f"--schema={schema}" for schema in schemas],
                "-f", str(dump_file),
            ]
            env = os.environ.copy()
            env["PGPASSWORD"] = params["DB_PASSWORD"]
            print("Running pg_dump...")
            try:
                subprocess.run(command, env=env, check=True)
            except FileNotFoundError:
                raise RuntimeError("pg_dump not found: add the PostgreSQL bin folder to PATH") from None
    except BaseException:
        dump_file.unlink(missing_ok=True)  # never leave a half-written dump behind
        raise
    finally:
        conn.rollback()
        conn.close()

    finished = datetime.now()
    width = max(len(t) for tables in counts.values() for t in tables) + 4
    lines = [
        "Database backup report",
        "",
        f"Database   : {params['DB_NAME']}",
        f"Host       : {params['DB_HOST']}:{params['DB_PORT']}",
        f"Started    : {started:%Y-%m-%d %H:%M:%S}",
        f"Finished   : {finished:%Y-%m-%d %H:%M:%S} ({(finished - started).total_seconds():.0f}s)",
        f"Dump file  : {dump_file.name} ({dump_file.stat().st_size / 1024 ** 2:,.1f} MB)",
        f"Schemas    : {', '.join(schemas)}",
        f"Snapshot   : {snapshot} (row counts and dump read the same snapshot)",
    ]
    for schema, tables in counts.items():
        lines += ["", f"[{schema}] {len(tables)} tables"]
        lines += [f"  {table:<{width}}{rows:>15,}" for table, rows in tables.items()]
        lines.append(f"  {'Total':<{width}}{sum(tables.values()):>15,}")
    grand_total = sum(sum(tables.values()) for tables in counts.values())
    lines += ["", f"{'Grand total':<{width + 2}}{grand_total:>15,}", ""]
    report_file.write_text("\n".join(lines), encoding="utf-8")

    print("\nBackup completed successfully.")
    print(f"Dump   : {dump_file}")
    print(f"Report : {report_file}")
    return dump_file, report_file


def cleanup_old_backups(keep: int = 7, db_name: str | None = None, backup_dir: Path | None = None):
    """Keep only the `keep` newest backups of one database, delete the older ones.

    A backup is the pair <db_name>_<YYYYmmdd_HHMMSS>.dump + <db_name>_<stamp>_row_counts.txt
    written by backup_database(). Only files in backup_dir whose name matches exactly this
    pattern for db_name are touched. Returns the list of deleted files.
    """
    if keep < 1:
        raise ValueError("keep must be at least 1")
    db_name = db_name or os.getenv("DB_NAME")
    if not db_name:
        raise ValueError("Missing environment variable: DB_NAME")
    backup_dir = Path(backup_dir or BACKUP_DIR)
    if not backup_dir.is_dir():
        return []

    pattern = re.compile(rf"^{re.escape(db_name)}_(\d{{8}}_\d{{6}})(\.dump|_row_counts\.txt)$")
    files_by_stamp: dict[str, list[Path]] = {}
    for path in backup_dir.iterdir():
        match = pattern.match(path.name)
        if match and path.is_file():
            files_by_stamp.setdefault(match.group(1), []).append(path)

    # YYYYmmdd_HHMMSS sorts chronologically as text: newest first
    old_stamps = sorted(files_by_stamp, reverse=True)[keep:]
    deleted = []
    for stamp in old_stamps:
        for path in files_by_stamp[stamp]:
            path.unlink()
            deleted.append(path)
            print(f"Deleted old backup file: {path.name}")
    print(f"Backup cleanup: kept {min(keep, len(files_by_stamp))} backup(s) of {db_name}, "
          f"deleted {len(deleted)} file(s).")
    return deleted


if __name__ == "__main__":
    try:
        backup_database()
    except Exception as e:
        print(f"\nBackup failed: {e}")
        sys.exit(1)
