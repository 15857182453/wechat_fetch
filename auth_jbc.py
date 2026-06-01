"""
金佰川鞋业看板 — 多用户权限认证系统
基于 auth_system.py 架构，适配 PostgreSQL 数据源
"""
import streamlit as st
import hashlib
import json
import sqlite3
import pandas as pd

DB_PATH = "/home/openclaw/.openclaw/workspace/jbc_users.db"

# ════════════════════════════════════════════
# 数据库初始化
# ════════════════════════════════════════════
def init_users_table():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS dashboard_users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'viewer',       -- admin / editor / viewer
            display_name TEXT,
            allowed_stores TEXT,                        -- JSON: ["门店A","门店B"] 或 null=全部
            allowed_brands TEXT,                        -- JSON: ["品牌A","品牌B"] 或 null=全部
            hidden_tabs TEXT,                           -- JSON: ["Tab名"]
            created_at TEXT DEFAULT (datetime('now')),
            is_active INTEGER DEFAULT 1
        )
    """)
    # 默认 admin
    admin_hash = hashlib.sha256("admin".encode()).hexdigest()
    cur.execute("""
        INSERT OR IGNORE INTO dashboard_users
            (username, password_hash, role, display_name)
        VALUES (?, ?, 'admin', '系统管理员')
    """, ("admin", admin_hash))

    # 测试账号：大区经理（只看部分门店）
    viewer_hash = hashlib.sha256("jbc2026".encode()).hexdigest()
    cur.execute("""
        INSERT OR IGNORE INTO dashboard_users
            (username, password_hash, role, display_name, allowed_stores)
        VALUES (?, ?, 'viewer', '西北大区经理',
            '["武威店","武威浙大店","武威万达店","张掖煌嘉店","张掖南大街店"]')
    """, ("xibei", viewer_hash))

    conn.commit()
    conn.close()

# ════════════════════════════════════════════
# 认证
# ════════════════════════════════════════════
def _hash_password(pwd: str) -> str:
    return hashlib.sha256(pwd.encode()).hexdigest()

def _verify_user(username: str, password: str) -> dict | None:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        "SELECT username, role, display_name, allowed_stores, allowed_brands, hidden_tabs, is_active "
        "FROM dashboard_users WHERE username = ? AND password_hash = ?",
        (username, _hash_password(password))
    )
    row = cur.fetchone()
    conn.close()
    if row and row[6] == 1:
        return {
            "username": row[0],
            "role": row[1],
            "display_name": row[2],
            "allowed_stores": json.loads(row[3]) if row[3] else None,
            "allowed_brands": json.loads(row[4]) if row[4] else None,
            "hidden_tabs": json.loads(row[5]) if row[5] else [],
        }
    return None

# ════════════════════════════════════════════
# 权限工具
# ════════════════════════════════════════════
def get_current_user() -> dict | None:
    return st.session_state.get("_jbc_user", None)

def is_admin() -> bool:
    return get_current_user().get("role") == "admin" if get_current_user() else False

def get_allowed_stores() -> list | None:
    """返回当前用户可访问的门店列表，None=全部"""
    user = get_current_user()
    if not user: return None
    return user.get("allowed_stores")

def get_allowed_brands() -> list | None:
    """返回当前用户可访问的品牌列表，None=全部"""
    user = get_current_user()
    if not user: return None
    return user.get("allowed_brands")

def get_hidden_tabs() -> list:
    user = get_current_user()
    if not user: return []
    return user.get("hidden_tabs", [])

def filter_dataframe(df: pd.DataFrame, store_col: str = "store_name", brand_col: str = "brand_name") -> pd.DataFrame:
    """根据当前用户权限过滤 DataFrame"""
    if df is None or df.empty:
        return df
    user = get_current_user()
    if not user or user.get("role") == "admin":
        return df

    stores = user.get("allowed_stores")
    brands = user.get("allowed_brands")

    if stores and store_col in df.columns:
        df = df[df[store_col].isin(stores)]
    if brands and brand_col in df.columns:
        df = df[df[brand_col].isin(brands)]
    return df

def build_store_filter() -> tuple[str, list]:
    """返回 SQL WHERE 片段和参数"""
    user = get_current_user()
    if not user or user.get("role") == "admin":
        return "", []
    stores = user.get("allowed_stores")
    if not stores:
        return "", []
    placeholders = ",".join(["%s"] * len(stores))
    return f" AND store_name IN ({placeholders})", stores

# ════════════════════════════════════════════
# 用户管理（admin 用）
# ════════════════════════════════════════════
def get_all_users() -> list:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT id, username, role, display_name, allowed_stores, allowed_brands, hidden_tabs, is_active FROM dashboard_users ORDER BY id")
    rows = cur.fetchall()
    conn.close()
    return rows

def add_user(username: str, password: str, role: str, display_name: str, allowed_stores: list = None, allowed_brands: list = None, hidden_tabs: list = None):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO dashboard_users (username, password_hash, role, display_name, allowed_stores, allowed_brands, hidden_tabs)
        VALUES (?,?,?,?,?,?,?)
    """, (
        username, _hash_password(password), role, display_name,
        json.dumps(allowed_stores) if allowed_stores else None,
        json.dumps(allowed_brands) if allowed_brands else None,
        json.dumps(hidden_tabs) if hidden_tabs else None
    ))
    conn.commit()
    conn.close()

def update_user(user_id: int, **kwargs):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    for k, v in kwargs.items():
        if k in ('allowed_stores', 'allowed_brands', 'hidden_tabs'):
            v = json.dumps(v) if v else None
        if k == 'password':
            cur.execute("UPDATE dashboard_users SET password_hash=? WHERE id=?", (_hash_password(v), user_id))
        else:
            cur.execute(f"UPDATE dashboard_users SET {k}=? WHERE id=?", (v, user_id))
    conn.commit()
    conn.close()

def toggle_user_active(user_id: int):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("UPDATE dashboard_users SET is_active = 1 - is_active WHERE id=?", (user_id,))
    conn.commit()
    conn.close()

# ════════════════════════════════════════════
# 登录页面
# ════════════════════════════════════════════
def authenticate() -> dict:
    """显示登录页面，返回用户信息"""
    init_users_table()

    if st.session_state.get("_jbc_user"):
        return st.session_state._jbc_user

    st.markdown("""
    <style>
        [data-testid="stAppViewContainer"] { background-color: #F8FAFC; }
        [data-testid="stHeader"] { display: none; }
    </style>
    """, unsafe_allow_html=True)

    # 垂直居中布局
    st.markdown("<div style='height:15vh'></div>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("### 🏪 金佰川运营数据看板")
        st.caption("请输入用户名和密码")
        st.divider()

        username = st.text_input("用户名", key="login_user", label_visibility="collapsed", placeholder="用户名")
        password = st.text_input("密码", type="password", key="login_pwd", label_visibility="collapsed", placeholder="密码")

        if st.button("登 录", type="primary", use_container_width=True):
            if username and password:
                user_result = _verify_user(username, password)
                if user_result:
                    st.session_state._jbc_user = user_result
                    st.rerun()
                else:
                    st.error("用户名或密码错误")
            else:
                st.error("请输入用户名和密码")

        st.markdown("""
        <div style="color:#CBD5E1;font-size:12px;text-align:center;margin-top:24px;">
        默认账号: admin / admin &nbsp;|&nbsp; 测试账号: xibei / jbc2026
        </div>
        """, unsafe_allow_html=True)

    st.stop()
    return {}
