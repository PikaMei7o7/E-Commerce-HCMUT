
"""
Main entry point for database setup, ETL execution (Full/Mini),
Star Schema loading (Full/Mini), and Web App startup.

Usage:
    Adjust the flags (0 or 1) in the CONFIGURATION section below,
    then run:
        python main.py
"""

import logging
import os
import sys
from pathlib import Path

import psycopg2
from dotenv import load_dotenv

OPERATION_SCHEMA_CREATE = 0
STAR_SCHEMA_CREATE = 0
VIEW_CREATE = 0
INDEX_CREATE = 0
MV_CREATE = 0   
DATABASE_ACCESS_CREATE = 0    
PROCESS_RAW_CSV = 0 
ETL = 0
ETL_MINI = 0
STAR_SCHEMA_LOADER = 0      
STAR_SCHEMA_LOADER_MINI = 0 
MINI_ROW_LIMIT = 1_000_000
RUN_WEB = 1  
# Path and environment configuration (.env)
ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / ".env")

# Add submodule directories to sys.path so internal imports work correctly
for sub_dir in (ROOT / "src", ROOT / "src" / "etl", ROOT / "web"):
    if str(sub_dir) not in sys.path:
        sys.path.insert(0, str(sub_dir))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("main")

SQL_FILES = {
    "OPERATION_SCHEMA": ROOT / "sql" / "schema" / "01_operational_schema.sql",
    "STAR_SCHEMA": ROOT / "sql" / "schema" / "02_star_schema.sql",
    "VIEW": ROOT / "sql" / "schema" / "03_views.sql",
    "INDEX": ROOT / "sql" / "optimization" / "indexes.sql",
    "MATERIALIZED_VIEW": ROOT / "sql" / "optimization" / "material_view.sql",
    "DATABASE_ACCESS": ROOT / "sql" / "security" / "roles_and_grants.sql",
}


# 1. Connect to the database using .env
def get_connection():
    required = ("DB_HOST", "DB_NAME", "DB_USER", "DB_PASSWORD")
    missing = [key for key in required if not os.getenv(key)]

    if missing:
        raise RuntimeError(
            f"Missing configuration in the .env file: {', '.join(missing)}"
        )

    return psycopg2.connect(
        host=os.environ["DB_HOST"],
        port=os.getenv("DB_PORT", "5432"),
        dbname=os.environ["DB_NAME"],
        user=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"],
        connect_timeout=20,
        application_name="hm_main_setup",
    )


# 2. Execute SQL files (schemas, views and access permissions)
def execute_sql_file(sql_path: Path, step_name: str) -> None:
    if not sql_path.is_file():
        raise FileNotFoundError(f"SQL file not found: {sql_path}")

    log.info(
        "[SQL] Starting %s (%s)...",
        step_name,
        sql_path.relative_to(ROOT),
    )

    sql_content = sql_path.read_text(encoding="utf-8")

    conn = get_connection()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(sql_content)

        log.info("[SQL] Successfully completed %s.", step_name)

    except Exception:
        log.exception(
            "[SQL] Error while executing %s (%s)",
            step_name,
            sql_path.name,
        )
        raise

    finally:
        conn.close()


def run_sql_setup() -> None:
    steps = [
        (
            OPERATION_SCHEMA_CREATE,
            SQL_FILES["OPERATION_SCHEMA"],
            "01_operational_schema.sql",
        ),
        (
            STAR_SCHEMA_CREATE,
            SQL_FILES["STAR_SCHEMA"],
            "02_star_schema.sql",
        ),
        (
            VIEW_CREATE,
            SQL_FILES["VIEW"],
            "03_views.sql",
        ),
        (
            INDEX_CREATE,
            SQL_FILES["INDEX"],
            "indexes.sql",
        ),
        (
            MV_CREATE,
            SQL_FILES["MATERIALIZED_VIEW"],
            "material_view.sql",
        ),
    ]

    for flag, sql_path, name in steps:
        if flag == 1:
            execute_sql_file(sql_path, name)
        else:
            log.info("[SKIP] Skipping %s (flag = %s)", name, flag)

    # material_view.sql drops vw_* with CASCADE, which also drops their grants:
    # the access step must follow it, even if DATABASE_ACCESS_CREATE was left at 0.
    if DATABASE_ACCESS_CREATE == 1 or MV_CREATE == 1:
        if DATABASE_ACCESS_CREATE != 1:
            log.info("[SQL] MV_CREATE = 1 dropped the vw_* grants: re-applying roles_and_grants.sql")
        run_database_access()
    else:
        log.info("[SKIP] Skipping roles_and_grants.sql (flag = %s)", DATABASE_ACCESS_CREATE)


def run_database_access() -> None:
    from src.security.create_login_users import create_login_users

    execute_sql_file(SQL_FILES["DATABASE_ACCESS"], "roles_and_grants.sql")
    logins = create_login_users()
    log.info("[SQL] Login accounts created/updated: %s", ", ".join(logins) or "none (no password in .env)")


# 3. Run ETL and star schema loader (full / mini)
def _ensure_processed_csv(max_contains_rows: int | None = None) -> None:
    from src.etl.transform_raw_data import processed_csv
    from src.etl.load_operational_data import LOAD_ORDER, PROCESSED_DIR

    missing_csv = [
        table
        for table in LOAD_ORDER
        if not (PROCESSED_DIR / f"{table}.csv").is_file()
    ]

    if PROCESS_RAW_CSV == 1 or missing_csv:
        if missing_csv:
            log.info(
                "[ETL] Missing processed CSV files (%s). "
                "Running transform_raw_data.py to generate them...",
                ", ".join(missing_csv),
            )
        else:
            log.info(
                "[ETL] PROCESS_RAW_CSV = 1. "
                "Running transform_raw_data.py to regenerate processed CSV files..."
            )

        processed_csv(max_contains_rows=max_contains_rows)

    else:
        log.info(
            "[ETL] All processed CSV files already exist in data/processed. "
            "Skipping raw CSV processing."
        )


def run_etl_pipeline() -> None:
    if ETL_MINI == 1:
        log.info(
            "[ETL-MINI] Starting MINI ETL "
            "(contains limited to %s rows)...",
            f"{MINI_ROW_LIMIT:,}",
        )

        from src.etl.load_operational_data import load_mini

        _ensure_processed_csv(max_contains_rows=MINI_ROW_LIMIT)
        load_mini(max_contains_rows=MINI_ROW_LIMIT)

        log.info("[ETL-MINI] MINI ETL completed successfully.")

    elif ETL == 1:
        log.info("[ETL-FULL] Starting FULL ETL...")

        from src.etl.load_operational_data import main as load_full

        _ensure_processed_csv(max_contains_rows=None)
        load_full(max_contains_rows=None)

        log.info("[ETL-FULL] FULL ETL completed successfully.")

    else:
        log.info(
            "[SKIP] Skipping ETL "
            "(ETL = %s, ETL_MINI = %s)",
            ETL,
            ETL_MINI,
        )

    if STAR_SCHEMA_LOADER_MINI == 1:
        log.info(
            "[LOADER-MINI] Starting MINI Star Schema loading "
            "(fact_sales limited to %s rows)...",
            f"{MINI_ROW_LIMIT:,}",
        )

        from src.warehouse.load_star_schema import load_star_schema_mini

        load_star_schema_mini(max_fact_rows=MINI_ROW_LIMIT)

        log.info(
            "[LOADER-MINI] MINI Star Schema loading completed successfully."
        )

    elif STAR_SCHEMA_LOADER == 1:
        log.info("[LOADER-FULL] Starting FULL Star Schema loading...")

        from src.warehouse.load_star_schema import load_star_schema

        load_star_schema(max_fact_rows=None)

        log.info(
            "[LOADER-FULL] FULL Star Schema loading completed successfully."
        )

    else:
        log.info(
            "[SKIP] Skipping Star Schema loading "
            "(STAR_SCHEMA_LOADER = %s, STAR_SCHEMA_LOADER_MINI = %s)",
            STAR_SCHEMA_LOADER,
            STAR_SCHEMA_LOADER_MINI,
        )


# 4. Start the web dashboard
def run_web_server() -> None:
    if RUN_WEB == 1:
        from web.app import app

        port = int(os.getenv("HM_PORT", "5050"))

        log.info(
            "[WEB] Starting H&M Analytics Hub at http://127.0.0.1:%d",
            port,
        )

        app.run(
            host="127.0.0.1",
            port=port,
            debug=False,
            threaded=True,
        )

    else:
        log.info("[SKIP] Skipping Web Dashboard startup (RUN_WEB = %s)", RUN_WEB)


def main() -> None:
    log.info("Starting main setup")

    run_sql_setup()
    run_etl_pipeline()
    run_web_server()

    log.info("Execution completed")


if __name__ == "__main__":
    main()