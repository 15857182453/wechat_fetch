#!/usr/bin/env python3
"""
业务对账日报表生成脚本
从业务对账统计明细.xlsx 生成汇总报表
"""

import pandas as pd
import matplotlib
matplotlib.use('Agg')  # 非交互式后端
import matplotlib.pyplot as plt
from datetime import datetime
import os

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

# 读取数据
df = pd.read_excel('/home/openclaw/.openclaw/workspace/业务对账统计明细.xlsx')

print('=== 开始生成日报表 ===\n')

# 1. 添加日期列
df['交易日期'] = df['交易时间'].dt.date
df['交易小时'] = df['交易时间'].dt.hour

# 2. 按日期汇总
daily_summary = df.groupby('交易日期').agg({
    '实际支付金额': 'sum',
    '医院分账金额': 'sum',
    '第三方分账金额': 'sum',
    '平台留存': 'sum',
    '商户订单号': 'count'
}).reset_index()
daily_summary.columns = ['日期', '实际支付金额', '医院分账金额', '第三方分账金额', '平台留存', '订单数']

# 3. 按业务类型汇总
type_summary = df.groupby('业务类型').agg({
    '实际支付金额': ['sum', 'count'],
    '医院分账金额': 'sum',
    '第三方分账金额': 'sum',
    '平台留存': 'sum'
}).round(2)
type_summary.columns = ['总金额', '订单数', '医院分账', '第三方分账', '平台留存']
type_summary = type_summary.sort_values('总金额', ascending=False)

# 4. 按机构汇总
org_summary = df.groupby('机构名称').agg({
    '实际支付金额': ['sum', 'count'],
    '医院分账金额': 'sum',
    '平台留存': 'sum'
}).round(2)
org_summary.columns = ['总金额', '订单数', '医院分账', '平台留存']
org_summary = org_summary.sort_values('总金额', ascending=False)

# 5. 按支付方式汇总
pay_summary = df.groupby('支付方式/账号').agg({
    '实际支付金额': ['sum', 'count'],
    '平台留存': 'sum'
}).round(2)
pay_summary.columns = ['总金额', '订单数', '平台留存']
pay_summary = pay_summary.sort_values('总金额', ascending=False)

print(f'生成日期：{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
print(f'数据日期范围：{df["交易时间"].min()} 至 {df["交易时间"].max()}')
print(f'总订单数：{len(df)}')
print(f'总流水：{df["实际支付金额"].sum():,.2f}元')
print()

# 保存汇总数据到Excel
output_file = '/home/openclaw/.openclaw/workspace/业务对账日报表_{}.xlsx'.format(
    datetime.now().strftime('%Y%m%d_%H%M%S')
)

with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
    # 页签1：每日流水
    daily_summary.to_excel(writer, sheet_name='每日流水', index=False)
    
    # 页签2：业务类型
    type_summary.to_excel(writer, sheet_name='业务类型')
    
    # 页签3：机构汇总
    org_summary.to_excel(writer, sheet_name='机构汇总')
    
    # 页签4：支付方式
    pay_summary.to_excel(writer, sheet_name='支付方式')

print(f'✅ 报表已生成：{output_file}')

# 生成可视化图表
fig, axes = plt.subplots(2, 2, figsize=(14, 10))
fig.suptitle('业务对账日报表 - {} 至 {}'.format(
    df['交易时间'].min().strftime('%Y-%m-%d'),
    df['交易时间'].max().strftime('%Y-%m-%d')
), fontsize=14, fontweight='bold')

# 图1：每日流水趋势
ax1 = axes[0, 0]
ax1.plot(daily_summary['日期'], daily_summary['实际支付金额'], marker='o', linestyle='-', linewidth=2, markersize=6)
ax1.set_title('每日流水趋势')
ax1.set_xlabel('日期')
ax1.set_ylabel('金额（元）')
ax1.grid(True, alpha=0.3)
ax1.tick_params(axis='x', rotation=45)

# 图2：业务类型分布
ax2 = axes[0, 1]
top_types = type_summary.head(10)
ax2.barh(range(len(top_types)), top_types['总金额'], color='steelblue')
ax2.set_yticks(range(len(top_types)))
ax2.set_yticklabels(top_types.index, fontsize=8)
ax2.set_title('TOP 10 业务类型流水')
ax2.set_xlabel('金额（元）')

# 图3：机构分布
ax3 = axes[1, 0]
top_orgs = org_summary.head(10)
ax3.barh(range(len(top_orgs)), top_orgs['总金额'], color='coral')
ax3.set_yticks(range(len(top_orgs)))
ax3.set_yticklabels(top_orgs.index, fontsize=8)
ax3.set_title('TOP 10 机构流水')
ax3.set_xlabel('金额（元）')

# 图4：金额构成饼图
ax4 = axes[1, 1]
amounts = [type_summary.loc['咨询', '总金额'], 
           type_summary.loc['处方', '总金额'],
           type_summary.loc['第三方平台业务', '总金额'],
           type_summary.loc['健康管理', '总金额']]
labels = ['咨询', '处方', '第三方平台', '健康管理']
colors = ['#66b3ff', '#ffcc99', '#99ff99', '#ff9999']
ax4.pie(amounts, labels=labels, autopct='%1.1f%%', colors=colors, startangle=90)
ax4.set_title('主要业务类型占比')

plt.tight_layout()
plt.savefig('/home/openclaw/.openclaw/workspace/业务对账日报表_{}.png'.format(
    datetime.now().strftime('%Y%m%d_%H%M%S')
), dpi=150, bbox_inches='tight')
print('✅ 图表已保存：业务对账日报表_{}.png'.format(datetime.now().strftime('%Y%m%d_%H%M%S')))

# 生成 Markdown 报告
report_md = f'''# 📊 业务对账日报表

**生成时间：** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}  
**数据范围：** {df["交易时间"].min()} 至 {df["交易时间"].max()}  
**总订单数：** {len(df):,}  
**总流水：** {df["实际支付金额"].sum():,.2f} 元

---

## 📈 总体概览

| 指标 | 数值 |
|------|------|
| **总流水** | {df["实际支付金额"].sum():,.2f} 元 |
| **总订单数** | {len(df):,} |
| **日均流水** | {daily_summary["实际支付金额"].mean():,.2f} 元 |
| **日均订单** | {len(df) / len(daily_summary):,.0f} 单 |

---

## 📅 每日流水明细

| 日期 | 实际支付金额 | 医院分账 | 第三方分账 | 平台留存 | 订单数 |
|------|-------------|---------|-----------|---------|--------|
'''

for _, row in daily_summary.iterrows():
    report_md += f"| {row['日期']} | {row['实际支付金额']:,.2f} | {row['医院分账金额']:,.2f} | {row['第三方分账金额']:,.2f} | {row['平台留存']:,.2f} | {int(row['订单数'])} |\n"

report_md += '''
---

## 📊 业务类型流水TOP 10

| 业务类型 | 总金额 | 订单数 | 医院分账 | 第三方分账 | 平台留存 |
|----------|--------|--------|----------|-----------|---------|
'''

for idx, (name, row) in enumerate(type_summary.head(10).iterrows(), 1):
    report_md += f"| {idx}. {name} | {row['总金额']:,.2f} | {int(row['订单数'])} | {row['医院分账']:,.2f} | {row['第三方分账']:,.2f} | {row['平台留存']:,.2f} |\n"

report_md += '''
---

## 🏥 机构流水TOP 10

| 机构名称 | 总金额 | 订单数 | 医院分账 | 平台留存 |
|----------|--------|--------|----------|---------|
'''

for idx, (name, row) in enumerate(org_summary.head(10).iterrows(), 1):
    report_md += f"| {idx}. {name} | {row['总金额']:,.2f} | {int(row['订单数'])} | {row['医院分账']:,.2f} | {row['平台留存']:,.2f} |\n"

report_md += '''
---

## 💳 支付方式分布

| 支付方式 | 总金额 | 订单数 | 平台留存 |
|----------|--------|--------|---------|
'''

for idx, (name, row) in enumerate(pay_summary.head(10).iterrows(), 1):
    report_md += f"| {idx}. {name} | {row['总金额']:,.2f} | {int(row['订单数'])} | {row['平台留存']:,.2f} |\n"

report_md += f'''

---

## 📊 可视化图表

| 每日流水趋势 | 业务类型分布 |
|-------------|-------------|
| ![每日流水](业务对账日报表_{datetime.now().strftime("%Y%m%d_%H%M%S")}.png) | *(图表见附件)* |

---

## ⚙️ 报表说明

1. **实际支付金额**：用户实际支付的总金额
2. **医院分账金额**：医院应得的分账金额
3. **第三方分账金额**：第三方合作方的分账金额
4. **平台留存**：平台收取的服务费

---

*本报表由系统自动生成*
'''

# 保存 Markdown 报告
with open('/home/openclaw/.openclaw/workspace/业务对账日报表_{}.md'.format(
    datetime.now().strftime('%Y%m%d_%H%M%S')
), 'w', encoding='utf-8') as f:
    f.write(report_md)
print('✅ Markdown 报告已保存：业务对账日报表_{}.md'.format(datetime.now().strftime('%Y%m%d_%H%M%S')))

print('\n=== 报表生成完成 ===')
