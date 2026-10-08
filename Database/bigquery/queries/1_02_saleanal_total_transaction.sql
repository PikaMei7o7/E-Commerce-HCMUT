-- --EXPLAIN ANALYZE
SELECT 
    COUNT(DISTINCT transaction_id) AS total_transactions
FROM FACT_SALES;

-- SELECT 
--     COUNT(transaction_id) AS total_transactions 
-- FROM transaction;
