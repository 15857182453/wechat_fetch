#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
导入宁夏医科大学总医院订单明细数据到 SQLite 数据库
"""

import pandas as pd
import sqlite3
from datetime import datetime
import os

# 配置
import os
WORKSPACE = '/home/openclaw/.openclaw/workspace'
# 找到正确的文件名
for f in os.listdir(WORKSPACE):
    if '103346' in f and f.endswith('.xlsx'):
        EXCEL_FILE = os.path.join(WORKSPACE, f)
        break
else:
    raise FileNotFoundError("找不到订单明细文件")

DB_PATH = '/home/openclaw/.openclaw/workspace/business_flow.db'
TABLE_NAME = 'ningxia_orders_2026_mar'  # 宁夏订单表

def create_table(conn):
    """创建宁夏订单明细表"""
    cursor = conn.cursor()
    
    # 删除旧表（如果需要重新导入）
    cursor.execute(f'DROP TABLE IF EXISTS {TABLE_NAME}')
    
    # 创建表结构（55 列）
    create_sql = f'''
    CREATE TABLE {TABLE_NAME} (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        
        -- 订单基本信息
        order_id TEXT,              -- 订单号
        order_type TEXT,            -- 订单类型
        order_status TEXT,          -- 订单状态
        delivery_status TEXT,       -- 发药状态
        delivery_time TEXT,         -- 发药时间
        refund_status TEXT,         -- 退款状态
        refund_apply_time TEXT,     -- 申请退费时间
        purchase_method TEXT,       -- 购药方式
        
        -- 供药机构
        supplier_org TEXT,          -- 供药药企
        supplier_pharmacy TEXT,     -- 供药药店
        
        -- 收货信息
        receiver_name TEXT,         -- 收货人
        receiver_phone TEXT,        -- 联系方式
        province TEXT,              -- 省
        city TEXT,                  -- 市
        district TEXT,              -- 区县
        street TEXT,                -- 街道
        community TEXT,             -- 社区
        detail_address TEXT,        -- 详细地址
        full_address TEXT,          -- 收货地址
        
        -- 用户信息
        order_user TEXT,            -- 下单用户
        order_phone TEXT,           -- 下单手机号
        marketing_scene TEXT,       -- 营销场景
        
        -- 时间信息
        order_time TEXT,            -- 下单时间
        payment_time TEXT,          -- 支付时间
        payment_trans_no TEXT,      -- 支付流水号
        
        -- 金额信息
        order_amount REAL,          -- 订单金额
        refund_amount REAL,         -- 退款金额
        settlement_type TEXT,       -- 结算类型
        pre_settle_amount REAL,     -- 预结算总金额
        insurance_amount REAL,      -- 医保金额
        self_pay_amount REAL,       -- 自费金额
        medicine_fee REAL,          -- 药品费
        shipping_fee REAL,          -- 运费
        discount_amount REAL,       -- 优惠金额
        dispensing_fee REAL,        -- 代煎费
        diagnosis_fee REAL,         -- 中医辨证论治费
        pharmacy_service_fee REAL,  -- 药事服务费
        registration_fee REAL,      -- 挂号费
        
        -- 处方信息
        platform_prescription_no TEXT,  -- 平台处方单号
        his_prescription_code TEXT,     -- HIS 处方编码
        his_payment_code TEXT,          -- HIS 缴费编码
        prescription_type TEXT,         -- 处方类型
        prescription_count INTEGER,     -- 帖数
        agreement_formula_name TEXT,    -- 协定方名称
        
        -- 开方信息
        prescribing_org TEXT,       -- 开方机构
        prescribing_dept TEXT,      -- 开方科室
        prescribing_doctor TEXT,    -- 开方医生
        
        -- 就诊人信息
        patient_name TEXT,          -- 就诊人姓名
        patient_id_no TEXT,         -- 证件号
        
        -- 处方时间
        prescription_time TEXT,     -- 开方时间
        
        -- 单方费用明细
        single_medicine_fee REAL,   -- 单方药品费
        single_pharmacy_fee REAL,   -- 单方药事服务费
        decoction_method TEXT,      -- 煎法
        is_decocted TEXT,           -- 是否代煎
        single_decoction_fee REAL,  -- 单方代煎费
        
        -- 导入时间
        created_at TEXT             -- 导入时间
    )
    '''
    
    cursor.execute(create_sql)
    conn.commit()
    print(f'✅ 表 {TABLE_NAME} 创建成功')
    
    # 创建索引
    cursor.execute(f'CREATE INDEX idx_order_time ON {TABLE_NAME}(order_time)')
    cursor.execute(f'CREATE INDEX idx_order_id ON {TABLE_NAME}(order_id)')
    cursor.execute(f'CREATE INDEX idx_prescribing_org ON {TABLE_NAME}(prescribing_org)')
    cursor.execute(f'CREATE INDEX idx_order_status ON {TABLE_NAME}(order_status)')
    conn.commit()
    print('✅ 索引创建成功')

def import_data():
    """导入数据"""
    print(f"\n{'='*70}")
    print(f"📊 导入宁夏医科大学总医院订单数据")
    print(f"{'='*70}\n")
    
    # 读取 Excel
    print("📁 正在读取 Excel 文件...")
    df = pd.read_excel(EXCEL_FILE)
    print(f"   读取到 {len(df)} 行数据")
    
    # 连接数据库
    conn = sqlite3.connect(DB_PATH)
    
    try:
        # 创建表
        print(f"\n📋 创建表 {TABLE_NAME}...")
        create_table(conn)
        
        # 准备数据
        print("\n🔄 准备导入数据...")
        records = []
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        for idx, row in df.iterrows():
            # 将 NaN 转换为 None
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
            
            if (idx + 1) % 1000 == 0:
                print(f"   已处理 {idx + 1}/{len(df)} 行...")
        
        # 批量插入
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
        
        print(f"\n✅ 成功导入 {len(records)} 条记录")
        
        # 验证导入结果
        print(f"\n📊 验证导入结果...")
        cursor.execute(f'SELECT COUNT(*) FROM {TABLE_NAME}')
        count = cursor.fetchone()[0]
        print(f"   表中总记录数：{count:,} 条")
        
        # 统计信息
        cursor.execute(f'''
            SELECT 
                COUNT(*) as total_orders,
                SUM(order_amount) as total_amount,
                AVG(order_amount) as avg_amount,
                MIN(order_time) as first_order,
                MAX(order_time) as last_order
            FROM {TABLE_NAME}
        ''')
        stats = cursor.fetchone()
        
        print(f"\n📈 数据统计:")
        print(f"   总订单数：{stats[0]:,} 单")
        print(f"   总金额：¥{stats[1]:,.2f}")
        print(f"   平均客单价：¥{stats[2]:.2f}")
        print(f"   时间范围：{stats[3]} ~ {stats[4]}")
        
        # 按状态统计
        cursor.execute(f'''
            SELECT order_status, COUNT(*) as cnt 
            FROM {TABLE_NAME} 
            GROUP BY order_status
        ''')
        print(f"\n📋 订单状态分布:")
        for row in cursor.fetchall():
            print(f"   {row[0]}: {row[1]:,} 单")
        
        print(f"\n{'='*70}")
        print(f"✅ 数据导入完成！")
        print(f"{'='*70}\n")
        
    except Exception as e:
        print(f"\n❌ 导入失败：{e}")
        conn.rollback()
        raise
    finally:
        conn.close()

if __name__ == '__main__':
    import_data()
