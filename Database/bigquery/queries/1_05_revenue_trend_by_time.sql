--EXPLAIN ANAYLYZE
SELECT 
    d.year,
    d.month,
    SUM(f.sales_revenue) AS total_revenue
FROM star_schema.fact_sales f
JOIN star_schema.dim_date d ON f.date_key = d.date_key
GROUP BY 
    d.year, 
    d.month
ORDER BY 
    d.year ASC, 
    d.month ASC;
