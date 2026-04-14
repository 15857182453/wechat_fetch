#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
导入Excel对账数据到SQLite数据库
处理结构：每行代表一个业务分类的汇总数据
"""

import pandas as pd
import sqlite3
from datetime import datetime

# 配置
EXCEL_FILE = '/mnt/c/Users/44238/Desktop/业务对账数据/4-2/流水-20260403.xlsx'
DB_PATH = '/home/openclaw/.openclaw/workspace/business_flow.db'
TABLE_NAME = 'daily_flow_2026_apr'

def clean_and_import_data():
    # 读取Excel文件
    print("正在读取Excel文件...")
    df = pd.read_excel(EXCEL_FILE, sheet_name='Sheet')
    print(f"成功读取 {len(df)} 行数据")
    
    # 解析数据结构
    records = []
    
    for idx in range(len(df)):
        row = df.iloc[idx]
        
        # 基本信息
        business_type = row['业务分类'] if pd.notna(row['业务分类']) else '未知'
        total_amount = float(row['金额（元）']) if pd.notna(row['金额（元）']) else 0
        total_orders = int(row['订单']) if pd.notna(row['订单']) else 0
        
        # 收集所有医院相关信息
        hospitals = []
        if pd.notna(row['医院']) and str(row['医院']).strip():
            hospitals.append(('医院', str(row['医院']).strip(), 
                            float(row['金额（元）.1']) if pd.notna(row['金额（元）.1']) else 0,
                            int(row['订单.1']) if pd.notna(row['订单.1']) else 0))
        if pd.notna(row['医院.1']) and str(row['医院.1']).strip():
            hospitals.append(('医院.1', str(row['医院.1']).strip(),
                            float(row['金额（元）.2']) if pd.notna(row['金额（元）.2']) else 0,
                            int(row['订单.2']) if pd.notna(row['订单.2']) else 0))
        
        # 创建汇总记录
        record = {
            'order_id': f"SUM{datetime.now().strftime('%Y%m%d%H%M%S')}{idx:06d}",
            'trans_no': f"SUM20260403{idx:06d}",
            'refund_batch_no': None,
            'biz_order_no': f"SUM{idx:06d}",
            'pay_method': None,
            'pay_status': '已汇总',
            'institution': '汇总数据',
            'institution_code': None,
            'province': None,
            'oper_person': None,
            'ye_wu_lei_mu': business_type,
            'ye_wu_zi_lei_mu': None,
            'yewu_leixing': None,
            'yewu_wancheng_shijian': None,
            'caiwu_ruzhang_shijian': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'shoukuan_shanghu': None,
            'order_amount': float(total_orders),
            'amount': float(total_amount),
            'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        records.append(record)
        
        # 如果存在医院明细，也创建记录
        for hospital_idx, (hcol, hospital, amount, order_count) in enumerate(hospitals):
            hospital_record = {
                'order_id': f"HOSP{datetime.now().strftime('%Y%m%d%H%M%S')}{idx:03d}{hospital_idx:02d}",
                'trans_no': f"HOSP{idx:03d}{hospital_idx:02d}",
                'refund_batch_no': None,
                'biz_order_no': f"HOSP{idx:03d}",
                'pay_method': None,
                'pay_status': '已汇总',
                'institution': hospital if '(' not in hospital else hospital.split('(')[0].strip(),
                'institution_code': None,
                'province': None,
                'oper_person': None,
                'ye_wu_lei_mu': business_type,
                'ye_wu_zi_lei_mu': hospital if '(' in hospital else None,
                'yewu_leixing': None,
                'yewu_wancheng_shijian': None,
                'caiwu_ruzhang_shijian': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'shoukuan_shanghu': None,
                'order_amount': float(order_count),
                'amount': float(amount),
                'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            records.append(hospital_record)
    
    print(f"\n整理后准备导入 {len(records)} 条记录")
    print(f"  - 汇总记录: {len(df)} 条")
    print(f"  - 医院明细: {len(records) - len(df)} 条")
    
    # 连接数据库并导入
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # 批量插入
        insert_sql = f'''
            INSERT INTO {TABLE_NAME} (
                order_id, trans_no, refund_batch_no, biz_order_no,
                pay_method, pay_status, institution, institution_code, province,
                oper_person, ye_wu_lei_mu, ye_wu_zi_lei_mu, yewu_leixing,
                yewu_wancheng_shijian, caiwu_ruzhang_shijian, shoukuan_shanghu,
                order_amount, amount, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        '''
        
        inserted = 0
        for record in records:
            cursor.execute(insert_sql, tuple(record.values()))
            inserted += 1
        
        conn.commit()
        print(f"\n✅ 成功导入 {inserted} 条记录到 {TABLE_NAME} 表")
        
        # 验证导入结果
        cursor.execute(f"SELECT COUNT(*) FROM {TABLE_NAME}")
        count = cursor.fetchone()[0]
        print(f"表 {TABLE_NAME} 当前共有 {count} 条记录")
        
    except Exception as e:
        print(f"❌ 导入失败: {e}")
        conn.rollback()
    finally:
        conn.close()
        print("\n数据导入完成！")

if __name__ == '__main__':
    clean_and_import_data()
