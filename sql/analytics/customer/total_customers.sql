--EXPLAIN ANALYZE
SELECT 
    total_customers_in_dimension AS total_customers
FROM star_schema.vw_sales_kpi;
-- SELECT 
--     COUNT(customer_id) AS total_customers
-- FROM dim_customer
