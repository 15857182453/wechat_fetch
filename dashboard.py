#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
医院数据 Dashboard - Streamlit 版本
"""

import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime, timedelta

# 页面配置
st.set_page_config(page_title="医院数据 Dashboard", page_icon="🏥", layout="wide")

# 自定义 CSS 样式 - 暗色主题
custom_css = """
<style>
/* 页面背景渐变 - 暗色主题 */
.stApp {
    background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
    color: #e0e0e0;
}

/* KPI 卡片样式 - 半透明白色/灰色 */
[data-testid="stMetric"] {
    background: rgba(255,255,255,0.15);
    border-radius: 15px;
    padding: 20px;
    backdrop-filter: blur(10px);
    border: 1px solid rgba(255,255,255,0.15);
    box-shadow: 0 8px 32px rgba(0,0,0,0.3);
    transition: transform 0.3s ease;
    height: 120px;
}
[data-testid="stMetric"] .stMetric-label {
    color: #e0e0e0 !important;
}
[data-testid="stMetric"] .stMetric-value {
    color: #ffffff !important;
}
[data-testid="stMetric"] .stMetric-delta {
    color: #a0a0a0 !important;
}
[data-testid="stMetric"]:hover {
    transform: translateY(-5px);
    background: rgba(255,255,255,0.2);
    box-shadow: 0 15px 35px rgba(0,0,0,0.4);
}

/* Tab 样式 */
.stTabs [data-baseweb="tab-list"] {
    gap: 2px;
    margin-top: 20px;
    margin-bottom: 20px;
}
.stTabs [data-baseweb="tab"] {
    border: 1px solid rgba(255,255,255,0.15) !important;
    border-radius: 10px !important;
    margin-right: 2px !important;
    padding: 12px 24px !important;
    background: rgba(255,255,255,0.1) !important;
    backdrop-filter: blur(5px);
    transition: all 0.3s ease;
    color: #e0e0e0 !important;
}
.stTabs [data-baseweb="tab"]:hover {
    background: rgba(255,255,255,0.2) !important;
    transform: scale(1.02);
    color: #ffffff !important;
}
.stTabs [aria-selected="true"] {
    background: linear-gradient(135deg, #4cc9f0, #4361ee) !important;
    color: white !important;
    border: 1px solid rgba(255,255,255,0.3) !important;
}

/* 数据表格样式 */
.stDataFrame, .stTable, .stDownloadButton {
    background: rgba(255,255,255,0.1) !important;
    border: 1px solid rgba(255,255,255,0.15) !important;
    border-radius: 10px !important;
    color: #e0e0e0 !important;
    overflow: hidden !important;
}
tr:nth-of-type(odd) {
    background-color: rgba(255,255,255,0.05) !important;
}
tr:nth-of-type(even) {
    background-color: rgba(255,255,255,0.08) !important;
}
th {
    background-color: rgba(255,255,255,0.1) !important;
    color: #ffffff !important;
}

/* 图表容器 */
.stPlotlyChart {
    background: rgba(255,255,255,0.05);
    border-radius: 12px;
    padding: 15px;
    backdrop-filter: blur(5px);
    border: 1px solid rgba(255,255,255,0.1);
}
.stBarChart, .stLineChart {
    background: rgba(255,255,255,0.05);
    border-radius: 12px;
    padding: 15px;
    backdrop-filter: blur(5px);
    border: 1px solid rgba(255,255,255,0.1);
}

/* 容器背景 */
.st-emotion-cache-1r6slb0 {
    background: rgba(255,255,255,0.08);
    border: 1px solid rgba(255,255,255,0.15);
    border-radius: 12px;
    padding: 16px;
    backdrop-filter: blur(10px);
}

/* 标题样式 */
h1, h2, h3, h4, h5, h6 {
    color: #ffffff !important;
}

/* 分割线 */
hr {
    border-color: rgba(255,255,255, 0.15) !important;
}

/* 页脚样式 */
.st-emotion-cache-1avcm0n {
    color: #a0a0a0 !important;
}
</style>
"""
st.markdown(custom_css, unsafe_allow_html=True)

# 数据库配置
DB_PATH = '/home/openclaw/.openclaw/workspace/business_flow.db'

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    return conn

def load_data():
    """加载数据"""
    conn = get_db_connection()
    
    # 对账明细数据 (2026 年 4 月)
    df_duizhang = pd.read_sql_query("""
        SELECT 
            date(yewu_wancheng_shijian) as date,
            institution as hospital,
            ye_wu_lei_mu as category,
            amount,
            order_amount
        FROM daily_flow_2026_apr
        WHERE yewu_wancheng_shijian != '' AND yewu_wancheng_shijian != 'NaT'
    """, conn)
    
    # 订单数据
    df_orders = pd.read_sql_query("""
        SELECT 
            date(order_time) as date,
            order_type,
            order_status,
            order_amount,
            province
        FROM ningxia_orders_2026_apr
        WHERE order_time != '' AND order_time != 'NaT'
    """, conn)
    
    conn.close()
    return df_duizhang, df_orders

# 加载数据
with st.spinner('正在加载数据...'):
    df_duizhang, df_orders = load_data()

# 标题
st.title("🏥 医院数据 Dashboard")
st.markdown("---")

# 创建标签页
tab1, tab2, tab3, tab4, tab5 = st.tabs(["📊 总览", "📈 趋势分析", "🏆 医院排行", "🗺️ 区域分布", "📦 订单分析"])

# ============ 标签页 1: 总览 ============
with tab1:
    st.header("📊 数据总览")
    
    # 计算汇总指标
    total_amount = df_duizhang['amount'].sum() if 'amount' in df_duizhang.columns else 0
    total_orders = len(df_duizhang)
    total_order_amount = df_duizhang['order_amount'].sum() if 'order_amount' in df_duizhang.columns else 0
    
    # 最新数据日期
    if 'date' in df_duizhang.columns:
        latest_date = df_duizhang['date'].max()
    else:
        latest_date = "N/A"
    
    # KPI 指标
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("总流水 (万元)", f"{total_amount/10000:.2f}" if total_amount > 10000 else f"{total_amount:.2f}")
    
    with col2:
        st.metric("订单总数", f"{total_orders:,}")
    
    with col3:
        st.metric("订单总金额", f"{total_order_amount/10000:.2f}万" if total_order_amount > 10000 else f"{total_order_amount:.2f}")
    
    with col4:
        st.metric("最新数据日期", str(latest_date) if latest_date else "N/A")
    
    st.markdown("---")
    
    # 医院汇总
    st.subheader("🏥 各医院数据汇总")
    if 'hospital' in df_duizhang.columns:
        hospital_summary = df_duizhang.groupby('hospital').agg({
            'amount': 'sum',
            'order_amount': 'sum' if 'order_amount' in df_duizhang.columns else None
        }).reset_index()
        hospital_summary.columns = ['医院', '流水金额', '订单金额']
        hospital_summary['流水金额'] = hospital_summary['流水金额'].apply(lambda x: f"¥{x:,.2f}")
        st.dataframe(hospital_summary, use_container_width=True, hide_index=True)

# ============ 标签页 2: 趋势分析 ============
with tab2:
    st.header("📈 趋势分析")
    
    if 'date' in df_duizhang.columns:
        # 按日期汇总
        daily_summary = df_duizhang.groupby('date').agg({
            'amount': 'sum',
            'order_amount': 'sum' if 'order_amount' in df_duizhang.columns else 0
        }).reset_index()
        
        st.subheader("每日流水趋势")
        st.line_chart(daily_summary.set_index('date')['amount'])
        
        st.subheader("每日数据明细")
        st.dataframe(daily_summary, use_container_width=True, hide_index=True)

# ============ 标签页 3: 医院排行 ============
with tab3:
    st.header("🏆 医院排行")
    
    if 'hospital' in df_duizhang.columns:
        hospital_rank = df_duizhang.groupby('hospital')['amount'].sum().reset_index()
        hospital_rank.columns = ['医院', '总流水']
        hospital_rank = hospital_rank.sort_values('总流水', ascending=False)
        
        st.subheader("按流水金额排行")
        st.bar_chart(hospital_rank.set_index('医院'))
        
        st.subheader("排行明细")
        st.dataframe(hospital_rank, use_container_width=True, hide_index=True)

# ============ 标签页 4: 区域分布 ============
with tab4:
    st.header("🗺️ 区域分布")
    
    if 'province' in df_orders.columns:
        province_summary = df_orders.groupby('province').agg({
            'order_amount': 'sum',
            'order_type': 'count'
        }).reset_index()
        province_summary.columns = ['省份', '订单金额', '订单数']
        province_summary = province_summary.sort_values('订单数', ascending=False)
        
        st.subheader("各省份订单分布")
        st.bar_chart(province_summary.set_index('省份')['订单数'])
        
        st.subheader("区域数据明细")
        st.dataframe(province_summary, use_container_width=True, hide_index=True)

# ============ 标签页 5: 订单分析 ============
with tab5:
    st.header("📦 订单分析")
    
    if 'order_type' in df_orders.columns:
        # 订单类型分布
        order_type_summary = df_orders.groupby('order_type').size().reset_index(name='订单数')
        order_type_summary = order_type_summary.sort_values('订单数', ascending=False)
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("订单类型分布")
            st.bar_chart(order_type_summary.set_index('订单类型'))
        
        with col2:
            st.subheader("订单状态分布")
            if 'order_status' in df_orders.columns:
                order_status_summary = df_orders.groupby('order_status').size().reset_index(name='订单数')
                st.bar_chart(order_status_summary.set_index('订单状态'))
        
        st.subheader("订单数据明细")
        st.dataframe(df_orders, use_container_width=True, hide_index=True)

# 页脚
st.markdown("---")
st.caption(f"数据更新时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | 数据源：business_flow.db")
