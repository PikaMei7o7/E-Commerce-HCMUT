INSERT INTO star_schema.dim_customer (
    customer_id, age, fn, active, club_member_status,
    fashion_news_frequency, postal_code
)
SELECT customer_id, age, fn, active, club_member_status,
       fashion_news_frequency, postal_code
FROM public.customer
ON CONFLICT (customer_id) DO UPDATE SET
    age = EXCLUDED.age,
    fn = EXCLUDED.fn,
    active = EXCLUDED.active,
    club_member_status = EXCLUDED.club_member_status,
    fashion_news_frequency = EXCLUDED.fashion_news_frequency,
    postal_code = EXCLUDED.postal_code;
