-- LOGIN_ACCOUNT: đánh dấu PHASE 2 theo đúng ghi chú trong Data Dictionary —
-- vẫn định nghĩa sẵn ở đây để không phải thiết kế lại sau, nhưng có thể bỏ
-- qua (comment out) nếu phase 1 chưa cần đến đăng nhập.

CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- 1. Customer — customers.csv
CREATE TABLE IF NOT EXISTS customer (
    customer_id             CHAR(64)     PRIMARY KEY,
    age                     SMALLINT     NULL CHECK (age BETWEEN 0 AND 120),
    fn                      BOOLEAN      NULL,
    active                  BOOLEAN      NULL,
    club_member_status      VARCHAR(20)  NULL,
    fashion_news_frequency  VARCHAR(20)  NULL,
    postal_code             CHAR(64)     NULL
);

-- 2. Login account — synthetic, phase 2 (theo Data Dictionary: "đừng quan
--    tâm cái này phase 2 mới dùng"). Giữ định nghĩa sẵn, tạo bảng khi cần.
CREATE TABLE IF NOT EXISTS login_account (
    customer_id    CHAR(64)      PRIMARY KEY REFERENCES customer(customer_id),
    username       VARCHAR(50)   NOT NULL UNIQUE,
    password_hash  VARCHAR(255)  NOT NULL
);

-- 3. Product group — articles.csv.product_group_name (distinct)
CREATE TABLE IF NOT EXISTS product_group (
    product_group_name  VARCHAR(50)  PRIMARY KEY
);

-- 4. Product type — articles.csv
CREATE TABLE IF NOT EXISTS product_type (
    product_type_no    INT          PRIMARY KEY,
    product_type_name  VARCHAR(50)  NOT NULL,
    product_group_name VARCHAR(50)  NOT NULL
        REFERENCES product_group(product_group_name)
);

-- 5. Product — articles.csv (product_code distinct)
CREATE TABLE IF NOT EXISTS product (
    product_code      INT           PRIMARY KEY,
    prod_name         VARCHAR(100)  NOT NULL,
    product_type_no   INT           NOT NULL REFERENCES product_type(product_type_no)
);

-- 6–11. Các lookup mô tả article — độc lập, không roll-up vào đâu
CREATE TABLE IF NOT EXISTS graphical_appearance (
    graphical_appearance_no    INT          PRIMARY KEY,
    graphical_appearance_name  VARCHAR(50)  NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS colour_group (
    colour_group_code  INT          PRIMARY KEY,
    colour_group_name  VARCHAR(50)  NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS perceived_colour_value (
    perceived_colour_value_id    INT          PRIMARY KEY,
    perceived_colour_value_name  VARCHAR(50)  NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS perceived_colour_master (
    perceived_colour_master_id    INT          PRIMARY KEY,
    perceived_colour_master_name  VARCHAR(50)  NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS department (
    department_no    INT          PRIMARY KEY,
    department_name  VARCHAR(50)  NOT NULL
);
ALTER TABLE department DROP CONSTRAINT IF EXISTS department_department_name_key;

CREATE TABLE IF NOT EXISTS garment_group (
    garment_group_no    INT          PRIMARY KEY,
    garment_group_name  VARCHAR(50)  NOT NULL
);

-- 12. Index group — articles.csv
CREATE TABLE IF NOT EXISTS index_group (
    index_group_no    INT          PRIMARY KEY,
    index_group_name  VARCHAR(50)  NOT NULL UNIQUE
);

-- 13. Article index — articles.csv (index_code/index_name/index_group_no)
CREATE TABLE IF NOT EXISTS article_index (
    index_code       CHAR(1)      PRIMARY KEY,
    index_name       VARCHAR(50)  NOT NULL,
    index_group_no   INT          NOT NULL REFERENCES index_group(index_group_no)
);

-- 14. Section — articles.csv (section_no/section_name)
CREATE TABLE IF NOT EXISTS section (
    section_no    INT          PRIMARY KEY,
    section_name  VARCHAR(50)  NOT NULL
);

-- 15. Article — articles.csv + 2 cột derived (image_path, price_base)
CREATE TABLE IF NOT EXISTS article (
    article_id                    CHAR(10)        PRIMARY KEY,
    detail_desc                   TEXT            NULL,
    image_path                    VARCHAR(100)    NULL,   -- derived từ article_id
    price_base                    DECIMAL(12,10)  NULL,   -- derived: median 90 ngày gần nhất (ghi chú b)
    product_code                  INT             NOT NULL REFERENCES product(product_code),
    graphical_appearance_no       INT             NOT NULL REFERENCES graphical_appearance(graphical_appearance_no),
    colour_group_code             INT             NOT NULL REFERENCES colour_group(colour_group_code),
    perceived_colour_value_id     INT             NOT NULL REFERENCES perceived_colour_value(perceived_colour_value_id),
    perceived_colour_master_id    INT             NOT NULL REFERENCES perceived_colour_master(perceived_colour_master_id),
    department_no                 INT             NOT NULL REFERENCES department(department_no),
    garment_group_no              INT             NOT NULL REFERENCES garment_group(garment_group_no),
    index_code                    CHAR(1)         NOT NULL REFERENCES article_index(index_code),
    section_no                    INT             NOT NULL REFERENCES section(section_no)
);

-- 16. Transaction — header giao dịch, transaction_id synthetic
--    (1=cửa hàng, 2=online) 
CREATE TABLE IF NOT EXISTS transaction (
    transaction_id     UUID   PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id        CHAR(64)  NOT NULL REFERENCES customer(customer_id),
    sales_channel_id   SMALLINT  NOT NULL CHECK (sales_channel_id IN (1, 2)),
    t_dat              DATE      NOT NULL
);

-- 17. Contains — chi tiết từng article trong 1 giao dịch (bảng nối M:N).
--    quantity derived: đếm số dòng trùng lặp trong transactions_train.csv
--    khi gộp nhóm lúc ETL (xem Data Dictionary mục 4).
CREATE TABLE IF NOT EXISTS contains (
    transaction_id  UUID            NOT NULL REFERENCES transaction(transaction_id),
    article_id      CHAR(10)        NOT NULL REFERENCES article(article_id),
    price            DECIMAL(12,10) NOT NULL CHECK (price >= 0),
    quantity         SMALLINT        NOT NULL DEFAULT 1 CHECK (quantity > 0),
    PRIMARY KEY (transaction_id, article_id)
);


