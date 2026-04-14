#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
导入 2025 年对账业务总表到 SQLite 数据库
"""

import pandas as pd
import sqlite3
from datetime import datetime
import glob

# 配置
WORKSPACE = '/home/openclaw/.openclaw/workspace'
files = glob.glob(f'{WORKSPACE}/*新流水*2025*.xlsx')
if not files:
    raise FileNotFoundError("找不到新流水 2025 文件")

EXCEL_FILE = files[0]
DB_PATH = f'{WORKSPACE}/business_flow.db'
TABLE_NAME = 'duizhang_summary_2025'  # 对账汇总 2025

def create_table(conn):
    """创建 2025 年对账汇总表"""
    cursor = conn.cursor()
    
    cursor.execute(f'DROP TABLE IF EXISTS {TABLE_NAME}')
    
    create_sql = f'''
    CREATE TABLE {TABLE_NAME} (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT,
        ywul_class_flow REAL, ywul_class_orders INTEGER,
        chufang_flow REAL, chufang_orders INTEGER,
        tiujian_flow REAL, tiujian_orders INTEGER,
        jianguan_flow REAL, jianguan_orders INTEGER,
        disanfang_flow REAL, disanfang_orders INTEGER,
        xinli_flow REAL, xinli_orders INTEGER,
        zhifu_flow REAL, zhifu_orders INTEGER,
        yuancheng_flow REAL, yuancheng_orders INTEGER,
        huiyuan_flow REAL, huiyuan_orders INTEGER,
        disanfang_tj_flow REAL, disanfang_tj_orders INTEGER,
        shangcheng_flow REAL, shangcheng_orders INTEGER,
        daily_total_flow REAL,
        daily_flow_increment REAL,
        daily_flow_ratio REAL,
        created_at TEXT
    )
    '''
    
    cursor.execute(create_sql)
    conn.commit()
    print(f'✅ 表 {TABLE_NAME} 创建成功')

def import_data():
    """导入数据"""
    print(f"\n{'='*70}")
    print(f"📊 导入 2025 年对账业务总表")
    print(f"{'='*70}\n")
    
    print("📁 正在读取 Excel 文件...")
    print(f"   文件：{EXCEL_FILE}")
    
    # 读取数据
    df = pd.read_excel(EXCEL_FILE, header=None, skiprows=4)
    print(f"   读取到 {len(df):,} 行数据")
    
    # 重命名列
    df.columns = [
        '日期', '咨询流水', '咨询订单', '处方流水', '处方订单', '体检流水', '体检订单',
        '健管流水', '健管订单', '第三方流水', '第三方订单', '心理流水', '心理订单',
        '支付流水', '支付订单', '远程流水', '远程订单', '会员流水', '会员订单',
        '第三方体检流水', '第三方体检订单', '商城流水', '商城订单',
        '日总流水', '日流水增量', '日流水环比', 'extra'
    ]
    
    # 清理数据
    df = df[df['日期'].notna()]
    df = df[df['日期'] != '总计']
    df['日期'] = pd.to_datetime(df['日期'], errors='coerce')
    df = df[df['日期'].notna()]
    df['日期'] = df['日期'].dt.strftime('%Y-%m-%d')
    
    conn = sqlite3.connect(DB_PATH)
    
    try:
        print(f"\n📋 创建表...")
        create_table(conn)
        
        print(f"\n💾 正在导入数据...")
        records = []
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        for idx, row in df.iterrows():
            record = {
                'date': row['日期'],
                'ywul_class_flow': float(row['咨询流水']) if pd.notna(row['咨询流水']) else 0.0,
                'ywul_class_orders': int(row['咨询订单']) if pd.notna(row['咨询订单']) else 0,
                'chufang_flow': float(row['处方流水']) if pd.notna(row['处方流水']) else 0.0,
                'chufang_orders': int(row['处方订单']) if pd.notna(row['处方订单']) else 0,
                'tiujian_flow': float(row['体检流水']) if pd.notna(row['体检流水']) else 0.0,
                'tiujian_orders': int(row['体检订单']) if pd.notna(row['体检订单']) else 0,
                'jianguan_flow': float(row['健管流水']) if pd.notna(row['健管流水']) else 0.0,
                'jianguan_orders': int(row['健管订单']) if pd.notna(row['健管订单']) else 0,
                'disanfang_flow': float(row['第三方流水']) if pd.notna(row['第三方流水']) else 0.0,
                'disanfang_orders': int(row['第三方订单']) if pd.notna(row['第三方订单']) else 0,
                'xinli_flow': float(row['心理流水']) if pd.notna(row['心理流水']) else 0.0,
                'xinli_orders': int(row['心理订单']) if pd.notna(row['心理订单']) else 0,
                'zhifu_flow': float(row['支付流水']) if pd.notna(row['支付流水']) else 0.0,
                'zhifu_orders': int(row['支付订单']) if pd.notna(row['支付订单']) else 0,
                'yuancheng_flow': float(row['远程流水']) if pd.notna(row['远程流水']) else 0.0,
                'yuancheng_orders': int(row['远程订单']) if pd.notna(row['远程订单']) else 0,
                'huiyuan_flow': float(row['会员流水']) if pd.notna(row['会员流水']) else 0.0,
                'huiyuan_orders': int(row['会员订单']) if pd.notna(row['会员订单']) else 0,
                'disanfang_tj_flow': float(row['第三方体检流水']) if pd.notna(row['第三方体检流水']) else 0.0,
                'disanfang_tj_orders': int(row['第三方体检订单']) if pd.notna(row['第三方体检订单']) else 0,
                'shangcheng_flow': float(row['商城流水']) if pd.notna(row['商城流水']) else 0.0,
                'shangcheng_orders': int(row['商城订单']) if pd.notna(row['商城订单']) else 0,
                'daily_total_flow': float(row['日总流水']) if pd.notna(row['日总流水']) else 0.0,
                'daily_flow_increment': float(row['日流水增量']) if pd.notna(row['日流水增量']) else 0.0,
                'daily_flow_ratio': float(row['日流水环比']) if pd.notna(row['日流水环比']) else 0.0,
                'created_at': now
            }
            records.append(record)
            
            if (idx + 1) % 50 == 0:
                print(f"   已处理 {idx + 1:,}/{len(df):,} 行...")
        
        # 批量插入
        cursor = conn.cursor()
        
        insert_sql = f'''
        INSERT INTO {TABLE_NAME} (
            date, ywul_class_flow, ywul_class_orders, chufang_flow, chufang_orders,
            tiujian_flow, tiujian_orders, jianguan_flow, jianguan_orders,
            disanfang_flow, disanfang_orders, xinli_flow, xinli_orders,
            zhifu_flow, zhifu_orders, yuancheng_flow, yuancheng_orders,
            huiyuan_flow, huiyuan_orders, disanfang_tj_flow, disanfang_tj_orders,
            shangcheng_flow, shangcheng_orders, daily_total_flow,
            daily_flow_increment, daily_flow_ratio, created_at
        ) VALUES (
            :date, :ywul_class_flow, :ywul_class_orders, :chufang_flow, :chufang_orders,
            :tiujian_flow, :tiujian_orders, :jianguan_flow, :jianguan_orders,
            :disanfang_flow, :disanfang_orders, :xinli_flow, :xinli_orders,
            :zhifu_flow, :zhifu_orders, :yuancheng_flow, :yuancheng_orders,
            :huiyuan_flow, :huiyuan_orders, :disanfang_tj_flow, :disanfang_tj_orders,
            :shangcheng_flow, :shangcheng_orders, :daily_total_flow,
            :daily_flow_increment, :daily_flow_ratio, :created_at
        )
        '''
        
        cursor.executemany(insert_sql, records)
        conn.commit()
        
        print(f"\n✅ 成功导入 {len(records):,} 条记录")
        
        # 验证导入结果
        print(f"\n📊 验证导入结果...")
        cursor.execute(f'SELECT COUNT(*) FROM {TABLE_NAME}')
        count = cursor.fetchone()[0]
        print(f"   表中总记录数：{count:,} 条")
        
        # 统计信息
        cursor.execute(f'''
            SELECT 
                MIN(date) as first_date,
                MAX(date) as last_date,
                SUM(daily_total_flow) as total_flow
            FROM {TABLE_NAME}
        ''')
        stats = cursor.fetchone()
        
        print(f"\n📈 数据统计:")
        print(f"   日期范围：{stats[0]} ~ {stats[1]}")
        print(f"   总流水：¥{stats[2]:,.2f} 万元")
        
        print(f"\n{'='*70}")
        print(f"✅ 2025 年数据导入完成！")
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
