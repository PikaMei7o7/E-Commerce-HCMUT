import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import psycopg2
from psycopg2 import extensions, sql
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")

BACKUP_DIR = ROOT / "backups"
SCHEMAS = ("public", "star_schema")


def backup_database(schemas=SCHEMAS):
    """Dump the given schemas with pg_dump and write a row-count report next to the dump.

    Both the row counts and pg_dump read the same exported snapshot, so the numbers in
    the report match exactly what is inside the .dump file. Returns (dump_file, report_file).
    """
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

    BACKUP_DIR.mkdir(exist_ok=True)
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


if __name__ == "__main__":
    try:
        backup_database()
    except Exception as e:
        print(f"\nBackup failed: {e}")
        sys.exit(1)
