#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Dashboard 用户管理后台
端口 8507，仅 admin 可访问
"""
import streamlit as st
import hashlib
import json
import sqlite3
import pandas as pd
from datetime import datetime

DB_PATH = "/home/openclaw/.openclaw/workspace/business_flow.db"

st.set_page_config(page_title="用户管理后台", page_icon="⚙️", layout="wide")

# ════════════════════════════════════════════
# 认证检查
# ════════════════════════════════════════════
def _hash_password(pwd: str) -> str:
    return hashlib.sha256(pwd.encode()).hexdigest()

def _verify_admin(username: str, password: str) -> bool:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        "SELECT role, is_active FROM dashboard_users WHERE username = ? AND password_hash = ?",
        (username, _hash_password(password))
    )
    row = cur.fetchone()
    conn.close()
    return row and row[0] == 'admin' and row[1] == 1

def ensure_admin():
    if st.session_state.get("_admin_auth"):
        return True

    st.markdown("""
    <style>
        .login-card { background: #fff; border-radius: 8px; padding: 40px 32px;
            box-shadow: 0 2px 12px rgba(0,0,0,0.08); max-width: 400px; margin: 80px auto; text-align: center; }
        .login-card h1 { font-size: 20px; color: #1E3A8A; }
        .login-error { background: #FEF2F2; color: #DC2626; padding: 8px 12px;
            border-radius: 6px; font-size: 13px; margin-top: 12px; border-left: 3px solid #DC2626; }
    </style>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown('<div class="login-card"><h1>🔐 管理后台登录</h1><p style="color:#64748B;font-size:14px;">仅管理员可访问</p>', unsafe_allow_html=True)
        username = st.text_input("管理员用户名", key="mgmt_user")
        password = st.text_input("密码", type="password", key="mgmt_pwd")
        if st.button("登录", type="primary", use_container_width=True):
            if _verify_admin(username, password):
                st.session_state._admin_auth = username
                st.rerun()
            else:
                st.markdown('<div class="login-error">认证失败，仅 admin 可访问</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
    st.stop()

# ════════════════════════════════════════════
# 工具函数
# ════════════════════════════════════════════
def get_all_users():
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query("SELECT id, username, role, display_name, allowed_institutions, hidden_tabs, is_active, created_at FROM dashboard_users ORDER BY id", conn)
    # 解析 JSON 字段
    def safe_json(s):
        if not s or not isinstance(s, str): return "-"
        try: return ", ".join(json.loads(s))
        except: return str(s)
    df["可访问医院"] = df["allowed_institutions"].apply(safe_json)
    df["隐藏Tab"] = df["hidden_tabs"].apply(safe_json)
    df["状态"] = df["is_active"].map({1: "✅ 启用", 0: "❌ 禁用"})
    conn.close()
    return df

def get_all_hospital_names():
    """获取所有唯一的医院名称，用于下拉选择"""
    conn = sqlite3.connect(DB_PATH)
    tables = ['daily_flow_2026_jan', 'daily_flow_2026_feb', 'daily_flow_2026_mar', 'daily_flow_2026_apr', 'daily_flow_2026_may']
    results = set()
    for t in tables:
        try:
            cur = conn.cursor()
            cur.execute(f"SELECT DISTINCT institution FROM {t}")
            for row in cur.fetchall():
                results.add(row[0])
        except:
            pass
    conn.close()
    return sorted(results)

def add_user(username, password, role, display_name, institutions, hidden_tabs):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    inst_json = json.dumps(institutions, ensure_ascii=False) if institutions else None
    tabs_json = json.dumps(hidden_tabs, ensure_ascii=False) if hidden_tabs else None
    try:
        cur.execute(
            "INSERT INTO dashboard_users (username, password_hash, role, display_name, allowed_institutions, hidden_tabs) VALUES (?, ?, ?, ?, ?, ?)",
            (username, _hash_password(password), role, display_name, inst_json, tabs_json)
        )
        conn.commit()
        conn.close()
        return True, "用户创建成功"
    except sqlite3.IntegrityError:
        conn.close()
        return False, "用户名已存在"
    except Exception as e:
        conn.close()
        return False, str(e)

def update_user(user_id, password=None, role=None, display_name=None, institutions=None, hidden_tabs=None, is_active=None):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    updates = []
    params = []
    if password:
        updates.append("password_hash = ?")
        params.append(_hash_password(password))
    if role:
        updates.append("role = ?")
        params.append(role)
    if display_name is not None:
        updates.append("display_name = ?")
        params.append(display_name)
    if institutions is not None:
        updates.append("allowed_institutions = ?")
        params.append(json.dumps(institutions, ensure_ascii=False) if institutions else None)
    if hidden_tabs is not None:
        updates.append("hidden_tabs = ?")
        params.append(json.dumps(hidden_tabs, ensure_ascii=False) if hidden_tabs else None)
    if is_active is not None:
        updates.append("is_active = ?")
        params.append(is_active)

    if updates:
        params.append(user_id)
        cur.execute(f"UPDATE dashboard_users SET {', '.join(updates)} WHERE id = ?", params)
        conn.commit()
    conn.close()
    return True, "更新成功"

def delete_user(user_id):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("DELETE FROM dashboard_users WHERE id = ? AND username != 'admin'", (user_id,))
    conn.commit()
    affected = cur.rowcount
    conn.close()
    if affected > 0:
        return True, "用户已删除"
    else:
        return False, "无法删除 admin 账号或用户不存在"

# ════════════════════════════════════════════
# 主界面
# ════════════════════════════════════════════
ensure_admin()

st.title("⚙️ 用户管理后台")
st.caption("管理 Dashboard 登录账号和权限")

tab_list, tab_add, tab_edit = st.tabs(["👥 用户列表", "➕ 新增用户", "✏️ 编辑/删除"])

# ── Tab 1: 用户列表 ──
with tab_list:
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query("SELECT username, role, display_name, allowed_institutions, is_active, created_at FROM dashboard_users ORDER BY id", conn)
    conn.close()

    def fmt_inst(s):
        if not s or not isinstance(s, str): return "全部医院"
        try: return ", ".join(json.loads(s))
        except: return str(s)

    df["可访问医院"] = df["allowed_institutions"].apply(fmt_inst)
    df["角色"] = df["role"].map({"admin": "👑 管理员", "viewer": "👁️ 只读", "hospital_admin": "🏥 医院管理员"})
    df["状态"] = df["is_active"].map({1: "✅ 启用", 0: "❌ 禁用"})

    display_df = df[["username", "角色", "display_name", "可访问医院", "状态", "created_at"]].rename(columns={
        "username": "用户名", "display_name": "显示名称", "created_at": "创建时间"
    })
    st.dataframe(display_df, use_container_width=True, hide_index=True)

# ── Tab 2: 新增用户 ──
with tab_add:
    col1, col2 = st.columns([1, 1])
    with col1:
        new_username = st.text_input("用户名 *", key="new_user")
        new_password = st.text_input("密码 *", type="password", key="new_pwd")
        new_display = st.text_input("显示名称", key="new_display", placeholder="如：青岛中心医院")
    with col2:
        new_role = st.selectbox("角色", ["viewer", "admin", "hospital_admin"], key="new_role",
                               help="viewer=只读查看，admin=管理员，hospital_admin=医院管理员")
        all_hospitals = get_all_hospital_names()
        selected_hospitals = st.multiselect("可访问医院（留空=全部）", all_hospitals, key="new_hospitals")
        all_tabs = ["总览分析", "趋势洞察", "异常监控", "医院排行", "月度环比", "便捷配药", "运营快报", "本周总结", "第三方服务分析", "用户行为分析"]
        hidden_tabs = st.multiselect("隐藏 Tab（留空=全部可见）", all_tabs, key="new_hidden")

    if st.button("创建用户", type="primary"):
        if new_username and new_password:
            ok, msg = add_user(new_username, new_password, new_role, new_display,
                              selected_hospitals if selected_hospitals else None,
                              hidden_tabs if hidden_tabs else None)
            if ok:
                st.session_state._msg = ("success", f"✅ 用户 **{new_username}** 已创建")
                st.rerun()
            else:
                st.error(msg)
        else:
            st.error("请填写用户名和密码")

# ── Tab 3: 编辑/删除 ──
with tab_edit:
    # 显示操作结果提示
    if st.session_state.get("_msg"):
        msg_type, msg_text = st.session_state._msg
        if msg_type == "success":
            st.success(msg_text)
        else:
            st.error(msg_text)
        st.session_state._msg = None

    conn = sqlite3.connect(DB_PATH)
    users = pd.read_sql_query("SELECT id, username, role, display_name, allowed_institutions, hidden_tabs, is_active FROM dashboard_users ORDER BY id", conn).to_dict("records")
    conn.close()

    user_options = {u["username"]: u for u in users}
    usernames = list(user_options.keys())

    edit_username = st.selectbox("选择要编辑的用户",
                                 options=usernames,
                                 key="edit_select")

    if edit_username and edit_username in user_options:
        user = user_options[edit_username]
        k = f"_e{user['id']}"  # 动态 key 前缀，切换用户时自动刷新表单

        st.info(f"正在编辑：**{user['username']}**（角色: {user['role']}）")
        col1, col2 = st.columns([1, 1])
        with col1:
            edit_display = st.text_input("显示名称", value=user.get("display_name") or "", key=f"edit_display{k}")
            edit_role = st.selectbox("角色", ["admin", "viewer", "hospital_admin"],
                                    index=["admin", "viewer", "hospital_admin"].index(user["role"]),
                                    key=f"edit_role{k}")
            edit_password = st.text_input("新密码（留空不改）", type="password", key=f"edit_pwd{k}")
            edit_active = st.checkbox("启用", value=bool(user.get("is_active", 1)), key=f"edit_active{k}")

        with col2:
            all_hospitals = get_all_hospital_names()
            current_inst = json.loads(user["allowed_institutions"]) if user.get("allowed_institutions") and isinstance(user["allowed_institutions"], str) else []
            edit_hospitals = st.multiselect("可访问医院", all_hospitals, default=current_inst, key=f"edit_hospitals{k}")
            all_tabs = ["总览分析", "趋势洞察", "异常监控", "医院排行", "月度环比", "便捷配药", "运营快报", "本周总结", "第三方服务分析", "用户行为分析"]
            current_tabs = json.loads(user["hidden_tabs"]) if user.get("hidden_tabs") and isinstance(user["hidden_tabs"], str) else []
            edit_hidden = st.multiselect("隐藏 Tab", all_tabs, default=current_tabs, key=f"edit_hidden{k}")

        col_btn1, col_btn2 = st.columns([1, 1])
        with col_btn1:
            if st.button("保存修改", type="primary", key=f"save_btn{k}"):
                update_user(user["id"],
                           password=edit_password if edit_password else None,
                           role=edit_role,
                           display_name=edit_display if edit_display else None,
                           institutions=edit_hospitals if edit_hospitals else None,
                           hidden_tabs=edit_hidden if edit_hidden else [],
                           is_active=1 if edit_active else 0)
                st.session_state._msg = ("success", f"✅ 用户 **{user['username']}** 已更新")
                st.rerun()

        with col_btn2:
            if user["username"] != "admin":
                if st.button("删除用户", type="secondary", key=f"del_btn{k}"):
                    ok, msg = delete_user(user["id"])
                    st.session_state._msg = ("success" if ok else "error", msg)
                    st.rerun()
