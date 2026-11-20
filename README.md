# E-Commerce-HCMUT: H&M Analytics Hub

Data warehouse and analytics portal for the H&M Personalized Fashion dataset.

- **PostgreSQL** (Google Cloud SQL): operational schema `public` and data warehouse `star_schema`.
- **`main.py`**: creates the schemas, runs the ETL, loads the star schema and starts the web portal.
- **Web portal** (`web/`, Flask): log in with a PostgreSQL account and view the dashboards that account is allowed to see.
- **Airflow** (`airflow/`, Docker): scheduled materialized view refresh and database backup.

```
main.py                  entry point (flags 0/1)
.env                     database connection (not in git)
web/                     Flask portal (app.py, dashboard_catalog.py, static/)
src/etl/                 CSV -> public schema
src/warehouse/           public -> star_schema, materialized view refresh
src/backup/              backup.py, restore.py, verify_restore.py
sql/schema/              01_operational_schema, 02_star_schema, 03_views
sql/optimization/        indexes.sql, material_view.sql
sql/security/            roles_and_grants.sql
airflow/                 Docker setup + DAGs
data/raw/                original CSV files (not in git)
backups/                 backup files (not in git)
```

---

## 1. Requirements

- Python 3.12
- PostgreSQL client tools (`pg_dump`, `pg_restore`) version **18**, only needed to run backup/restore by hand
- Docker Desktop (WSL2 backend), only needed for Airflow
- Your machine's public IP must be in the Cloud SQL instance's **Authorized networks**
  (Google Cloud Console → SQL → your instance → Connections → Networking)

## 2. First-time setup

From the repository root:

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows (PowerShell / cmd)
# source .venv/bin/activate     # macOS / Linux
pip install -r requirements.txt
```

Create `.env` from the template:

```bash
copy .env.example .env          # Windows
# cp .env.example .env          # macOS / Linux
```

## 3. The `.env` file (database connection)

`.env` is read by `main.py`, the web portal, the backup scripts and Airflow. It is in `.gitignore`:
never commit it.

```ini
DB_HOST=YOUR_CLOUD_SQL_PUBLIC_IP
DB_PORT=5432
DB_NAME=your_database
DB_USER=your_user
DB_PASSWORD=your_password
```

| Variable | Required | Meaning |
|---|---|---|
| `DB_HOST` | yes | Public IP (or host name) of the PostgreSQL server |
| `DB_PORT` | no | Default `5432` |
| `DB_NAME` | yes | Database to work on |
| `DB_USER` / `DB_PASSWORD` | yes | Account used by `main.py`, refresh and backup. It needs the rights to create schemas and tables. |
| `DB_SSLMODE` | no | Default value shown on the web login form (`prefer`) |
| `HM_PORT` | no | Web portal port, default `5050` |
| `HM_CACHE_SECONDS` | no | How long the portal caches query results, default `600` |
| `HM_QUERY_TIMEOUT_MS` | no | Portal query timeout, default `600000` (10 minutes) |
| `BACKUP_DIR` | no | Backup folder for `backup.py` run by hand, default `backups/`. Airflow always uses `backups/`. |

### Switching to another database

For example, to move from a mini database to the full one, or to another server:

1. **Edit `.env`**: change `DB_NAME`, and `DB_HOST` / `DB_USER` / `DB_PASSWORD` if they differ.
   Tip: keep the other database as commented lines so switching is a copy-paste:

   ```ini
   # --- full database
   DB_NAME=hm-ecommerce
   # --- mini database
   # DB_NAME=hm-ecommerce-mini
   ```

2. **New server?** Add your machine's IP to that instance's *Authorized networks*.
3. **Empty database?** Create the schemas and load the data first (see [4.2](#42-set-up-a-new-database)).
4. **Restart the web portal.** `.env` is only read at start-up: stop `main.py` (Ctrl+C) and run it again.
5. **Restart Airflow so it picks up the new values.** A plain `docker compose restart` is **not**
   enough: the containers keep the old values until they are re-created.

   ```bash
   cd airflow
   docker compose up -d --force-recreate
   ```

6. Backups are named after the database (`<DB_NAME>_<timestamp>.dump`), and the "keep 7" rotation
   only counts files of the current `DB_NAME`, so backups of the old database are never deleted.

---

## 4. Running `main.py`

`main.py` has no command-line options. Open it, set the flags at the top to `1` (run) or `0` (skip),
then run:

```bash
python main.py
```

The steps always run in this order, whatever flags are set:

| # | Flag | What it does |
|---|---|---|
| 1 | `OPERATION_SCHEMA_CREATE` | `sql/schema/01_operational_schema.sql` (schema `public`) |
| 2 | `STAR_SCHEMA_CREATE` | `sql/schema/02_star_schema.sql` (schema `star_schema`) |
| 3 | `VIEW_CREATE` | `sql/schema/03_views.sql` (`vw_*` views) |
| 4 | `INDEX_CREATE` | `sql/optimization/indexes.sql` |
| 5 | `MV_CREATE` | `sql/optimization/material_view.sql` (`mv_*`, makes `vw_*` read from them) |
| 6 | `DATABASE_ACCESS_CREATE` | `sql/security/roles_and_grants.sql` (analyst roles) |
| 7 | `PROCESS_RAW_CSV` | `1`: regenerate `data/processed/*.csv` from `data/raw/` even if they exist |
| 8 | `ETL` / `ETL_MINI` | Load CSV files into `public` (full, or `contains` limited to `MINI_ROW_LIMIT` rows) |
| 9 | `STAR_SCHEMA_LOADER` / `STAR_SCHEMA_LOADER_MINI` | Load `public` → `star_schema` (full, or `fact_sales` limited to `MINI_ROW_LIMIT`) |
| 10 | `RUN_WEB` | Start the web portal |

If a step fails, `main.py` stops: the following steps do not run.

### 4.1 Host the web portal (database already set up)

Set every flag to `0` except `RUN_WEB = 1` (this is the default), then:

```bash
python main.py
```

Open **http://127.0.0.1:5050** (or the port set in `HM_PORT`). The login form is pre-filled with
`DB_HOST`, `DB_PORT`, `DB_NAME` and `DB_USER` from `.env`. Type the password of the PostgreSQL account
you want to use (for example an analyst account): the dashboards shown depend on that account's
privileges. The password stays in the server's memory only.

The portal listens on `127.0.0.1`, so it is only reachable from the same machine.
Stop it with **Ctrl+C**.

You can also start the portal without `main.py`: `python web/app.py`.

### 4.2 Set up a new database

Put the raw CSV files (`articles.csv`, `customers.csv`, `transactions_train.csv`) in `data/raw/`,
point `.env` to the new (empty) database, then run `main.py` with:

```python
OPERATION_SCHEMA_CREATE = 1
STAR_SCHEMA_CREATE = 1
VIEW_CREATE = 1
INDEX_CREATE = 1
MV_CREATE = 1
DATABASE_ACCESS_CREATE = 1
ETL = 1                     # or ETL_MINI = 1 for a small test database
STAR_SCHEMA_LOADER = 1      # or STAR_SCHEMA_LOADER_MINI = 1
RUN_WEB = 1
```

Then set them back to `0` (except `RUN_WEB`) so the next run only starts the web portal.
The full load (about 31 million rows) takes a long time; use the `_MINI` flags to test first.

### 4.3 Load new data into an existing database

Run with `ETL = 1` and `STAR_SCHEMA_LOADER = 1` (or the `_MINI` versions), then **refresh the
materialized views**, otherwise the dashboards keep showing the old numbers:

```bash
python -m src.warehouse.refresh_materialized_views
```

or trigger the DAG `hm_refresh_mv` in Airflow (see [5](#5-airflow-scheduled-refresh-and-backup)).

---

## 5. Airflow (scheduled refresh and backup)

Airflow runs in Docker and handles two scheduled jobs. ETL and star schema loading stay in `main.py`.

| DAG | Schedule (Asia/Ho_Chi_Minh) | What it does |
|---|---|---|
| `hm_refresh_mv` | 02:00, every 48 hours | Refresh the 12 `mv_*` in one transaction |
| `hm_backup` | 04:00, every day | `pg_dump` of `public` + `star_schema` into `backups/`, keep the 7 newest |

Both jobs share the pool `hm_db_pool` (1 slot), so they never run at the same time.

### Start Airflow

1. Docker Desktop → Settings → Resources: give Docker **at least 4 GB** of memory.
2. Make sure the root `.env` is filled in: Airflow reads the database settings from it.
3. Create the Airflow settings and start it:

   ```bash
   cd airflow
   copy .env.example .env               # Windows (cp on macOS / Linux); then change the password
   docker compose up airflow-init       # first time only: builds the image, creates the admin user and the pool
   docker compose up -d
   ```

4. Open **http://localhost:8080** and log in with the user/password from `airflow/.env`.
5. New DAGs start **paused**: switch on `hm_refresh_mv` and `hm_backup`.

### Daily use

- After loading new data with `main.py`, trigger `hm_refresh_mv` by hand (▶ button).
- On the days between two refreshes, `hm_refresh_mv` shows as *skipped*: this is expected.
- Airflow only runs while Docker is running. A run missed because the machine was off is not replayed.
- After changing the database in `.env`: `docker compose up -d --force-recreate` (see [3](#switching-to-another-database)).

### Stop Airflow

```bash
cd airflow
docker compose down        # stop, keep run history
docker compose down -v     # stop and delete Airflow's own metadata (history, admin user, pool)
```

`down -v` only deletes Airflow's internal database (volume `hm-airflow_postgres-db-volume`), never
the project database. Details: [airflow/README.md](airflow/README.md).

---

## 6. Backup and restore by hand

From the repository root (needs `pg_dump` / `pg_restore` 18 in `PATH`):

```bash
python src/backup/backup.py           # dump public + star_schema into backups/
python src/backup/restore.py          # restore a dump into the database hm-ecommerce-recovery
python src/backup/verify_restore.py   # compare hm-ecommerce-recovery with DB_NAME, print row counts per table
```

`restore.py` restores the file set in `BACKUP_FILE` at the top of the script: change it to the dump you
want. `verify_restore.py` writes its report to `backups/verification_<db>_<timestamp>.txt` and exits
with code 0 (PASS) or 1 (FAIL).

---

## 7. Query optimization

The analytics portal and Power BI read the `star_schema.vw_*` views. To keep them fast:

- `mv_*` (materialized views, `sql/optimization/material_view.sql`) store the pre-computed result of the
  original JOIN / GROUP BY queries from `sql/schema/03_views.sql`.
- `vw_*` are replaced by thin wrappers `SELECT * FROM mv_*`, so the portal, Power BI and
  `web/dashboard_catalog.py` keep using the same `vw_*` names.

### Script run order

Set the flags in `main.py` (or run the files manually) in this order:

1. `VIEW_CREATE` → `sql/schema/03_views.sql`
2. `INDEX_CREATE` → `sql/optimization/indexes.sql`
3. `MV_CREATE` → `sql/optimization/material_view.sql`
4. `DATABASE_ACCESS_CREATE` → `sql/security/roles_and_grants.sql`

`material_view.sql` uses `DROP MATERIALIZED VIEW ... CASCADE`, which also drops the `vw_*` views and their
grants, so `roles_and_grants.sql` must always be re-run after it. If `03_views.sql` is run again
after `material_view.sql`, the `vw_*` views go back to the slow JOIN queries: re-run `material_view.sql`, then
`roles_and_grants.sql`.

### Refreshing the data

Materialized views do not update by themselves when `fact_sales` changes. Either:

- let **Airflow** do it: the DAG `hm_refresh_mv` (see [5](#5-airflow-scheduled-refresh-and-backup)); or
- refresh manually from the repo root (all 12 MVs, one transaction):

  ```bash
  python -m src.warehouse.refresh_materialized_views
  ```

  or a single MV in SQL: `REFRESH MATERIALIZED VIEW star_schema.mv_sales_kpi;`

### Warning

Never define a materialized view as `SELECT * FROM star_schema.vw_*`. Because `vw_*` reads from
`mv_*`, the MV would read itself and `REFRESH MATERIALIZED VIEW` would silently keep the old data.
Always copy the full query from `03_views.sql` into the MV.
