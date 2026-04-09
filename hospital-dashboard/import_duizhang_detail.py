#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
业务对账统计明细导入脚本
- 支持完整54列字段
- 自动去重（按商户订单号）
- 增量导入

作者：OpenClaw
"""

import pandas as pd
import sqlite3
import os
from datetime import datetime

DB_PATH = '/home/openclaw/.openclaw/workspace/business_flow.db'
TABLE_NAME = 'duizhang_detail_2026'

def create_table():
    """创建明细表（如果不存在）"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute(f'''
    CREATE TABLE IF NOT EXISTS {TABLE_NAME} (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        merchant_order_no TEXT UNIQUE,
        trans_flow_no TEXT,
        refund_batch_no TEXT,
        biz_order_no TEXT,
        pay_method TEXT,
        pay_status TEXT,
        institution TEXT,
        institution_code TEXT,
        province TEXT,
        oper_manager TEXT,
        biz_category TEXT,
        biz_subcategory TEXT,
        biz_type TEXT,
        product_subtype TEXT,
        oper_class TEXT,
        product_id TEXT,
        product_name TEXT,
        biz_status TEXT,
        biz_complete_time TEXT,
        finance_entry_time TEXT,
        data_status TEXT,
        pay_merchant TEXT,
        order_amount REAL,
        discount_amount REAL,
        actual_amount REAL,
        prepay_amount REAL,
        deposit REAL,
        logistics_fee REAL,
        hospital_share REAL,
        hospital_settle_status TEXT,
        hospital_ratio REAL,
        third_party_name TEXT,
        third_party_share REAL,
        third_party_settle_status TEXT,
        third_party_ratio REAL,
        doctor_points REAL,
        doctor_settle_status TEXT,
        doctor_ratio REAL,
        platform_retain REAL,
        platform_settle_status TEXT,
        trans_time TEXT,
        pay_time TEXT,
        exec_doctor TEXT,
        exec_doctor_no TEXT,
        in_out_hospital TEXT,
        check_time TEXT,
        is_cancel TEXT,
        channel_amount REAL,
        related_pay_no TEXT,
        team TEXT,
        is_workday TEXT,
        refer_doctor TEXT,
        refer_doctor_no TEXT,
        online_offline TEXT,
        created_at TEXT,
        updated_at TEXT
    )
    ''')
    
    # 创建索引
    cursor.execute(f'CREATE INDEX IF NOT EXISTS idx_detail_institution ON {TABLE_NAME}(institution_code)')
    cursor.execute(f'CREATE INDEX IF NOT EXISTS idx_detail_time ON {TABLE_NAME}(biz_complete_time)')
    cursor.execute(f'CREATE INDEX IF NOT EXISTS idx_detail_status ON {TABLE_NAME}(data_status)')
    
    conn.commit()
    conn.close()


def import_detail(file_path):
    """导入明细数据"""
    print("=" * 60)
    print("📊 业务对账统计明细导入")
    print("=" * 60)
    print()
    
    # 创建表
    create_table()
    
    print(f"📁 文件：{file_path}")
    
    # 读取数据
    print("📖 读取 Excel...")
    df = pd.read_excel(file_path)
    print(f"   读取到 {len(df):,} 条记录，{len(df.columns)} 列")
    
    # 连接数据库
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 获取已有订单号
    cursor.execute(f"SELECT merchant_order_no FROM {TABLE_NAME}")
    existing_orders = set(row[0] for row in cursor.fetchall())
    print(f"   数据库已有 {len(existing_orders):,} 条记录")
    
    # 过滤新记录
    new_records = df[df['商户订单号'].notna() & (~df['商户订单号'].isin(existing_orders))]
    print(f"   待导入新记录：{len(new_records):,} 条")
    
    if len(new_records) == 0:
        print("\nℹ️  没有新数据需要导入")
        conn.close()
        return
    
    # 准备插入
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    insert_sql = f'''
    INSERT INTO {TABLE_NAME} (
        merchant_order_no, trans_flow_no, refund_batch_no, biz_order_no,
        pay_method, pay_status, institution, institution_code, province,
        oper_manager, biz_category, biz_subcategory, biz_type, product_subtype,
        oper_class, product_id, product_name, biz_status, biz_complete_time,
        finance_entry_time, data_status, pay_merchant, order_amount,
        discount_amount, actual_amount, prepay_amount, deposit, logistics_fee,
        hospital_share, hospital_settle_status, hospital_ratio, third_party_name,
        third_party_share, third_party_settle_status, third_party_ratio,
        doctor_points, doctor_settle_status, doctor_ratio, platform_retain,
        platform_settle_status, trans_time, pay_time, exec_doctor, exec_doctor_no,
        in_out_hospital, check_time, is_cancel, channel_amount, related_pay_no,
        team, is_workday, refer_doctor, refer_doctor_no, online_offline,
        created_at, updated_at
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 
              ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 
              ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    '''
    
    # 列名映射（54个Excel列 -> 54个数据库列）
    col_map = [
        ('商户订单号', 'merchant_order_no'),
        ('交易流水号', 'trans_flow_no'),
        ('退费批次号', 'refund_batch_no'),
        ('业务订单号', 'biz_order_no'),
        ('支付方式/账号', 'pay_method'),
        ('收退标识', 'pay_status'),
        ('机构名称', 'institution'),
        ('机构编码', 'institution_code'),
        ('所在省份', 'province'),
        ('运营负责人', 'oper_manager'),
        ('业绩类目', 'biz_category'),
        ('业绩子类目', 'biz_subcategory'),
        ('业务类型', 'biz_type'),
        ('商品子类别', 'product_subtype'),
        ('运营分类', 'oper_class'),
        ('商品id', 'product_id'),
        ('商品名称', 'product_name'),
        ('业务完成状态', 'biz_status'),
        ('业务完成时间', 'biz_complete_time'),
        ('财务入账时间', 'finance_entry_time'),
        ('数据状态', 'data_status'),
        ('收款商户', 'pay_merchant'),
        ('订单金额', 'order_amount'),
        ('优惠金额', 'discount_amount'),
        ('实际支付金额', 'actual_amount'),
        ('代缴金额', 'prepay_amount'),
        ('押金', 'deposit'),
        ('物流费', 'logistics_fee'),
        ('医院分账金额', 'hospital_share'),
        ('医院分账结算状态', 'hospital_settle_status'),
        ('医院分成比例', 'hospital_ratio'),
        ('第三方名称', 'third_party_name'),
        ('第三方分账金额', 'third_party_share'),
        ('第三方分账结算状态', 'third_party_settle_status'),
        ('第三方分成比例', 'third_party_ratio'),
        ('医生积分', 'doctor_points'),
        ('医生分账结算状态', 'doctor_settle_status'),
        ('医生分成比例', 'doctor_ratio'),
        ('平台留存', 'platform_retain'),
        ('平台结算状态', 'platform_settle_status'),
        ('交易时间', 'trans_time'),
        ('对应收款单的支付时间', 'pay_time'),
        ('执行医生（服务人员）', 'exec_doctor'),
        ('执行医生工号', 'exec_doctor_no'),
        ('院内或院外', 'in_out_hospital'),
        ('核对时间', 'check_time'),
        ('是否取消', 'is_cancel'),
        ('渠道金额', 'channel_amount'),
        ('关联打款编号', 'related_pay_no'),
        ('所属团队', 'team'),
        ('是否工作日完成', 'is_workday'),
        ('转介医生', 'refer_doctor'),
        ('转介医生工号', 'refer_doctor_no'),
        ('线上或线下', 'online_offline'),
    ]
    
    # Excel列名列表
    excel_cols = [c[0] for c in col_map]
    
    # 批量插入
    batch_size = 500
    inserted = 0
    
    for i in range(0, len(new_records), batch_size):
        batch = new_records.iloc[i:i+batch_size]
        values_list = []
        
        for _, row in batch.iterrows():
            values = []
            for cn_col, db_col in col_map:
                val = row.get(cn_col)
                if pd.isna(val):
                    values.append(None)
                else:
                    values.append(str(val) if isinstance(val, str) else val)
            values.append(now)  # created_at
            values.append(now)  # updated_at
            values_list.append(values)
        
        cursor.executemany(insert_sql, values_list)
        inserted += len(values_list)
        print(f"   已导入 {inserted:,}/{len(new_records):,} 条...")
    
    conn.commit()
    
    # 验证结果
    print()
    print("📊 验证导入结果...")
    cursor.execute(f'SELECT COUNT(*) FROM {TABLE_NAME}')
    total = cursor.fetchone()[0]
    print(f"   表中总记录数：{total:,} 条")
    
    # 统计金额
    cursor.execute(f'SELECT SUM(actual_amount) FROM {TABLE_NAME} WHERE actual_amount > 0')
    total_amount = cursor.fetchone()[0] or 0
    print(f"   累计实际支付金额：¥{total_amount:,.2f}")
    
    # 按机构统计
    print()
    print("📋 各机构订单数（TOP 5）:")
    cursor.execute(f'''
    SELECT institution, COUNT(*) as cnt, SUM(actual_amount) as amt
    FROM {TABLE_NAME}
    GROUP BY institution
    ORDER BY cnt DESC
    LIMIT 5
    ''')
    for row in cursor.fetchall():
        print(f"   {row[0]}: {row[1]:,} 条，¥{row[2]:,.2f}")
    
    # 按状态统计
    print()
    print("📋 数据状态分布:")
    cursor.execute(f'''
    SELECT data_status, COUNT(*) as cnt
    FROM {TABLE_NAME}
    GROUP BY data_status
    ''')
    for row in cursor.fetchall():
        print(f"   {row[0]}: {row[1]:,} 条")
    
    conn.close()
    
    print()
    print("=" * 60)
    print("✅ 明细数据导入完成！")
    print("=" * 60)


if __name__ == '__main__':
    import sys
    
    if len(sys.argv) > 1:
        file_path = sys.argv[1]
    else:
        # 自动查找文件
        workspace = '/home/openclaw/.openclaw/workspace'
        for f in os.listdir(workspace):
            if '业务对账统计明细' in f and f.endswith('.xlsx'):
                file_path = os.path.join(workspace, f)
                break
        else:
            print("❌ 找不到明细文件")
            sys.exit(1)
    
    try:
        import_detail(file_path)
    except Exception as e:
        print(f"\n❌ 导入失败：{e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)