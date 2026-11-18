-- ============================================================================
-- SCRIPT: TẠO MATERIALIZED VIEWS VÀ INDEXES CHUẨN (AN TOÀN CHO SERVER CHUNG)
-- ============================================================================

-------------------------------------------------------------------------------
-- 1. SALES KPI
-------------------------------------------------------------------------------
CREATE MATERIALIZED VIEW IF NOT EXISTS star_schema.mv_sales_kpi AS
SELECT * FROM star_schema.vw_sales_kpi;

CREATE OR REPLACE VIEW star_schema.vw_sales_kpi AS
SELECT * FROM star_schema.mv_sales_kpi;

-------------------------------------------------------------------------------
-- 2. MONTHLY SALES
-------------------------------------------------------------------------------
CREATE MATERIALIZED VIEW IF NOT EXISTS star_schema.mv_monthly_sales AS
SELECT * FROM star_schema.vw_monthly_sales;

CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_monthly_sales_ym 
    ON star_schema.mv_monthly_sales (year, month);

CREATE OR REPLACE VIEW star_schema.vw_monthly_sales AS
SELECT * FROM star_schema.mv_monthly_sales;

-------------------------------------------------------------------------------
-- 3. DAILY CUSTOMER TREND
-------------------------------------------------------------------------------
CREATE MATERIALIZED VIEW IF NOT EXISTS star_schema.mv_daily_customer_trend AS
SELECT * FROM star_schema.vw_daily_customer_trend;

CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_daily_customer_trend_date 
    ON star_schema.mv_daily_customer_trend (full_date);

CREATE OR REPLACE VIEW star_schema.vw_daily_customer_trend AS
SELECT * FROM star_schema.mv_daily_customer_trend;

-------------------------------------------------------------------------------
-- 4. SALES BY CHANNEL
-------------------------------------------------------------------------------
CREATE MATERIALIZED VIEW IF NOT EXISTS star_schema.mv_sales_by_channel AS
SELECT * FROM star_schema.vw_sales_by_channel;

CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_sales_by_channel_id 
    ON star_schema.mv_sales_by_channel (sales_channel_id);

CREATE OR REPLACE VIEW star_schema.vw_sales_by_channel AS
SELECT * FROM star_schema.mv_sales_by_channel;

-------------------------------------------------------------------------------
-- 5. PRODUCT PERFORMANCE
-------------------------------------------------------------------------------
CREATE MATERIALIZED VIEW IF NOT EXISTS star_schema.mv_product_performance AS
SELECT * FROM star_schema.vw_product_performance;

CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_product_perf_code 
    ON star_schema.mv_product_performance (product_code);

CREATE INDEX IF NOT EXISTS idx_mv_product_perf_rev 
    ON star_schema.mv_product_performance (total_revenue DESC NULLS LAST);

CREATE INDEX IF NOT EXISTS idx_mv_product_perf_units 
    ON star_schema.mv_product_performance (total_units_sold DESC NULLS LAST);

CREATE OR REPLACE VIEW star_schema.vw_product_performance AS
SELECT * FROM star_schema.mv_product_performance;

-------------------------------------------------------------------------------
-- 6. PRODUCT GROUP & TYPE PERFORMANCE
-------------------------------------------------------------------------------
-- Product Group Performance
CREATE MATERIALIZED VIEW IF NOT EXISTS star_schema.mv_product_group_performance AS
SELECT * FROM star_schema.vw_product_group_performance;

CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_product_group_name 
    ON star_schema.mv_product_group_performance (product_group_name);

CREATE OR REPLACE VIEW star_schema.vw_product_group_performance AS
SELECT * FROM star_schema.mv_product_group_performance;

-------------------------------------------------------------------------------
-- Product Type Performance
-------------------------------------------------------------------------------
CREATE MATERIALIZED VIEW IF NOT EXISTS star_schema.mv_product_type_performance AS
SELECT * FROM star_schema.vw_product_type_performance;

CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_product_type_no 
    ON star_schema.mv_product_type_performance (product_type_no);

CREATE OR REPLACE VIEW star_schema.vw_product_type_performance AS
SELECT * FROM star_schema.mv_product_type_performance;

-------------------------------------------------------------------------------
-- 7. CUSTOMER SPENDING & SEGMENT
-------------------------------------------------------------------------------
-- Customer Spending
CREATE MATERIALIZED VIEW IF NOT EXISTS star_schema.mv_customer_spending AS
SELECT * FROM star_schema.vw_customer_spending;

CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_customer_spending_id 
    ON star_schema.mv_customer_spending (customer_id);

CREATE INDEX IF NOT EXISTS idx_mv_customer_spending_top 
    ON star_schema.mv_customer_spending (total_spending DESC NULLS LAST);

CREATE INDEX IF NOT EXISTS idx_mv_customer_spending_freq 
    ON star_schema.mv_customer_spending (purchase_frequency);

CREATE OR REPLACE VIEW star_schema.vw_customer_spending AS
SELECT * FROM star_schema.mv_customer_spending;

-------------------------------------------------------------------------------
-- Customer Spending By Segment
-------------------------------------------------------------------------------
CREATE MATERIALIZED VIEW IF NOT EXISTS star_schema.mv_customer_spending_by_segment AS
SELECT * FROM star_schema.vw_customer_spending_by_segment;

CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_customer_seg_pk 
    ON star_schema.mv_customer_spending_by_segment (age_group, club_member_status);

CREATE OR REPLACE VIEW star_schema.vw_customer_spending_by_segment AS
SELECT * FROM star_schema.mv_customer_spending_by_segment;

-------------------------------------------------------------------------------
-- 8. SALES EXPLORER (Dữ liệu chi tiết & Sở thích khách hàng)
-------------------------------------------------------------------------------
-- Sales Detail (Chi tiết giao dịch)
CREATE MATERIALIZED VIEW IF NOT EXISTS star_schema.mv_sales_detail AS
SELECT * FROM star_schema.vw_sales_detail;

-- Indexes tiêu chuẩn (B-Tree & Composite Indexes)
CREATE INDEX IF NOT EXISTS idx_mv_sales_detail_year_channel 
    ON star_schema.mv_sales_detail (year, sales_channel_name);

CREATE INDEX IF NOT EXISTS idx_mv_sales_detail_customer_seg 
    ON star_schema.mv_sales_detail (age_group, club_member_status);

CREATE INDEX IF NOT EXISTS idx_mv_sales_detail_group_name 
    ON star_schema.mv_sales_detail (product_group_name);

CREATE INDEX IF NOT EXISTS idx_mv_sales_detail_explorer_all 
    ON star_schema.mv_sales_detail (year, sales_channel_name, age_group, club_member_status, product_group_name);

CREATE INDEX IF NOT EXISTS idx_mv_sales_detail_dim_group 
    ON star_schema.mv_sales_detail (sales_revenue DESC) 
    INCLUDE (transaction_id, customer_id, quantity, year, sales_channel_name, age_group, club_member_status, product_group_name);

CREATE INDEX IF NOT EXISTS idx_mv_sales_detail_table_perf 
    ON star_schema.mv_sales_detail (year, month, sales_channel_name, product_group_name, age_group, club_member_status);

CREATE OR REPLACE VIEW star_schema.vw_sales_detail AS
SELECT * FROM star_schema.mv_sales_detail;

-------------------------------------------------------------------------------
-- Customer Product Group Preference
-------------------------------------------------------------------------------
CREATE MATERIALIZED VIEW IF NOT EXISTS star_schema.mv_customer_product_group_preference AS
SELECT * FROM star_schema.vw_customer_product_group_preference;

CREATE INDEX IF NOT EXISTS idx_mv_cust_prod_grp_pref_cust 
    ON star_schema.mv_customer_product_group_preference (customer_id);

CREATE INDEX IF NOT EXISTS idx_mv_cust_prod_grp_pref_spend 
    ON star_schema.mv_customer_spending (total_spending DESC NULLS LAST);

CREATE OR REPLACE VIEW star_schema.vw_customer_product_group_preference AS
SELECT * FROM star_schema.mv_customer_product_group_preference;

-------------------------------------------------------------------------------
-- Customer Product Preference
-------------------------------------------------------------------------------
CREATE MATERIALIZED VIEW IF NOT EXISTS star_schema.mv_customer_product_preference AS
SELECT * FROM star_schema.vw_customer_product_preference;

CREATE INDEX IF NOT EXISTS idx_mv_cust_prod_pref_article 
    ON star_schema.mv_customer_product_preference (article_id);

CREATE OR REPLACE VIEW star_schema.vw_customer_product_preference AS
SELECT * FROM star_schema.mv_customer_product_preference;

-------------------------------------------------------------------------------
-- 9. CẬP NHẬT THỐNG KÊ (ANALYZE) CHO QUERY PLANNER
-------------------------------------------------------------------------------
ANALYZE star_schema.fact_sales;
ANALYZE star_schema.dim_article;
ANALYZE star_schema.dim_customer;
ANALYZE star_schema.dim_date;
ANALYZE star_schema.mv_sales_detail;


-------------------------------------------------------------------------------
-- 10. OPTIONAL / ADVANCED: GIN TRIGRAM INDEXES
-------------------------------------------------------------------------------
-------------------------------------------------------------------------------
/*
--  extension 
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Tạo GIN Index cho product_group_name
CREATE INDEX IF NOT EXISTS idx_mv_sales_detail_group_gin 
    ON star_schema.mv_sales_detail USING gin (product_group_name gin_trgm_ops);

-- Tạo GIN Index cho prod_name
CREATE INDEX IF NOT EXISTS idx_mv_sales_detail_prodname_gin 
    ON star_schema.mv_sales_detail USING gin (prod_name gin_trgm_ops);

-- (Drop)
-- DROP INDEX IF EXISTS star_schema.idx_mv_sales_detail_group_gin;
-- DROP INDEX IF EXISTS star_schema.idx_mv_sales_detail_prodname_gin;
*/
