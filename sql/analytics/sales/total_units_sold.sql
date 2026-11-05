--EXPLAIN ANALYZE
SELECT 
    SUM(quantity) AS total_units_sold
FROM FACT_SALES;

-- SELECT 
--     SUM(quantity) AS total_units_sold
-- FROM contains;
-- --SEQ scan
