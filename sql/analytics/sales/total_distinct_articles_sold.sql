--EXPLAIN ANALYZE
--EXPLAIN ANALYZE
SELECT 
    distinct_articles_sold AS total_products_sold
FROM star_schema.vw_sales_kpi;

-- SELECT 
--     COUNT(DISTINCT article_id) AS total_products_sold
-- FROM FACT_SALES;

-- SELECT 
--     COUNT(DISTINCT article_id) AS total_products_sold
-- FROM contains;
