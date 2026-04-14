#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
导入 4 月 3 日业务对账明细数据到 SQLite 数据库
"""

import pandas as pd
import sqlite3
from datetime import datetime

# 配置
EXCEL_FILE = '/mnt/c/Users/44238/Desktop/业务对账数据/4-3/业务对账统计明细-20260407090646.xlsx'
DB_PATH = '/home/openclaw/.openclaw/workspace/business_flow.db'
TABLE_NAME = 'daily_flow_2026_apr'
TARGET_DATE = '2026-04-03'

def clean_and_import_data():
    print(f"=== 导入 {TARGET_DATE} 业务对账数据 ===\n")
    
    # 读取 Excel 文件
    print("正在读取 Excel 文件...")
    print(f"文件路径：{EXCEL_FILE}")
    df = pd.read_excel(EXCEL_FILE, sheet_name='业务对账统计明细')
    print(f"成功读取 {len(df)} 行数据")
    
    # 处理日期字段
    df['业务完成时间'] = pd.to_datetime(df['业务完成时间'], errors='coerce')
    df['交易时间'] = pd.to_datetime(df['交易时间'], errors='coerce')
    df['财务入账时间'] = pd.to_datetime(df['财务入账时间'], errors='coerce')
    
    # 显示日期分布
    print("\n=== 数据日期分布 ===")
    df['业务日期'] = df['业务完成时间'].dt.date
    date_counts = df['业务日期'].value_counts().sort_index()
    for date, count in date_counts.items():
        print(f"  {date}: {count} 条")
    
    # 只保留目标日期的数据
    target_date_obj = pd.to_datetime(TARGET_DATE).date()
    df = df[df['业务完成时间'].dt.date == target_date_obj]
    print(f"\n筛选后 {TARGET_DATE} 数据：{len(df)} 行")
    
    # 准备导入数据
    records = []
    
    for idx, row in df.iterrows():
        # 将可能的大数字转换为字符串
        trans_no = str(row['交易流水号']) if pd.notna(row['交易流水号']) else None
        refund_batch_no = str(row['退费批次号']) if pd.notna(row['退费批次号']) else None
        
        # 将订单号也转换为字符串
        order_id = str(row['商户订单号']) if pd.notna(row['商户订单号']) else None
        biz_order_no = str(row['业务订单号']) if pd.notna(row['业务订单号']) else None
        
        # 检查是否有有效数据
        if not order_id or order_id.strip() == '':
            continue
        
        # 构建记录
        record = {
            'order_id': order_id[:50],  # 限制长度
            'trans_no': trans_no[:50] if trans_no else None,
            'refund_batch_no': refund_batch_no[:50] if refund_batch_no else None,
            'biz_order_no': biz_order_no[:50] if biz_order_no else None,
            'pay_method': str(row['支付方式/账号'])[:50] if pd.notna(row['支付方式/账号']) else None,
            'pay_status': str(row['收退标识'])[:10] if pd.notna(row['收退标识']) else None,  # 收费/退费
            'institution': str(row['机构名称'])[:100] if pd.notna(row['机构名称']) else None,
            'institution_code': str(row['机构编码'])[:20] if pd.notna(row['机构编码']) else None,
            'province': str(row['所在省份'])[:20] if pd.notna(row['所在省份']) else None,
            'oper_person': str(row['运营负责人'])[:100] if pd.notna(row['运营负责人']) else None,
            'ye_wu_lei_mu': str(row['业绩类目'])[:100] if pd.notna(row['业绩类目']) else None,
            'ye_wu_zi_lei_mu': str(row['业绩子类目'])[:100] if pd.notna(row['业绩子类目']) else None,
            'yewu_leixing': str(row['业务类型'])[:50] if pd.notna(row['业务类型']) else None,
            'yewu_wancheng_shijian': row['业务完成时间'].strftime('%Y-%m-%d %H:%M:%S') if pd.notna(row['业务完成时间']) else None,
            'caiwu_ruzhang_shijian': row['财务入账时间'].strftime('%Y-%m-%d %H:%M:%S') if pd.notna(row['财务入账时间']) else None,
            'shoukuan_shanghu': str(row['收款商户'])[:50] if pd.notna(row['收款商户']) else None,
            'order_amount': float(row['订单金额']) if pd.notna(row['订单金额']) else 0.0,
            'amount': float(row['实际支付金额']) if pd.notna(row['实际支付金额']) else 0.0,
            'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        records.append(record)
    
    print(f"\n准备导入 {len(records)} 条 {TARGET_DATE} 数据")
    
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
        failed = 0
        
        for record in records:
            try:
                cursor.execute(insert_sql, tuple(record.values()))
                inserted += 1
            except Exception as e:
                failed += 1
                if failed <= 5:  # 只打印前 5 个错误
                    print(f"记录 {inserted} 插入失败：{e}")
                    print(f"  数据：{record}")
        
        conn.commit()
        print(f"\n✅ 成功导入 {inserted} 条记录到 {TABLE_NAME} 表")
        if failed > 0:
            print(f"⚠️ 有 {failed} 条记录插入失败")
        
        # 验证导入结果
        cursor.execute(f"SELECT COUNT(*) FROM {TABLE_NAME}")
        total_count = cursor.fetchone()[0]
        print(f"表 {TABLE_NAME} 当前共有 {total_count} 条记录")
        
        # 按日期统计
        print(f"\n=== {TARGET_DATE} 导入数据统计 ===")
        print(f"  - 原始记录数：{len(df)}")
        print(f"  - 有效记录数：{inserted}")
        print(f"  - 导入失败：{failed}")
        
        # 显示样例数据
        print("\n样例数据（前 3 条）:")
        cursor.execute(f"""
            SELECT order_id, institution, amount, order_amount, yewu_wancheng_shijian 
            FROM {TABLE_NAME} 
            WHERE DATE(yewu_wancheng_shijian) = '{TARGET_DATE}'
            LIMIT 3
        """)
        for row in cursor.fetchall():
            print(f"  {row}")
        
        # 显示金额汇总
        cursor.execute(f"""
            SELECT 
                COUNT(*) as total_records,
                SUM(order_amount) as total_order_amount,
                SUM(amount) as total_amount
            FROM {TABLE_NAME}
            WHERE DATE(yewu_wancheng_shijian) = '{TARGET_DATE}'
        """)
        summary = cursor.fetchone()
        print(f"\n金额汇总 ({TARGET_DATE}):")
        print(f"  - 订单总金额：¥{summary[1]:,.2f}")
        print(f"  - 实付总金额：¥{summary[2]:,.2f}")
        
    except Exception as e:
        print(f"❌ 导入失败：{e}")
        conn.rollback()
        raise
    finally:
        conn.close()
        print(f"\n📊 数据导入完成！时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == '__main__':
    clean_and_import_data()
