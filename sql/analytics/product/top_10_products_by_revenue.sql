--EXPLAIN ANALYZE
SELECT 
    a.product_code,
    a.prod_name,
    SUM(f.sales_revenue) AS total_revenue,
    SUM(f.quantity) AS total_units_sold
FROM FACT_SALES f
JOIN dim_article a ON f.article_id = a.article_id
GROUP BY 
    a.product_code, 
    a.prod_name
ORDER BY 
    total_revenue DESC
LIMIT 10;
