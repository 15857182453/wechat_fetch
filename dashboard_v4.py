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
    with st.spinner("正在连接数据库并获取数据..."):
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # 尝试从明细表获取数据
        table_names = ['daily_flow_2025', 'daily_flow_2026_jan_feb', 'daily_flow_2026_mar', 'daily_flow_2026_apr']
        
        queries = []
        for table in table_names:
            try:
                q = f"""
                    SELECT institution, 
                           COUNT(*) as cnt, 
                           SUM(amount) as amt, 
                           ROUND(SUM(amount)*1.0/COUNT(*), 2) as avg_amt,
                           SUBSTR(yewu_wancheng_shijian, 1, 10) as dt
                    FROM {table}
                    WHERE ye_wu_lei_mu LIKE '%处方服务%' AND pay_status = '收费'
                      AND yewu_wancheng_shijian IS NOT NULL AND amount IS NOT NULL
                    GROUP BY institution, SUBSTR(yewu_wancheng_shijian, 1, 10)
                """
                queries.append(q)
            except Exception as e:
                pass
        
        # 如果明细表数据不足，使用汇总数据
        if not queries:
            # 从 duizhang_summary_2026 获取汇总数据
            q = """
                SELECT '汇总数据' as institution,
                       1 as cnt,
                       daily_total_flow as amt,
                       daily_total_flow as avg_amt,
                       date as dt
                FROM duizhang_summary_2026
                WHERE date >= '2026-03-01' AND daily_total_flow > 0
            """
            queries.append(q)
        
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

# ========== 标签页布局 (7 个功能页签) ==========
tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8 = st.tabs([
    "📊 **总览分析**", 
    "📈 **趋势洞察**", 
    "⚠️ **异常监控**", 
    "🏆 **医院排行**", 
    "🌍 **区域分布", 
    "📉 **月度环比**",
    "💊 **便捷配药**",
    "📋 **运营快报**"
])

# ========== TAB 1: 总览分析 ==========
with tab1:
    st.markdown(f'<div class="card fade-in"><h3>📋 {selected_date_str} - 实时运营概览</h3></div>', unsafe_allow_html=True)
    
    # KPI 指标行
    col1, col2, col3, col4 = st.columns(4)
    
    total_orders = int(df_date['订单数'].sum()) if not df_date.empty else 0
    total_amount = float(df_date['金额'].sum()) if not df_date.empty else 0
    avg_amount = float(df_date['客单价'].mean()) if not df_date.empty and len(df_date) > 0 else 0
    active_hospitals = len(df_date) if not df_date.empty else 0
    
    # 计算与前一天的真实对比
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
    
    # 今日医院详情表格
    if not df_date.empty:
        st.divider()
        st.markdown("### 🏥 当日医院明细")
        df_rich = df_date[['医院', '订单数', '金额', '客单价']].round(2)
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
        st.markdown("⚠️ 当日无数据，请选择其他日期或检查筛选条件")

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
    st.markdown("- **Z-Score 算法**: 统计异常检测（阈值 ±3σ）\n- **IQR 算法**: 四分位距检测（1.5倍四分位距外）\n- **动态阈值**: 基于历史波动自适应调节\n- **环比增长**: 短期增长率超出200%报警")

    if not df_hospital.empty:
        all_hospitals = df_hospital['医院'].unique()
        anomalies = []
        
        with st.spinner("🤖 正在执行异常检测分析..."):
            for idx, hospital in enumerate(all_hospitals):
                # 获取近 7 天数据
                hosp_data = df_hospital[df_hospital['医院'] == hospital].sort_values('日期', ascending=False).head(7)
                if len(hosp_data) < 2:
                    continue
                
                # 按日期聚合
                daily = hosp_data.groupby('日期').agg({'订单数': 'sum', '金额': 'sum'}).reset_index()
                if len(daily) < 2:
                    continue
                
                # 获取今日数据
                today = daily[daily['日期'] == selected_date_str]
                if today.empty:
                    continue
                
                today_orders = int(today.iloc[0]['订单数'])
                today_amount = float(today.iloc[0]['金额'])
                
                # 计算统计指标（排除今日数据）
                other_days = daily[daily['日期'] != selected_date_str]['订单数']
                
                if len(other_days) < 2:
                    continue
                
                mean_orders = other_days.mean()
                median_orders = other_days.median()
                std_orders = other_days.std()
                
                q1_orders = other_days.quantile(0.25)
                q3_orders = other_days.quantile(0.75)
                iqr_orders = q3_orders - q1_orders
                upper_bound = q3_orders + 2.5 * iqr_orders  # 更宽松的IQR
                
                # 动态阈值（更宽松）
                dynamic_threshold = max(
                    median_orders * 2.0,
                    mean_orders + 3 * std_orders
                )
                dynamic_threshold = max(dynamic_threshold, 50)
                
                # 多算法检测逻辑
                anomaly_flags = []
                # 检查每个算法的触发条件
                if std_orders and std_orders > 0:
                    zscore = (today_orders - mean_orders) / std_orders
                    if abs(zscore) > 3.0:  # 3σ 规则
                        anomaly_flags.append(f'🔴 Z-Score={zscore:.2f}')
                
                if today_orders > upper_bound:
                    anomaly_flags.append(f'🟠 IQR>{upper_bound:.0f}')
                
                if today_orders >= 20 and today_orders > dynamic_threshold:
                    anomaly_flags.append(f'🟢 动态>{dynamic_threshold:.0f}')
                
                # 环比增长检测
                prev_day_data = daily[daily['日期'] < selected_date_str].sort_values('日期', ascending=False)
                if not prev_day_data.empty and prev_day_data.iloc[0]['订单数'] >= 10:
                    prev_orders = prev_day_data.iloc[0]['订单数']
                    if prev_orders > 0:
                        growth_rate = (today_orders - prev_orders) / prev_orders * 100
                        if growth_rate > 200:
                            anomaly_flags.append(f'🔵 环比+{growth_rate:.0f}%')
                
                # 所有算法都检测到异常才标记
                if len(anomaly_flags) >= 2 and len([f for f in anomaly_flags if 'IQR' not in f or len(anomaly_flags) > 1]):  # 至少2个检测器确认
                    anomalies.append({
                        '医院': hospital,
                        '日期': selected_date_str,
                        '订单数': today_orders,
                        '金额': today_amount,
                        '异常类型': anomaly_flags,
                        '均值': float(mean_orders),
                        '标准差': float(std_orders),
                        'IQR上限': float(upper_bound),
                        '动态阈值': float(dynamic_threshold),
                        '检测算法数': len(anomaly_flags)
                    })
        
        # 显示异常结果
        if anomalies:
            st.error(f"🚨 发现 **{len(anomalies)}** 个医院存在显著异常波动！")
            for i, a in enumerate(anomalies):
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
            st.success(f"✅ 所有 {len(all_hospitals)} 家医院数据正常，未检测到批量异常波动！系统运行稳定")
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
                st.info("🔍 当日无营业额排名数据")
        
        with tab4_sub2:
            df_top_orders = df_date.sort_values('订单数', ascending=False).head(10)
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
                st.info("🔍 当日无订单量排名数据")
        
        with tab4_sub3:
            df_top_price = df_date.sort_values('客单价', ascending=False).head(10)
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

# ========== TAB 7: 便捷配药数据统计 ==========
with tab7:
    st.markdown('<div style="text-align:center;font-size:22px;font-weight:bold;padding:10px 0;background:#2196F3;color:white;">💊 便捷配药数据统计</div>', unsafe_allow_html=True)
    st.markdown('')

    EXCEL_CP_PATH = '/mnt/c/Users/44238/Desktop/业务对账数据/对账业务总表/新流水2026.xlsx'

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
        tables_2026 = ['daily_flow_2026_jan_feb', 'daily_flow_2026_mar', 'daily_flow_2026_apr']
        all_data = {}
        for name, pattern in hospitals.items():
            parts = []
            for t in tables_2026:
                parts.append(f"SELECT SUBSTR(yewu_wancheng_shijian,1,10) as date, 1 as cnt, amount as amt FROM {t} WHERE institution LIKE '%{pattern}%' AND ye_wu_lei_mu LIKE '%处方服务%' AND pay_status='收费' AND yewu_wancheng_shijian IS NOT NULL AND amount IS NOT NULL")
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
        tables_2026 = ['daily_flow_2026_jan_feb', 'daily_flow_2026_mar', 'daily_flow_2026_apr']
        
        for config in HOSPITALS:
            # UNION ALL 联合所有 2026 年表
            queries = []
            for t in tables_2026:
                queries.append(f"SELECT SUBSTR(yewu_wancheng_shijian,1,10) as date, COUNT(*) as orders, SUM(amount) as flow FROM {t} WHERE institution LIKE '%{config['name']}%' AND pay_status='收费' AND yewu_wancheng_shijian IS NOT NULL AND amount IS NOT NULL GROUP BY SUBSTR(yewu_wancheng_shijian,1,10)")
            
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
        
        tables_2026 = ['daily_flow_2026_jan_feb', 'daily_flow_2026_mar', 'daily_flow_2026_apr']
        
        # 获取数据
        data_list = []
        for config in NEW_HOSPITALS:
            queries = []
            for t in tables_2026:
                queries.append(f"SELECT SUBSTR(yewu_wancheng_shijian,1,10) as date, COUNT(*) as orders FROM {t} WHERE institution LIKE '%{config['name']}%' AND pay_status='收费' AND yewu_wancheng_shijian IS NOT NULL AND amount IS NOT NULL GROUP BY SUBSTR(yewu_wancheng_shijian,1,10)")
            
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
        conn_r = sqlite3.connect(DB_PATH)

        # ===== 获取所有有效数据（过滤异常日期：订单<100视为异常）=====
        df_all = pd.read_sql_query('''
            SELECT date(yewu_wancheng_shijian) as date, institution, province,
                   pay_status, amount, ye_wu_lei_mu
            FROM daily_flow_2026_apr
            WHERE yewu_wancheng_shijian IS NOT NULL AND amount IS NOT NULL
        ''', conn_r)
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
            conn_r.close()
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

        conn_r.close()

    except Exception as e:
        st.error(f"❌ 运营快报加载失败：{e}")

# ========== 底部信息 ==========
# ========== 底部信息 ==========
st.divider()
col_info1, col_info2, col_info3 = st.columns(3)
with col_info1:
    st.markdown(f"<small>🔄 最后刷新：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</small>", unsafe_allow_html=True)
with col_info2:
    st.markdown("<small>🏥 智能监控，异常秒级响应</small>", unsafe_allow_html=True)
with col_info3:
    st.markdown("<small>⚙️ 优化版运营仪表板 v4.0</small>", unsafe_allow_html=True)