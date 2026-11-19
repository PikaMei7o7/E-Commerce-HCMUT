# Airflow: scheduled MV refresh and database backup

Airflow 3.4.0 runs in Docker on your machine and handles two scheduled jobs:

| DAG             | Schedule (Asia/Ho_Chi_Minh) | Task(s)                                              |
|-----------------|-----------------------------|------------------------------------------------------|
| `hm_refresh_mv` | 02:00, every 48 hours       | `check_refresh_day` → `refresh_materialized_views`: refresh the 12 `star_schema.mv_*` in one transaction |
| `hm_backup`     | 04:00, every day            | `backup_database` (`pg_dump` of `public` + `star_schema` into `backups/`) → `cleanup_old_backups` (keep the 7 newest) |

Both heavy tasks use the pool `hm_db_pool` (1 slot), so a refresh and a backup never run at the same
time on the Cloud SQL instance, even when triggered by hand.

ETL, star schema loading and schema creation are **not** in Airflow: run them with `main.py`.

## Requirements

- Docker Desktop with the WSL2 backend.
- Docker Desktop → Settings → Resources: give Docker **at least 4 GB of memory**.
- The public IP of the machine running Airflow must be in the Cloud SQL instance's
  **Authorized networks** (the same IP as the machine running the web portal).
- The project's root `.env` must contain `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`.
  Airflow reads it from `../.env`; no password is copied into `docker-compose.yaml`.

## Start

```bash
cd airflow
cp .env.example .env          # then edit the admin password and the JWT secret
docker compose up airflow-init   # first time only: builds the image, creates the metadata DB,
                                 # the admin user and the pool hm_db_pool
docker compose up -d
```

Open http://localhost:8080 and log in with the user/password from `airflow/.env`.

New DAGs start **paused**: switch `hm_refresh_mv` and `hm_backup` on in the UI.

## Daily use

- After loading new data with `main.py`, trigger `hm_refresh_mv` manually (▶ button) so the
  dashboards show the new data.
- Backups are written to `backups/` in the repository: `<DB_NAME>_<timestamp>.dump` and
  `<DB_NAME>_<timestamp>_row_counts.txt`. Only the 7 newest pairs of the current database are kept.
  Cleanup only runs after a successful backup.
- Logs of every run: in the UI, or in `airflow/logs/`.

## Good to know

- `hm_refresh_mv` is scheduled every day at 02:00, but `check_refresh_day` lets it continue only
  every second day (counted from 2026-01-01), so the refresh runs exactly every 48 hours.
  On the other days the run shows as *skipped* in the UI; that is expected. Manual triggers always refresh.
- The compose project is named `hm-airflow` (containers `hm-airflow-*`, volume
  `hm-airflow_postgres-db-volume`), so it never shares data with another Airflow on the same machine.

- Airflow only runs while Docker is running. If the machine or Docker is off at 02:00 / 04:00, that
  run is skipped (`catchup=False`); it is not replayed later.
- Each DAG runs at most once at a time (`max_active_runs=1`). Retries: refresh 1×, backup 2×, 15 minutes apart.
- `pg_dump` in the image is version 18 (from the PGDG apt repository), matching the
  PostgreSQL 18 server. Check: `docker compose run --rm airflow-cli pg_dump --version`.
- If the pool is missing (for example after deleting it in the UI), recreate it:
  `docker compose run --rm airflow-cli airflow pools set hm_db_pool 1 "MV refresh and backup"`
  (or Admin → Pools in the UI). Tasks in a missing pool never start.

## Stop

```bash
docker compose down        # stop Airflow, keep run history
docker compose down -v     # stop and delete the metadata database (history, admin user, pool)
```

## Run the jobs without Airflow

From the repository root:

```bash
python -m src.warehouse.refresh_materialized_views
python src/backup/backup.py
```
