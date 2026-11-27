-- ============================================================================
-- TESTCASE 5A: PRODUCT / SALES ANALYST  (login hm_product_analyst_01)
-- ============================================================================
-- Runs LOGGED IN as the analyst account itself. PowerShell, from the project folder:
--
--   Get-Content sql\tests\TESTCASE5_PRODUCT_ANALYST.sql | docker exec -i hm-postgres-local sh -c "psql -U hm_product_analyst_01 -d hm_ecommerce_local -e 2>&1"
--
-- Output is grouped for 3 screenshots:
--   0. OVERVIEW   (TC-P00): what this account can read on every table / view / materialized view
--   1. CAN DO     (TC-P01 - TC-P05): every query returns rows
--   2. CANNOT DO  (TC-P06 - TC-P14): every query fails (permission denied / read-only)
-- Each test case prints "TC-Pxx  what -> expect ...", then the query (-e), then its result.
-- Nothing is changed in the database.

\set QUIET on
\pset footer off
\pset null '-'
\set VERBOSITY terse
\set QUIET off

\echo
\echo '#################### PRODUCT ANALYST: OVERVIEW ####################'
\echo 'TC-P00  my privileges on every object  -> expect product + overview views, sales detail and fact_sales in part, no customer views, no mv_*'
SELECT c.relname AS object, CASE c.relkind WHEN 'v' THEN 'view' WHEN 'm' THEN 'mat. view' ELSE 'table' END AS kind, CASE WHEN has_table_privilege(c.oid, 'SELECT') THEN 'all' WHEN has_any_column_privilege(c.oid, 'SELECT') THEN 'some columns' ELSE 'no' END AS can_read FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace WHERE n.nspname = 'star_schema' AND c.relkind IN ('r', 'v', 'm') ORDER BY c.relkind DESC, c.relname;

\echo
\echo '#################### PRODUCT ANALYST: CAN DO ####################'
\echo 'TC-P01  who am I                          -> expect hm_product_analyst_01, member of hm_analyst_base + hm_product_sales_analyst, read-only on'
SELECT current_user AS login, (SELECT string_agg(rolname, ', ') FROM pg_roles WHERE pg_has_role(current_user, oid, 'MEMBER') AND rolname <> current_user AND rolname LIKE 'hm\_%') AS member_of, current_setting('default_transaction_read_only') AS read_only;
\echo 'TC-P02  sales overview view               -> expect OK'
SELECT total_revenue, total_transactions FROM star_schema.vw_sales_kpi;
\echo 'TC-P03  product performance view          -> expect OK'
SELECT prod_name, total_revenue FROM star_schema.vw_product_performance ORDER BY total_revenue DESC LIMIT 2;
\echo 'TC-P04  sales detail, product columns     -> expect OK'
SELECT year, sales_channel_name, SUM(sales_revenue) AS revenue FROM star_schema.vw_sales_detail GROUP BY 1, 2 ORDER BY 1, 2 LIMIT 2;
\echo 'TC-P05  fact_sales x dim_article          -> expect OK'
SELECT a.product_group_name, SUM(f.sales_revenue) AS revenue FROM star_schema.fact_sales f JOIN star_schema.dim_article a USING (article_id) GROUP BY 1 ORDER BY 2 DESC LIMIT 2;

\echo
\echo '#################### PRODUCT ANALYST: CANNOT DO ####################'
\echo 'TC-P06  customer column of sales detail   -> expect ERROR'
SELECT customer_id FROM star_schema.vw_sales_detail LIMIT 1;
\echo 'TC-P07  SELECT * on sales detail          -> expect ERROR'
SELECT * FROM star_schema.vw_sales_detail LIMIT 1;
\echo 'TC-P08  customer view                     -> expect ERROR'
SELECT * FROM star_schema.vw_customer_spending LIMIT 1;
\echo 'TC-P09  fact_sales.customer_id            -> expect ERROR'
SELECT customer_id FROM star_schema.fact_sales LIMIT 1;
\echo 'TC-P10  dim_customer                      -> expect ERROR'
SELECT * FROM star_schema.dim_customer LIMIT 1;
\echo 'TC-P11  materialized view read directly   -> expect ERROR'
SELECT * FROM star_schema.mv_product_performance LIMIT 1;
\echo 'TC-P12  operational schema (passwords)    -> expect ERROR'
SELECT * FROM public.login_account LIMIT 1;
\echo 'TC-P13  write in a read-only session      -> expect ERROR (read-only transaction)'
DELETE FROM star_schema.fact_sales WHERE false;
\echo 'TC-P14  write / DDL / refresh, read-only switched off -> expect ERROR on all 7 (permission denied)'
\set QUIET on
SET default_transaction_read_only = off;
\set QUIET off
INSERT INTO star_schema.dim_sale_channel VALUES (9, 'Test');
UPDATE star_schema.dim_article SET prod_name = prod_name WHERE false;
DELETE FROM star_schema.fact_sales WHERE false;
TRUNCATE star_schema.fact_sales;
CREATE TABLE star_schema.tc_should_fail (x INT);
DROP VIEW star_schema.vw_sales_kpi;
REFRESH MATERIALIZED VIEW star_schema.mv_sales_kpi;
\set QUIET on
RESET default_transaction_read_only;
\set QUIET off
