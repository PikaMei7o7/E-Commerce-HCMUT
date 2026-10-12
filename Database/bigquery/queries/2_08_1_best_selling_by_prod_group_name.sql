WITH ranked_products_by_group AS (
    SELECT 
        a.product_group_name,
        a.product_code,
        a.prod_name,
        SUM(f.quantity) AS total_units_sold,
        SUM(f.sales_revenue) AS total_revenue,
        ROW_NUMBER() OVER (
            PARTITION BY a.product_group_name 
            ORDER BY SUM(f.quantity) DESC
        ) AS rank
    FROM fact_sales f
    JOIN dim_article a ON f.article_id = a.article_id
    GROUP BY 
        a.product_group_name,
        a.product_code,
        a.prod_name
)
SELECT 
    product_group_name,
    product_code,
    prod_name,
    total_units_sold,
    total_revenue
FROM ranked_products_by_group
WHERE rank = 1
ORDER BY total_units_sold DESC;
