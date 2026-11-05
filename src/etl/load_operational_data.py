import os
from pathlib import Path

import psycopg2
from psycopg2 import sql
from dotenv import load_dotenv

from transform_raw_data import processed_csv
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


class _LimitedLineReader:
    """File-like wrapper that streams at most `max_lines` lines to psycopg2 copy_expert."""

    def __init__(self, file_obj, max_lines: int):
        self._file = file_obj
        self._remaining = max_lines
        self._buf = ""

    def read(self, size: int = -1) -> str:
        if size is None or size < 0:
            lines = [self._buf]
            self._buf = ""
            while self._remaining > 0:
                line = self._file.readline()
                if not line:
                    break
                lines.append(line)
                self._remaining -= 1
            return "".join(lines)

        while len(self._buf) < size and self._remaining > 0:
            line = self._file.readline()
            if not line:
                break
            self._buf += line
            self._remaining -= 1

        chunk, self._buf = self._buf[:size], self._buf[size:]
        return chunk

    def readline(self, size: int = -1) -> str:
        if self._remaining <= 0 and not self._buf:
            return ""
        if not self._buf and self._remaining > 0:
            line = self._file.readline()
            if line:
                self._remaining -= 1
            return line
        chunk, self._buf = self._buf, ""
        return chunk


def load_table(cur, table_name: str, max_rows: int | None = None):
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
        if max_rows is not None:
            # +1 line to include the CSV header row
            reader = _LimitedLineReader(f, max_rows + 1)
            cur.copy_expert(query, reader)
            print(f"[LOAD] {table_name} (mini: up to {max_rows:,} rows)")
        else:
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


def main(max_contains_rows: int | None = None):
    # processed_csv();
    print("Connecting to PostgreSQL...")

    conn = get_connection()

    try:
        with conn:
            with conn.cursor() as cur:

                print("Clearing existing data...")
                truncate_tables(cur)

                if max_contains_rows is not None:
                    print(f"Loading processed data (MINI mode: contains limited to {max_contains_rows:,} rows)...")
                else:
                    print("Loading processed data (FULL mode)...")

                for table in LOAD_ORDER:
                    limit = max_contains_rows if table == "contains" else None
                    load_table(cur, table, max_rows=limit)

                print("Database loading completed.")

    except Exception:
        print("Loading failed. Transaction rolled back.")
        raise

    finally:
        conn.close()


def load_mini(max_contains_rows: int = 1_000_000):
    """Load full lookup/entity/transaction tables and limit `contains` to `max_contains_rows`."""
    main(max_contains_rows=max_contains_rows)


if __name__ == "__main__":
    main()