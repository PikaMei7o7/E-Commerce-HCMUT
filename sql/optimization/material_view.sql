-- ============================================================================
-- MATERIALIZED VIEWS + INDEXES FOR THE ANALYTICS PORTAL
-- Run AFTER sql/schema/03_views.sql. Re-run sql/security/roles_and_grants.sql
-- afterwards, because DROP ... CASCADE also drops the vw_* wrapper views.
--
-- Each mv_* stores the full aggregation query from 03_views.sql (it does NOT
-- select from vw_*). The vw_* view is then replaced by a thin wrapper
-- SELECT * FROM mv_*, so the portal and Power BI keep using the same names.
-- If mv_* selected from vw_* instead, the wrapper would make mv_* read itself
-- and REFRESH MATERIALIZED VIEW would never load new data.
-- ============================================================================

-- 1. mv_sales_kpi
DROP MATERIALIZED VIEW IF EXISTS star_schema.mv_sales_kpi CASCADE;

CREATE MATERIALIZED VIEW star_schema.mv_sales_kpi AS
SELECT
    COALESCE(SUM(f.sales_revenue), 0) AS total_revenue,
    COALESCE(SUM(f.quantity), 0) AS total_units_sold,
    COUNT(DISTINCT f.transaction_id) AS total_transactions,
    COUNT(DISTINCT f.article_id) AS distinct_articles_sold,
    COUNT(DISTINCT f.customer_id) AS purchasing_customers,
    (SELECT COUNT(*) FROM star_schema.dim_customer) AS total_customers_in_dimension,
    SUM(f.sales_revenue) / NULLIF(COUNT(DISTINCT f.transaction_id), 0) AS average_order_value,
    SUM(f.sales_revenue) / NULLIF(COUNT(DISTINCT f.customer_id), 0) AS average_spending_per_purchasing_customer
FROM star_schema.fact_sales AS f
WITH DATA;

CREATE OR REPLACE VIEW star_schema.vw_sales_kpi AS
SELECT * FROM star_schema.mv_sales_kpi;

-- 2. mv_monthly_sales
DROP MATERIALIZED VIEW IF EXISTS star_schema.mv_monthly_sales CASCADE;

CREATE MATERIALIZED VIEW star_schema.mv_monthly_sales AS
SELECT
    d.year,
    d.month,
    MIN(d.full_date) AS month_start_date,
    SUM(f.sales_revenue) AS total_revenue,
    SUM(f.quantity) AS total_units_sold,
    COUNT(DISTINCT f.transaction_id) AS total_transactions,
    COUNT(DISTINCT f.customer_id) AS purchasing_customers,
    SUM(f.sales_revenue) / NULLIF(COUNT(DISTINCT f.transaction_id), 0) AS average_order_value
FROM star_schema.fact_sales AS f
JOIN star_schema.dim_date AS d ON d.date_key = f.date_key
GROUP BY d.year, d.month
WITH DATA;
CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_monthly_sales_ym
    ON star_schema.mv_monthly_sales (year, month);

CREATE OR REPLACE VIEW star_schema.vw_monthly_sales AS
SELECT * FROM star_schema.mv_monthly_sales;

-- 3. mv_daily_customer_trend
DROP MATERIALIZED VIEW IF EXISTS star_schema.mv_daily_customer_trend CASCADE;

CREATE MATERIALIZED VIEW star_schema.mv_daily_customer_trend AS
SELECT
    d.full_date,
    COUNT(DISTINCT f.customer_id) AS active_customers,
    SUM(f.quantity) AS total_units_sold,
    SUM(f.sales_revenue) AS total_revenue,
    SUM(f.quantity)::NUMERIC / NULLIF(COUNT(DISTINCT f.customer_id), 0) AS avg_units_per_customer,
    SUM(f.sales_revenue) / NULLIF(COUNT(DISTINCT f.customer_id), 0) AS avg_spending_per_customer
FROM star_schema.fact_sales AS f
JOIN star_schema.dim_date AS d ON d.date_key = f.date_key
GROUP BY d.full_date
WITH DATA;
CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_daily_customer_trend_date
    ON star_schema.mv_daily_customer_trend (full_date);

CREATE OR REPLACE VIEW star_schema.vw_daily_customer_trend AS
SELECT * FROM star_schema.mv_daily_customer_trend;

-- 4. mv_sales_by_channel
DROP MATERIALIZED VIEW IF EXISTS star_schema.mv_sales_by_channel CASCADE;

CREATE MATERIALIZED VIEW star_schema.mv_sales_by_channel AS
SELECT
    f.sales_channel_id,
    CASE f.sales_channel_id
        WHEN 1 THEN 'Store'
        WHEN 2 THEN 'Online'
        ELSE 'Unknown'
    END AS sales_channel_name,
    SUM(f.sales_revenue) AS total_revenue,
    SUM(f.quantity) AS total_units_sold,
    COUNT(DISTINCT f.transaction_id) AS total_transactions,
    COUNT(DISTINCT f.customer_id) AS unique_customers,
    SUM(f.sales_revenue) / NULLIF(COUNT(DISTINCT f.transaction_id), 0) AS average_order_value
FROM star_schema.fact_sales AS f
GROUP BY f.sales_channel_id
WITH DATA;
CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_sales_by_channel_id
    ON star_schema.mv_sales_by_channel (sales_channel_id);

CREATE OR REPLACE VIEW star_schema.vw_sales_by_channel AS
SELECT * FROM star_schema.mv_sales_by_channel;

-- 5. mv_product_performance
DROP MATERIALIZED VIEW IF EXISTS star_schema.mv_product_performance CASCADE;

CREATE MATERIALIZED VIEW star_schema.mv_product_performance AS
SELECT
    a.product_code,
    a.prod_name,
    a.product_type_no,
    a.prod_type_name,
    a.product_group_name,
    SUM(f.quantity) AS total_units_sold,
    SUM(f.sales_revenue) AS total_revenue,
    COUNT(DISTINCT f.transaction_id) AS total_transactions,
    COUNT(DISTINCT f.customer_id) AS unique_customers,
    SUM(f.sales_revenue) / NULLIF(SUM(f.quantity), 0) AS revenue_per_unit
FROM star_schema.fact_sales AS f
JOIN star_schema.dim_article AS a ON a.article_id = f.article_id
GROUP BY
    a.product_code, a.prod_name, a.product_type_no,
    a.prod_type_name, a.product_group_name
WITH DATA;
CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_product_perf_code
    ON star_schema.mv_product_performance (product_code);
CREATE INDEX IF NOT EXISTS idx_mv_product_perf_rev
    ON star_schema.mv_product_performance (total_revenue DESC NULLS LAST);
CREATE INDEX IF NOT EXISTS idx_mv_product_perf_units
    ON star_schema.mv_product_performance (total_units_sold DESC NULLS LAST);

CREATE OR REPLACE VIEW star_schema.vw_product_performance AS
SELECT * FROM star_schema.mv_product_performance;

-- 6. mv_product_group_performance
DROP MATERIALIZED VIEW IF EXISTS star_schema.mv_product_group_performance CASCADE;

CREATE MATERIALIZED VIEW star_schema.mv_product_group_performance AS
SELECT
    a.product_group_name,
    SUM(f.quantity) AS total_units_sold,
    SUM(f.sales_revenue) AS total_revenue,
    COUNT(DISTINCT f.transaction_id) AS total_transactions,
    COUNT(DISTINCT f.customer_id) AS unique_customers,
    SUM(f.sales_revenue) / NULLIF(SUM(f.quantity), 0) AS revenue_per_unit
FROM star_schema.fact_sales AS f
JOIN star_schema.dim_article AS a ON a.article_id = f.article_id
GROUP BY a.product_group_name
WITH DATA;
CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_product_group_name
    ON star_schema.mv_product_group_performance (product_group_name);

CREATE OR REPLACE VIEW star_schema.vw_product_group_performance AS
SELECT * FROM star_schema.mv_product_group_performance;

-- 7. mv_product_type_performance
DROP MATERIALIZED VIEW IF EXISTS star_schema.mv_product_type_performance CASCADE;

CREATE MATERIALIZED VIEW star_schema.mv_product_type_performance AS
SELECT
    a.product_type_no,
    a.prod_type_name AS product_type_name,
    SUM(f.quantity) AS total_units_sold,
    SUM(f.sales_revenue) AS total_revenue,
    COUNT(DISTINCT f.transaction_id) AS total_transactions,
    COUNT(DISTINCT f.article_id) AS distinct_articles_sold,
    COUNT(DISTINCT f.customer_id) AS unique_customers
FROM star_schema.fact_sales AS f
JOIN star_schema.dim_article AS a ON a.article_id = f.article_id
GROUP BY a.product_type_no, a.prod_type_name
WITH DATA;
CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_product_type_no
    ON star_schema.mv_product_type_performance (product_type_no);

CREATE OR REPLACE VIEW star_schema.vw_product_type_performance AS
SELECT * FROM star_schema.mv_product_type_performance;

-- 8. mv_customer_spending
DROP MATERIALIZED VIEW IF EXISTS star_schema.mv_customer_spending CASCADE;

CREATE MATERIALIZED VIEW star_schema.mv_customer_spending AS
SELECT
    c.customer_id,
    c.age,
    CASE
        WHEN c.age IS NULL THEN 'Unknown'
        WHEN c.age < 20 THEN 'Under 20'
        WHEN c.age BETWEEN 20 AND 29 THEN '20-29'
        WHEN c.age BETWEEN 30 AND 39 THEN '30-39'
        WHEN c.age BETWEEN 40 AND 49 THEN '40-49'
        WHEN c.age BETWEEN 50 AND 59 THEN '50-59'
        ELSE '60+'
    END AS age_group,
    COALESCE(c.club_member_status, 'UNKNOWN') AS club_member_status,
    COUNT(DISTINCT f.transaction_id) AS purchase_frequency,
    SUM(f.quantity) AS total_units_purchased,
    SUM(f.sales_revenue) AS total_spending,
    SUM(f.sales_revenue) / NULLIF(COUNT(DISTINCT f.transaction_id), 0) AS average_order_value
FROM star_schema.dim_customer AS c
JOIN star_schema.fact_sales AS f ON f.customer_id = c.customer_id
GROUP BY c.customer_id, c.age, c.club_member_status
WITH DATA;
CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_customer_spending_id
    ON star_schema.mv_customer_spending (customer_id);
CREATE INDEX IF NOT EXISTS idx_mv_customer_spending_top
    ON star_schema.mv_customer_spending (total_spending DESC NULLS LAST);
CREATE INDEX IF NOT EXISTS idx_mv_customer_spending_freq
    ON star_schema.mv_customer_spending (purchase_frequency);

CREATE OR REPLACE VIEW star_schema.vw_customer_spending AS
SELECT * FROM star_schema.mv_customer_spending;

-- 9. mv_customer_spending_by_segment
DROP MATERIALIZED VIEW IF EXISTS star_schema.mv_customer_spending_by_segment CASCADE;

CREATE MATERIALIZED VIEW star_schema.mv_customer_spending_by_segment AS
SELECT
    CASE
        WHEN c.age IS NULL THEN 'Unknown'
        WHEN c.age < 20 THEN 'Under 20'
        WHEN c.age BETWEEN 20 AND 29 THEN '20-29'
        WHEN c.age BETWEEN 30 AND 39 THEN '30-39'
        WHEN c.age BETWEEN 40 AND 49 THEN '40-49'
        WHEN c.age BETWEEN 50 AND 59 THEN '50-59'
        ELSE '60+'
    END AS age_group,
    COALESCE(c.club_member_status, 'UNKNOWN') AS club_member_status,
    COUNT(DISTINCT c.customer_id) AS purchasing_customers,
    SUM(f.quantity) AS total_units_sold,
    SUM(f.sales_revenue) AS total_revenue,
    SUM(f.sales_revenue) / NULLIF(COUNT(DISTINCT c.customer_id), 0) AS average_revenue_per_customer
FROM star_schema.fact_sales AS f
JOIN star_schema.dim_customer AS c ON c.customer_id = f.customer_id
GROUP BY 1, 2
WITH DATA;
CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_customer_seg_pk
    ON star_schema.mv_customer_spending_by_segment (age_group, club_member_status);

CREATE OR REPLACE VIEW star_schema.vw_customer_spending_by_segment AS
SELECT * FROM star_schema.mv_customer_spending_by_segment;

-- 10. mv_sales_detail
DROP MATERIALIZED VIEW IF EXISTS star_schema.mv_sales_detail CASCADE;

CREATE MATERIALIZED VIEW star_schema.mv_sales_detail AS
SELECT
    f.transaction_id,
    f.customer_id,
    f.article_id,
    d.full_date,
    d.date_key,
    d.day,
    d.month,
    d.quarter,
    d.year,
    d.day_of_week,
    f.sales_channel_id,
    CASE f.sales_channel_id
        WHEN 1 THEN 'Store'
        WHEN 2 THEN 'Online'
        ELSE 'Unknown'
    END AS sales_channel_name,
    a.price_base,
    a.product_code,
    a.prod_name,
    a.product_type_no,
    a.prod_type_name,
    a.product_group_name,
    a.graphical_appearance_no,
    a.colour_group_code,
    a.perceived_colour_value_id,
    a.perceived_colour_master_id,
    a.department_no,
    a.garment_group_no,
    a.index_code,
    a.index_group_no,
    a.section_no,
    c.age,
    CASE
        WHEN c.age IS NULL THEN 'Unknown'
        WHEN c.age < 20 THEN 'Under 20'
        WHEN c.age BETWEEN 20 AND 29 THEN '20-29'
        WHEN c.age BETWEEN 30 AND 39 THEN '30-39'
        WHEN c.age BETWEEN 40 AND 49 THEN '40-49'
        WHEN c.age BETWEEN 50 AND 59 THEN '50-59'
        ELSE '60+'
    END AS age_group,
    COALESCE(c.club_member_status, 'UNKNOWN') AS club_member_status,
    c.active,
    c.fn,
    c.fashion_news_frequency,
    f.price,
    f.quantity,
    f.sales_revenue
FROM star_schema.fact_sales AS f
JOIN star_schema.dim_date AS d ON d.date_key = f.date_key
JOIN star_schema.dim_article AS a ON a.article_id = f.article_id
JOIN star_schema.dim_customer AS c ON c.customer_id = f.customer_id
WITH DATA;
CREATE INDEX IF NOT EXISTS idx_mv_sales_detail_year_channel
    ON star_schema.mv_sales_detail (year, sales_channel_name);
CREATE INDEX IF NOT EXISTS idx_mv_sales_detail_customer_seg
    ON star_schema.mv_sales_detail (age_group, club_member_status);
CREATE INDEX IF NOT EXISTS idx_mv_sales_detail_group_name
    ON star_schema.mv_sales_detail (product_group_name);
CREATE INDEX IF NOT EXISTS idx_mv_sales_detail_explorer_all
    ON star_schema.mv_sales_detail (year, sales_channel_name, age_group, club_member_status, product_group_name);
CREATE INDEX IF NOT EXISTS idx_mv_sales_detail_dim_group
    ON star_schema.mv_sales_detail (sales_revenue DESC)
    INCLUDE (transaction_id, customer_id, quantity, year, sales_channel_name, age_group, club_member_status, product_group_name);
CREATE INDEX IF NOT EXISTS idx_mv_sales_detail_table_perf
    ON star_schema.mv_sales_detail (year, month, sales_channel_name, product_group_name, age_group, club_member_status);

CREATE OR REPLACE VIEW star_schema.vw_sales_detail AS
SELECT * FROM star_schema.mv_sales_detail;

-- 10b. mv_sales_detail_2018 / 2019 / 2020 (tạo trực tiếp từ mv_sales_detail)
DROP MATERIALIZED VIEW IF EXISTS star_schema.mv_sales_detail_2018 CASCADE;
CREATE MATERIALIZED VIEW star_schema.mv_sales_detail_2018 AS
SELECT *
FROM star_schema.mv_sales_detail
WHERE year = 2018
WITH DATA;

CREATE INDEX IF NOT EXISTS idx_mv_sales_2018_filter
    ON star_schema.mv_sales_detail_2018 (sales_channel_name, age_group, club_member_status, product_group_name);
CREATE INDEX IF NOT EXISTS idx_mv_sales_2018_month
    ON star_schema.mv_sales_detail_2018 (month);

DROP MATERIALIZED VIEW IF EXISTS star_schema.mv_sales_detail_2019 CASCADE;
CREATE MATERIALIZED VIEW star_schema.mv_sales_detail_2019 AS
SELECT *
FROM star_schema.mv_sales_detail
WHERE year = 2019
WITH DATA;

CREATE INDEX IF NOT EXISTS idx_mv_sales_2019_filter
    ON star_schema.mv_sales_detail_2019 (sales_channel_name, age_group, club_member_status, product_group_name);
CREATE INDEX IF NOT EXISTS idx_mv_sales_2019_month
    ON star_schema.mv_sales_detail_2019 (month);

DROP MATERIALIZED VIEW IF EXISTS star_schema.mv_sales_detail_2020 CASCADE;
CREATE MATERIALIZED VIEW star_schema.mv_sales_detail_2020 AS
SELECT *
FROM star_schema.mv_sales_detail
WHERE year = 2020
WITH DATA;

CREATE INDEX IF NOT EXISTS idx_mv_sales_2020_filter
    ON star_schema.mv_sales_detail_2020 (sales_channel_name, age_group, club_member_status, product_group_name);
CREATE INDEX IF NOT EXISTS idx_mv_sales_2020_month
    ON star_schema.mv_sales_detail_2020 (month);
-- 11. mv_customer_product_group_preference
DROP MATERIALIZED VIEW IF EXISTS star_schema.mv_customer_product_group_preference CASCADE;

CREATE MATERIALIZED VIEW star_schema.mv_customer_product_group_preference AS
SELECT
    f.customer_id,
    a.product_group_name,
    SUM(f.quantity) AS total_quantity_purchased,
    SUM(f.sales_revenue) AS total_spending_in_group,
    COUNT(DISTINCT f.transaction_id) AS transactions_in_group
FROM star_schema.fact_sales AS f
JOIN star_schema.dim_article AS a ON a.article_id = f.article_id
GROUP BY f.customer_id, a.product_group_name
WITH DATA;
CREATE INDEX IF NOT EXISTS idx_mv_cust_prod_grp_pref_cust
    ON star_schema.mv_customer_product_group_preference (customer_id);
CREATE INDEX IF NOT EXISTS idx_mv_cust_prod_grp_pref_spend
    ON star_schema.mv_customer_product_group_preference (total_spending_in_group DESC NULLS LAST);

CREATE OR REPLACE VIEW star_schema.vw_customer_product_group_preference AS
SELECT * FROM star_schema.mv_customer_product_group_preference;

-- 12. mv_customer_product_preference
DROP MATERIALIZED VIEW IF EXISTS star_schema.mv_customer_product_preference CASCADE;

CREATE MATERIALIZED VIEW star_schema.mv_customer_product_preference AS
SELECT
    f.customer_id,
    a.article_id,
    a.product_code,
    a.prod_name,
    a.product_type_no,
    a.prod_type_name AS product_type_name,
    a.product_group_name,
    SUM(f.quantity) AS total_quantity_purchased,
    SUM(f.sales_revenue) AS total_spending_on_product,
    COUNT(DISTINCT f.transaction_id) AS purchase_frequency
FROM star_schema.fact_sales AS f
JOIN star_schema.dim_article AS a ON a.article_id = f.article_id
GROUP BY
    f.customer_id, a.article_id, a.product_code, a.prod_name,
    a.product_type_no, a.prod_type_name, a.product_group_name
WITH DATA;
CREATE INDEX IF NOT EXISTS idx_mv_cust_prod_pref_article
    ON star_schema.mv_customer_product_preference (article_id);

CREATE OR REPLACE VIEW star_schema.vw_customer_product_preference AS
SELECT * FROM star_schema.mv_customer_product_preference;

-------------------------------------------------------------------------------
-- 13. UPDATE PLANNER STATISTICS
-------------------------------------------------------------------------------
ANALYZE star_schema.fact_sales;
ANALYZE star_schema.dim_article;
ANALYZE star_schema.dim_customer;
ANALYZE star_schema.dim_date;
ANALYZE star_schema.mv_sales_kpi;
ANALYZE star_schema.mv_monthly_sales;
ANALYZE star_schema.mv_daily_customer_trend;
ANALYZE star_schema.mv_sales_by_channel;
ANALYZE star_schema.mv_product_performance;
ANALYZE star_schema.mv_product_group_performance;
ANALYZE star_schema.mv_product_type_performance;
ANALYZE star_schema.mv_customer_spending;
ANALYZE star_schema.mv_customer_spending_by_segment;
ANALYZE star_schema.mv_sales_detail;
ANALYZE star_schema.mv_customer_product_group_preference;
ANALYZE star_schema.mv_customer_product_preference;


-------------------------------------------------------------------------------
-- 14. OPTIONAL / ADVANCED: GIN TRIGRAM INDEXES
-------------------------------------------------------------------------------
-------------------------------------------------------------------------------
/*
--  extension
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Tạo GIN Index cho product_group_name
CREATE INDEX IF NOT EXISTS idx_mv_sales_detail_group_gin
    ON star_schema.mv_sales_detail USING gin (product_group_name gin_trgm_ops);

-- Tạo GIN Index cho prod_name
CREATE INDEX IF NOT EXISTS idx_mv_sales_detail_prodname_gin
    ON star_schema.mv_sales_detail USING gin (prod_name gin_trgm_ops);

-- (Drop)
-- DROP INDEX IF EXISTS star_schema.idx_mv_sales_detail_group_gin;
-- DROP INDEX IF EXISTS star_schema.idx_mv_sales_detail_prodname_gin;
*/
