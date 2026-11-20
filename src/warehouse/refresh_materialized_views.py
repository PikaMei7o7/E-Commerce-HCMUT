import logging
import os
import time
from pathlib import Path

import psycopg2
from dotenv import load_dotenv
from psycopg2 import sql

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")
log = logging.getLogger("mv_refresh")

SCHEMA = "star_schema"
MV_LIST = [
    "mv_sales_kpi",
    "mv_monthly_sales",
    "mv_daily_customer_trend",
    "mv_sales_by_channel",
    "mv_product_performance",
    "mv_product_group_performance",
    "mv_product_type_performance",
    "mv_customer_spending",
    "mv_customer_spending_by_segment",
    "mv_sales_detail",
    "mv_customer_product_group_preference",
    "mv_customer_product_preference",
]

# The Cloud SQL instance only has 3.75 GB RAM: do not raise these values.
SESSION_SETTINGS = (
    "SET statement_timeout = 0",
    "SET work_mem = '128MB'",
    "SET maintenance_work_mem = '1GB'",
)


def get_connection():
    required = ("DB_HOST", "DB_NAME", "DB_USER", "DB_PASSWORD")
    missing = [key for key in required if not os.getenv(key)]
    if missing:
        raise RuntimeError("Missing .env settings: " + ", ".join(missing))
    return psycopg2.connect(
        host=os.environ["DB_HOST"], port=os.getenv("DB_PORT", "5432"),
        dbname=os.environ["DB_NAME"], user=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"], connect_timeout=20,
        application_name="hm_mv_refresh",
    )


def refresh_materialized_views() -> dict[str, float]:
    """Refresh every MV in MV_LIST in a single transaction.

    Returns {mv_name: seconds}. Raises on any error (after rolling back), so callers
    such as Airflow see the failure instead of a silent success.
    """
    timings: dict[str, float] = {}
    total = len(MV_LIST)
    started = time.perf_counter()
    log.info("[MV REFRESH] Starting refresh of %d materialized views", total)

    conn = get_connection()
    try:
        with conn:  # commit on success, rollback on any exception
            with conn.cursor() as cur:
                for setting in SESSION_SETTINGS:
                    cur.execute(setting)
                for index, mv_name in enumerate(MV_LIST, start=1):
                    log.info("[MV REFRESH] [%d/%d] Refreshing %s", index, total, mv_name)
                    mv_started = time.perf_counter()
                    cur.execute(sql.SQL("REFRESH MATERIALIZED VIEW {}.{}").format(
                        sql.Identifier(SCHEMA), sql.Identifier(mv_name)))
                    timings[mv_name] = round(time.perf_counter() - mv_started, 2)
                    log.info("[MV REFRESH] [%d/%d] Done %s in %.2fs",
                             index, total, mv_name, timings[mv_name])
    except Exception:
        log.exception("[MV REFRESH] Refresh failed, transaction rolled back. "
                      "No materialized view was changed.")
        raise
    finally:
        conn.close()

    log.info("[MV REFRESH] All %d views refreshed and committed in %.2fs",
             total, time.perf_counter() - started)
    return timings


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s",
                        datefmt="%H:%M:%S")
    refresh_materialized_views()
