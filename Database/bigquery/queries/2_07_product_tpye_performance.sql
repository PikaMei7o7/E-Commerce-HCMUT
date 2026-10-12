SELECT 
    a.product_type_name,
    SUM(f.quantity) AS total_units_sold,
    SUM(f.sales_revenue) AS total_revenue,
-- COUNT(DISTINCT f.article_id) AS total_unique_articles
FROM fact_sales f
JOIN dim_article a ON f.article_id = a.article_id
GROUP BY 
    a.product_type_name
ORDER BY 
    total_revenue DESC;
