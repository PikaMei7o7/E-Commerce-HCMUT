-- Create roles (if they do not already exist)
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'hm_product_sales_analyst') THEN
        CREATE ROLE hm_product_sales_analyst NOLOGIN;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'hm_customer_analyst') THEN
        CREATE ROLE hm_customer_analyst NOLOGIN;
    END IF;
END
$$;

-- Remove previous permissions
REVOKE ALL ON ALL TABLES IN SCHEMA star_schema
FROM PUBLIC, hm_product_sales_analyst, hm_customer_analyst;

-- Allow both roles to access the schema
GRANT USAGE ON SCHEMA star_schema
TO hm_product_sales_analyst, hm_customer_analyst;


-- 1. Product sales analyst

GRANT SELECT (
    transaction_id,
    article_id,
    date_key,
    sales_channel_id,
    price,
    quantity,
    sales_revenue
)
ON star_schema.FACT_SALES 
TO hm_product_sales_analyst;

GRANT SELECT ON
    star_schema.dim_article,
    star_schema.dim_date,
    star_schema.dim_sale_channel
TO hm_product_sales_analyst;


-- 2. Customer analyst

GRANT SELECT ON ALL TABLES IN SCHEMA star_schema
TO hm_customer_analyst;
