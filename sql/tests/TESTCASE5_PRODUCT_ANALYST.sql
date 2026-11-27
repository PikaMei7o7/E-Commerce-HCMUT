-- TESTCASE 5A: PRODUCT / SALES ANALYST  (login hm_product_analyst_01)
-- Pure SQL: no psql commands (\echo, \set, \pset), so it runs in psql, pgAdmin,
-- DBeaver or Cloud SQL Studio. Log in AS the analyst account, then run the whole file.
--
--   Part 0  OVERVIEW   (TC-P00)          : result grid of my privileges on every object
--   Part 1  CAN DO     (TC-P01 - TC-P05) : each query returns rows; column test_case names it
--   Part 2  CANNOT DO  (TC-P06 - TC-P14) : each statement must fail; one line per test is
--                                          printed as a NOTICE (psql output, pgAdmin
--                                          "Messages" tab, DBeaver "Output")
--
-- Nothing is changed in the database: in Part 2 every statement runs inside a
-- sub-transaction that is always rolled back, even if a permission were wrong.
-- If any Part 2 test fails, the script ends with an ERROR listing the failed tests.

-- PART 0. OVERVIEW

-- TC-P00  my privileges on every object
--         expect: product + overview views, sales detail and fact_sales in part,
--                 no customer views, no mv_*
SELECT 'TC-P00' AS test_case,
       c.relname AS object,
       CASE c.relkind WHEN 'v' THEN 'view' WHEN 'm' THEN 'mat. view' ELSE 'table' END AS kind,
       CASE WHEN has_table_privilege(c.oid, 'SELECT') THEN 'all'
            WHEN has_any_column_privilege(c.oid, 'SELECT') THEN 'some columns'
            ELSE 'no' END AS can_read
FROM pg_class c
JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE n.nspname = 'star_schema' AND c.relkind IN ('r', 'v', 'm')
ORDER BY c.relkind DESC, c.relname;

-- PART 1. CAN DO: every query returns rows

-- TC-P01  who am I -> expect hm_product_analyst_01, member of hm_analyst_base + hm_product_sales_analyst, read-only on
SELECT 'TC-P01' AS test_case,
       current_user AS login,
       (SELECT string_agg(rolname, ', ' ORDER BY rolname)
        FROM pg_roles
        WHERE pg_has_role(current_user, oid, 'MEMBER')
          AND rolname <> current_user
          AND rolname LIKE 'hm\_%') AS member_of,
       current_setting('default_transaction_read_only') AS read_only;

-- TC-P02  sales overview view -> expect OK
SELECT 'TC-P02' AS test_case, total_revenue, total_transactions
FROM star_schema.vw_sales_kpi;

-- TC-P03  product performance view -> expect OK
SELECT 'TC-P03' AS test_case, prod_name, total_revenue
FROM star_schema.vw_product_performance
ORDER BY total_revenue DESC
LIMIT 2;

-- TC-P04  sales detail, product columns only -> expect OK
SELECT 'TC-P04' AS test_case, year, sales_channel_name, SUM(sales_revenue) AS revenue
FROM star_schema.vw_sales_detail
GROUP BY year, sales_channel_name
ORDER BY year, sales_channel_name
LIMIT 2;

-- TC-P05  fact_sales joined with dim_article -> expect OK
SELECT 'TC-P05' AS test_case, a.product_group_name, SUM(f.sales_revenue) AS revenue
FROM star_schema.fact_sales f
JOIN star_schema.dim_article a USING (article_id)
GROUP BY a.product_group_name
ORDER BY revenue DESC
LIMIT 2;

-- PART 2a. CANNOT DO, in the read-only session (TC-P06 - TC-P13)

-- Expected SQLSTATE: 42501 = permission denied, 25006 = read-only transaction.
DO $$
DECLARE
    t      record;
    failed text[] := '{}';
BEGIN
    FOR t IN
        SELECT * FROM (VALUES
            ('TC-P06', 'customer column of sales detail', '42501', 'SELECT customer_id FROM star_schema.vw_sales_detail LIMIT 1'),
            ('TC-P07', 'SELECT * on sales detail',        '42501', 'SELECT * FROM star_schema.vw_sales_detail LIMIT 1'),
            ('TC-P08', 'customer view',                   '42501', 'SELECT * FROM star_schema.vw_customer_spending LIMIT 1'),
            ('TC-P09', 'fact_sales.customer_id',          '42501', 'SELECT customer_id FROM star_schema.fact_sales LIMIT 1'),
            ('TC-P10', 'dim_customer',                    '42501', 'SELECT * FROM star_schema.dim_customer LIMIT 1'),
            ('TC-P11', 'materialized view read directly', '42501', 'SELECT * FROM star_schema.mv_product_performance LIMIT 1'),
            ('TC-P12', 'operational schema (passwords)',  '42501', 'SELECT * FROM public.login_account LIMIT 1'),
            ('TC-P13', 'write in a read-only session',    '25006', 'DELETE FROM star_schema.fact_sales WHERE false')
        ) AS v(id, what, expected, stmt)
    LOOP
        BEGIN
            EXECUTE t.stmt;
            -- Reaching this line means the statement was NOT blocked: roll it back.
            RAISE EXCEPTION 'not blocked' USING ERRCODE = 'P0001';
        EXCEPTION WHEN OTHERS THEN
            IF SQLSTATE = t.expected THEN
                RAISE NOTICE '% PASS  %  -> % (%)', t.id, t.what, SQLERRM, SQLSTATE;
            ELSIF SQLERRM = 'not blocked' THEN
                RAISE NOTICE '% FAIL  %  -> statement was NOT blocked', t.id, t.what;
                failed := failed || t.id;
            ELSE
                RAISE NOTICE '% FAIL  %  -> unexpected error: % (%), expected %',
                             t.id, t.what, SQLERRM, SQLSTATE, t.expected;
                failed := failed || t.id;
            END IF;
        END;
    END LOOP;

    IF cardinality(failed) > 0 THEN
        RAISE EXCEPTION 'Part 2a: % test(s) failed: %', cardinality(failed), array_to_string(failed, ', ');
    END IF;
    RAISE NOTICE 'Part 2a: all 8 tests passed';
END
$$;

-- PART 2b. CANNOT DO, with read-only switched off (TC-P14)

-- Switch read-only off for the session: every write must now fail because of the
-- missing PERMISSION (42501), not because the session is read-only.
SET default_transaction_read_only = off;

DO $$
DECLARE
    t      record;
    failed text[] := '{}';
BEGIN
    FOR t IN
        SELECT * FROM (VALUES
            ('TC-P14a', 'INSERT',       'INSERT INTO star_schema.dim_sale_channel VALUES (9, ''Test'')'),
            ('TC-P14b', 'UPDATE',       'UPDATE star_schema.dim_article SET prod_name = prod_name WHERE false'),
            ('TC-P14c', 'DELETE',       'DELETE FROM star_schema.fact_sales WHERE false'),
            ('TC-P14d', 'TRUNCATE',     'TRUNCATE star_schema.fact_sales'),
            ('TC-P14e', 'CREATE TABLE', 'CREATE TABLE star_schema.tc_should_fail (x INT)'),
            ('TC-P14f', 'DROP VIEW',    'DROP VIEW star_schema.vw_sales_kpi'),
            ('TC-P14g', 'REFRESH MV',   'REFRESH MATERIALIZED VIEW star_schema.mv_sales_kpi')
        ) AS v(id, what, stmt)
    LOOP
        BEGIN
            EXECUTE t.stmt;
            RAISE EXCEPTION 'not blocked' USING ERRCODE = 'P0001';
        EXCEPTION WHEN OTHERS THEN
            IF SQLSTATE = '42501' THEN
                RAISE NOTICE '% PASS  %  -> %', t.id, t.what, SQLERRM;
            ELSIF SQLSTATE = '25006' THEN
                -- The tool ran the whole file in one transaction, so SET above had no effect.
                RAISE NOTICE '% FAIL  %  -> blocked only by read-only mode; run this part in autocommit mode',
                             t.id, t.what;
                failed := failed || t.id;
            ELSIF SQLERRM = 'not blocked' THEN
                RAISE NOTICE '% FAIL  %  -> statement was NOT blocked', t.id, t.what;
                failed := failed || t.id;
            ELSE
                RAISE NOTICE '% FAIL  %  -> unexpected error: % (%)', t.id, t.what, SQLERRM, SQLSTATE;
                failed := failed || t.id;
            END IF;
        END;
    END LOOP;

    IF cardinality(failed) > 0 THEN
        RAISE EXCEPTION 'Part 2b: % test(s) failed: %', cardinality(failed), array_to_string(failed, ', ');
    END IF;
    RAISE NOTICE 'Part 2b: all 7 tests passed';
END
$$;

RESET default_transaction_read_only;
