-- ============================================================================
-- TESTCASE 1: DAILY CUSTOMER TREND
-- ============================================================================

-- BEFORE:
EXPLAIN ANALYZE
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


-- AFTER:
EXPLAIN ANALYZE
SELECT * FROM star_schema.mv_daily_customer_trend;
