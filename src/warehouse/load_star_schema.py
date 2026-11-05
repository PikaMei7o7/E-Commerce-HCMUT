"""Load existing public operational tables into existing star_schema tables.
Does not run ETL, read CSVs, create/modify schema DDL, or truncate data.
"""
from datetime import timedelta
import logging
import os
from pathlib import Path

import psycopg2
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
SQL_DIR = ROOT / "sql" / "star_schema_load"
load_dotenv(ROOT / ".env")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S")
log = logging.getLogger("database_setup")


def get_connection():
    required = ("DB_HOST", "DB_NAME", "DB_USER", "DB_PASSWORD")
    missing = [key for key in required if not os.getenv(key)]
    if missing:
        raise RuntimeError("Missing .env settings: " + ", ".join(missing))
    return psycopg2.connect(
        host=os.environ["DB_HOST"], port=os.getenv("DB_PORT", "5432"),
        dbname=os.environ["DB_NAME"], user=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"], connect_timeout=20,
        application_name="hm_star_schema_loader",
    )


def read_sql(filename):
    path = SQL_DIR / filename
    if not path.is_file():
        raise FileNotFoundError(f"SQL file not found: {path}")
    return path.read_text(encoding="utf-8")


def run_dimension(conn, filename, table):
    log.info("[DIMENSION] START %s (%s)", table, filename)
    try:
        with conn.cursor() as cur:
            cur.execute(read_sql(filename))
            count = cur.rowcount
        conn.commit()
        log.info("[DIMENSION] DONE  %s: %s rows inserted/updated", table, count)
    except Exception:
        conn.rollback()
        log.exception("[DIMENSION] FAILED %s", table)
        raise


def run_fact_batches(conn, max_rows: int | None = None):
    log.info("[FACT] Getting transaction date range...")
    with conn.cursor() as cur:
        cur.execute('SELECT MIN(t_dat), MAX(t_dat) FROM public."transaction"')
        first, last = cur.fetchone()
        cur.execute("SELECT COUNT(*) FROM public.contains")
        total_contains = cur.fetchone()[0]
    if first is None or total_contains == 0:
        log.warning("[FACT] No source transactions/contains found; skipping fact_sales.")
        return

    total_batches = (last - first).days + 1
    batch_sql = read_sql("05_fact_sales_batch.sql")
    target_rows = min(max_rows, total_contains) if max_rows is not None else None
    if target_rows is not None:
        batch_sql = batch_sql.replace("ON CONFLICT", "LIMIT %(limit)s\nON CONFLICT", 1)
        log.info(
            "[FACT] MINI MODE: loading up to %s rows into fact_sales (public.contains has %s rows)",
            f"{target_rows:,}",
            f"{total_contains:,}",
        )

    day = first
    batch_no = 0
    loaded_rows = 0
    while day <= last:
        end_day = day + timedelta(days=1)
        batch_no += 1
        params = {"start_date": day, "end_date": end_day}
        if target_rows is not None:
            params["limit"] = target_rows - loaded_rows

        log.info("[FACT] START fact_sales batch %d/%d | %s", batch_no, total_batches, day)
        try:
            with conn.cursor() as cur:
                cur.execute(batch_sql, params)
                count = cur.rowcount
            conn.commit()
            loaded_rows += count
            if target_rows is not None:
                log.info(
                    "[FACT] DONE  fact_sales batch %d/%d | %s rows (total: %s/%s)",
                    batch_no,
                    total_batches,
                    count,
                    f"{loaded_rows:,}",
                    f"{target_rows:,}",
                )
                if loaded_rows >= target_rows:
                    log.info("[FACT] Reached target of %s rows in fact_sales; stopping early.", f"{target_rows:,}")
                    break
            else:
                log.info("[FACT] DONE  fact_sales batch %d/%d | %s rows", batch_no, total_batches, count)
        except Exception:
            conn.rollback()
            log.exception("[FACT] FAILED fact_sales batch %d/%d | date=%s", batch_no, total_batches, day)
            raise
        day = end_day


def verify_counts(conn):
    tables = ["dim_customer", "dim_article", "dim_date", "dim_sale_channel", "fact_sales"]
    log.info("[VERIFY] Target table row counts:")
    with conn.cursor() as cur:
        for table in tables:
            cur.execute("SELECT to_regclass(%s)", (f"star_schema.{table}",))
            if cur.fetchone()[0] is None:
                log.warning("[VERIFY] star_schema.%s does not exist", table)
                continue
            cur.execute(f'SELECT COUNT(*) FROM star_schema."{table}"')
            log.info("[VERIFY] star_schema.%-20s %s rows", table, cur.fetchone()[0])


def load_star_schema(max_fact_rows: int | None = None):
    mode_label = f"MINI ({max_fact_rows:,} fact rows)" if max_fact_rows is not None else "FULL"
    log.info("Start public -> star_schema [%s]", mode_label)
    log.info("This script will not run ETL, load CSVs, modify schema files, or truncate tables.")
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SET statement_timeout = 0")
        conn.commit()
        log.info("Connected to PostgreSQL.")

        log.info("[PROGRESS 1/5] Load dim_customer")
        run_dimension(conn, "01_dim_customer.sql", "dim_customer")
        log.info("[PROGRESS 2/5] Load dim_article")
        run_dimension(conn, "02_dim_article.sql", "dim_article")
        log.info("[PROGRESS 3/5] Load dim_date")
        run_dimension(conn, "03_dim_date.sql", "dim_date")
        log.info("[PROGRESS 4/5] Load dim_sale_channel")
        run_dimension(conn, "04_dim_sale_channel.sql", "dim_sale_channel")
        log.info("[PROGRESS 5/5] Load fact_sales in daily batches")
        run_fact_batches(conn, max_rows=max_fact_rows)
        verify_counts(conn)
        log.info("Success public -> star_schema [%s]", mode_label)
    except Exception:
        conn.rollback()
        log.exception("Database load failed.")
        raise
    finally:
        conn.close()


def load_star_schema_mini(max_fact_rows: int = 1_000_000):
    """Load full dimension tables and limit `fact_sales` to `max_fact_rows`."""
    load_star_schema(max_fact_rows=max_fact_rows)


if __name__ == "__main__":
    load_star_schema()
