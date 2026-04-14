#!/usr/bin/env python3
"""导入 4月10日明细数据到 daily_flow_2026_apr"""
import pandas as pd
import sqlite3
from datetime import datetime

DB_PATH = '/home/openclaw/.openclaw/workspace/business_flow.db'
EXCEL = '/home/openclaw/.openclaw/workspace/业务对账统计明细-20260410084654.xlsx'

# 跳过前5行标题行（0-4行是表头+说明）
df = pd.read_excel(EXCEL, header=None, skiprows=4)
df.columns = [
    '商户订单号','交易流水号','退费批次号','业务订单号','支付方式/账号','收退标识',
    '机构名称','机构编码','所在省份','运营负责人','业绩类目','业绩子类目','业务类型',
    '商品子类别','运营分类','商品id','商品名称','业务完成状态','业务完成时间',
    '财务入账时间','数据状态','收款商户','订单金额','优惠金额','实际支付金额',
    '代缴金额','押金','物流费','医院分账金额','医院分账结算状态','医院分成比例',
    '第三方名称','第三方分账金额','第三方分账结算状态','第三方分成比例','医生积分',
    '医生分账结算状态','医生分成比例','平台留存','平台结算状态','交易时间',
    '对应收款单的支付时间','执行医生（服务人员）','执行医生工号','院内或院外',
    '核对时间','是否取消','渠道金额','关联打款编号','所属团队','是否工作日完成',
    '转介医生','转介医生工号','线上或线下'
]

# 清理空行
df = df[df['商户订单号'].notna()].copy()
print(f"📖 读取到 {len(df):,} 条明细记录")

# 映射到数据库字段
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
        'yewu_wancheng_shijian': str(row['业务完成时间']) if pd.notna(row['业务完成时间']) else '',
        'caiwu_ruzhang_shijian': str(row['财务入账时间']) if pd.notna(row['财务入账时间']) else '',
        'shoukuan_shanghu': str(row['收款商户']) if pd.notna(row['收款商户']) else '',
        'order_amount': float(row['订单金额']) if pd.notna(row['订单金额']) else 0.0,
        'amount': float(row['实际支付金额']) if pd.notna(row['实际支付金额']) else 0.0,
        'created_at': now,
    })

print(f"💾 构建 {len(records):,} 条数据库记录")

# 连接数据库
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# 获取已有 order_id
cursor.execute("SELECT order_id FROM daily_flow_2026_apr")
existing_ids = set(row[0] for row in cursor.fetchall())

# 过滤已存在的（增量）
new_records = [r for r in records if r['order_id'] not in existing_ids]
skipped = len(records) - len(new_records)
print(f"⏭️  跳过已存在: {skipped:,} 条")
print(f"➕ 新增: {len(new_records):,} 条")

if new_records:
    cursor.executemany("""
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
    """, new_records)
    conn.commit()
    
    # 统计
    cursor.execute("""
        SELECT COUNT(*), SUM(amount), 
               MIN(yewu_wancheng_shijian), MAX(yewu_wancheng_shijian)
        FROM daily_flow_2026_apr
    """)
    total, total_amount, min_t, max_t = cursor.fetchone()
    print(f"\n📊 明细表总计: {total:,} 条, ¥{total_amount:,.2f}")
    print(f"📅 时间范围: {min_t} ~ {max_t}")

conn.close()
print("\n✅ 导入完成!")
