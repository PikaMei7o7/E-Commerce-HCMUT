-- ============================================================================
-- TESTCASE 3: CUSTOMER SPENDING
-- ============================================================================

-- BEFORE:
EXPLAIN ANALYZE
SELECT
    c.customer_id,
    c.age,
    CASE
        WHEN c.age IS NULL THEN 'Unknown'
        WHEN c.age < 20 THEN 'Under 20'
        WHEN c.age BETWEEN 20 AND 29 THEN '20-29'
        WHEN c.age BETWEEN 30 AND 39 THEN '30-39'
        WHEN c.age BETWEEN 40 AND 49 THEN '40-49'
        WHEN c.age BETWEEN 50 AND 59 THEN '50-59'
        ELSE '60+'
    END AS age_group,
    COALESCE(c.club_member_status, 'UNKNOWN') AS club_member_status,
    COUNT(DISTINCT f.transaction_id) AS purchase_frequency,
    SUM(f.quantity) AS total_units_purchased,
    SUM(f.sales_revenue) AS total_spending,
    SUM(f.sales_revenue) / NULLIF(COUNT(DISTINCT f.transaction_id), 0) AS average_order_value
FROM star_schema.dim_customer AS c
JOIN star_schema.fact_sales AS f ON f.customer_id = c.customer_id
GROUP BY c.customer_id, c.age, c.club_member_status;


-- AFTER:
EXPLAIN ANALYZE
SELECT * FROM star_schema.mv_customer_spending;
