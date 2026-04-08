#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
各医院处方服务结构分析
统计各医院处方服务的内部构成（便捷购药 vs 院内处方 vs 院外处方）
"""

import sqlite3
import pandas as pd
import sys
from datetime import datetime, timedelta

DB_PATH = "/home/openclaw/.openclaw/workspace/business_flow.db"
conn = sqlite3.connect(DB_PATH)

# 参数：时间范围（默认近30天）
if len(sys.argv) > 1:
    days = int(sys.argv[1])
else:
    days = 30

target_date = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')

print(f"📊 各医院处方服务结构分析")
print(f"📅 时间范围: {start_date} 至 {target_date}")
print(f"{'='*70}")

# 查询各医院处方服务结构
query = f"""
SELECT 
    institution as 医院,
    ye_wu_zi_lei_mu as 子类目,
    COUNT(*) as 订单数,
    SUM(amount) as 金额,
    ROUND(SUM(amount)/COUNT(*), 2) as 客单价
FROM daily_flow_2025
WHERE SUBSTR(yewu_wancheng_shijian, 1, 10) >= '{start_date}'
  AND SUBSTR(yewu_wancheng_shijian, 1, 10) <= '{target_date}'
  AND ye_wu_lei_mu LIKE '%处方服务%'
  AND pay_status = '收费'
GROUP BY institution, ye_wu_zi_lei_mu
ORDER BY institution, 金额 DESC
"""

cursor = conn.cursor()
cursor.execute(query)
results = cursor.fetchall()

if not results:
    print(f"\n当期无处方服务订单数据")
    conn.close()
    sys.exit()

# 转换为DataFrame
df = pd.DataFrame(results, columns=['医院', '子类目', '订单数', '金额', '客单价'])

# 按医院分组汇总
print(f"\n{'医院':<40} | {'子类目':<15} | {'订单数':>8} | {'金额(元)':>12} | {'客单价':>10} | {'占比':>8}")
print("-" * 100)

for _, row in df.iterrows():
    print(f"{row['医院']:<40} | {row['子类目']:<15} | {int(row['订单数']):>8,} | {row['金额']:>12,.2f} | {row['客单价']:>10,.2f} | -")

# 计算各医院占比
print(f"\n{'='*70}")
print(f"各医院处方服务结构占比:")

for 医院 in df['医院'].unique():
    医院数据 = df[df['医院'] == 医院]
    总金额 = 医院数据['金额'].sum()
    
    print(f"\n{医院}:")
    for _, row in 医院数据.iterrows():
        占比 = (row['金额'] / 总金额 * 100) if 总金额 > 0 else 0
        print(f"  {row['子类目']:<15}: {int(row['订单数']):>6}单, {row['金额']:>10,.2f}元 ({占比:.1f}%)")

conn.close()

print(f"\n✅ 分析完成: {start_date} 至 {target_date}")
