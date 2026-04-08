#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
医院订单异常波动检测脚本
采用多种算法结合的方式检测异常数据
"""

import sqlite3
import pandas as pd
import numpy as np
import sys
from datetime import datetime, timedelta

# 连接数据库
DB_PATH = "/home/openclaw/.openclaw/workspace/business_flow.db"
conn = sqlite3.connect(DB_PATH)

# 参数：分析日期（默认今天）
if len(sys.argv) > 1:
    target_date = sys.argv[1]  # 格式：YYYY-MM-DD
else:
    target_date = datetime.now().strftime('%Y-%m-%d')

print(f"⚠️  医院订单异常波动检测")
print(f"📅 检测日期: {target_date}")
print(f"{'='*60}")

# 查询所有医院的每日数据（最近30天）
query = """
SELECT 
    institution as 医院,
    COUNT(*) as 订单数,
    SUM(amount) as 金额,
    SUBSTR(yewu_wancheng_shijian, 1, 10) as 日期
FROM (
    SELECT * FROM daily_flow_2025
    UNION ALL
    SELECT * FROM daily_flow_2026_jan_feb
    UNION ALL
    SELECT * FROM daily_flow_2026_mar
    UNION ALL
    SELECT * FROM daily_flow_2026_apr
)
WHERE SUBSTR(yewu_wancheng_shijian, 1, 10) >= date('{target_date}', '-30 days')
  AND SUBSTR(yewu_wancheng_shijian, 1, 10) <= '{target_date}'
  AND ye_wu_lei_mu LIKE '%处方服务%'
  AND pay_status = '收费'
GROUP BY institution, SUBSTR(yewu_wancheng_shijian, 1, 10)
ORDER BY 日期 DESC
""".format(target_date=target_date)

df = pd.read_sql_query(query, conn)
conn.close()

if df.empty:
    print(f"\n⚠️  最近30天内无处方服务订单数据")
    sys.exit()

# 按医院分组分析
unique_hospitals = df['医院'].unique()
print(f"📊 检测医院数量: {len(unique_hospitals)}")
print(f"📅 数据时间范围: {df['日期'].min()} ~ {df['日期'].max()}")
print(f"{'='*60}\n")

all_anomalies = []

for hospital in unique_hospitals:
    hospital_data = df[df['医院'] == hospital].sort_values('日期', ascending=False)
    
    if len(hospital_data) < 2:
        continue
    
    # 获取当天和最近7天的数据
    today_data = hospital_data[hospital_data['日期'] == target_date]
    recent_7_days = hospital_data.head(7)
    
    if today_data.empty:
        continue
    
    today_orders = today_data.iloc[0]['订单数']
    today_amount = today_data.iloc[0]['金额']
    
    # 计算最近7天的统计指标
    recent_orders = recent_7_days['订单数'].values
    recent_amounts = recent_7_days['金额'].values
    
    mean_orders = np.mean(recent_orders)
    std_orders = np.std(recent_orders)
    mean_amount = np.mean(recent_amounts)
    std_amount = np.std(recent_amounts)
    
    # 算法1: Z-Score 扩展（更宽松）
    zscore_orders = (today_orders - mean_orders) / std_orders if std_orders > 0 else 0
    zscore_amount = (today_amount - mean_amount) / std_amount if std_amount > 0 else 0
    
    # 算法2: IQR（四分位距）方法
    q1_orders = np.percentile(recent_orders, 25)
    q3_orders = np.percentile(recent_orders, 75)
    iqr_orders = q3_orders - q1_orders
    upper_bound_orders = q3_orders + 1.5 * iqr_orders
    
    q1_amount = np.percentile(recent_amounts, 25)
    q3_amount = np.percentile(recent_amounts, 75)
    iqr_amount = q3_amount - q1_amount
    upper_bound_amount = q3_amount + 1.5 * iqr_amount
    
    # 算法3: 动态阈值（基于订单量大小的比例）
    dynamic_threshold_orders = mean_orders * 1.5 + 50  # 基础1.5倍+50单缓冲
    dynamic_threshold_amount = mean_amount * 1.5 + 10000  # 基础1.5倍+1万元缓冲
    
    # 综合判断
    anomaly_flags = []
    reasons = []
    
    # Z-Score检测（宽松阈值2.0）
    if zscore_orders > 2.0:
        anomaly_flags.append('ZScore订单')
        reasons.append(f'  • 订单Z-Score: {zscore_orders:.2f} (阈值: 2.0)')
    if zscore_amount > 2.0:
        anomaly_flags.append('ZScore金额')
        reasons.append(f'  • 金额Z-Score: {zscore_amount:.2f} (阈值: 2.0)')
    
    # IQR检测
    if today_orders > upper_bound_orders:
        anomaly_flags.append('IQR订单')
        reasons.append(f'  • 订单IQR上限: {upper_bound_orders:.0f} (当前: {today_orders})')
    if today_amount > upper_bound_amount:
        anomaly_flags.append('IQR金额')
        reasons.append(f'  • 金额IQR上限: {upper_bound_amount:.0f} (当前: {today_amount:,.0f})')
    
    # 动态阈值检测
    if today_orders > dynamic_threshold_orders:
        anomaly_flags.append('动态订单')
        reasons.append(f'  • 订单动态阈值: {dynamic_threshold_orders:.0f} (当前: {today_orders})')
    if today_amount > dynamic_threshold_amount:
        anomaly_flags.append('动态金额')
        reasons.append(f'  • 金额动态阈值: {dynamic_threshold_amount:.0f} (当前: {today_amount:,.0f})')
    
    # 增长率检测（如果前一天有数据）
    if len(recent_7_days) >= 2:
        yesterday_orders = recent_7_days.iloc[1]['订单数']
        if yesterday_orders > 0:
            growth_rate = (today_orders - yesterday_orders) / yesterday_orders * 100
            if growth_rate > 50:  # 增长超过50%
                anomaly_flags.append('增长率订单')
                reasons.append(f'  • 订单增长率: {growth_rate:.1f}% (昨日: {yesterday_orders})')
    
    # 记录异常
    if anomaly_flags:
        all_anomalies.append({
            '医院': hospital,
            '日期': target_date,
            '订单数': today_orders,
            '金额': today_amount,
            '异常类型': ', '.join(anomaly_flags),
            '详细原因': '\n'.join(reasons)
        })

# 输出结果
print(f"🔍 检测结果: {len(all_anomalies)} 个医院存在异常波动")
print(f"{'='*60}\n")

if all_anomalies:
    # 按订单数降序排列
    all_anomalies.sort(key=lambda x: x['订单数'], reverse=True)
    
    for i, anomaly in enumerate(all_anomalies, 1):
        print(f"医院 {i}: {anomaly['医院']}")
        print(f"  📅 日期: {anomaly['日期']}")
        print(f"  📊 订单数: {anomaly['订单数']:,}")
        print(f"  💰 金额: {anomaly['金额']:,.2f}元")
        print(f"  ⚠️  异常类型: {anomaly['异常类型']}")
        print(f"  🔍 详细原因:")
        print(anomaly['详细原因'])
        print(f"{'-'*60}\n")
    
    # Excel导出
    anomaly_df = pd.DataFrame(all_anomalies)
    output_file = f"/home/openclaw/.openclaw/workspace/异常监控报告_{target_date}.xlsx"
    anomaly_df.to_excel(output_file, index=False)
    print(f"📄 报告已保存至: {output_file}")
    
else:
    print("✅ 所有医院数据正常，未发现异常波动")

print(f"\n✅ 异常检测完成")
