"""
Streamlit 简易登录守卫
用法: 在 app.py 顶部加一行: from auth_guard import guard; guard()
"""
import streamlit as st
import hashlib
import os

# ════════════════════════════════════════════
# 密码配置
# ════════════════════════════════════════════
# 修改这里或设置环境变量 DASHBOARD_PASSWORD
_DEFAULT_PASSWORD = "admin"

def _get_password():
    return os.environ.get("DASHBOARD_PASSWORD", _DEFAULT_PASSWORD)

def _hash_password(pwd: str) -> str:
    return hashlib.sha256(pwd.encode()).hexdigest()

# ════════════════════════════════════════════
# 密码哈希存储（不存明文）
# ════════════════════════════════════════════
def _init_session_state():
    if "password_hash" not in st.session_state:
        st.session_state.password_hash = _hash_password(_get_password())
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False

# ════════════════════════════════════════════
# 登录页面
# ════════════════════════════════════════════
def guard():
    _init_session_state()
    if st.session_state.authenticated:
        return

    st.markdown("""
    <style>
        .login-card {
            background: #ffffff;
            border-radius: 12px;
            padding: 40px 32px;
            box-shadow: 0 2px 12px rgba(0,0,0,0.08);
            max-width: 400px;
            margin: 80px auto;
            text-align: center;
        }
        .login-card h1 {
            color: #0EA5E9;
            font-size: 24px;
            margin-bottom: 8px;
        }
        .login-card p {
            color: #94A3B8;
            font-size: 14px;
            margin-bottom: 24px;
        }
        .login-error {
            background: #FEE2E2;
            color: #DC2626;
            padding: 8px 12px;
            border-radius: 6px;
            font-size: 13px;
            margin-top: 12px;
        }
        .login-footer {
            color: #CBD5E1;
            font-size: 12px;
            margin-top: 16px;
        }
    </style>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown('<div class="login-card">', unsafe_allow_html=True)
        st.markdown("### 🔐 数据看板")
        st.markdown("<p>请输入访问密码</p>", unsafe_allow_html=True)

        pwd = st.text_input(
            "密码",
            type="password",
            label_visibility="collapsed",
            key="login_pwd"
        )

        if st.button("登录", type="primary", use_container_width=True):
            if _hash_password(pwd) == st.session_state.password_hash:
                st.session_state.authenticated = True
                st.rerun()
            else:
                st.markdown('<div class="login-error">❌ 密码错误，请重试</div>', unsafe_allow_html=True)

        st.markdown('<div class="login-footer">OpenClaw Dashboard System</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    st.stop()
