WITH customer_group_ranking AS (
    SELECT 
        customer_id,
        product_group_name,
        total_quantity_purchased,
        total_spending_in_group,
        ROW_NUMBER() OVER (
            PARTITION BY customer_id 
            ORDER BY total_quantity_purchased DESC, total_spending_in_group DESC
        ) AS group_rank
    FROM star_schema.vw_customer_product_group_preference
)
SELECT
    customer_id,
    product_group_name AS preferred_product_group,
    total_quantity_purchased,
    total_spending_in_group
FROM customer_group_ranking
WHERE group_rank = 1
ORDER BY total_quantity_purchased DESC;

-- WITH customer_group_ranking AS (
--     SELECT 
--         f.customer_id,
--         a.product_group_name,
--         SUM(f.quantity) AS total_quantity_purchased,
--         SUM(f.sales_revenue) AS total_spending_in_group,
--         ROW_NUMBER() OVER (
--             PARTITION BY f.customer_id 
--             ORDER BY SUM(f.quantity) DESC, SUM(f.sales_revenue) DESC
--         ) AS group_rank
--     FROM fact_sales f
--     JOIN dim_article a ON f.article_id = a.article_id
--     GROUP BY 
--         f.customer_id,
--         a.product_group_name
-- )
-- SELECT
--     customer_id,
--     product_group_name AS preferred_product_group,
--     total_quantity_purchased,
--     total_spending_in_group
-- FROM customer_group_ranking
-- WHERE group_rank = 1
-- ORDER BY total_quantity_purchased DESC;
