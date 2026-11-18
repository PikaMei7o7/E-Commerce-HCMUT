--EXPLAIN ANALYZE
SELECT 
    ROUND(SUM(sales_revenue) / COUNT(DISTINCT transaction_id), 2) AS average_order_value   
    -- SUM(sales_revenue) / COUNT(DISTINCT transaction_id) AS average_order_value
FROM FACT_SALES;

-- SELECT 
--     SUM(price * quantity) / COUNT(DISTINCT transaction_id) AS average_order_value
-- FROM contains;
-- EXPLAIN ANALYZE 
-- SELECT 
--     (SELECT SUM(price * quantity) FROM contains) / (SELECT COUNT(transaction_id) FROM transaction) AS average_order_value;
