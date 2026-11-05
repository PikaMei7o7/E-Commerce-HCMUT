"""Compare a restored recovery database against the original and write a text report.

The report (backups/verification_<recovery_db>_<timestamp>.txt) lists every difference in plain
English, e.g. "public.contains: recovery DB is missing 1,204 rows". Exit code is 0 on PASS, 1 otherwise.
"""
import os
import sys
from datetime import datetime
from pathlib import Path

import psycopg2
from psycopg2 import sql
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")

DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")

RECOVERY_DB = "hm-ecommerce-recovery"
SCHEMAS = ("public", "star_schema")
REPORT_DIR = ROOT / "backups"

# (schema, table, order-by column): first rows are compared value by value
SAMPLE_TABLES = [
    ("public", "customer", "customer_id"),
    ("public", "article", "article_id"),
    ("public", "product", "product_code"),
    ("star_schema", "dim_customer", "customer_id"),
    ("star_schema", "dim_article", "article_id"),
]
SAMPLE_SIZE = 5

CONSTRAINT_TYPES = {"p": "primary key", "f": "foreign key", "u": "unique", "c": "check", "n": "not null", "x": "exclusion"}


def connect(database):
    return psycopg2.connect(host=DB_HOST, port=DB_PORT, dbname=database, user=DB_USER,
                            password=DB_PASSWORD, connect_timeout=20, application_name="hm_verify_restore")


def get_tables(conn, schema):
    with conn.cursor() as cur:
        cur.execute("SELECT table_name FROM information_schema.tables "
                    "WHERE table_schema = %s AND table_type = 'BASE TABLE'", (schema,))
        return {row[0] for row in cur.fetchall()}


def get_row_count(conn, schema, table):
    with conn.cursor() as cur:
        cur.execute(sql.SQL("SELECT COUNT(*) FROM {}.{}").format(sql.Identifier(schema), sql.Identifier(table)))
        return cur.fetchone()[0]


def get_constraints(conn, schema):
    """{(table, constraint_name): type}; names survive pg_dump/pg_restore, so they can be matched."""
    with conn.cursor() as cur:
        cur.execute("""
            SELECT cl.relname, co.conname, co.contype
            FROM pg_constraint co
            JOIN pg_class cl ON cl.oid = co.conrelid
            JOIN pg_namespace n ON n.oid = cl.relnamespace
            WHERE n.nspname = %s
        """, (schema,))
        return {(t, name): CONSTRAINT_TYPES.get(kind, kind) for t, name, kind in cur.fetchall()}


def get_indexes(conn, schema):
    with conn.cursor() as cur:
        cur.execute("SELECT tablename, indexname FROM pg_indexes WHERE schemaname = %s", (schema,))
        return set(cur.fetchall())


def get_sample(conn, schema, table, order_col):
    with conn.cursor() as cur:
        cur.execute(sql.SQL("SELECT * FROM {}.{} ORDER BY {} LIMIT %s").format(
            sql.Identifier(schema), sql.Identifier(table), sql.Identifier(order_col)), (SAMPLE_SIZE,))
        return cur.fetchall()


def run_representative_query(conn):
    with conn.cursor() as cur:
        cur.execute("""
            SELECT c.customer_id, a.prod_name, SUM(ct.price * ct.quantity) AS total_revenue
            FROM public."transaction" AS t
            JOIN public.customer AS c ON t.customer_id = c.customer_id
            JOIN public.contains AS ct ON t.transaction_id = ct.transaction_id
            JOIN public.article AS a ON ct.article_id = a.article_id
            GROUP BY c.customer_id, a.prod_name
            ORDER BY total_revenue DESC, c.customer_id, a.prod_name
            LIMIT 10
        """)
        return cur.fetchall()


def plural(n, word):
    if n == 1:
        return f"{n:,} {word}"
    return f"{n:,} {word}" + ("es" if word.endswith(("x", "s", "ch")) else "s")


def verify():
    started = datetime.now()
    report_file = REPORT_DIR / f"verification_{RECOVERY_DB}_{started:%Y%m%d_%H%M%S}.txt"
    issues, warnings, sections = [], [], []
    original_conn = recovery_conn = None

    def section(title, rows):
        sections.append(("", title, *rows))

    try:
        missing_env = [k for k, v in {"DB_HOST": DB_HOST, "DB_NAME": DB_NAME, "DB_USER": DB_USER,
                                      "DB_PASSWORD": DB_PASSWORD}.items() if not v]
        if missing_env:
            raise ValueError("Missing environment variable(s): " + ", ".join(missing_env))
        original_conn = connect(DB_NAME)
        recovery_conn = connect(RECOVERY_DB)
        for c in (original_conn, recovery_conn):
            c.set_session(readonly=True)

        # 1. tables
        tables, rows = {}, []
        for schema in SCHEMAS:
            orig, rec = get_tables(original_conn, schema), get_tables(recovery_conn, schema)
            tables[schema] = sorted(orig & rec)
            rows.append(f"  {schema}: {plural(len(orig), 'table')} in original, {len(rec):,} in recovery")
            if not orig:
                warnings.append(f"Schema {schema} has no tables in the original DB (nothing to compare)")
            for t in sorted(orig - rec):
                issues.append(f"{schema}.{t}: table is missing in recovery DB")
                rows.append(f"    MISSING  {t}")
            for t in sorted(rec - orig):
                warnings.append(f"{schema}.{t}: table exists only in recovery DB")
                rows.append(f"    EXTRA    {t}")
        section("[1] Tables", rows)

        # 2. row counts
        width = max([len(f"{s}.{t}") for s in tables for t in tables[s]] + [20]) + 2
        rows = [f"  {'Table':<{width}}{'Original':>15}{'Recovery':>15}{'Difference':>13}  Status"]
        for schema in SCHEMAS:
            for t in tables[schema]:
                name = f"{schema}.{t}"
                try:
                    o, r = get_row_count(original_conn, schema, t), get_row_count(recovery_conn, schema, t)
                except psycopg2.Error as e:
                    original_conn.rollback(); recovery_conn.rollback()
                    issues.append(f"{name}: could not count rows ({str(e).strip()})")
                    rows.append(f"  {name:<{width}}{'?':>15}{'?':>15}{'':>13}  ERROR")
                    continue
                diff = r - o
                if diff < 0:
                    status = f"MISSING {-diff:,} rows"
                    issues.append(f"{name}: recovery DB is missing {plural(-diff, 'row')} "
                                  f"(original {o:,}, recovery {r:,})")
                elif diff > 0:
                    status = f"EXTRA {diff:,} rows"
                    issues.append(f"{name}: recovery DB has {plural(diff, 'extra row')} "
                                  f"(original {o:,}, recovery {r:,})")
                else:
                    status = "OK"
                rows.append(f"  {name:<{width}}{o:>15,}{r:>15,}{diff:>+13,}  {status}")
        section("[2] Row counts", rows)

        # 3. constraints and 4. indexes, matched by name
        rows_c, rows_i = [], []
        for schema in SCHEMAS:
            oc, rc = get_constraints(original_conn, schema), get_constraints(recovery_conn, schema)
            lost = sorted(set(oc) - set(rc))
            rows_c.append(f"  {schema}: {plural(len(oc), 'constraint')} in original, {len(rc):,} in recovery")
            for t, name in lost:
                issues.append(f"{schema}.{t}: {oc[(t, name)]} constraint {name} is missing in recovery DB")
                rows_c.append(f"    MISSING  {t}.{name} ({oc[(t, name)]})")
            for t, name in sorted(set(rc) - set(oc)):
                warnings.append(f"{schema}.{t}: constraint {name} exists only in recovery DB")
                rows_c.append(f"    EXTRA    {t}.{name} ({rc[(t, name)]})")

            oi, ri = get_indexes(original_conn, schema), get_indexes(recovery_conn, schema)
            rows_i.append(f"  {schema}: {plural(len(oi), 'index')} in original, {len(ri):,} in recovery")
            for t, name in sorted(oi - ri):
                issues.append(f"{schema}.{t}: index {name} is missing in recovery DB")
                rows_i.append(f"    MISSING  {t}.{name}")
            for t, name in sorted(ri - oi):
                warnings.append(f"{schema}.{t}: index {name} exists only in recovery DB")
                rows_i.append(f"    EXTRA    {t}.{name}")
        section("[3] Constraints", rows_c)
        section("[4] Indexes", rows_i)

        # 5. sample rows
        rows = []
        for schema, t, col in SAMPLE_TABLES:
            name = f"{schema}.{t}"
            if t not in tables.get(schema, []):
                rows.append(f"  SKIP  {name:<{width}}table not present in both databases")
                continue
            try:
                o, r = get_sample(original_conn, schema, t, col), get_sample(recovery_conn, schema, t, col)
            except psycopg2.Error as e:
                original_conn.rollback(); recovery_conn.rollback()
                issues.append(f"{name}: sample query failed ({str(e).strip()})")
                rows.append(f"  FAIL  {name:<{width}}sample query failed")
                continue
            if o == r:
                rows.append(f"  OK    {name:<{width}}first {len(o)} rows (ordered by {col}) are identical")
            else:
                bad = sum(1 for a, b in zip(o, r) if a != b) + abs(len(o) - len(r))
                verb = "differs" if bad == 1 else "differ"
                issues.append(f"{name}: {plural(bad, 'sample row')} of the first {SAMPLE_SIZE} {verb} (ordered by {col})")
                rows.append(f"  FAIL  {name:<{width}}{plural(bad, 'sample row')} {verb}")
        section("[5] Sample rows", rows)

        # 6. representative query
        try:
            o, r = run_representative_query(original_conn), run_representative_query(recovery_conn)
            if o == r:
                rows = [f"  OK    top-10 revenue query returns identical results ({plural(len(o), 'row')})"]
            else:
                issues.append("Representative query (top-10 revenue by customer and product) returns different results")
                rows = ["  FAIL  top-10 revenue query results differ"]
        except psycopg2.Error as e:
            issues.append(f"Representative query failed ({str(e).strip()})")
            rows = ["  FAIL  query could not run"]
        section("[6] Representative query", rows)

    except Exception as e:
        issues.append(f"Verification stopped early: {str(e).strip()}")
    finally:
        for c in (original_conn, recovery_conn):
            if c is not None:
                c.close()

    finished = datetime.now()
    passed = not issues
    lines = [
        "Database recovery verification report",
        "",
        f"Original DB  : {DB_NAME}",
        f"Recovery DB  : {RECOVERY_DB}",
        f"Host         : {DB_HOST}:{DB_PORT}",
        f"Schemas      : {', '.join(SCHEMAS)}",
        f"Run at       : {started:%Y-%m-%d %H:%M:%S} ({(finished - started).total_seconds():.0f}s)",
        f"Result       : {'PASS' if passed else 'FAIL'}"
        + ("" if passed else f" ({plural(len(issues), 'issue')})"),
        "",
        "Issues",
        *([f"  {i}. {msg}" for i, msg in enumerate(issues, 1)] or ["  None. The recovery database matches the original."]),
    ]
    if warnings:
        lines += ["", "Warnings (not counted as failures)", *[f"  - {w}" for w in warnings]]
    for block in sections:
        lines += list(block)
    lines.append("")

    REPORT_DIR.mkdir(exist_ok=True)
    report_file.write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))
    print(f"Report saved to {report_file}")
    return passed, report_file


if __name__ == "__main__":
    ok, _ = verify()
    sys.exit(0 if ok else 1)
