-- ============================================================================
-- TESTCASE 4: SALES EXPLORER
-- ============================================================================

-- BEFORE:
-- Baseline = original JOIN query of vw_sales_detail from sql/schema/03_views.sql.
-- (vw_sales_detail itself now only forwards to mv_sales_detail, so it is not a baseline.)
EXPLAIN ANALYZE
WITH v AS (
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
)
SELECT 
    v.year,
    v.month,
    v.sales_channel_name,
    v.age_group,
    v.product_group_name,
    SUM(v.sales_revenue) AS total_revenue,
    SUM(v.quantity) AS total_units_sold,
    COUNT(DISTINCT v.transaction_id) AS total_transactions
FROM v
WHERE v.year = 2018
  AND v.sales_channel_name = 'Online'
  AND v.age_group = '20-29'
  AND v.product_group_name ILIKE '%Garment%'
GROUP BY v.year, v.month, v.sales_channel_name, v.age_group, v.product_group_name;


-- AFTER:
EXPLAIN ANALYZE
SELECT 
    year,
    month,
    sales_channel_name,
    age_group,
    product_group_name,
    SUM(sales_revenue) AS total_revenue,
    SUM(quantity) AS total_units_sold,
    COUNT(DISTINCT transaction_id) AS total_transactions
FROM star_schema.mv_sales_detail
WHERE year = 2018
  AND sales_channel_name = 'Online'
  AND age_group = '20-29'
  AND product_group_name ILIKE '%Garment%'
GROUP BY year, month, sales_channel_name, age_group, product_group_name;
