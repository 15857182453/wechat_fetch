#!/usr/bin/env python3
"""导入 5/8 明细数据到 daily_flow_2026_may（增量）"""
import pandas as pd
import sqlite3
from datetime import datetime

DB_PATH = '/home/openclaw/.openclaw/workspace/business_flow.db'
EXCEL = '/mnt/e/办公资料/业务对账数据/5-8/业务对账统计明细-20260509072411.xlsx'

df = pd.read_excel(EXCEL, engine='openpyxl')
df = df[df.iloc[:, 0].notna()].copy()
print(f'📖 读取到 {len(df):,} 条明细记录')

# 54列，列18(索引17)是业务完成状态，列19(索引18)是业务完成时间
# 检查列结构
print(f'列17: {df.columns[17]} = {df.iloc[0, 17]}')
print(f'列18: {df.columns[18]} = {df.iloc[0, 18]}')

# 用交易时间(列19/索引18)作为业务时间
df['yewu_wancheng_shijian'] = pd.to_datetime(df.iloc[:, 19], errors='coerce')
valid_dates = df[df['yewu_wancheng_shijian'].notna()]
print(f'📅 有效日期: {len(valid_dates)}/{len(df)} 条')
print(f'📅 日期范围: {valid_dates["yewu_wancheng_shijian"].min()} 到 {valid_dates["yewu_wancheng_shijian"].max()}')

date_dist = valid_dates.groupby(valid_dates['yewu_wancheng_shijian'].dt.date).agg(
    订单数=(df.columns[0], 'count'),
    金额=(df.columns[22], 'sum')
).reset_index()
print('\n📅 日期分布:')
for _, row in date_dist.iterrows():
    print(f'  {row["yewu_wancheng_shijian"]}: {row["订单数"]}条, ¥{row["金额"]:,.2f}')

now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
records = []
for _, row in df.iterrows():
    def safe(val):
        return str(val) if pd.notna(val) else ''
    def safe_float(val):
        return float(val) if pd.notna(val) else 0.0

    records.append({
        'order_id': safe(row.iloc[0]),
        'trans_no': safe(row.iloc[1]),
        'refund_batch_no': safe(row.iloc[2]),
        'biz_order_no': safe(row.iloc[3]),
        'pay_method': safe(row.iloc[4]),
        'pay_status': safe(row.iloc[5]),
        'institution': safe(row.iloc[6]),
        'institution_code': safe(row.iloc[7]),
        'province': safe(row.iloc[8]),
        'oper_person': safe(row.iloc[9]),
        'ye_wu_lei_mu': safe(row.iloc[10]),
        'ye_wu_zi_lei_mu': safe(row.iloc[11]),
        'yewu_leixing': safe(row.iloc[12]),
        'product_subcategory': safe(row.iloc[13]),
        'operation_category': safe(row.iloc[14]),
        'product_id': safe(row.iloc[15]),
        'product_name': safe(row.iloc[16]),
        'completion_status': safe(row.iloc[17]),
        'yewu_wancheng_shijian': row['yewu_wancheng_shijian'].strftime('%Y-%m-%d %H:%M:%S') if pd.notna(row['yewu_wancheng_shijian']) else '',
        'caiwu_ruzhang_shijian': safe(row.iloc[19]),
        'data_status': safe(row.iloc[20]),
        'shoukuan_shanghu': safe(row.iloc[21]),
        'order_amount': safe_float(row.iloc[22]),
        'discount_amount': safe_float(row.iloc[23]),
        'amount': safe_float(row.iloc[24]),
        'daijiao_amount': safe_float(row.iloc[25]),
        'deposit': safe_float(row.iloc[26]),
        'logistics_fee': safe_float(row.iloc[27]),
        'hospital_share': safe_float(row.iloc[28]),
        'hospital_share_status': safe(row.iloc[29]),
        'hospital_ratio': safe_float(row.iloc[30]),
        'third_party_name': safe(row.iloc[31]),
        'third_party_amount': safe_float(row.iloc[32]),
        'third_party_share_status': safe(row.iloc[33]),
        'third_party_ratio': safe_float(row.iloc[34]),
        'doctor_points': safe_float(row.iloc[35]),
        'doctor_share_status': safe(row.iloc[36]),
        'doctor_ratio': safe_float(row.iloc[37]),
        'platform_amount': safe_float(row.iloc[38]),
        'platform_status': safe(row.iloc[39]),
        'transaction_time': safe(row.iloc[40]),
        'payment_time': safe(row.iloc[41]),
        'exec_doctor': safe(row.iloc[42]),
        'exec_doctor_id': safe(row.iloc[43]),
        'in_or_out': safe(row.iloc[44]),
        'check_time': safe(row.iloc[45]),
        'is_cancelled': safe(row.iloc[46]),
        'channel_amount': safe_float(row.iloc[47]),
        'payment_ref_no': safe(row.iloc[48]),
        'team': safe(row.iloc[49]),
        'is_workday': safe(row.iloc[50]),
        'ref_doctor': safe(row.iloc[51]),
        'ref_doctor_id': safe(row.iloc[52]),
        'online_offline': safe(row.iloc[53]),
        'created_at': now,
    })

print(f'\n💾 构建 {len(records):,} 条数据库记录')

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()
cursor.execute('SELECT order_id FROM daily_flow_2026_may')
existing_ids = set(row[0] for row in cursor.fetchall())

new_records = [r for r in records if r['order_id'] not in existing_ids]
skipped = len(records) - len(new_records)
print(f'⏭️  跳过已存在: {skipped:,} 条')
print(f'➕ 新增: {len(new_records):,} 条')

if new_records:
    cols = list(new_records[0].keys())
    col_names = ', '.join(cols)
    placeholders = ', '.join([f':{c}' for c in cols])
    cursor.executemany(f'INSERT OR IGNORE INTO daily_flow_2026_may ({col_names}) VALUES ({placeholders})', new_records)
    conn.commit()
    print(f'✅ 成功插入 {len(new_records):,} 条')

cursor.execute('SELECT COUNT(*), SUM(amount) FROM daily_flow_2026_may')
total, total_amount = cursor.fetchone()
print(f'\n📊 may表总计: {total:,} 条，¥{total_amount:,.2f}')

cursor.execute("SELECT substr(yewu_wancheng_shijian,1,10) as d, COUNT(*), ROUND(SUM(amount),2) FROM daily_flow_2026_may WHERE yewu_wancheng_shijian IS NOT NULL AND yewu_wancheng_shijian != '' AND yewu_wancheng_shijian != 'NaT' GROUP BY d ORDER BY d DESC")
for r in cursor.fetchall():
    print(f'  {r[0]}: {r[1]}条, ¥{r[2]:,.2f}')

conn.close()
print('\n✅ 导入完成!')
