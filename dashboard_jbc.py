#!/usr/bin/env python3
"""金佰川鞋业运营数据看板 — Streamlit + PostgreSQL"""
import streamlit as st
import pandas as pd
import psycopg2
# 直接用 psycopg2，避免 SQLAlchemy params 兼容问题
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime

from auth_jbc import authenticate, is_admin, get_allowed_stores, get_current_user, get_hidden_tabs, filter_dataframe, build_store_filter

user = authenticate()

# ========= 页面配置 =========
st.set_page_config(page_title="金佰川运营看板", page_icon="🏪", layout="wide", initial_sidebar_state="expanded")

# ========= 数据库 =========
from psycopg2.pool import ThreadedConnectionPool

PG_DSN = "host=localhost dbname=jinbaichuan user=openclaw password=jbc2026"
_pool = ThreadedConnectionPool(minconn=2, maxconn=20, dsn=PG_DSN)

def _template(sql):
    """替换 SQL 模板变量 {ds} {de} {store_filter...}"""
    import re
    sql = sql.replace('{ds}', ds).replace('{de}', de)
    # {store_filter} 和 {store_filter.replace(...)}
    sql = re.sub(r'\{store_filter[^}]*\}', lambda m: str(eval(m.group()[1:-1])), sql)
    return sql

def query(sql, params=None):
    """执行 SQL 返回 DataFrame"""
    sql = _template(sql)
    if params is not None and isinstance(params, list):
        params = tuple(params)
    c = _pool.getconn()
    try:
        return pd.read_sql_query(sql, c, params=params if params else None)
    finally:
        _pool.putconn(c)

def query_one(sql, params=None):
    """执行 SQL 返回单行"""
    sql = _template(sql)
    c = _pool.getconn()
    try:
        cur = c.cursor()
        cur.execute(sql, params if params else None)
        return cur.fetchone()
    finally:
        cur.close()
        _pool.putconn(c)

# ========= CSS (dashboard_v6 模版) =========
st.markdown("""
<style>
:root {
  --color-primary: #1E40AF; --color-accent: #D97706; --color-success: #059669;
  --color-danger: #DC2626; --bg-page: #F8FAFC; --bg-card: #FFFFFF;
  --bg-hover: #F1F5F9; --border-default: #E2E8F0;
  --text-primary: #1E3A8A; --text-secondary: #64748B; --text-muted: #94A3B8;
  --font-mono: 'SF Mono','Fira Code','Courier New',monospace;
  --font-sans: 'Fira Sans',-apple-system,BlinkMacSystemFont,'Segoe UI','Microsoft YaHei','PingFang SC',sans-serif;
  --radius: 8px; --transition: 150ms ease;
}
.stApp { background: var(--bg-page); color: var(--text-primary); }
.top-nav {
    background: linear-gradient(135deg, #1E3A8A, #1E40AF); padding: 14px 24px;
    border-radius: var(--radius); margin-bottom: 20px;
    display: flex; align-items: center; justify-content: space-between;
    box-shadow: 0 4px 12px rgba(30,64,175,0.15);
}
.top-nav-title { color: #FFFFFF !important; font-size: 20px; font-weight: 700; font-family: var(--font-sans) !important; margin: 0 !important; text-shadow: 0 1px 3px rgba(0,0,0,0.3); }
.top-nav-subtitle { color: #93C5FD; font-size: 13px; margin-top: 2px; }
.top-nav-right { display: flex; align-items: center; gap: 12px; }
.top-nav-time { color: #BFDBFE; font-size: 13px; font-family: var(--font-mono); }
.top-nav-dot { width: 8px; height: 8px; border-radius: 50%; background: #34D399; display: inline-block; animation: pulse 2s infinite; }
@keyframes pulse { 0%,100%{opacity:1} 50%{opacity:0.4} }
.kpi-card {
    background: var(--bg-card); border: 1px solid var(--border-default);
    border-radius: var(--radius); padding: 20px; position: relative;
    transition: box-shadow var(--transition), border-color var(--transition);
    min-height: 120px; display: flex; flex-direction: column; justify-content: space-between;
}
.kpi-card:hover { border-color: var(--color-primary); box-shadow: 0 4px 12px rgba(30,64,175,0.1); }
.kpi-card::before { content:''; position:absolute; left:0; top:0; bottom:0; width:4px; background: var(--color-primary); border-radius: var(--radius) 0 0 var(--radius); }
.kpi-card.kpi-accent::before { background: var(--color-accent); }
.kpi-card.kpi-success::before { background: var(--color-success); }
.kpi-label { font-size:12px; color:var(--text-secondary); text-transform:uppercase; letter-spacing:0.5px; font-weight:500; }
.kpi-value { font-size:28px; font-weight:700; font-family:var(--font-mono); color:var(--text-primary); line-height:1.2; }
.kpi-sub { font-size:13px; color:var(--text-secondary); margin-top:4px; }
[data-testid="stMetric"] { background: transparent !important; border: none !important; box-shadow: none !important; padding: 0 !important; }
.stTabs [data-baseweb="tab-list"] { gap: 4px; flex-wrap: nowrap !important; overflow-x: auto !important; }
.stTabs [data-baseweb="tab"] {
    border: 1px solid var(--border-default) !important; border-radius: var(--radius) !important;
    margin-right: 4px !important; padding: 10px 20px !important; background: var(--bg-card) !important;
    transition: all var(--transition); color: var(--text-secondary) !important;
    font-family: var(--font-sans) !important; font-weight: 500 !important; font-size: 14px !important;
    white-space: nowrap !important; min-width: fit-content !important;
}
.stTabs [data-baseweb="tab"]:hover { background: var(--bg-hover) !important; transform: translateY(-1px); color: var(--text-primary) !important; }
.stTabs [aria-selected="true"] { background: var(--color-primary) !important; color: white !important; border-color: var(--color-primary) !important; }
.stDataFrame, .stTable { background: var(--bg-card) !important; border: 1px solid var(--border-default) !important; border-radius: var(--radius) !important; }
tr:nth-of-type(odd) { background-color: var(--bg-page) !important; }
tr:nth-of-type(even) { background-color: var(--bg-card) !important; }
</style>
""", unsafe_allow_html=True)

# ========= Top Nav =========
st.markdown(f"""
<div class="top-nav">
  <div>
    <div class="top-nav-title">🏪 金佰川鞋业 · 运营数据看板</div>
    <div class="top-nav-subtitle">数据更新: {datetime.now().strftime('%Y-%m-%d %H:%M')} | {user.get('display_name','')} ({user.get('role','')})</div>
  </div>
  <div class="top-nav-right">
    <span class="top-nav-time">54门店 · 109品牌</span>
    <span class="top-nav-dot"></span>
  </div>
</div>
""", unsafe_allow_html=True)

# ========= 侧边栏：日期筛选 =========
ds, de = "2026-05-01", "2026-05-31"  # 默认值，防止 f-string 报错
with st.sidebar:
    st.markdown("### 📅 日期筛选")
    date_range = st.date_input(
        "选择日期范围",
        value=(pd.to_datetime(ds), pd.to_datetime(de)),
        min_value=pd.to_datetime("2026-05-01"),
        max_value=pd.to_datetime("2026-05-31")
    )
    if isinstance(date_range, (tuple, list)) and len(date_range) == 2:
        ds = date_range[0].strftime('%Y-%m-%d')
        de = date_range[1].strftime('%Y-%m-%d')
    elif date_range is not None:
        ds = de = date_range.strftime('%Y-%m-%d') if hasattr(date_range, 'strftime') else str(date_range)[:10]
    days = max(1, (pd.to_datetime(de) - pd.to_datetime(ds)).days + 1)
    st.caption(f"已选 {days} 天 ({ds} ~ {de})")
    st.divider()

# ========= 数据加载 =========
store_filter, store_params = build_store_filter()

kpi_row = query_one("""
    SELECT
        COALESCE(SUM(settle_amount) FILTER (WHERE NOT is_return), 0) AS total_amt,
        COALESCE(SUM(gross_profit) FILTER (WHERE NOT is_return), 0) AS total_profit,
        COALESCE(COUNT(DISTINCT doc_no) FILTER (WHERE NOT is_return), 0) AS total_orders,
        COALESCE(SUM(quantity) FILTER (WHERE NOT is_return), 0) AS total_qty,
        COALESCE(COUNT(DISTINCT store_name), 0) AS store_cnt,
        COALESCE(SUM(settle_amount) FILTER (WHERE is_return), 0) AS return_amt
    FROM sales_detail WHERE submit_date >= '{ds}' AND submit_date <= '{de}'
    {store_filter}
""", store_params)

total_amt = float(kpi_row[0])
total_profit = float(kpi_row[1])
total_orders = int(kpi_row[2])
total_qty = int(kpi_row[3])
store_cnt = int(kpi_row[4])
return_amt = abs(float(kpi_row[5]))

# ========= Tabs =========
hidden_tabs = get_hidden_tabs()
tab_labels = [t for t in [
    "📊 总览KPI", "📈 趋势分析", "⚠️ 异常监控", "🏆 排行榜",
    "🔍 多维下钻", "📉 月度环比", "🏪 门店分析", "🏷️ 品牌分析",
    "📦 商品分析", "🔔 实时预警", "👥 用户管理", "📋 数据导入"
] if t not in hidden_tabs]
tabs = st.tabs(tab_labels)
T = dict(zip(tab_labels, tabs))

# ==================== TAB 1: 总览 KPI ====================
with T["📊 总览KPI"]:
    st.markdown(f"### 📊 数据总览 ({ds} ~ {de})")

    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.markdown(f'<div class="kpi-card"><div class="kpi-label">销售额</div><div class="kpi-value">¥{total_amt/10000:.1f}万</div><div class="kpi-sub">日均 ¥{total_amt/days/10000:.1f}万</div></div>', unsafe_allow_html=True)
    with col2:
        st.markdown(f'<div class="kpi-card kpi-success"><div class="kpi-label">毛利</div><div class="kpi-value">¥{total_profit/10000:.1f}万</div><div class="kpi-sub">毛利率 {total_profit/total_amt*100:.1f}%</div></div>', unsafe_allow_html=True)
    with col3:
        st.markdown(f'<div class="kpi-card kpi-accent"><div class="kpi-label">订单数</div><div class="kpi-value">{total_orders/10000:.2f}万</div><div class="kpi-sub">客单价 ¥{total_amt/total_orders:.0f}</div></div>', unsafe_allow_html=True)
    with col4:
        st.markdown(f'<div class="kpi-card"><div class="kpi-label">件数</div><div class="kpi-value">{total_qty/10000:.2f}万</div><div class="kpi-sub">连带率 {total_qty/total_orders:.1f}件/单</div></div>', unsafe_allow_html=True)
    with col5:
        st.markdown(f'<div class="kpi-card kpi-success"><div class="kpi-label">件单价</div><div class="kpi-value">¥{total_amt/total_qty:.0f}</div><div class="kpi-sub">门店 {store_cnt} 家</div></div>', unsafe_allow_html=True)

    c1, c2 = st.columns([1, 2])
    with c1:
        dept_df = query("""
            SELECT dept_name, SUM(settle_amount) as amt
            FROM sales_detail WHERE NOT is_return AND submit_date >= '{ds}' {store_filter}
            GROUP BY dept_name ORDER BY amt DESC
        """, store_params)
        dept_df['pct'] = dept_df['amt'] / dept_df['amt'].sum() * 100
        dept_df['label'] = dept_df.apply(lambda r: f"{r['dept_name']}<br>¥{r['amt']/10000:.0f}万 ({r['pct']:.1f}%)", axis=1)
        # Explode largest slice
        pull = [0.08 if i == 0 else 0.02 for i in range(len(dept_df))]
        fig = go.Figure(go.Pie(
            labels=dept_df['dept_name'],
            values=dept_df['amt'],
            hole=0.55,
            pull=pull,
            textinfo='percent',
            texttemplate='%{percent:.1%}',
            textfont=dict(size=13, family='Fira Sans'),
            marker=dict(
                colors=['#1E40AF','#3B82F6','#059669','#D97706','#7C3AED','#DC2626','#0891B2','#2563EB','#9333EA'],
                line=dict(color='#FFFFFF', width=2)
            ),
            hovertemplate='<b>%{label}</b><br>销售额: ¥%{value:,.0f}<br>占比: %{percent:.1%}<extra></extra>',
            sort=False
        ))
        fig.add_annotation(text=f'<b>9</b><br><span style="font-size:12px;color:#64748B">品类</span>',
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=24, color='#1E3A8A', family='Fira Sans'))
        fig.update_layout(height=360, margin=dict(t=10,b=10,l=10,r=10),
            showlegend=True, legend=dict(orientation='h', y=-0.1, font=dict(size=11)),
            paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig, use_container_width=True)

    with c2:
        daily_df = query("""
            SELECT submit_date, SUM(total_amt) as amt, SUM(total_profit) as profit
            FROM mv_store_daily WHERE submit_date >= '{ds}' {store_filter.replace('store_name','mv_store_daily.store_name')}
            GROUP BY submit_date ORDER BY submit_date
        """, store_params)
        fig = make_subplots(specs=[[{"secondary_y": True}]])
        fig.add_trace(go.Bar(x=daily_df['submit_date'], y=daily_df['amt']/10000, name='日销售额(万)', marker_color='#D97706'), secondary_y=False)
        fig.add_trace(go.Scatter(x=daily_df['submit_date'], y=daily_df['profit']/daily_df['amt']*100, name='毛利率%', marker_color='#059669', mode='lines+markers'), secondary_y=True)
        fig.update_layout(title='{ds}~{de} 日销售趋势', height=350, hovermode='x unified', template='plotly_white')
        st.plotly_chart(fig, use_container_width=True)

# ==================== TAB 2: 趋势分析 ====================
with T["📈 趋势分析"]:
    st.markdown("### 📈 趋势分析")

    dim = st.selectbox("分析维度", ["门店", "品牌", "品类", "时段(小时)"], key="trend_dim")
    top_n = st.slider("Top N", 5, 30, 10)

    if dim == "时段(小时)":
        trend_df = query(f"""
            SELECT hour, SUM(settle_amount) as amt, COUNT(DISTINCT doc_no) as orders
            FROM sales_detail WHERE NOT is_return AND submit_date >= '{ds}' {store_filter}
            GROUP BY hour ORDER BY hour
        """, store_params)
        fig = make_subplots(specs=[[{"secondary_y": True}]])
        fig.add_trace(go.Bar(x=trend_df['hour'], y=trend_df['amt']/10000, name='销售额(万)', marker_color='#D97706'), secondary_y=False)
        fig.add_trace(go.Scatter(x=trend_df['hour'], y=trend_df['orders'], name='订单数', marker_color='#1E40AF', mode='lines+markers'), secondary_y=True)
        fig.update_layout(title='时段销售分布 (5月累计)', hovermode='x unified')
    else:
        dim_map = {"门店": ("mv_store_daily", "store_name"), "品牌": ("mv_brand_daily", "brand_name"), "品类": ("mv_dept_daily", "dept_name")}
        tbl, col = dim_map[dim]
        sfilter = store_filter.replace('store_name', f'{tbl}.store_name') if 'mv_store' in tbl else ''
        trend_df = query(f"""
            SELECT {col}, submit_date, SUM(total_amt) as amt
            FROM {tbl} WHERE submit_date >= '{ds}' {sfilter}
            GROUP BY {col}, submit_date ORDER BY submit_date
        """, store_params if sfilter else None)
        top = query(f"""
            SELECT {col}, SUM(total_amt) as amt FROM {tbl}
            WHERE submit_date >= '{ds}' {sfilter}
            GROUP BY {col} ORDER BY amt DESC LIMIT {top_n}
        """, store_params if sfilter else None)
        trend_df = trend_df[trend_df[col].isin(top[col])]
        fig = px.line(trend_df, x='submit_date', y='amt', color=col, title=f'Top {top_n} {dim}日销售趋势', color_discrete_sequence=px.colors.qualitative.Set3)

    fig.update_layout(height=400, template='plotly_white')
    st.plotly_chart(fig, use_container_width=True)

# ==================== TAB 3: 业务预警 ====================
with T["⚠️ 异常监控"]:
    st.markdown("### ⚠️ 业务预警")

    # 1. 库存告急
    st.markdown("#### 📦 库存告急 (<30天)")
    inv_alert = query("""
        SELECT i.brand_name, i.location, i.stock_qty,
               COALESCE(s.month_qty,0) as month_qty,
               CASE WHEN COALESCE(s.month_qty,0)>0
                    THEN ROUND(i.stock_qty::numeric/(s.month_qty::numeric/31),0) ELSE 999 END as stock_days
        FROM inventory_snapshot i
        LEFT JOIN (SELECT brand_name, store_name, SUM(quantity) as month_qty
            FROM sales_detail WHERE submit_date>='{ds}' AND NOT is_return GROUP BY 1,2
        ) s ON i.brand_name=s.brand_name AND i.location=s.store_name
        WHERE i.snapshot_date='{de}' AND i.location NOT LIKE '%仓'
          AND COALESCE(s.month_qty,0)>0
    """)
    urgent = inv_alert[inv_alert['stock_days'] < 30]
    low = inv_alert[(inv_alert['stock_days'] >= 30) & (inv_alert['stock_days'] < 60)]

    c1, c2, c3 = st.columns(3)
    with c1: st.metric("🔴 紧急 (<30天)", len(urgent))
    with c2: st.metric("🟡 偏低 (30-60天)", len(low))
    with c3: st.metric("🟢 正常 (>60天)", len(inv_alert[inv_alert['stock_days']>=60]))

    if not urgent.empty:
        st.error(f"以下门店库存告急，需立即补货:")
        st.dataframe(urgent.rename(columns={'brand_name':'品牌','location':'门店','stock_qty':'库存','month_qty':'月销','stock_days':'可售天'}), use_container_width=True, hide_index=True)

    if not low.empty:
        st.warning(f"以下门店库存偏低:")
        st.dataframe(low.head(10).rename(columns={'brand_name':'品牌','location':'门店','stock_qty':'库存','month_qty':'月销','stock_days':'可售天'}), use_container_width=True, hide_index=True)

    # 2. 退货率监控
    st.markdown("#### 🔄 退货率趋势")
    return_daily = query("""
        SELECT submit_date,
            COALESCE(SUM(CASE WHEN is_return THEN ABS(settle_amount) ELSE 0 END), 0) as return_amt,
            COALESCE(SUM(CASE WHEN NOT is_return THEN settle_amount ELSE 0 END), 0) as sales_amt
        FROM sales_detail WHERE submit_date >= '{ds}'
        GROUP BY submit_date ORDER BY submit_date
    """)
    return_daily['return_rate'] = return_daily['return_amt'] / (return_daily['sales_amt'] + return_daily['return_amt']) * 100

    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(go.Bar(x=return_daily['submit_date'], y=return_daily['return_amt']/10000, name='退货额(万)', marker_color='#DC2626'), secondary_y=False)
    fig.add_trace(go.Scatter(x=return_daily['submit_date'], y=return_daily['return_rate'], name='退货率%', marker_color='#D97706', mode='lines+markers'), secondary_y=True)
    fig.add_hline(y=5, line_dash="dash", line_color="red", annotation_text="5%警戒线", secondary_y=True)
    fig.update_layout(title='每日退货监控', height=350, hovermode='x unified', template='plotly_white')
    st.plotly_chart(fig, use_container_width=True)

    # 3. 日销波动 Top10
    st.markdown("#### 📊 日销波动最大门店 (Top10)")
    volatility = query("""
        SELECT store_name, STDDEV(total_amt)/AVG(total_amt)*100 as cv, AVG(total_amt) as avg_amt
        FROM mv_store_daily WHERE submit_date >= '{ds}'
        {store_filter.replace('store_name','mv_store_daily.store_name')}
        GROUP BY store_name HAVING AVG(total_amt) > 0 ORDER BY cv DESC LIMIT 10
    """, store_params)
    if not volatility.empty:
        fig = px.bar(volatility, x='store_name', y='cv', title='日销变异系数 (CV%) — 越高越不稳定',
                     color='avg_amt', color_continuous_scale='reds',
                     labels={'cv':'波动率%','store_name':'门店','avg_amt':'日均销'})
        fig.update_layout(height=350, template='plotly_white')
        st.plotly_chart(fig, use_container_width=True)

    # 4. 预警日志
    st.markdown("#### 📋 最近预警记录")
    alerts = query("""
        SELECT r.rule_name, a.alert_time, a.description, a.metric_value, a.is_read
        FROM alert_log a LEFT JOIN alert_rules r ON a.rule_id = r.id
        ORDER BY a.alert_time DESC LIMIT 20
    """)
    if not alerts.empty:
        st.dataframe(alerts, use_container_width=True, hide_index=True)
    else:
        st.info("暂无预警记录。运行 alert_checker.py 生成预警。")

# ==================== TAB 4: 排行榜 ====================
with T["🏆 排行榜"]:
    st.markdown("### 🏆 排行榜")

    rank_dim = st.selectbox("排行维度", ["门店", "品牌", "品类", "单品", "营业员"], key="rank_dim")
    rank_metric = st.radio("指标", ["销售额", "毛利", "订单数"], horizontal=True)

    metric_map = {
        "销售额": "SUM(total_amt)", "毛利": "SUM(total_profit)", "订单数": "SUM(order_cnt)"
    }
    metric_sql = metric_map[rank_metric]

    if rank_dim == "门店":
        df = query(f"""SELECT store_name, {metric_sql} as val FROM mv_store_daily
            WHERE submit_date >= '{ds}' {store_filter.replace('store_name','mv_store_daily.store_name')}
            GROUP BY store_name ORDER BY val DESC LIMIT 20""", store_params)
    elif rank_dim == "品牌":
        df = query(f"SELECT brand_name, {metric_sql} as val FROM mv_brand_daily WHERE submit_date >= '{ds}' GROUP BY brand_name ORDER BY val DESC LIMIT 20")
    elif rank_dim == "品类":
        df = query(f"SELECT dept_name, {metric_sql} as val FROM mv_dept_daily WHERE submit_date >= '{ds}' GROUP BY dept_name ORDER BY val DESC")
    elif rank_dim == "单品":
        df = query("SELECT product_name, SUM(settle_amount) as val FROM sales_detail WHERE NOT is_return AND submit_date >= '{ds}' {store_filter} GROUP BY product_name ORDER BY val DESC LIMIT 20", store_params)
        df['product_name'] = df['product_name'].str[:30]
    else:  # 营业员
        df = query("SELECT salesperson, SUM(settle_amount) as val FROM sales_detail WHERE NOT is_return AND submit_date >= '{ds}' AND salesperson IS NOT NULL {store_filter} GROUP BY salesperson ORDER BY val DESC LIMIT 20", store_params)

    if not df.empty:
        col_name = df.columns[0]
        fig = px.bar(df, x='val', y=col_name, orientation='h', title=f'{rank_dim} — {rank_metric}', color='val', color_continuous_scale='oranges')
        fig.update_layout(height=500, yaxis={'categoryorder':'total ascending'}, template='plotly_white')
        st.plotly_chart(fig, use_container_width=True)

# ==================== TAB 5: 多维下钻 ====================
with T["🔍 多维下钻"]:
    st.markdown("### 🔍 多维下钻")

    drill = st.radio("下钻路径", ["品牌→门店→商品", "品类→品牌→商品"], horizontal=True)

    if drill == "品牌→门店→商品":
        brands = query("SELECT brand_name FROM dim_brand ORDER BY brand_name")['brand_name'].tolist()
        sel_brand = st.selectbox("1️⃣ 选择品牌", brands)
        brand_store = query("""
            SELECT store_name, SUM(settle_amount) as amt, SUM(gross_profit) as profit
            FROM sales_detail WHERE NOT is_return AND brand_name = %s AND submit_date >= '{ds}'
            GROUP BY store_name ORDER BY amt DESC LIMIT 15
        """, [sel_brand])
        if not brand_store.empty:
            fig = px.bar(brand_store, x='store_name', y='amt', title=f'{sel_brand} — 各门店销售额', color='profit', color_continuous_scale='greens')
            fig.update_layout(height=300, template='plotly_white')
            st.plotly_chart(fig, use_container_width=True)
            sel_store = st.selectbox("2️⃣ 选择门店", brand_store['store_name'].tolist())
            detail = query("""
                SELECT product_name, SUM(quantity) as qty, SUM(settle_amount) as amt
                FROM sales_detail WHERE NOT is_return AND brand_name=%s AND store_name=%s AND submit_date>='{ds}'
                GROUP BY product_name ORDER BY amt DESC LIMIT 20
            """, [sel_brand, sel_store])
            detail['product_name'] = detail['product_name'].str[:40]
            st.dataframe(detail, use_container_width=True, hide_index=True)
    else:
        depts = query("SELECT dept_name FROM dim_dept ORDER BY dept_name")['dept_name'].tolist()
        sel_dept = st.selectbox("1️⃣ 选择品类", depts)
        dept_brand = query("""
            SELECT brand_name, SUM(total_amt) as amt FROM mv_brand_daily
            WHERE dept_name = %s AND submit_date >= '{ds}'
            GROUP BY brand_name ORDER BY amt DESC LIMIT 10
        """, [sel_dept])
        if not dept_brand.empty:
            fig = px.treemap(dept_brand, path=['brand_name'], values='amt', title=f'{sel_dept} — 品牌分布')
            fig.update_layout(height=350, template='plotly_white')
            st.plotly_chart(fig, use_container_width=True)

# ==================== TAB 6: 月度环比 ====================
with T["📉 月度环比"]:
    st.markdown("### 📉 月度环比分析")
    st.info("环比分析需要至少2个月数据，当前仅有5月数据。导入6月数据后自动激活。")
    daily_df = query("""
        SELECT submit_date, SUM(total_amt) as amt FROM mv_store_daily
        WHERE submit_date >= '{ds}' GROUP BY submit_date ORDER BY submit_date
    """)
    fig = px.bar(daily_df, x='submit_date', y='amt', title=f'{ds}~{de} 每日销售额')
    fig.update_layout(height=350, template='plotly_white')
    st.plotly_chart(fig, use_container_width=True)

# ==================== TAB 7: 门店分析 ====================
with T["🏪 门店分析"]:
    st.markdown("### 🏪 门店分析")
    stores = query("SELECT store_name FROM dim_store ORDER BY store_name")['store_name'].tolist()
    sel_store2 = st.selectbox("选择门店", stores, key="store_detail")

    store_info = query("""
        SELECT submit_date, total_amt, total_profit, order_cnt, total_qty
        FROM mv_store_daily WHERE store_name=%s AND submit_date>='{ds}' ORDER BY submit_date
    """, [sel_store2])

    if not store_info.empty:
        s_amt = store_info['total_amt'].sum()
        s_profit = store_info['total_profit'].sum()
        s_orders = store_info['order_cnt'].sum()
        c1,c2,c3,c4 = st.columns(4)
        with c1: st.metric("月销售额", f"¥{s_amt/10000:.1f}万")
        with c2: st.metric("月毛利", f"¥{s_profit/10000:.1f}万", f"{s_profit/s_amt*100:.1f}%")
        with c3: st.metric("订单数", f"{s_orders:,}")
        with c4: st.metric("客单价", f"¥{s_amt/s_orders:.0f}" if s_orders else "N/A")

        fig = make_subplots(specs=[[{"secondary_y": True}]])
        fig.add_trace(go.Bar(x=store_info['submit_date'], y=store_info['total_amt']/10000, name='日销(万)'), secondary_y=False)
        fig.add_trace(go.Scatter(x=store_info['submit_date'], y=store_info['total_profit']/store_info['total_amt']*100, name='毛利率%', mode='lines+markers', marker_color='green'), secondary_y=True)
        fig.update_layout(title=f'{sel_store2} 日销售趋势', height=350, template='plotly_white')
        st.plotly_chart(fig, use_container_width=True)

        cc1, cc2 = st.columns(2)
        with cc1:
            dept_df = query("SELECT dept_name, SUM(settle_amount) as amt FROM sales_detail WHERE NOT is_return AND store_name=%s AND submit_date>='{ds}' GROUP BY dept_name ORDER BY amt DESC", [sel_store2])
            fig = px.pie(dept_df, values='amt', names='dept_name', title='品类结构')
            fig.update_layout(height=300, template='plotly_white')
            st.plotly_chart(fig, use_container_width=True)
        with cc2:
            brand_df = query("SELECT brand_name, SUM(settle_amount) as amt FROM sales_detail WHERE NOT is_return AND store_name=%s AND submit_date>='{ds}' GROUP BY brand_name ORDER BY amt DESC LIMIT 10", [sel_store2])
            fig = px.bar(brand_df, x='brand_name', y='amt', title='Top10品牌', color='amt', color_continuous_scale='oranges')
            fig.update_layout(height=300, template='plotly_white')
            st.plotly_chart(fig, use_container_width=True)

# ==================== TAB 8: 品牌分析 ====================
with T["🏷️ 品牌分析"]:
    st.markdown("### 🏷️ 品牌分析")
    brand_summary = query("""
        SELECT brand_name, SUM(total_amt) as amt, SUM(total_profit) as profit,
               SUM(order_cnt) as orders, MAX(store_cnt) as stores
        FROM mv_brand_daily WHERE submit_date >= '{ds}'
        GROUP BY brand_name ORDER BY amt DESC
    """)
    brand_summary['margin'] = brand_summary['profit'] / brand_summary['amt'] * 100
    brand_summary['pct'] = brand_summary['amt'] / brand_summary['amt'].sum() * 100

    c1,c2,c3 = st.columns(3)
    with c1: st.metric("品牌总数", len(brand_summary))
    with c2: st.metric("Top10占比", f"{brand_summary['pct'].head(10).sum():.1f}%")
    with c3: st.metric("Top3品牌", ", ".join(brand_summary['brand_name'].head(3).tolist()))

    fig = px.bar(brand_summary.head(30), x='brand_name', y='amt', title='品牌销售额排行 (Top30)', color='margin', color_continuous_scale='RdYlGn')
    fig.update_layout(height=450, template='plotly_white')
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("**品牌日趋势对比**")
    all_brands = query("SELECT brand_name FROM dim_brand ORDER BY brand_name")['brand_name'].tolist()
    sel_brands = st.multiselect("选择品牌 (最多5个)", all_brands, default=['JBC女', 'JBC男', 'JBC童鞋'], max_selections=5)
    if sel_brands:
        cdf = query(f"SELECT brand_name, submit_date, SUM(total_amt) as amt FROM mv_brand_daily WHERE submit_date >= '{{ds}}' AND brand_name IN ({','.join(['%s']*len(sel_brands))}) GROUP BY brand_name, submit_date ORDER BY submit_date", sel_brands)
        fig = px.line(cdf, x='submit_date', y='amt', color='brand_name', title='品牌日销售趋势对比')
        fig.update_layout(height=400, template='plotly_white')
        st.plotly_chart(fig, use_container_width=True)

# ==================== TAB 9: 商品分析 ====================
with T["📦 商品分析"]:
    st.markdown("### 📦 商品分析")
    prod_tab = st.radio("商品视角", ["爆款排行", "新品追踪", "库存分析"], horizontal=True)

    if prod_tab == "爆款排行":
        hot = query("""SELECT product_name, SUM(quantity) as qty, SUM(settle_amount) as amt, COUNT(DISTINCT store_name) as stores
            FROM sales_detail WHERE NOT is_return AND submit_date >= '{ds}' {store_filter}
            AND product_name NOT IN (SELECT store_name FROM dim_store)
            AND product_name NOT LIKE '%租赁%' AND product_name NOT LIKE '%联营%'
            AND product_name !~ '[0-9]{1,2}%'
            AND LENGTH(product_name) >= 6
            GROUP BY product_name ORDER BY amt DESC LIMIT 30""", store_params)
        hot['product_name'] = hot['product_name'].str[:40]
        hot['avg_price'] = hot['amt'] / hot['qty']
        st.dataframe(hot, use_container_width=True, hide_index=True, column_config={'product_name':'商品','qty':'销量','amt':'销售额','stores':'门店','avg_price':'均价'})
    elif prod_tab == "新品追踪":
        new_prods = query("""SELECT p.launch_date, p.brand_name, p.product_name, p.season, COALESCE(s.sales,0) as sales, COALESCE(s.qty,0) as qty
            FROM prod_launch p LEFT JOIN (SELECT product_name, SUM(settle_amount) as sales, SUM(quantity) as qty FROM sales_detail WHERE submit_date >= '{ds}' AND NOT is_return GROUP BY product_name) s ON p.product_name = s.product_name
            ORDER BY sales DESC""")
        st.metric("上市新品", len(new_prods)); st.metric("有销售新品", (new_prods['sales']>0).sum())
        new_prods['product_name'] = new_prods['product_name'].str[:35]
        st.dataframe(new_prods.head(30), use_container_width=True, hide_index=True)
    else:
        inv = query("""SELECT i.brand_name, i.location, i.stock_qty, COALESCE(s.month_qty,0) as month_qty,
            CASE WHEN COALESCE(s.month_qty,0)>0 THEN ROUND(i.stock_qty::numeric/(s.month_qty::numeric/31),0) ELSE 999 END as stock_days
            FROM inventory_snapshot i LEFT JOIN (SELECT brand_name, store_name, SUM(quantity) as month_qty FROM sales_detail WHERE submit_date >= '{ds}' AND NOT is_return GROUP BY brand_name, store_name) s
            ON i.brand_name = s.brand_name AND i.location = s.store_name WHERE i.snapshot_date = '{de}' ORDER BY stock_days ASC""")
        if not inv.empty:
            urgent = inv[inv['stock_days'] < 30]
            low = inv[(inv['stock_days'] >= 30) & (inv['stock_days'] < 60)]
            c1,c2,c3 = st.columns(3)
            with c1: st.metric("⚠️ 紧急(<30天)", len(urgent))
            with c2: st.metric("⚡ 偏低(30-60天)", len(low))
            with c3: st.metric("✅ 正常(>60天)", len(inv)-len(urgent)-len(low))
            inv_display = inv.head(30).copy()
            inv_display['状态'] = inv_display['stock_days'].apply(lambda x: '🔴' if x<30 else ('🟡' if x<60 else '🟢'))
            inv_display['stock_days'] = inv_display['stock_days'].apply(lambda x: f'{int(x)}天')
            st.dataframe(inv_display, use_container_width=True, hide_index=True)

# ==================== TAB 10: 实时预警 ====================
with T["🔔 实时预警"]:
    st.markdown("### 🔔 实时预警")

    # 运行检查按钮
    c1, c2 = st.columns([1, 3])
    with c1:
        if st.button("🔍 运行预警检查", type="primary", use_container_width=True):
            import subprocess
            result = subprocess.run(['python3', '/home/openclaw/.openclaw/workspace/alert_checker.py'], capture_output=True, text=True)
            st.text(result.stdout)
            if result.returncode == 0:
                st.success("✅ 检查完成")
                st.rerun()
    with c2:
        st.caption("检查库存告急、退货率异常、日销骤降/暴增等")

    st.divider()

    # 预警日志
    st.markdown("**📋 预警历史**")
    alerts = query("""SELECT r.rule_name, a.alert_time, a.metric_value, a.threshold_value, a.description, a.is_read
        FROM alert_log a LEFT JOIN alert_rules r ON a.rule_id = r.id ORDER BY a.alert_time DESC LIMIT 50""")
    if not alerts.empty:
        c1,c2,c3 = st.columns(3)
        with c1: st.metric("总预警", len(alerts))
        with c2: st.metric("未读", alerts['is_read'].sum() if 'is_read' in alerts.columns else 0)
        with c3: st.metric("今日", len(alerts[pd.to_datetime(alerts['alert_time']).dt.date == pd.Timestamp.now().date()]) if not alerts.empty else 0)
        st.dataframe(alerts, use_container_width=True, hide_index=True)
    else:
        st.info("暂无预警记录，点击上方按钮运行检查")

    # 规则配置
    with st.expander("⚙️ 预警规则配置"):
        rules = query("SELECT * FROM alert_rules")
        if rules.empty:
            c = psycopg2.connect(PG_DSN); cur = c.cursor()
            cur.executemany("INSERT INTO alert_rules (rule_name, metric, dimension, condition, threshold, compare_period) VALUES (%s,%s,%s,%s,%s,%s)", [
                ('日销售额骤降', 'daily_sales', 'store', 'drop_below', 50, '1_day'),
                ('日销售额暴增', 'daily_sales', 'store', 'spike_above', 200, '1_day'),
                ('库存告急', 'stock_days', 'store', 'lt', 30, '1_day'),
                ('退货率异常', 'return_rate', 'overall', 'gt', 5, '1_day'),
            ])
            c.commit(); cur.close(); c.close()
            st.rerun()
        st.dataframe(rules, use_container_width=True, hide_index=True,
            column_config={'id':'ID','rule_name':'规则名称','metric':'监控指标','dimension':'维度','condition':'条件','threshold':'阈值','compare_period':'对比周期','is_enabled':'启用'})

# ==================== TAB 11: 用户管理 ====================
with T["👥 用户管理"]:
    st.markdown("### 👥 用户管理")
    if not is_admin():
        st.warning("仅管理员可访问")
    else:
        from auth_jbc import get_all_users, add_user as au, update_user as uu, toggle_user_active as tua
        users = get_all_users()
        for u in users:
            uid, uname, role, dname, stores, brands, htabs, active = u
            with st.expander(f"{'🟢' if active else '🔴'} {dname or uname} ({role})"):
                st.write(f"用户名: {uname} | 状态: {'启用' if active else '禁用'}")
                if st.button(f"{'禁用' if active else '启用'}", key=f"toggle_{uid}"):
                    tua(uid); st.rerun()

        with st.expander("➕ 新增用户"):
            nu = st.text_input("用户名"); np = st.text_input("密码", type="password")
            nr = st.selectbox("角色", ["viewer", "editor", "admin"])
            nd = st.text_input("显示名称")
            ns = st.text_area("授权门店 (每行一个，空=全部)")
            if st.button("创建"):
                if nu and np:
                    sl = [s.strip() for s in ns.split('\n') if s.strip()] if ns else None
                    au(nu, np, nr, nd, sl); st.success("创建成功"); st.rerun()
                else:
                    st.error("用户名密码必填")

# ==================== TAB 12: 数据导入 ====================
with T["📋 数据导入"]:
    st.markdown("### 📋 数据导入")
    if not is_admin() and user.get('role') != 'editor':
        st.warning("仅管理员/编辑者可用")
    else:
        counts = query("""SELECT '交易明细' as t, COUNT(*)::text FROM sales_detail
            UNION ALL SELECT '日汇总', COUNT(*)::text FROM sales_daily
            UNION ALL SELECT '库存', COUNT(*)::text FROM inventory_snapshot
            UNION ALL SELECT '上市商品', COUNT(*)::text FROM prod_launch
            UNION ALL SELECT '品牌日聚合', COUNT(*)::text FROM mv_brand_daily
            UNION ALL SELECT '门店日聚合', COUNT(*)::text FROM mv_store_daily""")
        st.dataframe(counts, use_container_width=True, hide_index=True)
        if st.button("🔄 刷新物化视图"):
            c = psycopg2.connect(PG_DSN); cur = c.cursor()
            for mv in ['mv_brand_daily', 'mv_store_daily', 'mv_dept_daily']:
                cur.execute(f"REFRESH MATERIALIZED VIEW {mv}")
            c.commit(); cur.close(); c.close()
            st.success("已刷新"); st.rerun()

st.markdown("---")
st.caption(f"金佰川运营数据看板 v1.0 | {user.get('display_name','')} | PostgreSQL 16 | 54门店 109品牌")
