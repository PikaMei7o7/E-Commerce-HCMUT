SELECT 
    CASE 
        WHEN c.age IS NULL THEN 'Unknown'
        WHEN c.age < 20 THEN 'Under 20'
        WHEN c.age BETWEEN 20 AND 29 THEN '20-29'
        WHEN c.age BETWEEN 30 AND 39 THEN '30-39'
        WHEN c.age BETWEEN 40 AND 49 THEN '40-49'
        WHEN c.age BETWEEN 50 AND 59 THEN '50-59'
        ELSE '60+' 
    END AS age_group,
    COUNT(DISTINCT c.customer_id) AS total_customers,
    SUM(f.quantity) AS total_units_sold,
    SUM(f.sales_revenue) AS total_revenue,
    ROUND(SUM(f.sales_revenue) / NULLIF(COUNT(DISTINCT c.customer_id), 0), 2) AS avg_revenue_per_customer
FROM fact_sales f
JOIN dim_customer c ON f.customer_id = c.customer_id
GROUP BY age_group
ORDER BY total_revenue DESC;
