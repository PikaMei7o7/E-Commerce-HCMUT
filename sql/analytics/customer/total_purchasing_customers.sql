-- EXPLAIN ANALYZE
-- SELECT 
--     COUNT(DISTINCT customer_id) AS total_customers
-- FROM FACT_SALES;
SELECT 
    purchasing_customers AS total_purchasing_customers
FROM star_schema.vw_sales_kpi;
-- Total customers: tổng số khách hàng duy nhất đã phát sinh giao dịch
