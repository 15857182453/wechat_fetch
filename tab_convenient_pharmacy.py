#!/usr/bin/env python3
"""便捷配药数据统计 - 独立测试页"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go

st.set_page_config(page_title="便捷配药数据统计", layout="wide")

EXCEL_PATH = '/mnt/c/Users/44238/Desktop/业务对账数据/对账业务总表/新流水2026.xlsx'

@st.cache_data(ttl=300)
def load_data():
    df = pd.read_excel(EXCEL_PATH, header=None, skiprows=4)
    data = []
    for _, row in df.iterrows():
        date_val = row.iloc[0]
        flow_val = row.iloc[3]  # 处方服务(便捷购药) 流水
        order_val = row.iloc[4]  # 处方服务(便捷购药) 订单
        # 过滤：日期必须是有效的日期格式
        if pd.notna(date_val) and pd.notna(flow_val):
            try:
                dt = pd.to_datetime(date_val)
                if dt.year != 2026:
                    continue
                data.append({
                    '日期': dt.strftime('%Y-%m-%d'),
                    '流水': float(flow_val),
                    '订单': int(order_val) if pd.notna(order_val) else 0
                })
            except:
                pass
    df = pd.DataFrame(data)
    df['日期'] = pd.to_datetime(df['日期'])
    return df

df = load_data()

if df.empty:
    st.warning("⚠️ 暂无2026年便捷购药数据")
    st.stop()

# ========== 页面标题 ==========
st.markdown('<div style="text-align:center"><h2>💊 便捷配药数据统计</h2></div>', unsafe_allow_html=True)
st.divider()

# ========== 顶部 KPI ==========
total_flow = df['流水'].sum()
total_orders = df['订单'].sum()

kpi1, kpi2, kpi3, kpi4 = st.columns(4)
with kpi1:
    st.metric("💰 今年总流水", f"¥{total_flow:,.0f} 元")
with kpi2:
    st.metric("🎫 今年总订单", f"{total_orders:,} 单")
with kpi3:
    avg = total_flow / total_orders if total_orders > 0 else 0
    st.metric("🏷️ 平均客单价", f"¥{avg:.2f}")
with kpi4:
    st.metric("📅 数据天数", f"{len(df)} 天")

st.divider()

# ========== 图表 1: 2026年便捷购药统计（总） ==========
st.markdown("### 📈 2026年便捷购药统计（总）")

fig = go.Figure()

# 折线 - 流水（左轴）
fig.add_trace(go.Scatter(
    x=df['日期'], y=df['流水'],
    name='流水 (元)',
    mode='lines+markers',
    line=dict(color='#FF6B6B', width=2.5),
    marker=dict(size=4),
    hovertemplate='<b>%{x|%Y-%m-%d}</b><br>流水: ¥%{y:,.2f}<extra></extra>'
))

# 折线 - 订单（右轴）
fig.add_trace(go.Scatter(
    x=df['日期'], y=df['订单'],
    name='订单数',
    mode='lines+markers',
    line=dict(color='#4ECDC4', width=2.5),
    marker=dict(size=4),
    yaxis='y2',
    hovertemplate='<b>%{x|%Y-%m-%d}</b><br>订单: %{y:,.0f}单<extra></extra>'
))

fig.update_layout(
    template='plotly_white',
    height=420,
    xaxis_title='日期',
    yaxis=dict(title='流水 (元)', title_font=dict(color='#FF6B6B'), tickfont=dict(color='#FF6B6B')),
    yaxis2=dict(title='订单数', title_font=dict(color='#4ECDC4'), tickfont=dict(color='#4ECDC4'),
                overlaying='y', side='right', showgrid=False),
    hovermode='x unified',
    legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='center', x=0.5)
)
st.plotly_chart(fig, use_container_width=True)

# ========== 近 15 日明细表 ==========
st.markdown("### 📋 近 15 日明细")

df_recent = df.tail(15).copy()
df_recent['日期'] = df_recent['日期'].dt.strftime('%Y-%m-%d')
df_recent = df_recent.rename(columns={'流水': '流水 (元)', '订单': '订单数'})

st.dataframe(
    df_recent.style.format({'流水 (元)': '¥{:,.2f}'}),
    use_container_width=True,
    hide_index=True,
    height=480
)
