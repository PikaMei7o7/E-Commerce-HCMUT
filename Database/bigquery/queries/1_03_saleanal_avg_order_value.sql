--EXPLAIN ANALYZE
-- SELECT 
--     SUM(price * quantity) / COUNT(DISTINCT transaction_id) AS average_order_value
-- FROM contains;
--EXPLAIN ANALYZE 
SELECT 
    (SELECT SUM(price * quantity) FROM contains) / (SELECT COUNT(transaction_id) FROM transaction) AS average_order_value;
