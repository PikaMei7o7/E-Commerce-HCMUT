--EXPLAIN ANALYZE
SELECT 
    ROUND(average_order_value, 2) AS average_order_value
FROM star_schema.vw_sales_kpi;

-- SELECT 
--     ROUND(SUM(sales_revenue) / COUNT(DISTINCT transaction_id), 2) AS average_order_value   
--     -- SUM(sales_revenue) / COUNT(DISTINCT transaction_id) AS average_order_value
-- FROM FACT_SALES;
