#!/usr/bin/env python3
"""医院运营数据仪表板 — NiceGUI 版本（Demo）。

仅实现 Tab 1 总览页，验证 NiceGUI UI 效果。
"""

import sqlite3
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
from nicegui import ui

DB_PATH = "/home/openclaw/.openclaw/workspace/business_flow.db"

# ── 数据加载 ──

def load_hospital_data():
    """加载医院运营数据（明细表 UNION ALL）。"""
    conn = sqlite3.connect(DB_PATH)
    table_names = [
        'daily_flow_2025', 'daily_flow_2026_jan', 'daily_flow_2026_feb',
        'daily_flow_2026_mar', 'daily_flow_2026_apr', 'daily_flow_2026_may',
    ]
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
                  AND yewu_wancheng_shijian IS NOT NULL
                  AND yewu_wancheng_shijian != ''
                  AND yewu_wancheng_shijian != 'NaT'
                  AND amount IS NOT NULL
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


def load_latest_summary():
    """从 duizhang_summary_2026 获取最新日期和总流水。"""
    conn = sqlite3.connect(DB_PATH)
    r = conn.execute(
        "SELECT MAX(date) FROM duizhang_summary_2026 WHERE date < date('now') AND daily_total_flow > 0"
    ).fetchone()
    latest = r[0] if r and r[0] else None
    if latest:
        rows = conn.execute(
            "SELECT date, daily_total_flow FROM duizhang_summary_2026 "
            "WHERE date >= date('now','-30 days') AND date <= ? AND daily_total_flow > 0 "
            "ORDER BY date", (latest,)
        ).fetchall()
    else:
        rows = []
    conn.close()
    return latest, rows


# ── UI 组件 ──

def kpi_card(label: str, value: str, delta: str = "", delta_up: bool = False):
    """自定义 KPI 卡片。"""
    color = '#059669' if delta_up else ('#dc2626' if delta and delta[0] == '-' else '#a3a3a3')
    arrow = '↑' if delta_up else ('↓' if delta and delta[0] == '-' else '')
    with ui.card().classes('w-full no-shadow'):
        with ui.row().classes('w-full items-center justify-between'):
            ui.label(label).classes('text-sm text-grey-7 font-medium')
            ui.html(f'<div style="font-size:2em;font-weight:700;font-family:\'SF Mono\',monospace;line-height:1.1">{value}</div>')
        if delta:
            ui.html(f'<div style="font-size:0.8em;color:{color};text-align:right">{arrow} {delta}</div>')


def apply_plotly_style(fig, title=None):
    """统一 Plotly 样式。"""
    fig.update_layout(
        template='plotly_white',
        plot_bgcolor='#ffffff',
        paper_bgcolor='#ffffff',
        font={'family': '-apple-system, sans-serif', 'color': '#737373'},
        xaxis={'gridcolor': '#f0f0f0', 'zerolinecolor': '#e5e5e5'},
        yaxis={'gridcolor': '#f0f0f0', 'zerolinecolor': '#e5e5e5'},
        colorway=['#4361ee', '#059669', '#dc2626', '#d97706', '#7c3aed', '#0891b2'],
        margin={'l': 50, 'r': 20, 't': 40, 'b': 50},
        hoverlabel={'bgcolor': '#1a1a2e', 'font': {'color': '#ffffff'}},
    )
    if title:
        fig.update_layout(title={'text': title, 'font': {'size': 14, 'color': '#171717'}})
    return fig


# ── 页面 ──

# 自定义 CSS
ui.add_head_html("""
<style>
    .no-shadow { box-shadow: none !important; border: 1px solid #e5e5e5 !important; }
    .nav-bar { background: #1a1a2e; color: #fff; padding: 0 24px; height: 56px; display: flex; align-items: center; justify-content: space-between; }
    .nav-title { font-size: 1.15em; font-weight: 700; letter-spacing: -0.01em; }
    .nav-sub { font-size: 0.8em; color: #a3a3a3; }
    .section-title { font-size: 1.1em; font-weight: 600; color: #171717; border-bottom: 1px solid #e5e5e5; padding-bottom: 10px; margin-bottom: 16px; }
</style>
""")

# 顶部导航
with ui.row().classes('w-full no-wrap items-center').style('background:#1a1a2e;color:#fff;padding:0 24px;height:56px'):
    with ui.column().classes('gap-0'):
        ui.label('运营数据仪表板').classes('text-white font-bold').style('font-size:1.15em;letter-spacing:-0.01em')
        ui.label('实时监控业务表现 · 智能异常预警').style('font-size:0.8em;color:#a3a3a3')
    ui.space()
    _now = datetime.now().strftime('%Y-%m-%d %H:%M')
    ui.label(f'数据更新: {_now}').style('font-size:0.8em;color:#a3a3a3')

# 数据
df = load_hospital_data()
if df.empty:
    ui.label('暂无数据').classes('text-2xl text-center mt-20 text-grey')
else:
    hospital_list = sorted(df['医院'].unique())
    max_date = pd.to_datetime(df['日期'].max()).date()
    min_date = pd.to_datetime(df['日期'].min()).date()

    with ui.row().classes('w-full gap-4 items-start'):
        # 左侧栏 — 筛选
        with ui.column().classes('w-64 gap-4 mt-4'):
            ui.label('筛选').classes('section-title')

            hospitals_sel = ui.select(
                options={h: h for h in hospital_list},
                multiple=True,
                value=[],
                label='医院'
            ).classes('w-full')

            date_sel = ui.date(value=str(max_date)).classes('w-full')

            ui.label('').classes('text-sm text-grey-7')
            date_label = ui.label(f'范围: {min_date} ~ {max_date}')

        # 右侧 — 主内容
        with ui.column().classes('flex-1 gap-6 mt-4'):

            # 日期切换回调
            def on_date_change():
                sel_date = date_sel.value
                sel_hospitals = hospitals_sel.value or hospital_list
                refresh(sel_date, sel_hospitals)

            hospitals_sel.on('update:model-value', on_date_change)
            date_sel.on('update:model-value', on_date_change)

            # KPI 行
            kpi_row = ui.row().classes('w-full gap-4')

            # 图表区域
            chart_row = ui.row().classes('w-full gap-4')

            # 表格区域
            table_cont = ui.column().classes('w-full gap-2')

            def refresh(sel_date, sel_hospitals):
                """刷新页面内容。"""
                df_filtered = df[df['医院'].isin(sel_hospitals)]
                df_date = df_filtered[df_filtered['日期'] == sel_date]

                # 前一天
                prev_dt = pd.to_datetime(sel_date) - timedelta(days=1)
                prev_str = prev_dt.strftime('%Y-%m-%d')
                df_prev = df_filtered[df_filtered['日期'] == prev_str]

                total_orders = int(df_date['订单数'].sum()) if not df_date.empty else 0
                total_amount = float(df_date['金额'].sum()) if not df_date.empty else 0
                avg_amount = float(df_date['客单价'].mean()) if not df_date.empty else 0
                active = len(df_date) if not df_date.empty else 0

                prev_orders = int(df_prev['订单数'].sum()) if not df_prev.empty else 0
                prev_amount = float(df_prev['金额'].sum()) if not df_prev.empty else 0

                def fmt_delta(curr, prev):
                    if prev == 0:
                        return '', False
                    diff = curr - prev
                    pct = diff / prev * 100
                    return f'{pct:+.1f}%', diff > 0

                od, ou = fmt_delta(total_orders, prev_orders)
                ad, au = fmt_delta(total_amount, prev_amount)

                # 清除旧 KPI
                kpi_row.clear()
                with kpi_row:
                    kpi_card('日总订单', f'{total_orders:,}', od, ou)
                    kpi_card('日总流水', f'¥{total_amount:,.0f}', ad, au)
                    kpi_card('客单价', f'¥{avg_amount:.2f}')
                    kpi_card('覆盖医院', f'{active} 家')

                # 图表
                chart_row.clear()
                with chart_row:
                    if not df_date.empty:
                        import plotly.express as px
                        fig = px.bar(
                            df_date.sort_values('金额', ascending=False),
                            x='医院', y='金额', title='当日医院流水',
                            color='金额', color_continuous_scale='Blues',
                            text='金额'
                        )
                        fig.update_traces(texttemplate='¥%{text:,.0f}', textposition='auto')
                        apply_plotly_style(fig)
                        fig.update_layout(xaxis_tickangle=-30)
                        ui.plotly(fig).classes('w-1/2')

                        fig2 = px.pie(
                            df_date, values='订单数', names='医院', title='订单占比'
                        )
                        apply_plotly_style(fig2)
                        fig2.update_layout(colorway=['#4361ee', '#059669', '#d97706', '#dc2626', '#7c3aed', '#0891b2'])
                        ui.plotly(fig2).classes('w-1/2')

                # 表格
                table_cont.clear()
                with table_cont:
                    ui.label('医院明细').classes('section-title')
                    if not df_date.empty:
                        df_show = df_date[['医院', '订单数', '金额', '客单价']].round(2)
                        ui.table(
                            columns=[
                                {'name': '医院', 'label': '医院', 'field': '医院'},
                                {'name': '订单数', 'label': '订单数', 'field': '订单数'},
                                {'name': '金额', 'label': '金额', 'field': '金额'},
                                {'name': '客单价', 'label': '客单价', 'field': '客单价'},
                            ],
                            rows=df_show.to_dict('records'),
                            pagination={'rowsPerPage': 15},
                        ).classes('w-full')

            # 首次渲染
            refresh(str(max_date), hospital_list)

ui.run(
    title='运营数据仪表板',
    port=8503,
    reload=False,
    dark=False,
)
