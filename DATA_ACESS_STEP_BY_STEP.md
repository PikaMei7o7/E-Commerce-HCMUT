# Step by step: data access on the local database

Run every command from the project folder `E-Commerce-HCMUT`, in a terminal (PowerShell or cmd).
More detail: [DATA_ACCESS_REPORT.md](DATA_ACCESS_REPORT.md).

---

## Step 0 (optional). Wipe everything and start from zero

Deletes the local database with all its data, roles and accounts. **Cannot be undone.**

```bash
docker stop hm-postgres-local
docker rm hm-postgres-local
docker volume rm hm-pgdata
```

Then do Step 1 with the "First time only" commands. The result is an empty database
`hm_ecommerce_local` (owner `hm_owner`) with no tables, roles or analyst accounts.

## Step 1. Start the database

Start **Docker Desktop**, then:

```bash
docker start hm-postgres-local
```

First time only (the container does not exist yet):

```bash
docker run -d --name hm-postgres-local -e POSTGRES_PASSWORD=postgres_local_pw -p 5432:5432 -v hm-pgdata:/var/lib/postgresql postgres:18
docker exec hm-postgres-local psql -U postgres -c "CREATE ROLE hm_owner LOGIN CREATEROLE PASSWORD 'hm_owner_local_pw';" -c "CREATE DATABASE hm_ecommerce_local OWNER hm_owner;"
```

## Step 2. Fill in `.env`

```ini
DB_HOST=localhost
DB_PORT=5432
DB_NAME=hm_ecommerce_local
DB_SSLMODE=disable

# owner (admin)
DB_USER=hm_owner
DB_PASSWORD=hm_owner_local_pw

# product / sales analyst
HM_PRODUCT_ANALYST_USER=hm_product_analyst_01
HM_PRODUCT_ANALYST_PASSWORD=product_local_pw

# customer analyst
HM_CUSTOMER_ANALYST_USER=hm_customer_analyst_01
HM_CUSTOMER_ANALYST_PASSWORD=customer_local_pw
```

## Step 3. Build the database (once, on an empty database)

The access step needs the tables, views and data to exist first. These belong to the other parts
(schema, ETL, materialized views), but you run them once to get a working local database.

**Before you start:** the terminal must be free. If the portal is running in it (last line
`Press CTRL+C to quit`), anything you paste is not executed: click the terminal and press **Ctrl+C**
until you see the prompt `(.venv) PS C:\...\E-Commerce-HCMUT>`. Tip: open a second terminal with the
**+** button of the terminal panel, one for the portal and one for commands.

### 3.1 Build everything with one command (recommended)

Turns all the build flags on for this run only; `main.py` itself is not changed:

```powershell
.venv\Scripts\python -c "import main as m; [setattr(m, f, 1) for f in ('OPERATION_SCHEMA_CREATE','STAR_SCHEMA_CREATE','VIEW_CREATE','INDEX_CREATE','MV_CREATE','DATABASE_ACCESS_CREATE','PROCESS_RAW_CSV','ETL','STAR_SCHEMA_LOADER')]; m.RUN_WEB = 0; m.main()"
```

It runs, in order: operational tables (`public`), `star_schema`, the 12 `vw_*`, indexes, the 12 `mv_*`,
**`roles_and_grants.sql` + the 2 analyst accounts**, CSV cleaning (`data/raw/`), ETL into `public`, load
of `star_schema`. About 30-60 s with the sample data, much longer with the full H&M files.

Wait for the last line `[INFO] Execution completed`. On the way you should see `Starting ...` /
`Successfully completed ...` lines (not `[SKIP]`), the 2 `[ACCESS] Login ...` lines and
`[VERIFY] star_schema.fact_sales ... rows`.

It does **not** start the database (Step 1), fill the MVs (3.2) or start the portal (Step 5).

### 3.2 Fill the materialized views

The MVs are created before the data is loaded, so they stay empty (and the dashboards too) until:

```powershell
.venv\Scripts\python -m src.warehouse.refresh_materialized_views
```

Last line: `All 12 views refreshed and committed`.

### 3.3 Check it worked

```powershell
docker exec hm-postgres-local psql -U hm_owner -d hm_ecommerce_local -c "SELECT COUNT(*) FROM star_schema.fact_sales" -c "\du hm_*"
```

Expected: a non-zero row count, and the roles `hm_analyst_base`, `hm_product_sales_analyst`,
`hm_customer_analyst`, `hm_product_analyst_01`, `hm_customer_analyst_01`.

### Alternative: edit the flags in `main.py`

Same result as 3.1, but you change the file: set `OPERATION_SCHEMA_CREATE`, `STAR_SCHEMA_CREATE`,
`VIEW_CREATE`, `INDEX_CREATE`, `MV_CREATE`, `DATABASE_ACCESS_CREATE`, `PROCESS_RAW_CSV`, `ETL` and
`STAR_SCHEMA_LOADER` to `1` and `RUN_WEB` to `0`, **save (Ctrl+S)**, run `.venv\Scripts\python main.py`,
then 3.2. Afterwards set them all back to `0` except `RUN_WEB = 1`. If the log only shows `[SKIP]`
lines, the file was not saved.

### Errors when a step is skipped or run in the wrong order

| Error / symptom | Cause | Fix |
|---|---|---|
| Log shows only `[SKIP] ... (flag = 0)` | Flags still `0` (or `main.py` not saved) | Use 3.1, or save the file |
| Nothing happens after pasting a command | The portal is running in that terminal | Ctrl+C, then paste again |
| `schema "star_schema" does not exist` (refresh) | Refresh run before the build | Run 3.1 first, then 3.2 |
| `Group roles missing: ...` (account script) | Accounts created before `roles_and_grants.sql` ran | Run 3.1 (it creates roles and accounts) |
| `relation ... does not exist` (`roles_and_grants.sql`) | Grants applied before the views exist | Run 3.1 |

## Step 4. Create the accounts

- **Did Step 3?** The accounts already exist: go to Step 5. Use this step only to change a password or
  add an analyst.
- **Skipped Step 3** (you already have a database with data)? First create the roles once:

  ```powershell
  .venv\Scripts\python -c "import main as m; m.DATABASE_ACCESS_CREATE = 1; m.RUN_WEB = 0; m.main()"
  ```

  This also creates the 2 accounts, so you are done: go to Step 5.

### Option A: run the account script

The script **`src/security/create_login_users.py`** reads the user names and passwords from `.env`
and creates (or updates) the 2 logins:

| Login | Password (from `.env`) | Group role |
|---|---|---|
| `hm_product_analyst_01` | `HM_PRODUCT_ANALYST_PASSWORD` | `hm_product_sales_analyst` |
| `hm_customer_analyst_01` | `HM_CUSTOMER_ANALYST_PASSWORD` | `hm_customer_analyst` |

```powershell
.venv\Scripts\python -m src.security.create_login_users
```

Expected output:

```
[ACCESS] Login hm_product_analyst_01 -> hm_product_sales_analyst (read-only)
[ACCESS] Login hm_customer_analyst_01 -> hm_customer_analyst (read-only)
```

- **Change a password:** edit it in `.env`, then run the command again.
- **Add another analyst:** add a line to `LOGIN_USERS` in `src/security/create_login_users.py`, e.g.
  `("HM_PRODUCT_ANALYST2_USER", "hm_product_analyst_02", "HM_PRODUCT_ANALYST2_PASSWORD", "hm_product_sales_analyst"),`
  then add `HM_PRODUCT_ANALYST2_PASSWORD=...` to `.env` and run the command again.
- **Check the accounts exist:**

  ```powershell
  docker exec hm-postgres-local psql -U hm_owner -d hm_ecommerce_local -c "\du hm_*"
  ```

## Step 5. Log in to the portal

```bash
.venv\Scripts\python main.py
```

(with only `RUN_WEB = 1`), open http://127.0.0.1:5050 and log in:

| User | Password | Sees |
|---|---|---|
| `hm_product_analyst_01` | `product_local_pw` | Sales overview, Product performance |
| `hm_customer_analyst_01` | `customer_local_pw` | Sales overview, Customer segments, Sales explorer |
| `hm_owner` | `hm_owner_local_pw` | everything |

Stop the portal with Ctrl+C.

## Step 6. Run the tests

The test cases are split into 2 files, one per analyst. Each runs **logged in as that analyst**, so it
shows exactly what the analyst gets. Each takes a few seconds:

| File | Logged in as | Test cases |
|---|---|---|
| `sql/tests/TESTCASE5_PRODUCT_ANALYST.sql` | `hm_product_analyst_01` | TC-P00 - TC-P14 |
| `sql/tests/TESTCASE5_CUSTOMER_ANALYST.sql` | `hm_customer_analyst_01` | TC-C00 - TC-C13 |

```powershell
Get-Content sql\tests\TESTCASE5_PRODUCT_ANALYST.sql | docker exec -i hm-postgres-local sh -c "psql -U hm_product_analyst_01 -d hm_ecommerce_local -e 2>&1"
Get-Content sql\tests\TESTCASE5_CUSTOMER_ANALYST.sql | docker exec -i hm-postgres-local sh -c "psql -U hm_customer_analyst_01 -d hm_ecommerce_local -e 2>&1"
```

- `-e` prints each query right before its result, so the query and its output are together.
- `2>&1` keeps the `ERROR` lines in the right place.

The output of each file has **3 blocks**, one screenshot each:

| Block | Product analyst | Customer analyst | Every query... |
|---|---|---|---|
| `##### OVERVIEW #####` | TC-P00 | TC-C00 | lists every table / view / MV with `all`, `some columns` or `no` |
| `##### CAN DO #####` | TC-P01 - TC-P05 | TC-C01 - TC-C06 | returns rows |
| `##### CANNOT DO #####` | TC-P06 - TC-P14 | TC-C07 - TC-C13 | fails: `permission denied` (or `read-only transaction`) |

Each test case prints one line with what to expect, then the query, then the result:

```
TC-P06  customer column of sales detail   -> expect ERROR
SELECT customer_id FROM star_schema.vw_sales_detail LIMIT 1;
ERROR:  permission denied for view vw_sales_detail
```

What the blocks contain:

- **Overview:** what this account can read on every table, view and materialized view of `star_schema`.
- **Can do:** who am I (login, group roles, read-only session), then the views and tables the analyst is
  allowed to read.
- **Cannot do:** the views, columns and tables the analyst must not read, no direct `mv_*`, no `public`
  schema, then writes blocked twice: by the read-only session, then by missing privileges.

**For the report:** maximize the terminal (each block is about 40 lines), then take one screenshot of each
block: `OVERVIEW`, `CAN DO`, `CANNOT DO` (Win+Shift+S), and paste them in the 3 boxes of section 13
of `DATA_ACCESS_REPORT.docx`.

**One test case by hand:** log in as the analyst and paste the query of that test case from the file:

```powershell
docker exec -it hm-postgres-local psql -U hm_product_analyst_01 -d hm_ecommerce_local
```

(`hm_customer_analyst_01` for the other one; `\q` to leave.)
