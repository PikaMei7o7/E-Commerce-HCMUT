-- EXPLAIN ANALYZE
SELECT 
    COUNT(DISTINCT customer_id) AS total_customers
FROM FACT_SALES;
-- Total customers: tổng số khách hàng duy nhất đã phát sinh giao dịch
