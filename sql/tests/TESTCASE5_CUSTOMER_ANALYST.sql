-- ============================================================================
-- TESTCASE 5B: CUSTOMER ANALYST  (login hm_customer_analyst_01)
-- ============================================================================
-- Runs LOGGED IN as the analyst account itself. PowerShell, from the project folder:
--
--   Get-Content sql\tests\TESTCASE5_CUSTOMER_ANALYST.sql | docker exec -i hm-postgres-local sh -c "psql -U hm_customer_analyst_01 -d hm_ecommerce_local -e 2>&1"
--
-- Output is grouped for 3 screenshots:
--   0. OVERVIEW   (TC-C00): what this account can read on every table / view / materialized view
--   1. CAN DO     (TC-C01 - TC-C06): every query returns rows
--   2. CANNOT DO  (TC-C07 - TC-C13): every query fails (permission denied / read-only)
-- Each test case prints "TC-Cxx  what -> expect ...", then the query (-e), then its result.
-- Nothing is changed in the database.

\set QUIET on
\pset footer off
\pset null '-'
\set VERBOSITY terse
\set QUIET off

\echo
\echo '#################### CUSTOMER ANALYST: OVERVIEW ####################'
\echo 'TC-C00  my privileges on every object  -> expect customer + overview views, dim_customer in part, no product views, no mv_*'
SELECT c.relname AS object, CASE c.relkind WHEN 'v' THEN 'view' WHEN 'm' THEN 'mat. view' ELSE 'table' END AS kind, CASE WHEN has_table_privilege(c.oid, 'SELECT') THEN 'all' WHEN has_any_column_privilege(c.oid, 'SELECT') THEN 'some columns' ELSE 'no' END AS can_read FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace WHERE n.nspname = 'star_schema' AND c.relkind IN ('r', 'v', 'm') ORDER BY c.relkind DESC, c.relname;

\echo
\echo '#################### CUSTOMER ANALYST: CAN DO ####################'
\echo 'TC-C01  who am I                          -> expect hm_customer_analyst_01, member of hm_analyst_base + hm_customer_analyst, read-only on'
SELECT current_user AS login, (SELECT string_agg(rolname, ', ') FROM pg_roles WHERE pg_has_role(current_user, oid, 'MEMBER') AND rolname <> current_user AND rolname LIKE 'hm\_%') AS member_of, current_setting('default_transaction_read_only') AS read_only;
\echo 'TC-C02  sales overview view               -> expect OK'
SELECT total_revenue, total_transactions FROM star_schema.vw_sales_kpi;
\echo 'TC-C03  customer segment view             -> expect OK'
SELECT age_group, club_member_status, purchasing_customers FROM star_schema.vw_customer_spending_by_segment ORDER BY 3 DESC LIMIT 2;
\echo 'TC-C04  sales detail incl. customer cols  -> expect OK'
SELECT age_group, COUNT(DISTINCT customer_id) AS customers FROM star_schema.vw_sales_detail GROUP BY 1 ORDER BY 1 LIMIT 2;
\echo 'TC-C05  dim_customer without postal_code  -> expect OK'
SELECT club_member_status, COUNT(*) AS customers FROM star_schema.dim_customer GROUP BY 1 ORDER BY 2 DESC LIMIT 2;
\echo 'TC-C06  fact_sales x dim_customer         -> expect OK'
SELECT c.age, COUNT(DISTINCT f.customer_id) AS customers FROM star_schema.fact_sales f JOIN star_schema.dim_customer c USING (customer_id) GROUP BY 1 ORDER BY 2 DESC LIMIT 2;

\echo
\echo '#################### CUSTOMER ANALYST: CANNOT DO ####################'
\echo 'TC-C07  product performance view          -> expect ERROR'
SELECT * FROM star_schema.vw_product_performance LIMIT 1;
\echo 'TC-C08  dim_customer.postal_code          -> expect ERROR'
SELECT postal_code FROM star_schema.dim_customer LIMIT 1;
\echo 'TC-C09  SELECT * on dim_customer          -> expect ERROR'
SELECT * FROM star_schema.dim_customer LIMIT 1;
\echo 'TC-C10  materialized view read directly   -> expect ERROR'
SELECT * FROM star_schema.mv_customer_spending LIMIT 1;
\echo 'TC-C11  operational schema (passwords)    -> expect ERROR'
SELECT * FROM public.login_account LIMIT 1;
\echo 'TC-C12  write in a read-only session      -> expect ERROR (read-only transaction)'
DELETE FROM star_schema.fact_sales WHERE false;
\echo 'TC-C13  write / DDL / refresh, read-only switched off -> expect ERROR on all 7 (permission denied)'
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
