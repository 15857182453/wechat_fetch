#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
运营数据仪表板 - Streamlit 应用（动态环比版）
环比逻辑：自动计算到最新数据日期
"""

import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
from datetime import datetime, timedelta
from typing import Optional, Tuple, Dict, Any

# 设置页面配置和自定义CSS
st.set_page_config(
    page_title="运营数据仪表板", 
    page_icon="📊", 
    layout="wide", 
    initial_sidebar_state="expanded"
)

# 自定义CSS样式
st.markdown("""
<style>
/* 渐变背景 */
.stApp {
    background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
}
/* 卡片容器 */
[data-testid="stMetricContainer"] {
    background: linear-gradient(135deg, rgba(255,255,255,0.9) 0%, rgba(255,255,255,0.8) 100%);
    border-radius: 16px;
    padding: 20px;
    box-shadow: 0 8px 32px rgba(31, 38, 135, 0.1);
    backdrop-filter: blur(2px);
    border: 1px solid rgba(255, 255, 255, 0.18);
}

/* 标题和标签 */
h1, h2, h3 {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
}

/* 标签页样式 */
.stTabs > div[role="tablist"] {
    background: linear-gradient(135deg, rgba(255,255,255,0.8) 0%, rgba(255,255,255,0.6) 100%);
    border-radius: 12px;
    padding: 10px;
    margin-bottom: 20px;
}
</style>
""", unsafe_allow_html=True)

st.title("📊 运营数据仪表板")
st.markdown("### 🔥 实时监控医院业务表现")

DB_PATH = "/home/openclaw/.openclaw/workspace/business_flow.db"

# ========== 数据加载函数 ==========
@st.cache_data(ttl=30)
def load_hospital_data():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    table_names = ['daily_flow_2025', 'daily_flow_2026_jan_feb', 'daily_flow_2026_mar', 'daily_flow_2026_apr']
    queries = []
    for table in table_names:
        try:
            q = f"""SELECT institution, COUNT(*) as cnt, SUM(amount) as amt, 
                    ROUND(SUM(amount)*1.0/COUNT(*), 2) as avg_amt,
                    SUBSTR(yewu_wancheng_shijian, 1, 10) as dt
                    FROM {table}
                    WHERE ye_wu_lei_mu LIKE '%处方服务%' AND pay_status = '收费'
                    GROUP BY institution, SUBSTR(yewu_wancheng_shijian, 1, 10)"""
            queries.append(q)
        except: pass
    if not queries:
        conn.close()
        return pd.DataFrame(columns=['医院', '订单数', '金额', '客单价', '日期'])
    full_query = " UNION ALL ".join(queries) + " ORDER BY dt DESC, amt DESC"
    df = pd.read_sql_query(full_query, conn)
    df.columns = ['医院', '订单数', '金额', '客单价', '日期']
    conn.close()
    return df

# ========== 环比计算函数 ==========
def calculate_mom_growth():
    """计算月环比：动态计算到最新数据日期"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 获取 2026 年最新数据日期
    cursor.execute("""
        SELECT MAX(date) FROM (
            SELECT MAX(date) as date FROM duizhang_summary_2026
        )
    """)
    latest_date = cursor.fetchone()[0]
    
    if not latest_date:
        conn.close()
        return None, None, None
    
    # 解析最新日期
    latest_dt = datetime.strptime(latest_date, '%Y-%m-%d')
    current_month = latest_dt.month
    current_day = latest_dt.day
    
    # 计算本月 1 日 到 最新日期的数据
    current_start = f'2026-{current_month:02d}-01'
    current_end = latest_date
    
    cursor.execute("""
        SELECT COUNT(*), SUM(daily_total_flow), AVG(daily_total_flow)
        FROM duizhang_summary_2026
        WHERE date >= ? AND date <= ?
    """, (current_start, current_end))
    current_data = cursor.fetchone()
    
    # 计算上月同期（上月 1 日 到 上月相同日期）
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
    else:
        mom_growth = 0.0
    
    result = {
        'latest_date': latest_date,
        'current_period': f'{current_start} ~ {current_end}',
        'current_days': current_days,
        'current_total': current_total,
        'current_avg': current_avg,
        'prev_period': f'{prev_start} ~ {prev_end}',
        'prev_days': prev_days,
        'prev_total': prev_total,
        'prev_avg': prev_avg,
        'mom_growth': mom_growth
    }
    
    return result, current_data, prev_data

# ========== 数据处理 ==========
try:
    df_hospital = load_hospital_data()
except Exception as e:
    st.error(f"医院数据加载失败：{e}")
    df_hospital = pd.DataFrame()

# ========== 侧边栏 ==========
hospital_list = sorted(df_hospital['医院'].unique()) if not df_hospital.empty else []
selected_hospitals = st.sidebar.multiselect("🏥 选择医院", hospital_list, default=hospital_list[:10] if hospital_list else [])
max_date = df_hospital['日期'].max() if not df_hospital.empty else datetime.today().strftime('%Y-%m-%d')
selected_date_str = st.sidebar.date_input("📅 选择日期", value=datetime.strptime(max_date, '%Y-%m-%d')).strftime('%Y-%m-%d')

if selected_hospitals:
    df_filtered = df_hospital[df_hospital['医院'].isin(selected_hospitals)]
else:
    df_filtered = df_hospital

df_date = df_filtered[df_filtered['日期'] == selected_date_str] if not df_filtered.empty and max_date else pd.DataFrame()

# ========== KPI 卡片样式函数 ==========
def display_kpi_cards():
    """展示KPI指标卡片"""
    total_orders = int(df_date['订单数'].sum()) if not df_date.empty else 0
    total_amount = float(df_date['金额'].sum()) if not df_date.empty else 0.0
    avg_ticket = float(df_date['客单价'].mean()) if not df_date.empty else 0.0
    hospital_count = len(df_date) if not df_date.empty else 0

    kpi_configs = [
        {"label": "总订单数", "value": f"{total_orders:,}", "icon": "🛍️"},
        {"label": "总金额", "value": f"¥{total_amount:,.0f}", "icon": "💰"},
        {"label": "平均客单价", "value": f"¥{avg_ticket:,.2f}", "icon": "📊"},
        {"label": "医院数", "value": f"{hospital_count}", "icon": "🏥"}
    ]

    cols = st.columns(len(kpi_configs))
    for col, config in zip(cols, kpi_configs):
        with col:
            st.markdown(f"""
            <div style="
                background: linear-gradient(135deg, rgba(255,255,255,0.95) 0%, rgba(255,255,255,0.85) 100%);
                border-radius: 16px;
                padding: 16px;
                box-shadow: 0 8px 32px rgba(31, 38, 135, 0.1);
                backdrop-filter: blur(4px);
                border: 1px solid rgba(255, 255, 255, 0.2);
                text-align: center;
                height: 120px;
                display: flex;
                flex-direction: column;
                justify-content: center;
                align-items: center;
            ">
                <div style="font-size: 24px; margin-bottom: 8px;">{config['icon']}</div>
                <div style="font-size: 14px; color: #666; margin-bottom: 4px; font-weight: 600;">{config['label']}</div>
                <div style="font-size: 24px; font-weight: bold; color: #333;">
                    {config['value']}
                </div>
            </div>
            """, unsafe_allow_html=True)

# ========== 标签页 ==========
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "📊 总览", "📈 趋势", "⚠️ 异常监控", 
    "🏆 排行榜", "🗺️ 区域分布", "📉 环比分析"
])

with tab1:
    st.header("📈 KPI 概览")
    
    if not df_hospital.empty:
        st.markdown(f"### 📍 {selected_date_str} 数据概览")
        st.write("")
        display_kpi_cards()
        
        st.divider()
        st.subheader("🏥 当前筛选医院详情")
        if not df_date.empty:
            styled_df = df_date[['医院', '订单数', '金额', '客单价']].sort_values('金额', ascending=False)
            st.dataframe(
                styled_df.style.format({
                    '订单数': lambda x: f'{x:,}',
                    '金额': lambda x: f'¥{x:,.2f}',
                    '客单价': lambda x: f'¥{x:,.2f}'
                }),
                use_container_width=True,
                height=600,
                hide_index=True
            )
        else:
            st.warning("当前筛选条件下暂无数据")
    else:
        st.warning("暂无医院数据")

with tab2:
    st.header("📈 订单趨勢分析")
    
    if not df_hospital.empty:
        selected_dt = pd.to_datetime(selected_date_str)
        date_range = pd.date_range(end=selected_dt, periods=7, freq='D')
        date_strings = [d.strftime('%Y-%m-%d') for d in date_range]
        df_7days = df_filtered[df_filtered['日期'].isin(date_strings)].copy()
        
        if not df_7days.empty:
            df_7days_agg = df_7days.groupby(['日期', '医院']).agg({
                '订单数': 'sum',
                '金额': 'sum'
            }).reset_index()
            
            date_range_df = pd.DataFrame({'日期': date_strings})
            hospitals_in_filter = df_7days['医院'].unique()
            
            trend_data = []
            for hospital in hospitals_in_filter:
                for date in date_strings:
                    day_data = df_7days_agg[(df_7days_agg['医院'] == hospital) & (df_7days_agg['日期'] == date)]
                    if not day_data.empty:
                        trend_data.append({
                            '日期': date,
                            '医院': hospital,
                            '订单数': day_data.iloc[0]['订单数'],
                            '金额': day_data.iloc[0]['金额']
                        })
                    else:
                        trend_data.append({
                            '日期': date,
                            '医院': hospital,
                            '订单数': 0,
                            '金额': 0
                        })
            df_trend = pd.DataFrame(trend_data)
            
            # 图表选项卡
            trend_tab1, trend_tab2, trend_tab3 = st.tabs(["订单数趋势", "金额趋势", "组合视图"])
            
            with trend_tab1:
                fig_orders = px.line(
                    df_trend, 
                    x='日期', 
                    y='订单数', 
                    color='医院', 
                    title='各医院订单数趋势（近7天）',
                    markers=True,
                    line_shape='spline'
                )
                fig_orders.update_layout(
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    hovermode='x unified'
                )
                st.plotly_chart(fig_orders, use_container_width=True)
            
            with trend_tab2:
                fig_amount = px.line(
                    df_trend, 
                    x='日期', 
                    y='金额', 
                    color='医院', 
                    title='各医院金额趋势（近7天）',
                    markers=True,
                    line_shape='spline'
                )
                fig_amount.update_layout(
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    hovermode='x unified'
                )
                st.plotly_chart(fig_amount, use_container_width=True)
            
            with trend_tab3:
                fig_combo = go.Figure()
                for hospital in df_trend['医院'].unique():
                    hospital_data = df_trend[df_trend['医院'] == hospital]
                    fig_combo.add_trace(go.Scatter(
                        x=hospital_data['日期'], 
                        y=hospital_data['订单数'],
                        mode='lines+markers',
                        name=f'{hospital} (订单)',
                        yaxis='y1',
                        line=dict(shape='spline')
                    ))
                    fig_combo.add_trace(go.Scatter(
                        x=hospital_data['日期'], 
                        y=hospital_data['金额']/1000,
                        mode='lines+markers',
                        name=f'{hospital} (金额/1000)',
                        yaxis='y2',
                        line=dict(shape='spline', dash='dash')
                    ))
                fig_combo.update_layout(
                    title='订单数与金额对比趋势',
                    xaxis=dict(title='日期'),
                    yaxis=dict(title='订单数', side='left'),
                    yaxis2=dict(title='金额(分)/1000', side='right', overlaying='y'),
                    hovermode='x unified'
                )
                st.plotly_chart(fig_combo, use_container_width=True)
        else:
            st.warning("当前筛选条件下暂无7天趋势数据")
    else:
        st.warning("暂无数据")

with tab3:
    st.header("⚠️ 异常数据智能监控")
    st.markdown("### 🔍 采用 **Z-Score + IQR + 动态阈值** 三重算法检测")
    
    if not df_hospital.empty:
        all_hospitals = df_hospital['医院'].unique()
        anomalies = []
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        for idx, hospital in enumerate(all_hospitals):
            progress_bar.progress((idx + 1) / len(all_hospitals))
            status_text.text(f"正在分析医院: {hospital}")
            
            if '医院' not in df_hospital.columns:
                continue
                
            hosp_data = df_hospital[df_hospital['医院'] == hospital].sort_values('日期', ascending=False).head(7)
            if len(hosp_data) < 2:
                continue
            
            daily = hosp_data.groupby('日期').agg({'订单数': 'sum', '金额': 'sum'}).reset_index()
            if len(daily) < 2:
                continue
            
            today = daily[daily['日期'] == selected_date_str]
            if today.empty:
                continue
            
            today_orders = int(today.iloc[0]['订单数'])
            today_amount = float(today.iloc[0]['金额'])
            
            other_days = daily[daily['日期'] != selected_date_str]['订单数']
            
            if len(other_days) < 2:
                continue
            
            mean_orders = other_days.mean()
            median_orders = other_days.median()
            std_orders = other_days.std()
            
            q1_orders = other_days.quantile(0.25)
            q3_orders = other_days.quantile(0.75)
            iqr_orders = q3_orders - q1_orders
            upper_bound = q3_orders + 2.5 * iqr_orders
            
            dynamic_threshold = max(
                median_orders * 2.0,
                mean_orders + 3 * std_orders
            )
            dynamic_threshold = max(dynamic_threshold, 50)
            
            anomaly_flags = []
            
            if std_orders and std_orders > 0:
                zscore = (today_orders - mean_orders) / std_orders
                if abs(zscore) > 3.0:
                    anomaly_flags.append(f'Z-Score={zscore:.2f} ⚠️')
            
            if today_orders > upper_bound:
                anomaly_flags.append(f'IQR>{upper_bound:.0f} ⚠️')
            
            min_threshold = 20
            if today_orders >= min_threshold and today_orders > dynamic_threshold:
                anomaly_flags.append(f'动态>{dynamic_threshold:.0f} ⚠️')
            
            if len(other_days) > 0:
                prev_day_data = daily[daily['日期'] < selected_date_str].sort_values('日期', ascending=False)
                if not prev_day_data.empty:
                    prev_day = prev_day_data.iloc[0]['订单数']
                    if prev_day >= 10 and prev_day > 0:
                        growth_rate = (today_orders - prev_day) / prev_day * 100
                        if growth_rate > 200:
                            anomaly_flags.append(f'环比+{growth_rate:.0f}% ⚠️')
            
            if anomaly_flags:
                anomalies.append({
                    '医院': hospital,
                    '日期': selected_date_str,
                    '订单数': today_orders,
                    '金额': today_amount,
                    '异常类型': anomaly_flags,
                    '均值': float(mean_orders),
                    '标准差': float(std_orders),
                    'IQR上限': float(upper_bound),
                    '动态阈值': float(dynamic_threshold)
                })
        
        progress_bar.empty()
        status_text.empty()
        
        if anomalies:
            st.error(f"❌ 发现 **{len(anomalies)}** 个医院存在异常波动")
            
            for i, a in enumerate(anomalies):
                anomaly_types = f" | ".join(a['异常类型'])
                
                card_key = f"expander_{i}_{a['医院'][:5]}_{a['日期']}"
                
                with st.expander(
                    f"🚨 {a['医院']} - {a['订单数']:,}单 / ¥{a['金额']:,.0f} / {anomaly_types}",
                    expanded=False
                ):
                    st.markdown(
                        f"<div style='background: #fff3cd; padding: 10px; border-radius: 8px; "
                        f"border-left: 4px solid #ffc107; margin-bottom: 10px; "
                        f"box-shadow: 0 2px 4px rgba(0,0,0,0.1);'>",
                        unsafe_allow_html=True
                    )
                    st.write(f"### 🏥 医院: {a['医院']}")
                    st.write(f"#### 📅 日期: {a['日期']}")
                    st.write(f"#### 📊 订单数: {a['订单数']:,} 单")
                    st.write(f"#### 💰 金额: ¥{a['金额']:,.2f} 元") 
                    st.write(f"#### 📈 近7日均值: {a['均值']:.1f} 单")
                    st.write(f"#### 📉 标准差: {a['标准差']:.2f}")
                    st.markdown("</div>", unsafe_allow_html=True)
                    
                    st.markdown("### 🚨 异常检测结果")
                    for flag in a['异常类型']:
                        if 'Z-Score' in flag:
                            st.warning(f"🔴 **Z-Score算法**: {flag}")
                        elif 'IQR' in flag:
                            st.warning(f"🟠 **IQR算法**: {flag}")
                        elif '动态' in flag:
                            st.warning(f"🟡 **动态阈值算法**: {flag}")
                        elif '环比' in flag:
                            st.warning(f"🔵 **环比增长算法**: {flag}")
                    
                    st.markdown("### 📊 统计指标详情")
                    metrics_cols = st.columns(2)
                    with metrics_cols[0]:
                        st.metric("均值", f"{a['均值']:.1f} 单", delta=None)
                        st.metric("IQR上限", f"{a['IQR上限']:.0f} 单", delta=None)
                    with metrics_cols[1]:
                        st.metric("标准差", f"{a['标准差']:.2f}", delta=None)
                        st.metric("动态阈值", f"{a['动态阈值']:.0f} 单", delta=None)
                    
                    hosp_full_7days = df_hospital[df_hospital['医院'] == a['医院']].sort_values('日期', ascending=False).head(7)
                    if not hosp_full_7days.empty:
                        fig = go.Figure(data=[
                            go.Bar(name='订单数', 
                                   x=hosp_full_7days['日期'], 
                                   y=hosp_full_7days['订单数'],
                                   marker_color=px.colors.qualitative.Set3[i % len(px.colors.qualitative.Set3)])
                        ])
                        fig.update_layout(
                            title=f'{a["医院"]} - 近7天订单趋势分析',
                            xaxis_title='日期',
                            yaxis_title='订单数量',
                            height=400,
                            showlegend=False
                        )
                        st.plotly_chart(fig, use_container_width=True)
                    else:
                        st.warning(f"⚠️ {a['医院']} 近7天数据不足")
        else:
            st.success("✅ 所有医院数据正常，未发现异常波动")
            st.balloons()
    else:
        st.warning("暂无数据")

with tab4:
    st.header("🏆 医院业务排行榜")
    st.markdown("### 📊 按金额排序的Top 10医院")
    
    if not df_hospital.empty and not df_date.empty:
        col1, col2 = st.columns([3, 2])
        
        with col1:
            df_rank = df_date.sort_values('金额', ascending=False).head(10)
            if not df_rank.empty:
                fig = go.Figure(data=[
                    go.Bar(
                        x=df_rank['金额'],
                        y=df_rank['医院'],
                        orientation='h',
                        text=[f'¥{amt:,.0f}\n{orders}单' for amt, orders in zip(df_rank['金额'], df_rank['订单数'])],
                        textposition='auto',
                        marker_color=px.colors.sequential.Plasma_r
                    )
                ])
                fig.update_layout(
                    title='医院收入排名 Top 10',
                    xaxis_title='金额',
                    yaxis_title='医院名称',
                    height=500,
                    yaxis={'categoryorder':'total ascending'}  # 从小到大排列
                )
                st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            st.subheader("🏆 排名详情")
            ranked_df = df_date.sort_values('金额', ascending=False).head(10)[['医院', '订单数', '金额', '客单价']]
            for idx, (hospital, row) in enumerate(ranked_df.iterrows(), 1):
                medal = {1: '🥇', 2: '🥈', 3: '🥉'}.get(idx, f'{idx}')
                expander = st.expander(f"{medal} {hospital[:20]}...")
                with expander:
                    st.write(f"**订单数**: {row['订单数']:,}")
                    st.write(f"**金额**: ¥{row['金额']:,.0f}") 
                    st.write(f"**客单价**: ¥{row['客单价']:,.2f}")
    else:
        st.warning("暂无数据")

with tab5:
    st.header("🌍 医院区域分布分析") 
    
    try:
        conn = sqlite3.connect(DB_PATH)
        query = """
        SELECT province, COUNT(DISTINCT institution) as cnt 
        FROM (
            SELECT DISTINCT institution, province 
            FROM daily_flow_2025 WHERE province IS NOT NULL 
            UNION 
            SELECT DISTINCT institution, province 
            FROM daily_flow_2026_jan_feb WHERE province IS NOT NULL 
            UNION 
            SELECT DISTINCT institution, province 
            FROM daily_flow_2026_mar WHERE province IS NOT NULL 
            UNION 
            SELECT DISTINCT institution, province 
            FROM daily_flow_2026_apr WHERE province IS NOT NULL
        ) 
        WHERE province IS NOT NULL 
        GROUP BY province 
        ORDER BY cnt DESC
        """
        df_province = pd.read_sql_query(query, conn)
        conn.close()
        
        if not df_province.empty:
            tab_map1, tab_map2 = st.tabs(["🌐 分布图", "📋 详细列表"])
            
            with tab_map1:
                # 饼图
                fig_pie = px.pie(
                    df_province.head(10),  # 取top 10省份
                    values='cnt', 
                    names='province', 
                    title='医院前10省份分布',
                    color_discrete_sequence=px.colors.sequential.Viridis
                )
                st.plotly_chart(fig_pie, use_container_width=True)
                
                # 条形图
                fig_bar = go.Figure(data=[
                    go.Bar(
                        x=df_province['province'],
                        y=df_province['cnt'],
                        marker_color=px.colors.sequential.Viridis
                    )
                ])
                fig_bar.update_layout(
                    title='各省份医院数量分布',
                    xaxis_title='省份',
                    yaxis_title='医院数量',
                    height=500,
                    xaxis_tickangle=-45
                )
                st.plotly_chart(fig_bar, use_container_width=True)
            
            with tab_map2:
                st.dataframe(
                    df_province,
                    column_config={
                        "province": "省份",
                        "cnt": st.column_config.NumberColumn(" hospitals", format="%d"),
                    },
                    use_container_width=True,
                    hide_index=True
                )
                
                # 地理分布统计摘要
                top_provinces = df_province.head(5)
                st.info(f"""
                📊 **地理分布总结**:
                - 总计覆盖省份: **{len(df_province)}** 个
                - 总计医院数: **{df_province['cnt'].sum()}** 家
                - Top 5 省份:
                  {' '.join([f"{row['province']}({row['cnt']}家)" for _, row in top_provinces.iterrows()])}
                """)
        else:
            st.warning("暂无省份分布数据")
    except Exception as e:
        st.error(f"数据加载失败：{e}")

with tab6:
    st.header("📊 月环比/同比分析（动态计算）")
    st.markdown("""
    ### 💡 智能计算逻辑
    >
    > - **月环比**: 自动计算至最新数据日期（如4月1-7日 vs 3月1-7日）
    > - **同比**: 对比去年同期数据（本年X月 vs 去年12月同期）
    > - **动态更新**: 自动识别最新可用数据并进行计算
    """)

    try:
        result, current_data, prev_data = calculate_mom_growth()
        
        if result:
            st.info(f"📅 **最新数据日期**: `{result['latest_date']}` | {datetime.strptime(result['latest_date'], '%Y-%m-%d').strftime('%A, %B %d, %Y')}")

            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            current_day = datetime.strptime(result['latest_date'], '%Y-%m-%d').day
            
            cursor.execute("""
                SELECT COUNT(*), SUM(daily_total_flow), AVG(daily_total_flow)
                FROM duizhang_summary_2025
                WHERE date >= ? AND date <= ?
            """, ('2025-12-01', f'2025-12-{current_day:02d}'))
            dec25_data = cursor.fetchone()
            conn.close()
            
            dec25_avg = dec25_data[2] if dec25_data and dec25_data[2] else 0.0
            
            yoy_growth = (
                (result['current_avg'] - dec25_avg) / dec25_avg * 100 
                if dec25_avg and dec25_avg > 0 
                else 0.0
            )

            # 展示对比数据
            st.markdown("### 📈 月度表现对比")
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.markdown("###### 🎯 本月数据")
                st.metric(
                    label="统计周期", 
                    value=result['current_period'],
                    help=f"包含{result['current_days']}天数据"
                )
                st.metric(
                    label="总流水", 
                    value=f"¥{result['current_total']:,.2f}万",
                    delta=f"{result.get('current_total', 0) - result.get('prev_total', 0):+,}" if result.get('prev_total') else "",
                    delta_color="normal"
                )
            
            with col2:
                st.markdown("###### 🔄 上月同期")  
                st.metric(
                    label="统计周期", 
                    value=result['prev_period'],
                    help=f"包含{result['prev_days']}天数据"
                )
                st.metric(
                    label="总流水", 
                    value=f"¥{result['prev_total']:,.2f}万"
                )
                
            with col3:
                st.markdown("###### 🌍 同期2025")  
                st.metric(
                    label="参考周期", 
                    value=f"2025-12-01 ~ 2025-12-{current_day:02d}",
                    help="作为同比基准"
                )
                st.metric(
                    label="日均流水", 
                    value=f"¥{dec25_avg:,.2f}万"
                )

            # 环比结果展示
            st.divider()
            col_mom, col_yoy = st.columns(2)
            
            with col_mom:
                st.subheader("📈 月环比增长率")
                mom_growth = result['mom_growth']
                growth_color = "green" if mom_growth > 0 else "red" if mom_growth < 0 else "gray"
                
                st.markdown(f"""
                <div style="
                    background: linear-gradient(135deg, 
                        rgba(255,255,255,0.95) 0%, 
                        rgba(255,255,255,0.85) 100%);
                    border-radius: 16px;
                    padding: 20px;
                    text-align: center;
                    box-shadow: 0 8px 32px rgba(31, 38, 135, 0.1);
                    border: 1px solid rgba(255,255,255,0.2);
                ">
                    <div style="
                        font-size: 32px; 
                        font-weight: bold; 
                        color: {'#2dce89' if mom_growth > 0 else '#fb6340' if mom_growth < 0 else '#adb5bd'}
                    ">
                        {mom_growth:+.2f}%
                    </div>
                    <div style="font-size: 16px; color: #666; margin-top: 8px;">
                        💹 vs 上月同期
                    </div>
                    <div style="margin-top: 12px; font-size: 14px; color: #888;">
                        {('📈 持续增长' if mom_growth > 0 else '📉 需要关注') if abs(mom_growth) > 0.01 else '➡️ 基本稳定'}
                    </div>
                </div>
                """, unsafe_allow_html=True)
            
            with col_yoy:
                st.subheader("📊 同比增长率")
                yoy_text = f"{yoy_growth:+.2f}%" if abs(yoy_growth) <= 1000 else f"{yoy_growth:+E}"
                
                st.markdown(f"""
                <div style="
                    background: linear-gradient(135deg, 
                        rgba(255,255,255,0.95) 0%, 
                        rgba(255,255,255,0.85) 100%);
                    border-radius: 16px;
                    padding: 20px;
                    text-align: center;
                    box-shadow: 0 8px 32px rgba(31, 38, 135, 0.1);
                    border: 1px solid rgba(255,255,255,0.2);
                ">
                    <div style="
                        font-size: 32px; 
                        font-weight: bold; 
                        color: {'#2dce89' if yoy_growth > 0 else '#fb6340' if yoy_growth < 0 else '#adb5bd'}
                    ">
                        {yoy_text}
                    </div>
                    <div style="font-size: 16px; color: #666; margin-top: 8px;">
                        🏆 vs 2025年12月同期
                    </div>
                    <div style="margin-top: 12px; font-size: 14px; color: #888;">
                        {('📈 同比增长' if yoy_growth > 0 else '📉 同比下滑') if abs(yoy_growth) > 0.01 else '➡️ 同比平稳'}
                    </div>
                </div>
                """, unsafe_allow_html=True)

            # 详细计算过程 - 折叠展开
            with st.expander("🧮 显示详细计算过程"):
                st.markdown(f"""
                **【1】月环比计算公式**（vs 上月同期）：
                ```text
                环比增长率 = (本月日均 - 上月日均) ÷ 上月日均 × 100%
                ```
                
                **代入数据**：
                - **本期日均** (`{result['current_period']}`)：¥{result['current_avg']:,.2f}万
                - **上期日均** (`{result['prev_period']}`)：¥{result['prev_avg']:,.2f}万
                
                **运算步骤**：
                ```text
                ({result['current_avg']:.2f} - {result['prev_avg']:.2f}) ÷ {result['prev_avg']:.2f} × 100%
                = {((result['current_avg'] - result['prev_avg']) / result['prev_avg'] * 100 if result['prev_avg'] > 0 else 0):+.4f}%
                ≈ {mom_growth:+.2f}%
                ```

                ---
                **【2】同比计算公式**（vs 2025年12月同期）：
                ```text
                同比增长率 = (本期日均 - 同期日均) ÷ 同期日均 × 100%
                ```
                
                **代入数据**：
                - **本期日均** (`{result['current_period']}`)：¥{result['current_avg']:,.2f}万  
                - **2025同期日均** (`2025-12-01 ~ 2025-12-{current_day:02d}`)：¥{dec25_avg:,.2f}万
                
                **运算步骤**：
                ```text
                ({result['current_avg']:.2f} - {dec25_avg:.2f}) ÷ {dec25_avg:.2f} × 100%
                = {((result['current_avg'] - dec25_avg) / dec25_avg * 100 if dec25_avg > 0 else 0):+.4f}%
                ≈ {yoy_growth:+.2f}%
                ```

                ---
                **📊 结果摘要**：
                | 指标 | 增长率 | 表现 |
                |------|--------|------|
                | 月环比 | `{mom_growth:+.2f}%` | {"📈 成长" if mom_growth > 5 else "➡️ 稳定" if abs(mom_growth) <= 5 else "📉 关注"} |
                | 同比变化 | `{yoy_growth:+.2f}%` | {"📈 发展良好" if yoy_growth > 10 else "➡️ 基本持平" if abs(yoy_growth) <= 10 else "📉 需改进"} |

                """)

            # 本月每日明细图表
            st.subheader(f"📅 `{result['latest_date'][:7].replace('-', '年')}月` 每日流水明细")
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
                df_daily = pd.DataFrame(daily_data, columns=['日期', '流水(万元)'])
                
                tab_detail1, tab_detail2, tab_detail3 = st.tabs(["📈 趋势图", "📊 数据表", "📋 汇总"])
                
                with tab_detail1:
                    fig = go.Figure()
                    fig.add_trace(go.Scatter(
                        x=df_daily['日期'], 
                        y=df_daily['流水(万元)'],
                        mode='lines+markers',
                        name='日流水',
                        line=dict(color='#667eea', width=3, shape='spline'),
                        marker=dict(size=8),
                        fill='tonexty',
                        fillcolor='rgba(102, 126, 234, 0.1)'
                    ))
                    fig.update_layout(
                        title=f'2026年{current_month}月每日流水趋势',
                        xaxis_title='日期',
                        yaxis_title='流水（万元）',
                        height=350,
                        hovermode='x unified'
                    )
                    st.plotly_chart(fig, use_container_width=True)
                
                with tab_detail2:
                    st.dataframe(
                        df_daily.style.format({
                            '流水(万元)': lambda x: f'{x:,.2f}万'
                        }).highlight_max(subset=['流水(万元)'], axis=0, props='background-color: #d4edda'),
                        use_container_width=True,
                        hide_index=True
                    )
                
                with tab_detail3:
                    col_stats1, col_stats2, col_stats3 = st.columns(3)
                    with col_stats1:
                        st.metric("总流水", f"¥{df_daily['流水(万元)'].sum():,.2f}万")
                    with col_stats2:
                        st.metric("日均流水", f"¥{df_daily['流水(万元)'].mean():,.2f}万") 
                    with col_stats3:
                        st.metric("最高单日", f"¥{df_daily['流水(万元)'].max():,.2f}万")
            else:
                st.warning("当前月份暂无详细每日数据")
        else:
            st.warning("⚠️ 暂无环比数据，请确保已导入对账业务总表数据")
    except Exception as e:
        st.error(f"❌ 数据加载失败: {str(e)}")
        st.info("📋 **解决建议**：请确认已导入 `duizhang_summary_2025` 和 `duizhang_summary_2026` 表")

# 边栏信息
st.sidebar.divider()
st.sidebar.info(f"""
## 🏷️ 仪表板信息
- **数据源**: 静态数据库读取
- **缓存策略**: 每30秒刷新一次
- **更新时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
### 🎯 今日重点
{'- 有异常数据 ⚠️' if (df_date['订单数'] > df_filtered.groupby('医院')['订单数'].transform('mean') * 2).any() if not df_date.empty else '- 暂无异常数据 ✅'}
""")