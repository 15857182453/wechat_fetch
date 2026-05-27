#!/usr/bin/env python3
"""导入 4/21 明细数据到 daily_flow_2026_apr（增量）"""
import pandas as pd
import sqlite3
from datetime import datetime

DB_PATH = '/home/openclaw/.openclaw/workspace/business_flow.db'
EXCEL = '/home/openclaw/.openclaw/workspace/业务对账统计明细-20260427084332.xlsx'

df = pd.read_excel(EXCEL, engine='openpyxl')
df = df[df['商户订单号'].notna()].copy()
print(f'📖 读取到 {len(df):,} 条明细记录')

df['业务完成时间'] = pd.to_datetime(df['业务完成时间'], errors='coerce')
print(f'📅 业务日期范围：{df["业务完成时间"].min()} 到 {df["业务完成时间"].max()}')

date_dist = df.groupby(df['业务完成时间'].dt.date).agg(
    订单数=('商户订单号', 'count'),
    金额=('实际支付金额', 'sum')
).reset_index()
print('\n📅 日期分布:')
for _, row in date_dist.iterrows():
    print(f'  {row["业务完成时间"]}: {row["订单数"]}条, ¥{row["金额"]:,.2f}')

now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
records = []
for _, row in df.iterrows():
    records.append({
        'order_id': str(row['商户订单号']),
        'trans_no': str(row['交易流水号']) if pd.notna(row['交易流水号']) else '',
        'refund_batch_no': str(row['退费批次号']) if pd.notna(row['退费批次号']) else '',
        'biz_order_no': str(row['业务订单号']) if pd.notna(row['业务订单号']) else '',
        'pay_method': str(row['支付方式/账号']) if pd.notna(row['支付方式/账号']) else '',
        'pay_status': str(row['收退标识']) if pd.notna(row['收退标识']) else '',
        'institution': str(row['机构名称']) if pd.notna(row['机构名称']) else '',
        'institution_code': str(row['机构编码']) if pd.notna(row['机构编码']) else '',
        'province': str(row['所在省份']) if pd.notna(row['所在省份']) else '',
        'oper_person': str(row['运营负责人']) if pd.notna(row['运营负责人']) else '',
        'ye_wu_lei_mu': str(row['业绩类目']) if pd.notna(row['业绩类目']) else '',
        'ye_wu_zi_lei_mu': str(row['业绩子类目']) if pd.notna(row['业绩子类目']) else '',
        'yewu_leixing': str(row['业务类型']) if pd.notna(row['业务类型']) else '',
        'yewu_wancheng_shijian': row['业务完成时间'].strftime('%Y-%m-%d %H:%M:%S') if pd.notna(row['业务完成时间']) and hasattr(row['业务完成时间'], 'strftime') else str(row['业务完成时间']),
        'caiwu_ruzhang_shijian': str(row['财务入账时间']) if pd.notna(row['财务入账时间']) else '',
        'shoukuan_shanghu': str(row['收款商户']) if pd.notna(row['收款商户']) else '',
        'order_amount': float(row['订单金额']) if pd.notna(row['订单金额']) else 0.0,
        'amount': float(row['实际支付金额']) if pd.notna(row['实际支付金额']) else 0.0,
        'created_at': now,
    })

print(f'\n💾 构建 {len(records):,} 条数据库记录')

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# 获取已有 order_id（增量去重）
cursor.execute('SELECT order_id FROM daily_flow_2026_apr')
existing_ids = set(row[0] for row in cursor.fetchall())

new_records = [r for r in records if r['order_id'] not in existing_ids]
skipped = len(records) - len(new_records)
print(f'⏭️  跳过已存在：{skipped:,} 条')
print(f'➕ 新增：{len(new_records):,} 条')

if new_records:
    cursor.executemany('''
        INSERT OR IGNORE INTO daily_flow_2026_apr (
            order_id, trans_no, refund_batch_no, biz_order_no, pay_method,
            pay_status, institution, institution_code, province, oper_person,
            ye_wu_lei_mu, ye_wu_zi_lei_mu, yewu_leixing,
            yewu_wancheng_shijian, caiwu_ruzhang_shijian, shoukuan_shanghu,
            order_amount, amount, created_at
        ) VALUES (
            :order_id, :trans_no, :refund_batch_no, :biz_order_no, :pay_method,
            :pay_status, :institution, :institution_code, :province, :oper_person,
            :ye_wu_lei_mu, :ye_wu_zi_lei_mu, :yewu_leixing,
            :yewu_wancheng_shijian, :caiwu_ruzhang_shijian, :shoukuan_shanghu,
            :order_amount, :amount, :created_at
        )
    ''', new_records)
    conn.commit()
    print(f'✅ 成功插入 {len(new_records):,} 条')

# 验证
cursor.execute('SELECT COUNT(*), SUM(amount) FROM daily_flow_2026_apr')
total, total_amount = cursor.fetchone()
print(f'\n📊 明细表总计：{total:,} 条，¥{total_amount:,.2f}')

cursor.execute("SELECT substr(yewu_wancheng_shijian,1,10) as d, COUNT(*), SUM(amount) FROM daily_flow_2026_apr WHERE d IN ('2026-04-21','2026-04-22') GROUP BY d")
for r in cursor.fetchall():
    print(f'  {r[0]}: {r[1]}条, ¥{r[2]:,.2f}')

conn.close()
print('\n✅ 导入完成!')
