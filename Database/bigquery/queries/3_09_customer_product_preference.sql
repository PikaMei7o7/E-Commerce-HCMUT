WITH customer_product_ranking AS (
    SELECT 
        f.customer_id,
        a.article_id,
        a.product_code,
        a.prod_name,
        a.product_type_name,
        SUM(f.quantity) AS total_quantity_purchased,
        SUM(f.sales_revenue) AS total_spending_on_product,
        ROW_NUMBER() OVER (
            PARTITION BY f.customer_id 
            ORDER BY SUM(f.quantity) DESC, SUM(f.sales_revenue) DESC
        ) AS preference_rank
    FROM fact_sales f
    JOIN dim_article a ON f.article_id = a.article_id
    GROUP BY 
        f.customer_id,
        a.article_id,
        a.product_code,
        a.prod_name,
        a.product_type_name
)
SELECT 
    customer_id,
    article_id,
    product_code,
    prod_name,
    product_type_name,
    total_quantity_purchased,
    total_spending_on_product
FROM customer_product_ranking
WHERE preference_rank = 1
ORDER BY total_quantity_purchased DESC;
