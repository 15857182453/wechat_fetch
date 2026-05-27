#!/usr/bin/env python3
"""导入 5/22 明细数据到 daily_flow_2026_may（增量）"""
import pandas as pd
import sqlite3
from datetime import datetime

DB_PATH = '/home/openclaw/.openclaw/workspace/business_flow.db'
EXCEL = '/home/openclaw/.openclaw/workspace/业务对账统计明细-20260525090616.xlsx'

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
        'product_subcategory': str(row['商品子类别']) if pd.notna(row['商品子类别']) else '',
        'operation_category': str(row['运营分类']) if pd.notna(row['运营分类']) else '',
        'product_id': str(row['商品id']) if pd.notna(row['商品id']) else '',
        'product_name': str(row['商品名称']) if pd.notna(row['商品名称']) else '',
        'completion_status': str(row['业务完成状态']) if pd.notna(row['业务完成状态']) else '',
        'yewu_wancheng_shijian': row['业务完成时间'].strftime('%Y-%m-%d %H:%M:%S') if pd.notna(row['业务完成时间']) and hasattr(row['业务完成时间'], 'strftime') else str(row['业务完成时间']),
        'caiwu_ruzhang_shijian': str(row['财务入账时间']) if pd.notna(row['财务入账时间']) else '',
        'data_status': str(row['数据状态']) if pd.notna(row['数据状态']) else '',
        'shoukuan_shanghu': str(row['收款商户']) if pd.notna(row['收款商户']) else '',
        'order_amount': float(row['订单金额']) if pd.notna(row['订单金额']) else 0.0,
        'discount_amount': float(row['优惠金额']) if pd.notna(row['优惠金额']) else 0.0,
        'amount': float(row['实际支付金额']) if pd.notna(row['实际支付金额']) else 0.0,
        'daijiao_amount': float(row['代缴金额']) if pd.notna(row['代缴金额']) else 0.0,
        'deposit': float(row['押金']) if pd.notna(row['押金']) else 0.0,
        'logistics_fee': float(row['物流费']) if pd.notna(row['物流费']) else 0.0,
        'hospital_share': float(row['医院分账金额']) if pd.notna(row['医院分账金额']) else 0.0,
        'hospital_share_status': str(row['医院分账结算状态']) if pd.notna(row['医院分账结算状态']) else '',
        'hospital_ratio': float(row['医院分成比例']) if pd.notna(row['医院分成比例']) else 0.0,
        'third_party_name': str(row['第三方名称']) if pd.notna(row['第三方名称']) else '',
        'third_party_amount': float(row['第三方分账金额']) if pd.notna(row['第三方分账金额']) else 0.0,
        'third_party_share_status': str(row['第三方分账结算状态']) if pd.notna(row['第三方分账结算状态']) else '',
        'third_party_ratio': float(row['第三方分成比例']) if pd.notna(row['第三方分成比例']) else 0.0,
        'doctor_points': float(row['医生积分']) if pd.notna(row['医生积分']) else 0.0,
        'doctor_share_status': str(row['医生分账结算状态']) if pd.notna(row['医生分账结算状态']) else '',
        'doctor_ratio': float(row['医生分成比例']) if pd.notna(row['医生分成比例']) else 0.0,
        'platform_amount': float(row['平台留存']) if pd.notna(row['平台留存']) else 0.0,
        'platform_status': str(row['平台结算状态']) if pd.notna(row['平台结算状态']) else '',
        'transaction_time': str(row['交易时间']) if pd.notna(row['交易时间']) else '',
        'payment_time': str(row['对应收款单的支付时间']) if pd.notna(row['对应收款单的支付时间']) else '',
        'exec_doctor': str(row['执行医生（服务人员）']) if pd.notna(row['执行医生（服务人员）']) else '',
        'exec_doctor_id': str(row['执行医生工号']) if pd.notna(row['执行医生工号']) else '',
        'in_or_out': str(row['院内或院外']) if pd.notna(row['院内或院外']) else '',
        'check_time': str(row['核对时间']) if pd.notna(row['核对时间']) else '',
        'is_cancelled': str(row['是否取消']) if pd.notna(row['是否取消']) else '',
        'channel_amount': float(row['渠道金额']) if pd.notna(row['渠道金额']) else 0.0,
        'payment_ref_no': str(row['关联打款编号']) if pd.notna(row['关联打款编号']) else '',
        'team': str(row['所属团队']) if pd.notna(row['所属团队']) else '',
        'is_workday': str(row['是否工作日完成']) if pd.notna(row['是否工作日完成']) else '',
        'ref_doctor': str(row['转介医生']) if pd.notna(row['转介医生']) else '',
        'ref_doctor_id': str(row['转介医生工号']) if pd.notna(row['转介医生工号']) else '',
        'online_offline': str(row['线上或线下']) if pd.notna(row['线上或线下']) else '',
        'created_at': now,
    })

print(f'\n💾 构建 {len(records):,} 条数据库记录')

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# 增量去重
cursor.execute('SELECT order_id FROM daily_flow_2026_may')
existing_ids = set(row[0] for row in cursor.fetchall())

new_records = [r for r in records if r['order_id'] not in existing_ids]
skipped = len(records) - len(new_records)
print(f'⏭️  跳过已存在：{skipped:,} 条')
print(f'➕ 新增：{len(new_records):,} 条')

if new_records:
    cursor.executemany('''
        INSERT OR IGNORE INTO daily_flow_2026_may (
            order_id, trans_no, refund_batch_no, biz_order_no, pay_method,
            pay_status, institution, institution_code, province, oper_person,
            ye_wu_lei_mu, ye_wu_zi_lei_mu, yewu_leixing,
            product_subcategory, operation_category, product_id, product_name,
            completion_status, yewu_wancheng_shijian, caiwu_ruzhang_shijian,
            data_status, shoukuan_shanghu,
            order_amount, discount_amount, amount, daijiao_amount, deposit,
            logistics_fee, hospital_share, hospital_share_status, hospital_ratio,
            third_party_name, third_party_amount, third_party_share_status, third_party_ratio,
            doctor_points, doctor_share_status, doctor_ratio,
            platform_amount, platform_status,
            transaction_time, payment_time, exec_doctor, exec_doctor_id,
            in_or_out, check_time, is_cancelled, channel_amount, payment_ref_no,
            team, is_workday, ref_doctor, ref_doctor_id, online_offline, created_at
        ) VALUES (
            :order_id, :trans_no, :refund_batch_no, :biz_order_no, :pay_method,
            :pay_status, :institution, :institution_code, :province, :oper_person,
            :ye_wu_lei_mu, :ye_wu_zi_lei_mu, :yewu_leixing,
            :product_subcategory, :operation_category, :product_id, :product_name,
            :completion_status, :yewu_wancheng_shijian, :caiwu_ruzhang_shijian,
            :data_status, :shoukuan_shanghu,
            :order_amount, :discount_amount, :amount, :daijiao_amount, :deposit,
            :logistics_fee, :hospital_share, :hospital_share_status, :hospital_ratio,
            :third_party_name, :third_party_amount, :third_party_share_status, :third_party_ratio,
            :doctor_points, :doctor_share_status, :doctor_ratio,
            :platform_amount, :platform_status,
            :transaction_time, :payment_time, :exec_doctor, :exec_doctor_id,
            :in_or_out, :check_time, :is_cancelled, :channel_amount, :payment_ref_no,
            :team, :is_workday, :ref_doctor, :ref_doctor_id, :online_offline, :created_at
        )
    ''', new_records)
    conn.commit()
    print(f'✅ 成功插入 {len(new_records):,} 条')

# 验证
cursor.execute('SELECT COUNT(*), SUM(amount) FROM daily_flow_2026_may')
total, total_amount = cursor.fetchone()
print(f'\n📊 明细表总计：{total:,} 条，¥{total_amount:,.2f}')

# 5/22 数据验证
cursor.execute("""
    SELECT substr(yewu_wancheng_shijian,1,10) as d, COUNT(*), SUM(amount)
    FROM daily_flow_2026_may
    WHERE d = '2026-05-22'
    GROUP BY d
""")
for r in cursor.fetchall():
    print(f'  {r[0]}: {r[1]}条, ¥{r[2]:,.2f}')

conn.close()
print('\n✅ 导入完成!')
