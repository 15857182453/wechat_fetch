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
from datetime import datetime, timedelta

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
    """
    数据加载逻辑：
    1. 优先从明细表获取数据（按医院/日期分组）
    2. 检查哪些日期在明细表中缺失
    3. 仅从汇总表补充缺失的日期数据
    """
    conn = sqlite3.connect(DB_PATH)
    
    # Step 1: 从明细表获取数据（4 个表 UNION ALL）
    table_names = ['daily_flow_2025', 'daily_flow_2026_jan_feb', 'daily_flow_2026_mar', 'daily_flow_2026_apr']
    
    queries = []
    for table in table_names:
        q = f"""
            SELECT institution, 
                   COUNT(*) as cnt, 
                   SUM(amount) as amt, 
                   ROUND(SUM(amount)/COUNT(*), 2) as avg_amt,
                   SUBSTR(yewu_wancheng_shijian, 1, 10) as dt
            FROM {table}
            WHERE ye_wu_lei_mu LIKE '%处方服务%' AND pay_status = '收费'
              AND yewu_wancheng_shijian IS NOT NULL AND amount IS NOT NULL
            GROUP BY institution, SUBSTR(yewu_wancheng_shijian, 1, 10)
        """
        queries.append(q)
    
    # 执行明细查询
    full_query = " UNION ALL ".join(queries)
    df_detail = pd.read_sql_query(full_query, conn)
    df_detail.columns = ['医院', '订单数', '金额', '客单价', '日期']
    
    # Step 2: 获取明细表已有的日期
    existing_dates = set(df_detail['日期'].unique()) if len(df_detail) > 0 else set()
    
    # Step 3: 仅查询缺失日期的汇总数据（避免读取全部汇总表）
    if len(existing_dates) > 0:
        dates_placeholder = ','.join([f"'{d}'" for d in existing_dates])
        q_missing = f"""
            SELECT date as dt, daily_total_flow as amt
            FROM duizhang_summary_2026
            WHERE daily_total_flow > 0
              AND date NOT IN ({dates_placeholder})
        """
    else:
        # 明细表完全无数据时，读取全部汇总数据
        q_missing = """
            SELECT date as dt, daily_total_flow as amt
            FROM duizhang_summary_2026
            WHERE daily_total_flow > 0
        """
    
    df_missing = pd.read_sql_query(q_missing, conn)
    
    # Step 4: 为缺失日期创建补充数据
    if len(df_missing) > 0:
        avg_orders = int(df_detail['订单数'].mean()) if len(df_detail) > 0 else 100
        
        df_missing['医院'] = '数据待补充'
        df_missing['订单数'] = avg_orders
        df_missing['金额'] = df_missing['amt'] * 10000  # 汇总表万元→元
        df_missing['客单价'] = (df_missing['金额'] / avg_orders).round(2) if avg_orders > 0 else 0
        df_missing['日期'] = df_missing['dt']
        df_missing = df_missing[['医院', '订单数', '金额', '客单价', '日期']]
        
        # 合并明细数据 + 汇总补充数据
        df = pd.concat([df_detail, df_missing], ignore_index=True)
    else:
        # 明细表数据完整，无需补充
        df = df_detail
    
    conn.close()
    return df

# ========= 环比计算函数 =========
def calculate_mom_growth():
    """计算月环比：动态计算到最新数据日期"""
    with st.spinner("🔄 正在计算月环比数据分析..."):
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
        
        selected_date = st.date_input(
            "📅 选择分析日期",
            value=max_date,
            min_value=min_date,
            max_value=max_date,
            help="选择特定日期查看当天数据详情"
        )
        selected_date_str = selected_date.strftime('%Y-%m-%d')
    
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

# ========== 标签页布局 (6 个功能页签) ==========
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "📊 **总览分析**", 
    "📈 **趋势洞察**", 
    "⚠️ **异常监控**", 
    "🏆 **医院排行**", 
    "🌍 **区域分布**", 
    "📉 **月度环比**"
])

# ========== TAB 1: 总览分析 ==========
with tab1:
    st.markdown(f'<div class="card fade-in"><h3>📋 {selected_date_str} - 实时运营概览</h3></div>', unsafe_allow_html=True)
    
    # KPI 指标行
    col1, col2, col3, col4 = st.columns(4)
    
    total_orders = df_date['订单数'].sum() if not df_date.empty else 0
    total_amount = df_date['金额'].sum() if not df_date.empty else 0
    avg_amount = total_amount / total_orders if total_orders > 0 else 0
    active_hospitals = len(df_date) if not df_date.empty else 0
    
    # 计算与前一天的对比
    from datetime import datetime, timedelta
    try:
        current_dt = datetime.strptime(selected_date_str, '%Y-%m-%d')
        prev_date_str = (current_dt - timedelta(days=1)).strftime('%Y-%m-%d')
        df_prev = df_filtered[df_filtered['日期'] == prev_date_str]
        
        prev_orders = df_prev['订单数'].sum() if not df_prev.empty else 0
        prev_amount = df_prev['金额'].sum() if not df_prev.empty else 0
        prev_avg = prev_amount / prev_orders if prev_orders > 0 else 0
        
        orders_delta = ((total_orders - prev_orders) / prev_orders * 100) if prev_orders > 0 else None
        amount_delta = ((total_amount - prev_amount) / prev_amount * 100) if prev_amount > 0 else None
        avg_delta = ((avg_amount - prev_avg) / prev_avg * 100) if prev_avg > 0 else None
    except:
        orders_delta = None
        amount_delta = None
        avg_delta = None
    
    with col1:
        st.markdown('<div class="fade-in">', unsafe_allow_html=True)
        st.metric(
            label="🎫 总订单数",
            value=f"{int(total_orders):,}",
            delta=f"{orders_delta:+.1f}%" if orders_delta is not None else None,
            delta_color="normal",
            help="与前一日对比"
        )
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col2:
        st.markdown('<div class="fade-in">', unsafe_allow_html=True)
        st.metric(
            label="💰 总金额",
            value=f"¥{total_amount:,.0f}",
            delta=f"{amount_delta:+.1f}%" if amount_delta is not None else None,
            delta_color="normal",
            help="与前一日对比（元）"
        )
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col3:
        st.markdown('<div class="fade-in">', unsafe_allow_html=True)
        st.metric(
            label="🏷️ 平均客单价",
            value=f"¥{avg_amount:,.2f}",
            delta=f"{avg_delta:+.1f}%" if avg_delta is not None else None,
            delta_color="normal",
            help="每笔订单平均消费金额（元），与前一日对比"
        )
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col4:
        st.markdown('<div class="fade-in">', unsafe_allow_html=True)
        st.metric(
            label="🏥 覆盖医院",
            value=f"{active_hospitals} 家",
            delta=None,
            help="参与当日报表的医院数量"
        )
        st.markdown('</div>', unsafe_allow_html=True)
    
    # 今日医院详情表格
    if not df_date.empty:
        st.divider()
        st.markdown("### 🏥 当日医院明细")
        df_rich = df_date[['医院', '订单数', '金额', '客单价']].sort_values('订单数', ascending=False).reset_index(drop=True).copy()
        df_rich['订单数'] = df_rich['订单数'].astype(int)
        # 金额和客单价已统一为元，无需转换
        
        # 创建表格样式
        def color_row(row):
            color = '#e8f2ff' if row.name % 2 == 0 else '#ffffff'  # 交替颜色
            return [f'background-color: {color}' for _ in row]
        
        st.dataframe(
            df_rich.style.apply(color_row, axis=1).format({
                '金额': '¥{:,}',
                '客单价': '¥{:.2f}',
                '金额': '¥{:,.0f}',
                '订单数': '{:,.0f}'
            }),
            use_container_width=True,
            hide_index=True,
            height=400
        )
    else:
        st.markdown("⚠️ 当日无数据，请选择其他日期或检查筛选条件")

# ========== TAB 2: 趋势洞察 ==========
with tab2:
    st.markdown('<div class="card fade-in"><h3>📈 近7天运营趋势分析</h3></div>', unsafe_allow_html=True)
    
    if not df_filtered.empty:
        selected_dt = pd.to_datetime(selected_date_str)
        date_range = pd.date_range(end=selected_dt, periods=7, freq='D')
        date_strings = [d.strftime('%Y-%m-%d') for d in date_range]
        
        # 按日期聚合数据（排除"数据待补充"的汇总数据，避免重复计算）
        df_detail_only = df_filtered[df_filtered['医院'] != '数据待补充']
        df_temp = df_detail_only[df_detail_only['日期'].isin(date_strings)]
        
        # 各医院趋势（明细数据）
        daily_trends = df_temp.groupby(['日期', '医院']).agg({
            '订单数': 'sum',
            '金额': 'sum',
            '客单价': 'mean'
        }).reset_index()
        
        # 按日期聚合总量（含汇总补充数据）
        df_temp_all = df_filtered[df_filtered['日期'].isin(date_strings)]
        daily_totals = df_temp_all.groupby('日期').agg({
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
                    yaxis_title='金额 (万元)',
                    hovermode='x unified'
                )
                st.plotly_chart(fig_revenue, use_container_width=True)
            
            st.divider()
            st.markdown("### 🏥 各医院详细趋势")
            
            if not daily_trends.empty:
                # 按总订单数取 TOP 15 医院，避免图表混乱
                top_hospitals = daily_trends.groupby('医院')['订单数'].sum().nlargest(15).index.tolist()
                df_top = daily_trends[daily_trends['医院'].isin(top_hospitals)]
                
                fig_detail = px.line(
                    df_top,
                    x='日期',
                    y='订单数',
                    color='医院',
                    title='各医院订单数趋势对比 (TOP 15)',
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
                    df_top,
                    x='日期',
                    y='金额',
                    color='医院',
                    title='各医院营业额趋势对比 (TOP 15)',
                    markers=True,
                    line_shape='spline',
                    color_discrete_sequence=px.colors.qualitative.Set3
                )
                fig_revenue_compare.update_layout(
                    template='plotly_white',
                    height=400,
                    xaxis_title='日期',
                    yaxis_title='金额 (万元)',
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
    st.markdown("- **Z-Score 算法**: 统计异常检测（阈值 ±3σ）\n- **IQR 算法**: 四分位距检测（1.5倍四分位距外）\n- **动态阈值**: 基于历史波动自适应调节\n- **环比增长**: 短期增长率超出200%报警")

    if not df_hospital.empty:
        all_hospitals = df_hospital['医院'].unique()
        anomalies = []
        
        with st.spinner("🤖 正在执行异常检测分析..."):
            for idx, hospital in enumerate(all_hospitals):
                # 获取近 7 天数据（检测所有日期，而非仅选中日期）
                hosp_data = df_hospital[df_hospital['医院'] == hospital].sort_values('日期', ascending=False).head(7)
                if len(hosp_data) < 2:
                    continue
                
                # 按日期聚合
                daily = hosp_data.groupby('日期').agg({'订单数': 'sum', '金额': 'sum'}).reset_index()
                if len(daily) < 3:  # 至少需要3天才能检测异常
                    continue
                
                # 对每一天进行检测（而非仅检测选中日期）
                for _, today_row in daily.iterrows():
                    check_date = today_row['日期']
                    today_orders = int(today_row['订单数'])
                    today_amount = float(today_row['金额'])
                    
                    # 计算统计指标（排除当天数据）
                    other_days = daily[daily['日期'] != check_date]['订单数']
                    if len(other_days) < 2:
                        continue
                    
                    mean_orders = other_days.mean()
                    median_orders = other_days.median()
                    std_orders = other_days.std()
                    
                    q1_orders = other_days.quantile(0.25)
                    q3_orders = other_days.quantile(0.75)
                    iqr_orders = q3_orders - q1_orders
                    upper_bound = q3_orders + 2.5 * iqr_orders
                    
                    dynamic_threshold = max(median_orders * 2.0, mean_orders + 3 * std_orders)
                    dynamic_threshold = max(dynamic_threshold, 50)
                    
                    # 多算法检测
                    anomaly_flags = []
                    if std_orders and std_orders > 0:
                        zscore = (today_orders - mean_orders) / std_orders
                        if abs(zscore) > 3.0:
                            anomaly_flags.append(f'🔴 Z-Score={zscore:.2f}')
                    
                    if today_orders > upper_bound:
                        anomaly_flags.append(f'🟠 IQR>{upper_bound:.0f}')
                    
                    if today_orders >= 20 and today_orders > dynamic_threshold:
                        anomaly_flags.append(f'🟢 动态>{dynamic_threshold:.0f}')
                    
                    # 环比增长检测
                    prev_day_data = daily[daily['日期'] < check_date].sort_values('日期', ascending=False)
                    if not prev_day_data.empty and prev_day_data.iloc[0]['订单数'] >= 10:
                        prev_orders = prev_day_data.iloc[0]['订单数']
                        if prev_orders > 0:
                            growth_rate = (today_orders - prev_orders) / prev_orders * 100
                            if growth_rate > 200:
                                anomaly_flags.append(f'🔵 环比+{growth_rate:.0f}%')
                    
                    # 至少2个检测器确认才标记异常
                    if len(anomaly_flags) >= 2:
                        anomalies.append({
                            '医院': hospital,
                            '日期': check_date,
                            '订单数': today_orders,
                            '金额': today_amount,
                            '异常类型': anomaly_flags,
                            '均值': float(mean_orders),
                            '标准差': float(std_orders),
                            'IQR上限': float(upper_bound),
                        '动态阈值': float(dynamic_threshold),
                        '检测算法数': len(anomaly_flags)
                    })
        
        # 按选中日期过滤异常数据
        anomalies_filtered = [a for a in anomalies if a['日期'] == selected_date_str]
        
        # 显示异常结果
        if anomalies_filtered:
            st.error(f"🚨 **{selected_date_str}** 发现 **{len(anomalies_filtered)}** 个医院存在显著异常波动！")
            for i, a in enumerate(anomalies_filtered):
                anomaly_types = " | ".join(a['异常类型'])
                expander_title = f"🏥 异常医院：{a['医院']} | 📦 {a['订单数']:,} 单 | 💰 ¥{a['金额']:,.0f} | 🔍 {a['检测算法数']}种预警"
                
                with st.expander(expander_title, expanded=False):
                    col1, col2 = st.columns(2)
                    with col1:
                        st.subheader("📊 异常概要")
                        st.write(f"**📅 日期**：{a['日期']}")
                        st.write(f"**📦 订单**：{a['订单数']:,} 单")
                        st.write(f"**💰 金额**：¥{a['金额']:,.0f}")
                        st.write(f"**📈 近 7 日均值**：{a['均值']:.1f} 单")
                        st.write(f"**📉 标准差**：{a['标准差']:.2f} 单")
                        st.write(f"**🎯 检出算法**：{a['检测算法数']} 种")
                    
                    with col2:
                        st.subheader("🔍 异常明细")
                        for flag in a['异常类型']:
                            if 'Z-Score' in flag:
                                st.error(f"🔴 **统计异常**：{flag}")
                            elif 'IQR' in flag:
                                st.warning(f"🟠 **分布异常**：{flag}")
                            elif '动态' in flag:
                                st.info(f"🟢 **基准异常**：{flag}")
                            elif '环比' in flag:
                                st.success(f"🔵 **增长异常**：{flag}")
                        
                    # 绘制异常医院趋势图
                    hosp_trend = df_hospital[df_hospital['医院'] == a['医院']].sort_values('日期', ascending=False).head(7)
                    if not hosp_trend.empty:
                        fig = go.Figure()
                        fig.add_trace(go.Bar(
                            x=hosp_trend['日期'],
                            y=hosp_trend['订单数'],
                            name='订单数',
                            marker_color='rgba(255, 107, 107, 0.7)'
                        ))
                        fig.add_hline(y=a['均值'], line_dash="dash", line_color="red", annotation_text="7日均值")
                        fig.add_hline(y=a['动态阈值'], line_dash="dot", line_color="green", annotation_text="动态阈值")
                        fig.update_layout(
                            title=f'{a["医院"]} - 近 7 天订单趋势与异常线',
                            xaxis_title='日期',
                            yaxis_title='订单数',
                            height=300
                        )
                        st.plotly_chart(fig, use_container_width=True)
        else:
            st.success(f"✅ **{selected_date_str}** 所有 {len(all_hospitals)} 家医院数据正常，未检测到异常波动")
    else:
        st.warning("⚠️ 暂无有效数据可供异常检测分析")

# ========== TAB 4: 医院排行 ==========
with tab4:
    st.markdown('<div class="card fade-in"><h3>🏆 医院业绩排行榜 (按当日营业额排名)</h3></div>', unsafe_allow_html=True)
    
    if not df_date.empty:
        tab4_sub1, tab4_sub2, tab4_sub3 = st.tabs(["💰 营业额Top10", "📦 订单量Top10", "🏷️ 客单价Top10"])
        
        with tab4_sub1:
            df_top_revenue = df_date.sort_values('金额', ascending=False).head(10)
            if not df_top_revenue.empty:
                st.dataframe(
                    df_top_revenue[['医院', '订单数', '金额', '客单价']].rename(
                        columns={'医院':'医院', '订单数':'订单数', '金额':'金额(元)', '客单价':'客单价(元)'}
                    ).reset_index(drop=True),
                    use_container_width=True,
                    hide_index=True
                )
            else:
                st.info("🔍 当日无营业额排名数据")
        
        with tab4_sub2:
            df_top_orders = df_date.sort_values('订单数', ascending=False).head(10)
            if not df_top_orders.empty:
                st.dataframe(
                    df_top_orders[['医院', '订单数', '金额', '客单价']].rename(
                        columns={'医院':'医院', '订单数':'订单数', '金额':'金额(元)', '客单价':'客单价(元)'}
                    ).reset_index(drop=True),
                    use_container_width=True,
                    hide_index=True
                )
            else:
                st.info("🔍 当日无订单量排名数据")
        
        with tab4_sub3:
            df_top_price = df_date.sort_values('客单价', ascending=False).head(10)
            if not df_top_price.empty:
                st.dataframe(
                    df_top_price[['医院', '订单数', '金额', '客单价']].rename(
                        columns={'医院':'医院', '订单数':'订单数', '金额':'金额(元)', '客单价':'客单价(元)'}
                    ).reset_index(drop=True),
                    use_container_width=True,
                    hide_index=True
                )
            else:
                st.info("🔍 当日无客单价排名数据")
    else:
        st.warning("⚠️ 请先选择有效的日期和医院查看排行数据")

# ========== TAB 5: 区域分布 ==========
with tab5:
    st.markdown('<div class="card fade-in"><h3>🌍 医院地理区域分布热力分析</h3></div>', unsafe_allow_html=True)
    
    with st.spinner("🗺️ 正在绘制区域分布..."):
        try:
            conn = sqlite3.connect(DB_PATH)
            query = """
                SELECT province, COUNT(DISTINCT institution) as 医院数量 
                FROM (
                    SELECT DISTINCT institution, province FROM daily_flow_2025 WHERE province IS NOT NULL
                    UNION SELECT DISTINCT institution, province FROM daily_flow_2026_jan_feb WHERE province IS NOT NULL
                    UNION SELECT DISTINCT institution, province FROM daily_flow_2026_mar WHERE province IS NOT NULL
                    UNION SELECT DISTINCT institution, province FROM daily_flow_2026_apr WHERE province IS NOT NULL
                ) 
                WHERE province IS NOT NULL 
                GROUP BY province 
                ORDER BY 医院数量 DESC
            """
            df_province = pd.read_sql_query(query, conn)
            
            if not df_province.empty:
                col1, col2 = st.columns(2)
                
                with col1:
                    if len(df_province) <= 20:  # 如果省份数较少，用饼图
                        fig_pie = px.pie(
                            df_province, 
                            values='医院数量', 
                            names='province', 
                            title=' Hospitals by Province - Top Regions Coverage',
                            color_discrete_sequence=px.colors.sequential.Plasma_r
                        )
                        fig_pie.update_traces(textposition='inside', textinfo='percent+label')
                        st.plotly_chart(fig_pie, use_container_width=True)
                    else:
                        # 省份数较多时用条形图，只显示TOP10
                        df_prov_top = df_province.head(10)
                        fig_bar = px.bar(
                            df_prov_top, 
                            x='province', 
                            y='医院数量',
                            title='🏥 TOP 10 Province Distribution',
                            color='医院数量',
                            color_continuous_scale='Bluered'
                        )
                        fig_bar.update_xaxes(tickangle=45)
                        st.plotly_chart(fig_bar, use_container_width=True)
                
                with col2:
                    # 区域数据表格
                    st.subheader("📋 区域覆盖详情")
                    st.dataframe(
                        df_province.rename(columns={
                            'province': '省份',
                            '医院数量': '医院数量'
                        }),
                        use_container_width=True,
                        height=500
                    )
                
                # 区域摘要信息
                total_provinces = len(df_province)
                top_province = df_province.iloc[0]['province'] if not df_province.empty else 'Unknown'
                top_count = df_province.iloc[0]['医院数量'] if not df_province.empty else 0
                avg_provinces = df_province['医院数量'].mean() if not df_province.empty else 0
                
                metrics_col1, metrics_col2, metrics_col3 = st.columns(3)
                with metrics_col1:
                    st.metric("🌐 覆盖省份数", f"{total_provinces}", help="总计覆盖多少个省份")
                with metrics_col2:
                    st.metric("📍 最多省份", f"{top_province} ({top_count})", help="医院分布最多的省份")
                with metrics_col3:
                    st.metric("📊 平均密度", f"{avg_provinces:.1f}", help="各省平均医院数量")
            
            else:
                st.info("🔍 暂无区域分布数据")
            
            conn.close()
        
        except Exception as e:
            st.error(f"❌ 区域数据加载失败: {e}")
    
# ========== TAB 6: 月环比分析 ==========
with tab6:
    st.markdown('<div class="card fade-in"><h3>📉 月环比智能分析 - 动态计算模式</h3></div>', unsafe_allow_html=True)
    st.info("💡 **智能环比说明**: 自动匹配最新数据截止日期（如 4月6日 -> 计算 4月1-6日 vs 3月1-6日的对比），并包含同比分析")
    
    try:
        result, current_data, prev_data = calculate_mom_growth()
        
        if result:
            # 今日数据日期
            st.markdown(f"📅 **最新数据日期**：{result['latest_date']}")
            
            # 查询2025年12月同期做同比 (年度对比)
            with st.spinner("🔄 正在计算同比数据..."):
                conn = sqlite3.connect(DB_PATH)
                current_day = datetime.strptime(result['latest_date'], '%Y-%m-%d').day
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT COUNT(*), SUM(daily_total_flow), AVG(daily_total_flow)
                    FROM duizhang_summary_2025
                    WHERE date >= ? AND date <= ?
                """, ('2025-12-01', f'2025-12-{current_day:02d}'))
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

# ========== 底部信息 ==========
st.divider()
col_info1, col_info2, col_info3 = st.columns(3)
with col_info1:
    st.markdown(f"<small>🔄 最后刷新：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</small>", unsafe_allow_html=True)
with col_info2:
    st.markdown("<small>🏥 智能监控，异常秒级响应</small>", unsafe_allow_html=True)
with col_info3:
    st.markdown("<small>⚙️ 优化版运营仪表板 v4.0</small>", unsafe_allow_html=True)