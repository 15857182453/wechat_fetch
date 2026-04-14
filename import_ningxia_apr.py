#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
导入宁夏医科大学总医院 4 月订单数据（4 月 1-6 日）
"""

import pandas as pd
import sqlite3
from datetime import datetime
import os

# 配置
WORKSPACE = '/home/openclaw/.openclaw/workspace'
for f in os.listdir(WORKSPACE):
    if '103517' in f and f.endswith('.xlsx'):
        EXCEL_FILE = os.path.join(WORKSPACE, f)
        break
else:
    raise FileNotFoundError("找不到订单明细文件")

DB_PATH = '/home/openclaw/.openclaw/workspace/business_flow.db'
TABLE_NAME = 'ningxia_orders_2026_apr'  # 宁夏 4 月订单表

def create_table(conn):
    """创建宁夏 4 月订单表"""
    cursor = conn.cursor()
    
    cursor.execute(f'DROP TABLE IF EXISTS {TABLE_NAME}')
    
    create_sql = f'''
    CREATE TABLE {TABLE_NAME} (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_id TEXT, order_type TEXT, order_status TEXT, delivery_status TEXT, delivery_time TEXT,
        refund_status TEXT, refund_apply_time TEXT, purchase_method TEXT, supplier_org TEXT, supplier_pharmacy TEXT,
        receiver_name TEXT, receiver_phone TEXT, province TEXT, city TEXT, district TEXT, street TEXT, community TEXT,
        detail_address TEXT, full_address TEXT, order_user TEXT, order_phone TEXT, marketing_scene TEXT,
        order_time TEXT, payment_time TEXT, payment_trans_no TEXT, order_amount REAL, refund_amount REAL,
        settlement_type TEXT, pre_settle_amount REAL, insurance_amount REAL, self_pay_amount REAL,
        medicine_fee REAL, shipping_fee REAL, discount_amount REAL, dispensing_fee REAL, diagnosis_fee REAL,
        pharmacy_service_fee REAL, registration_fee REAL, platform_prescription_no TEXT,
        his_prescription_code TEXT, his_payment_code TEXT, prescription_type TEXT, prescription_count INTEGER,
        agreement_formula_name TEXT, prescribing_org TEXT, prescribing_dept TEXT, prescribing_doctor TEXT,
        patient_name TEXT, patient_id_no TEXT, prescription_time TEXT, single_medicine_fee REAL,
        single_pharmacy_fee REAL, decoction_method TEXT, is_decocted TEXT, single_decoction_fee REAL,
        created_at TEXT
    )
    '''
    
    cursor.execute(create_sql)
    conn.commit()
    print(f'✅ 表 {TABLE_NAME} 创建成功')
    
    cursor.execute(f'CREATE INDEX IF NOT EXISTS idx_{TABLE_NAME}_order_time ON {TABLE_NAME}(order_time)')
    cursor.execute(f'CREATE INDEX IF NOT EXISTS idx_{TABLE_NAME}_payment_time ON {TABLE_NAME}(payment_time)')
    cursor.execute(f'CREATE INDEX IF NOT EXISTS idx_{TABLE_NAME}_order_id ON {TABLE_NAME}(order_id)')
    cursor.execute(f'CREATE INDEX IF NOT EXISTS idx_{TABLE_NAME}_prescribing_org ON {TABLE_NAME}(prescribing_org)')
    conn.commit()
    print('✅ 索引创建成功')

def import_data():
    """导入数据"""
    print(f"\n{'='*70}")
    print(f"📊 导入宁夏医科大学总医院 4 月订单数据（4 月 1-6 日）")
    print(f"{'='*70}\n")
    
    print("📁 正在读取 Excel 文件...")
    df = pd.read_excel(EXCEL_FILE)
    print(f"   读取到 {len(df):,} 行数据")
    
    conn = sqlite3.connect(DB_PATH)
    
    try:
        print(f"\n📋 创建表 {TABLE_NAME}...")
        create_table(conn)
        
        print("\n🔄 准备导入数据...")
        records = []
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        for idx, row in df.iterrows():
            def safe_val(val):
                if pd.isna(val):
                    return None
                if isinstance(val, datetime):
                    return val.strftime('%Y-%m-%d %H:%M:%S')
                return str(val)
            
            record = {
                'order_id': safe_val(row.get('订单号')),
                'order_type': safe_val(row.get('订单类型')),
                'order_status': safe_val(row.get('订单状态')),
                'delivery_status': safe_val(row.get('发药状态')),
                'delivery_time': safe_val(row.get('发药时间')),
                'refund_status': safe_val(row.get('退款状态')),
                'refund_apply_time': safe_val(row.get('申请退费时间')),
                'purchase_method': safe_val(row.get('购药方式')),
                'supplier_org': safe_val(row.get('供药药企')),
                'supplier_pharmacy': safe_val(row.get('供药药店')),
                'receiver_name': safe_val(row.get('收货人')),
                'receiver_phone': safe_val(row.get('联系方式')),
                'province': safe_val(row.get('省')),
                'city': safe_val(row.get('市')),
                'district': safe_val(row.get('区县')),
                'street': safe_val(row.get('街道')),
                'community': safe_val(row.get('社区')),
                'detail_address': safe_val(row.get('详细地址')),
                'full_address': safe_val(row.get('收货地址')),
                'order_user': safe_val(row.get('下单用户')),
                'order_phone': safe_val(row.get('下单手机号')),
                'marketing_scene': safe_val(row.get('营销场景')),
                'order_time': safe_val(row.get('下单时间')),
                'payment_time': safe_val(row.get('支付时间')),
                'payment_trans_no': safe_val(row.get('支付流水号')),
                'order_amount': float(row.get('订单金额', 0)) if pd.notna(row.get('订单金额')) else 0.0,
                'refund_amount': float(row.get('退款金额', 0)) if pd.notna(row.get('退款金额')) else 0.0,
                'settlement_type': safe_val(row.get('结算类型')),
                'pre_settle_amount': float(row.get('预结算总金额', 0)) if pd.notna(row.get('预结算总金额')) else 0.0,
                'insurance_amount': float(row.get('医保金额', 0)) if pd.notna(row.get('医保金额')) else 0.0,
                'self_pay_amount': float(row.get('自费金额', 0)) if pd.notna(row.get('自费金额')) else 0.0,
                'medicine_fee': float(row.get('药品费', 0)) if pd.notna(row.get('药品费')) else 0.0,
                'shipping_fee': float(row.get('运费', 0)) if pd.notna(row.get('运费')) else 0.0,
                'discount_amount': float(row.get('优惠金额', 0)) if pd.notna(row.get('优惠金额')) else 0.0,
                'dispensing_fee': float(row.get('代煎费', 0)) if pd.notna(row.get('代煎费')) else 0.0,
                'diagnosis_fee': float(row.get('中医辨证论治费', 0)) if pd.notna(row.get('中医辨证论治费')) else 0.0,
                'pharmacy_service_fee': float(row.get('药事服务费', 0)) if pd.notna(row.get('药事服务费')) else 0.0,
                'registration_fee': float(row.get('挂号费', 0)) if pd.notna(row.get('挂号费')) else 0.0,
                'platform_prescription_no': safe_val(row.get('平台处方单号')),
                'his_prescription_code': safe_val(row.get('HIS 处方编码')),
                'his_payment_code': safe_val(row.get('HIS 缴费编码')),
                'prescription_type': safe_val(row.get('处方类型')),
                'prescription_count': int(row.get('帖数', 0)) if pd.notna(row.get('帖数')) else 0,
                'agreement_formula_name': safe_val(row.get('协定方名称')),
                'prescribing_org': safe_val(row.get('开方机构')),
                'prescribing_dept': safe_val(row.get('开方科室')),
                'prescribing_doctor': safe_val(row.get('开方医生')),
                'patient_name': safe_val(row.get('就诊人姓名')),
                'patient_id_no': safe_val(row.get('证件号')),
                'prescription_time': safe_val(row.get('开方时间')),
                'single_medicine_fee': float(row.get('单方药品费', 0)) if pd.notna(row.get('单方药品费')) else 0.0,
                'single_pharmacy_fee': float(row.get('单方药事服务费', 0)) if pd.notna(row.get('单方药事服务费')) else 0.0,
                'decoction_method': safe_val(row.get('煎法')),
                'is_decocted': safe_val(row.get('是否代煎')),
                'single_decoction_fee': float(row.get('单方代煎费', 0)) if pd.notna(row.get('单方代煎费')) else 0.0,
                'created_at': now
            }
            records.append(record)
            
            if (idx + 1) % 2000 == 0:
                print(f"   已处理 {idx + 1:,}/{len(df):,} 行...")
        
        print(f"\n💾 正在插入数据到数据库...")
        cursor = conn.cursor()
        
        insert_sql = f'''
        INSERT INTO {TABLE_NAME} (
            order_id, order_type, order_status, delivery_status, delivery_time,
            refund_status, refund_apply_time, purchase_method, supplier_org, supplier_pharmacy,
            receiver_name, receiver_phone, province, city, district, street, community,
            detail_address, full_address, order_user, order_phone, marketing_scene,
            order_time, payment_time, payment_trans_no, order_amount, refund_amount,
            settlement_type, pre_settle_amount, insurance_amount, self_pay_amount,
            medicine_fee, shipping_fee, discount_amount, dispensing_fee, diagnosis_fee,
            pharmacy_service_fee, registration_fee, platform_prescription_no,
            his_prescription_code, his_payment_code, prescription_type, prescription_count,
            agreement_formula_name, prescribing_org, prescribing_dept, prescribing_doctor,
            patient_name, patient_id_no, prescription_time, single_medicine_fee,
            single_pharmacy_fee, decoction_method, is_decocted, single_decoction_fee,
            created_at
        ) VALUES (
            :order_id, :order_type, :order_status, :delivery_status, :delivery_time,
            :refund_status, :refund_apply_time, :purchase_method, :supplier_org, :supplier_pharmacy,
            :receiver_name, :receiver_phone, :province, :city, :district, :street, :community,
            :detail_address, :full_address, :order_user, :order_phone, :marketing_scene,
            :order_time, :payment_time, :payment_trans_no, :order_amount, :refund_amount,
            :settlement_type, :pre_settle_amount, :insurance_amount, :self_pay_amount,
            :medicine_fee, :shipping_fee, :discount_amount, :dispensing_fee, :diagnosis_fee,
            :pharmacy_service_fee, :registration_fee, :platform_prescription_no,
            :his_prescription_code, :his_payment_code, :prescription_type, :prescription_count,
            :agreement_formula_name, :prescribing_org, :prescribing_dept, :prescribing_doctor,
            :patient_name, :patient_id_no, :prescription_time, :single_medicine_fee,
            :single_pharmacy_fee, :decoction_method, :is_decocted, :single_decoction_fee,
            :created_at
        )
        '''
        
        cursor.executemany(insert_sql, records)
        conn.commit()
        
        print(f"\n✅ 成功导入 {len(records):,} 条记录")
        
        print(f"\n📊 验证导入结果...")
        cursor.execute(f'SELECT COUNT(*) FROM {TABLE_NAME}')
        count = cursor.fetchone()[0]
        print(f"   表中总记录数：{count:,} 条")
        
        cursor.execute(f'''
            SELECT 
                COUNT(*) as total_orders,
                SUM(order_amount) as total_amount,
                AVG(order_amount) as avg_amount,
                MIN(payment_time) as first_payment,
                MAX(payment_time) as last_payment
            FROM {TABLE_NAME}
            WHERE payment_time IS NOT NULL
        ''')
        stats = cursor.fetchone()
        
        print(f"\n📈 数据统计 (已支付订单):")
        print(f"   总订单数：{stats[0]:,} 单")
        print(f"   总金额：¥{stats[1]:,.2f}")
        print(f"   平均客单价：¥{stats[2]:.2f}")
        print(f"   时间范围：{stats[3]} ~ {stats[4]}")
        
        print(f"\n📅 每日订单分布:")
        cursor.execute('''
            SELECT substr(payment_time, 1, 10) as date, COUNT(*) as cnt, SUM(order_amount) as amount
            FROM {TABLE_NAME}
            WHERE payment_time IS NOT NULL
            GROUP BY 1
            ORDER BY 1
        '''.format(TABLE_NAME=TABLE_NAME))
        for row in cursor.fetchall():
            print(f"   {row[0]}: {row[1]:>5,} 单 | ¥{row[2]:>10,.2f}")
        
        print(f"\n📋 订单状态分布:")
        cursor.execute(f'SELECT order_status, COUNT(*) as cnt FROM {TABLE_NAME} GROUP BY 1 ORDER BY 2 DESC')
        for row in cursor.fetchall():
            status = row[0] if row[0] else 'None'
            print(f"   {status}: {row[1]:,} 单")
        
        print(f"\n{'='*70}")
        print(f"✅ 4 月数据导入完成！")
        print(f"{'='*70}\n")
        
    except Exception as e:
        print(f"\n❌ 导入失败：{e}")
        import traceback
        traceback.print_exc()
        conn.rollback()
        raise
    finally:
        conn.close()

if __name__ == '__main__':
    import_data()
