--Index for product_total_product_sold
CREATE INDEX IF NOT EXISTS idx_contains_article_id ON contains(article_id);

--Index for product_top_selling_product
CREATE INDEX IF NOT EXISTS idx_contains_covering ON contains(article_id) INCLUDE (quantity, price);
--Temporarily not use this file
