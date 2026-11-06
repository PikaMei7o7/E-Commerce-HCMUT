SELECT 
    full_date AS t_dat,
    product_code,               
    prod_name,             
    SUM(sales_revenue) AS total_revenue,
    SUM(quantity) AS total_units_sold
FROM star_schema.vw_sales_detail
GROUP BY 
    full_date,
    product_code,
    prod_name
ORDER BY 
    full_date ASC, 
    total_revenue DESC;

-- SELECT 
--     d.full_date AS t_dat,
--     a.product_code,               
--     a.prod_name,             
--     SUM(f.sales_revenue) AS total_revenue,
--     SUM(f.quantity) AS total_units_sold
-- FROM fact_sales f
-- JOIN dim_date d ON f.date_key = d.date_key
-- JOIN dim_article a ON f.article_id = a.article_id
-- GROUP BY 
--     d.full_date,
--     a.product_code,
--     a.prod_name
-- ORDER BY 
--     d.full_date ASC, 
--     total_revenue DESC;
