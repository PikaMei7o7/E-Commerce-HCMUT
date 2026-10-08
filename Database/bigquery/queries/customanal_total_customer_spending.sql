--EXPLAIN ANALYZE
SELECT 
    SUM(sales_revenue) AS total_customer_spending
FROM FACT_SALES;