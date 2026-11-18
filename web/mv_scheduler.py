
############################################################
# MATERIALIZED VIEW SCHEDULER
# Refresh 12 Materialized Views every 2 days at 02:00 AM
############################################################

import logging
import os
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from pathlib import Path

import psycopg2
from dotenv import load_dotenv

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger


# ============================================================
# CONFIGURATION
# ============================================================

ROOT = Path(__file__).resolve().parent.parent

load_dotenv(ROOT / ".env")

MV_TIMEZONE = ZoneInfo("Asia/Ho_Chi_Minh")

logger = logging.getLogger("mv_scheduler")


# ============================================================
# MATERIALIZED VIEW LIST
# ============================================================

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


# ============================================================
# DATABASE CONNECTION
# ============================================================

def mv_get_connection():
    """
    Create a separate PostgreSQL connection
    for scheduled Materialized View refresh.
    """

    return psycopg2.connect(
        host=os.environ["DB_HOST"],
        port=os.getenv("DB_PORT", "5432"),
        dbname=os.environ["DB_NAME"],
        user=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"],
        connect_timeout=20,
        application_name="mv_refresh_scheduler",
    )


# ============================================================
# REFRESH MATERIALIZED VIEWS
# ============================================================

def mv_refresh_all():
    """
    Refresh all 12 Materialized Views in star_schema.

    This function is independent of existing refresh functions.
    """

    logger.info("=" * 60)
    logger.info("[MV SCHEDULER] Starting refresh of 12 views")
    logger.info("=" * 60)

    conn = None

    try:
        conn = mv_get_connection()

        # All refresh operations are in one transaction
        with conn:
            with conn.cursor() as cur:

                for index, view_name in enumerate(MV_LIST, start=1):

                    query = (
                        f'REFRESH MATERIALIZED VIEW '
                        f'"star_schema"."{view_name}"'
                    )

                    logger.info(
                        "[MV SCHEDULER] [%d/%d] Refreshing %s",
                        index,
                        len(MV_LIST),
                        view_name,
                    )

                    cur.execute(query)

                    logger.info(
                        "[MV SCHEDULER] [%d/%d] Completed %s",
                        index,
                        len(MV_LIST),
                        view_name,
                    )

        logger.info(
            "[MV SCHEDULER] All 12 views refreshed successfully."
        )

    except Exception:
        logger.exception(
            "[MV SCHEDULER] Refresh failed. Transaction rolled back."
        )

    finally:
        if conn is not None:
            conn.close()


# ============================================================
# CALCULATE NEXT 02:00 AM
# ============================================================

def mv_get_next_2am():
    """
    Calculate the next 02:00 AM in Vietnam timezone.
    """

    now = datetime.now(MV_TIMEZONE)

    next_run = now.replace(
        hour=2,
        minute=0,
        second=0,
        microsecond=0,
    )

    if now >= next_run:
        next_run += timedelta(days=1)

    return next_run


# ============================================================
# START SCHEDULER
# ============================================================

def start_mv_scheduler():
    """
    Start the background Materialized View scheduler.

    First run:
        Next 02:00 AM

    Subsequent runs:
        Every 48 hours
    """

    scheduler = BackgroundScheduler(
        timezone=MV_TIMEZONE
    )

    first_run = mv_get_next_2am()

    scheduler.add_job(
        mv_refresh_all,
        trigger=IntervalTrigger(
            days=2,
            start_date=first_run,
            timezone=MV_TIMEZONE,
        ),
        id="mv_refresh_all_job",
        name="Refresh 12 Materialized Views",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )

    scheduler.start()

    logger.info("[MV SCHEDULER] Started successfully.")

    logger.info(
        "[MV SCHEDULER] First refresh scheduled at: %s",
        first_run.strftime("%d/%m/%Y %H:%M:%S"),
    )

    logger.info(
        "[MV SCHEDULER] Refresh interval: every 48 hours."
    )

    return scheduler