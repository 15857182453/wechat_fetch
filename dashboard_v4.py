#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
优化版 - 运营数据仪表板 - Streamlit 应用（动态环比版）
环比逻辑：自动计算到最新数据日期
UI 优化：现代化设计 + 渐变主题 + 交互体验增强
"""

import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
from auth_guard import guard; guard()

# ========= 页面配置 =========
st.set_page_config(
    page_title="🏥 医院运营数据仪表板",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ========= 自定义 CSS 样式 - 白色主题 =========
custom_css = """
<style>
/* 页面背景 - 白色主题 */
.stApp {
    background: #ffffff;
    color: #333333;
}

/* KPI 卡片样式 */
[data-testid="stMetric"] {
    background: #f5f5f5;
    border-radius: 10px;
    padding: 20px;
    border: 1px solid #e0e0e0;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    height: 120px;
}
[data-testid="stMetric"] .stMetric-label {
    color: #666666 !important;
}
[data-testid="stMetric"] .stMetric-value {
    color: #333333 !important;
}
[data-testid="stMetric"] .stMetric-delta {
    color: #666666 !important;
}
[data-testid="stMetric"]:hover {
    transform: translateY(-2px);
    background: #e8e8e8;
    box-shadow: 0 4px 8px rgba(0,0,0,0.15);
}

/* Tab 样式 */
.stTabs [data-baseweb="tab-list"] {
    gap: 2px;
}
.stTabs [data-baseweb="tab"] {
    border: 1px solid #e0e0e0 !important;
    border-radius: 8px !important;
    margin-right: 2px !important;
    padding: 12px 24px !important;
    background: #f5f5f5 !important;
    transition: all 0.3s ease;
    color: #666666 !important;
}
.stTabs [data-baseweb="tab"]:hover {
    background: #e8e8e8 !important;
    transform: scale(1.02);
    color: #333333 !important;
}
.stTabs [aria-selected="true"] {
    background: #4361ee !important;
    color: white !important;
    border: 1px solid #4361ee !important;
}

/* 卡片容器 */
.card {
    background: #ffffff;
    border: 1px solid #e0e0e0;
    border-radius: 10px;
    padding: 20px;
    margin-bottom: 20px;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    color: #333333;
}

/* 加载动画 */
@keyframes fadeIn {
    from { opacity: 0; transform: translateY(20px); }
    to { opacity: 1; transform: translateY(0); }
}
.fade-in {
    animation: fadeIn 0.6s ease-out;
}

/* 顶部标题 */
.top-header {
    text-align: center;
    margin-bottom: 30px;
    color: #333333;
}
.top-header h1 {
    font-size: 2.5em;
    font-weight: bold;
    margin-bottom: 10px;
    color: #333333;
}
.top-header p {
    font-size: 1.2em;
    color: #666666;
}

/* 仪表板总览 */
.dashboard-overview {
    text-align: center;
    margin: 30px 0;
    color: #ffffff;
}

/* 图表标题 */
.chart-title {
    color: #ffffff !important;
    text-align: center !important;
    font-weight: bold !important;
    background: linear-gradient(135deg, #4cc9f0, #4361ee);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
}

/* 数据表格样式 */
.stDataFrame, .stTable {
    background: #ffffff !important;
    border: 1px solid #e0e0e0 !important;
    border-radius: 8px !important;
    color: #333333 !important;
}
.css-1q8gw5k { /* Expander header */
    background: #f5f5f5 !important;
    border: 1px solid #e0e0e0 !important;
    border-radius: 8px !important;
    color: #666666 !important;
}
.css-1q8gw5k:focus {
    outline: none;
    border: 1px solid #4361ee !important;
}
tr:nth-of-type(odd) {
    background-color: #fafafa !important;
}
tr:nth-of-type(even) {
    background-color: #f5f5f5 !important;
}

/* Sidebar 样式 */
.stSidebar .stSelectbox label, 
.stSidebar .stMultiSelect label,
.stSidebar .stDateInput label,
.stSidebar .stCheckbox label,
.stSidebar .stRadio label {
    color: #333333 !important;
}
.st-emotion-cache-1v0mbdj {
    border: 1px solid #e0e0e0 !important;
    border-radius: 8px !important;
}
.st-emotion-cache-qcptxx {
    color: #333333 !important;
}
</style>
"""

st.markdown(custom_css, unsafe_allow_html=True)

# ========= 顶部标题 =========
st.markdown('<div class="top-header"><h1>🏥 医院运营数据仪表板</h1><p>实时监控业务表现 · 智能异常预警</p></div>', unsafe_allow_html=True)

# ========= 数据库路径 =========
DB_PATH = "/home/openclaw/.openclaw/workspace/business_flow.db"

# ========= 数据加载函数 =========
@st.cache_data(ttl=30, show_spinner="🔄 正在加载医院数据...")
def load_hospital_data():
    """使用预聚合表查询处方服务数据（避免每次全表扫描 120 万行）"""
    conn = sqlite3.connect(DB_PATH)
    
    # 优先使用预聚合表（0.01s vs 0.85s）
    try:
        df = pd.read_sql_query(
            "SELECT institution, cnt, amt, avg_amt, dt "
            "FROM prescription_summary ORDER BY dt DESC, amt DESC",
            conn
        )
        if len(df) > 0:
            df.columns = ['医院', '订单数', '金额', '客单价', '日期']
            conn.close()
            return df
    except Exception:
        pass
    
    # 回退：从明细表全表扫描（仅预聚合表不存在时）
    table_names = ['daily_flow_2025', 'daily_flow_2026_jan', 'daily_flow_2026_feb', 'daily_flow_2026_mar', 'daily_flow_2026_apr', 'daily_flow_2026_may']
    queries = []
    for table in table_names:
        try:
            q = f"""
                SELECT institution, COUNT(*) as cnt, SUM(amount) as amt,
                       ROUND(SUM(amount)*1.0/COUNT(*), 2) as avg_amt,
                       SUBSTR(yewu_wancheng_shijian, 1, 10) as dt
                FROM {table}
                WHERE ye_wu_lei_mu LIKE '%处方服务%' AND pay_status = '收费'
                  AND yewu_wancheng_shijian IS NOT NULL AND yewu_wancheng_shijian != '' AND yewu_wancheng_shijian != 'NaT' AND amount IS NOT NULL
                GROUP BY institution, SUBSTR(yewu_wancheng_shijian, 1, 10)
            """
            queries.append(q)
        except Exception:
            pass
    
    if not queries:
        conn.close()
        return pd.DataFrame(columns=['医院', '订单数', '金额', '客单价', '日期'])
    
    full_query = " UNION ALL ".join(queries) + " ORDER BY dt DESC, amt DESC"
    df = pd.read_sql_query(full_query, conn)
    df.columns = ['医院', '订单数', '金额', '客单价', '日期']
    conn.close()
    return df

# ========= 环比计算函数 =========
def calculate_mom_growth():
    """计算月环比：动态计算到最新数据日期"""
    with st.spinner("🔄 正在计算月环比数据分析..."):
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # 获取 2026 年最新数据日期（排除今天及未来日期的空数据，只取到昨天）
        cursor.execute("""
            SELECT MAX(date) FROM duizhang_summary_2026 
            WHERE date < date('now') AND daily_total_flow > 0
        """)
        latest_date = cursor.fetchone()[0]
        
        if not latest_date:
            conn.close()
            return None, None, None
        
        # 解析最新日期
        latest_dt = datetime.strptime(latest_date, '%Y-%m-%d')
        current_month = latest_dt.month
        current_day = latest_dt.day
        
        # 计算本月 1 日到最新日期的数据
        current_start = f'2026-{current_month:02d}-01'
        current_end = latest_date
        
        cursor.execute("""
            SELECT COUNT(*), SUM(daily_total_flow), AVG(daily_total_flow)
            FROM duizhang_summary_2026
            WHERE date >= ? AND date <= ?
        """, (current_start, current_end))
        current_data = cursor.fetchone()
        
        # 计算上月同期
        if current_month == 1:
            prev_month = 12
            prev_year = 2025
            prev_table = 'duizhang_summary_2025'
        else:
            prev_month = current_month - 1
            prev_year = 2026
            prev_table = 'duizhang_summary_2026'
        
        prev_start = f'{prev_year}-{prev_month:02d}-01'
        prev_end = f'{prev_year}-{prev_month:02d}-{current_day:02d}'
        
        cursor.execute(f"""
            SELECT COUNT(*), SUM(daily_total_flow), AVG(daily_total_flow)
            FROM {prev_table}
            WHERE date >= ? AND date <= ?
        """, (prev_start, prev_end))
        prev_data = cursor.fetchone()
        
        conn.close()
        
        # 安全处理 None 值
        current_days = current_data[0] if current_data and current_data[0] else 0
        current_total = current_data[1] if current_data and current_data[1] else 0.0
        current_avg = current_data[2] if current_data and current_data[2] else 0.0
        
        prev_days = prev_data[0] if prev_data and prev_data[0] else 0
        prev_total = prev_data[1] if prev_data and prev_data[1] else 0.0
        prev_avg = prev_data[2] if prev_data and prev_data[2] else 0.0
        
        # 计算环比
        if prev_avg and prev_avg > 0:
            mom_growth = (current_avg - prev_avg) / prev_avg * 100
            mom_growth = round(mom_growth, 2)
        else:
            mom_growth = 0.0
        
        result = {
            'latest_date': latest_date,
            'current_period': f'{current_start} ~ {current_end}',
            'current_days': current_days,
            'current_total': round(current_total, 2),
            'current_avg': round(current_avg, 2),
            'prev_period': f'{prev_start} ~ {prev_end}',
            'prev_days': prev_days,
            'prev_total': round(prev_total, 2),
            'prev_avg': round(prev_avg, 2),
            'mom_growth': mom_growth
        }
        
        return result, current_data, prev_data

# ========= 缓存数据加载函数 =========

@st.cache_data(ttl=60)
def load_province_data():
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query("""
        SELECT province, COUNT(DISTINCT institution) as hospital_cnt
        FROM (
            SELECT DISTINCT institution, province FROM daily_flow_2025 WHERE province IS NOT NULL
            UNION SELECT DISTINCT institution, province FROM daily_flow_2026_jan WHERE province IS NOT NULL
            UNION SELECT DISTINCT institution, province FROM daily_flow_2026_feb WHERE province IS NOT NULL
            UNION SELECT DISTINCT institution, province FROM daily_flow_2026_mar WHERE province IS NOT NULL
            UNION SELECT DISTINCT institution, province FROM daily_flow_2026_apr WHERE province IS NOT NULL
        ) WHERE province IS NOT NULL
        GROUP BY province ORDER BY hospital_cnt DESC
    """, conn)
    conn.close()
    return df

@st.cache_data(ttl=60)
def load_yoy_data():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT MAX(date) FROM duizhang_summary_2026 WHERE date < date('now') AND daily_total_flow > 0")
    latest = cursor.fetchone()[0]
    if not latest:
        conn.close()
        return None, 0
    month = int(latest.split('-')[1])
    day = int(latest.split('-')[2])
    yoy_start = f'2025-{month:02d}-01'
    yoy_end = f'2025-{month:02d}-{day:02d}'
    cursor.execute("SELECT COUNT(*), SUM(daily_total_flow), AVG(daily_total_flow) FROM duizhang_summary_2025 WHERE date >= ? AND date <= ?", (yoy_start, yoy_end))
    yoy = cursor.fetchone()
    conn.close()
    return yoy, (yoy[2] if yoy and yoy[2] else 0.0)

@st.cache_data(ttl=60)
def load_monthly_detail(month_str, latest_date):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT date, daily_total_flow FROM duizhang_summary_2026 WHERE date >= ? AND date <= ? ORDER BY date", (month_str, latest_date))
    rows = cursor.fetchall()
    conn.close()
    return rows

@st.cache_data(ttl=60)
def load_daily_express():
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query("""
        SELECT date(yewu_wancheng_shijian) as date, institution, province, pay_status, amount, ye_wu_lei_mu
        FROM daily_flow_2026_jan
        WHERE yewu_wancheng_shijian IS NOT NULL AND yewu_wancheng_shijian != '' AND yewu_wancheng_shijian != 'NaT' AND amount IS NOT NULL
        UNION ALL
        SELECT date(yewu_wancheng_shijian) as date, institution, province, pay_status, amount, ye_wu_lei_mu
        FROM daily_flow_2026_feb
        WHERE yewu_wancheng_shijian IS NOT NULL AND yewu_wancheng_shijian != '' AND yewu_wancheng_shijian != 'NaT' AND amount IS NOT NULL
        UNION ALL
        SELECT date(yewu_wancheng_shijian) as date, institution, province, pay_status, amount, ye_wu_lei_mu
        FROM daily_flow_2026_mar
        WHERE yewu_wancheng_shijian IS NOT NULL AND yewu_wancheng_shijian != '' AND yewu_wancheng_shijian != 'NaT' AND amount IS NOT NULL
        UNION ALL
        SELECT date(yewu_wancheng_shijian) as date, institution, province, pay_status, amount, ye_wu_lei_mu
        FROM daily_flow_2026_apr
        WHERE yewu_wancheng_shijian IS NOT NULL AND yewu_wancheng_shijian != '' AND yewu_wancheng_shijian != 'NaT' AND amount IS NOT NULL
        UNION ALL
        SELECT date(yewu_wancheng_shijian) as date, institution, province, pay_status, amount, ye_wu_lei_mu
        FROM daily_flow_2026_may
        WHERE yewu_wancheng_shijian IS NOT NULL AND yewu_wancheng_shijian != '' AND yewu_wancheng_shijian != 'NaT' AND amount IS NOT NULL
    """, conn)
    conn.close()
    return df

@st.cache_data(ttl=60)
def load_week_summary(monday_str, today_str, last_monday_str, last_today_str):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT date, daily_total_flow FROM duizhang_summary_2026 WHERE date >= ? AND date <= ? AND daily_total_flow > 0 ORDER BY date", (monday_str, today_str))
    week = cursor.fetchall()
    cursor.execute("SELECT date, daily_total_flow FROM duizhang_summary_2026 WHERE date >= ? AND date <= ? AND daily_total_flow > 0 ORDER BY date", (last_monday_str, last_today_str))
    last_week = cursor.fetchall()
    conn.close()
    return week, last_week

@st.cache_data(ttl=60)
def load_week_hospital_top5(monday_str):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT institution, COUNT(*) as orders, SUM(amount) as flow FROM (
            SELECT institution, amount, yewu_wancheng_shijian, pay_status FROM daily_flow_2026_jan
            UNION ALL SELECT institution, amount, yewu_wancheng_shijian, pay_status FROM daily_flow_2026_feb
            UNION ALL SELECT institution, amount, yewu_wancheng_shijian, pay_status FROM daily_flow_2026_mar
            UNION ALL SELECT institution, amount, yewu_wancheng_shijian, pay_status FROM daily_flow_2026_apr
            UNION ALL SELECT institution, amount, yewu_wancheng_shijian, pay_status FROM daily_flow_2026_may
        ) WHERE date(yewu_wancheng_shijian) >= ? AND pay_status = '收费' GROUP BY institution ORDER BY flow DESC LIMIT 5
    """, (monday_str,))
    rows = cursor.fetchall()
    conn.close()
    return rows

@st.cache_data(ttl=60)
def load_week_category(monday_str):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT ye_wu_lei_mu, COUNT(*) as orders, SUM(amount) as flow FROM (
            SELECT ye_wu_lei_mu, amount, yewu_wancheng_shijian, pay_status FROM daily_flow_2026_jan
            UNION ALL SELECT ye_wu_lei_mu, amount, yewu_wancheng_shijian, pay_status FROM daily_flow_2026_feb
            UNION ALL SELECT ye_wu_lei_mu, amount, yewu_wancheng_shijian, pay_status FROM daily_flow_2026_mar
            UNION ALL SELECT ye_wu_lei_mu, amount, yewu_wancheng_shijian, pay_status FROM daily_flow_2026_apr
            UNION ALL SELECT ye_wu_lei_mu, amount, yewu_wancheng_shijian, pay_status FROM daily_flow_2026_may
        ) WHERE date(yewu_wancheng_shijian) >= ? AND ye_wu_lei_mu IS NOT NULL AND ye_wu_lei_mu != '' AND pay_status = '收费' GROUP BY ye_wu_lei_mu ORDER BY flow DESC
    """, (monday_str,))
    rows = cursor.fetchall()
    conn.close()
    return rows

@st.cache_data(ttl=60)
def load_week_province_top5(monday_str):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT province, COUNT(*) as orders, SUM(amount) as flow FROM (
            SELECT province, amount, yewu_wancheng_shijian, pay_status FROM daily_flow_2026_jan
            UNION ALL SELECT province, amount, yewu_wancheng_shijian, pay_status FROM daily_flow_2026_feb
            UNION ALL SELECT province, amount, yewu_wancheng_shijian, pay_status FROM daily_flow_2026_mar
            UNION ALL SELECT province, amount, yewu_wancheng_shijian, pay_status FROM daily_flow_2026_apr
            UNION ALL SELECT province, amount, yewu_wancheng_shijian, pay_status FROM daily_flow_2026_may
        ) WHERE date(yewu_wancheng_shijian) >= ? AND province IS NOT NULL AND province != '' AND pay_status = '收费' GROUP BY province ORDER BY flow DESC LIMIT 5
    """, (monday_str,))
    rows = cursor.fetchall()
    conn.close()
    return rows

@st.cache_data(ttl=60)
def load_week_rx(monday_str, last_monday_str, last_today_str):
    rx = "ye_wu_lei_mu LIKE '%处方%' AND pay_status='收费' AND yewu_wancheng_shijian IS NOT NULL AND yewu_wancheng_shijian != '' AND yewu_wancheng_shijian != 'NaT'"
    all_tbls = "SELECT institution, province, amount, ye_wu_lei_mu, yewu_wancheng_shijian, pay_status FROM daily_flow_2026_jan UNION ALL SELECT institution, province, amount, ye_wu_lei_mu, yewu_wancheng_shijian, pay_status FROM daily_flow_2026_feb UNION ALL SELECT institution, province, amount, ye_wu_lei_mu, yewu_wancheng_shijian, pay_status FROM daily_flow_2026_mar UNION ALL SELECT institution, province, amount, ye_wu_lei_mu, yewu_wancheng_shijian, pay_status FROM daily_flow_2026_apr UNION ALL SELECT institution, province, amount, ye_wu_lei_mu, yewu_wancheng_shijian, pay_status FROM daily_flow_2026_may"
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(f"SELECT COUNT(*), COALESCE(SUM(amount),0) FROM ({all_tbls}) WHERE substr(yewu_wancheng_shijian,1,10) >= ? AND {rx}", (monday_str,))
    rx_total = cursor.fetchone()
    cursor.execute(f"SELECT COUNT(*), COALESCE(SUM(amount),0) FROM ({all_tbls}) WHERE substr(yewu_wancheng_shijian,1,10) >= ? AND substr(yewu_wancheng_shijian,1,10) <= ? AND {rx}", (last_monday_str, last_today_str))
    rx_last = cursor.fetchone()
    cursor.execute(f"SELECT substr(yewu_wancheng_shijian,1,10) as d, COUNT(*) as orders, SUM(amount) as flow FROM ({all_tbls}) WHERE substr(yewu_wancheng_shijian,1,10) >= ? AND {rx} GROUP BY d ORDER BY d", (monday_str,))
    rx_week = cursor.fetchall()
    cursor.execute(f"SELECT substr(yewu_wancheng_shijian,1,10) as d, COUNT(*) as orders, SUM(amount) as flow FROM ({all_tbls}) WHERE substr(yewu_wancheng_shijian,1,10) >= ? AND substr(yewu_wancheng_shijian,1,10) <= ? AND {rx} GROUP BY d ORDER BY d", (last_monday_str, last_today_str))
    rx_last_week = cursor.fetchall()
    cursor.execute(f"SELECT institution, COUNT(*) as orders, SUM(amount) as flow, ROUND(SUM(amount)*1.0/COUNT(*), 1) as avg_price FROM ({all_tbls}) WHERE substr(yewu_wancheng_shijian,1,10) >= ? AND {rx} GROUP BY institution ORDER BY flow DESC LIMIT 10", (monday_str,))
    rx_hosp = cursor.fetchall()
    cursor.execute(f"SELECT province, COUNT(*) as orders, SUM(amount) as flow FROM ({all_tbls}) WHERE substr(yewu_wancheng_shijian,1,10) >= ? AND {rx} AND province IS NOT NULL AND province != '' GROUP BY province ORDER BY flow DESC LIMIT 10", (monday_str,))
    rx_prov = cursor.fetchall()
    cursor.execute(f"SELECT substr(yewu_wancheng_shijian,1,10) as d, institution, COUNT(*) as orders, SUM(amount) as flow FROM ({all_tbls}) WHERE substr(yewu_wancheng_shijian,1,10) >= ? AND {rx} AND (institution LIKE '%浙江省中医院%' OR institution LIKE '%杭州师范大学附属医院%' OR institution LIKE '%黑龙江中医药大学附属第一%') GROUP BY d, institution ORDER BY d", (monday_str,))
    rx_key = cursor.fetchall()
    conn.close()
    return {'total': rx_total, 'last': rx_last, 'week': rx_week, 'last_week': rx_last_week, 'hosp': rx_hosp, 'prov': rx_prov, 'key': rx_key}

@st.cache_data(ttl=60)
def load_tp_companies(table_name):
    wf = "third_party_name IS NOT NULL AND third_party_name != '' AND third_party_name NOT GLOB '[0-9]*'"
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(f"SELECT third_party_name, COUNT(*) as orders, ROUND(SUM(COALESCE(third_party_amount, 0)), 2) as total_amount, COUNT(DISTINCT institution) as hospital_cnt FROM {table_name} WHERE {wf} AND COALESCE(third_party_amount, 0) > 0 GROUP BY third_party_name ORDER BY total_amount DESC")
    rows = cursor.fetchall()
    conn.close()
    return rows

@st.cache_data(ttl=60)
def load_tp_hosp_detail(table_name, company_name):
    wf = "third_party_name IS NOT NULL AND third_party_name != '' AND third_party_name NOT GLOB '[0-9]*'"
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(f"SELECT institution, COUNT(*) as orders, ROUND(SUM(COALESCE(third_party_amount, 0)), 2) as tp_amount, ROUND(SUM(COALESCE(amount, 0)), 2) as total_amount, ROUND(AVG(COALESCE(third_party_amount, 0)), 2) as avg_tp, ROUND(AVG(COALESCE(amount, 0)), 2) as avg_total FROM {table_name} WHERE {wf} AND third_party_name = ? GROUP BY institution ORDER BY tp_amount DESC", (company_name,))
    rows = cursor.fetchall()
    conn.close()
    return rows

@st.cache_data(ttl=60)
def load_tp_matrix(table_name):
    wf = "third_party_name IS NOT NULL AND third_party_name != '' AND third_party_name NOT GLOB '[0-9]*'"
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(f"SELECT third_party_name, institution, COUNT(*) as orders, ROUND(SUM(COALESCE(third_party_amount, 0)), 2) as total_amount FROM {table_name} WHERE {wf} AND COALESCE(third_party_amount, 0) > 0 GROUP BY third_party_name, institution ORDER BY total_amount DESC")
    rows = cursor.fetchall()
    conn.close()
    return rows

@st.cache_data(ttl=60)
def load_tp_trend():
    tables = {'2026年1月': 'daily_flow_2026_jan', '2026年2月': 'daily_flow_2026_feb', '2026年3月': 'daily_flow_2026_mar', '2026年4月': 'daily_flow_2026_apr', '2026年5月': 'daily_flow_2026_may'}
    wf = "third_party_name IS NOT NULL AND third_party_name != '' AND third_party_name NOT GLOB '[0-9]*'"
    conn = sqlite3.connect(DB_PATH)
    all_data = []
    for mn, tbl in tables.items():
        cursor = conn.cursor()
        cursor.execute(f"SELECT third_party_name, '{mn}' as month, COUNT(*) as orders, ROUND(SUM(COALESCE(third_party_amount, 0)), 2) as total_amount FROM {tbl} WHERE {wf} AND COALESCE(third_party_amount, 0) > 0 GROUP BY third_party_name")
        for row in cursor.fetchall():
            all_data.append(row)
    conn.close()
    return all_data

@st.cache_data(ttl=300)
def load_tp_month_hosp(company_name=None):
    """跨月查询第三方公司→医院月度数据（用于月度环比）"""
    tables = {
        '2026年1月': 'daily_flow_2026_jan',
        '2026年2月': 'daily_flow_2026_feb',
        '2026年3月': 'daily_flow_2026_mar',
        '2026年4月': 'daily_flow_2026_apr',
        '2026年5月': 'daily_flow_2026_may',
    }
    wf = "third_party_name IS NOT NULL AND third_party_name != '' AND third_party_name NOT GLOB '[0-9]*'"
    conn = sqlite3.connect(DB_PATH)
    unions = []
    for mn, tbl in tables.items():
        unions.append(
            f"SELECT third_party_name, institution, '{mn}' as month, "
            f"COUNT(*) as orders, ROUND(SUM(COALESCE(third_party_amount, 0)), 2) as amount "
            f"FROM {tbl} WHERE {wf} AND COALESCE(third_party_amount, 0) > 0 "
            f"GROUP BY third_party_name, institution"
        )
    sql = " UNION ALL ".join(unions) + " ORDER BY third_party_name, institution, month"
    cursor = conn.cursor()
    cursor.execute(sql)
    rows = cursor.fetchall()
    conn.close()
    if company_name:
        rows = [r for r in rows if r[0] == company_name]
    return rows

# ========= 加载数据 =========
try:
    df_hospital = load_hospital_data()
    if df_hospital.empty:
        st.warning("⚠️ 数据库中暂时没有有效的医院运营数据")
        st.stop()
except Exception as e:
    st.error(f"❌ 医院数据加载失败：{e}")
    st.stop()

# ========= 侧边栏过滤器 =========
with st.sidebar:
    st.markdown('<div class="card"><h3>📊 筛选控制面板</h3></div>', unsafe_allow_html=True)
    
    # 医院选择
    with st.container():
        hospital_list = sorted(df_hospital['医院'].unique())
        selected_hospitals = st.multiselect(
            "🏥 选择医院",
            hospital_list,
            default=[],  # 默认不选  # 默认前5家
            help="可多选医院进行对比分析"
        )
    
    # 日期选择
    with st.container():
        max_date = pd.to_datetime(df_hospital['日期'].max()).date()
        min_date = pd.to_datetime(df_hospital['日期'].min()).date()
        
        date_mode = st.radio("📅 日期模式", ["单日查看", "范围查看"], index=0, horizontal=True)
        
        if date_mode == "单日查看":
            selected_date = st.date_input(
                "📅 选择分析日期",
                value=max_date,
                min_value=min_date,
                max_value=max_date,
                help="选择特定日期查看当天数据详情"
            )
            selected_date_str = selected_date.strftime('%Y-%m-%d')
            start_date_str = selected_date_str
            end_date_str = selected_date_str
            is_range_mode = False
        else:
            col_start, col_end = st.columns(2)
            with col_start:
                start_date = st.date_input("开始日期", value=max_date - pd.Timedelta(days=6), min_value=min_date, max_value=max_date)
            with col_end:
                end_date = st.date_input("结束日期", value=max_date, min_value=min_date, max_value=max_date)
            if start_date > end_date:
                st.warning("⚠️ 开始日期不能晚于结束日期，已自动交换")
                start_date, end_date = end_date, start_date
            start_date_str = start_date.strftime('%Y-%m-%d')
            end_date_str = end_date.strftime('%Y-%m-%d')
            selected_date_str = end_date_str
            selected_date = end_date
            is_range_mode = True
    
    # 添加其他筛选条件
    with st.container():
        st.divider()
        st.markdown("⚙️ 数据源设置")
        auto_calc = st.checkbox("📊 自动显示最新数据", True, help="启用后自动跟随最新数据日期")
    
    st.divider()
    
    # 状态信息
    st.info(f'''
    📈 数据概览
    - 🏥 医院总数: {len(df_hospital["医院"].unique())}
    - 🗓️ 日期范围: {df_hospital["日期"].min()} ~ {df_hospital["日期"].max()}
    - 📊 总记录数: {len(df_hospital):,}
    ''')

# ========== 主容器 ==========
st.markdown('<div class="dashboard-overview">', unsafe_allow_html=True)
col1, col2, col3, col4 = st.columns(4)
st.markdown('</div>', unsafe_allow_html=True)

# ========== 筛选数据 ==========
df_filtered = df_hospital
if selected_hospitals:
    df_filtered = df_hospital[df_hospital['医院'].isin(selected_hospitals)]
df_date = df_filtered[df_filtered['日期'] == selected_date_str]

# 范围过滤
if is_range_mode:
    df_range = df_filtered[(df_filtered['日期'] >= start_date_str) & (df_filtered['日期'] <= end_date_str)]
else:
    df_range = df_date

# ========== 标签页布局 (7 个功能页签) ==========
tab1, tab2, tab3, tab4, tab6, tab7, tab8, tab9, tab10, tab11 = st.tabs([
    "📊 **总览分析**", 
    "📈 **趋势洞察**", 
    "⚠️ **异常监控**", 
    "🏆 **医院排行**", 
    "📉 **月度环比**",
    "💊 **便捷配药**",
    "📋 **运营快报**",
    "📊 **本周总结**",
    "🔗 **第三方服务分析**",
    "📊 **用户行为分析**"
])

# ========== TAB 1: 总览分析 ==========
with tab1:
    if is_range_mode:
        tab1_title = f"📋 {start_date_str} ~ {end_date_str} - 运营概览"
    else:
        tab1_title = f"📋 {selected_date_str} - 实时运营概览"
    st.markdown(f'<div class="card fade-in"><h3>{tab1_title}</h3></div>', unsafe_allow_html=True)
    
    # KPI 指标行
    col1, col2, col3, col4 = st.columns(4)
    
    total_orders = int(df_range['订单数'].sum()) if not df_range.empty else 0
    total_amount = float(df_range['金额'].sum()) if not df_range.empty else 0
    avg_amount = float(df_range['客单价'].mean()) if not df_range.empty and len(df_range) > 0 else 0
    active_hospitals = df_range['医院'].nunique() if not df_range.empty else 0
    
    # 计算与前一天/前一个同等时段的对比
    if is_range_mode:
        range_days = (pd.to_datetime(end_date_str) - pd.to_datetime(start_date_str)).days + 1
        prev_end_dt = pd.to_datetime(start_date_str) - pd.Timedelta(days=1)
        prev_start_dt = prev_end_dt - pd.Timedelta(days=range_days - 1)
        prev_date_str = prev_start_dt.strftime('%Y-%m-%d')
        prev_end_date_str = prev_end_dt.strftime('%Y-%m-%d')
        df_prev = df_filtered[(df_filtered['日期'] >= prev_date_str) & (df_filtered['日期'] <= prev_end_date_str)]
    else:
        prev_dt = pd.to_datetime(selected_date_str) - pd.Timedelta(days=1)
        prev_date_str = prev_dt.strftime('%Y-%m-%d')
        df_prev = df_filtered[df_filtered['日期'] == prev_date_str]
    prev_orders = int(df_prev['订单数'].sum()) if not df_prev.empty else 0
    prev_amount = float(df_prev['金额'].sum()) if not df_prev.empty else 0
    prev_avg = float(df_prev['客单价'].mean()) if not df_prev.empty and len(df_prev) > 0 else 0
    prev_hospitals = len(df_prev) if not df_prev.empty else 0
    
    def fmt_delta(curr, prev, is_int=True):
        if prev == 0:
            return None
        diff = round(curr - prev, 2)
        pct = round((diff / prev * 100) if prev != 0 else 0, 1)
        if is_int:
            return f"{diff:+,} ({pct:+.1f}%)"
        return f"{diff:+,.2f} ({pct:+.1f}%)"
    
    orders_delta = fmt_delta(total_orders, prev_orders)
    amount_delta = fmt_delta(total_amount, prev_amount)
    avg_delta = fmt_delta(avg_amount, prev_avg, is_int=False)
    hosp_delta = f"{active_hospitals - prev_hospitals:+d}" if prev_hospitals > 0 else None
    
    with col1:
        st.markdown('<div class="fade-in">', unsafe_allow_html=True)
        st.metric(
            label="🎫 总订单数",
            value=f"{total_orders:,}",
            delta=orders_delta,
            delta_color="normal",
            help="当日所有医院的订单总数"
        )
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col2:
        st.markdown('<div class="fade-in">', unsafe_allow_html=True)
        st.metric(
            label="💰 总金额",
            value=f"¥{total_amount:,.0f}",
            delta=amount_delta,
            delta_color="normal",
            help="当日交易总金额"
        )
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col3:
        st.markdown('<div class="fade-in">', unsafe_allow_html=True)
        st.metric(
            label="🏷️ 平均客单价",
            value=f"¥{avg_amount:.2f}",
            delta=avg_delta,
            delta_color="normal",
            help="每笔订单的平均消费金额"
        )
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col4:
        st.markdown('<div class="fade-in">', unsafe_allow_html=True)
        st.metric(
            label="🏥 覆盖医院",
            value=f"{active_hospitals} 家",
            delta=hosp_delta,
            delta_color="normal",
            help="参与当日报表的医院数量"
        )
        st.markdown('</div>', unsafe_allow_html=True)
    
    # 医院详情表格
    if not df_range.empty:
        st.divider()
        if is_range_mode:
            st.markdown(f"### 🏥 {start_date_str} ~ {end_date_str} 医院汇总明细")
            df_rich = df_range.groupby('医院').agg({'订单数': 'sum', '金额': 'sum', '客单价': 'mean'}).reset_index().round(2)
        else:
            st.markdown("### 🏥 当日医院明细")
            df_rich = df_range[['医院', '订单数', '金额', '客单价']].round(2)
        df_rich['订单数'] = df_rich['订单数'].astype(int)
        
        # 创建表格样式
        def color_row(row):
            color = '#e8f2ff' if row.name % 2 == 0 else '#ffffff'  # 交替颜色
            return [f'background-color: {color}' for _ in row]
        
        st.dataframe(
            df_rich.style.apply(color_row, axis=1).format({
                '金额': '¥{:,}',
                '客单价': '¥{:.2f}'
            }),
            use_container_width=True,
            hide_index=True,
            height=400
        )
    else:
        st.markdown("⚠️ 无数据，请选择其他日期或检查筛选条件")

# ========== TAB 2: 趋势洞察 ==========
with tab2:
    st.markdown('<div class="card fade-in"><h3>📈 近7天运营趋势分析</h3></div>', unsafe_allow_html=True)
    
    if not df_filtered.empty:
        selected_dt = pd.to_datetime(selected_date_str)
        date_range = pd.date_range(end=selected_dt, periods=7, freq='D')
        date_strings = [d.strftime('%Y-%m-%d') for d in date_range]
        
        # 按日期聚合数据
        df_temp = df_filtered[df_filtered['日期'].isin(date_strings)]
        daily_trends = df_temp.groupby(['日期', '医院']).agg({
            '订单数': 'sum',
            '金额': 'sum',
            '客单价': 'mean'
        }).reset_index()
        
        # 按日期进一步聚合（不分医院，用于总量趋势）
        daily_totals = df_temp.groupby('日期').agg({
            '订单数': 'sum',
            '金额': 'sum',
            '客单价': 'mean'
        }).reset_index()
        
        if not daily_totals.empty:
            # 用量度图显示汇总趋势
            col1, col2 = st.columns(2)
            with col1:
                fig_orders = px.area(
                    daily_totals, 
                    x='日期', 
                    y='订单数',
                    title='📊 医院总体订单数趋势',
                    color_discrete_sequence=['#FF6B6B'],
                    line_shape='spline'
                )
                fig_orders.update_traces(fill='tonexty', fillcolor='rgba(255,107,107,0.2)')
                fig_orders.update_layout(
                    template='plotly_white',
                    height=350,
                    xaxis_title='日期',
                    yaxis_title='订单数',
                    hovermode='x unified'
                )
                st.plotly_chart(fig_orders, use_container_width=True)
            
            with col2:
                fig_revenue = px.area(
                    daily_totals, 
                    x='日期', 
                    y='金额',
                    title='💰 医院总体营收趋势',
                    color_discrete_sequence=['#4ECDC4'],
                    line_shape='spline'
                )
                fig_revenue.update_traces(fill='tonexty', fillcolor='rgba(78,205,196,0.2)')
                fig_revenue.update_layout(
                    template='plotly_white',
                    height=350,
                    xaxis_title='日期',
                    yaxis_title='金额 (元)',
                    hovermode='x unified'
                )
                st.plotly_chart(fig_revenue, use_container_width=True)
            
            st.divider()
            st.markdown("### 🏥 各医院详细趋势")
            
            if not daily_trends.empty:
                # 只显示 TOP 15 医院（避免线条过多重叠）
                top_hospitals = daily_trends.groupby('医院')['订单数'].sum().nlargest(15).index.tolist()
                daily_top = daily_trends[daily_trends['医院'].isin(top_hospitals)]
                
                # 分医院的趋势图
                fig_detail = px.line(
                    daily_top,
                    x='日期',
                    y='订单数',
                    color='医院',
                    title='各医院订单数趋势对比（TOP 15）',
                    markers=True,
                    line_shape='spline',
                    color_discrete_sequence=px.colors.qualitative.Set3
                )
                fig_detail.update_layout(
                    template='plotly_white',
                    height=500,
                    xaxis_title='日期',
                    yaxis_title='订单数',
                    hovermode='x unified'
                )
                st.plotly_chart(fig_detail, use_container_width=True)
                
                # 各医院营收趋势
                fig_revenue_compare = px.line(
                    daily_top,
                    x='日期',
                    y='金额',
                    color='医院',
                    title='各医院营业额趋势对比（TOP 15）',
                    markers=True,
                    line_shape='spline',
                    color_discrete_sequence=px.colors.qualitative.Set3
                )
                fig_revenue_compare.update_layout(
                    template='plotly_white',
                    height=400,
                    xaxis_title='日期',
                    yaxis_title='金额 (元)',
                    hovermode='x unified'
                )
                st.plotly_chart(fig_revenue_compare, use_container_width=True)
        else:
            st.info("🔍 暂无足够的趋势数据，可能是日期范围选择不当")
    else:
        st.warning("⚠️ 请选择至少一家医院查看趋势数据")

# ========== TAB 3: 异常监控 ==========
with tab3:
    st.markdown('<div class="card fade-in"><h3>⚠️ 异常数据实时监测</h3></div>', unsafe_allow_html=True)
    st.markdown(
        "- **Z-Score 统计异常**：基于 14 天历史数据，|Z| > 2.5 触发（双向检测暴增与暴跌）\n"
        "- **周同比异常**：对比上周同一天（消除周末效应），变化超 ±50% 触发\n"
        "- **日环比突变**：对比前一天，变化超 ±80% 且前一天 ≥20 单触发\n"
        "- **工作日/周末模式偏离**：按工作日/周末分别建基线，偏离同类基线 >2σ 或周末超工作日均值 120% 触发\n"
        "- **连续趋势检测**：连续 3 天递减且累计降幅 >40% 或连续 3 天递增且累计增幅 >80% 触发\n"
        "- **分级预警**：🔴 严重（≥3 项触发） / 🟠 警告（2 项触发） / 🟡 关注（1 项触发）\n"
        "- **最小样本**：日均 ≥30 单的医院才参与检测，过滤小医院噪声"
    )

    if not df_hospital.empty:
        all_hospitals = df_hospital['医院'].unique()
        anomalies_critical = []  # 🔴 严重：≥3 个检测器
        anomalies_warning = []   # 🟠 警告：2 个检测器
        anomalies_watch = []     # 🟡 关注：1 个检测器

        with st.spinner("🤖 正在执行异常检测分析..."):
            for idx, hospital in enumerate(all_hospitals):
                # 获取近 14 天数据
                hosp_data = df_hospital[df_hospital['医院'] == hospital].sort_values('日期', ascending=False).head(14)
                if len(hosp_data) < 3:
                    continue

                # 按日期聚合
                daily = hosp_data.groupby('日期').agg({'订单数': 'sum', '金额': 'sum'}).reset_index()
                daily = daily.sort_values('日期', ascending=True).reset_index(drop=True)
                if len(daily) < 3:
                    continue

                # 获取今日数据
                today = daily[daily['日期'] == selected_date_str]
                if today.empty:
                    continue

                today_orders = int(today.iloc[0]['订单数'])
                today_amount = float(today.iloc[0]['金额'])

                # 日均订单量门槛：≥30 单
                daily_avg = daily['订单数'].mean()
                if daily_avg < 30:
                    continue

                # 历史数据（排除今日）
                other_days = daily[daily['日期'] != selected_date_str]['订单数']
                if len(other_days) < 3:
                    continue

                mean_orders = other_days.mean()
                std_orders = other_days.std()

                # ---- 检测器 1：Z-Score 统计异常 ----
                zscore_flag = None
                zscore_val = None
                if std_orders and std_orders > 0:
                    zscore_val = (today_orders - mean_orders) / std_orders
                    if abs(zscore_val) > 2.5:
                        direction = "暴增" if zscore_val > 0 else "暴跌"
                        zscore_flag = f"Z-Score={zscore_val:+.2f}（{direction}）"

                # ---- 检测器 2：周同比异常 ----
                wow_flag = None
                wow_pct = None
                try:
                    today_date = pd.to_datetime(selected_date_str)
                    same_weekday_last_week = (today_date - pd.Timedelta(days=7)).strftime('%Y-%m-%d')
                    last_week_data = daily[daily['日期'] == same_weekday_last_week]
                    if not last_week_data.empty:
                        lw_orders = int(last_week_data.iloc[0]['订单数'])
                        if lw_orders > 0:
                            wow_pct = (today_orders - lw_orders) / lw_orders * 100
                            if abs(wow_pct) > 50:
                                direction = "暴增" if wow_pct > 0 else "暴跌"
                                wow_flag = f"周同比{wow_pct:+.0f}%（{direction}）"
                except Exception:
                    pass

                # ---- 检测器 3：日环比突变 ----
                dod_flag = None
                dod_pct = None
                prev_day_data = daily[daily['日期'] < selected_date_str].sort_values('日期', ascending=False)
                if not prev_day_data.empty:
                    prev_orders = int(prev_day_data.iloc[0]['订单数'])
                    if prev_orders >= 20:
                        dod_pct = (today_orders - prev_orders) / prev_orders * 100
                        if abs(dod_pct) > 80:
                            direction = "暴增" if dod_pct > 0 else "暴跌"
                            dod_flag = f"日环比{dod_pct:+.0f}%（{direction}）"

                # ---- 检测器 4：工作日/周末模式偏离检测 ----
                daytype_flag = None
                try:
                    today_ts = pd.Timestamp(selected_date_str)
                    is_weekend = today_ts.dayofweek >= 5  # 5=周六, 6=周日
                    # 将历史数据（排除今日）按工作日/周末分组
                    other_daily = daily[daily['日期'] != selected_date_str].copy()
                    other_daily['_dow'] = pd.to_datetime(other_daily['日期']).dt.dayofweek
                    weekday_data = other_daily[other_daily['_dow'] < 5]['订单数']
                    weekend_data = other_daily[other_daily['_dow'] >= 5]['订单数']

                    if is_weekend and len(weekend_data) >= 2:
                        wk_mean = weekend_data.mean()
                        wk_std = weekend_data.std()
                        if wk_std and wk_std > 0:
                            wk_z = (today_orders - wk_mean) / wk_std
                            if abs(wk_z) > 2:
                                direction = "偏高" if wk_z > 0 else "偏低"
                                daytype_flag = f"🟣 周末{direction}（Z={abs(wk_z):.1f}）"
                        # 额外规则：周末单量超过工作日均值的120%
                        if daytype_flag is None and len(weekday_data) >= 2:
                            wd_mean = weekday_data.mean()
                            if wd_mean > 0 and today_orders > wd_mean * 1.2:
                                daytype_flag = f"🟣 周末异常活跃（超工作日{today_orders / wd_mean * 100 - 100:.0f}%）"
                    elif not is_weekend and len(weekday_data) >= 2:
                        wd_mean = weekday_data.mean()
                        wd_std = weekday_data.std()
                        if wd_std and wd_std > 0:
                            wd_z = (today_orders - wd_mean) / wd_std
                            if abs(wd_z) > 2:
                                direction = "偏高" if wd_z > 0 else "偏低"
                                daytype_flag = f"🟣 工作日{direction}（Z={abs(wd_z):.1f}）"
                except Exception:
                    pass

                # ---- 检测器 5：连续趋势检测 ----
                trend_flag = None
                try:
                    # 取最近4天数据（含当天），按日期升序
                    recent_4 = daily.sort_values('日期', ascending=False).head(4)
                    recent_4 = recent_4.sort_values('日期', ascending=True).reset_index(drop=True)
                    if len(recent_4) >= 4:
                        vals = recent_4['订单数'].tolist()
                        # 检查连续3天递减（vals[0] > vals[1] > vals[2] > vals[3]）
                        is_decreasing = all(vals[i] > vals[i+1] for i in range(3))
                        is_increasing = all(vals[i] < vals[i+1] for i in range(3))
                        if is_decreasing and vals[0] > 0:
                            cum_change = (vals[3] - vals[0]) / vals[0] * 100
                            if cum_change < -40:
                                trend_flag = f"🟤 连续下滑3天（累计{cum_change:+.0f}%）"
                        elif is_increasing and vals[0] > 0:
                            cum_change = (vals[3] - vals[0]) / vals[0] * 100
                            if cum_change > 80:
                                trend_flag = f"🟤 连续暴增3天（累计{cum_change:+.0f}%）"
                except Exception:
                    pass

                # ---- 汇总触发数 ----
                flags = []
                if zscore_flag:
                    flags.append(('zscore', zscore_flag))
                if wow_flag:
                    flags.append(('wow', wow_flag))
                if dod_flag:
                    flags.append(('dod', dod_flag))
                if daytype_flag:
                    flags.append(('daytype', daytype_flag))
                if trend_flag:
                    flags.append(('trend', trend_flag))

                if not flags:
                    continue

                trigger_count = len(flags)
                anomaly_entry = {
                    '医院': hospital,
                    '日期': selected_date_str,
                    '订单数': today_orders,
                    '金额': today_amount,
                    '触发数_display': f"{trigger_count} / 5",
                    '触发数': trigger_count,
                    '检测明细': flags,
                    '均值': float(mean_orders),
                    '标准差': float(std_orders),
                    'zscore': zscore_val,
                    '周同比': wow_pct,
                    '日环比': dod_pct,
                }

                if trigger_count >= 3:
                    anomalies_critical.append(anomaly_entry)
                elif trigger_count == 2:
                    anomalies_warning.append(anomaly_entry)
                else:
                    anomalies_watch.append(anomaly_entry)

        total_anomalies = len(anomalies_critical) + len(anomalies_warning) + len(anomalies_watch)

        # 显示异常结果
        if total_anomalies > 0:
            st.error(
                f"🚨 发现 **{total_anomalies}** 家医院存在异常波动："
                f"🔴 严重 {len(anomalies_critical)} | "
                f"🟠 警告 {len(anomalies_warning)} | "
                f"🟡 关注 {len(anomalies_watch)}"
            )

            # ---- 🔴 严重（3 项触发）----
            if anomalies_critical:
                st.markdown("### 🔴 严重异常（≥3 项检测器触发）")
                for a in anomalies_critical:
                    expander_title = (
                        f"🏥 {a['医院']} | 📦 {a['订单数']:,} 单 | "
                        f"💰 ¥{a['金额']:,.0f} | 🔴 严重"
                    )
                    with st.expander(expander_title, expanded=True):
                        col1, col2 = st.columns(2)
                        with col1:
                            st.subheader("📊 异常概要")
                            st.write(f"**📅 日期**：{a['日期']}")
                            st.write(f"**📦 订单**：{a['订单数']:,} 单")
                            st.write(f"**💰 金额**：¥{a['金额']:,.0f}")
                            st.write(f"**📈 近 14 日均值**：{a['均值']:.1f} 单")
                            st.write(f"**📉 标准差**：{a['标准差']:.2f} 单")
                            st.write(f"**🎯 触发检测器**：{a['触发数_display']}")

                        with col2:
                            st.subheader("🔍 检测明细")
                            for kind, desc in a['检测明细']:
                                if kind == 'zscore':
                                    st.error(f"🔴 **统计异常**：{desc}")
                                elif kind == 'wow':
                                    st.warning(f"🟠 **周同比异常**：{desc}")
                                elif kind == 'dod':
                                    st.info(f"🔵 **日环比突变**：{desc}")
                                elif kind == 'daytype':
                                    st.warning(f"🟣 **工作日/周末模式**：{desc}")
                                elif kind == 'trend':
                                    st.info(f"🟤 **连续趋势**：{desc}")

                        # 14 天趋势图 + 周同比虚线
                        hosp_trend = df_hospital[df_hospital['医院'] == a['医院']].sort_values('日期', ascending=False).head(14)
                        if not hosp_trend.empty:
                            trend_daily = hosp_trend.groupby('日期').agg({'订单数': 'sum'}).reset_index().sort_values('日期')
                            fig = go.Figure()
                            fig.add_trace(go.Bar(
                                x=trend_daily['日期'],
                                y=trend_daily['订单数'],
                                name='订单数',
                                marker_color='rgba(255, 107, 107, 0.7)'
                            ))
                            # 周同比虚线（每个日期对应 7 天前的值）
                            wow_dates = []
                            wow_values = []
                            for _, row in trend_daily.iterrows():
                                try:
                                    d = pd.to_datetime(row['日期'])
                                    prev_week_str = (d - pd.Timedelta(days=7)).strftime('%Y-%m-%d')
                                    prev_week_row = trend_daily[trend_daily['日期'] == prev_week_str]
                                    if not prev_week_row.empty:
                                        wow_dates.append(row['日期'])
                                        wow_values.append(int(prev_week_row.iloc[0]['订单数']))
                                except Exception:
                                    pass
                            if wow_dates:
                                fig.add_trace(go.Scatter(
                                    x=wow_dates,
                                    y=wow_values,
                                    name='上周同期',
                                    mode='lines',
                                    line=dict(dash='dash', color='rgba(100, 100, 255, 0.6)', width=2)
                                ))
                            fig.add_hline(y=a['均值'], line_dash="dash", line_color="red", annotation_text="14日均值")
                            fig.update_layout(
                                title=f'{a["医院"]} - 近 14 天订单趋势与周同比',
                                xaxis_title='日期',
                                yaxis_title='订单数',
                                height=300
                            )
                            st.plotly_chart(fig, use_container_width=True)

            # ---- 🟠 警告（2 项触发）----
            if anomalies_warning:
                st.markdown("### 🟠 警告异常（2 项检测器触发）")
                for a in anomalies_warning:
                    expander_title = (
                        f"🏥 {a['医院']} | 📦 {a['订单数']:,} 单 | "
                        f"💰 ¥{a['金额']:,.0f} | 🟠 警告"
                    )
                    with st.expander(expander_title, expanded=False):
                        col1, col2 = st.columns(2)
                        with col1:
                            st.subheader("📊 异常概要")
                            st.write(f"**📅 日期**：{a['日期']}")
                            st.write(f"**📦 订单**：{a['订单数']:,} 单")
                            st.write(f"**💰 金额**：¥{a['金额']:,.0f}")
                            st.write(f"**📈 近 14 日均值**：{a['均值']:.1f} 单")
                            st.write(f"**📉 标准差**：{a['标准差']:.2f} 单")
                            st.write(f"**🎯 触发检测器**：{a['触发数_display']}")

                        with col2:
                            st.subheader("🔍 检测明细")
                            for kind, desc in a['检测明细']:
                                if kind == 'zscore':
                                    st.error(f"🔴 **统计异常**：{desc}")
                                elif kind == 'wow':
                                    st.warning(f"🟠 **周同比异常**：{desc}")
                                elif kind == 'dod':
                                    st.info(f"🔵 **日环比突变**：{desc}")
                                elif kind == 'daytype':
                                    st.warning(f"🟣 **工作日/周末模式**：{desc}")
                                elif kind == 'trend':
                                    st.info(f"🟤 **连续趋势**：{desc}")

                        # 14 天趋势图 + 周同比虚线
                        hosp_trend = df_hospital[df_hospital['医院'] == a['医院']].sort_values('日期', ascending=False).head(14)
                        if not hosp_trend.empty:
                            trend_daily = hosp_trend.groupby('日期').agg({'订单数': 'sum'}).reset_index().sort_values('日期')
                            fig = go.Figure()
                            fig.add_trace(go.Bar(
                                x=trend_daily['日期'],
                                y=trend_daily['订单数'],
                                name='订单数',
                                marker_color='rgba(255, 165, 0, 0.7)'
                            ))
                            wow_dates = []
                            wow_values = []
                            for _, row in trend_daily.iterrows():
                                try:
                                    d = pd.to_datetime(row['日期'])
                                    prev_week_str = (d - pd.Timedelta(days=7)).strftime('%Y-%m-%d')
                                    prev_week_row = trend_daily[trend_daily['日期'] == prev_week_str]
                                    if not prev_week_row.empty:
                                        wow_dates.append(row['日期'])
                                        wow_values.append(int(prev_week_row.iloc[0]['订单数']))
                                except Exception:
                                    pass
                            if wow_dates:
                                fig.add_trace(go.Scatter(
                                    x=wow_dates,
                                    y=wow_values,
                                    name='上周同期',
                                    mode='lines',
                                    line=dict(dash='dash', color='rgba(100, 100, 255, 0.6)', width=2)
                                ))
                            fig.add_hline(y=a['均值'], line_dash="dash", line_color="red", annotation_text="14日均值")
                            fig.update_layout(
                                title=f'{a["医院"]} - 近 14 天订单趋势与周同比',
                                xaxis_title='日期',
                                yaxis_title='订单数',
                                height=300
                            )
                            st.plotly_chart(fig, use_container_width=True)

            # ---- 🟡 关注（1 项触发）----
            if anomalies_watch:
                st.markdown(f"### 🟡 关注（1 项检测器触发，共 {len(anomalies_watch)} 家）")
                watch_names = [f"{a['医院']}（{a['检测明细'][0][1]}）" for a in anomalies_watch]
                st.info("、".join(watch_names))

        else:
            st.success(f"✅ 所有 {len(all_hospitals)} 家医院数据正常，未检测到异常波动！系统运行稳定")
    else:
        st.warning("⚠️ 暂无有效数据可供异常检测分析")

# ========== TAB 4: 医院排行 ==========
with tab4:
    if is_range_mode:
        tab4_title = f"🏆 医院业绩排行榜 ({start_date_str} ~ {end_date_str} 累计)"
    else:
        tab4_title = "🏆 医院业绩排行榜 (按当日营业额排名)"
    st.markdown(f'<div class="card fade-in"><h3>{tab4_title}</h3></div>', unsafe_allow_html=True)
    
    # 范围模式下按医院汇总
    if is_range_mode and not df_range.empty:
        df_tab4 = df_range.groupby('医院').agg({'订单数': 'sum', '金额': 'sum', '客单价': 'mean'}).reset_index()
    else:
        df_tab4 = df_date.copy() if not df_date.empty else pd.DataFrame()
    
    if not df_tab4.empty:
        tab4_sub1, tab4_sub2, tab4_sub3 = st.tabs(["💰 营业额Top10", "📦 订单量Top10", "🏷️ 客单价Top10"])
        
        with tab4_sub1:
            df_top_revenue = df_tab4.sort_values('金额', ascending=False).head(10)
            if not df_top_revenue.empty:
                fig_rev = px.bar(
                    df_top_revenue,
                    x='金额',
                    y='医院',
                    orientation='h',
                    title='营业额排行榜 (TOP 10)',
                    color='金额',
                    color_continuous_scale='viridis',
                    text='金额'
                )
                fig_rev.update_traces(texttemplate='¥%{text:,.0f}', textposition='auto')
                fig_rev.update_layout(height=500)
                st.plotly_chart(fig_rev, use_container_width=True)
            else:
                st.info("🔍 无营业额排名数据")
        
        with tab4_sub2:
            df_top_orders = df_tab4.sort_values('订单数', ascending=False).head(10)
            if not df_top_orders.empty:
                fig_ord = px.bar(
                    df_top_orders,
                    x='订单数',
                    y='医院',
                    orientation='h',
                    title='订单量排行榜 (TOP 10)',
                    color='订单数',
                    color_continuous_scale='Blues',
                    text='订单数'
                )
                fig_ord.update_traces(texttemplate='%{text:,}', textposition='auto')
                fig_ord.update_layout(height=500)
                st.plotly_chart(fig_ord, use_container_width=True)
            else:
                st.info("🔍 无订单量排名数据")
        
        with tab4_sub3:
            df_top_price = df_tab4.sort_values('客单价', ascending=False).head(10)
            if not df_top_price.empty:
                fig_avg = px.bar(
                    df_top_price,
                    x='客单价',
                    y='医院',
                    orientation='h',
                    title='客单价排行榜 (TOP 10)',
                    color='客单价',
                    color_continuous_scale='Oranges',
                    text='客单价'
                )
                fig_avg.update_traces(texttemplate='¥%{text:.2f}', textposition='auto')
                fig_avg.update_layout(height=500)
                st.plotly_chart(fig_avg, use_container_width=True)
            else:
                st.info("🔍 无客单价排名数据")
    else:
        st.warning("⚠️ 请先选择有效的日期和医院查看排行数据")

# ========== TAB 6: 月环比分析 ==========
with tab6:
    st.markdown('<div class="card fade-in"><h3>📉 月环比智能分析 - 动态计算模式</h3></div>', unsafe_allow_html=True)
    st.info("💡 **智能环比说明**: 自动匹配最新数据截止日期（如 4月6日 -> 计算 4月1-6日 vs 3月1-6日的对比），并包含同比分析")
    
    try:
        result, current_data, prev_data = calculate_mom_growth()
        
        if result:
            # 今日数据日期
            st.markdown(f"📅 **最新数据日期**：{result['latest_date']}")
            
            # 查询去年同月同期做同比 (年度对比)
            with st.spinner("🔄 正在计算同比数据..."):
                conn = sqlite3.connect(DB_PATH)
                latest_dt = datetime.strptime(result['latest_date'], '%Y-%m-%d')
                current_day = latest_dt.day
                current_month = latest_dt.month
                prev_year = 2025
                
                cursor = conn.cursor()
                yoy_period = f'{prev_year}-{current_month:02d}-01 ~ {prev_year}-{current_month:02d}-{current_day:02d}'
                cursor.execute("""
                    SELECT COUNT(*), SUM(daily_total_flow), AVG(daily_total_flow)
                    FROM duizhang_summary_2025
                    WHERE date >= ? AND date <= ?
                """, (f'{prev_year}-{current_month:02d}-01', f'{prev_year}-{current_month:02d}-{current_day:02d}'))
                yoy_data = cursor.fetchone()
                conn.close()
                
                yoy_avg = yoy_data[2] if yoy_data and yoy_data[2] else 0.0
                if yoy_avg and yoy_avg > 0:
                    yoy_growth = round((result['current_avg'] - yoy_avg) / yoy_avg * 100, 2)
                else:
                    yoy_growth = 0.0
            
            # 修改后的布局：第一行放本月和上月同期对比，第二行放环比和同比分析
            st.subheader("📊 月环比对比")
            
            # 第一行：本月数据 vs 上月同期
            col1, col2 = st.columns(2)
            
            with col1:
                st.info(f"**📅 本月数据 ({result['current_period']})**\n\n" +
                        f"⏳ 天数：{result['current_days']} 天  \n" +
                        f"📈 总流量：¥{result['current_total']:,.2f} 万元  \n" +
                        f"🎯 日均流量：¥{result['current_avg']:,.2f} 万元")
            
            with col2:
                st.info(f"**◀️ 上月同期 ({result['prev_period']})**\n\n" +
                        f"⏳ 天数：{result['prev_days']} 天  \n" +
                        f"📈 总流量：¥{result['prev_total']:,.2f} 万元  \n" +
                        f"🎯 日均流量：¥{result['prev_avg']:,.2f} 万元")
            
            st.divider()
            
            # 第二行：环比结果分析 + 年度同比分析
            col3, col4 = st.columns(2)
            
            with col3:
                st.subheader("📈 环比结果分析")
                mom_growth = result['mom_growth']
                arrow = "📈" if mom_growth > 0 else "📉" if mom_growth < 0 else "➡️"
                
                if mom_growth > 0:
                    st.success(f"**✅ 月环比增长**：{mom_growth:+.2f}% {arrow}", icon="📈")
                    st.progress(min(abs(mom_growth)/100, 1.0))
                    st.write(f"增长幅度：{abs(mom_growth):.2f}%")
                elif mom_growth < 0:
                    st.error(f"**⚠️ 月环比下降**：{mom_growth:+.2f}% {arrow}", icon="📉")
                    st.progress(min(abs(mom_growth)/200, 1.0))
                    st.write(f"下降幅度：{abs(mom_growth):.2f}%")
                else:
                    st.info(f"**🔄 环比持平**：{mom_growth:+.2f}% {arrow}", icon="➡️")
            
            with col4:
                st.subheader("📊 年度同比分析")
                st.markdown(f"📅 对比期间：**{result['current_period']}** vs **{yoy_period}**（去年同月）")
                if yoy_growth > 0:
                    st.success(f"**✅ 年同比例增长**：{yoy_growth:+.2f}% 📈", icon="🌍")
                elif yoy_growth < 0:
                    st.error(f"**⚠️ 年同比较低**：{yoy_growth:+.2f}% 📉", icon="🌍")
                else:
                    st.info(f"**🔄 年同比持平**：{yoy_growth:+.2f}% ➡️", icon="🌍")
                
                st.divider()
                
                # 今年 vs 去年同期对比
                st.markdown("#### 📈 年度增长趋势")

                # 显示增长指标
                col_g1, col_g2 = st.columns(2)
                with col_g1:
                    st.metric("📊 本月月环比", f"{mom_growth:+.2f}%")
                with col_g2:
                    st.metric("🌍 本月年同比", f"{yoy_growth:+.2f}%")
            
            # 展示本期间内每日详细数据
            with st.expander("📊 查看本月每日数据明细", expanded=True):
                conn = sqlite3.connect(DB_PATH)
                cursor = conn.cursor()
                current_month = datetime.strptime(result['latest_date'], '%Y-%m-%d').month
                cursor.execute(f"""
                    SELECT date, daily_total_flow FROM duizhang_summary_2026
                    WHERE date >= '2026-{current_month:02d}-01' AND date <= ?
                    ORDER BY date
                """, (result['latest_date'],))
                daily_data = cursor.fetchall()
                conn.close()
                
                if daily_data:
                    df_daily = pd.DataFrame(daily_data, columns=['日期', '流水 (万元)'])
                    df_daily['流水 (万元)'] = df_daily['流水 (万元)'].round(2)
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        # 数据表格
                        st.dataframe(df_daily, use_container_width=True, hide_index=True)
                
                    with col2:
                        # 每日趋势图
                        fig_daily = px.bar(
                            df_daily,
                            x='日期',
                            y='流水 (万元)',
                            title='📊 本月每日流水趋势',
                            color_discrete_sequence=['#667eea']
                        )
                        fig_daily.update_layout(height=400)
                        st.plotly_chart(fig_daily, use_container_width=True)
                        
                        # 本月关键指标
                        max_daily = df_daily['流水 (万元)'].max()
                        max_daily_date = df_daily.loc[df_daily['流水 (万元)'].idxmax(), '日期']
                        avg_daily = df_daily['流水 (万元)'].mean()
                        st.metric("📅 最高单日流水", f"¥{max_daily:.2f} 万元", f"发生于 {max_daily_date}")
                        st.metric("🎯 本月日均流水", f"¥{avg_daily:.2f} 万元", f"共 {len(df_daily)} 个工作日")
                else:
                    st.info("🔍 暂无本月详细数据")
        
        else:
            st.warning("❌ 暂无环比数据，请确认是否已导入 duizhang_summary_2025 和 2026 对账表数据")
    
    except Exception as e:
        st.error(f"❌ 环比数据分析加载失败：{e}")
        st.info("🔍 系统提示：可能未找到 duizhang_summary_2025 和 duizhang_summary_2026 表，或该数据表格式不正确")
# ========== TAB 7: 便捷配药数据统计 ==========
with tab7:
    st.markdown('<div style="text-align:center;font-size:22px;font-weight:bold;padding:10px 0;background:#2196F3;color:white;">💊 便捷配药数据统计</div>', unsafe_allow_html=True)
    st.markdown('')

    EXCEL_CP_PATH = '/mnt/e/办公资料/业务对账数据/对账业务总表/新流水2026.xlsx'

    @st.cache_data(ttl=300)
    def load_convenient_pharmacy():
        df = pd.read_excel(EXCEL_CP_PATH, header=None, skiprows=4)
        data = []
        for _, row in df.iterrows():
            date_val = row.iloc[0]
            flow_val = row.iloc[3]
            order_val = row.iloc[4]
            if pd.notna(date_val) and pd.notna(flow_val):
                try:
                    dt = pd.to_datetime(date_val)
                    if dt.year != 2026: continue
                    data.append({'日期': dt.strftime('%Y-%m-%d'), '流水': float(flow_val), '订单': int(order_val) if pd.notna(order_val) else 0})
                except: pass
        df = pd.DataFrame(data)
        if not df.empty: df['日期'] = pd.to_datetime(df['日期'])
        return df

    @st.cache_data(ttl=300)
    def load_new_hospitals():
        conn = sqlite3.connect(DB_PATH)
        hospitals = {'齐鲁德医': '齐鲁德医', '齐鲁二院': '齐鲁第二医院', '安徽省立': '安徽省立医院', '青岛中心': '青岛中心'}
        tables_2026 = ['daily_flow_2026_jan', 'daily_flow_2026_feb', 'daily_flow_2026_mar', 'daily_flow_2026_apr', 'daily_flow_2026_may']
        all_data = {}
        for name, pattern in hospitals.items():
            parts = []
            for t in tables_2026:
                parts.append(f"SELECT SUBSTR(COALESCE(NULLIF(TRIM(yewu_wancheng_shijian),''), NULLIF(TRIM(\"业务完成时间\"),'')),1,10) as date, 1 as cnt, COALESCE(amount, CAST(\"订单金额\" AS REAL)) as amt FROM {t} WHERE (institution LIKE '%{pattern}%' OR \"机构名称\" LIKE '%{pattern}%') AND (ye_wu_lei_mu LIKE '%处方服务%' OR \"业绩类目\" LIKE '%处方%') AND (pay_status='收费' OR \"收退标识\"='收费') AND (yewu_wancheng_shijian IS NOT NULL AND yewu_wancheng_shijian != '' AND yewu_wancheng_shijian != 'NaT' OR \"业务完成时间\" IS NOT NULL AND \"业务完成时间\" != '' AND \"业务完成时间\" != 'NaT')")
            inner = ' UNION ALL '.join(parts)
            full_query = f'SELECT date, SUM(cnt) as orders, SUM(amt) as flow FROM ({inner}) GROUP BY date ORDER BY date'
            df_h = pd.read_sql_query(full_query, conn)
            if not df_h.empty:
                df_h['date'] = pd.to_datetime(df_h['date'])
                all_data[name] = df_h
        conn.close()
        return all_data

    try:
        df_cp = load_convenient_pharmacy()
        hosp_data = load_new_hospitals()

        if df_cp.empty:
            st.warning("⚠️ 暂无数据")
        else:
            col_left, col_right = st.columns([1, 1])

            # ==================== 左栏 ====================
            with col_left:
                total_flow_all = df_cp['流水'].sum()
                total_orders_all = df_cp['订单'].sum()
                df_recent = df_cp.tail(15).copy()
                tf_r = df_recent['流水'].sum()
                to_r = df_recent['订单'].sum()

                st.markdown(f'''<div style="text-align:center;font-size:15px;font-weight:bold;margin-bottom:6px;">2026年便捷购药统计（总）</div>
<table style="width:100%;border-collapse:collapse;font-size:13px;margin-bottom:8px;">
<tr><td style="padding:5px 10px;border:1px solid #ccc;font-weight:bold;text-align:right;background:#f5f5f5;width:32%;">总流水（元）：</td>
<td style="padding:5px 10px;border:1px solid #ccc;font-weight:bold;text-align:center;width:18%;">{total_flow_all:,.0f}</td>
<td style="padding:5px 10px;border:1px solid #ccc;font-weight:bold;text-align:right;background:#f5f5f5;width:32%;">总订单（单）：</td>
<td style="padding:5px 10px;border:1px solid #ccc;font-weight:bold;text-align:center;width:18%;">{total_orders_all:,}</td></tr></table>''', unsafe_allow_html=True)

                fig_cp = go.Figure()
                fig_cp.add_trace(go.Scatter(x=df_recent['日期'], y=df_recent['流水'], name='金额', mode='lines+markers', line=dict(color='#4285F4', width=2.5), marker=dict(size=4)))
                fig_cp.add_trace(go.Scatter(x=df_recent['日期'], y=df_recent['订单'], name='订单', mode='lines+markers', line=dict(color='#FF9800', width=2.5), marker=dict(size=4), yaxis='y2'))
                df_recent['日期显示'] = df_recent['日期'].dt.strftime('%-m月%-d日')
                fig_cp.update_layout(template='plotly_white', height=320,
                    xaxis=dict(title=None, tickvals=df_recent['日期'], ticktext=df_recent['日期显示'], tickangle=45, tickfont=dict(size=8)),
                    yaxis=dict(title=None, tickprefix='¥', tickformat=',.0f', side='left'),
                    yaxis2=dict(title=None, side='right', overlaying='y', showgrid=False, tickformat=',.0f'),
                    hovermode='x unified', legend=dict(orientation='h', yanchor='bottom', y=1.12, xanchor='left', x=0, font=dict(size=9)), margin=dict(l=50, r=50, t=5, b=55))
                st.plotly_chart(fig_cp, use_container_width=True)

                # 底部表格
                dr = df_recent['日期'].dt.strftime('%m月%d日').tolist()
                fl = [f"{v:,.0f}" for v in df_recent['流水'].tolist()]
                ol = [f"{int(v):,}" for v in df_recent['订单'].tolist()]
                dr.append('总计'); fl.append(f"{tf_r:,.0f}"); ol.append(f"{to_r:,}")
                hc = '<th style="padding:2px 3px;border:1px solid #ccc;background:#f0f0f0;font-weight:bold;text-align:center;font-size:8px;white-space:nowrap;">日期</th>'
                for d in dr[:-1]: hc += f'<th style="padding:2px 3px;border:1px solid #ccc;background:#f0f0f0;text-align:center;font-size:8px;white-space:nowrap;">{d}</th>'
                hc += '<th style="padding:2px 3px;border:1px solid #ccc;background:#d4edda;font-weight:bold;text-align:center;font-size:8px;white-space:nowrap;">总计</th>'
                ac = '<td style="padding:2px 3px;border:1px solid #ccc;background:#e8f0fe;font-weight:bold;text-align:center;font-size:8px;white-space:nowrap;">金额</td>'
                for v in fl[:-1]: ac += f'<td style="padding:2px 3px;border:1px solid #ccc;text-align:right;font-size:8px;white-space:nowrap;">{v}</td>'
                ac += f'<td style="padding:2px 3px;border:1px solid #ccc;background:#d4edda;font-weight:bold;text-align:right;font-size:8px;white-space:nowrap;">{fl[-1]}</td>'
                oc = '<td style="padding:2px 3px;border:1px solid #ccc;background:#fff3e0;font-weight:bold;text-align:center;font-size:8px;white-space:nowrap;">订单</td>'
                for v in ol[:-1]: oc += f'<td style="padding:2px 3px;border:1px solid #ccc;text-align:right;font-size:8px;white-space:nowrap;">{v}</td>'
                oc += f'<td style="padding:2px 3px;border:1px solid #ccc;background:#d4edda;font-weight:bold;text-align:right;font-size:8px;white-space:nowrap;">{ol[-1]}</td>'
                n_cols = len(dr)
                colgroup = f'<col style="width:80px;">' + f'<col>' * n_cols
                st.markdown(f'<div style="width:100%;"><table style="border-collapse:collapse;font-family:monospace;width:100%;table-layout:fixed;"><colgroup>{colgroup}</colgroup><thead><tr>{hc}</tr></thead><tbody><tr>{ac}</tr><tr>{oc}</tr></tbody></table></div>', unsafe_allow_html=True)

            # ==================== 右栏 ====================
            with col_right:
                if hosp_data:
                    all_dates = set()
                    for df_h in hosp_data.values(): all_dates.update(df_h['date'].tolist())
                    all_dates_sorted = sorted(all_dates)
                    recent_dates = all_dates_sorted[-15:] if len(all_dates_sorted) > 15 else all_dates_sorted

                    df_hr = pd.DataFrame({'date': recent_dates})
                    hosp_names = list(hosp_data.keys())
                    for name in hosp_names:
                        df_hf = hosp_data[name][hosp_data[name]['date'].isin(recent_dates)][['date', 'orders', 'flow']].copy()
                        df_hf = df_hf.rename(columns={'orders': f'{name}_订单', 'flow': f'{name}_流水'})
                        df_hr = df_hr.merge(df_hf, on='date', how='left')
                        df_hr[f'{name}_订单'] = df_hr[f'{name}_订单'].fillna(0).astype(int)
                        df_hr[f'{name}_流水'] = df_hr[f'{name}_流水'].fillna(0)
                    df_hr = df_hr.sort_values('date').reset_index(drop=True)
                    df_hr['总流水'] = sum(df_hr[f'{name}_流水'] for name in hosp_names)
                    df_hr['总订单'] = sum(df_hr[f'{name}_订单'] for name in hosp_names)

                    total_fh = sum(df_h['flow'].sum() for df_h in hosp_data.values())
                    total_oh = sum(df_h['orders'].sum() for df_h in hosp_data.values())

                    st.markdown(f'''<div style="text-align:center;font-size:15px;font-weight:bold;margin-bottom:6px;">新增医院便捷配药统计</div>
<table style="width:100%;border-collapse:collapse;font-size:13px;margin-bottom:8px;">
<tr><td style="padding:5px 10px;border:1px solid #ccc;font-weight:bold;text-align:right;background:#f5f5f5;width:28%;">总流水：</td>
<td style="padding:5px 10px;border:1px solid #ccc;font-weight:bold;text-align:center;width:22%;">{total_fh:,.0f}</td>
<td style="padding:5px 10px;border:1px solid #ccc;font-weight:bold;text-align:right;background:#f5f5f5;width:28%;">总订单：</td>
<td style="padding:5px 10px;border:1px solid #ccc;font-weight:bold;text-align:center;width:22%;">{total_oh:,}</td></tr></table>''', unsafe_allow_html=True)

                    colors_order = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf']
                    fig_hr = go.Figure()
                    idx = 0
                    for name in hosp_names:
                        fig_hr.add_trace(go.Scatter(x=df_hr['date'], y=df_hr[f'{name}_流水'], name=f'{name}流水', mode='lines+markers', line=dict(color=colors_order[idx%len(colors_order)], width=2), marker=dict(size=4)))
                        idx += 1
                        fig_hr.add_trace(go.Scatter(x=df_hr['date'], y=df_hr[f'{name}_订单'], name=f'{name}订单', mode='lines+markers', line=dict(color=colors_order[idx%len(colors_order)], width=2, dash='dot'), marker=dict(size=4), yaxis='y2'))
                        idx += 1
                    fig_hr.add_trace(go.Scatter(x=df_hr['date'], y=df_hr['总流水'], name='总流水', mode='lines+markers', line=dict(color='#000', width=3), marker=dict(size=5, symbol='diamond')))
                    fig_hr.add_trace(go.Scatter(x=df_hr['date'], y=df_hr['总订单'], name='总订单', mode='lines+markers', line=dict(color='#F00', width=3), marker=dict(size=5, symbol='diamond'), yaxis='y2'))
                    df_hr['日期显示'] = df_hr['date'].dt.strftime('%-m月%-d日')
                    fig_hr.update_layout(template='plotly_white', height=320,
                        xaxis=dict(title=None, tickvals=df_hr['date'], ticktext=df_hr['日期显示'], tickangle=45, tickfont=dict(size=8)),
                        yaxis=dict(title=None, tickprefix='¥', tickformat=',.0f', side='left'),
                        yaxis2=dict(title=None, side='right', overlaying='y', showgrid=False, tickformat=',.0f'),
                        hovermode='x unified', legend=dict(orientation='h', yanchor='bottom', y=1.12, xanchor='left', x=0, font=dict(size=7)), margin=dict(l=50, r=50, t=5, b=55))
                    st.plotly_chart(fig_hr, use_container_width=True)

                    # 底部表格
                    dr2 = df_hr['date'].dt.strftime('%m月%d日').tolist()
                    rows = []
                    for name in hosp_names:
                        rows.append(('流水', name, [f"{v:,.0f}" for v in df_hr[f'{name}_流水'].tolist()], '#e8f0fe'))
                        rows.append(('订单', name, [f"{int(v):,}" for v in df_hr[f'{name}_订单'].tolist()], '#fff3e0'))
                    rows.append(('流水', '总计', [f"{v:,.0f}" for v in df_hr['总流水'].tolist()], '#d4edda'))
                    rows.append(('订单', '总计', [f"{int(v):,}" for v in df_hr['总订单'].tolist()], '#d4edda'))
                    # 表头
                    hc2 = '<th style="padding:2px 3px;border:1px solid #ccc;background:#f0f0f0;font-weight:bold;text-align:center;font-size:8px;white-space:nowrap;">日期</th>'
                    for d in dr2: hc2 += f'<th style="padding:2px 3px;border:1px solid #ccc;background:#f0f0f0;text-align:center;font-size:8px;white-space:nowrap;">{d}</th>'
                    thead = f'<thead><tr>{hc2}</tr></thead>'
                    # 表体
                    tbody = '<tbody>'
                    for rt, rn, vals, bg in rows:
                        tr = f'<td style="padding:2px 3px;border:1px solid #ccc;background:{bg};font-weight:bold;text-align:center;font-size:8px;white-space:nowrap;">{rn}{rt}</td>'
                        for v in vals: tr += f'<td style="padding:2px 3px;border:1px solid #ccc;text-align:right;font-size:8px;white-space:nowrap;">{v}</td>'
                        tbody += f'<tr>{tr}</tr>'
                    tbody += '</tbody>'
                    n_cols2 = len(dr2) + 1
                    colgroup2 = f'<col style="width:80px;">' + f'<col>' * n_cols2
                    st.markdown(f'<div style="width:100%;"><table style="border-collapse:collapse;font-family:monospace;width:100%;table-layout:fixed;"><colgroup>{colgroup2}</colgroup>{thead}{tbody}</table></div>', unsafe_allow_html=True)
                else:
                    st.info("🔍 暂无新增医院数据")

    except Exception as e:
        st.error(f"❌ 便捷配药数据加载失败：{e}")

# ========== 便捷配药 - 机构趋势图 ==========
    st.markdown('---')
    st.markdown('<div style="text-align:center;font-size:18px;font-weight:bold;padding:8px 0;background:#2196F3;color:white;">常规机构便捷配药数据趋势图</div>', unsafe_allow_html=True)
    st.markdown('')
    
    try:
        # 重新连接数据库
        conn2 = sqlite3.connect(DB_PATH)
        cursor2 = conn2.cursor()
        
        # 医院配置
        HOSPITALS = [
            {'title': '浙江省中医院便捷配药订单统计', 'name': '浙江省中医院（湖滨院区）', 'type': 'single'},
            {'title': '杭州师范大学附属医院便捷配药统计', 'name': '杭州师范大学附属医院', 'type': 'dual'},
            {'title': '青岛市中医院便捷配药统计', 'name': '青岛市中医医院（市海慈医院）', 'type': 'dual'},
            {'title': '宁夏医科大学总医院便捷配药订单统计', 'name': '宁夏医科大学总医院', 'type': 'single'}
        ]
        
        # 获取数据（查询 2026 年所有月份）
        data_list = []
        tables_2026 = ['daily_flow_2026_jan', 'daily_flow_2026_feb', 'daily_flow_2026_mar', 'daily_flow_2026_apr', 'daily_flow_2026_may']
        
        for config in HOSPITALS:
            # UNION ALL 联合所有 2026 年表
            queries = []
            for t in tables_2026:
                queries.append(f"SELECT SUBSTR(COALESCE(NULLIF(TRIM(yewu_wancheng_shijian),''), NULLIF(TRIM(\"业务完成时间\"),'')),1,10) as date, COUNT(*) as orders, SUM(COALESCE(amount, CAST(\"订单金额\" AS REAL))) as flow FROM {t} WHERE (institution LIKE '%{config['name']}%' OR \"机构名称\" LIKE '%{config['name']}%') AND (ye_wu_lei_mu LIKE '%处方%' OR \"业绩类目\" LIKE '%处方%') AND (pay_status='收费' OR \"收退标识\"='收费') AND (yewu_wancheng_shijian IS NOT NULL AND yewu_wancheng_shijian != '' AND yewu_wancheng_shijian != 'NaT' OR \"业务完成时间\" IS NOT NULL AND \"业务完成时间\" != '' AND \"业务完成时间\" != 'NaT') GROUP BY SUBSTR(COALESCE(NULLIF(TRIM(yewu_wancheng_shijian),''), NULLIF(TRIM(\"业务完成时间\"),'')),1,10)")
            
            full_query = ' UNION ALL '.join(queries)
            inner = f'SELECT date, SUM(orders) as orders, SUM(flow) as flow FROM ({full_query}) GROUP BY date ORDER BY date'
            cursor2.execute(inner)
            rows = cursor2.fetchall()
            df = pd.DataFrame(rows, columns=['date', 'orders', 'flow'])
            df = df[df['date'].notna()]
            df['date'] = pd.to_datetime(df['date'])
            
            if len(df) > 0:
                config['data'] = df
                config['total_orders'] = int(df['orders'].sum())
                config['total_flow'] = float(df['flow'].sum())
                data_list.append(config)
        
        if not data_list:
            st.info("🔍 暂无数据")
        else:
            # 2x2 布局
            row1_col1, row1_col2 = st.columns(2)
            row2_col1, row2_col2 = st.columns(2)
            cols = [row1_col1, row1_col2, row2_col1, row2_col2]
            
            for idx, config in enumerate(data_list):
                df = config['data']
                
                # === 数据清洗：去重、聚合、补全日期 ===
                if not df.empty:
                    df['date'] = pd.to_datetime(df['date'])
                    
                    # 1. 聚合：按日期汇总（防止 UNION ALL 产生重复行）
                    agg_dict = {'orders': 'sum'}
                    if 'flow' in df.columns:
                        agg_dict['flow'] = 'sum'
                    df = df.groupby('date').agg(agg_dict).reset_index()

                    # 2. 补全日期：确保每一天都有数据，缺失的填 0
                    df = df.set_index('date')
                    max_date = df.index.max()
                    target_end = max(max_date, pd.Timestamp.now() - pd.Timedelta(days=1)).normalize()
                    
                    # 仅对近 30 天的数据补全（太久远的数据不需要补全到今天）
                    if max_date >= pd.Timestamp.now() - pd.Timedelta(days=30):
                         full_range = pd.date_range(start=df.index.min(), end=target_end)
                         df = df.reindex(full_range, fill_value=0)
                    
                    # 重置索引恢复为普通列
                    df = df.reset_index()
                    df.columns = ['date'] + list(agg_dict.keys())
                    config['data'] = df
                    df = config['data']
                
                title = config['title']
                
                # 汇总卡片用累计数据（2026 年至今）
                total_orders_all = config['total_orders']
                total_flow_all = config['total_flow']
                
                # 图表和表格用近 15 天数据
                df_recent = df.tail(15).copy()
                
                with cols[idx]:
                    # 标题
                    st.markdown(f'''<div style="text-align:center;font-size:14px;font-weight:bold;margin-bottom:6px;">{title}</div>''', unsafe_allow_html=True)
                    
                    # 汇总卡片（2026年累计数据）
                    if config['type'] == 'single':
                        st.markdown(f'''<table style="width:100%;border-collapse:collapse;font-size:12px;margin-bottom:6px;">
<tr><td style="padding:4px 8px;border:1px solid #ccc;font-weight:bold;text-align:right;background:#f5f5f5;width:40%;">订单总数（单）：</td>
<td style="padding:4px 8px;border:1px solid #ccc;font-weight:bold;text-align:center;width:60%;">{total_orders_all:,}</td></tr></table>''', unsafe_allow_html=True)
                    else:
                        st.markdown(f'''<table style="width:100%;border-collapse:collapse;font-size:12px;margin-bottom:6px;">
<tr><td style="padding:4px 8px;border:1px solid #ccc;font-weight:bold;text-align:right;background:#f5f5f5;width:28%;">总流水（元）：</td>
<td style="padding:4px 8px;border:1px solid #ccc;font-weight:bold;text-align:center;width:22%;">{total_flow_all:,.0f}</td>
<td style="padding:4px 8px;border:1px solid #ccc;font-weight:bold;text-align:right;background:#f5f5f5;width:28%;">总订单（单）：</td>
<td style="padding:4px 8px;border:1px solid #ccc;font-weight:bold;text-align:center;width:22%;">{total_orders_all:,}</td></tr></table>''', unsafe_allow_html=True)
                    
                    # 图表（近15天数据）
                    if config['type'] == 'single':
                        fig = go.Figure()
                        fig.add_trace(go.Scatter(x=df_recent['date'], y=df_recent['orders'], name='订单', mode='lines+markers', line=dict(color='#FF9800', width=2), marker=dict(size=4)))
                        df_recent['日期显示'] = df_recent['date'].dt.strftime('%-m月%-d日')
                        fig.update_layout(template='plotly_white', height=280,
                            xaxis=dict(title=None, tickvals=df_recent['date'], ticktext=df_recent['日期显示'], tickangle=45, tickfont=dict(size=8)),
                            yaxis=dict(title=None, tickformat=',.0f', side='left'),
                            hovermode='x unified', legend=dict(orientation='h', yanchor='bottom', y=1.12, xanchor='left', x=0, font=dict(size=8)), margin=dict(l=50, r=30, t=5, b=45))
                    else:
                        fig = make_subplots(specs=[[{"secondary_y": True}]])
                        fig.add_trace(go.Scatter(x=df_recent['date'], y=df_recent['flow'], name='流水', mode='lines+markers', line=dict(color='#4285F4', width=2), marker=dict(size=4)), secondary_y=False)
                        fig.add_trace(go.Scatter(x=df_recent['date'], y=df_recent['orders'], name='订单', mode='lines+markers', line=dict(color='#FF9800', width=2), marker=dict(size=4)), secondary_y=True)
                        df_recent['日期显示'] = df_recent['date'].dt.strftime('%-m月%-d日')
                        fig.update_layout(template='plotly_white', height=280,
                            xaxis=dict(title=None, tickvals=df_recent['date'], ticktext=df_recent['日期显示'], tickangle=45, tickfont=dict(size=8)),
                            yaxis=dict(title=None, tickprefix='¥', tickformat=',.0f', side='left'),
                            yaxis2=dict(title=None, side='right', overlaying='y', showgrid=False, tickformat=',.0f'),
                            hovermode='x unified', legend=dict(orientation='h', yanchor='bottom', y=1.12, xanchor='left', x=0, font=dict(size=8)), margin=dict(l=50, r=50, t=5, b=45))
                    
                    st.plotly_chart(fig, use_container_width=True)
                    
                    # 底部表格（近15天数据，HTML 转置透视表）
                    date_list = df_recent['date'].dt.strftime('%m月%d日').tolist()
                    rows_table = []
                    if config['type'] == 'dual':
                        rows_table.append(('流水', '金额', [f"{v:,.0f}" for v in df_recent['flow'].tolist()], '#e8f0fe'))
                        rows_table.append(('订单', '数量', [f"{int(v):,}" for v in df_recent['orders'].tolist()], '#fff3e0'))
                    else:
                        rows_table.append(('订单', '数量', [f"{int(v):,}" for v in df_recent['orders'].tolist()], '#fff3e0'))
                    
                    total_flow_recent = df_recent['flow'].sum()
                    total_orders_recent = int(df_recent['orders'].sum())
                    if config['type'] == 'dual':
                        rows_table.append(('流水', '总计', [f"{total_flow_recent:,.0f}"], '#d4edda'))
                    rows_table.append(('订单', '总计', [f"{total_orders_recent:,}"], '#d4edda'))
                    
                    th_cells = '<th style="padding:2px 3px;border:1px solid #ccc;background:#f0f0f0;font-weight:bold;text-align:center;font-size:8px;white-space:nowrap;">日期</th>'
                    for d in date_list:
                        th_cells += f'<th style="padding:2px 3px;border:1px solid #ccc;background:#f0f0f0;text-align:center;font-size:8px;white-space:nowrap;">{d}</th>'
                    thead = f'<thead><tr>{th_cells}</tr></thead>'
                    
                    tbody = '<tbody>'
                    for rt, rn, vals, bg in rows_table:
                        tr = f'<td style="padding:2px 3px;border:1px solid #ccc;background:{bg};font-weight:bold;text-align:center;font-size:8px;white-space:nowrap;">{rn}{rt}</td>'
                        for v in vals:
                            tr += f'<td style="padding:2px 3px;border:1px solid #ccc;text-align:right;font-size:8px;white-space:nowrap;">{v}</td>'
                        tbody += f'<tr>{tr}</tr>'
                    tbody += '</tbody>'
                    
                    n_cols = len(date_list) + 1
                    colgroup = f'<col style="width:70px;">' + f'<col>' * n_cols
                    st.markdown(f'<div style="width:100%;"><table style="border-collapse:collapse;font-family:monospace;width:100%;table-layout:fixed;"><colgroup>{colgroup}</colgroup>{thead}{tbody}</table></div>', unsafe_allow_html=True)
        
        conn2.close()
    
    except Exception as e:
        st.error(f"❌ 机构趋势图加载失败：{e}")

# ========== 便捷配药 - 新增机构趋势图 ==========
    st.markdown('---')
    st.markdown('<div style="text-align:center;font-size:18px;font-weight:bold;padding:8px 0;background:#2196F3;color:white;">新增机构便捷配药数据趋势图</div>', unsafe_allow_html=True)
    st.markdown('')
    
    try:
        # 重新连接数据库
        conn3 = sqlite3.connect(DB_PATH)
        cursor3 = conn3.cursor()
        
        # 新增医院配置（4 家便捷配药医院）
        NEW_HOSPITALS = [
            {'title': '齐鲁德医便捷配药订单统计', 'name': '齐鲁德医', 'total': 71061},
            {'title': '齐鲁第二医院便捷配药订单统计', 'name': '齐鲁第二医院', 'total': 4645},
            {'title': '安徽省立医院便捷配药订单统计', 'name': '安徽省立医院', 'total': 7089},
            {'title': '青岛中心医院便捷配药订单统计', 'name': '青岛中心', 'total': 115}
        ]
        
        tables_2026 = ['daily_flow_2026_jan', 'daily_flow_2026_feb', 'daily_flow_2026_mar', 'daily_flow_2026_apr', 'daily_flow_2026_may']
        
        # 获取数据
        data_list = []
        for config in NEW_HOSPITALS:
            queries = []
            for t in tables_2026:
                queries.append(f"SELECT SUBSTR(COALESCE(NULLIF(TRIM(yewu_wancheng_shijian),''), NULLIF(TRIM(\"业务完成时间\"),'')),1,10) as date, COUNT(*) as orders FROM {t} WHERE (institution LIKE '%{config['name']}%' OR \"机构名称\" LIKE '%{config['name']}%') AND (ye_wu_lei_mu LIKE '%处方%' OR \"业绩类目\" LIKE '%处方%') AND (pay_status='收费' OR \"收退标识\"='收费') AND (yewu_wancheng_shijian IS NOT NULL AND yewu_wancheng_shijian != '' AND yewu_wancheng_shijian != 'NaT' OR \"业务完成时间\" IS NOT NULL AND \"业务完成时间\" != '' AND \"业务完成时间\" != 'NaT') GROUP BY SUBSTR(COALESCE(NULLIF(TRIM(yewu_wancheng_shijian),''), NULLIF(TRIM(\"业务完成时间\"),'')),1,10)")
            
            full_query = ' UNION ALL '.join(queries)
            inner = f'SELECT date, SUM(orders) as orders FROM ({full_query}) GROUP BY date ORDER BY date'
            cursor3.execute(inner)
            rows = cursor3.fetchall()
            df = pd.DataFrame(rows, columns=['date', 'orders'])
            df = df[df['date'].notna()]
            df['date'] = pd.to_datetime(df['date'])
            
            if len(df) > 0:
                config['data'] = df
                config['total_orders'] = int(df['orders'].sum())
                data_list.append(config)
        
        if not data_list:
            st.info("🔍 暂无数据")
        else:
            # 2x2 布局
            row1_col1, row1_col2 = st.columns(2)
            row2_col1, row2_col2 = st.columns(2)
            cols = [row1_col1, row1_col2, row2_col1, row2_col2]
            
            for idx, config in enumerate(data_list):
                df = config['data']
                
                # === 数据清洗：去重、聚合、补全日期 ===
                if not df.empty:
                    df['date'] = pd.to_datetime(df['date'])
                    
                    # 1. 聚合：按日期汇总（防止 UNION ALL 产生重复行）
                    agg_dict = {'orders': 'sum'}
                    if 'flow' in df.columns:
                        agg_dict['flow'] = 'sum'
                    df = df.groupby('date').agg(agg_dict).reset_index()

                    # 2. 补全日期：确保每一天都有数据，缺失的填 0
                    df = df.set_index('date')
                    max_date = df.index.max()
                    target_end = max(max_date, pd.Timestamp.now() - pd.Timedelta(days=1)).normalize()
                    
                    # 仅对近 30 天的数据补全（太久远的数据不需要补全到今天）
                    if max_date >= pd.Timestamp.now() - pd.Timedelta(days=30):
                         full_range = pd.date_range(start=df.index.min(), end=target_end)
                         df = df.reindex(full_range, fill_value=0)
                    
                    # 重置索引恢复为普通列
                    df = df.reset_index()
                    df.columns = ['date'] + list(agg_dict.keys())
                    config['data'] = df
                    df = config['data']
                
                title = config['title']
                
                # 汇总数据（2026年累计）
                total_orders_all = config['total_orders']
                
                # 图表数据（近15天）
                df_recent = df.tail(15).copy()
                
                with cols[idx]:
                    # 标题
                    st.markdown(f'''<div style="text-align:center;font-size:14px;font-weight:bold;margin-bottom:6px;">{title}</div>''', unsafe_allow_html=True)
                    
                    # 汇总卡片（HTML 表格）
                    st.markdown(f'''<table style="width:100%;border-collapse:collapse;font-size:12px;margin-bottom:6px;">
<tr><td style="padding:4px 8px;border:1px solid #ccc;font-weight:bold;text-align:right;background:#f5f5f5;width:40%;">订单总数（单）：</td>
<td style="padding:4px 8px;border:1px solid #ccc;font-weight:bold;text-align:center;width:60%;">{total_orders_all:,}</td></tr></table>''', unsafe_allow_html=True)
                    
                    # 图表（单折线，和上面样式一致）
                    fig = go.Figure()
                    fig.add_trace(go.Scatter(x=df_recent['date'], y=df_recent['orders'], name='订单', mode='lines+markers', line=dict(color='#FF9800', width=2), marker=dict(size=4)))
                    df_recent['日期显示'] = df_recent['date'].dt.strftime('%-m月%-d日')
                    fig.update_layout(template='plotly_white', height=280,
                        xaxis=dict(title=None, tickvals=df_recent['date'], ticktext=df_recent['日期显示'], tickangle=45, tickfont=dict(size=8)),
                        yaxis=dict(title=None, tickformat=',.0f', side='left'),
                        hovermode='x unified', legend=dict(orientation='h', yanchor='bottom', y=1.12, xanchor='left', x=0, font=dict(size=8)), margin=dict(l=50, r=30, t=5, b=45))
                    
                    st.plotly_chart(fig, use_container_width=True)
                    
                    # 底部表格（近15天，HTML 转置透视表）
                    date_list = df_recent['date'].dt.strftime('%m月%d日').tolist()
                    rows_table = [('订单', '数量', [f"{int(v):,}" for v in df_recent['orders'].tolist()], '#fff3e0')]
                    total_orders_recent = int(df_recent['orders'].sum())
                    rows_table.append(('订单', '总计', [f"{total_orders_recent:,}"], '#d4edda'))
                    
                    th_cells = '<th style="padding:2px 3px;border:1px solid #ccc;background:#f0f0f0;font-weight:bold;text-align:center;font-size:8px;white-space:nowrap;">日期</th>'
                    for d in date_list:
                        th_cells += f'<th style="padding:2px 3px;border:1px solid #ccc;background:#f0f0f0;text-align:center;font-size:8px;white-space:nowrap;">{d}</th>'
                    thead = f'<thead><tr>{th_cells}</tr></thead>'
                    
                    tbody = '<tbody>'
                    for rt, rn, vals, bg in rows_table:
                        tr = f'<td style="padding:2px 3px;border:1px solid #ccc;background:{bg};font-weight:bold;text-align:center;font-size:8px;white-space:nowrap;">{rn}{rt}</td>'
                        for v in vals:
                            tr += f'<td style="padding:2px 3px;border:1px solid #ccc;text-align:right;font-size:8px;white-space:nowrap;">{v}</td>'
                        tbody += f'<tr>{tr}</tr>'
                    tbody += '</tbody>'
                    
                    n_cols = len(date_list) + 1
                    colgroup = f'<col style="width:70px;">' + f'<col>' * n_cols
                    st.markdown(f'<div style="width:100%;"><table style="border-collapse:collapse;font-family:monospace;width:100%;table-layout:fixed;"><colgroup>{colgroup}</colgroup>{thead}{tbody}</table></div>', unsafe_allow_html=True)
        
        conn3.close()
    
    except Exception as e:
        st.error(f"❌ 新增机构趋势图加载失败：{e}")

# ========== TAB 8: 每日运营快报 ==========
with tab8:
    st.markdown('<div class="card fade-in"><h3>📋 每日运营快报</h3></div>', unsafe_allow_html=True)

    try:
        # ===== 获取所有有效数据（缓存加载）=====
        df_all = load_daily_express()
        df_all['date'] = pd.to_datetime(df_all['date'])
        df_all = df_all[df_all['date'].notna()]
        df_all['amount'] = pd.to_numeric(df_all['amount'], errors='coerce')

        # 按日期统计订单数，过滤异常日期（<100单的视为异常/测试数据）
        daily_counts = df_all[df_all['pay_status']=='收费'].groupby('date').size()
        valid_dates = daily_counts[daily_counts >= 100].index
        df_valid = df_all[df_all['date'].isin(valid_dates)].copy()
        df_valid = df_valid.sort_values('date')

        # 过滤收费数据
        df_charge = df_valid[df_valid['pay_status'] == '收费'].copy()
        df_refund = df_valid[df_valid['pay_status'] == '退费'].copy()

        if len(df_charge) == 0:
            st.warning("暂无有效数据")
            st.stop()

        # 获取最新有效日期
        latest_date = df_charge['date'].max()
        all_dates = sorted(df_charge['date'].unique())
        date_idx = all_dates.index(latest_date)
        prev_date = all_dates[date_idx - 1] if date_idx > 0 else None

        # ===== 当日数据 =====
        df_today = df_charge[df_charge['date'] == latest_date]
        today_flow = df_today['amount'].sum()
        today_orders = len(df_today)
        today_avg = today_flow / today_orders if today_orders > 0 else 0
        active_hospitals = df_today['institution'].nunique()

        # 月累计
        month_start = latest_date.replace(day=1)
        df_month = df_charge[df_charge['date'] >= month_start]
        month_flow = df_month['amount'].sum()
        month_orders = len(df_month)

        # ===== 整体概览 =====
        st.markdown("---")
        weekdays = ['周一','周二','周三','周四','周五','周六','周日']
        wd = weekdays[latest_date.weekday()]
        st.markdown(f"📅 **最新数据日期：{latest_date.strftime('%Y-%m-%d')}（{wd}）| 有效日期数：{len(valid_dates)} 天")

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("💰 当日流水", f"¥{today_flow:,.0f} 元")
        with col2:
            st.metric("📦 当日订单", f"{today_orders:,} 单")
        with col3:
            st.metric("💲 客单价", f"¥{today_avg:,.0f} 元")
        with col4:
            st.metric("🏥 活跃医院", f"{active_hospitals} 家")

        st.info(f"📊 **月累计**（{month_start.strftime('%m/01')} - {latest_date.strftime('%m/%d')}）：流水 ¥{month_flow:,.0f} 元 | 订单 {month_orders:,} 单")

        # ===== 环比 =====
        if prev_date is not None:
            df_prev = df_charge[df_charge['date'] == prev_date]
            prev_flow = df_prev['amount'].sum()
            prev_orders = len(df_prev)
            flow_chg = ((today_flow - prev_flow) / prev_flow * 100) if prev_flow > 0 else 0
            orders_chg = ((today_orders - prev_orders) / prev_orders * 100) if prev_orders > 0 else 0

            col_c1, col_c2 = st.columns(2)
            with col_c1:
                arrow = "📈" if flow_chg >= 0 else "📉"
                st.metric(f"💰 环比（{latest_date.strftime('%m/%d')} vs {prev_date.strftime('%m/%d')}）", f"¥{today_flow:,.0f}", f"{flow_chg:+.1f}% {arrow}")
            with col_c2:
                arrow = "📈" if orders_chg >= 0 else "📉"
                st.metric(f"📦 订单环比", f"{today_orders:,} 单", f"{orders_chg:+.1f}% {arrow}")

        # ===== 医院排名 =====
        st.markdown("---")
        st.markdown("🏆 **医院排行**")

        hosp_today = df_today.groupby('institution').agg(
            flow=('amount', 'sum'), orders=('amount', 'count')
        ).reset_index().sort_values('flow', ascending=False)

        col_left, col_right = st.columns(2)
        with col_left:
            st.markdown("📈 **流水 TOP10**")
            top10 = hosp_today.head(10)
            fig1 = px.bar(top10, x='flow', y='institution', orientation='h',
                         color='flow', color_continuous_scale='Blues', height=380)
            fig1.update_layout(template='plotly_white', showlegend=False,
                              xaxis_tickformat=',.0f', margin=dict(l=150,r=20,t=10,b=40))
            st.plotly_chart(fig1, use_container_width=True)
        with col_right:
            st.markdown("📦 **订单 TOP10**")
            top10o = hosp_today.sort_values('orders', ascending=False).head(10)
            fig2 = px.bar(top10o, x='orders', y='institution', orientation='h',
                         color='orders', color_continuous_scale='Oranges', height=380)
            fig2.update_layout(template='plotly_white', showlegend=False,
                              xaxis_tickformat=',', margin=dict(l=150,r=20,t=10,b=40))
            st.plotly_chart(fig2, use_container_width=True)

        # 增长/下降 TOP5
        if prev_date is not None:
            st.markdown("---")
            st.markdown(f"📊 **环比变化**（{latest_date.strftime('%m/%d')} vs {prev_date.strftime('%m/%d')}）")

            h_t = df_today.groupby('institution')['amount'].sum().reset_index()
            h_t.columns = ['institution', 'today']
            h_p = df_prev.groupby('institution')['amount'].sum().reset_index()
            h_p.columns = ['institution', 'prev']
            h_c = h_t.merge(h_p, on='institution', how='outer').fillna(0)
            h_c['change'] = h_c['today'] - h_c['prev']

            col_g1, col_g2 = st.columns(2)
            with col_g1:
                st.markdown("📈 **增长 TOP5**")
                growth = h_c.sort_values('change', ascending=False).head(5)
                for _, r in growth.iterrows():
                    st.success(f"**{r['institution'][:12]:<12}** ¥{r['today']:,.0f}（+¥{r['change']:,.0f}）")
            with col_g2:
                st.markdown("📉 **下降 TOP5**")
                decline = h_c.sort_values('change', ascending=True).head(5)
                for _, r in decline.iterrows():
                    st.error(f"**{r['institution'][:12]:<12}** ¥{r['today']:,.0f}（-¥{abs(r['change']):,.0f}）")

        # ===== 业绩类目 =====
        st.markdown("---")
        st.markdown("📂 **业绩类目分析**")

        cat_stats = df_charge[df_charge['ye_wu_lei_mu'].notna()].groupby('ye_wu_lei_mu').agg(
            flow=('amount', 'sum'), orders=('amount', 'count')
        ).sort_values('flow', ascending=False)

        col_c1, col_c2 = st.columns(2)
        with col_c1:
            st.markdown("💰 **类目流水占比**")
            fig3 = px.pie(cat_stats.reset_index(), values='flow', names='ye_wu_lei_mu',
                         hole=0.4, height=350)
            fig3.update_layout(template='plotly_white', margin=dict(l=0,r=0,t=10,b=10))
            fig3.update_traces(textposition='inside', textinfo='percent+label')
            st.plotly_chart(fig3, use_container_width=True)
        with col_c2:
            st.markdown("📋 **类目明细**")
            for cat, row in cat_stats.iterrows():
                pct = row['flow'] / cat_stats['flow'].sum() * 100
                bar = "█" * int(pct / 2)
                st.markdown(f"**{cat}**<br><small>¥{row['flow']:,.0f}（{pct:.1f}%）{int(row['orders']):,}单</small><br>{bar}", unsafe_allow_html=True)

        # ===== 省份分析 =====
        st.markdown("---")
        st.markdown("🌍 **省份分析**")

        prov_stats = df_charge[df_charge['province'].notna()].groupby('province').agg(
            flow=('amount', 'sum'), orders=('amount', 'count')
        ).sort_values('flow', ascending=False)

        col_p1, col_p2 = st.columns(2)
        with col_p1:
            st.markdown("💰 **省份 TOP10**")
            p10 = prov_stats.head(10).reset_index()
            fig4 = px.bar(p10, x='flow', y='province', orientation='h',
                         color='flow', color_continuous_scale='Greens', height=350)
            fig4.update_layout(template='plotly_white', showlegend=False,
                              xaxis_tickformat=',.0f', margin=dict(l=120,r=20,t=10,b=40))
            st.plotly_chart(fig4, use_container_width=True)
        with col_p2:
            st.markdown("📦 **省份订单 TOP10**")
            p10o = prov_stats.sort_values('orders', ascending=False).head(10).reset_index()
            fig5 = px.bar(p10o, x='orders', y='province', orientation='h',
                         color='orders', color_continuous_scale='YlOrRd', height=350)
            fig5.update_layout(template='plotly_white', showlegend=False,
                              xaxis_tickformat=',', margin=dict(l=120,r=20,t=10,b=40))
            st.plotly_chart(fig5, use_container_width=True)

        # ===== 退款监控 =====
        st.markdown("---")
        st.markdown("⚠️ **退款监控**")

        refund_today = df_refund[df_refund['date'] == latest_date]
        refund_flow = abs(refund_today['amount'].sum())
        refund_count = len(refund_today)
        refund_rate = refund_count / (today_orders + refund_count) * 100 if (today_orders + refund_count) > 0 else 0

        col_r1, col_r2, col_r3 = st.columns(3)
        with col_r1:
            st.metric("💸 退款金额", f"¥{refund_flow:,.0f} 元")
        with col_r2:
            st.metric("📦 退款订单", f"{refund_count} 单")
        with col_r3:
            st.metric("📊 退款率", f"{refund_rate:.1f}%")

        if refund_count > 0:
            st.markdown("🏥 **退款 TOP 医院**")
            rh = refund_today.groupby('institution').agg(
                count=('amount', 'count'), flow=('amount', 'sum')
            ).sort_values('count', ascending=False).head(10).reset_index()
            for _, r in rh.iterrows():
                st.warning(f"**{r['institution'][:20]}** {int(r['count'])}单 ¥{abs(r['flow']):,.0f}")

            st.markdown("📂 **退款 TOP 类目**")
            rc = refund_today[refund_today['ye_wu_lei_mu'].notna()].groupby('ye_wu_lei_mu').size().sort_values(ascending=False).head(5)
            for cat, cnt in rc.items():
                st.warning(f"{cat}：{int(cnt)}单")
        else:
            st.success("✅ 今日无退款")


    except Exception as e:
        st.error(f"❌ 运营快报加载失败：{e}")

# ========== TAB 9: 本周数据 http://localhost:8501 ==========
with tab9:
    st.markdown('<div class="card fade-in"><h3>📊 本周数据总结分析</h3></div>', unsafe_allow_html=True)
    
    try:
        # 获取本周数据（周一至周日）
        today = datetime.now()
        monday = today - timedelta(days=today.weekday())
        monday_str = monday.strftime('%Y-%m-%d')
        today_str = today.strftime('%Y-%m-%d')
        
        last_monday = monday - timedelta(days=7)
        last_monday_str = last_monday.strftime('%Y-%m-%d')
        last_today_str = (today - timedelta(days=7)).strftime('%Y-%m-%d')
        
        # 缓存加载所有数据
        week_data, last_week_data = load_week_summary(monday_str, today_str, last_monday_str, last_today_str)
        
        # 计算本周总计
        week_total = sum(row[1] for row in week_data)
        week_days = len(week_data)
        week_avg = week_total / week_days if week_days > 0 else 0
        
        # 计算上周总计
        last_week_total = sum(row[1] for row in last_week_data)
        last_week_days = len(last_week_data)
        last_week_avg = last_week_total / last_week_days if last_week_days > 0 else 0
        
        # 环比
        wow_growth = ((week_total - last_week_total) / last_week_total * 100) if last_week_total > 0 else 0
        
        # ====== 本周概览 ======
        st.markdown("---")
        st.markdown(f"📅 **本周**: {monday_str} 至 {today_str}（{week_days} 天）")
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("💰 本周总流水", f"¥{week_total:,.2f} 万元")
        with col2:
            arrow = "📈" if wow_growth > 0 else "📉"
            st.metric("📊 环比上周", f"{wow_growth:+.1f}%", f"{wow_growth:+.1f}% {arrow}")
        with col3:
            st.metric("📈 日均流水", f"¥{week_avg:,.2f} 万元")
        with col4:
            st.metric("📅 有效天数", f"{week_days} 天")
        
        # ====== 每日趋势图 ======
        st.markdown("---")
        st.markdown("📈 **每日流水趋势**")
        
        if week_data:
            df_week = pd.DataFrame(week_data, columns=['date', 'flow'])
            df_week['date'] = pd.to_datetime(df_week['date'])
            df_week['weekday'] = df_week['date'].dt.day_name()
            
            fig = go.Figure()
            fig.add_trace(go.Bar(
                x=df_week['date'].dt.strftime('%m/%d'),
                y=df_week['flow'],
                text=df_week['flow'].apply(lambda x: f"¥{x:.1f}万"),
                textposition='outside',
                marker_color='#4361ee',
                name='本周'
            ))
            
            if last_week_data:
                df_last = pd.DataFrame(last_week_data, columns=['date', 'flow'])
                df_last['date'] = pd.to_datetime(df_last['date'])
                fig.add_trace(go.Scatter(
                    x=df_last['date'].dt.strftime('%m/%d'),
                    y=df_last['flow'],
                    mode='lines+markers',
                    line=dict(color='#ff6b6b', width=2, dash='dash'),
                    marker=dict(size=6),
                    name='上周'
                ))
            
            fig.update_layout(
                template='plotly_white',
                height=350,
                yaxis=dict(title='流水（万元）', tickformat=',.0f'),
                xaxis=dict(title='日期'),
                legend=dict(orientation='h', y=1.02),
                margin=dict(l=50, r=20, t=30, b=50)
            )
            st.plotly_chart(fig, use_container_width=True)
        
        # ====== 医院 TOP5 ======
        st.markdown("---")
        st.markdown("🏆 **本周医院 TOP5**")
        
        top5 = load_week_hospital_top5(monday_str)
        
        if top5:
            for i, (hosp, orders, flow) in enumerate(top5, 1):
                medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
                st.markdown(f"{medal} **{hosp[:20]}**: ¥{flow:,.0f} 元（{orders} 单）")
        
        # ====== 业绩类目分布 ======
        st.markdown("---")
        st.markdown("📂 **本周业绩类目分布**")
        
        cat_data = load_week_category(monday_str)
        
        if cat_data:
            col_c1, col_c2 = st.columns(2)
            
            with col_c1:
                fig_cat = px.pie(
                    pd.DataFrame(cat_data, columns=['类目', '订单', '流水']),
                    values='流水',
                    names='类目',
                    hole=0.4,
                    height=300
                )
                fig_cat.update_layout(template='plotly_white', margin=dict(l=0, r=0, t=10, b=10))
                fig_cat.update_traces(textposition='inside', textinfo='percent+label')
                st.plotly_chart(fig_cat, use_container_width=True)
            
            with col_c2:
                for cat, orders, flow in cat_data:
                    pct = flow / sum(row[2] for row in cat_data) * 100
                    bar = "█" * int(pct / 2)
                    st.markdown(f"**{cat}**<br><small>¥{flow:,.0f}（{pct:.1f}%）{orders}单</small><br>{bar}", unsafe_allow_html=True)
        
        # ====== 省份 TOP5 ======
        st.markdown("---")
        st.markdown("🌍 **本周省份 TOP5**")
        
        prov_data = load_week_province_top5(monday_str)
        
        if prov_data:
            for i, (prov, orders, flow) in enumerate(prov_data, 1):
                medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
                st.markdown(f"{medal} **{prov}**: ¥{flow:,.0f} 元（{orders} 单）")
        
        # ====== 💊 便捷购药专项分析 ======
        st.markdown("---")
        st.markdown('<div style="text-align:center;font-size:18px;font-weight:bold;padding:8px 0;background:#2196F3;color:white;">💊 本周便捷购药专项分析</div>', unsafe_allow_html=True)
        st.markdown("")

        try:
            rx_data = load_week_rx(monday_str, last_monday_str, last_today_str)
            rx_total_orders, rx_total_flow = rx_data['total']
            rx_total_flow = rx_total_flow or 0
            rx_last_orders, rx_last_flow = rx_data['last']
            rx_last_flow = rx_last_flow or 0

            # 环比
            rx_wow = ((rx_total_flow - rx_last_flow) / rx_last_flow * 100) if rx_last_flow > 0 else 0
            rx_wow_orders = ((rx_total_orders - rx_last_orders) / rx_last_orders * 100) if rx_last_orders > 0 else 0

            # KPI 卡片
            rx_col1, rx_col2, rx_col3, rx_col4 = st.columns(4)
            with rx_col1:
                st.metric("💊 本周处方订单", f"{rx_total_orders:,} 单", f"{rx_wow_orders:+.1f}% vs上周")
            with rx_col2:
                st.metric("💰 本周处方流水", f"¥{rx_total_flow:,.0f}", f"{rx_wow:+.1f}% vs上周")
            with rx_col3:
                rx_avg = rx_total_flow / rx_total_orders if rx_total_orders > 0 else 0
                st.metric("📊 客单价", f"¥{rx_avg:,.1f}")
            with rx_col4:
                rx_daily_avg = rx_total_orders / week_days if week_days > 0 else 0
                st.metric("📈 日均订单", f"{rx_daily_avg:,.0f} 单")

            # 3. 每日趋势（本周 vs 上周）
            st.markdown("---")
            st.markdown("📈 **便捷购药每日趋势（本周 vs 上周）**")

            rx_week = rx_data['week']
            rx_last_week = rx_data['last_week']

            if rx_week:
                df_rx = pd.DataFrame(rx_week, columns=['date', 'orders', 'flow'])
                df_rx['date'] = pd.to_datetime(df_rx['date'])

                fig_rx = make_subplots(specs=[[{"secondary_y": True}]])
                fig_rx.add_trace(go.Bar(
                    x=df_rx['date'].dt.strftime('%m/%d %a'),
                    y=df_rx['flow'],
                    text=df_rx['flow'].apply(lambda x: f"¥{x:,.0f}"),
                    textposition='outside',
                    marker_color='#4285F4',
                    name='本周流水'
                ), secondary_y=False)
                fig_rx.add_trace(go.Scatter(
                    x=df_rx['date'].dt.strftime('%m/%d %a'),
                    y=df_rx['orders'],
                    mode='lines+markers+text',
                    text=df_rx['orders'].apply(lambda x: f"{x}"),
                    textposition='top center',
                    line=dict(color='#FF9800', width=2),
                    marker=dict(size=6),
                    name='本周订单'
                ), secondary_y=True)

                if rx_last_week:
                    df_rx_last = pd.DataFrame(rx_last_week, columns=['date', 'orders', 'flow'])
                    df_rx_last['date'] = pd.to_datetime(df_rx_last['date'])
                    # 对齐 x 轴：用本周日期标签
                    x_labels = df_rx['date'].dt.strftime('%m/%d %a').tolist()
                    fig_rx.add_trace(go.Scatter(
                        x=x_labels[:len(df_rx_last)],
                        y=df_rx_last['flow'].tolist()[:len(x_labels)],
                        mode='lines+markers',
                        line=dict(color='#ff6b6b', width=2, dash='dash'),
                        marker=dict(size=5),
                        name='上周流水'
                    ), secondary_y=False)

                fig_rx.update_layout(
                    template='plotly_white', height=380,
                    yaxis=dict(title='流水（元）', tickprefix='¥', tickformat=',.0f'),
                    yaxis2=dict(title='订单数', side='right', showgrid=False),
                    legend=dict(orientation='h', y=1.08, xanchor='left', x=0),
                    margin=dict(l=50, r=50, t=30, b=50)
                )
                st.plotly_chart(fig_rx, use_container_width=True)

            # 4. 医院排行
            st.markdown("---")
            st.markdown("🏥 **便捷购药医院排行**")

            rx_hosp = rx_data['hosp']

            if rx_hosp:
                rx_h_col1, rx_h_col2 = st.columns(2)

                with rx_h_col1:
                    df_hosp = pd.DataFrame(rx_hosp, columns=['医院', '订单', '流水', '客单价'])
                    df_hosp['医院简称'] = df_hosp['医院'].apply(lambda x: x[:12] + '...' if len(x) > 12 else x)
                    fig_hosp = go.Figure(go.Bar(
                        x=df_hosp['流水'],
                        y=df_hosp['医院简称'],
                        orientation='h',
                        text=df_hosp['流水'].apply(lambda x: f"¥{x:,.0f}"),
                        textposition='auto',
                        marker_color='#4285F4'
                    ))
                    fig_hosp.update_layout(
                        template='plotly_white', height=350,
                        yaxis=dict(autorange='reversed'),
                        xaxis=dict(title='流水（元）', tickprefix='¥', tickformat=',.0f'),
                        margin=dict(l=120, r=20, t=10, b=40)
                    )
                    st.plotly_chart(fig_hosp, use_container_width=True)

                with rx_h_col2:
                    for i, (hosp, orders, flow, avg_p) in enumerate(rx_hosp, 1):
                        medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
                        st.markdown(f"{medal} **{hosp[:18]}**<br><small>¥{flow:,.0f} | {orders}单 | 客单价¥{avg_p:.0f}</small>", unsafe_allow_html=True)

            # 5. 省份分布
            st.markdown("---")
            st.markdown("🗺️ **便捷购药省份分布 TOP10**")

            rx_prov = rx_data['prov']

            if rx_prov:
                rx_p_col1, rx_p_col2 = st.columns(2)

                with rx_p_col1:
                    df_prov = pd.DataFrame(rx_prov, columns=['省份', '订单', '流水'])
                    fig_prov = px.pie(
                        df_prov, values='流水', names='省份',
                        hole=0.4, height=300
                    )
                    fig_prov.update_layout(template='plotly_white', margin=dict(l=0, r=0, t=10, b=10))
                    fig_prov.update_traces(textposition='inside', textinfo='percent+label')
                    st.plotly_chart(fig_prov, use_container_width=True)

                with rx_p_col2:
                    for i, (prov, orders, flow) in enumerate(rx_prov, 1):
                        pct = flow / rx_total_flow * 100 if rx_total_flow > 0 else 0
                        medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
                        st.markdown(f"{medal} **{prov}**: ¥{flow:,.0f}（{pct:.1f}%）| {orders}单", unsafe_allow_html=True)

            # 6. 重点机构日趋势对比
            st.markdown("---")
            st.markdown("📊 **重点机构本周每日对比**")

            key_hospitals = ['浙江省中医院（湖滨院区）', '杭州师范大学附属医院', '黑龙江中医药大学附属第一医院']

            rx_key = rx_data['key']

            if rx_key:
                df_key = pd.DataFrame(rx_key, columns=['date', 'institution', 'orders', 'flow'])
                df_key['date'] = pd.to_datetime(df_key['date'])
                df_key['简称'] = df_key['institution'].apply(lambda x: '浙江省中' if '浙江省中医院' in x else '杭师大附院' if '杭州师范' in x else '黑龙江中医大' if '黑龙江' in x else x[:8])

                fig_key = go.Figure()
                colors = {'浙江省中': '#4285F4', '杭师大附院': '#FF9800', '黑龙江中医大': '#34A853'}
                for name in df_key['简称'].unique():
                    sub = df_key[df_key['简称'] == name]
                    fig_key.add_trace(go.Scatter(
                        x=sub['date'].dt.strftime('%m/%d'),
                        y=sub['orders'],
                        mode='lines+markers+text',
                        text=sub['orders'].apply(str),
                        textposition='top center',
                        name=name,
                        line=dict(color=colors.get(name, '#999'), width=2),
                        marker=dict(size=6)
                    ))
                fig_key.update_layout(
                    template='plotly_white', height=320,
                    yaxis=dict(title='订单数'),
                    legend=dict(orientation='h', y=1.08),
                    margin=dict(l=50, r=20, t=30, b=50)
                )
                st.plotly_chart(fig_key, use_container_width=True)

        except Exception as e:
            st.error(f"❌ 便捷购药专项分析加载失败：{e}")


    except Exception as e:
        st.error(f"❌ 本周总结加载失败：{e}")

# ========== TAB 10: 第三方服务分析 ==========
with tab10:
    st.markdown('<div class="card fade-in"><h3>🔗 第三方服务分析</h3></div>', unsafe_allow_html=True)

    try:
        tp_tables = {
            '2026年1月': 'daily_flow_2026_jan',
            '2026年2月': 'daily_flow_2026_feb',
            '2026年3月': 'daily_flow_2026_mar',
            '2026年4月': 'daily_flow_2026_apr',
            '2026年5月': 'daily_flow_2026_may',
        }

        selected_month = st.selectbox("📅 选择月份", list(tp_tables.keys()), index=len(tp_tables)-1)
        table_name = tp_tables[selected_month]

        # 缓存加载
        company_rows = load_tp_companies(table_name)

        # KPI
        kpi_company = len(company_rows) if company_rows else 0
        kpi_orders = sum(r[1] for r in company_rows) if company_rows else 0
        kpi_amount = sum(r[2] for r in company_rows) if company_rows else 0
        kpi_hosp = sum(r[3] for r in company_rows) if company_rows else 0
        col_k1, col_k2, col_k3, col_k4 = st.columns(4)
        col_k1.metric("🏢 第三方公司数", kpi_company)
        col_k2.metric("📦 第三方订单数", kpi_orders)
        col_k3.metric("💰 分账总金额", f"¥{kpi_amount:,.0f}" if kpi_amount else "¥0")
        col_k4.metric("🏥 覆盖医院数", kpi_hosp)
        st.divider()

        # ========================================
        # 📋 公司列表 + 医院详情（左右布局）
        # ========================================
        if company_rows:
            company_df = pd.DataFrame(company_rows, columns=[
                '公司', '订单数', '分账金额', '覆盖医院数'
            ])
            col_left, col_right = st.columns([1, 3])

            with col_left:
                st.subheader("📋 第三方公司列表")
                selected_company = st.selectbox(
                    "选择公司查看详情",
                    options=[r[0] for r in company_rows],
                    label_visibility="collapsed"
                )
                st.dataframe(company_df, use_container_width=True, height=500)

            with col_right:
                if selected_company:
                    st.subheader(f"🏥 {selected_company} — 覆盖医院详情")
                    hosp_detail = load_tp_hosp_detail(table_name, selected_company)

                    if hosp_detail:
                        total_tp = sum(r[2] for r in hosp_detail)
                        total_orders = sum(r[1] for r in hosp_detail)
                        st.markdown(
                            f"<div style='padding:12px;background:#f0f4ff;border-radius:8px;"
                            f"margin-bottom:16px;'>"
                            f"<b>📊 公司概览</b> | 覆盖 <b>{len(hosp_detail)}</b> 家医院 | "
                            f"第三方订单 <b>{total_orders}</b> 单 | "
                            f"分账总额 <b>¥{total_tp:,.0f}</b>"
                            f"</div>",
                            unsafe_allow_html=True
                        )

                        hosp_df = pd.DataFrame(hosp_detail, columns=[
                            '医院', '订单数', '分账金额', '订单总金额',
                            '平均单笔分账', '平均单笔订单金额'
                        ])
                        hosp_df['分账占比'] = (hosp_df['分账金额'] / hosp_df['订单总金额'] * 100).round(1)
                        hosp_df['订单量占比'] = (hosp_df['订单数'] / total_orders * 100).round(1)
                        st.dataframe(hosp_df, use_container_width=True, height=300)

                        # 医院对比柱状图
                        fig_hosp = px.bar(
                            hosp_df, x='医院', y='分账金额', text='分账金额',
                            color='分账金额', color_continuous_scale='Blues',
                            title=f'{selected_company} 各医院分账金额对比'
                        )
                        fig_hosp.update_layout(
                            height=max(350, len(hosp_detail) * 50),
                            yaxis_title='分账金额（元）', showlegend=False, plot_bgcolor='white'
                        )
                        fig_hosp.update_traces(texttemplate='¥%{text:,.0f}', textposition='outside')
                        fig_hosp.update_xaxes(tickangle=45)
                        st.plotly_chart(fig_hosp, use_container_width=True)

                        # 分账占比饼图
                        if len(hosp_detail) <= 10:
                            fig_pie = px.pie(
                                hosp_df, values='分账金额', names='医院',
                                title=f'{selected_company} 各医院分账占比', hole=0.4
                            )
                            fig_pie.update_layout(height=400, plot_bgcolor='white')
                            st.plotly_chart(fig_pie, use_container_width=True)

                        # 订单数 vs 分账金额 双轴图
                        fig_dual = go.Figure()
                        fig_dual.add_trace(go.Bar(
                            x=hosp_df['医院'], y=hosp_df['订单数'],
                            name='订单数', marker_color='#4361ee', yaxis='y'
                        ))
                        fig_dual.add_trace(go.Scatter(
                            x=hosp_df['医院'], y=hosp_df['分账金额'],
                            name='分账金额', marker_color='#f72585',
                            mode='lines+markers', yaxis='y2'
                        ))
                        fig_dual.update_layout(
                            height=400,
                            title=f'{selected_company} 订单数 vs 分账金额',
                            plot_bgcolor='white',
                            yaxis=dict(title='订单数', side='left'),
                            yaxis2=dict(title='分账金额（元）', side='right', overlaying='y'),
                            xaxis=dict(tickangle=45),
                            legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01)
                        )
                        st.plotly_chart(fig_dual, use_container_width=True)
                    else:
                        st.info(f"{selected_company} 暂无医院数据")

            st.divider()

            # ========================================
            # 📊 第三方公司 × 医院 月度环比
            # ========================================
            st.subheader("📊 第三方公司 × 医院 月度环比")

            try:
                tp_month_hosp_data = load_tp_month_hosp()

                # 获取所有有数据的第三方公司列表
                tp_companies_list = sorted(set(r[0] for r in tp_month_hosp_data)) if tp_month_hosp_data else []
                month_order = ['2026年1月', '2026年2月', '2026年3月', '2026年4月', '2026年5月']

                tp_select_options = ['📋 全量概览'] + tp_companies_list
                tp_select_choice = st.selectbox(
                    "选择第三方公司查看环比", tp_select_options,
                    index=0, key="tp_mom_select"
                )

                if tp_select_choice == '📋 全量概览':
                    # 全量概览：按公司维度汇总
                    summary = {}
                    for r in tp_month_hosp_data:
                        co, hosp, mn, orders, amt = r
                        key = co
                        if key not in summary:
                            summary[key] = {}
                        if mn not in summary[key]:
                            summary[key][mn] = {'amount': 0.0, 'orders': 0}
                        summary[key][mn]['amount'] += amt
                        summary[key][mn]['orders'] += orders

                    # 按总金额排序，取TOP10
                    sorted_cos = sorted(summary.keys(),
                                        key=lambda c: sum(summary[c].get(m, {}).get('amount', 0) for m in month_order),
                                        reverse=True)[:10]

                    def _color_mom_summary(val):
                        if not isinstance(val, str):
                            return ''
                        if '↓' in val:
                            return 'color: #dc3545; font-weight: bold'
                        elif '↑' in val or '新增' in val:
                            return 'color: #28a745; font-weight: bold'
                        return ''

                    display_data = []
                    for co in sorted_cos:
                        row_data = {'公司': co}
                        for mn in month_order:
                            row_data[mn] = summary.get(co, {}).get(mn, {}).get('amount', 0)
                        display_data.append(row_data)

                    if display_data:
                        sum_df = pd.DataFrame(display_data)
                        st.dataframe(
                            sum_df.style.map(_color_mom_summary,
                                                   subset=[c for c in month_order]),
                            use_container_width=True, height=400
                        )
                    else:
                        st.info("暂无全量概览数据")

                else:
                    # 单公司医院维度环比
                    company_data = load_tp_month_hosp(company_name=tp_select_choice)

                    if not company_data:
                        st.info(f"{tp_select_choice} 暂无月度数据")
                    else:
                        # 聚合: 按 (hospital, month) → amount
                        hosp_month = {}
                        active_months = set()
                        for r in company_data:
                            co, hosp, mn, orders, amt = r
                            if (hosp, mn) not in hosp_month:
                                hosp_month[(hosp, mn)] = 0.0
                            hosp_month[(hosp, mn)] += amt
                            active_months.add(mn)

                        # 按实际有数据的月份（保持顺序）
                        actual_months = [m for m in month_order if m in active_months]

                        # 按总金额排序医院
                        hosp_totals = {}
                        for (h, m), a in hosp_month.items():
                            hosp_totals[h] = hosp_totals.get(h, 0) + a
                        sorted_hospitals = sorted(hosp_totals.keys(), key=lambda h: hosp_totals[h], reverse=True)

                        def _color_mom(val):
                            if not isinstance(val, str):
                                return ''
                            if '↓' in val:
                                return 'color: #dc3545; font-weight: bold'
                            elif '↑' in val or '新增' in val:
                                return 'color: #28a745; font-weight: bold'
                            return ''

                        display_rows = []
                        for hosp in sorted_hospitals:
                            row = {'医院': hosp}
                            for mn in actual_months:
                                row[mn] = hosp_month.get((hosp, mn), 0)

                            # 环比计算：最后一个月 vs 前一个月
                            if len(actual_months) >= 2:
                                curr_mn = actual_months[-1]
                                prev_mn = actual_months[-2]
                                curr_amt = hosp_month.get((hosp, curr_mn), 0)
                                prev_amt = hosp_month.get((hosp, prev_mn), 0)
                                diff = curr_amt - prev_amt
                                if prev_amt == 0:
                                    change_str = "🆕 新增"
                                else:
                                    pct = (diff / prev_amt) * 100
                                    if diff > 0:
                                        change_str = f"↑ +{diff:,.0f} (+{pct:.1f}%)"
                                    elif diff < 0:
                                        change_str = f"↓ {diff:,.0f} ({pct:.1f}%)"
                                    else:
                                        change_str = "— 持平"
                                row['环比上月'] = change_str
                            else:
                                row['环比上月'] = "— 仅单月数据"

                            display_rows.append(row)

                        if display_rows:
                            mom_df = pd.DataFrame(display_rows)
                            col_list = ['医院'] + actual_months + ['环比上月']
                            styled = mom_df.style.map(_color_mom, subset=['环比上月'])
                            # 金额列格式化
                            styled = styled.format({
                                m: lambda x: f"¥{x:,.0f}" if isinstance(x, (int, float)) else x
                                for m in actual_months
                            })
                            st.dataframe(styled, use_container_width=True, height=max(350, len(display_rows) * 35 + 50))

                            # 环比饼图（显示环比变动TOP医院）
                            mom_with_vals = []
                            for row in display_rows:
                                rs = str(row.get('环比上月', ''))
                                if '↑' in rs or '↓' in rs:
                                    import re
                                    nums = re.findall(r'[-+]?[\d,]+\.?\d*', rs)
                                    if nums:
                                        val = float(nums[0].replace(',', ''))
                                        mom_with_vals.append({'医院': row['医院'], '增减金额': val})
                            if mom_with_vals:
                                mom_vals_df = pd.DataFrame(mom_with_vals).sort_values('增减金额', ascending=False).head(10)
                                fig_mom_bar = px.bar(
                                    mom_vals_df, x='医院', y='增减金额',
                                    color='增减金额', text='增减金额',
                                    color_continuous_scale='RdYlGn',
                                    title=f'{tp_select_choice} 环比上月增减金额 TOP10'
                                )
                                fig_mom_bar.update_layout(height=350, plot_bgcolor='white')
                                fig_mom_bar.update_traces(texttemplate='¥%{text:,.0f}', textposition='outside')
                                fig_mom_bar.update_xaxes(tickangle=45)
                                st.plotly_chart(fig_mom_bar, use_container_width=True)
                        else:
                            st.info("暂无环比数据")

            except Exception as e:
                st.error(f"❌ 月度环比加载失败：{e}")

        else:
            st.info(f"{selected_month} 暂无第三方分账数据")


    except Exception as e:
        st.error(f"❌ 第三方服务分析加载失败：{e}")
        import traceback
        st.code(traceback.format_exc())


# ========== TAB 11: 用户行为分析 ==========
with tab11:
    st.markdown('<div class="card fade-in"><h3>📊 用户行为分析 · 医院运营月报</h3></div>', unsafe_allow_html=True)

    import json
    from pathlib import Path as Path2
    DATA_DIR = Path2(__file__).parent

    @st.cache_data(ttl=3600)
    def load_fenxiti_data():
        data = {}
        for name, fname in [
            ('monthly_4', 'data_fenxiti_monthly_4.json'),
            ('monthly_5', 'data_fenxiti_monthly_5.json'),
            ('rx_4', 'data_fenxiti_rx_4.json'),
            ('rx_5', 'data_fenxiti_rx_5.json'),
        ]:
            fpath = DATA_DIR / fname
            if fpath.exists():
                with open(fpath, 'r') as f:
                    data[name] = json.load(f)
        return data

    try:
        fx_data = load_fenxiti_data()
        if not all(k in fx_data for k in ['monthly_4', 'monthly_5', 'rx_4', 'rx_5']):
            st.warning("⚠️ 数据未加载，请检查数据文件")
        else:
            d4 = fx_data['monthly_4']
            d5 = fx_data['monthly_5']
            # 从 API 数据中获取 5 月实际结束日期
            ai5 = d5.get('analysisInfo', {})
            ai5_end = str(ai5.get('endTime', '27'))[8:10].lstrip('0')  # 提取天数

            # 构建医院列表
            hospitals_4 = {r[1]: r for r in d4['resultRows']}
            hospitals_5 = {r[1]: r for r in d5['resultRows']}
            all_hospitals = sorted(set(hospitals_4.keys()) | set(hospitals_5.keys()))

            # ── 医院选择器（唯一入口）──
            st.markdown('<div style="text-align:center;font-size:15px;color:#94A3B8;margin-bottom:8px;">选择一家医院，查看该院专属运营数据报告（仅显示该院数据，无其他医院信息）</div>', unsafe_allow_html=True)
            selected_hospital = st.selectbox(
                "🏥 选择医院",
                ["— 请选择医院 —"] + all_hospitals,
                index=0
            )

            if selected_hospital == "— 请选择医院 —":
                st.info("👆 请先选择一家医院，查看该院的专属运营数据报告")
                st.markdown(
                    '<div style="text-align:center;padding:50px 20px;color:#94A3B8;">'
                    '<p style="font-size:64px;margin:0;">🏥</p>'
                    '<p style="font-size:16px;margin-top:16px;">选择医院后，将显示该院的：</p>'
                    '<p style="margin:4px 0;">• 4月 vs 5月核心指标对比</p>'
                    '<p style="margin:4px 0;">• 用户转化漏斗</p>'
                    '<p style="margin:4px 0;">• 复购率趋势分析</p>'
                    '<p style="margin:4px 0;">• 药方维度详细数据</p>'
                    '</div>',
                    unsafe_allow_html=True
                )
            else:
                # ── 仅展示选中医院的专属数据 ──
                r4 = hospitals_4.get(selected_hospital)
                r5 = hospitals_5.get(selected_hospital)

                # 报告标题
                st.markdown(f'<div style="text-align:center;font-size:22px;font-weight:bold;padding:16px;background:linear-gradient(90deg,#0EA5E9,#3B82F6);color:white;border-radius:10px;margin-bottom:16px;">📋 {selected_hospital} · 运营数据报告</div>', unsafe_allow_html=True)

                # 解析 5月数据
                if r5:
                    g5 = float(r5[2]); v5 = int(r5[3]); pv5 = int(r5[4]); q5 = int(r5[5])
                    o5 = int(r5[6]); p5_cnt = int(r5[7]); avg5 = float(r5[8])
                    order5 = int(r5[9]); conv5 = float(r5[10]) if r5[10] else 0
                    r60_5 = float(r5[11]) if r5[11] and str(r5[11]) != 'nan' else 0
                    r30_5 = float(r5[12]) if r5[12] and str(r5[12]) != 'nan' else 0
                    r14_5 = float(r5[13]) if r5[13] and str(r5[13]) != 'nan' else 0
                else:
                    st.warning(f"⚠️ 暂无 {selected_hospital} 的5月数据")
                    st.stop()

                # 解析 4月数据（用于环比）
                if r4:
                    g4 = float(r4[2]); v4 = int(r4[3]); pv4 = int(r4[4]); q4 = int(r4[5])
                    o4 = int(r4[6]); p4_cnt = int(r4[7]); avg4 = float(r4[8])
                    order4 = int(r4[9]); conv4 = float(r4[10]) if r4[10] else 0
                    r60_4 = float(r4[11]) if r4[11] and str(r4[11]) != 'nan' else 0
                    r30_4 = float(r4[12]) if r4[12] and str(r4[12]) != 'nan' else 0
                    r14_4 = float(r4[13]) if r4[13] and str(r4[13]) != 'nan' else 0
                else:
                    g4 = v4 = pv4 = q4 = o4 = p4_cnt = order4 = 0
                    avg4 = conv4 = r60_4 = r30_4 = r14_4 = 0

                def fmt_chg(curr, prev):
                    if prev == 0: return None
                    return f"{(curr - prev) / prev * 100:+.1f}%"

                # ── 核心指标 ──
                st.subheader(f"📈 4月 vs 5月(1-{ai5_end}) 核心指标对比")
                c1, c2, c3, c4, c5, c6 = st.columns(6)
                c1.metric("💰 GMV", f"¥{g5:,.0f}", fmt_chg(g5, g4) if r4 else None)
                c2.metric("👥 访问人数", f"{v5:,}", fmt_chg(v5, v4) if r4 else None)
                c3.metric("📦 支付订单", f"{order5:,}", fmt_chg(order5, order4) if r4 else None)
                c4.metric("💲 客单价", f"¥{avg5:.2f}", fmt_chg(avg5, avg4) if r4 else None)
                c5.metric("🔄 转化率", f"{conv5*100:.1f}%", fmt_chg(conv5*100, conv4*100) if r4 else None)
                c6.metric("🔁 60天复购", f"{r60_5*100:.1f}%", fmt_chg(r60_5*100, r60_4*100) if r4 else None)

                st.info(f"📅 数据周期：4月(4/1~5/1) vs 5月(5/1~5/{ai5_end})")
                st.divider()

                # ── 转化漏斗 ──
                st.subheader("🔻 用户转化漏斗 (5月 vs 4月)")
                funnel_labels = ['访问总人数', '商详浏览人数', '问卷提交成功人数', '订单创建人数', '订单支付成功人数']
                funnel_vals_5 = [v5, pv5, q5, o5, p5_cnt]
                funnel_vals_4 = [v4, pv4, q4, o4, p4_cnt]
                
                # 转化漏斗明细表
                funnel_detail = []
                for i, label in enumerate(funnel_labels):
                    curr = funnel_vals_5[i]
                    prev = funnel_vals_4[i]
                    if prev > 0:
                        ringbi = f"{((curr - prev) / prev * 100):+.1f}%"
                    else:
                        ringbi = '—'
                    funnel_detail.append({
                        '步骤': label,
                        '本期(5月)': curr,
                        '上期(4月)': prev,
                        '环比': ringbi
                    })
                df_funnel = pd.DataFrame(funnel_detail)
                st.dataframe(df_funnel, use_container_width=True, hide_index=True,
                            column_config={
                                '本期(5月)': st.column_config.NumberColumn("本期(5月)", format="%,d"),
                                '上期(4月)': st.column_config.NumberColumn("上期(4月)", format="%,d"),
                            })
                
                st.divider()
                
                # 转化率矩阵
                st.subheader("📊 各节点转化率")
                
                conv_data = []
                # 访问→问卷
                conv_v_q5 = round(q5 / v5 * 100, 1) if v5 > 0 else 0
                conv_v_q4 = round(q4 / v4 * 100, 1) if v4 > 0 else 0
                conv_data.append({'转化率': '访问→问卷', '本期': conv_v_q5, '上期': conv_v_q4})
                
                # 浏览→问卷
                conv_pv_q5 = round(q5 / pv5 * 100, 1) if pv5 > 0 else 0
                conv_pv_q4 = round(q4 / pv4 * 100, 1) if pv4 > 0 else 0
                conv_data.append({'转化率': '商详浏览→问卷', '本期': conv_pv_q5, '上期': conv_pv_q4})
                
                # 访问→创建
                conv_v_o5 = round(o5 / v5 * 100, 1) if v5 > 0 else 0
                conv_v_o4 = round(o4 / v4 * 100, 1) if v4 > 0 else 0
                conv_data.append({'转化率': '访问→订单创建', '本期': conv_v_o5, '上期': conv_v_o4})
                
                # 问卷→创建
                conv_q_o5 = round(o5 / q5 * 100, 1) if q5 > 0 else 0
                conv_q_o4 = round(o4 / q4 * 100, 1) if q4 > 0 else 0
                conv_data.append({'转化率': '问卷→订单创建', '本期': conv_q_o5, '上期': conv_q_o4})
                
                # 访问→支付
                conv_v_p5 = round(p5_cnt / v5 * 100, 1) if v5 > 0 else 0
                conv_v_p4 = round(p4_cnt / v4 * 100, 1) if v4 > 0 else 0
                conv_data.append({'转化率': '访问→支付成功', '本期': conv_v_p5, '上期': conv_v_p4})
                
                # 创建→支付
                conv_o_p5 = round(p5_cnt / o5 * 100, 1) if o5 > 0 else 0
                conv_o_p4 = round(p4_cnt / o4 * 100, 1) if o4 > 0 else 0
                conv_data.append({'转化率': '订单创建→支付成功', '本期': conv_o_p5, '上期': conv_o_p4})
                
                df_conv = pd.DataFrame(conv_data)
                st.dataframe(df_conv, use_container_width=True, hide_index=True,
                            column_config={
                                '本期': st.column_config.NumberColumn("本期(5月)", format="%.1f%%"),
                                '上期': st.column_config.NumberColumn("上期(4月)", format="%.1f%%"),
                            })
                st.divider()

                # ── 复购率分析 ──
                st.subheader("🔁 复购率分析")
                col_r1, col_r2, col_r3 = st.columns(3)
                col_r1.metric("近14天复购率", f"{r14_5*100:.1f}%")
                col_r2.metric("近30天复购率", f"{r30_5*100:.1f}%")
                col_r3.metric("近60天复购率", f"{r60_5*100:.1f}%")

                if r4:
                    fig_ret = go.Figure()
                    fig_ret.add_trace(go.Bar(
                        x=['近14天', '近30天', '近60天'],
                        y=[r14_4*100, r30_4*100, r60_4*100],
                        name='4月', marker_color='rgba(99,110,250,0.6)'
                    ))
                    fig_ret.add_trace(go.Bar(
                        x=['近14天', '近30天', '近60天'],
                        y=[r14_5*100, r30_5*100, r60_5*100],
                        name='5月', marker_color='rgba(0,204,150,0.8)'
                    ))
                    fig_ret.update_layout(
                        barmode='group', height=300, template='plotly_white',
                        yaxis=dict(title='复购率(%)', ticksuffix='%')
                    )
                    st.plotly_chart(fig_ret, use_container_width=True)
                st.divider()

                # ── 药方维度数据（仅该院）──
                st.subheader("💊 药方维度数据 (5月)")
                rx5 = fx_data['rx_5']
                # 用 resultHeader 动态匹配列索引（rx_4 和 rx_5 列结构不同！）
                def rx_row(r, rx_data):
                    h = rx_data['resultHeader']
                    def idx(name):
                        for j, hname in enumerate(h):
                            if name in hname:
                                return j
                        return -1
                    return {
                        '药方名称': r[1],
                        '是否需问卷': r[5] if idx('购买是否需要问卷') == 5 else '',
                        '详情页浏览': int(float(r[idx('详情页浏览')])) if idx('详情页浏览') >= 0 and r[idx('详情页浏览')] else 0,
                        '加购人数': int(float(r[idx('加购')])) if idx('加购') >= 0 and r[idx('加购')] else 0,
                        '订单提交': int(float(r[idx('提交')])) if idx('提交') >= 0 and r[idx('提交')] else 0,
                        '支付成功': int(float(r[idx('支付成功')])) if idx('支付成功') >= 0 and r[idx('支付成功')] else 0,
                        '转化率': round(float(r[idx('转化率')]), 2) if idx('转化率') >= 0 and r[idx('转化率')] else 0,
                        '支付金额': round(float(r[idx('金额')]), 2) if idx('金额') >= 0 and r[idx('金额')] else 0,
                    }
                
                rx5_rows = [rx_row(r, rx5) for r in rx5['resultRows'] if r[3] == selected_hospital]
                
                # 同时获取 4月药方数据
                rx4 = fx_data['rx_4']
                rx4_rows = [rx_row(r, rx4) for r in rx4['resultRows'] if r[3] == selected_hospital]

                if rx5_rows:
                    df_rx5 = pd.DataFrame(rx5_rows).sort_values('支付金额', ascending=False)
                    st.markdown("**5月药方数据**")
                    st.dataframe(df_rx5, use_container_width=True, hide_index=True,
                                column_config={
                                    '支付金额': st.column_config.NumberColumn("支付金额", format="¥%.2f"),
                                    '转化率': st.column_config.NumberColumn("转化率", format="%.2f%%"),
                                })
                    rx_top = df_rx5.head(10)
                    fig_rx = px.bar(
                        rx_top, x='支付金额', y='药方名称', orientation='h',
                        title='药方 GMV TOP 10',
                        color='支付金额', color_continuous_scale='Blues'
                    )
                    fig_rx.update_layout(height=400, template='plotly_white')
                    st.plotly_chart(fig_rx, use_container_width=True)
                    
                    # 4月药方对比
                    if rx4_rows:
                        st.markdown("**4月药方数据（对比）**")
                        df_rx4 = pd.DataFrame(rx4_rows).sort_values('支付金额', ascending=False)
                        st.dataframe(df_rx4, use_container_width=True, hide_index=True,
                                    column_config={
                                        '支付金额': st.column_config.NumberColumn("支付金额", format="¥%.2f"),
                                        '转化率': st.column_config.NumberColumn("转化率", format="%.2f%%"),
                                    })
                else:
                    st.info("💊 暂无该院的药方数据")

    except Exception as e:
        st.error(f"❌ 加载失败：{e}")
        import traceback
        st.code(traceback.format_exc())

# ========== 底部信息 ==========
st.divider()
col_info1, col_info2, col_info3 = st.columns(3)
with col_info1:
    st.markdown(f"<small>🔄 最后刷新：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</small>", unsafe_allow_html=True)
with col_info2:
    st.markdown("<small>🏥 智能监控，异常秒级响应</small>", unsafe_allow_html=True)
with col_info3:
    st.markdown("<small>⚙️ 优化版运营仪表板 v4.0</small>", unsafe_allow_html=True)