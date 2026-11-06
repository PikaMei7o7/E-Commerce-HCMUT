--EXPLAIN ANALYZE
-- SELECT 
--     SUM(sales_revenue) AS total_customer_spending
-- FROM FACT_SALES;
SELECT 
    total_revenue AS total_customer_spending
FROM star_schema.vw_sales_kpi;