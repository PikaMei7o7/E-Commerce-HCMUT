-- Keep the existing star_schema.sql unchanged: dim_sale_channel currently has only sales_channel_id.
INSERT INTO star_schema.dim_sale_channel (
    sales_channel_id,
    sales_channel_name
)
VALUES
    (1, 'Store'),
    (2, 'Online')
ON CONFLICT (sales_channel_id)
DO UPDATE SET
    sales_channel_name = EXCLUDED.sales_channel_name;