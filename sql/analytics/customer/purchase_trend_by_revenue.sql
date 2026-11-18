SELECT 
    d.full_date AS t_dat,
    SUM(f.sales_revenue) AS total_spending,
    COUNT(DISTINCT f.customer_id) AS total_buyers,
    ROUND(SUM(f.sales_revenue) / NULLIF(COUNT(DISTINCT f.customer_id), 0), 2) AS avg_spending_per_customer
FROM fact_sales f
JOIN dim_date d ON f.date_key = d.date_key
GROUP BY 
    d.full_date
ORDER BY 
    d.full_date ASC;
