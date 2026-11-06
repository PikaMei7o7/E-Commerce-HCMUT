--EXPLAIN ANAYLYZE
SELECT 
    year,
    month,
    total_revenue
FROM star_schema.vw_monthly_sales
ORDER BY 
    year ASC, 
    month ASC;
-- SELECT 
--     d.year,
--     d.month,
--     SUM(f.sales_revenue) AS total_revenue
-- FROM fact_sales f
-- JOIN dim_date d ON f.date_key = d.date_key
-- GROUP BY 
--     d.year, 
--     d.month
-- ORDER BY 
--     d.year ASC, 
--     d.month ASC;
