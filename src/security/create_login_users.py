"""Create or update the login accounts that belong to the group roles of
sql/security/roles_and_grants.sql. Passwords come from .env, never from git.

    python -m src.security.create_login_users      (main.py runs it after roles_and_grants.sql)

An account whose password variable is empty is skipped. Running it again only resets the
password, the attributes and the membership, so the result is always the same.
"""

import logging
import os
from pathlib import Path

import psycopg2
from dotenv import load_dotenv
from psycopg2 import sql

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")
log = logging.getLogger("access")

GROUP_ROLES = ("hm_analyst_base", "hm_product_sales_analyst", "hm_customer_analyst")

# The 2 analyst logins: (user env var, default login name, password env var, group role)
LOGIN_USERS = (
    ("HM_PRODUCT_ANALYST_USER", "hm_product_analyst_01", "HM_PRODUCT_ANALYST_PASSWORD",
     "hm_product_sales_analyst"),
    ("HM_CUSTOMER_ANALYST_USER", "hm_customer_analyst_01", "HM_CUSTOMER_ANALYST_PASSWORD",
     "hm_customer_analyst"),
)



def login_name(user_env: str, default: str) -> str:
    return os.getenv(user_env) or default


def get_connection():
    required = ("DB_HOST", "DB_NAME", "DB_USER", "DB_PASSWORD")
    missing = [key for key in required if not os.getenv(key)]
    if missing:
        raise RuntimeError("Missing .env settings: " + ", ".join(missing))
    return psycopg2.connect(
        host=os.environ["DB_HOST"], port=os.getenv("DB_PORT", "5432"),
        dbname=os.environ["DB_NAME"], user=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"], connect_timeout=20,
        application_name="hm_access_setup",
    )


def _apply_user(cur, name: str, password: str, group: str) -> None:
    ident = sql.Identifier(name)
    cur.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", (name,))
    if cur.fetchone() is None:
        # Defaults: NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS. They cannot be
        # restated in ALTER ROLE by a non-superuser owner (Cloud SQL), so they are set only here.
        cur.execute(sql.SQL("CREATE ROLE {} LOGIN").format(ident))
    # psycopg2 sends the password as a quoted literal; it is never logged.
    # CONNECTION LIMIT -1 = no limit (also clears the limit of 10 set by earlier versions).
    cur.execute(sql.SQL(
        "ALTER ROLE {} LOGIN INHERIT NOCREATEROLE CONNECTION LIMIT -1 PASSWORD %s"
    ).format(ident), (password,))

    # Exactly one hm_* group: drop memberships left over from an earlier setup.
    cur.execute(
        "SELECT g.rolname FROM pg_auth_members m "
        "JOIN pg_roles g ON g.oid = m.roleid JOIN pg_roles u ON u.oid = m.member "
        "WHERE u.rolname = %s AND g.rolname = ANY(%s) AND g.rolname <> %s",
        (name, list(GROUP_ROLES), group))
    for (old_group,) in cur.fetchall():
        cur.execute(sql.SQL("REVOKE {} FROM {}").format(sql.Identifier(old_group), ident))
    cur.execute(sql.SQL("GRANT {} TO {}").format(sql.Identifier(group), ident))

    # Second safety net after the grants: an analyst session cannot write even by mistake.
    cur.execute(sql.SQL("ALTER ROLE {} SET default_transaction_read_only = on").format(ident))
    # No query time limit: clear the 10-minute limit set by earlier versions of this script.
    cur.execute(sql.SQL("ALTER ROLE {} RESET statement_timeout").format(ident))


def create_login_users() -> list[str]:
    """Create/update every account whose password is set in .env. Returns the login names."""
    done: list[str] = []
    conn = get_connection()
    try:
        with conn, conn.cursor() as cur:
            cur.execute("SELECT rolname FROM pg_roles WHERE rolname = ANY(%s)", (list(GROUP_ROLES),))
            missing = sorted(set(GROUP_ROLES) - {r for (r,) in cur.fetchall()})
            if missing:
                raise RuntimeError(
                    f"Group roles missing: {', '.join(missing)}. Run sql/security/roles_and_grants.sql first "
                    "(main.py with DATABASE_ACCESS_CREATE = 1); it needs the star schema and views to exist.")
            for user_env, default, pw_env, group in LOGIN_USERS:
                name = login_name(user_env, default)
                password = os.getenv(pw_env, "")
                if not password:
                    log.info("[ACCESS] %s is empty in .env: login %s not created/updated", pw_env, name)
                    continue
                _apply_user(cur, name, password, group)
                log.info("[ACCESS] Login %s -> %s (read-only)", name, group)
                done.append(name)
    finally:
        conn.close()
    return done


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s",
                        datefmt="%H:%M:%S")
    create_login_users()
