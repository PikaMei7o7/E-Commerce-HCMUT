--EXPLAIN ANALYZE
SELECT 
    c.customer_key,
    COUNT(DISTINCT f.transaction_id) AS purchase_frequency
FROM FACT_SALES f
JOIN dim_customer c ON f.customer_id = c.customer_id
GROUP BY 
    c.customer_key
ORDER BY 
    purchase_frequency DESC;