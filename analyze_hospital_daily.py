#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
医院日度绩效监控分析脚本
 analyzes hospital performance metrics
"""

import sqlite3
import pandas as pd
import sys
from datetime import datetime, timedelta

# 连接数据库
DB_PATH = "/home/openclaw/.openclaw/workspace/business_flow.db"
conn = sqlite3.connect(DB_PATH)

# 参数：分析日期（默认昨天）
if len(sys.argv) > 1:
    target_date = sys.argv[1]  # 格式：YYYY-MM-DD
else:
    target_date = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')

print(f"📊 医院日度绩效监控分析")
print(f"📅 分析日期: {target_date}")
print(f"{'='*60}")

# 查询各医院的处方服务订单数据
query = f"""
SELECT 
    institution as 医院,
    COUNT(*) as 订单数,
    SUM(amount) as 实际支付金额,
    ROUND(SUM(amount)/COUNT(*), 2) as 客单价
FROM daily_flow_2025
WHERE SUBSTR(yewu_wancheng_shijian, 1, 10) = '{target_date}'
  AND ye_wu_lei_mu LIKE '%处方服务%'
  AND pay_status = '收费'
GROUP BY institution
ORDER BY 实际支付金额 DESC
"""

cursor = conn.cursor()
cursor.execute(query)
results = cursor.fetchall()

if not results:
    print(f"\n当日无处方服务订单数据")
    conn.close()
    sys.exit()

# 转换为DataFrame
df = pd.DataFrame(results, columns=['医院', '订单数', '实际支付金额', '客单价'])

# 输出结果
print(f"\n{'医院':<40} | {'订单数':>8} | {'金额(元)':>12} | {'客单价(元)':>10}")
print("-" * 75)

for _, row in df.iterrows():
    print(f"{row['医院']:<40} | {int(row['订单数']):>8,} | {row['实际支付金额']:>12,.2f} | {row['客单价']:>10,.2f}")

# 统计汇总
total_orders = df['订单数'].sum()
total_amount = df['实际支付金额'].sum()
avg_price = df['实际支付金额'].mean()

print(f"\n{'='*60}")
print(f"汇总数据:")
print(f"  总订单数: {int(total_orders):,}")
print(f"  总金额: {total_amount:,.2f}元")
print(f"  平均客单价: {avg_price:.2f}元")

# Top 5医院
print(f"\nTop 5医院:")
for i, (_, row) in enumerate(df.head(5).iterrows(), 1):
    print(f"  {i}. {row['医院']}: {int(row['订单数'])}单, {row['实际支付金额']:,.2f}元")

conn.close()

print(f"\n✅ 分析完成: {target_date}")
