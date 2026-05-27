#!/usr/bin/env python3
"""邵逸夫医院 便捷购药处方快递费 每日趋势+环比"""
import sqlite3, matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.font_manager import FontProperties, fontManager
from matplotlib.gridspec import GridSpec
from datetime import datetime

font_path = '/home/openclaw/.local/share/fonts/simhei.ttf'
fp = FontProperties(fname=font_path); fpb = FontProperties(fname=font_path, weight='bold')
fontManager.addfont(font_path)
plt.rcParams['font.family']='sans-serif'; plt.rcParams['font.sans-serif']=['SimHei']; plt.rcParams['axes.unicode_minus']=False

BG='#f4f6f9'; CARD='#ffffff'; BLUE='#2563eb'; BLUE_L='#93c5fd'
RED='#ef4444'; GREEN='#22c55e'; ORANGE='#f59e0b'; PURPLE='#8b5cf6'
TEXT_D='#1e293b'; TEXT_M='#475569'; TEXT_L='#94a3b8'; GRID='#e2e8f0'; BORDER='#cbd5e1'

conn = sqlite3.connect('business_flow.db')
cur = conn.cursor()
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
conn.close()

seen = {}
for r in all_rows:
    seen[r[0]] = (r[1], r[2])
dates_sorted = sorted(seen.keys())
dates = [datetime.strptime(d, '%Y-%m-%d') for d in dates_sorted]
orders = [seen[d][0] for d in dates_sorted]
amounts = [seen[d][1] for d in dates_sorted]

total_orders = sum(orders)
total_amount = sum(amounts)
avg_o = total_orders / len(orders)
avg_a = total_amount / len(orders)

# Daily环比
mom_orders = [0] + [round((orders[i]-orders[i-1])/orders[i-1]*100,1) if orders[i-1]>0 else 0 for i in range(1,len(orders))]
mom_amounts = [0] + [round((amounts[i]-amounts[i-1])/amounts[i-1]*100,1) if amounts[i-1]>0 else 0 for i in range(1,len(amounts))]

fig = plt.figure(figsize=(10, 16), facecolor=BG)
gs = GridSpec(4, 1, figure=fig, hspace=0.45, left=0.08, right=0.95, top=0.95, bottom=0.06,
    height_ratios=[0.5, 1.3, 1.3, 0.5])

# Title
ax = fig.add_subplot(gs[0]); ax.set_xlim(0, 10); ax.set_ylim(0, 2); ax.axis('off')
ax.add_patch(mpatches.FancyBboxPatch((0.3, 0.15), 9.4, 1.6, boxstyle="round,pad=0.15",
    facecolor=BLUE, edgecolor='none'))
ax.text(5, 1.35, '邵逸夫医院 便捷购药处方快递费', fontsize=20, fontweight='bold', color='white', ha='center', fontproperties=fpb)
ax.text(5, 0.7, f'{dates[0].strftime("%Y/%m/%d")} - {dates[-1].strftime("%Y/%m/%d")}  共{len(dates)}天  |  总{total_orders:,}单  ¥{total_amount:,.0f}',
    fontsize=11, color='#bfdbfe', ha='center', fontproperties=fp)

# Orders + mom
ax1 = fig.add_subplot(gs[1]); ax1.set_facecolor(CARD)
for s in ax1.spines.values(): s.set_color(BORDER); s.set_linewidth(0.5)
ax1.spines['top'].set_visible(False); ax1.spines['right'].set_visible(False)
ax1.grid(axis='y', alpha=0.3, color=GRID)

bars1 = ax1.bar(range(len(dates)), orders, color=[BLUE if orders[i]>=avg_o else BLUE_L for i in range(len(orders))],
    edgecolor='white', width=0.6, alpha=0.9)
ax1.axhline(y=avg_o, color=RED, linestyle='--', linewidth=1.5, alpha=0.6, label=f'日均 {avg_o:.0f}单')
for i, o in enumerate(orders):
    ax1.text(i, o + max(orders)*0.02, str(o), ha='center', va='bottom', fontsize=7.5, color=TEXT_D, fontweight='bold', fontproperties=fp)

# 环比标注
for i in range(1, len(mom_orders)):
    m = mom_orders[i]
    color = GREEN if m > 0 else RED if m < 0 else TEXT_L
    sign = '+' if m > 0 else ''
    ax1.annotate(f'{sign}{m}%', xy=(i, 0), xytext=(i, -max(orders)*0.12),
        ha='center', fontsize=7, fontweight='bold', color=color, fontproperties=fp,
        arrowprops=dict(arrowstyle='-', color=color, lw=0.8) if abs(m)>20 else None)

ax1.set_xticks(range(len(dates)))
ax1.set_xticklabels([d.strftime('%m/%d') for d in dates], rotation=30, ha='right', fontsize=8, fontproperties=fp)
ax1.set_ylabel('每日订单（单）', fontsize=10, color=TEXT_M, fontproperties=fp)
ax1.set_title('每日订单量  +  环比', fontsize=13, fontweight='bold', color=TEXT_D, fontproperties=fpb, pad=10, loc='left')
ax1.legend(prop=fp, fontsize=8, framealpha=0.9, loc='upper right')
ax1.set_ylim(0, max(orders)*1.25)
ax1.tick_params(colors=TEXT_M, labelsize=7.5)

# Amount + mom
ax2 = fig.add_subplot(gs[2]); ax2.set_facecolor(CARD)
for s in ax2.spines.values(): s.set_color(BORDER); s.set_linewidth(0.5)
ax2.spines['top'].set_visible(False); ax2.spines['right'].set_visible(False)
ax2.grid(axis='y', alpha=0.3, color=GRID)

bars2 = ax2.bar(range(len(dates)), amounts, color=[GREEN if amounts[i]>=avg_a else '#A8E6CF' for i in range(len(amounts))],
    edgecolor='white', width=0.6, alpha=0.9)
ax2.axhline(y=avg_a, color=RED, linestyle='--', linewidth=1.5, alpha=0.6, label=f'日均 ¥{avg_a:,.0f}')
for i, a in enumerate(amounts):
    ax2.text(i, a + max(amounts)*0.02, f'{a:,.0f}', ha='center', va='bottom', fontsize=7, color=TEXT_D, fontweight='bold', fontproperties=fp)

for i in range(1, len(mom_amounts)):
    m = mom_amounts[i]
    color = GREEN if m > 0 else RED if m < 0 else TEXT_L
    sign = '+' if m > 0 else ''
    ax2.annotate(f'{sign}{m}%', xy=(i, 0), xytext=(i, -max(amounts)*0.12),
        ha='center', fontsize=7, fontweight='bold', color=color, fontproperties=fp,
        arrowprops=dict(arrowstyle='-', color=color, lw=0.8) if abs(m)>20 else None)

ax2.set_xticks(range(len(dates)))
ax2.set_xticklabels([d.strftime('%m/%d') for d in dates], rotation=30, ha='right', fontsize=8, fontproperties=fp)
ax2.set_ylabel('每日快递费（元）', fontsize=10, color=TEXT_M, fontproperties=fp)
ax2.set_title('每日快递费  +  环比', fontsize=13, fontweight='bold', color=TEXT_D, fontproperties=fpb, pad=10, loc='left')
ax2.legend(prop=fp, fontsize=8, framealpha=0.9, loc='upper right')
ax2.set_ylim(0, max(amounts)*1.25)
ax2.tick_params(colors=TEXT_M, labelsize=7.5)

# Summary table
ax3 = fig.add_subplot(gs[3]); ax3.set_xlim(0, 10); ax3.set_ylim(0, 1.2); ax3.axis('off')
headers = ['日期', '订单', '快递费', '订单环比', '费用环比']
colw = [1.3, 1.3, 1.6, 1.8, 1.8]
x_start = 0.6
y_top = 1.0

# Header row
ax3.add_patch(mpatches.Rectangle((x_start, y_top-0.22), sum(colw), 0.25, facecolor=BLUE, edgecolor='none'))
cx = x_start
for h, w in zip(headers, colw):
    ax3.text(cx + w/2, y_top-0.09, h, ha='center', va='center', fontsize=8, fontweight='bold', color='white', fontproperties=fpb)
    cx += w

# Data rows
for i in range(len(dates)):
    y = y_top - 0.22 - (i+1)*0.18
    bg = '#eff6ff' if orders[i] >= avg_o else '#ffffff'
    ax3.add_patch(mpatches.Rectangle((x_start, y), sum(colw), 0.2, facecolor=bg, edgecolor=BORDER, linewidth=0.3))
    cx = x_start
    vals = [dates_sorted[i], str(orders[i]), f'¥{amounts[i]:,.0f}',
            f'{"+"+str(mom_orders[i])+"%" if mom_orders[i]>0 else str(mom_orders[i])+"%" if i>0 else "--"',
            f'{"+"+str(mom_amounts[i])+"%" if mom_amounts[i]>0 else str(mom_amounts[i])+"%" if i>0 else "--"']
    colors_v = [TEXT_D, TEXT_D, TEXT_D,
                GREEN if i>0 and mom_orders[i]>0 else RED if i>0 and mom_orders[i]<0 else TEXT_L,
                GREEN if i>0 and mom_amounts[i]>0 else RED if i>0 and mom_amounts[i]<0 else TEXT_L]
    for v, w, c in zip(vals, colw, colors_v):
        ax3.text(cx + w/2, y+0.1, v, ha='center', va='center', fontsize=7.5, color=c, fontproperties=fp, fontweight='bold')
        cx += w

plt.savefig('/home/openclaw/.openclaw/workspace/shaoyifu_simple_20260507.png', dpi=200, bbox_inches='tight', facecolor=BG)
plt.close()
import shutil, os
shutil.copy2('/home/openclaw/.openclaw/workspace/shaoyifu_simple_20260507.png', '/mnt/c/Users/44238/Desktop/邵逸夫便捷购药_每日趋势_20260507.png')
print(f'Done: {os.path.getsize("/home/openclaw/.openclaw/workspace/shaoyifu_simple_20260507.png")/1024:.0f} KB')
