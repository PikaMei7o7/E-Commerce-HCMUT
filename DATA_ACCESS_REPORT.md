# Data Access Report

This report lists access for every role, object and column in the **`star_schema`** schema:
5 base tables and 12 views (`vw_*`).

> **No role can access any materialized view (`mv_*`).** Analysts read the data only through the matching `vw_*`.

Sources:
- Access rules: [sql/security/roles_and_grants.sql](sql/security/roles_and_grants.sql)
- Login accounts: [src/security/create_login_users.py](src/security/create_login_users.py)
- Objects: [sql/schema/02_star_schema.sql](sql/schema/02_star_schema.sql), [sql/schema/03_views.sql](sql/schema/03_views.sql), [sql/optimization/material_view.sql](sql/optimization/material_view.sql)
- Tests: [TESTCASE5_PRODUCT_ANALYST.sql](sql/tests/TESTCASE5_PRODUCT_ANALYST.sql), [TESTCASE5_CUSTOMER_ANALYST.sql](sql/tests/TESTCASE5_CUSTOMER_ANALYST.sql)

---

## Contents

1. [Legend](#1-legend)
2. [Roles](#2-roles)
3. [Login accounts](#3-login-accounts)
4. [Privilege types](#4-privilege-types)
5. [Database and schema privileges](#5-database-and-schema-privileges)
6. [Summary matrix: all 17 objects](#6-summary-matrix-all-17-objects)
7. [Column detail: views `vw_*`](#7-column-detail-views-vw_)
8. [Column detail: star schema base tables](#8-column-detail-star-schema-base-tables)
9. [Sensitive columns: where each one is visible](#9-sensitive-columns-where-each-one-is-visible)
10. [Dashboards and the objects they read](#10-dashboards-and-the-objects-they-read)
11. [What no analyst can do](#11-what-no-analyst-can-do)
12. [Verification](#12-verification)

---

## 1. Legend

| Symbol | Meaning |
|:---:|---|
| ✅ | `SELECT` granted |
| 🟡 | `SELECT` granted on **some** columns only: see the column tables |
| ❌ | No access. The query fails with `permission denied` |

Role short names used in the tables:

| Short name | Role | Login |
|---|---|---|
| **Product** | `hm_product_sales_analyst` | `hm_product_analyst_01` |
| **Customer** | `hm_customer_analyst` | `hm_customer_analyst_01` |

---

## 2. Roles

| Role | `LOGIN` | Members | Purpose |
|---|:---:|---|---|
| `hm_product_sales_analyst` | NOLOGIN | `hm_product_analyst_01` | Product and sales analysis. **Cannot identify any customer** |
| `hm_customer_analyst` | NOLOGIN | `hm_customer_analyst_01` | Customer and purchase analysis. **No product-performance views** |

Both roles can read the "Sales overview" dashboard.

Attributes of both group roles: `NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS`. These are the `CREATE ROLE` defaults.

The groups are created only once and never dropped, because dropping a group would remove its members.

The materialized views are refreshed by the schema owner (`DB_USER`). There is **no** refresh role.

---

## 3. Login accounts

| Login (default name) | Name override in `.env` | Password in `.env` | Group |
|---|---|---|---|
| `hm_product_analyst_01` | `HM_PRODUCT_ANALYST_USER` | `HM_PRODUCT_ANALYST_PASSWORD` | `hm_product_sales_analyst` |
| `hm_customer_analyst_01` | `HM_CUSTOMER_ANALYST_USER` | `HM_CUSTOMER_ANALYST_PASSWORD` | `hm_customer_analyst` |

Attributes set on both logins:

| Setting | Value | Effect |
|---|---|---|
| `LOGIN` | yes | Can connect |
| `INHERIT` | yes | Gets its group's privileges automatically, with no `SET ROLE` needed |
| `SUPERUSER`, `CREATEDB`, `CREATEROLE`, `REPLICATION`, `BYPASSRLS` | no | No administrative powers |
| `default_transaction_read_only` | `on` | Every transaction is read-only. This is a second safety net in addition to the grants |
| Group memberships | exactly one `hm_*` group | Memberships left over from an earlier setup are revoked |

A login whose password variable is empty is skipped: it is not created or changed. Passwords are never stored in git or written to logs.

---

## 4. Privilege types

These are all the PostgreSQL privileges that exist on a table or view. The tables show which ones any analyst role gets.

| Privilege | Product | Customer |
|---|:---:|:---:|
| `SELECT` | listed objects / columns | listed objects / columns |
| Other (`INSERT`, `UPDATE`, `DELETE`, `TRUNCATE`, `REFERENCES`, `TRIGGER`, `MAINTAIN`, `WITH GRANT OPTION`) | ❌ | ❌ |

---

## 5. Database and schema privileges

| Object | Privilege | Product | Customer | Note |
|---|---|:---:|:---:|---|
| Current database (`DB_NAME`) | `CONNECT` | ✅ | ✅ | Needed to reach `star_schema` |
| Schema `star_schema` | `USAGE` | ✅ | ✅ | Needed to reference any object in the schema |
| Schema `star_schema` | `CREATE` | ❌ | ❌ | No analyst can create tables or views |

---

## 6. Summary matrix: all 17 objects

| # | Schema | Object | Type | Columns | Product | Customer |
|---:|---|---|---|---:|:---:|:---:|
| 1 | star_schema | `vw_sales_kpi` | View | 8 | ✅ | ✅ |
| 2 | star_schema | `vw_monthly_sales` | View | 8 | ✅ | ✅ |
| 3 | star_schema | `vw_sales_by_channel` | View | 7 | ✅ | ✅ |
| 4 | star_schema | `vw_daily_customer_trend` | View | 6 | ✅ | ✅ |
| 5 | star_schema | `vw_product_performance` | View | 10 | ✅ | ❌ |
| 6 | star_schema | `vw_product_group_performance` | View | 6 | ✅ | ❌ |
| 7 | star_schema | `vw_product_type_performance` | View | 7 | ✅ | ❌ |
| 8 | star_schema | `vw_customer_spending` | View | 8 | ❌ | ✅ |
| 9 | star_schema | `vw_customer_spending_by_segment` | View | 6 | ❌ | ✅ |
| 10 | star_schema | `vw_customer_product_group_preference` | View | 5 | ❌ | ✅ |
| 11 | star_schema | `vw_customer_product_preference` | View | 10 | ❌ | ✅ |
| 12 | star_schema | `vw_sales_detail` | View | 36 | 🟡 29/36 | ✅ |
| 13 | star_schema | `fact_sales` | Table | 8 | 🟡 7/8 | ✅ |
| 14 | star_schema | `dim_customer` | Table | 7 | ❌ | 🟡 6/7 |
| 15 | star_schema | `dim_article` | Table | 16 | ✅ | ✅ |
| 16 | star_schema | `dim_date` | Table | 7 | ✅ | ✅ |
| 17 | star_schema | `dim_sale_channel` | Table | 2 | ✅ | ✅ |

Totals (out of 17 objects):

| | Product | Customer |
|---|---:|---:|
| Objects readable in full | 10 | 13 |
| Objects readable in part | 2 | 1 |
| Objects with no access | 5 | 3 |

---

## 7. Column detail: views `vw_*`

### 7.1 `star_schema.vw_sales_kpi`

Grain: **1 row**, the KPIs for the whole data set. Dashboard: Sales overview.

| # | Column | Meaning | Product | Customer |
|---:|---|---|:---:|:---:|
| 1 | `total_revenue` | Sum of `sales_revenue` | ✅ | ✅ |
| 2 | `total_units_sold` | Sum of `quantity` | ✅ | ✅ |
| 3 | `total_transactions` | Distinct `transaction_id` | ✅ | ✅ |
| 4 | `distinct_articles_sold` | Distinct `article_id` | ✅ | ✅ |
| 5 | `purchasing_customers` | Distinct `customer_id` in `fact_sales` | ✅ | ✅ |
| 6 | `total_customers_in_dimension` | Row count of `dim_customer` | ✅ | ✅ |
| 7 | `average_order_value` | Revenue ÷ transactions | ✅ | ✅ |
| 8 | `average_spending_per_purchasing_customer` | Revenue ÷ purchasing customers | ✅ | ✅ |

### 7.2 `star_schema.vw_monthly_sales`

Grain: **1 row per year + month**. Dashboard: Sales overview.

| # | Column | Meaning | Product | Customer |
|---:|---|---|:---:|:---:|
| 1 | `year` | Calendar year | ✅ | ✅ |
| 2 | `month` | Calendar month (1–12) | ✅ | ✅ |
| 3 | `month_start_date` | First sales date of the month | ✅ | ✅ |
| 4 | `total_revenue` | Sum of `sales_revenue` | ✅ | ✅ |
| 5 | `total_units_sold` | Sum of `quantity` | ✅ | ✅ |
| 6 | `total_transactions` | Distinct transactions | ✅ | ✅ |
| 7 | `purchasing_customers` | Distinct customers | ✅ | ✅ |
| 8 | `average_order_value` | Revenue ÷ transactions | ✅ | ✅ |

### 7.3 `star_schema.vw_sales_by_channel`

Grain: **1 row per sales channel**. Dashboard: Sales overview.

| # | Column | Meaning | Product | Customer |
|---:|---|---|:---:|:---:|
| 1 | `sales_channel_id` | 1 = Store, 2 = Online | ✅ | ✅ |
| 2 | `sales_channel_name` | `Store` / `Online` / `Unknown` | ✅ | ✅ |
| 3 | `total_revenue` | Sum of `sales_revenue` | ✅ | ✅ |
| 4 | `total_units_sold` | Sum of `quantity` | ✅ | ✅ |
| 5 | `total_transactions` | Distinct transactions | ✅ | ✅ |
| 6 | `unique_customers` | Distinct customers | ✅ | ✅ |
| 7 | `average_order_value` | Revenue ÷ transactions | ✅ | ✅ |

### 7.4 `star_schema.vw_daily_customer_trend`

Grain: **1 row per day**. Dashboard: Sales overview.

| # | Column | Meaning | Product | Customer |
|---:|---|---|:---:|:---:|
| 1 | `full_date` | Sales date | ✅ | ✅ |
| 2 | `active_customers` | Distinct customers who bought that day | ✅ | ✅ |
| 3 | `total_units_sold` | Sum of `quantity` | ✅ | ✅ |
| 4 | `total_revenue` | Sum of `sales_revenue` | ✅ | ✅ |
| 5 | `avg_units_per_customer` | Units ÷ active customers | ✅ | ✅ |
| 6 | `avg_spending_per_customer` | Revenue ÷ active customers | ✅ | ✅ |

### 7.5 `star_schema.vw_product_performance`

Grain: **1 row per product** (`product_code`). Dashboard: Product performance.

| # | Column | Meaning | Product | Customer |
|---:|---|---|:---:|:---:|
| 1 | `product_code` | Product key | ✅ | ❌ |
| 2 | `prod_name` | Product name | ✅ | ❌ |
| 3 | `product_type_no` | Product type key | ✅ | ❌ |
| 4 | `prod_type_name` | Product type name | ✅ | ❌ |
| 5 | `product_group_name` | Product group | ✅ | ❌ |
| 6 | `total_units_sold` | Sum of `quantity` | ✅ | ❌ |
| 7 | `total_revenue` | Sum of `sales_revenue` | ✅ | ❌ |
| 8 | `total_transactions` | Distinct transactions | ✅ | ❌ |
| 9 | `unique_customers` | Distinct customers (a count only) | ✅ | ❌ |
| 10 | `revenue_per_unit` | Revenue ÷ units | ✅ | ❌ |

### 7.6 `star_schema.vw_product_group_performance`

Grain: **1 row per product group**. Dashboard: Product performance.

| # | Column | Meaning | Product | Customer |
|---:|---|---|:---:|:---:|
| 1 | `product_group_name` | Product group | ✅ | ❌ |
| 2 | `total_units_sold` | Sum of `quantity` | ✅ | ❌ |
| 3 | `total_revenue` | Sum of `sales_revenue` | ✅ | ❌ |
| 4 | `total_transactions` | Distinct transactions | ✅ | ❌ |
| 5 | `unique_customers` | Distinct customers (a count only) | ✅ | ❌ |
| 6 | `revenue_per_unit` | Revenue ÷ units | ✅ | ❌ |

### 7.7 `star_schema.vw_product_type_performance`

Grain: **1 row per product type**. Dashboard: Product performance.

| # | Column | Meaning | Product | Customer |
|---:|---|---|:---:|:---:|
| 1 | `product_type_no` | Product type key | ✅ | ❌ |
| 2 | `product_type_name` | Product type name | ✅ | ❌ |
| 3 | `total_units_sold` | Sum of `quantity` | ✅ | ❌ |
| 4 | `total_revenue` | Sum of `sales_revenue` | ✅ | ❌ |
| 5 | `total_transactions` | Distinct transactions | ✅ | ❌ |
| 6 | `distinct_articles_sold` | Distinct articles | ✅ | ❌ |
| 7 | `unique_customers` | Distinct customers (a count only) | ✅ | ❌ |

### 7.8 `star_schema.vw_customer_spending`

Grain: **1 row per customer** who bought at least once. Dashboard: Customer segments.

| # | Column | Meaning | Product | Customer |
|---:|---|---|:---:|:---:|
| 1 | `customer_id` | Customer key | ❌ | ✅ |
| 2 | `age` | Age in years | ❌ | ✅ |
| 3 | `age_group` | `Under 20`, `20-29`, …, `60+`, `Unknown` | ❌ | ✅ |
| 4 | `club_member_status` | Membership status (`UNKNOWN` if null) | ❌ | ✅ |
| 5 | `purchase_frequency` | Distinct transactions of the customer | ❌ | ✅ |
| 6 | `total_units_purchased` | Sum of `quantity` | ❌ | ✅ |
| 7 | `total_spending` | Sum of `sales_revenue` | ❌ | ✅ |
| 8 | `average_order_value` | Spending ÷ transactions | ❌ | ✅ |

### 7.9 `star_schema.vw_customer_spending_by_segment`

Grain: **1 row per age group + membership status**. Dashboard: Customer segments.

| # | Column | Meaning | Product | Customer |
|---:|---|---|:---:|:---:|
| 1 | `age_group` | Segment: age band | ❌ | ✅ |
| 2 | `club_member_status` | Segment: membership status | ❌ | ✅ |
| 3 | `purchasing_customers` | Distinct customers in the segment | ❌ | ✅ |
| 4 | `total_units_sold` | Sum of `quantity` | ❌ | ✅ |
| 5 | `total_revenue` | Sum of `sales_revenue` | ❌ | ✅ |
| 6 | `average_revenue_per_customer` | Revenue ÷ customers | ❌ | ✅ |

### 7.10 `star_schema.vw_customer_product_group_preference`

Grain: **1 row per customer + product group**. Dashboard: Customer segments (preferences).

| # | Column | Meaning | Product | Customer |
|---:|---|---|:---:|:---:|
| 1 | `customer_id` | Customer key | ❌ | ✅ |
| 2 | `product_group_name` | Product group | ❌ | ✅ |
| 3 | `total_quantity_purchased` | Units the customer bought in the group | ❌ | ✅ |
| 4 | `total_spending_in_group` | Spending in the group | ❌ | ✅ |
| 5 | `transactions_in_group` | Transactions in the group | ❌ | ✅ |

### 7.11 `star_schema.vw_customer_product_preference`

Grain: **1 row per customer + article**. Dashboard: Customer segments (preferences).

| # | Column | Meaning | Product | Customer |
|---:|---|---|:---:|:---:|
| 1 | `customer_id` | Customer key | ❌ | ✅ |
| 2 | `article_id` | Article key | ❌ | ✅ |
| 3 | `product_code` | Product key | ❌ | ✅ |
| 4 | `prod_name` | Product name | ❌ | ✅ |
| 5 | `product_type_no` | Product type key | ❌ | ✅ |
| 6 | `product_type_name` | Product type name | ❌ | ✅ |
| 7 | `product_group_name` | Product group | ❌ | ✅ |
| 8 | `total_quantity_purchased` | Units the customer bought | ❌ | ✅ |
| 9 | `total_spending_on_product` | Spending on the article | ❌ | ✅ |
| 10 | `purchase_frequency` | Transactions containing the article | ❌ | ✅ |

### 7.12 `star_schema.vw_sales_detail`

Built from `fact_sales` ⋈ `dim_date` ⋈ `dim_article` ⋈ `dim_customer`. Grain: **1 row per transaction + article**. Dashboard: Sales explorer.

- Product: **column-level grant**, 29 of 36 columns.
- Customer: **full grant**, 36 of 36 columns.

| # | Column | From | Product | Customer |
|---:|---|---|:---:|:---:|
| 1 | `transaction_id` | fact_sales | ✅ | ✅ |
| 2 | `customer_id` | fact_sales | ❌ | ✅ |
| 3 | `article_id` | fact_sales | ✅ | ✅ |
| 4 | `full_date` | dim_date | ✅ | ✅ |
| 5 | `date_key` | dim_date | ✅ | ✅ |
| 6 | `day` | dim_date | ✅ | ✅ |
| 7 | `month` | dim_date | ✅ | ✅ |
| 8 | `quarter` | dim_date | ✅ | ✅ |
| 9 | `year` | dim_date | ✅ | ✅ |
| 10 | `day_of_week` | dim_date | ✅ | ✅ |
| 11 | `sales_channel_id` | fact_sales | ✅ | ✅ |
| 12 | `sales_channel_name` | computed | ✅ | ✅ |
| 13 | `price_base` | dim_article | ✅ | ✅ |
| 14 | `product_code` | dim_article | ✅ | ✅ |
| 15 | `prod_name` | dim_article | ✅ | ✅ |
| 16 | `product_type_no` | dim_article | ✅ | ✅ |
| 17 | `prod_type_name` | dim_article | ✅ | ✅ |
| 18 | `product_group_name` | dim_article | ✅ | ✅ |
| 19 | `graphical_appearance_no` | dim_article | ✅ | ✅ |
| 20 | `colour_group_code` | dim_article | ✅ | ✅ |
| 21 | `perceived_colour_value_id` | dim_article | ✅ | ✅ |
| 22 | `perceived_colour_master_id` | dim_article | ✅ | ✅ |
| 23 | `department_no` | dim_article | ✅ | ✅ |
| 24 | `garment_group_no` | dim_article | ✅ | ✅ |
| 25 | `index_code` | dim_article | ✅ | ✅ |
| 26 | `index_group_no` | dim_article | ✅ | ✅ |
| 27 | `section_no` | dim_article | ✅ | ✅ |
| 28 | `age` | dim_customer | ❌ | ✅ |
| 29 | `age_group` | computed from `age` | ❌ | ✅ |
| 30 | `club_member_status` | dim_customer | ❌ | ✅ |
| 31 | `active` | dim_customer | ❌ | ✅ |
| 32 | `fn` | dim_customer | ❌ | ✅ |
| 33 | `fashion_news_frequency` | dim_customer | ❌ | ✅ |
| 34 | `price` | fact_sales | ✅ | ✅ |
| 35 | `quantity` | fact_sales | ✅ | ✅ |
| 36 | `sales_revenue` | fact_sales | ✅ | ✅ |

> **Product analyst: `SELECT *` fails.** The query must name only the 29 allowed columns, for example
> `SELECT transaction_id, full_date, prod_name, sales_revenue FROM star_schema.vw_sales_detail`.

---

## 8. Column detail: star schema base tables

These are for ad-hoc and Power BI work.

### 8.1 `star_schema.fact_sales`

Grain: 1 row per transaction + article. Primary key: (`transaction_id`, `article_id`).

- Product: **column-level grant**, 7 of 8 columns.
- Customer: **full grant**.

| # | Column | Type | Key | Product | Customer |
|---:|---|---|---|:---:|:---:|
| 1 | `transaction_id` | UUID | PK | ✅ | ✅ |
| 2 | `customer_id` | CHAR(64) | FK → dim_customer | ❌ | ✅ |
| 3 | `article_id` | CHAR(10) | PK, FK → dim_article | ✅ | ✅ |
| 4 | `date_key` | INTEGER | FK → dim_date | ✅ | ✅ |
| 5 | `sales_channel_id` | SMALLINT | FK → dim_sale_channel | ✅ | ✅ |
| 6 | `price` | DECIMAL(12,10) | | ✅ | ✅ |
| 7 | `quantity` | SMALLINT | | ✅ | ✅ |
| 8 | `sales_revenue` | DECIMAL(14,10) | | ✅ | ✅ |

> **Product analyst: `SELECT *` fails** on `fact_sales`. The query must leave out `customer_id`.

### 8.2 `star_schema.dim_customer`

Grain: 1 row per customer. Primary key: `customer_id`.

- Product: **no access**.
- Customer: **column-level grant**, 6 of 7 columns.

| # | Column | Type | Key | Product | Customer |
|---:|---|---|---|:---:|:---:|
| 1 | `customer_id` | CHAR(64) | PK | ❌ | ✅ |
| 2 | `age` | SMALLINT | | ❌ | ✅ |
| 3 | `fn` | BOOLEAN | | ❌ | ✅ |
| 4 | `active` | BOOLEAN | | ❌ | ✅ |
| 5 | `club_member_status` | VARCHAR(20) | | ❌ | ✅ |
| 6 | `fashion_news_frequency` | VARCHAR(20) | | ❌ | ✅ |
| 7 | `postal_code` | CHAR(64) | | ❌ | ❌ |

> **Customer analyst: `SELECT *` fails** on `dim_customer`. The query must leave out `postal_code`.
> No analysis needs it, so no role can read it.

### 8.3 `star_schema.dim_article`

Grain: 1 row per article. Primary key: `article_id`.

| # | Column | Type | Key | Product | Customer |
|---:|---|---|---|:---:|:---:|
| 1 | `article_id` | CHAR(10) | PK | ✅ | ✅ |
| 2 | `price_base` | DECIMAL(12,10) | | ✅ | ✅ |
| 3 | `product_code` | INT | | ✅ | ✅ |
| 4 | `prod_name` | VARCHAR(100) | | ✅ | ✅ |
| 5 | `product_type_no` | INT | | ✅ | ✅ |
| 6 | `prod_type_name` | VARCHAR(50) | | ✅ | ✅ |
| 7 | `product_group_name` | VARCHAR(50) | | ✅ | ✅ |
| 8 | `graphical_appearance_no` | INT | | ✅ | ✅ |
| 9 | `colour_group_code` | INT | | ✅ | ✅ |
| 10 | `perceived_colour_value_id` | INT | | ✅ | ✅ |
| 11 | `perceived_colour_master_id` | INT | | ✅ | ✅ |
| 12 | `department_no` | INT | | ✅ | ✅ |
| 13 | `garment_group_no` | INT | | ✅ | ✅ |
| 14 | `index_code` | CHAR(1) | | ✅ | ✅ |
| 15 | `index_group_no` | INT | | ✅ | ✅ |
| 16 | `section_no` | INT | | ✅ | ✅ |

### 8.4 `star_schema.dim_date`

Grain: 1 row per calendar day. Primary key: `date_key`.

| # | Column | Type | Key | Product | Customer |
|---:|---|---|---|:---:|:---:|
| 1 | `date_key` | INTEGER | PK | ✅ | ✅ |
| 2 | `full_date` | DATE | UNIQUE | ✅ | ✅ |
| 3 | `day` | SMALLINT | | ✅ | ✅ |
| 4 | `month` | SMALLINT | | ✅ | ✅ |
| 5 | `quarter` | SMALLINT | | ✅ | ✅ |
| 6 | `year` | SMALLINT | | ✅ | ✅ |
| 7 | `day_of_week` | SMALLINT | | ✅ | ✅ |

### 8.5 `star_schema.dim_sale_channel`

Grain: 1 row per channel (1 = Store, 2 = Online). Primary key: `sales_channel_id`.

| # | Column | Type | Key | Product | Customer |
|---:|---|---|---|:---:|:---:|
| 1 | `sales_channel_id` | SMALLINT | PK | ✅ | ✅ |
| 2 | `sales_channel_name` | VARCHAR(20) | | ✅ | ✅ |

---

## 9. Sensitive columns: where each one is visible

Every place in `star_schema` where each sensitive column appears, and who can see it there:

| Column | Object | Product | Customer |
|---|---|:---:|:---:|
| `customer_id` | `star_schema.fact_sales` | ❌ | ✅ |
| | `star_schema.dim_customer` | ❌ | ✅ |
| | `star_schema.vw_sales_detail` | ❌ | ✅ |
| | `star_schema.vw_customer_spending` | ❌ | ✅ |
| | `star_schema.vw_customer_product_group_preference` | ❌ | ✅ |
| | `star_schema.vw_customer_product_preference` | ❌ | ✅ |
| `age` / `age_group` | `star_schema.dim_customer` (`age`) | ❌ | ✅ |
| | `star_schema.vw_sales_detail` | ❌ | ✅ |
| | `star_schema.vw_customer_spending` | ❌ | ✅ |
| | `star_schema.vw_customer_spending_by_segment` (segment label only) | ❌ | ✅ |
| `club_member_status` | `star_schema.dim_customer`, `vw_sales_detail`, `vw_customer_spending`, `vw_customer_spending_by_segment` | ❌ | ✅ |
| `active`, `fn`, `fashion_news_frequency` | `star_schema.dim_customer`, `vw_sales_detail` | ❌ | ✅ |
| `postal_code` | `star_schema.dim_customer` (the only place it appears) | ❌ | ❌ |

What this gives each role:
- **Product analyst:** cannot see any customer-level column anywhere in `star_schema`. They only see customer **counts** (`purchasing_customers`, `unique_customers`, `active_customers`), which are aggregates.
- **Customer analyst:** sees the customer key and the analytic attributes, but never the location.
- **Nobody** can read `postal_code`.

---

## 10. Dashboards and the objects they read

| Dashboard (web portal / Power BI) | Objects | Product | Customer |
|---|---|:---:|:---:|
| Sales overview | `vw_sales_kpi`, `vw_monthly_sales`, `vw_sales_by_channel`, `vw_daily_customer_trend` | ✅ | ✅ |
| Product performance | `vw_product_performance`, `vw_product_group_performance`, `vw_product_type_performance` | ✅ | ❌ |
| Customer segments | `vw_customer_spending`, `vw_customer_spending_by_segment`, `vw_customer_product_group_preference`, `vw_customer_product_preference` | ❌ | ✅ |
| Sales explorer | `vw_sales_detail` | 🟡 no customer filters / columns | ✅ |
| Ad-hoc / Power BI model | `fact_sales`, `dim_article`, `dim_date`, `dim_sale_channel`, `dim_customer` | 🟡 no `customer_id`, no `dim_customer` | 🟡 no `postal_code` |

---

## 11. What no analyst can do

| Action | Blocked by |
|---|---|
| Read a column outside the column-level grants | Column grants on `vw_sales_detail`, `fact_sales`, `dim_customer` |
| `INSERT` / `UPDATE` / `DELETE` / `TRUNCATE` any table | No write privilege. Sessions are also read-only (`default_transaction_read_only = on`) |
| Create tables or views in `star_schema` | No `CREATE` on `star_schema` |
| `REFRESH MATERIALIZED VIEW` | Only the owner may refresh |
| Grant their rights to someone else | No `WITH GRANT OPTION` |
| Create roles or change a password other than their own | `NOCREATEROLE`, `NOSUPERUSER` |

---

## 12. Verification

Show the grants that are in effect now:

```sql
-- Object level: effective rights of each role on every star_schema table / view
-- (full = SELECT on the whole object, any_col = SELECT on at least one column)
SELECT c.relname AS object,
       has_table_privilege     ('hm_product_sales_analyst', c.oid, 'SELECT') AS product_full,
       has_any_column_privilege('hm_product_sales_analyst', c.oid, 'SELECT') AS product_any_col,
       has_table_privilege     ('hm_customer_analyst',      c.oid, 'SELECT') AS customer_full,
       has_any_column_privilege('hm_customer_analyst',      c.oid, 'SELECT') AS customer_any_col
FROM pg_class c
JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE n.nspname = 'star_schema' AND c.relkind IN ('r', 'v', 'm')
ORDER BY c.relname;

-- Column level (vw_sales_detail, fact_sales, dim_customer)
SELECT grantee, table_name, column_name, privilege_type
FROM information_schema.column_privileges
WHERE table_schema = 'star_schema'
  AND grantee IN ('hm_product_sales_analyst', 'hm_customer_analyst')
ORDER BY grantee, table_name, column_name;

-- Check one right for one login
SELECT has_column_privilege('hm_product_analyst_01', 'star_schema.fact_sales', 'customer_id', 'SELECT');  -- false
SELECT has_table_privilege ('hm_customer_analyst_01', 'star_schema.mv_sales_detail', 'SELECT');           -- false
```

The test cases are split by account. Each analyst file runs logged in as that analyst, so it shows exactly
what the analyst gets (including the read-only session):

| File | Logged in as | Test cases |
|---|---|---|
| [TESTCASE5_PRODUCT_ANALYST.sql](sql/tests/TESTCASE5_PRODUCT_ANALYST.sql) | `hm_product_analyst_01` | TC-P00 - TC-P14 |
| [TESTCASE5_CUSTOMER_ANALYST.sql](sql/tests/TESTCASE5_CUSTOMER_ANALYST.sql) | `hm_customer_analyst_01` | TC-C00 - TC-C13 |

Run them with:

```powershell
Get-Content sql\tests\TESTCASE5_PRODUCT_ANALYST.sql | docker exec -i hm-postgres-local sh -c "psql -U hm_product_analyst_01 -d hm_ecommerce_local -e 2>&1"
Get-Content sql\tests\TESTCASE5_CUSTOMER_ANALYST.sql | docker exec -i hm-postgres-local sh -c "psql -U hm_customer_analyst_01 -d hm_ecommerce_local -e 2>&1"
```
