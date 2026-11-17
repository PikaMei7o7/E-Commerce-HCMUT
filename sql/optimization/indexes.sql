-- ============================================================================
-- 1. INDEX TRÊN BẢNG FACT_SALES
-- ============================================================================
-- Hỗ trợ tối ưu cho biểu đồ xu hướng và kênh bán hàng
CREATE INDEX IF NOT EXISTS idx_fact_sales_date_channel 
    ON star_schema.fact_sales (date_key, sales_channel_id);

-- Hỗ trợ truy vấn liên kết (JOIN) từ Fact sang Dim Customer cho các widget phân khúc khách hàng
CREATE INDEX IF NOT EXISTS idx_fact_sales_customer_fact 
    ON star_schema.fact_sales (customer_id, sales_revenue);

-- Hỗ trợ truy vấn liên kết sang Dim Article cho các widget hiệu suất sản phẩm
CREATE INDEX IF NOT EXISTS idx_fact_sales_article_fact 
    ON star_schema.fact_sales (article_id, sales_revenue, quantity);

-- Index đơn cho article_id trên bảng fact_sales (Hỗ trợ các view tổng hợp chi tiết theo article)
CREATE INDEX IF NOT EXISTS idx_fact_sales_article_id 
    ON star_schema.fact_sales (article_id);

-- Index đơn cho customer_id trên bảng fact_sales (Hỗ trợ các view thống kê chi tiết theo customer)
CREATE INDEX IF NOT EXISTS idx_fact_sales_customer_id 
    ON star_schema.fact_sales (customer_id);
-- ============================================================================
-- 2. INDEX TRÊN CÁC BẢNG DIM
-- ============================================================================

-- Hỗ trợ widget "Monthly trend" và lọc theo năm/tháng trong bảng dim_date
CREATE INDEX IF NOT EXISTS idx_dim_date_year_month_key 
    ON star_schema.dim_date (year, month, date_key);
-- Composite Index
-- Giúp tối ưu hóa việc nhóm theo age_group và club_member_status
CREATE INDEX IF NOT EXISTS idx_dim_customer_segment 
    ON star_schema.dim_customer (club_member_status, age, customer_id);
-- Hỗ trợ tìm kiếm và sắp xếp nhóm sản phẩm trong tab "Product performance"
CREATE INDEX IF NOT EXISTS idx_dim_article_group_type 
    ON star_schema.dim_article (product_group_name, product_type_no, article_id);

-- Hỗ trợ các view gom nhóm theo tên nhóm sản phẩm (như vw_product_group_performance)
CREATE INDEX IF NOT EXISTS idx_dim_article_group_name 
    ON star_schema.dim_article (product_group_name);