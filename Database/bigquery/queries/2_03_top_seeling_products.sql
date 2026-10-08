-- EXPLAIN ANALYZE 
--STAR
SELECT 
    a.product_code,
    a.prod_name,
    SUM(f.quantity) AS total_quantity_sold,
    SUM(f.sales_revenue) AS total_revenue
-- FROM FACT_SALES f
FROM contains f
JOIN dim_article a ON f.article_id = a.article_id
GROUP BY 
    a.product_code, 
    a.prod_name
ORDER BY 
    total_quantity_sold DESC
LIMIT 10;




-- SELECT 
--     p.prod_name,
--     p.product_code,
--     SUM(c.quantity) AS total_quantity_sold,
--     SUM(c.price * c.quantity) AS total_revenue
-- FROM contains c -- contain = root
-- JOIN article a ON c.article_id = a.article_id -- join article
-- JOIN product p ON a.product_code = p.product_code -- join product code
-- GROUP BY p.product_code, p.prod_name
-- ORDER BY total_quantity_sold DESC
-- LIMIT 10;


----- Group before join ------
-- SELECT 
--     p.prod_name,
--     top_products.total_quantity_sold,
--     top_products.total_revenue
-- FROM (
--     SELECT 
--         article_id,
--         SUM(quantity) AS total_quantity_sold,
--         SUM(price * quantity) AS total_revenue
--     FROM contains
--     GROUP BY article_id
--     ORDER BY total_quantity_sold DESC
--     LIMIT 10
-- ) top_products
-- JOIN article a ON top_products.article_id = a.article_id
-- JOIN product p ON a.product_code = p.product_code
-- ORDER BY top_products.total_quantity_sold DESC;
