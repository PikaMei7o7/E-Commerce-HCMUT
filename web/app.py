"""H&M Analytics Hub: kiểm thử tài khoản Postgres -> quyền trên view -> dashboard dùng được.

Chạy:  python app.py   (mặc định http://127.0.0.1:5050, chỉ nghe trên localhost)
Mật khẩu chỉ nằm trong RAM của tiến trình này, không ghi ra đĩa, không gửi lại trình duyệt.
Trình duyệt không bao giờ gửi SQL: chỉ gửi id widget + giá trị control đã whitelist (dashboard_catalog.py).
"""
import datetime
import decimal
import hashlib
import json
import os
import re
import secrets
import threading
import time
import uuid
import zipfile
from pathlib import Path

import psycopg2
from dotenv import load_dotenv
from flask import Flask, jsonify, make_response, request, send_file, send_from_directory

import dashboard_catalog as catalog

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT.parent / ".env")
load_dotenv(ROOT / ".env")
PBIX_FILE = ROOT.parent / "powerbi" / "hm_sales_report.pbix"

SESSION_TTL = 2 * 3600
CACHE_TTL = int(os.getenv("HM_CACHE_SECONDS", "600"))
QUERY_TIMEOUT_MS = int(os.getenv("HM_QUERY_TIMEOUT_MS", "600000"))
MAX_ROWS = 5000
IDENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_$]*$")

app = Flask(__name__, static_folder=str(ROOT / "static"), static_url_path="/static")
SESSIONS: dict[str, dict] = {}
CACHE: dict[str, tuple[float, dict]] = {}
INFLIGHT: dict[str, threading.Event] = {}
LOCK = threading.Lock()


# Helpers
def qident(name: str) -> str:
    if not name or '"' in name or "\x00" in name or len(name) > 63:
        raise ValueError("Invalid identifier")
    return '"' + name + '"'


def jsonable(v):
    if isinstance(v, decimal.Decimal):
        return float(v)
    if isinstance(v, (datetime.date, datetime.datetime)):
        return v.isoformat()
    if isinstance(v, uuid.UUID):
        return str(v)
    if isinstance(v, (bytes, memoryview)):
        return None
    return v


def err_text(e: Exception) -> str:
    msg = (getattr(e, "pgerror", None) or str(e) or e.__class__.__name__).strip()
    return msg.splitlines()[0][:300] if msg else e.__class__.__name__


def fail(status, message, **extra):
    return jsonify(error=message, **extra), status


def open_conn(sess, role=None):
    p = sess["params"]
    conn = psycopg2.connect(
        host=p["host"], port=p["port"], dbname=p["dbname"], user=p["user"], password=p["password"],
        sslmode=p["sslmode"], connect_timeout=10, application_name="hm_analytics_hub")
    conn.autocommit = True
    cur = conn.cursor()
    cur.execute(f"SET statement_timeout = {QUERY_TIMEOUT_MS}")
    cur.execute("SET default_transaction_read_only = on")
    role = role if role is not None else sess.get("role")
    if role:
        cur.execute("SET ROLE " + qident(role))
    return conn, cur


def get_session():
    tok = request.cookies.get("hm_session")
    now = time.time()
    with LOCK:
        for k in [k for k, s in SESSIONS.items() if now - s["last"] > SESSION_TTL]:
            SESSIONS.pop(k, None)
        s = SESSIONS.get(tok or "")
        if s:
            s["last"] = now
        return s


@app.before_request
def guard():
    # Chặn CSRF cơ bản: POST phải là JSON (form cross-site không gửi được content-type này nếu không có preflight).
    if request.method == "POST" and not request.is_json:
        return fail(415, "Request must be JSON")
    return None


# Kiểm tra quyền
def check_access(cur, schema: str) -> dict:
    """Trả về quyền của current_user trên 12 view (cấp view + cấp cột) và khả năng dùng từng dashboard."""
    cur.execute("SELECT current_user, session_user, "
                "COALESCE((SELECT rolsuper FROM pg_roles WHERE rolname = current_user), false), version(), "
                "EXISTS (SELECT 1 FROM pg_namespace WHERE nspname = %(s)s)", {"s": schema})
    cu, su, is_super, version, schema_exists = cur.fetchone()
    schema_usage = False
    if schema_exists:
        cur.execute("SELECT has_schema_privilege(current_user, %(s)s, 'USAGE')", {"s": schema})
        schema_usage = bool(cur.fetchone()[0])
    cur.execute("SELECT r.rolname FROM pg_roles r WHERE r.rolname !~ '^pg_' AND r.rolname <> current_user "
                "AND pg_has_role(current_user, r.oid, 'USAGE') ORDER BY 1")
    member_of = [r[0] for r in cur.fetchall()]

    objects: dict[str, dict] = {}
    if schema_exists:
        cur.execute(
            "SELECT c.relname, c.relkind, has_table_privilege(c.oid, 'SELECT'), a.attname, "
            "       has_column_privilege(c.oid, a.attnum, 'SELECT') "
            "FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace "
            "LEFT JOIN pg_attribute a ON a.attrelid = c.oid AND a.attnum > 0 AND NOT a.attisdropped "
            "WHERE n.nspname = %(s)s AND c.relkind IN ('v', 'm', 'r', 'p') AND c.relname = ANY(%(names)s)",
            {"s": schema, "names": list(catalog.VIEWS) + catalog.BASE_TABLES})
        for relname, relkind, tbl_sel, attname, col_ok in cur.fetchall():
            o = objects.setdefault(relname, {"kind": relkind, "table_select": bool(tbl_sel), "columns": {}})
            if attname:
                o["columns"][attname] = bool(col_ok)

    S = qident(schema)
    views = []
    for name, expected in catalog.VIEWS.items():
        o = objects.get(name)
        v = {"name": name, "exists": o is not None, "table_select": bool(o and o["table_select"]),
             "columns": [], "missing_columns": [], "probe": None}
        if o:
            for c in expected:
                if c in o["columns"]:
                    v["columns"].append({"name": c, "ok": o["columns"][c]})
                else:
                    v["missing_columns"].append(c)
            ok_cols = [c["name"] for c in v["columns"] if c["ok"]]
            if ok_cols and schema_usage:
                try:  # thực sự gọi view: bắt lỗi quyền ở bảng gốc / security_invoker
                    cur.execute("SELECT " + ", ".join(qident(c) for c in ok_cols) + f" FROM {S}.{qident(name)} WHERE false")
                    cur.fetchall()
                    v["probe"] = {"ok": True}
                except psycopg2.Error as e:
                    v["probe"] = {"ok": False, "error": err_text(e)}
        n_ok = sum(1 for c in v["columns"] if c["ok"])
        n_tot = len(v["columns"])
        if not o:
            v["status"] = "missing"
        elif not schema_usage or n_ok == 0:
            v["status"] = "denied"
        elif v["probe"] and not v["probe"]["ok"]:
            v["status"] = "error"
        elif n_ok < len(expected):
            v["status"] = "partial"
        else:
            v["status"] = "ok"
        v["cols_ok"], v["cols_total"] = n_ok, len(expected)
        views.append(v)
    by_name = {v["name"]: v for v in views}

    dashboards = []
    for d in catalog.DASHBOARDS:
        wl = []
        for w in d["widgets"]:
            reasons = widget_reasons(w, by_name, schema_exists, schema_usage, schema)
            wl.append({"id": w["id"], "title": w["title"], "available": not reasons, "reasons": reasons,
                       "views": [u[0] for u in w["uses"]]})
        n_av = sum(1 for w in wl if w["available"])
        dashboards.append({"id": d["id"], "title": d["title"], "desc": d["desc"], "icon": d["icon"],
                           "status": "full" if n_av == len(wl) else ("partial" if n_av else "locked"),
                           "available": n_av, "total": len(wl), "widgets": wl,
                           "views": sorted({u[0] for w in d["widgets"] for u in w["uses"]})})
    for v in views:
        v["used_by"] = [d["id"] for d in dashboards if v["name"] in d["views"]]

    tables = []
    for t in catalog.BASE_TABLES:
        o = objects.get(t)
        tables.append({"name": t, "exists": o is not None, "select": bool(o and o["table_select"])})
    return {"identity": {"current_user": cu, "session_user": su, "superuser": bool(is_super), "member_of": member_of,
                         "server": version.split(" on ")[0], "schema": schema, "schema_exists": bool(schema_exists),
                         "schema_usage": schema_usage},
            "views": views, "tables": tables, "dashboards": dashboards}


def widget_reasons(w, by_name, schema_exists, schema_usage, schema):
    out = []
    if not schema_exists:
        return [f"Schema {schema} does not exist"]
    if not schema_usage:
        return [f"No USAGE privilege on schema {schema}"]
    for view, cols in w["uses"]:
        v = by_name[view]
        if v["status"] == "missing":
            out.append(f"View {view} does not exist"); continue
        if v["status"] == "denied":
            out.append(f"No SELECT privilege on {view}"); continue
        if v["status"] == "error":
            out.append(f"{view}: {v['probe']['error']}"); continue
        have = {c["name"]: c["ok"] for c in v["columns"]}
        gone = [c for c in cols if c not in have]
        noacc = [c for c in cols if c in have and not have[c]]
        if gone:
            out.append(f"{view} is missing columns: {', '.join(gone)}")
        if noacc:
            out.append(f"No read privilege on columns {', '.join(noacc)} of {view}")
    return out


def schema_from(sess) -> str:
    return sess["params"]["schema"]


# API
@app.get("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


@app.get("/api/defaults")
def defaults():
    return jsonify(host=os.getenv("DB_HOST", ""), port=os.getenv("DB_PORT", "5432"), dbname=os.getenv("DB_NAME", ""),
                   user=os.getenv("DB_USER", ""), schema=catalog.DEFAULT_SCHEMA, sslmode=os.getenv("DB_SSLMODE", "prefer"))


@app.post("/api/connect")
def connect():
    b = request.get_json(silent=True) or {}
    p = {"host": str(b.get("host", "")).strip(), "port": str(b.get("port") or "5432").strip(),
         "dbname": str(b.get("dbname", "")).strip(), "user": str(b.get("user", "")).strip(),
         "password": str(b.get("password", "")), "sslmode": str(b.get("sslmode") or "prefer"),
         "schema": str(b.get("schema") or catalog.DEFAULT_SCHEMA).strip()}
    role = str(b.get("role") or "").strip() or None
    if not (p["host"] and p["dbname"] and p["user"]):
        return fail(400, "Host, database and user are required")
    if not p["port"].isdigit():
        return fail(400, "Port must be a number")
    if p["sslmode"] not in ("disable", "allow", "prefer", "require", "verify-ca", "verify-full"):
        return fail(400, "Invalid sslmode")
    if not IDENT.match(p["schema"]):
        return fail(400, "Invalid schema name")
    sess = {"params": p, "role": role, "last": time.time()}
    try:
        conn, cur = open_conn(sess)
    except (psycopg2.Error, ValueError) as e:
        return fail(401, "Could not connect: " + err_text(e))
    try:
        result = check_access(cur, p["schema"])
    except psycopg2.Error as e:
        return fail(500, "Connected, but the permission check failed: " + err_text(e))
    finally:
        conn.close()
    tok = secrets.token_urlsafe(32)
    with LOCK:
        sess["access"] = result
        SESSIONS[tok] = sess
    resp = jsonify(result)
    resp.set_cookie("hm_session", tok, httponly=True, samesite="Strict", max_age=SESSION_TTL)
    return resp


@app.post("/api/disconnect")
def disconnect():
    tok = request.cookies.get("hm_session")
    with LOCK:
        SESSIONS.pop(tok or "", None)
    resp = jsonify(ok=True)
    resp.delete_cookie("hm_session")
    return resp


@app.get("/api/me")
def me():
    s = get_session()
    if not s:
        return jsonify(connected=False)
    return jsonify(connected=True, access=s["access"], host=s["params"]["host"], dbname=s["params"]["dbname"])


@app.post("/api/recheck")
def recheck():
    s = get_session()
    if not s:
        return fail(401, "Session expired, please reconnect")
    try:
        conn, cur = open_conn(s)
        try:
            s["access"] = check_access(cur, schema_from(s))
        finally:
            conn.close()
    except psycopg2.Error as e:
        return fail(500, err_text(e))
    return jsonify(s["access"])


@app.post("/api/compare")
def compare():
    """So sánh nhiều role: dùng SET ROLE (cần tài khoản đăng nhập là thành viên các role đó, hoặc superuser)."""
    s = get_session()
    if not s:
        return fail(401, "Session expired, please reconnect")
    roles = [str(r).strip() for r in (request.get_json(silent=True) or {}).get("roles", []) if str(r).strip()][:12]
    if not roles:
        return fail(400, "Enter at least one role")
    out = []
    for role in roles:
        try:
            conn, cur = open_conn(s, role=role)
        except (psycopg2.Error, ValueError) as e:
            out.append({"role": role, "error": err_text(e)}); continue
        try:
            a = check_access(cur, schema_from(s))
            out.append({"role": role, "identity": a["identity"],
                        "views": {v["name"]: v["status"] for v in a["views"]},
                        "dashboards": {d["id"]: {"status": d["status"], "available": d["available"], "total": d["total"]}
                                       for d in a["dashboards"]}})
        except psycopg2.Error as e:
            out.append({"role": role, "error": err_text(e)})
        finally:
            conn.close()
    return jsonify(results=out, view_order=list(catalog.VIEWS),
                   dashboards=[{"id": d["id"], "title": d["title"]} for d in catalog.DASHBOARDS])


def _parse_pbir_proj(proj: dict) -> dict | None:
    f = proj.get("field", {})
    label = proj.get("nativeQueryRef") or proj.get("queryRef", "")
    qref = proj.get("queryRef", "")
    if "Column" in f:
        c = f["Column"]
        entity = c.get("Expression", {}).get("SourceRef", {}).get("Entity", "")
        prop = c.get("Property", "")
        return {"entity": entity, "prop": prop, "agg": None, "label": label, "queryRef": qref}
    if "Aggregation" in f:
        ag = f["Aggregation"]
        c = ag.get("Expression", {}).get("Column", {})
        entity = c.get("Expression", {}).get("SourceRef", {}).get("Entity", "")
        prop = c.get("Property", "")
        func = int(ag.get("Function", 0))
        return {"entity": entity, "prop": prop, "agg": func, "label": label, "queryRef": qref}
    return None


def _agg_sql(prop: str, agg: int | None) -> str:
    col = qident(prop)
    if agg is None:
        return col
    if agg == 0:
        return f"SUM({col})"
    if agg == 1:
        return f"AVG({col})"
    if agg == 2:
        return f"COUNT(DISTINCT {col})"
    if agg == 3:
        return f"MIN({col})"
    if agg == 4:
        return f"MAX({col})"
    if agg == 5:
        return f"COUNT({col})"
    return f"SUM({col})"


def read_pbix_pages() -> list[dict]:
    """Đọc trực tiếp cấu trúc 4 trang và các visual từ file powerbi/hm_sales_report.pbix."""
    if not PBIX_FILE.is_file():
        return []
    try:
        with zipfile.ZipFile(PBIX_FILE, "r") as z:
            pages_meta = json.loads(z.read("Report/definition/pages/pages.json").decode("utf-8"))
            page_order = pages_meta.get("pageOrder", [])
            names = set(z.namelist())
            out = []
            for idx, pid in enumerate(page_order, start=1):
                p_path = f"Report/definition/pages/{pid}/page.json"
                if p_path not in names:
                    continue
                p_obj = json.loads(z.read(p_path).decode("utf-8"))
                prefix = f"Report/definition/pages/{pid}/visuals/"
                v_files = [n for n in names if n.startswith(prefix) and n.endswith("/visual.json")]
                visuals = []
                for vf in v_files:
                    v_obj = json.loads(z.read(vf).decode("utf-8"))
                    pos = v_obj.get("position", {})
                    vis = v_obj.get("visual", {})
                    qstate = vis.get("query", {}).get("queryState", {})
                    roles = {}
                    fields = []
                    for role_name, role_data in qstate.items():
                        parsed_list = []
                        for proj in role_data.get("projections", []):
                            p_info = _parse_pbir_proj(proj)
                            if p_info:
                                parsed_list.append(p_info)
                                fields.append(p_info)
                        roles[role_name] = parsed_list
                    sort_defs = vis.get("query", {}).get("sortDefinition", {}).get("sort", [])
                    sort_by_cat = False
                    if sort_defs and "Column" in sort_defs[0].get("field", {}):
                        sort_by_cat = True
                    visuals.append({
                        "name": v_obj.get("name", ""),
                        "visualType": vis.get("visualType", "visual"),
                        "x": pos.get("x", 0),
                        "y": pos.get("y", 0),
                        "width": pos.get("width", 200),
                        "height": pos.get("height", 150),
                        "z": pos.get("z", 0),
                        "fields": fields,
                        "roles": roles,
                        "sort_by_cat": sort_by_cat,
                    })
                visuals.sort(key=lambda item: (item["y"], item["x"], item["z"]))
                out.append({
                    "page_number": idx,
                    "id": pid,
                    "displayName": p_obj.get("displayName", f"Page {idx}"),
                    "width": p_obj.get("width", 1920),
                    "height": p_obj.get("height", 1080),
                    "visuals": visuals,
                })
            return out
    except Exception:
        return []


@app.get("/api/powerbi/download")
def download_pbix():
    if not PBIX_FILE.is_file():
        return fail(404, f"{PBIX_FILE.name} file not found")
    return send_file(PBIX_FILE, as_attachment=True, download_name=PBIX_FILE.name)


@app.get("/api/powerbi/data/<page_id>/<visual_name>")
def pbix_visual_data(page_id, visual_name):
    s = get_session()
    if not s:
        return fail(401, "Session expired, please reconnect")
    pages = read_pbix_pages()
    page = next((p for p in pages if p["id"] == page_id), None)
    vis = next((v for v in (page["visuals"] if page else []) if v["name"] == visual_name), None)
    if not vis or not vis["fields"]:
        return fail(404, "Power BI visual not found")

    entity = vis["fields"][0]["entity"]
    if entity not in catalog.VIEWS:
        return fail(400, f"Unsupported entity in PBIX: {entity}")
    allowed_cols = set(catalog.VIEWS[entity])
    used_cols = []
    for f in vis["fields"]:
        if f["entity"] != entity or f["prop"] not in allowed_cols:
            return fail(400, f"Invalid column {f['entity']}.{f['prop']}")
        if f["prop"] not in used_cols:
            used_cols.append(f["prop"])

    # Áp dụng bộ lọc từ các Slicer trên cùng trang (nếu có)
    where, args = ["TRUE"], {}
    for k, val in request.args.items():
        if k.startswith("slicer_") and val != "" and val != "all":
            scol = k[len("slicer_"):]
            if scol in allowed_cols:
                where.append(f"{qident(scol)}::text = %({k})s")
                args[k] = val
                if scol not in used_cols:
                    used_cols.append(scol)

    # Kiểm tra quyền của tài khoản hiện tại trên view & các cột
    by_name = {v["name"]: v for v in s["access"]["views"]}
    id_info = s["access"]["identity"]
    reasons = widget_reasons({"uses": [(entity, used_cols)]}, by_name, id_info["schema_exists"], id_info["schema_usage"], id_info["schema"])
    if reasons:
        return fail(403, "This account cannot read this Power BI visual", reasons=reasons)

    S = qident(schema_from(s))
    W = " AND ".join(where)
    vtype = vis["visualType"]
    roles = vis["roles"]

    if vtype == "cardVisual":
        f0 = roles.get("Data", vis["fields"])[0]
        sql = f"SELECT {_agg_sql(f0['prop'], f0['agg'])} AS val FROM {S}.{qident(entity)} WHERE {W}"
    elif vtype == "slicer":
        f0 = roles.get("Values", vis["fields"])[0]
        sql = f"SELECT DISTINCT {qident(f0['prop'])} AS val FROM {S}.{qident(entity)} WHERE {qident(f0['prop'])} IS NOT NULL ORDER BY 1 LIMIT 50"
    elif vtype in ("lineChart", "donutChart", "clusteredBarChart", "clusteredColumnChart"):
        cat = roles.get("Category", [vis["fields"][0]])[0]
        y = roles.get("Y", [vis["fields"][-1]])[0]
        if vtype == "lineChart" or vis.get("sort_by_cat"):
            order = "1 ASC"
        else:
            order = "2 DESC NULLS LAST"
        limit = "" if vtype == "lineChart" else " LIMIT 18"
        sql = f"SELECT {qident(cat['prop'])} AS x, {_agg_sql(y['prop'], y['agg'])} AS y FROM {S}.{qident(entity)} WHERE {W} GROUP BY 1 ORDER BY {order}{limit}"
    elif vtype == "pivotTable":
        r = roles.get("Rows", [vis["fields"][0]])[0]
        c = roles.get("Columns", [vis["fields"][1]])[0]
        v = roles.get("Values", [vis["fields"][-1]])[0]
        sql = f"SELECT {qident(r['prop'])} AS r, {qident(c['prop'])} AS c, {_agg_sql(v['prop'], v['agg'])} AS v FROM {S}.{qident(entity)} WHERE {W} GROUP BY 1, 2"
    elif vtype == "tableEx":
        vals = roles.get("Values", vis["fields"])
        sel = [f"{_agg_sql(f['prop'], f['agg'])} AS c{i}" for i, f in enumerate(vals)]
        grp = [str(i + 1) for i, f in enumerate(vals) if f["agg"] is None]
        has_agg = any(f["agg"] is not None for f in vals)
        grp_sql = f" GROUP BY {', '.join(grp)}" if (grp and has_agg) else ""
        first_agg_idx = next((i + 1 for i, f in enumerate(vals) if f["agg"] is not None), 1)
        order_sql = f"{first_agg_idx} DESC NULLS LAST" if has_agg else "1 ASC"
        sql = f"SELECT {', '.join(sel)} FROM {S}.{qident(entity)} WHERE {W}{grp_sql} ORDER BY {order_sql} LIMIT 50"
    else:
        return fail(400, f"Unsupported visualType: {vtype}")

    ident = f'{s["params"]["host"]}|{s["params"]["dbname"]}|{s["access"]["identity"]["current_user"]}|pbix|{page_id}|{visual_name}'
    key = hashlib.sha256(json.dumps([ident, sql, args], sort_keys=True, default=str).encode()).hexdigest()
    now = time.time()
    hit = CACHE.get(key)
    if hit and now - hit[0] < CACHE_TTL and request.args.get("refresh") != "1":
        return jsonify(hit[1] | {"cached": True, "age": int(now - hit[0])})
    return run_widget_query(s, sql, args, key)


@app.get("/api/catalog")
def get_catalog():
    s = get_session()
    if not s:
        return fail(401, "Session expired, please reconnect")
    pbix_pages = read_pbix_pages()
    dashes = []
    for idx, d in enumerate(catalog.DASHBOARDS):
        pbix_page = pbix_pages[idx] if idx < len(pbix_pages) else None
        dashes.append({k: d[k] for k in ("id", "title", "icon", "desc", "controls")} | {
            "widgets": [{k: v for k, v in w.items() if k not in ("sql", "uses")} for w in d["widgets"]],
            "pbix_page": pbix_page,
        })
    return jsonify(dashboards=dashes)


def norm_controls(dash, args):
    """Chuẩn hóa tham số về giá trị đã whitelist."""
    out = {}
    for c in catalog.CTRL.values():
        v = args.get(c["name"], c["default"])
        if c["type"] == "select":
            allowed = [str(o[0] if isinstance(o, list) else o) for o in c["options"]]
            v = str(v)
            if v not in allowed:
                v = str(c["default"])
            if c["name"] == "top_n":
                v = int(v)
        else:
            v = str(v).strip()[: c.get("maxlen", 80)]
        out[c["name"]] = v
    return out


@app.get("/api/data/<dash_id>/<widget_id>")
def widget_data(dash_id, widget_id):
    s = get_session()
    if not s:
        return fail(401, "Session expired, please reconnect")
    d = catalog.DASH_BY_ID.get(dash_id)
    w = next((x for x in d["widgets"] if x["id"] == widget_id), None) if d else None
    if not w:
        return fail(404, "Widget not found")
    dw = next(x for x in s["access"]["dashboards"] if x["id"] == dash_id)
    wa = next(x for x in dw["widgets"] if x["id"] == widget_id)
    if not wa["available"]:
        return fail(403, "This account cannot use this widget", reasons=wa["reasons"])
    p = norm_controls(d, request.args)
    for need in w.get("needs", []):
        if not p.get(need):
            return fail(400, "Missing required value: " + need)
    sql, args = w["sql"](qident(schema_from(s)), p)
    ident = f'{s["params"]["host"]}|{s["params"]["dbname"]}|{s["access"]["identity"]["current_user"]}'
    key = hashlib.sha256(json.dumps([ident, sql, args], sort_keys=True, default=str).encode()).hexdigest()
    now = time.time()
    hit = CACHE.get(key)
    if hit and now - hit[0] < CACHE_TTL and request.args.get("refresh") != "1":
        return jsonify(hit[1] | {"cached": True, "age": int(now - hit[0])})
    # Cùng truy vấn đang chạy (vd: rời dashboard rồi quay lại khi truy vấn cũ chưa xong):
    # chờ kết quả của lần chạy đó thay vì chạy thêm một truy vấn nặng nữa.
    with LOCK:
        ev = INFLIGHT.get(key)
        owner = ev is None
        if owner:
            ev = INFLIGHT[key] = threading.Event()
    if not owner:
        ev.wait(QUERY_TIMEOUT_MS / 1000 + 15)
        hit = CACHE.get(key)
        if hit:
            return jsonify(hit[1] | {"cached": True, "age": int(time.time() - hit[0])})
    try:
        return run_widget_query(s, sql, args, key)
    finally:
        if owner:
            with LOCK:
                INFLIGHT.pop(key, None)
            ev.set()


def run_widget_query(s, sql, args, key):
    now = t0 = time.time()
    try:
        conn, cur = open_conn(s)
    except (psycopg2.Error, ValueError) as e:
        return fail(502, "Connection lost: " + err_text(e))
    try:
        cur.execute(sql, args)
        cols = [c[0] for c in cur.description] if cur.description else []
        rows = cur.fetchmany(MAX_ROWS)
    except psycopg2.Error as e:
        code = getattr(e, "pgcode", "")
        if code == "42501":
            return fail(403, "Insufficient privileges: " + err_text(e))
        if code == "57014":
            return fail(504, f"Query exceeded {QUERY_TIMEOUT_MS // 1000}s and was cancelled. Try narrowing the filters or increase HM_QUERY_TIMEOUT_MS.")
        return fail(500, "Query error: " + err_text(e))
    finally:
        conn.close()
    payload = {"columns": cols, "rows": [[jsonable(v) for v in r] for r in rows],
               "ms": int((time.time() - t0) * 1000), "truncated": len(rows) >= MAX_ROWS}
    if len(CACHE) > 300:
        CACHE.clear()
    CACHE[key] = (now, payload)
    return jsonify(payload | {"cached": False})


if __name__ == "__main__":
    port = int(os.getenv("HM_PORT", "5050"))
    print(f"H&M Analytics Hub: http://127.0.0.1:{port}")
    app.run(host="127.0.0.1", port=port, debug=False, threaded=True)
