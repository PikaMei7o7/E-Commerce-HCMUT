"""Danh mục 12 view + dashboard + truy vấn (toàn bộ SQL cố định, tham số hóa).

Trình duyệt KHÔNG gửi SQL: chỉ gửi id widget + giá trị control đã được whitelist ở đây.
Mỗi widget khai báo `uses` (view + cột nó đọc) để app biết tài khoản hiện tại có dùng được không.
"""

DEFAULT_SCHEMA = "star_schema"

# Bảng gốc của star schema (chỉ để hiển thị thông tin quyền, dashboard không đọc trực tiếp)
BASE_TABLES = ["dim_customer", "dim_article", "dim_date", "dim_sale_channel", "fact_sales"]

VIEWS = {
    "vw_sales_detail": [
        "transaction_id", "customer_id", "article_id", "full_date", "date_key", "day", "month", "quarter",
        "year", "day_of_week", "sales_channel_id", "sales_channel_name", "price_base", "product_code",
        "prod_name", "product_type_no", "prod_type_name", "product_group_name", "graphical_appearance_no",
        "colour_group_code", "perceived_colour_value_id", "perceived_colour_master_id", "department_no",
        "garment_group_no", "index_code", "index_group_no", "section_no", "age", "age_group",
        "club_member_status", "active", "fn", "fashion_news_frequency", "price", "quantity", "sales_revenue"],
    "vw_sales_kpi": [
        "total_revenue", "total_units_sold", "total_transactions", "distinct_articles_sold",
        "purchasing_customers", "total_customers_in_dimension", "average_order_value",
        "average_spending_per_purchasing_customer"],
    "vw_monthly_sales": [
        "year", "month", "month_start_date", "total_revenue", "total_units_sold", "total_transactions",
        "purchasing_customers", "average_order_value"],
    "vw_daily_customer_trend": [
        "full_date", "active_customers", "total_units_sold", "total_revenue", "avg_units_per_customer",
        "avg_spending_per_customer"],
    "vw_product_performance": [
        "product_code", "prod_name", "product_type_no", "prod_type_name", "product_group_name",
        "total_units_sold", "total_revenue", "total_transactions", "unique_customers", "revenue_per_unit"],
    "vw_product_group_performance": [
        "product_group_name", "total_units_sold", "total_revenue", "total_transactions", "unique_customers",
        "revenue_per_unit"],
    "vw_product_type_performance": [
        "product_type_no", "product_type_name", "total_units_sold", "total_revenue", "total_transactions",
        "distinct_articles_sold", "unique_customers"],
    "vw_sales_by_channel": [
        "sales_channel_id", "sales_channel_name", "total_revenue", "total_units_sold", "total_transactions",
        "unique_customers", "average_order_value"],
    "vw_customer_spending": [
        "customer_id", "age", "age_group", "club_member_status", "purchase_frequency",
        "total_units_purchased", "total_spending", "average_order_value"],
    "vw_customer_spending_by_segment": [
        "age_group", "club_member_status", "purchasing_customers", "total_units_sold", "total_revenue",
        "average_revenue_per_customer"],
    "vw_customer_product_group_preference": [
        "customer_id", "product_group_name", "total_quantity_purchased", "total_spending_in_group",
        "transactions_in_group"],
    "vw_customer_product_preference": [
        "customer_id", "article_id", "product_code", "prod_name", "product_type_no", "product_type_name",
        "product_group_name", "total_quantity_purchased", "total_spending_on_product", "purchase_frequency"],
}

AGE_ORDER = ("CASE age_group WHEN 'Under 20' THEN 1 WHEN '20-29' THEN 2 WHEN '30-39' THEN 3 "
             "WHEN '40-49' THEN 4 WHEN '50-59' THEN 5 WHEN '60+' THEN 6 ELSE 7 END")
AGE_GROUPS = ["Under 20", "20-29", "30-39", "40-49", "50-59", "60+", "Unknown"]
CLUB_STATUS = ["ACTIVE", "PRE-CREATE", "LEFT CLUB", "UNKNOWN"]


def _s(*pairs):
    """uses = [(view, [cols...]), ...]"""
    return [(v, list(c)) for v, c in pairs]


def M(label, col, fmt="money"):
    return {"col": col, "label": label, "fmt": fmt}


# 1. Tổng quan doanh số
def _sales_widgets():
    return [
        dict(id="kpi", title="Key metrics", kind="kpis", span=12,
             uses=_s(("vw_sales_kpi", ["total_revenue", "total_units_sold", "total_transactions",
                                       "purchasing_customers", "average_order_value",
                                       "average_spending_per_purchasing_customer"])),
             items=[M("Total revenue", "total_revenue"), M("Units sold", "total_units_sold", "int"),
                    M("Transactions", "total_transactions", "int"),
                    M("Purchasing customers", "purchasing_customers", "int"),
                    M("Avg. order value (AOV)", "average_order_value", "dec"),
                    M("Avg. spend / customer", "average_spending_per_purchasing_customer", "dec")],
             sql=lambda S, p: (f"SELECT total_revenue, total_units_sold, total_transactions, purchasing_customers,"
                               f" average_order_value, average_spending_per_purchasing_customer"
                               f" FROM {S}.vw_sales_kpi", {})),
        dict(id="monthly", title="Monthly trend", kind="line", span=12,
             uses=_s(("vw_monthly_sales", ["year", "month", "month_start_date", "total_revenue", "total_units_sold",
                                           "total_transactions", "purchasing_customers", "average_order_value"])),
             x="month_start_date", series=[M("Revenue", "total_revenue"), M("Units sold", "total_units_sold", "int"),
                                           M("Transactions", "total_transactions", "int"),
                                           M("Customers", "purchasing_customers", "int"),
                                           M("AOV", "average_order_value", "dec")],
             sql=lambda S, p: (f"SELECT month_start_date, total_revenue, total_units_sold, total_transactions,"
                               f" purchasing_customers, average_order_value FROM {S}.vw_monthly_sales"
                               f" ORDER BY year, month", {})),
        dict(id="channel", title="Sales channel (Store vs Online)", kind="donut", span=5,
             uses=_s(("vw_sales_by_channel", ["sales_channel_name", "total_revenue", "total_units_sold",
                                              "total_transactions", "unique_customers"])),
             label="sales_channel_name", series=[M("Revenue", "total_revenue"), M("Units sold", "total_units_sold", "int"),
                                                 M("Transactions", "total_transactions", "int"),
                                                 M("Customers", "unique_customers", "int")],
             sql=lambda S, p: (f"SELECT sales_channel_name, total_revenue, total_units_sold, total_transactions,"
                               f" unique_customers FROM {S}.vw_sales_by_channel ORDER BY sales_channel_id", {})),
        dict(id="daily", title="Daily trend", kind="line", span=7,
             uses=_s(("vw_daily_customer_trend", ["full_date", "active_customers", "total_revenue",
                                                  "avg_spending_per_customer", "total_units_sold"])),
             x="full_date", series=[M("Revenue", "total_revenue"), M("Active customers", "active_customers", "int"),
                                    M("Avg. spend / customer", "avg_spending_per_customer", "dec"),
                                    M("Units sold", "total_units_sold", "int")],
             sql=lambda S, p: (f"SELECT full_date, total_revenue, active_customers, avg_spending_per_customer,"
                               f" total_units_sold FROM {S}.vw_daily_customer_trend ORDER BY full_date", {})),
    ]


# 2. Hiệu suất sản phẩm
PRODUCT_SORT = {"revenue": "total_revenue", "units": "total_units_sold", "customers": "unique_customers",
                "per_unit": "revenue_per_unit"}


def _product_widgets():
    def top_types(S, p):
        return (f"SELECT product_type_name, total_revenue, total_units_sold, unique_customers, distinct_articles_sold"
                f" FROM {S}.vw_product_type_performance"
                f" ORDER BY {PRODUCT_SORT.get(p['sort'], 'total_revenue')} DESC NULLS LAST LIMIT %(n)s", {"n": p["top_n"]})

    def top_products(S, p):
        return (f"SELECT prod_name, total_revenue, total_units_sold, unique_customers, revenue_per_unit"
                f" FROM {S}.vw_product_performance WHERE (%(q)s = '' OR prod_name ILIKE %(like)s)"
                f" ORDER BY {PRODUCT_SORT.get(p['sort'], 'total_revenue')} DESC NULLS LAST LIMIT %(n)s",
                {"q": p["q"], "like": "%" + p["q"] + "%", "n": p["top_n"]})

    def table(S, p):
        return (f"SELECT prod_name, prod_type_name, product_group_name, total_units_sold, total_revenue,"
                f" unique_customers, revenue_per_unit FROM {S}.vw_product_performance"
                f" WHERE (%(q)s = '' OR prod_name ILIKE %(like)s)"
                f" ORDER BY {PRODUCT_SORT.get(p['sort'], 'total_revenue')} DESC NULLS LAST LIMIT 100",
                {"q": p["q"], "like": "%" + p["q"] + "%"})
    return [
        dict(id="kpi", title="Product overview", kind="kpis", span=12,
             uses=_s(("vw_product_group_performance", ["product_group_name", "total_revenue", "total_units_sold"]),
                     ("vw_product_type_performance", ["product_type_no"])),
             items=[M("Revenue", "total_revenue"), M("Units sold", "total_units_sold", "int"),
                    M("Product groups", "groups", "int"), M("Product types", "types", "int")],
             sql=lambda S, p: (f"SELECT (SELECT SUM(total_revenue) FROM {S}.vw_product_group_performance) AS total_revenue,"
                               f" (SELECT SUM(total_units_sold) FROM {S}.vw_product_group_performance) AS total_units_sold,"
                               f" (SELECT COUNT(*) FROM {S}.vw_product_group_performance) AS groups,"
                               f" (SELECT COUNT(*) FROM {S}.vw_product_type_performance) AS types", {})),
        dict(id="groups", title="Performance by product group", kind="bar", span=6, horizontal=True,
             uses=_s(("vw_product_group_performance", ["product_group_name", "total_revenue", "total_units_sold",
                                                       "unique_customers", "revenue_per_unit"])),
             x="product_group_name", series=[M("Revenue", "total_revenue"), M("Units sold", "total_units_sold", "int"),
                                             M("Customers", "unique_customers", "int"),
                                             M("Revenue / unit", "revenue_per_unit", "dec")],
             sql=lambda S, p: (f"SELECT product_group_name, total_revenue, total_units_sold, unique_customers,"
                               f" revenue_per_unit FROM {S}.vw_product_group_performance"
                               f" ORDER BY total_revenue DESC NULLS LAST", {})),
        dict(id="types", title="Top product types", kind="bar", span=6, horizontal=True, use_controls=["top_n", "sort"],
             uses=_s(("vw_product_type_performance", ["product_type_name", "total_revenue", "total_units_sold",
                                                      "unique_customers", "distinct_articles_sold", "product_type_no"])),
             x="product_type_name", series=[M("Revenue", "total_revenue"), M("Units sold", "total_units_sold", "int"),
                                            M("Customers", "unique_customers", "int")],
             sql=top_types),
        dict(id="top_products", title="Top products", kind="bar", span=12, horizontal=True, use_controls=["top_n", "sort", "q"],
             uses=_s(("vw_product_performance", ["prod_name", "total_revenue", "total_units_sold", "unique_customers",
                                                 "revenue_per_unit"])),
             x="prod_name", series=[M("Revenue", "total_revenue"), M("Units sold", "total_units_sold", "int"),
                                    M("Customers", "unique_customers", "int"), M("Revenue / unit", "revenue_per_unit", "dec")],
             sql=top_products),
        dict(id="table", title="Product detail table (max 100 rows)", kind="table", span=12, use_controls=["sort", "q"],
             uses=_s(("vw_product_performance", ["prod_name", "prod_type_name", "product_group_name", "total_units_sold",
                                                 "total_revenue", "unique_customers", "revenue_per_unit"])),
             columns=[M("Product", "prod_name", "text"), M("Type", "prod_type_name", "text"),
                      M("Group", "product_group_name", "text"), M("Units", "total_units_sold", "int"),
                      M("Revenue", "total_revenue"), M("Customers", "unique_customers", "int"),
                      M("Rev. / unit", "revenue_per_unit", "dec")],
             sql=table),
    ]


# 3. Phân khúc khách hàng
def _segment_widgets():
    def by_age(S, p):
        return (f"SELECT age_group, SUM(purchasing_customers) AS customers, SUM(total_revenue) AS revenue,"
                f" SUM(total_units_sold) AS units,"
                f" SUM(total_revenue) / NULLIF(SUM(purchasing_customers), 0) AS avg_per_customer"
                f" FROM {S}.vw_customer_spending_by_segment GROUP BY age_group ORDER BY {AGE_ORDER}", {})

    def by_club(S, p):
        return (f"SELECT club_member_status, SUM(purchasing_customers) AS customers, SUM(total_revenue) AS revenue,"
                f" SUM(total_units_sold) AS units,"
                f" SUM(total_revenue) / NULLIF(SUM(purchasing_customers), 0) AS avg_per_customer"
                f" FROM {S}.vw_customer_spending_by_segment GROUP BY club_member_status ORDER BY revenue DESC", {})
    seg_cols = ["age_group", "club_member_status", "purchasing_customers", "total_units_sold", "total_revenue",
                "average_revenue_per_customer"]
    return [
        dict(id="kpi", title="Customer overview", kind="kpis", span=12,
             uses=_s(("vw_customer_spending_by_segment", seg_cols)),
             items=[M("Purchasing customers", "customers", "int"), M("Total revenue", "revenue"),
                    M("Avg. revenue / customer", "avg_per_customer", "dec"), M("Units sold", "units", "int")],
             sql=lambda S, p: (f"SELECT SUM(purchasing_customers) AS customers, SUM(total_revenue) AS revenue,"
                               f" SUM(total_units_sold) AS units,"
                               f" SUM(total_revenue) / NULLIF(SUM(purchasing_customers), 0) AS avg_per_customer"
                               f" FROM {S}.vw_customer_spending_by_segment", {})),
        dict(id="age", title="By age group", kind="bar", span=7,
             uses=_s(("vw_customer_spending_by_segment", seg_cols)),
             x="age_group", series=[M("Revenue", "revenue"), M("Customers", "customers", "int"),
                                    M("Avg. revenue / customer", "avg_per_customer", "dec"), M("Units sold", "units", "int")],
             sql=by_age),
        dict(id="club", title="By club member status", kind="donut", span=5,
             uses=_s(("vw_customer_spending_by_segment", seg_cols)),
             label="club_member_status", series=[M("Customers", "customers", "int"), M("Revenue", "revenue"),
                                                 M("Units sold", "units", "int")],
             sql=by_club),
        dict(id="heat", title="Avg. revenue / customer: age group × club member status", kind="heat", span=12,
             uses=_s(("vw_customer_spending_by_segment", seg_cols)),
             rows="age_group", cols="club_member_status", value="average_revenue_per_customer", fmt="dec",
             row_order=AGE_GROUPS,
             sql=lambda S, p: (f"SELECT age_group, club_member_status, average_revenue_per_customer"
                               f" FROM {S}.vw_customer_spending_by_segment", {})),
        dict(id="freq", title="Purchase frequency distribution", kind="bar", span=6, heavy=True,
             uses=_s(("vw_customer_spending", ["purchase_frequency", "total_spending", "customer_id"])),
             x="bucket", series=[M("Customers", "customers", "int"), M("Total spending", "spending"),
                                 M("Avg. spend / customer", "avg_spending", "dec")],
             sql=lambda S, p: (
                 f"SELECT CASE WHEN purchase_frequency = 1 THEN '1 time' WHEN purchase_frequency <= 3 THEN '2-3 times'"
                 f" WHEN purchase_frequency <= 5 THEN '4-5 times' WHEN purchase_frequency <= 10 THEN '6-10 times'"
                 f" WHEN purchase_frequency <= 20 THEN '11-20 times' ELSE '21+ times' END AS bucket,"
                 f" COUNT(*) AS customers, SUM(total_spending) AS spending, AVG(total_spending) AS avg_spending,"
                 f" MIN(purchase_frequency) AS _o FROM {S}.vw_customer_spending GROUP BY 1 ORDER BY _o", {})),
        dict(id="top", title="Top 20 highest-spending customers", kind="table", span=6, heavy=True,
             uses=_s(("vw_customer_spending", ["customer_id", "age_group", "club_member_status", "purchase_frequency",
                                               "total_spending", "average_order_value"])),
             columns=[M("Customer (shortened)", "customer", "text"), M("Age", "age_group", "text"),
                      M("Membership", "club_member_status", "text"), M("Purchases", "purchase_frequency", "int"),
                      M("Total spending", "total_spending"), M("AOV", "average_order_value", "dec")],
             sql=lambda S, p: (f"SELECT LEFT(customer_id, 10) || '…' AS customer, age_group, club_member_status,"
                               f" purchase_frequency, total_spending, average_order_value"
                               f" FROM {S}.vw_customer_spending ORDER BY total_spending DESC NULLS LAST LIMIT 20", {})),
    ]


# 4. Khám phá doanh số (vw_sales_detail)
DIMENSIONS = {  # key: (nhãn, biểu thức select, order by)
    "month": ("Month", "make_date(year::int, month::int, 1)::text", "1"),
    "quarter": ("Quarter", "year::text || '-Q' || quarter::text", "1"),
    "year": ("Year", "year::text", "1"),
    "day_of_week": ("Day of week (1=Mon)", "day_of_week::text", "1"),
    "sales_channel_name": ("Sales channel", "sales_channel_name", "revenue DESC"),
    "product_group_name": ("Product group", "product_group_name", "revenue DESC"),
    "prod_type_name": ("Product type", "prod_type_name", "revenue DESC"),
    "age_group": ("Age group", "age_group", AGE_ORDER),
    "club_member_status": ("Club member status", "club_member_status", "revenue DESC"),
    "fashion_news_frequency": ("Fashion news frequency", "COALESCE(fashion_news_frequency, 'NULL')", "revenue DESC"),
    "index_group_no": ("Index group", "index_group_no::text", "revenue DESC"),
    "department_no": ("Department", "department_no::text", "revenue DESC"),
    "colour_group_code": ("Colour group", "colour_group_code::text", "revenue DESC"),
}


def _explorer_widgets():
    def q(S, p):
        label, expr, order = DIMENSIONS[p["dim"]]
        where, args = ["TRUE"], {}
        if p["year"] != "all":
            where.append("year = %(year)s"); args["year"] = int(p["year"])
        if p["channel"] != "all":
            where.append("sales_channel_name = %(channel)s"); args["channel"] = p["channel"]
        if p["age_group"] != "all":
            where.append("age_group = %(age)s"); args["age"] = p["age_group"]
        if p["club"] != "all":
            where.append("club_member_status = %(club)s"); args["club"] = p["club"]
        if p["group_like"]:
            where.append("product_group_name ILIKE %(g)s"); args["g"] = "%" + p["group_like"] + "%"
        sql = (f"SELECT {expr} AS dim, SUM(sales_revenue) AS revenue, SUM(quantity) AS units,"
               f" COUNT(DISTINCT transaction_id) AS transactions, COUNT(DISTINCT customer_id) AS customers"
               f" FROM {S}.vw_sales_detail WHERE {' AND '.join(where)} GROUP BY 1 ORDER BY {order} LIMIT 60")
        return sql, args
    cols = ["sales_revenue", "quantity", "transaction_id", "customer_id", "year", "month", "quarter", "day_of_week",
            "sales_channel_name", "product_group_name", "prod_type_name", "age_group", "club_member_status",
            "fashion_news_frequency", "index_group_no", "department_no", "colour_group_code"]
    return [
        dict(id="explore", title="Analyze by any dimension", kind="bar", span=12, heavy=True, apply_run=True, table=True,
             dynamic_x=True, use_controls=["dim", "year", "channel", "age_group", "club", "group_like"],
             uses=_s(("vw_sales_detail", cols)),
             x="dim", series=[M("Revenue", "revenue"), M("Units sold", "units", "int"),
                              M("Transactions", "transactions", "int"), M("Customers", "customers", "int")],
             note="Reads vw_sales_detail directly (~tens of millions of rows), so it may take tens of seconds.",
             sql=q),
    ]


def _sel(name, label, options, default):
    return dict(name=name, label=label, type="select", options=options, default=default)


CTRL = {
    "top_n": _sel("top_n", "Rows", [10, 15, 20, 30, 50], 15),
    "sort": dict(name="sort", label="Sort by", type="select", default="revenue",
                 options=[["revenue", "Revenue"], ["units", "Units sold"], ["customers", "Buyers"],
                          ["per_unit", "Revenue / unit"]]),
    "q": dict(name="q", label="Search product name", type="text", default="", placeholder="e.g. Jade"),
    "dim": dict(name="dim", label="Analyze by", type="select", default="month",
                options=[[k, v[0]] for k, v in DIMENSIONS.items()]),
    "year": dict(name="year", label="Year", type="select", default="all",
                 options=[["all", "All"], ["2018", "2018"], ["2019", "2019"], ["2020", "2020"]]),
    "channel": dict(name="channel", label="Channel", type="select", default="all",
                    options=[["all", "All"], ["Store", "Store"], ["Online", "Online"]]),
    "age_group": dict(name="age_group", label="Age group", type="select", default="all",
                      options=[["all", "All"]] + [[a, a] for a in AGE_GROUPS]),
    "club": dict(name="club", label="Membership", type="select", default="all",
                 options=[["all", "All"]] + [[c, c] for c in CLUB_STATUS]),
    "group_like": dict(name="group_like", label="Product group contains", type="text", default="", placeholder="e.g. Garment"),
}

DASHBOARDS = [
    dict(id="sales", title="Sales overview", icon="📈",
         desc="KPIs, monthly/daily trends and sales channel share.",
         controls=[], widgets=_sales_widgets()),
    dict(id="product", title="Product performance", icon="🧥",
         desc="Best-selling product groups, types and individual products.",
         controls=[CTRL["top_n"], CTRL["sort"], CTRL["q"]], widgets=_product_widgets()),
    dict(id="segments", title="Customer segments", icon="👥",
         desc="Age groups, membership, purchase frequency, top spenders.",
         controls=[], widgets=_segment_widgets()),
    dict(id="explorer", title="Sales explorer", icon="🔎",
         desc="Filter and group vw_sales_detail by any dimension (time, channel, age, product...).",
         controls=[CTRL["dim"], CTRL["year"], CTRL["channel"], CTRL["age_group"], CTRL["club"], CTRL["group_like"]],
         widgets=_explorer_widgets()),
]

DASH_BY_ID = {d["id"]: d for d in DASHBOARDS}
