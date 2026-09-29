import os
from pathlib import Path

import psycopg2
from psycopg2 import sql
from dotenv import load_dotenv

from etl import processed_csv
load_dotenv()

ROOT = Path(__file__).resolve().parents[2]
PROCESSED_DIR = ROOT / "data" / "processed"

# Parent tables must be loaded before child tables
LOAD_ORDER = [
    "product_group",
    "product_type",
    "product",

    "graphical_appearance",
    "colour_group",
    "perceived_colour_value",
    "perceived_colour_master",

    "department",
    "garment_group",
    "index_group",
    "article_index",
    "section",

    "customer",
    "article",
    "transaction",
    "contains",
]


def get_connection():
    return psycopg2.connect(
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT", "5432"),
        database=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
    )


def load_table(cur, table_name: str):
    file_path = PROCESSED_DIR / f"{table_name}.csv"

    if not file_path.exists():
        raise FileNotFoundError(
            f"Processed file not found: {file_path}"
        )

    query = sql.SQL(
        """
        COPY {} FROM STDIN
        WITH (
            FORMAT CSV,
            HEADER TRUE,
            NULL ''
        )
        """
    ).format(sql.Identifier(table_name))

    with file_path.open("r", encoding="utf-8", newline="") as f:
        cur.copy_expert(query, f)

    print(f"[LOAD] {table_name}")


def truncate_tables(cur):
    tables = [
        sql.Identifier(table)
        for table in LOAD_ORDER
    ]

    query = sql.SQL(
        "TRUNCATE TABLE {} RESTART IDENTITY CASCADE"
    ).format(sql.SQL(", ").join(tables))

    cur.execute(query)


def main():
    # processed_csv();
    print("Connecting to PostgreSQL...")

    conn = get_connection()

    try:
        with conn:
            with conn.cursor() as cur:

                print("Clearing existing data...")
                truncate_tables(cur)

                print("Loading processed data...")

                for table in LOAD_ORDER:
                    load_table(cur, table)

                print("Database loading completed.")

    except Exception:
        print("Loading failed. Transaction rolled back.")
        raise

    finally:
        conn.close()


if __name__ == "__main__":
    main()