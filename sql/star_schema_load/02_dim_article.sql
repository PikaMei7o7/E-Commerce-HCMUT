INSERT INTO star_schema.dim_article (
    article_id, price_base, product_code, prod_name,
    product_type_no, prod_type_name, product_group_name,
    graphical_appearance_no, colour_group_code,
    perceived_colour_value_id, perceived_colour_master_id,
    department_no, garment_group_no, index_code,
    index_group_no, section_no
)
SELECT a.article_id, a.price_base, p.product_code, p.prod_name,
       pt.product_type_no, pt.product_type_name, pt.product_group_name,
       a.graphical_appearance_no, a.colour_group_code,
       a.perceived_colour_value_id, a.perceived_colour_master_id,
       a.department_no, a.garment_group_no, a.index_code,
       ai.index_group_no, a.section_no
FROM public.article AS a
JOIN public.product AS p ON p.product_code = a.product_code
JOIN public.product_type AS pt ON pt.product_type_no = p.product_type_no
JOIN public.article_index AS ai ON ai.index_code = a.index_code
ON CONFLICT (article_id) DO UPDATE SET
    price_base = EXCLUDED.price_base,
    product_code = EXCLUDED.product_code,
    prod_name = EXCLUDED.prod_name,
    product_type_no = EXCLUDED.product_type_no,
    prod_type_name = EXCLUDED.prod_type_name,
    product_group_name = EXCLUDED.product_group_name,
    graphical_appearance_no = EXCLUDED.graphical_appearance_no,
    colour_group_code = EXCLUDED.colour_group_code,
    perceived_colour_value_id = EXCLUDED.perceived_colour_value_id,
    perceived_colour_master_id = EXCLUDED.perceived_colour_master_id,
    department_no = EXCLUDED.department_no,
    garment_group_no = EXCLUDED.garment_group_no,
    index_code = EXCLUDED.index_code,
    index_group_no = EXCLUDED.index_group_no,
    section_no = EXCLUDED.section_no;
