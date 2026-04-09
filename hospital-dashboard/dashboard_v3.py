#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
医院数据 Dashboard v3 - Streamlit 版本
6 个标签页：总览、趋势、异常监控、排行、区域分布、月环比分析
"""

import streamlit as st
import pandas as pd
import sqlite3
import numpy as np
from datetime import datetime, timedelta

# 页面配置
st.set_page_config(page_title="医院数据 Dashboard", page_icon="🏥", layout="wide")

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
            order_amount,
            yewu_leixing
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
            province,
            prescribing_org as institution
        FROM ningxia_orders_2026_apr
        WHERE order_time != '' AND order_time != 'NaT'
    """, conn)
    
    # 对账汇总数据（用于月环比）
    df_summary = pd.read_sql_query("""
        SELECT date, daily_total_flow, daily_flow_ratio
        FROM duizhang_summary_2026
        WHERE date >= '2026-03-01'
        ORDER BY date
    """, conn)
    
    conn.close()
    return df_duizhang, df_orders, df_summary

def detect_anomalies(df, hospital_col, date_col, amount_col, order_col):
    """异常检测 - 4 种算法"""
    anomalies = []
    
    for hospital in df[hospital_col].unique():
        hsp_data = df[df[hospital_col] == hospital].copy()
        hsp_data = hsp_data.sort_values(date_col)
        
        if len(hsp_data) < 3:
            continue
        
        # 排除最新一天计算统计指标
        if len(hsp_data) > 1:
            latest_date = hsp_data[date_col].max()
            historical = hsp_data[hsp_data[date_col] != latest_date]
        else:
            historical = hsp_data
        
        if len(historical) < 2:
            continue
        
        for idx, row in hsp_data.iterrows():
            current_date = row[date_col]
            current_orders = row[order_col] if order_col in row else 0
            current_amount = row[amount_col] if amount_col in row else 0
            
            # 计算历史统计
            hist_mean = historical[order_col].mean() if order_col in historical.columns else 0
            hist_std = historical[order_col].std() if order_col in historical.columns else 0
            hist_median = historical[order_col].median() if order_col in historical.columns else 0
            
            # 1. Z-Score 检测
            z_score = abs((current_orders - hist_mean) / hist_std) if hist_std > 0 else 0
            if z_score > 2.0:
                anomalies.append({
                    '医院': hospital,
                    '日期': current_date,
                    '订单数': current_orders,
                    '异常类型': 'Z-Score 异常',
                    '详情': f'Z={z_score:.2f} (>2.0)'
                })
            
            # 2. IQR 检测
            Q1 = historical[order_col].quantile(0.25) if order_col in historical.columns else 0
            Q3 = historical[order_col].quantile(0.75) if order_col in historical.columns else 0
            IQR = Q3 - Q1
            upper_bound = Q3 + 1.5 * IQR
            if current_orders > upper_bound and IQR > 0:
                anomalies.append({
                    '医院': hospital,
                    '日期': current_date,
                    '订单数': current_orders,
                    '异常类型': 'IQR 极端值',
                    '详情': f'>{upper_bound:.0f}'
                })
            
            # 3. 动态阈值检测
            dynamic_threshold = min(hist_median * 1.3, hist_mean + 1.5 * hist_std) if hist_std > 0 else hist_median * 1.3
            if current_orders > dynamic_threshold and dynamic_threshold > 0:
                anomalies.append({
                    '医院': hospital,
                    '日期': current_date,
                    '订单数': current_orders,
                    '异常类型': '动态阈值',
                    '详情': f'>{dynamic_threshold:.0f}'
                })
            
            # 4. 环比增长检测（需要前一日数据）
            prev_date = hsp_data[hsp_data[date_col] < current_date].sort_values(date_col)
            if len(prev_date) > 0:
                prev_row = prev_date.iloc[-1]
                prev_orders = prev_row[order_col] if order_col in prev_row else 0
                if prev_orders >= 10 and current_orders > prev_orders * 3:  # 增长>200%
                    growth_rate = ((current_orders - prev_orders) / prev_orders) * 100
                    anomalies.append({
                        '医院': hospital,
                        '日期': current_date,
                        '订单数': current_orders,
                        '异常类型': '环比暴增 ⭐',
                        '详情': f'+{growth_rate:.0f}% (前日={prev_orders})'
                    })
    
    return pd.DataFrame(anomalies)

# 加载数据
with st.spinner('正在加载数据...'):
    df_duizhang, df_orders, df_summary = load_data()

# 标题
st.title("🏥 医院数据 Dashboard")
st.caption(f"数据更新时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
st.markdown("---")

# 创建 6 个标签页
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "📊 总览", 
    "📈 趋势", 
    "⚠️ 异常监控", 
    "🏆 排行", 
    "🗺️ 区域分布",
    "📉 月环比"
])

# ============ 标签页 1: 总览 ============
with tab1:
    st.header("📊 数据总览")
    
    # 计算汇总指标
    total_amount = df_duizhang['amount'].sum() if 'amount' in df_duizhang.columns else 0
    total_orders = len(df_duizhang)
    
    # 最新数据日期
    latest_date = df_duizhang['date'].max() if 'date' in df_duizhang.columns else "N/A"
    
    # KPI 指标
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("总流水", f"¥{total_amount/10000:.2f}万")
    
    with col2:
        st.metric("订单总数", f"{total_orders:,}")
    
    with col3:
        st.metric("最新数据日期", str(latest_date))
    
    with col4:
        # 计算日均
        if 'date' in df_duizhang.columns and latest_date:
            days = df_duizhang['date'].nunique()
            daily_avg = total_amount / days if days > 0 else 0
            st.metric("日均流水", f"¥{daily_avg/10000:.2f}万")
    
    st.markdown("---")
    
    # 医院汇总
    st.subheader("🏥 各医院数据汇总")
    if 'hospital' in df_duizhang.columns:
        hospital_summary = df_duizhang.groupby('hospital').agg({
            'amount': 'sum',
            'order_amount': 'sum' if 'order_amount' in df_duizhang.columns else 0
        }).reset_index()
        hospital_summary.columns = ['医院', '流水金额', '订单金额']
        hospital_summary['流水金额'] = hospital_summary['流水金额'].apply(lambda x: f"¥{x/10000:.2f}万")
        st.dataframe(hospital_summary, use_container_width=True, hide_index=True)

# ============ 标签页 2: 趋势 ============
with tab2:
    st.header("📈 趋势分析")
    
    if 'date' in df_duizhang.columns:
        # 按日期汇总
        daily_summary = df_duizhang.groupby('date').agg({
            'amount': 'sum',
            'order_amount': 'sum' if 'order_amount' in df_duizhang.columns else 0
        }).reset_index()
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("每日流水趋势")
            st.line_chart(daily_summary.set_index('date')['amount'])
        
        with col2:
            st.subheader("每日订单趋势")
            daily_counts = df_duizhang.groupby('date').size().reset_index(name='订单数')
            st.line_chart(daily_counts.set_index('date')['订单数'])
        
        st.subheader("每日数据明细")
        st.dataframe(daily_summary, use_container_width=True, hide_index=True)

# ============ 标签页 3: 异常监控 ============
with tab3:
    st.header("⚠️ 异常监控")
    st.caption("4 种算法检测异常波动：Z-Score、IQR、动态阈值、环比暴增")
    
    # 按医院和日期汇总
    if 'hospital' in df_duizhang.columns and 'date' in df_duizhang.columns:
        daily_hospital = df_duizhang.groupby(['hospital', 'date']).agg({
            'amount': 'sum',
        }).reset_index()
        daily_hospital['order_count'] = daily_hospital.apply(lambda x: len(df_duizhang[(df_duizhang['hospital']==x['hospital']) & (df_duizhang['date']==x['date'])]), axis=1)
        
        # 执行异常检测
        anomalies = detect_anomalies(
            daily_hospital, 
            'hospital', 
            'date', 
            'amount', 
            'order_count'
        )
        
        if len(anomalies) > 0:
            st.warning(f"发现 {len(anomalies)} 条异常记录")
            st.dataframe(anomalies, use_container_width=True, hide_index=True)
        else:
            st.success("✅ 未发现异常波动")
        
        st.markdown("---")
        st.subheader("📋 检测算法说明")
        st.markdown("""
        1. **Z-Score 检测**: 统计学异常，|Z| > 2.0 判定为异常
        2. **IQR 检测**: 极端值检测，> Q3 + 1.5×IQR 判定为异常
        3. **动态阈值**: 业务规则，> min(中位数×1.3, 均值 +1.5×标准差)
        4. **环比暴增 ⭐**: 前一日≥10 单 且 增长>200%
        """)

# ============ 标签页 4: 排行 ============
with tab4:
    st.header("🏆 医院排行")
    
    if 'hospital' in df_duizhang.columns:
        # 总排行
        hospital_rank = df_duizhang.groupby('hospital')['amount'].sum().reset_index()
        hospital_rank.columns = ['医院', '总流水']
        hospital_rank = hospital_rank.sort_values('总流水', ascending=False)
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("按流水金额排行")
            st.bar_chart(hospital_rank.set_index('医院'))
        
        with col2:
            st.subheader("排行明细")
            st.dataframe(hospital_rank, use_container_width=True, hide_index=True)

# ============ 标签页 5: 区域分布 ============
with tab5:
    st.header("🗺️ 区域分布")
    
    if 'province' in df_orders.columns:
        province_summary = df_orders.groupby('province').agg({
            'order_amount': 'sum',
        }).reset_index()
        province_summary['订单数'] = province_summary.apply(lambda x: len(df_orders[df_orders['province']==x['province']]), axis=1)
        province_summary.columns = ['省份', '订单金额', '订单数']
        province_summary = province_summary.sort_values('订单数', ascending=False)
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("各省份订单分布")
            st.bar_chart(province_summary.set_index('省份')['订单数'])
        
        with col2:
            st.subheader("区域数据明细")
            st.dataframe(province_summary, use_container_width=True, hide_index=True)

# ============ 标签页 6: 月环比分析 ============
with tab6:
    st.header("📉 月环比分析")
    
    if len(df_summary) > 0:
        # 获取最新数据日期
        latest_date = df_summary['date'].max()
        latest_data = df_summary[df_summary['date'] == latest_date].iloc[0]
        
        # 计算逻辑说明
        st.info(f"""
        **最新数据日期**: {latest_date}
        
        **计算规则**: 动态计算到最新数据日期
        - 本月：2026 年 4 月 1 日 - {latest_date}
        - 上月同期：2026 年 3 月 1 日 - 对应日期
        - 去年同期：2025 年对应期间
        """)
        
        # 显示数据
        st.subheader("月度数据对比")
        st.dataframe(df_summary, use_container_width=True, hide_index=True)
        
        # 趋势图
        st.subheader("流水趋势与环比")
        st.line_chart(df_summary.set_index('date')['daily_total_flow'])
    else:
        st.warning("暂无对账汇总数据，请先运行 import_duizhang_summary.py 导入")

# 页脚
st.markdown("---")
st.caption("Dashboard v3 | 数据源：business_flow.db")
