SELECT 
    COALESCE(c.club_member_status, 'UNKNOWN') AS club_member_status,
    COUNT(DISTINCT c.customer_id) AS total_customers,
    SUM(f.quantity) AS total_units_sold,
    SUM(f.sales_revenue) AS total_revenue,
    ROUND(SUM(f.sales_revenue) / NULLIF(COUNT(DISTINCT c.customer_id), 0), 2) AS avg_revenue_per_customer
FROM fact_sales f
JOIN dim_customer c ON f.customer_id = c.customer_id
GROUP BY c.club_member_status
ORDER BY total_revenue DESC;
