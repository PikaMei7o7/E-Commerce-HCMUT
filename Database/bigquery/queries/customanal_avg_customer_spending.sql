--EXPLAIN ANALYZE
SELECT 
    SUM(sales_revenue) / COUNT(DISTINCT customer_id) AS avg_customer_spending
FROM FACT_SALES;