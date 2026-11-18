-- ============================================================================
-- TESTCASE 4: SALES EXPLORER
-- ============================================================================

-- BEFORE:
EXPLAIN ANALYZE
SELECT 
    v.year,
    v.month,
    v.sales_channel_name,
    v.age_group,
    v.product_group_name,
    SUM(v.sales_revenue) AS total_revenue,
    SUM(v.quantity) AS total_units_sold,
    COUNT(DISTINCT v.transaction_id) AS total_transactions
FROM star_schema.vw_sales_detail AS v
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
