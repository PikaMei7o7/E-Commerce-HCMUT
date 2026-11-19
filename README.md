# E-Commerce-HCMUT

## Query optimization

The analytics portal and Power BI read the `star_schema.vw_*` views. To keep them fast:

- `mv_*` (materialized views, `sql/optimization/views.sql`) store the pre-computed result of the
  original JOIN / GROUP BY queries from `sql/schema/03_views.sql`.
- `vw_*` are replaced by thin wrappers `SELECT * FROM mv_*`, so the portal, Power BI and
  `web/dashboard_catalog.py` keep using the same `vw_*` names.

### Script run order

Set the flags in `main.py` (or run the files manually) in this order:

1. `VIEW_CREATE` → `sql/schema/03_views.sql`
2. `INDEX_CREATE` → `sql/optimization/indexes.sql`
3. `MV_CREATE` → `sql/optimization/views.sql`
4. `DATABASE_ACCESS_CREATE` → `sql/security/roles_and_grants.sql`

`views.sql` uses `DROP MATERIALIZED VIEW ... CASCADE`, which also drops the `vw_*` views and their
grants, so `roles_and_grants.sql` must always be re-run after it. If `03_views.sql` is run again
after `views.sql`, the `vw_*` views go back to the slow JOIN queries: re-run `views.sql`, then
`roles_and_grants.sql`.

### Refreshing the data

Materialized views do not update by themselves when `fact_sales` changes. Either:

- let **Airflow** do it: the DAG `hm_refresh_mv` refreshes all 12 `mv_*` at 02:00
  (Asia/Ho_Chi_Minh) every 48 hours. After loading new data with `main.py`, trigger it manually
  in the Airflow UI. See [airflow/README.md](airflow/README.md); or
- refresh manually from the repo root (all 12 MVs, one transaction):

  ```bash
  python -m src.warehouse.refresh_materialized_views
  ```

  or a single MV in SQL: `REFRESH MATERIALIZED VIEW star_schema.mv_sales_kpi;`

### Warning

Never define a materialized view as `SELECT * FROM star_schema.vw_*`. Because `vw_*` reads from
`mv_*`, the MV would read itself and `REFRESH MATERIALIZED VIEW` would silently keep the old data.
Always copy the full query from `03_views.sql` into the MV.

## Scheduled jobs (Airflow)

Airflow (Docker, folder [airflow/](airflow/)) runs two scheduled jobs:

| DAG             | Schedule (Asia/Ho_Chi_Minh)  | What it does                                             |
|-----------------|------------------------------|----------------------------------------------------------|
| `hm_refresh_mv` | 02:00, every 48 hours        | refresh the 12 `mv_*` (`src/warehouse/refresh_materialized_views.py`) |
| `hm_backup`     | 04:00, every day             | `pg_dump` of `public` + `star_schema` into `backups/`, keep the 7 newest (`src/backup/backup.py`) |

ETL, star schema loading and schema creation are **not** in Airflow: they still run with `main.py`.
Setup and usage: [airflow/README.md](airflow/README.md).
