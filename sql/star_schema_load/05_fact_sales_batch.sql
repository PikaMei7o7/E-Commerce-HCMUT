INSERT INTO star_schema.fact_sales (
    transaction_id, customer_id, article_id, date_key,
    sales_channel_id, price, quantity, sales_revenue
)
SELECT t.transaction_id,
       t.customer_id,
       c.article_id,
       TO_CHAR(t.t_dat, 'YYYYMMDD')::INTEGER,
       t.sales_channel_id,
       c.price,
       c.quantity,
       c.price * c.quantity
FROM public."transaction" AS t
JOIN public.contains AS c ON c.transaction_id = t.transaction_id
WHERE t.t_dat >= %(start_date)s
  AND t.t_dat < %(end_date)s
ON CONFLICT (transaction_id, article_id) DO UPDATE SET
    customer_id = EXCLUDED.customer_id,
    date_key = EXCLUDED.date_key,
    sales_channel_id = EXCLUDED.sales_channel_id,
    price = EXCLUDED.price,
    quantity = EXCLUDED.quantity,
    sales_revenue = EXCLUDED.sales_revenue;
