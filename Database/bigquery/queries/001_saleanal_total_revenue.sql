--EXPLAIN ANALYZE
SELECT 
    SUM(price * quantity) AS total_revenue
FROM contains;
