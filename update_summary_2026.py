#!/usr/bin/env python3
"""UPSERT 新流水2026.xlsx 到 duizhang_summary_2026（不删表）"""
import pandas as pd
import sqlite3
from datetime import datetime

DB_PATH = '/home/openclaw/.openclaw/workspace/business_flow.db'
EXCEL = '/home/openclaw/.openclaw/workspace/新流水2026.xlsx'

df = pd.read_excel(EXCEL, skiprows=4, header=None)
print(f'📖 读取 {len(df)} 行原始数据')

# 列索引映射（skiprows=4 后）
# idx0=日期, idx1-22=11类业务(流水+订单), idx23=日总流水(元), idx24=日总流水(万元)
# idx25=日流水增量, idx26=日流水环比

# 清理
df = df[~df.iloc[:, 0].isin(['总计', '流水汇总(万元)', 'nan'])].copy()
df['日期'] = pd.to_datetime(df.iloc[:, 0], errors='coerce')
df = df[df['日期'].notna()].copy()
df['日期'] = df['日期'].dt.strftime('%Y-%m-%d')

print(f'📅 有效数据：{len(df)} 条')

# 显示日期分布
for i in range(max(0, len(df)-10), len(df)):
    row = df.iloc[i]
    print(f'  {row["日期"]}: c23={row.iloc[23]}, c24(万)={row.iloc[24]}')

now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
records = []
for _, row in df.iterrows():
    record = {
        'date': row['日期'],
        'ywul_class_flow': float(row.iloc[1]) / 10000 if pd.notna(row.iloc[1]) else 0.0,
        'ywul_class_orders': int(row.iloc[2]) if pd.notna(row.iloc[2]) else 0,
        'chufang_flow': float(row.iloc[3]) / 10000 if pd.notna(row.iloc[3]) else 0.0,
        'chufang_orders': int(row.iloc[4]) if pd.notna(row.iloc[4]) else 0,
        'tiujian_flow': float(row.iloc[5]) / 10000 if pd.notna(row.iloc[5]) else 0.0,
        'tiujian_orders': int(row.iloc[6]) if pd.notna(row.iloc[6]) else 0,
        'jianguan_flow': float(row.iloc[7]) / 10000 if pd.notna(row.iloc[7]) else 0.0,
        'jianguan_orders': int(row.iloc[8]) if pd.notna(row.iloc[8]) else 0,
        'disanfang_flow': float(row.iloc[9]) / 10000 if pd.notna(row.iloc[9]) else 0.0,
        'disanfang_orders': int(row.iloc[10]) if pd.notna(row.iloc[10]) else 0,
        'xinli_flow': float(row.iloc[11]) / 10000 if pd.notna(row.iloc[11]) else 0.0,
        'xinli_orders': int(row.iloc[12]) if pd.notna(row.iloc[12]) else 0,
        'zhifu_flow': float(row.iloc[13]) / 10000 if pd.notna(row.iloc[13]) else 0.0,
        'zhifu_orders': int(row.iloc[14]) if pd.notna(row.iloc[14]) else 0,
        'yuancheng_flow': float(row.iloc[15]) / 10000 if pd.notna(row.iloc[15]) else 0.0,
        'yuancheng_orders': int(row.iloc[16]) if pd.notna(row.iloc[16]) else 0,
        'huiyuan_flow': float(row.iloc[17]) / 10000 if pd.notna(row.iloc[17]) else 0.0,
        'huiyuan_orders': int(row.iloc[18]) if pd.notna(row.iloc[18]) else 0,
        'disanfang_tj_flow': float(row.iloc[19]) / 10000 if pd.notna(row.iloc[19]) else 0.0,
        'disanfang_tj_orders': int(row.iloc[20]) if pd.notna(row.iloc[20]) else 0,
        'shangcheng_flow': float(row.iloc[21]) / 10000 if pd.notna(row.iloc[21]) else 0.0,
        'shangcheng_orders': int(row.iloc[22]) if pd.notna(row.iloc[22]) else 0,
        # idx23 是日总流水(元)，÷10000 → 万元
        'daily_total_flow': float(row.iloc[23]) / 10000 if pd.notna(row.iloc[23]) else 0.0,
        'daily_flow_increment': float(row.iloc[25]) if pd.notna(row.iloc[25]) else 0.0,
        'daily_flow_ratio': float(row.iloc[26]) if pd.notna(row.iloc[26]) else 0.0,
        'created_at': now
    }
    records.append(record)

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# 获取已有日期
cursor.execute('SELECT date FROM duizhang_summary_2026')
existing_dates = set(row[0] for row in cursor.fetchall())

new_dates = set(r['date'] for r in records) - existing_dates
update_dates = set(r['date'] for r in records) & existing_dates

print(f'\n📊 UPSERT 统计:')
print(f'  新增日期: {len(new_dates)} 个 → {sorted(new_dates)}')
print(f'  更新日期: {len(update_dates)} 个')

if new_dates:
    new_recs = [r for r in records if r['date'] in new_dates]
    cursor.executemany('''
        INSERT INTO duizhang_summary_2026 (
            date, ywul_class_flow, ywul_class_orders, chufang_flow, chufang_orders,
            tiujian_flow, tiujian_orders, jianguan_flow, jianguan_orders,
            disanfang_flow, disanfang_orders, xinli_flow, xinli_orders,
            zhifu_flow, zhifu_orders, yuancheng_flow, yuancheng_orders,
            huiyuan_flow, huiyuan_orders, disanfang_tj_flow, disanfang_tj_orders,
            shangcheng_flow, shangcheng_orders, daily_total_flow,
            daily_flow_increment, daily_flow_ratio, created_at
        ) VALUES (
            :date, :ywul_class_flow, :ywul_class_orders, :chufang_flow, :chufang_orders,
            :tiujian_flow, :tiujian_orders, :jianguan_flow, :jianguan_orders,
            :disanfang_flow, :disanfang_orders, :xinli_flow, :xinli_orders,
            :zhifu_flow, :zhifu_orders, :yuancheng_flow, :yuancheng_orders,
            :huiyuan_flow, :huiyuan_orders, :disanfang_tj_flow, :disanfang_tj_orders,
            :shangcheng_flow, :shangcheng_orders, :daily_total_flow,
            :daily_flow_increment, :daily_flow_ratio, :created_at
        )
    ''', new_recs)
    print(f'  ✅ INSERT {len(new_recs)} 条')

for r in records:
    if r['date'] in update_dates:
        cursor.execute('''
            UPDATE duizhang_summary_2026 SET
                ywul_class_flow=:ywul_class_flow, ywul_class_orders=:ywul_class_orders,
                chufang_flow=:chufang_flow, chufang_orders=:chufang_orders,
                tiujian_flow=:tiujian_flow, tiujian_orders=:tiujian_orders,
                jianguan_flow=:jianguan_flow, jianguan_orders=:jianguan_orders,
                disanfang_flow=:disanfang_flow, disanfang_orders=:disanfang_orders,
                xinli_flow=:xinli_flow, xinli_orders=:xinli_orders,
                zhifu_flow=:zhifu_flow, zhifu_orders=:zhifu_orders,
                yuancheng_flow=:yuancheng_flow, yuancheng_orders=:yuancheng_orders,
                huiyuan_flow=:huiyuan_flow, huiyuan_orders=:huiyuan_orders,
                disanfang_tj_flow=:disanfang_tj_flow, disanfang_tj_orders=:disanfang_tj_orders,
                shangcheng_flow=:shangcheng_flow, shangcheng_orders=:shangcheng_orders,
                daily_total_flow=:daily_total_flow,
                daily_flow_increment=:daily_flow_increment, daily_flow_ratio=:daily_flow_ratio,
                created_at=:created_at
            WHERE date=:date
        ''', r)
print(f'  ✅ UPDATE {len(update_dates)} 条')

conn.commit()

# 验证
cursor.execute('SELECT COUNT(*), MIN(date), MAX(date), SUM(CASE WHEN daily_total_flow > 0 THEN 1 ELSE 0 END) FROM duizhang_summary_2026')
cnt, mn, mx, active = cursor.fetchone()
print(f'\n📊 汇总表: {cnt} 条, 日期范围 {mn} ~ {mx}, 有数据 {active} 天')

# 检查最近5天
cursor.execute('SELECT date, daily_total_flow FROM duizhang_summary_2026 WHERE date >= date("now","-10 days") ORDER BY date')
print('\n最近10天:')
for r in cursor.fetchall():
    print(f'  {r[0]}: ¥{r[1]:.2f}万')

conn.close()
print('\n✅ UPSERT 完成!')
