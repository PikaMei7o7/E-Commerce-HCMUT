-- ***** Have index created *****
--EXPLAIN ANALYZE
SELECT 
    COUNT(DISTINCT article_id) AS total_products_sold
FROM contains;
