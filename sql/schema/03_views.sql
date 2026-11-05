-- Power BI analytics views
-- Run this entire file in PostgreSQL / pgAdmin Query Tool.
-- Creates/replaces views only; does not modify source tables or data.


-- 1. vw_sales_detail

-- Detail-level view for flexible Power BI filtering.
-- Grain: one row per transaction_id + article_id.
CREATE OR REPLACE VIEW star_schema.vw_sales_detail AS
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
JOIN star_schema.dim_customer AS c ON c.customer_id = f.customer_id;

-- 2. vw_sales_kpi

-- Overall KPIs. total_customers_in_dimension is all customers in dim_customer;
-- purchasing_customers is customers who appear in fact_sales.
CREATE OR REPLACE VIEW star_schema.vw_sales_kpi AS
SELECT
    COALESCE(SUM(f.sales_revenue), 0) AS total_revenue,
    COALESCE(SUM(f.quantity), 0) AS total_units_sold,
    COUNT(DISTINCT f.transaction_id) AS total_transactions,
    COUNT(DISTINCT f.article_id) AS distinct_articles_sold,
    COUNT(DISTINCT f.customer_id) AS purchasing_customers,
    (SELECT COUNT(*) FROM star_schema.dim_customer) AS total_customers_in_dimension,
    SUM(f.sales_revenue) / NULLIF(COUNT(DISTINCT f.transaction_id), 0) AS average_order_value,
    SUM(f.sales_revenue) / NULLIF(COUNT(DISTINCT f.customer_id), 0) AS average_spending_per_purchasing_customer
FROM star_schema.fact_sales AS f;

-- 3. vw_monthly_sales

CREATE OR REPLACE VIEW star_schema.vw_monthly_sales AS
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
GROUP BY d.year, d.month;

-- 4. vw_daily_customer_trend

CREATE OR REPLACE VIEW star_schema.vw_daily_customer_trend AS
SELECT
    d.full_date,
    COUNT(DISTINCT f.customer_id) AS active_customers,
    SUM(f.quantity) AS total_units_sold,
    SUM(f.sales_revenue) AS total_revenue,
    SUM(f.quantity)::NUMERIC / NULLIF(COUNT(DISTINCT f.customer_id), 0) AS avg_units_per_customer,
    SUM(f.sales_revenue) / NULLIF(COUNT(DISTINCT f.customer_id), 0) AS avg_spending_per_customer
FROM star_schema.fact_sales AS f
JOIN star_schema.dim_date AS d ON d.date_key = f.date_key
GROUP BY d.full_date;

-- 5. vw_product_performance

CREATE OR REPLACE VIEW star_schema.vw_product_performance AS
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
    a.prod_type_name, a.product_group_name;

-- 6. vw_product_group_performance

CREATE OR REPLACE VIEW star_schema.vw_product_group_performance AS
SELECT
    a.product_group_name,
    SUM(f.quantity) AS total_units_sold,
    SUM(f.sales_revenue) AS total_revenue,
    COUNT(DISTINCT f.transaction_id) AS total_transactions,
    COUNT(DISTINCT f.customer_id) AS unique_customers,
    SUM(f.sales_revenue) / NULLIF(SUM(f.quantity), 0) AS revenue_per_unit
FROM star_schema.fact_sales AS f
JOIN star_schema.dim_article AS a ON a.article_id = f.article_id
GROUP BY a.product_group_name;

-- 7. vw_product_type_performance

CREATE OR REPLACE VIEW star_schema.vw_product_type_performance AS
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
GROUP BY a.product_type_no, a.prod_type_name;

-- 8. vw_sales_by_channel

CREATE OR REPLACE VIEW star_schema.vw_sales_by_channel AS
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
GROUP BY f.sales_channel_id;

-- 9. vw_customer_spending

CREATE OR REPLACE VIEW star_schema.vw_customer_spending AS
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
GROUP BY c.customer_id, c.age, c.club_member_status;

-- 10. vw_customer_spending_by_segment

-- One row per age group and membership status, suitable for segmented charts.
CREATE OR REPLACE VIEW star_schema.vw_customer_spending_by_segment AS
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
GROUP BY 1, 2;

-- 11. vw_customer_product_group_preference

-- One row per customer and product group. Use this for flexible preference analysis.
CREATE OR REPLACE VIEW star_schema.vw_customer_product_group_preference AS
SELECT
    f.customer_id,
    a.product_group_name,
    SUM(f.quantity) AS total_quantity_purchased,
    SUM(f.sales_revenue) AS total_spending_in_group,
    COUNT(DISTINCT f.transaction_id) AS transactions_in_group
FROM star_schema.fact_sales AS f
JOIN star_schema.dim_article AS a ON a.article_id = f.article_id
GROUP BY f.customer_id, a.product_group_name;

-- 12. vw_customer_product_preference

-- One row per customer and product. Ranking/top preference can be done in Power BI.
CREATE OR REPLACE VIEW star_schema.vw_customer_product_preference AS
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
    a.product_type_no, a.prod_type_name, a.product_group_name;
