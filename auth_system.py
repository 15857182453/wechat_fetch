"""
Dashboard 多用户权限认证系统
- 多账号登录（用户名 + 密码）
- 按医院过滤数据可见性
- admin 看全部，其他账号只能看授权医院
"""
import streamlit as st
import hashlib
import json
import sqlite3
import pandas as pd
from datetime import datetime

DB_PATH = "/home/openclaw/.openclaw/workspace/business_flow.db"

# ════════════════════════════════════════════
# 数据库初始化
# ════════════════════════════════════════════
def init_users_table():
    """创建用户表并初始化默认账号"""
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS dashboard_users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'viewer',
            display_name TEXT,
            allowed_institutions TEXT,
            hidden_tabs TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            is_active INTEGER DEFAULT 1
        )
    """)
    # 初始化 admin（密码: admin）
    admin_hash = hashlib.sha256("admin".encode()).hexdigest()
    cur.execute("""
        INSERT OR IGNORE INTO dashboard_users
            (username, password_hash, role, display_name, allowed_institutions)
        VALUES (?, ?, 'admin', '系统管理员', NULL)
    """, ("admin", admin_hash))

    # 初始化测试账号：青岛中心医院只读
    qd_hash = hashlib.sha256("qingdao123".encode()).hexdigest()
    cur.execute("""
        INSERT OR IGNORE INTO dashboard_users
            (username, password_hash, role, display_name, allowed_institutions)
        VALUES (?, ?, 'viewer', '青岛中心医院', '["青岛中心医院"]')
    """, ("qingdao", qd_hash))

    conn.commit()
    conn.close()

# ════════════════════════════════════════════
# 认证核心
# ════════════════════════════════════════════
def _hash_password(pwd: str) -> str:
    return hashlib.sha256(pwd.encode()).hexdigest()

def _verify_user(username: str, password: str) -> dict | None:
    """验证用户名密码，返回用户信息或 None"""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        "SELECT username, role, display_name, allowed_institutions, hidden_tabs, is_active "
        "FROM dashboard_users WHERE username = ? AND password_hash = ?",
        (username, _hash_password(password))
    )
    row = cur.fetchone()
    conn.close()
    if row and row[5] == 1:  # is_active
        return {
            "username": row[0],
            "role": row[1],
            "display_name": row[2],
            "allowed_institutions": json.loads(row[3]) if row[3] else None,
            "hidden_tabs": json.loads(row[4]) if row[4] else [],
        }
    return None

# ════════════════════════════════════════════
# 权限工具函数
# ════════════════════════════════════════════
def get_current_user() -> dict | None:
    """获取当前登录用户信息"""
    return st.session_state.get("_current_user", None)

def filter_dataframe(df: pd.DataFrame, institution_column: str = "institution") -> pd.DataFrame:
    """
    根据当前用户权限过滤 DataFrame。
    admin 返回原数据，其他账号只返回授权医院的数据。
    如果 DataFrame 中没有 institution 列，返回原数据。
    """
    if df is None or df.empty:
        return df
    if institution_column not in df.columns:
        return df
    inst = get_allowed_institutions()
    if inst is None:  # admin
        return df
    return df[df[institution_column].isin(inst)]

def is_admin() -> bool:
    return st.session_state.get("_current_user", {}).get("role") == "admin"

def get_allowed_institutions() -> list | None:
    """返回当前用户可访问的医院列表，None = 全部"""
    user = get_current_user()
    if not user:
        return None
    return user.get("allowed_institutions")

def get_hidden_tabs() -> list:
    """返回当前用户不可见的 Tab 名称列表"""
    user = get_current_user()
    if not user:
        return []
    return user.get("hidden_tabs", [])

def build_institution_filter() -> tuple[str, list]:
    """
    返回 SQL WHERE 片段和参数列表
    用法: sql = f"SELECT ... FROM table {build_institution_filter()[0]} ..."
    """
    inst = get_allowed_institutions()
    if inst is None:  # admin
        return "", []
    placeholders = ",".join(["?"] * len(inst))
    return f" WHERE institution IN ({placeholders})", inst

# ════════════════════════════════════════════
# 登录页面
# ════════════════════════════════════════════
def authenticate() -> dict:
    """
    显示登录页面，验证后返回用户信息 dict。
    已登录则直接返回用户信息。
    调用后如果返回了，说明已认证，可以继续加载 Dashboard。
    """
    init_users_table()

    if st.session_state.get("_current_user"):
        return st.session_state._current_user

    # 页面样式
    st.markdown("""
    <style>
        [data-testid="stAppViewContainer"] { background-color: #F8FAFC; }
    </style>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 3, 1])
    with col2:
        st.markdown("### 运营数据仪表板")
        st.caption("请输入用户名和密码")
        st.divider()

        username = st.text_input("用户名", key="login_user", label_visibility="collapsed")
        password = st.text_input("密码", type="password", key="login_pwd", label_visibility="collapsed")

        if st.button("登录", type="primary", use_container_width=True):
            if username and password:
                user = _verify_user(username, password)
                if user:
                    st.session_state._current_user = user
                    st.rerun()
                else:
                    st.error("用户名或密码错误")
            else:
                st.error("请输入用户名和密码")

        st.markdown('<div style="color:#CBD5E1;font-size:12px;text-align:center;margin-top:24px;">OpenClaw Dashboard System</div>', unsafe_allow_html=True)

    st.stop()
    return {}  # never reached
