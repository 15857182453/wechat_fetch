#!/usr/bin/env python3
"""邵逸夫医院 便捷购药处方快递费 数据报告 - 跟随4月月报模板"""
import sqlite3, pandas as pd, numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.font_manager import FontProperties, fontManager
from matplotlib.gridspec import GridSpec
import matplotlib.dates as mdates
from datetime import datetime, timedelta

font_path = '/home/openclaw/.local/share/fonts/simhei.ttf'
fp = FontProperties(fname=font_path); fpb = FontProperties(fname=font_path, weight='bold')
fontManager.addfont(font_path)
plt.rcParams['font.family']='sans-serif'; plt.rcParams['font.sans-serif']=['SimHei']; plt.rcParams['axes.unicode_minus']=False

BG='#f4f6f9'; CARD='#ffffff'; BLUE='#2563eb'; BLUE_L='#93c5fd'
RED='#ef4444'; GREEN='#22c55e'; ORANGE='#f59e0b'; PURPLE='#8b5cf6'; CYAN='#06b6d4'; PINK='#ec4899'; LIME='#84cc16'
TEXT_D='#1e293b'; TEXT_M='#475569'; TEXT_L='#94a3b8'; GRID='#e2e8f0'; BORDER='#cbd5e1'

conn = sqlite3.connect('business_flow.db')
cur = conn.cursor()

# Get 2 weeks data (Apr 22 - May 6)
tables = ['daily_flow_2026_apr', 'daily_flow_2026_may']
all_rows = []
for t in tables:
    cur.execute(f'''SELECT substr(yewu_wancheng_shijian,1,10) as dt,
        COUNT(*) as orders, SUM(amount) as amount
        FROM {t}
        WHERE yewu_wancheng_shijian IS NOT NULL AND yewu_wancheng_shijian != "" AND yewu_wancheng_shijian != "NaT"
        AND yewu_leixing = "处方快递费" AND ye_wu_lei_mu LIKE "%处方%"
        AND institution LIKE "%邵逸夫%"
        AND substr(yewu_wancheng_shijian,1,10) >= "2026-04-22"
        GROUP BY dt ORDER BY dt''')
    all_rows.extend(cur.fetchall())

seen = {}
for r in all_rows:
    seen[r[0]] = (r[1], r[2])
dates_sorted = sorted(seen.keys())
dates = [datetime.strptime(d, '%Y-%m-%d') for d in dates_sorted]
orders = [seen[d][0] for d in dates_sorted]
amounts = [seen[d][1] for d in dates_sorted]

total_orders = sum(orders)
total_amount = sum(amounts)
avg_daily_orders = total_orders / len(orders)
avg_daily_amount = total_amount / len(orders)

# Period analysis
pre_idx = [i for i, d in enumerate(dates_sorted) if d < '2026-05-01']
holiday_idx = [i for i, d in enumerate(dates_sorted) if '2026-05-01' <= d <= '2026-05-03']
post_idx = [i for i, d in enumerate(dates_sorted) if d >= '2026-05-04']

pre_orders = sum(orders[j] for j in pre_idx); pre_amount = sum(amounts[j] for j in pre_idx); pre_days = len(pre_idx)
hol_orders = sum(orders[j] for j in holiday_idx); hol_amount = sum(amounts[j] for j in holiday_idx); hol_days = len(holiday_idx)
post_orders = sum(orders[j] for j in post_idx); post_amount = sum(amounts[j] for j in post_idx); post_days = len(post_idx)

print(f'数据: {len(dates)}天, 总{total_orders}单, ¥{total_amount:,.0f}')
print(f'  节前: {pre_days}天 {pre_orders}单 ¥{pre_amount:,.0f}')
print(f'  假期: {hol_days}天 {hol_orders}单 ¥{hol_amount:,.0f}')
print(f'  节后: {post_days}天 {post_orders}单 ¥{post_amount:,.0f}')

# Create report
fig = plt.figure(figsize=(10, 45), facecolor=BG)
gs = GridSpec(15, 2, figure=fig, hspace=0.5, wspace=0.3, left=0.07, right=0.93, top=0.985, bottom=0.006,
    height_ratios=[0.55, 0.42, 0.85, 0.78, 0.65, 0.78, 0.65, 0.78, 0.72, 0.65, 0.78, 0.65, 1.2, 1.8, 0.16])

def sax(ax, title=''):
    ax.set_facecolor(CARD)
    for s in ax.spines.values(): s.set_color(BORDER); s.set_linewidth(0.5)
    ax.spines['top'].set_visible(False); ax.spines['right'].set_visible(False)
    ax.tick_params(colors=TEXT_M, labelsize=7.5)
    ax.grid(axis='y', alpha=0.4, color=GRID, linewidth=0.5)
    if title:
        ax.set_title(title, fontsize=12, fontweight='bold', color=TEXT_D, fontproperties=fpb, pad=10, loc='left')

# 0 Title
ax = fig.add_subplot(gs[0, :]); ax.set_xlim(0, 10); ax.set_ylim(0, 3); ax.axis('off')
for i in range(200):
    y = i / 200 * 3; t = i / 200
    ax.axhspan(y, y + 0.02, facecolor=(0.12*(1-t)+0.15*t, 0.23*(1-t)+0.39*t, 0.37*(1-t)+0.92*t), alpha=0.95)
ax.plot([3, 7], [0.35, 0.35], color='white', linewidth=0.8, alpha=0.3)
ax.text(5, 2.35, '2026年4月22日 - 5月6日', fontsize=14, color='#93c5fd', ha='center', fontproperties=fp, alpha=0.9)
ax.text(5, 1.65, '邵逸夫医院 便捷购药数据报告', fontsize=28, fontweight='bold', color='white', ha='center', fontproperties=fpb)
ax.text(5, 0.9, '运营平台部  /  数据分析', fontsize=12, color='#bfdbfe', ha='center', fontproperties=fp)
ax.text(5, 0.55, '统计范围  2026.04.22 - 05.06    共15天', fontsize=9, color='#93c5fd', ha='center', fontproperties=fp, alpha=0.8)

# 1 KPI
ax = fig.add_subplot(gs[1, :]); ax.set_xlim(0, 10); ax.set_ylim(0, 2.2); ax.axis('off')
for i, (label, val, sub, badge, color, bg, bc) in enumerate([
    ('总订单', f'{total_orders:,}单', f'日均{avg_daily_orders:.0f}单', '', BLUE, '#eff6ff', TEXT_L),
    ('总快递费', f'{total_amount:,.0f}元', f'日均{avg_daily_amount:,.0f}元', '', '#0891b2', '#ecfeff', TEXT_L),
    ('最高单日', f'{max(orders)}单', f'{dates_sorted[orders.index(max(orders))]}', f'¥{max(amounts):,.0f}', GREEN, '#f0fdf4', TEXT_L),
    ('最低单日', f'{min(orders)}单', f'{dates_sorted[orders.index(min(orders))]}', f'¥{min(amounts):,.0f}', RED, '#fef2f2', TEXT_L),
]):
    x = 0.15 + i * 2.5
    ax.add_patch(mpatches.FancyBboxPatch((x, 0.15), 2.2, 1.85, boxstyle="round,pad=0.12", facecolor=bg, edgecolor=BORDER, linewidth=0.8))
    ax.add_patch(mpatches.Rectangle((x + 0.02, 0.3), 0.06, 1.55, facecolor=color, alpha=0.8))
    ax.text(x + 1.2, 1.65, label, fontsize=9, color=TEXT_L, ha='center', fontproperties=fp)
    ax.text(x + 1.2, 1.1, val, fontsize=20, fontweight='bold', color=color, ha='center', fontproperties=fpb)
    ax.text(x + 1.2, 0.6, sub, fontsize=7.5, color=TEXT_L, ha='center', fontproperties=fp)
    if badge:
        ax.text(x + 1.2, 0.3, badge, fontsize=8, fontweight='bold', color=bc, ha='center', fontproperties=fpb)

# 2 Daily orders trend
ax = fig.add_subplot(gs[2, :]); sax(ax, '每日订单趋势')
colors1 = [GREEN if orders[i] >= avg_daily_orders else BLUE_L for i in range(len(orders))]
ax.bar(range(len(dates)), orders, color=colors1, edgecolor='white', width=0.6, alpha=0.9)
ax.axhline(y=avg_daily_orders, color=RED, linestyle='--', linewidth=1.5, alpha=0.6, label=f'日均 {avg_daily_orders:.0f}单')
for i, o in enumerate(orders):
    ax.text(i, o + max(orders)*0.02, str(o), ha='center', va='bottom', fontsize=7.5, color=TEXT_D, fontweight='bold', fontproperties=fp)
ax.set_xticks(range(len(dates)))
ax.set_xticklabels([d.strftime('%m/%d') for d in dates], rotation=30, ha='right', fontsize=7.5, fontproperties=fp)
ax.set_ylabel('订单量（单）', fontsize=9, color=TEXT_M, fontproperties=fp)
ax.legend(prop=fp, fontsize=8, framealpha=0.9)
ax.set_ylim(0, max(orders) * 1.2)
ax.grid(axis='y', alpha=0.4, color=GRID, linewidth=0.5)
for s in ax.spines.values(): s.set_color(BORDER)
ax.spines['top'].set_visible(False); ax.spines['right'].set_visible(False)

# 3 Daily amount
ax = fig.add_subplot(gs[3, :]); sax(ax, '每日快递费趋势（元）')
colors2 = [GREEN if amounts[i] >= avg_daily_amount else BLUE_L for i in range(len(amounts))]
ax.bar(range(len(dates)), amounts, color=colors2, edgecolor='white', width=0.6, alpha=0.9)
ax.axhline(y=avg_daily_amount, color=RED, linestyle='--', linewidth=1.5, alpha=0.6, label=f'日均 ¥{avg_daily_amount:,.0f}')
for i, a in enumerate(amounts):
    ax.text(i, a + max(amounts)*0.02, f'{a:,.0f}', ha='center', va='bottom', fontsize=7, color=TEXT_D, fontweight='bold', fontproperties=fp)
ax.set_xticks(range(len(dates)))
ax.set_xticklabels([d.strftime('%m/%d') for d in dates], rotation=30, ha='right', fontsize=7.5, fontproperties=fp)
ax.set_ylabel('金额（元）', fontsize=9, color=TEXT_M, fontproperties=fp)
ax.legend(prop=fp, fontsize=8, framealpha=0.9)
ax.set_ylim(0, max(amounts) * 1.2)
ax.grid(axis='y', alpha=0.4, color=GRID, linewidth=0.5)
for s in ax.spines.values(): s.set_color(BORDER)
ax.spines['top'].set_visible(False); ax.spines['right'].set_visible(False)

# 4 Period comparison
ax = fig.add_subplot(gs[4, :]); ax.set_xlim(0, 10); ax.set_ylim(0, 2); ax.axis('off')
ax.add_patch(mpatches.FancyBboxPatch((0.15, 0.2), 9.7, 1.5, boxstyle="round,pad=0.1", facecolor=BLUE_L, alpha=0.1, edgecolor=BLUE_L))
ax.text(5, 1.55, '三阶段对比', fontsize=13, fontweight='bold', color=TEXT_D, ha='center', fontproperties=fpb)
for i, (label, o, a, days, color) in enumerate([
    ('节前 4/22-4/30', pre_orders, pre_amount, pre_days, BLUE),
    ('五一假期 5/1-5/3', hol_orders, hol_amount, hol_days, ORANGE),
    ('节后 5/4-5/6', post_orders, post_amount, post_days, GREEN),
]):
    x = 1.2 + i * 3
    ax.add_patch(mpatches.FancyBboxPatch((x, 0.25), 2.5, 1.2, boxstyle="round,pad=0.08", facecolor=color, alpha=0.08, edgecolor=color, linewidth=1))
    ax.text(x + 1.25, 1.15, f'{days}天', fontsize=9, color=TEXT_L, ha='center', fontproperties=fp)
    ax.text(x + 1.25, 0.85, f'{o}单', fontsize=16, fontweight='bold', color=color, ha='center', fontproperties=fpb)
    ax.text(x + 1.25, 0.55, f'¥{a:,.0f}', fontsize=11, color=TEXT_M, ha='center', fontproperties=fp)
    ax.text(x + 1.25, 0.3, f'日均{o/days:.0f}单/¥{a/days:,.0f}', fontsize=7.5, color=TEXT_L, ha='center', fontproperties=fp)

# 5 Weekday vs Holiday
ax = fig.add_subplot(gs[5, :]); sax(ax, '工作日/周末/节假日日均对比')
weekday_orders = [orders[i] for i in range(len(dates)) if dates[i].weekday() < 5 and dates[i] >= datetime(2026,5,1)]
holiday_orders = [orders[i] for i in range(len(dates)) if dates[i] >= datetime(2026,5,1) and dates[i] <= datetime(2026,5,3)]
pre_orders_list = [orders[i] for i in pre_idx]

if weekday_orders: avg_wd = sum(weekday_orders)/len(weekday_orders)
else: avg_wd = 0
avg_hol = sum(holiday_orders)/len(holiday_orders) if holiday_orders else 0
avg_pre = sum(pre_orders_list)/len(pre_orders_list) if pre_orders_list else 0

labels2 = ['节前(工作日)', '五一假期', '节后(工作日)']
vals2 = [avg_pre, avg_hol, avg_daily_orders if post_days > 0 else 0]
colors3 = [BLUE_L, ORANGE, GREEN]
for i, (lbl, val, col) in enumerate(zip(labels2, vals2, colors3)):
    ax.bar(i, val, color=col, width=0.5, edgecolor='white', alpha=0.9)
    ax.text(i, val + max(vals2)*0.04, f'{val:.0f}单', ha='center', fontsize=10, fontweight='bold', color=TEXT_D, fontproperties=fpb)
ax.set_xticks(range(3))
ax.set_xticklabels(labels2, fontproperties=fp, fontsize=10, color=TEXT_D)
ax.set_ylabel('日均订单', fontsize=9, color=TEXT_M, fontproperties=fp)
ax.set_ylim(0, max(vals2) * 1.2)
ax.grid(axis='y', alpha=0.4, color=GRID)
for s in ax.spines.values(): s.set_color(BORDER)
ax.spines['top'].set_visible(False); ax.spines['right'].set_visible(False)

# 6 Orders vs Amount dual axis
ax1 = fig.add_subplot(gs[6, :]); sax(ax1, '订单量 vs 快递费 双轴对照')
ax1.bar(range(len(dates)), orders, color=BLUE, alpha=0.6, edgecolor='white', width=0.6, label='订单量')
ax1.set_ylabel('订单量（单）', fontsize=9, color=BLUE, fontproperties=fp)
ax2 = ax1.twinx()
ax2.plot(range(len(dates)), amounts, color=RED, marker='o', markersize=4, linewidth=2, label='快递费')
ax2.set_ylabel('快递费（元）', fontsize=9, color=RED, fontproperties=fp)
ax1.set_xticks(range(len(dates)))
ax1.set_xticklabels([d.strftime('%m/%d') for d in dates], rotation=30, ha='right', fontsize=7.5, fontproperties=fp)
for s in ax1.spines.values(): s.set_color(BORDER)
for s in ax2.spines.values(): s.set_color(BORDER)
ax1.spines['top'].set_visible(False); ax2.spines['top'].set_visible(False)
lines1, labels1 = ax1.get_legend_handles_labels()
lines2, labels2 = ax2.get_legend_handles_labels()
ax1.legend(lines1 + lines2, labels1 + labels2, prop=fp, fontsize=8, framealpha=0.9)
ax1.grid(axis='y', alpha=0.4, color=GRID)

# 7 Top days
ax = fig.add_subplot(gs[7, :]); sax(ax, 'TOP5 订单最高日')
top5_idx = sorted(range(len(orders)), key=lambda i: orders[i], reverse=True)[:5]
top5_labels = [dates_sorted[i] for i in top5_idx]
top5_vals = [orders[i] for i in top5_idx]
top5_amt = [amounts[i] for i in top5_idx]
for i, (lbl, v, a) in enumerate(zip(top5_labels, top5_vals, top5_amt)):
    color_idx = [BLUE, GREEN, ORANGE, CYAN, PURPLE][i]
    ax.barh(4 - i, v, color=color_idx, height=0.55, edgecolor='white')
    ax.text(v + 3, 4 - i, f'{v}单 / ¥{a:,.0f}', va='center', fontsize=8.5, color=TEXT_D, fontproperties=fp)
ax.set_yticks(range(5))
ax.set_yticklabels(top5_labels, fontproperties=fp, fontsize=9, color=TEXT_D)
ax.set_xlim(0, max(top5_vals) * 1.3)
ax.grid(axis='x', alpha=0.3, color=GRID)
for s in ax.spines.values(): s.set_color(BORDER)
ax.spines['top'].set_visible(False); ax.spines['right'].set_visible(False)

# 8 Cumulative trend
ax = fig.add_subplot(gs[8, :]); sax(ax, '累计订单 & 累计快递费 走势')
cum_orders = np.cumsum(orders)
cum_amounts = np.cumsum(amounts)
ax.plot(range(len(dates)), cum_orders, color=BLUE, marker='o', markersize=3, linewidth=2, label=f'累计订单 (最终{cum_orders[-1]:,}单)')
ax.set_ylabel('累计订单', fontsize=9, color=BLUE, fontproperties=fp)
ax2 = ax.twinx()
ax2.plot(range(len(dates)), cum_amounts, color=GREEN, marker='s', markersize=3, linewidth=2, label=f'累计快递费 (最终¥{cum_amounts[-1]:,.0f})')
ax2.set_ylabel('累计金额（元）', fontsize=9, color=GREEN, fontproperties=fp)
ax.set_xticks(range(len(dates)))
ax.set_xticklabels([d.strftime('%m/%d') for d in dates], rotation=30, ha='right', fontsize=7.5, fontproperties=fp)
lines1, labels1 = ax.get_legend_handles_labels()
lines2, labels2 = ax2.get_legend_handles_labels()
ax.legend(lines1 + lines2, labels1 + labels2, prop=fp, fontsize=8, framealpha=0.9)
ax.grid(axis='y', alpha=0.4, color=GRID)

# 9 Daily avg comparison
ax = fig.add_subplot(gs[9, :]); sax(ax, '各阶段日均对比（订单 vs 费用）')
stages = [('节前', avg_pre, pre_amount/pre_days, BLUE), ('假期', avg_hol, hol_amount/hol_days, ORANGE), ('节后', post_orders/post_days, post_amount/post_days, GREEN)]
x9 = np.arange(3); w9 = 0.3
ax.bar(x9 - w9/2, [s[1] for s in stages], w9, color=[BLUE_L, '#fed7aa', '#bbf7d0'], edgecolor='white', label='日均订单')
ax.bar(x9 + w9/2, [s[2] for s in stages], w9, color=[BLUE, ORANGE, GREEN], edgecolor='white', label='日均费用')
ax.set_xticks(x9)
ax.set_xticklabels([s[0] for s in stages], fontproperties=fp, fontsize=10, color=TEXT_D)
for i, s in enumerate(stages):
    ax.text(i - w9/2, s[1] + 5, f'{s[1]:.0f}', ha='center', fontsize=8, fontweight='bold', color=TEXT_D, fontproperties=fpb)
    ax.text(i + w9/2, s[2] + 50, f'¥{s[2]:,.0f}', ha='center', fontsize=8, fontweight='bold', color=TEXT_D, fontproperties=fpb)
ax.set_ylabel('日均值', fontsize=9, color=TEXT_M, fontproperties=fp)
ax.legend(prop=fp, fontsize=8)
ax.grid(axis='y', alpha=0.4, color=GRID)
for s in ax.spines.values(): s.set_color(BORDER)
ax.spines['top'].set_visible(False); ax.spines['right'].set_visible(False)

# 10 Pie chart (order distribution by phase)
ax = fig.add_subplot(gs[10, :])
ax.set_facecolor(CARD)
labels_p = ['节前 4/22-4/30', '五一 5/1-5/3', '节后 5/4-5/6']
sizes_p = [pre_orders, hol_orders, post_orders]
colors_p = [BLUE_L, ORANGE, GREEN]
wedges, texts, autotexts = ax.pie(sizes_p, labels=labels_p, autopct='%1.0f%%', colors=colors_p,
    startangle=90, pctdistance=0.75,
    textprops={'fontproperties': fp, 'fontsize': 9, 'color': TEXT_M},
    wedgeprops={'edgecolor': 'white', 'linewidth': 2})
for t in autotexts:
    t.set_fontsize(9); t.set_color(TEXT_D); t.set_fontproperties(fpb)
ax.set_title('订单量阶段分布', fontsize=12, fontweight='bold', color=TEXT_D, fontproperties=fpb, pad=10, loc='left')
for s in ax.spines.values(): s.set_color(BORDER)

# 11 Amount distribution pie
ax = fig.add_subplot(gs[11, :])
ax.set_facecolor(CARD)
sizes_a = [pre_amount, hol_amount, post_amount]
wedges, texts, autotexts = ax.pie(sizes_a, labels=labels_p, autopct='%1.0f%%', colors=colors_p,
    startangle=90, pctdistance=0.75,
    textprops={'fontproperties': fp, 'fontsize': 9, 'color': TEXT_M},
    wedgeprops={'edgecolor': 'white', 'linewidth': 2})
for t in autotexts:
    t.set_fontsize(9); t.set_color(TEXT_D); t.set_fontproperties(fpb)
ax.set_title('快递费阶段分布', fontsize=12, fontweight='bold', color=TEXT_D, fontproperties=fpb, pad=10, loc='left')
for s in ax.spines.values(): s.set_color(BORDER)

# 12 Insights
ax = fig.add_subplot(gs[12, :]); ax.set_xlim(0, 10); ax.set_ylim(0, 4); ax.axis('off')
ax.add_patch(mpatches.FancyBboxPatch((0.15, 0.1), 9.7, 3.7, boxstyle="round,pad=0.2", facecolor=CARD, edgecolor=BORDER, linewidth=0.8))
ax.add_patch(mpatches.FancyBboxPatch((0.15, 3.3), 9.7, 0.5, boxstyle="round,pad=0.05", facecolor='#eff6ff', edgecolor='none'))
ax.text(0.5, 3.48, 'DATA INSIGHTS  /  数据洞察', fontsize=12, fontweight='bold', color=BLUE, fontproperties=fpb)
insights = [
    (BLUE, f'15天累计 {total_orders:,}单 / ¥{total_amount:,.0f}，日均 {avg_daily_orders:.0f}单 / ¥{avg_daily_amount:,.0f}'),
    (RED, f'五一假期订单锐减：3天仅{hol_orders}单（日均{hol_orders/hol_days:.0f}单），为节前日均{pre_orders/pre_days:.0f}单的{hol_orders/hol_days/(pre_orders/pre_days)*100:.0f}%'),
    (GREEN, f'节后爆发：5/4-5/6日均{post_orders/post_days:.0f}单，是节前日均{pre_orders/pre_days:.0f}单的{post_orders/post_days/(pre_orders/pre_days):.1f}倍'),
    (ORANGE, f'最高单日5/5达{max(orders)}单/¥{max(amounts):,.0f}，是最低日(5/1 {min(orders)}单/¥{min(amounts):,.0f})的{max(amounts)/min(amounts):.1f}倍'),
    (PURPLE, '节后5/6回落至133单，但仍高于节前平均水平（74单/天），说明需求仍在恢复'),
]
for i, (dc, text) in enumerate(insights):
    y = 2.95 - i * 0.55
    ax.add_patch(plt.Circle((0.5, y + 0.04), 0.06, facecolor=dc, edgecolor='none', alpha=0.8))
    ax.text(0.8, y, text, fontsize=8.5, color=TEXT_D, fontproperties=fp, va='center')

# 13 Text analysis
ax = fig.add_subplot(gs[13, :]); ax.set_xlim(0, 10); ax.set_ylim(0, 5); ax.axis('off')
ax.add_patch(mpatches.FancyBboxPatch((0.15, 0.1), 9.7, 4.7, boxstyle="round,pad=0.2", facecolor='#f0fdf4', edgecolor='#86efac', linewidth=0.8))
ax.add_patch(mpatches.FancyBboxPatch((0.15, 4.3), 9.7, 0.5, boxstyle="round,pad=0.05", facecolor='#dcfce7', edgecolor='none'))
ax.text(0.5, 4.48, '便捷购药处方快递费  /  运营分析', fontsize=12, fontweight='bold', color='#166534', fontproperties=fpb)
lines = [
    (True, '整体态势'),
    (False, f'4/22-5/6共15天，邵逸夫医院便捷购药处方快递费累计{total_orders:,}单，¥{total_amount:,.0f}。'),
    (False, f'节前(4/22-4/30)日均{pre_orders/pre_days:.0f}单，五一假期骤降至{hol_orders/hol_days:.0f}单，'),
    (False, f'节后(5/4-5/6)迅速反弹至{post_orders/post_days:.0f}单/天，超过节前水平。'),
    (True, '波动特征'),
    (False, f'最低日5/1仅{min(orders)}单（¥{min(amounts):,.0f}），最高日5/5达{max(orders)}单（¥{max(amounts):,.0f}），'),
    (False, f'极差比{max(amounts)/min(amounts):.1f}倍，受假期/工作日影响显著。'),
    (True, '运营建议方向'),
    (False, '假期前应做好运力储备，节后需关注订单持续性，避免节后快速回落。'),
    (False, '5/6回落至133单但仍高于节前均值，需观察是否能维持回升趋势。'),
]
y = 4.1
for is_title, text in lines:
    if is_title:
        ax.text(0.4, y, text, fontsize=9.5, fontweight='bold', color='#166534', fontproperties=fpb, va='top')
        y -= 0.27
    else:
        ax.text(0.4, y, text, fontsize=8, color=TEXT_D, fontproperties=fp, va='top')
        y -= 0.24

# 16 Footer
ax = fig.add_subplot(gs[14, :]); ax.set_xlim(0, 10); ax.set_ylim(0, 1); ax.axis('off')
ax.plot([1.5, 8.5], [0.65, 0.65], color=BORDER, linewidth=0.5)
ax.text(5, 0.3, '运营平台部  /  数据分析  /  数据来源: 业务对账系统  /  仅供内部参考', fontsize=7.5, color=TEXT_L, ha='center', fontproperties=fp)

print('Saving...')
plt.savefig('/home/openclaw/.openclaw/workspace/shaoyifu_full_report_20260507.png', dpi=200, bbox_inches='tight', facecolor=BG)
plt.close()
import shutil
shutil.copy2('/home/openclaw/.openclaw/workspace/shaoyifu_full_report_20260507.png', '/mnt/c/Users/44238/Desktop/邵逸夫便捷购药报告_20260507.png')
import os
print(f'Done: {os.path.getsize("/home/openclaw/.openclaw/workspace/shaoyifu_full_report_20260507.png")/1024:.0f} KB')
conn.close()
