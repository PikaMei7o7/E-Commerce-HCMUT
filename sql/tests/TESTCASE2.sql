-- ============================================================================
-- TESTCASE 2: PRODUCT PERFORMANCE
-- ============================================================================

-- BEFORE
EXPLAIN ANALYZE
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


-- AFTER
EXPLAIN ANALYZE
SELECT * FROM star_schema.mv_product_performance;
