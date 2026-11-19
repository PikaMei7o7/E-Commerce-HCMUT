"""Daily database backup (pg_dump of public + star_schema) with rotation of old files.

Schedule: 04:00 Asia/Ho_Chi_Minh every day, after the 02:00 MV refresh. The pool hm_db_pool
(1 slot) is shared with hm_refresh_mv, so backup and refresh never run at the same time.
"""
from datetime import timedelta

import pendulum
from airflow.sdk import dag, task

VN_TZ = "Asia/Ho_Chi_Minh"
KEEP_BACKUPS = 7


@dag(
    dag_id="hm_backup",
    description="pg_dump public + star_schema, keep the newest 7 backups",
    schedule="0 4 * * *",
    start_date=pendulum.datetime(2026, 1, 1, tz=VN_TZ),
    catchup=False,
    max_active_runs=1,
    tags=["hm", "backup"],
    default_args={
        "retries": 2,
        "retry_delay": timedelta(minutes=15),
    },
)
def hm_backup():
    @task(pool="hm_db_pool")
    def backup_database() -> dict[str, str]:
        # Imported inside the task so DAG parsing never touches the project code or the DB
        from src.backup.backup import backup_database as run

        dump_file, report_file = run()
        return {"dump_file": str(dump_file), "report_file": str(report_file)}

    @task
    def cleanup_old_backups() -> list[str]:
        from src.backup.backup import cleanup_old_backups as run

        return [str(path) for path in run(keep=KEEP_BACKUPS)]

    backup_database() >> cleanup_old_backups()


hm_backup()
