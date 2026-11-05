CREATE SCHEMA IF NOT EXISTS star_schema;

CREATE TABLE IF NOT EXISTS star_schema.dim_customer (
    customer_id             CHAR(64) PRIMARY KEY,
    age                     SMALLINT,
    fn                      BOOLEAN,
    active                  BOOLEAN,
    club_member_status      VARCHAR(20),
    fashion_news_frequency  VARCHAR(20),
    postal_code             CHAR(64)
);

CREATE TABLE IF NOT EXISTS star_schema.dim_article (
    article_id                  CHAR(10) PRIMARY KEY,
    price_base                  DECIMAL(12,10),

    product_code                INT,
    prod_name                   VARCHAR(100),
    product_type_no             INT,
    product_type_name              VARCHAR(50),
    product_group_name          VARCHAR(50),

    graphical_appearance_no     INT,

    colour_group_code           INT,

    perceived_colour_value_id   INT,

    perceived_colour_master_id  INT,

    department_no               INT,

    garment_group_no            INT,

    index_code                  CHAR(1),

    index_group_no              INT,

    section_no                  INT
);

CREATE TABLE IF NOT EXISTS star_schema.dim_date (
    date_key INTEGER PRIMARY KEY,
    full_date DATE NOT NULL UNIQUE,
    day SMALLINT NOT NULL,
    month SMALLINT NOT NULL,
    quarter SMALLINT NOT NULL,
    year SMALLINT NOT NULL,
    day_of_week SMALLINT NOT NULL
);

CREATE TABLE IF NOT EXISTS star_schema.dim_sale_channel (
    sales_channel_id SMALLINT PRIMARY KEY,
    sales_channel_name VARCHAR(20) NOT NULL
);

CREATE TABLE IF NOT EXISTS star_schema.fact_sales (
    transaction_id UUID NOT NULL,
    customer_id CHAR(64) NOT NULL,
    article_id CHAR(10) NOT NULL,
    date_key INTEGER NOT NULL,
    sales_channel_id SMALLINT NOT NULL,

    price DECIMAL(12,10) NOT NULL,
    quantity SMALLINT NOT NULL CHECK (quantity > 0),
    sales_revenue DECIMAL(14,10) NOT NULL,

    PRIMARY KEY (transaction_id, article_id),

    FOREIGN KEY (customer_id)
        REFERENCES star_schema.dim_customer(customer_id),

    FOREIGN KEY (article_id)
        REFERENCES star_schema.dim_article(article_id),

    FOREIGN KEY (date_key)
        REFERENCES star_schema.dim_date(date_key),

    FOREIGN KEY (sales_channel_id)
        REFERENCES star_schema.dim_sale_channel(sales_channel_id),

    CHECK (price >= 0),
    CHECK (sales_revenue >= 0)
);

INSERT INTO star_schema.dim_sale_channel (
    sales_channel_id,
    sales_channel_name
)
VALUES
    (1, 'Store'),
    (2, 'Online')
ON CONFLICT (sales_channel_id) DO NOTHING;

