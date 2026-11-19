"""Refresh the 12 star_schema materialized views (replaces the old APScheduler job).

Schedule: 02:00 Asia/Ho_Chi_Minh, every 48 hours. After loading new data with main.py,
trigger this DAG manually from the UI (manual runs always refresh).

How "every 48 hours at 02:00" is built:
- The DAG is scheduled daily at 02:00 (cron "0 2 * * *").
- The first task lets the run continue only on even days counted from REFRESH_ANCHOR,
  so refreshes are exactly 48 hours apart, also across month ends.
Why not schedule=timedelta(days=2): in Airflow 3 with catchup=False, a timedelta schedule is
not aligned to start_date. The first run happens when the DAG is switched on (e.g. 15:37) and
every restart of Docker after a missed run moves the time again, so 02:00 would be lost.
Why not cron "0 2 */2 * *": it runs on day 31 and again on day 1 (only 24 hours apart).
"""
from datetime import timedelta

import pendulum
from airflow.sdk import dag, task

VN_TZ = "Asia/Ho_Chi_Minh"
REFRESH_ANCHOR = pendulum.date(2026, 1, 1)  # a refresh day; the next ones are every 2 days


def is_refresh_day(run_type: str, run_after) -> bool:
    """Manual runs always refresh; scheduled runs only on even days since REFRESH_ANCHOR."""
    if run_type != "scheduled":
        return True
    day = pendulum.instance(run_after).in_timezone(VN_TZ).date()
    return (day - REFRESH_ANCHOR).days % 2 == 0


@dag(
    dag_id="hm_refresh_mv",
    description="Refresh the 12 star_schema materialized views in one transaction",
    schedule="0 2 * * *",
    start_date=pendulum.datetime(2026, 1, 1, tz=VN_TZ),
    catchup=False,
    max_active_runs=1,
    tags=["hm", "materialized-view"],
    default_args={
        "retries": 1,
        "retry_delay": timedelta(minutes=15),
    },
)
def hm_refresh_mv():
    @task.short_circuit
    def check_refresh_day(**context) -> bool:
        dag_run = context["dag_run"]
        return is_refresh_day(dag_run.run_type, dag_run.run_after)

    @task(pool="hm_db_pool")
    def refresh_materialized_views() -> dict[str, float]:
        # Imported inside the task so DAG parsing never touches the project code or the DB
        from src.warehouse.refresh_materialized_views import refresh_materialized_views as run

        return run()

    check_refresh_day() >> refresh_materialized_views()


hm_refresh_mv()
