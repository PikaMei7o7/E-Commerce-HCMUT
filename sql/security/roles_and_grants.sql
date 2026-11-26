-- ============================================================================
-- DATA ACCESS CONTROL (RBAC) FOR THE STAR SCHEMA AND MATERIALIZED VIEWS
--
-- Run order: after 03_views.sql, indexes.sql and material_view.sql (main.py step 6).
-- material_view.sql runs DROP MATERIALIZED VIEW ... CASCADE, which drops every vw_*
-- together with its grants, so this file MUST be re-run after it. main.py does that
-- automatically whenever MV_CREATE = 1.
-- REFRESH MATERIALIZED VIEW keeps grants: no re-run is needed after a refresh.
--
-- Idempotent: every run first revokes everything from the roles below, then grants
-- exactly what is listed here. Running it twice gives the same result.
--
-- Three object layers, three different rules:
--   vw_*              interface used by the web portal and Power BI -> SELECT per role
--   mv_*              pre-computed storage behind vw_*              -> no SELECT for anyone
--   fact_sales, dim_* star schema base tables (ad-hoc analysis)     -> column-level SELECT
-- A view runs with its owner's privileges (security_invoker is off by default), so SELECT
-- on vw_* is all an analyst needs: no right on mv_* or on the tables behind it.
--
-- Roles (all NOLOGIN group roles; the 2 analyst logins are members, see
-- src/security/create_login_users.py):
--   hm_analyst_base           CONNECT, USAGE on star_schema, the 4 "Sales overview" views
--   hm_product_sales_analyst  + product views, sales detail WITHOUT any customer column
--   hm_customer_analyst       + customer views, full sales detail, dim_customer without postal_code
-- The MVs are refreshed by the owner (DB_USER): there is no separate refresh role.
--
-- Requires the CREATEROLE attribute and ownership of the star_schema objects
-- (the DB_USER account of .env, which creates them in main.py).
-- ============================================================================


-- ----------------------------------------------------------------------------
-- 0. Group roles (created once, never dropped: dropping would break memberships)
-- ----------------------------------------------------------------------------
DO $$
DECLARE
    r TEXT;
BEGIN
    FOREACH r IN ARRAY ARRAY['hm_analyst_base', 'hm_product_sales_analyst', 'hm_customer_analyst']
    LOOP
        -- CREATE ROLE defaults to NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS.
        -- They are not repeated in ALTER ROLE: a non-superuser (Cloud SQL "postgres") may not
        -- even name SUPERUSER / REPLICATION / BYPASSRLS, and CREATEDB only if it has it itself.
        IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = r) THEN
            EXECUTE format('CREATE ROLE %I NOLOGIN', r);
        END IF;
        -- Group roles never log in.
        EXECUTE format('ALTER ROLE %I NOLOGIN', r);
    END LOOP;
END
$$;

-- Both analyst roles inherit the shared base role.
GRANT hm_analyst_base TO hm_product_sales_analyst, hm_customer_analyst;


-- ----------------------------------------------------------------------------
-- 1. Reset: remove every earlier grant (table- and column-level) before granting again
-- ----------------------------------------------------------------------------
-- REVOKE on a table also removes the column-level grants on it.
REVOKE ALL ON ALL TABLES IN SCHEMA star_schema
    FROM PUBLIC, hm_analyst_base, hm_product_sales_analyst, hm_customer_analyst;
REVOKE ALL ON SCHEMA star_schema
    FROM PUBLIC, hm_analyst_base, hm_product_sales_analyst, hm_customer_analyst;

-- Operational schema (public): customer, login_account (password_hash), transaction...
-- is never readable by analysts. PUBLIC has no table rights there by default; make it explicit.
REVOKE ALL ON ALL TABLES IN SCHEMA public
    FROM PUBLIC, hm_analyst_base, hm_product_sales_analyst, hm_customer_analyst;
REVOKE CREATE ON SCHEMA public FROM PUBLIC;  -- already the default since PostgreSQL 15


-- ----------------------------------------------------------------------------
-- 2. Database and schema access
-- ----------------------------------------------------------------------------
DO $$
BEGIN
    EXECUTE format('GRANT CONNECT ON DATABASE %I TO hm_analyst_base',
                   current_database());
END
$$;

-- USAGE only: no role may CREATE objects in star_schema.
GRANT USAGE ON SCHEMA star_schema TO hm_analyst_base;


-- ----------------------------------------------------------------------------
-- 3. hm_analyst_base: dashboard "Sales overview" (aggregates only, no customer row)
-- ----------------------------------------------------------------------------
GRANT SELECT ON
    star_schema.vw_sales_kpi,
    star_schema.vw_monthly_sales,
    star_schema.vw_sales_by_channel,
    star_schema.vw_daily_customer_trend
TO hm_analyst_base;


-- ----------------------------------------------------------------------------
-- 4. hm_product_sales_analyst: products and sales, no customer-level data
-- ----------------------------------------------------------------------------
-- Dashboard "Product performance"
GRANT SELECT ON
    star_schema.vw_product_performance,
    star_schema.vw_product_group_performance,
    star_schema.vw_product_type_performance
TO hm_product_sales_analyst;

-- Sales detail: every time / channel / product column, no customer column
-- (customer_id, age, age_group, club_member_status, active, fn, fashion_news_frequency).
GRANT SELECT (
    transaction_id, article_id,
    full_date, date_key, day, month, quarter, year, day_of_week,
    sales_channel_id, sales_channel_name,
    price_base, product_code, prod_name, product_type_no, prod_type_name, product_group_name,
    graphical_appearance_no, colour_group_code, perceived_colour_value_id,
    perceived_colour_master_id, department_no, garment_group_no, index_code,
    index_group_no, section_no,
    price, quantity, sales_revenue
) ON star_schema.vw_sales_detail TO hm_product_sales_analyst;

-- Base tables for ad-hoc / Power BI work: fact_sales without customer_id, no dim_customer.
GRANT SELECT (
    transaction_id, article_id, date_key, sales_channel_id, price, quantity, sales_revenue
) ON star_schema.fact_sales TO hm_product_sales_analyst;

GRANT SELECT ON
    star_schema.dim_article,
    star_schema.dim_date,
    star_schema.dim_sale_channel
TO hm_product_sales_analyst;


-- ----------------------------------------------------------------------------
-- 5. hm_customer_analyst: customers and their purchases, no product-performance views
-- ----------------------------------------------------------------------------
-- Dashboard "Customer segments" + preference views
GRANT SELECT ON
    star_schema.vw_customer_spending,
    star_schema.vw_customer_spending_by_segment,
    star_schema.vw_customer_product_group_preference,
    star_schema.vw_customer_product_preference
TO hm_customer_analyst;

-- Dashboard "Sales explorer": needs the customer columns of the detail view.
GRANT SELECT ON star_schema.vw_sales_detail TO hm_customer_analyst;

-- Base tables: postal_code (pseudonymised address) is not needed by any analysis.
GRANT SELECT (
    customer_id, age, fn, active, club_member_status, fashion_news_frequency
) ON star_schema.dim_customer TO hm_customer_analyst;

GRANT SELECT ON
    star_schema.fact_sales,
    star_schema.dim_article,
    star_schema.dim_date,
    star_schema.dim_sale_channel
TO hm_customer_analyst;


-- ----------------------------------------------------------------------------
-- 6. Summary (shown by psql / pgAdmin; main.py ignores it)
-- ----------------------------------------------------------------------------
SELECT grantee, table_name, string_agg(DISTINCT privilege_type, ', ') AS privileges
FROM information_schema.role_table_grants
WHERE table_schema = 'star_schema'
  AND grantee IN ('hm_analyst_base', 'hm_product_sales_analyst', 'hm_customer_analyst')
GROUP BY grantee, table_name
ORDER BY grantee, table_name;
