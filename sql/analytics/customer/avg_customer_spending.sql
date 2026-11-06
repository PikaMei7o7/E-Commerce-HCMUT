--EXPLAIN ANALYZE
-- SELECT 
--     SUM(sales_revenue) / COUNT(DISTINCT customer_id) AS avg_customer_spending
-- FROM FACT_SALES;

SELECT 
    average_spending_per_purchasing_customer AS avg_customer_spending
FROM star_schema.vw_sales_kpi;