#!/usr/bin/env python3
"""导入 5/7 明细数据到 daily_flow_2026_may（增量）"""
import pandas as pd
import sqlite3
from datetime import datetime

DB_PATH = '/home/openclaw/.openclaw/workspace/business_flow.db'
EXCEL = '/mnt/e/办公资料/业务对账数据/5-7/业务对账统计明细-20260508084907.xlsx'

df = pd.read_excel(EXCEL, engine='openpyxl')
df = df[df['商户订单号'].notna()].copy()
print(f'📖 读取到 {len(df):,} 条明细记录')

df['业务完成时间'] = pd.to_datetime(df['业务完成时间'], errors='coerce')
valid_dates = df[df['业务完成时间'].notna()]
print(f'📅 有效日期: {len(valid_dates)}/{len(df)} 条')
print(f'📅 日期范围: {valid_dates["业务完成时间"].min()} 到 {valid_dates["业务完成时间"].max()}')

date_dist = valid_dates.groupby(valid_dates['业务完成时间'].dt.date).agg(
    订单数=('商户订单号', 'count'),
    金额=('实际支付金额', 'sum')
).reset_index()
print('\n📅 日期分布:')
for _, row in date_dist.iterrows():
    print(f'  {row["业务完成时间"]}: {row["订单数"]}条, ¥{row["金额"]:,.2f}')

now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
records = []
for _, row in df.iterrows():
    def safe(val):
        return str(val) if pd.notna(val) else ''
    def safe_float(val):
        return float(val) if pd.notna(val) else 0.0

    records.append({
        'order_id': safe(row['商户订单号']),
        'trans_no': safe(row['交易流水号']),
        'refund_batch_no': safe(row['退费批次号']),
        'biz_order_no': safe(row['业务订单号']),
        'pay_method': safe(row['支付方式/账号']),
        'pay_status': safe(row['收退标识']),
        'institution': safe(row['机构名称']),
        'institution_code': safe(row['机构编码']),
        'province': safe(row['所在省份']),
        'oper_person': safe(row['运营负责人']),
        'ye_wu_lei_mu': safe(row['业绩类目']),
        'ye_wu_zi_lei_mu': safe(row['业绩子类目']),
        'yewu_leixing': safe(row['业务类型']),
        'product_subcategory': safe(row['商品子类别']),
        'operation_category': safe(row['运营分类']),
        'product_id': safe(row['商品id']),
        'product_name': safe(row['商品名称']),
        'completion_status': safe(row['业务完成状态']),
        'yewu_wancheng_shijian': row['业务完成时间'].strftime('%Y-%m-%d %H:%M:%S') if pd.notna(row['业务完成时间']) else '',
        'caiwu_ruzhang_shijian': safe(row['财务入账时间']),
        'data_status': safe(row['数据状态']),
        'shoukuan_shanghu': safe(row['收款商户']),
        'order_amount': safe_float(row['订单金额']),
        'discount_amount': safe_float(row['优惠金额']),
        'amount': safe_float(row['实际支付金额']),
        'daijiao_amount': safe_float(row['代缴金额']),
        'deposit': safe_float(row['押金']),
        'logistics_fee': safe_float(row['物流费']),
        'hospital_share': safe_float(row['医院分账金额']),
        'hospital_share_status': safe(row['医院分账结算状态']),
        'hospital_ratio': safe_float(row['医院分成比例']),
        'third_party_name': safe(row['第三方名称']),
        'third_party_amount': safe_float(row['第三方分账金额']),
        'third_party_share_status': safe(row['第三方分账结算状态']),
        'third_party_ratio': safe_float(row['第三方分成比例']),
        'doctor_points': safe_float(row['医生积分']),
        'doctor_share_status': safe(row['医生分账结算状态']),
        'doctor_ratio': safe_float(row['医生分成比例']),
        'platform_amount': safe_float(row['平台留存']),
        'platform_status': safe(row['平台结算状态']),
        'transaction_time': safe(row['交易时间']),
        'payment_time': safe(row['对应收款单的支付时间']),
        'exec_doctor': safe(row['执行医生（服务人员）']),
        'exec_doctor_id': safe(row['执行医生工号']),
        'in_or_out': safe(row['院内或院外']),
        'check_time': safe(row['核对时间']),
        'is_cancelled': safe(row['是否取消']),
        'channel_amount': safe_float(row['渠道金额']),
        'payment_ref_no': safe(row['关联打款编号']),
        'team': safe(row['所属团队']),
        'is_workday': safe(row['是否工作日完成']),
        'ref_doctor': safe(row['转介医生']),
        'ref_doctor_id': safe(row['转介医生工号']),
        'online_offline': safe(row['线上或线下']),
        'created_at': now,
    })

print(f'\n💾 构建 {len(records):,} 条数据库记录')

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# 获取已有 order_id
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

# 验证
cursor.execute('SELECT COUNT(*), SUM(amount) FROM daily_flow_2026_may')
total, total_amount = cursor.fetchone()
print(f'\n📊 may表总计: {total:,} 条，¥{total_amount:,.2f}')

cursor.execute("SELECT substr(yewu_wancheng_shijian,1,10) as d, COUNT(*), ROUND(SUM(amount),2) FROM daily_flow_2026_may WHERE yewu_wancheng_shijian IS NOT NULL AND yewu_wancheng_shijian != '' AND yewu_wancheng_shijian != 'NaT' GROUP BY d ORDER BY d DESC")
for r in cursor.fetchall():
    print(f'  {r[0]}: {r[1]}条, ¥{r[2]:,.2f}')

conn.close()
print('\n✅ 导入完成!')
