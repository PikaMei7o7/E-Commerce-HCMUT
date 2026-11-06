SELECT 
    product_type_name,
    total_units_sold,
    total_revenue,
    distinct_articles_sold AS total_unique_articles
FROM star_schema.vw_product_type_performance
ORDER BY 
    total_revenue DESC;
    
-- SELECT 
--     a.prod_type_name,
--     SUM(f.quantity) AS total_units_sold,
--     SUM(f.sales_revenue) AS total_revenue,
-- -- COUNT(DISTINCT f.article_id) AS total_unique_articles
-- FROM fact_sales f
-- JOIN dim_article a ON f.article_id = a.article_id
-- GROUP BY 
--     a.prod_type_name
-- ORDER BY 
--     total_revenue DESC;
