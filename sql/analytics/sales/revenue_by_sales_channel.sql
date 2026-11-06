--EXPLAIN ANALYZE
SELECT 
    sales_channel_id,
    sales_channel_name,
    total_revenue
FROM star_schema.vw_sales_by_channel;

-- SELECT 
--     sc.sales_channel_id,
--     sc.sales_channel_name,
--     SUM(f.sales_revenue) AS total_revenue
-- FROM fact_sales f
-- JOIN dim_sale_chanel sc ON f.sales_channel_id = sc.sales_channel_id
-- GROUP BY sc.sales_channel_id, sc.sales_channel_name;
