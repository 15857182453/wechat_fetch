#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
导入对账业务总表（新流水 2026）到 SQLite 数据库
"""

import pandas as pd
import sqlite3
import os
from datetime import datetime

# 配置
WORKSPACE = '/home/openclaw/.openclaw/workspace'

# 查找文件（排除临时文件）
excel_file = None
for f in os.listdir(WORKSPACE):
    if f.startswith('新流水') and '2026' in f and f.endswith('.xlsx') and not f.startswith('~$'):
        excel_file = os.path.join(WORKSPACE, f)
        break

if not excel_file:
    raise FileNotFoundError("找不到新流水 2026.xlsx 文件")

EXCEL_FILE = excel_file
print(f"📁 使用文件：{EXCEL_FILE}")
DB_PATH = f'{WORKSPACE}/business_flow.db'
TABLE_NAME = 'duizhang_summary_2026'  # 对账汇总 2026

def create_table(conn):
    """创建对账汇总表"""
    cursor = conn.cursor()
    
    cursor.execute(f'DROP TABLE IF EXISTS {TABLE_NAME}')
    
    create_sql = f'''
    CREATE TABLE {TABLE_NAME} (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT,                    -- 日期
        
        -- 咨询/复诊/护理
        ywul_class_flow REAL,         -- 流水（万元）
        ywul_class_orders INTEGER,    -- 订单数
        
        -- 处方服务 (便捷购药)
        chufang_flow REAL,
        chufang_orders INTEGER,
        
        -- 自营体检
        tiujian_flow REAL,
        tiujian_orders INTEGER,
        
        -- 自营健管
        jianguan_flow REAL,
        jianguan_orders INTEGER,
        
        -- 第三方服务
        disanfang_flow REAL,
        disanfang_orders INTEGER,
        
        -- 心理咨询
        xinli_flow REAL,
        xinli_orders INTEGER,
        
        -- 支付类
        zhifu_flow REAL,
        zhifu_orders INTEGER,
        
        -- 远程服务
        yuancheng_flow REAL,
        yuancheng_orders INTEGER,
        
        -- 会员服务
        huiyuan_flow REAL,
        huiyuan_orders INTEGER,
        
        -- 第三方体检
        disanfang_tj_flow REAL,
        disanfang_tj_orders INTEGER,
        
        -- 在线商城
        shangcheng_flow REAL,
        shangcheng_orders INTEGER,
        
        -- 汇总
        daily_total_flow REAL,        -- 日总流水（万元）
        daily_flow_increment REAL,    -- 日流水增量（万元）
        daily_flow_ratio REAL,        -- 日流水环比
        
        created_at TEXT
    )
    '''
    
    cursor.execute(create_sql)
    conn.commit()
    print(f'✅ 表 {TABLE_NAME} 创建成功')

def import_data():
    """导入数据"""
    print(f"\n{'='*70}")
    print(f"📊 导入对账业务总表（新流水 2026）")
    print(f"{'='*70}\n")
    
    print("📁 正在读取 Excel 文件...")
    print(f"   文件：{EXCEL_FILE}")
    
    # 读取数据（前 4 行是表头，从第 5 行开始是数据）
    df = pd.read_excel(EXCEL_FILE, header=None, skiprows=4)
    print(f"   读取到 {len(df):,} 行数据")
    
    # 重命名列（28 列）
    df.columns = [
        '日期', '咨询流水', '咨询订单', '处方流水', '处方订单', '体检流水', '体检订单',
        '健管流水', '健管订单', '第三方流水', '第三方订单', '心理流水', '心理订单',
        '支付流水', '支付订单', '远程流水', '远程订单', '会员流水', '会员订单',
        '第三方体检流水', '第三方体检订单', '商城流水', '商城订单',
        'extra1', '日总流水', '日流水增量', '日流水环比', 'extra2'
    ]
    
    # 清理数据
    df = df[df['日期'].notna()]
    df = df[df['日期'] != '总计']  # 过滤总计行
    df['日期'] = pd.to_datetime(df['日期'], errors='coerce')
    df = df[df['日期'].notna()]  # 过滤无法转换的日期
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
                'date': row['日期'] if pd.notna(row['日期']) else None,
                # 所有流水列单位是元，需要转换为万元
                'ywul_class_flow': float(row['咨询流水']) / 10000 if pd.notna(row['咨询流水']) else 0.0,
                'ywul_class_orders': int(row['咨询订单']) if pd.notna(row['咨询订单']) else 0,
                'chufang_flow': float(row['处方流水']) / 10000 if pd.notna(row['处方流水']) else 0.0,
                'chufang_orders': int(row['处方订单']) if pd.notna(row['处方订单']) else 0,
                'tiujian_flow': float(row['体检流水']) / 10000 if pd.notna(row['体检流水']) else 0.0,
                'tiujian_orders': int(row['体检订单']) if pd.notna(row['体检订单']) else 0,
                'jianguan_flow': float(row['健管流水']) / 10000 if pd.notna(row['健管流水']) else 0.0,
                'jianguan_orders': int(row['健管订单']) if pd.notna(row['健管订单']) else 0,
                'disanfang_flow': float(row['第三方流水']) / 10000 if pd.notna(row['第三方流水']) else 0.0,
                'disanfang_orders': int(row['第三方订单']) if pd.notna(row['第三方订单']) else 0,
                'xinli_flow': float(row['心理流水']) / 10000 if pd.notna(row['心理流水']) else 0.0,
                'xinli_orders': int(row['心理订单']) if pd.notna(row['心理订单']) else 0,
                'zhifu_flow': float(row['支付流水']) / 10000 if pd.notna(row['支付流水']) else 0.0,
                'zhifu_orders': int(row['支付订单']) if pd.notna(row['支付订单']) else 0,
                'yuancheng_flow': float(row['远程流水']) / 10000 if pd.notna(row['远程流水']) else 0.0,
                'yuancheng_orders': int(row['远程订单']) if pd.notna(row['远程订单']) else 0,
                'huiyuan_flow': float(row['会员流水']) / 10000 if pd.notna(row['会员流水']) else 0.0,
                'huiyuan_orders': int(row['会员订单']) if pd.notna(row['会员订单']) else 0,
                'disanfang_tj_flow': float(row['第三方体检流水']) / 10000 if pd.notna(row['第三方体检流水']) else 0.0,
                'disanfang_tj_orders': int(row['第三方体检订单']) if pd.notna(row['第三方体检订单']) else 0,
                'shangcheng_flow': float(row['商城流水']) / 10000 if pd.notna(row['商城流水']) else 0.0,
                'shangcheng_orders': int(row['商城订单']) if pd.notna(row['商城订单']) else 0,
                # 日总流水、日流水增量单位是万元（新 Excel 格式），无需转换
                'daily_total_flow': float(row['日总流水']) if pd.notna(row['日总流水']) else 0.0,
                'daily_flow_increment': float(row['日流水增量']) if pd.notna(row['日流水增量']) else 0.0,
                'daily_flow_ratio': float(row['日流水环比']) if pd.notna(row['日流水环比']) else 0.0,
                'created_at': now
            }
            records.append(record)
            
            if (idx + 1) % 20 == 0:
                print(f"   已处理 {idx + 1:,}/{len(df):,} 行...")
        
        # 批量插入
        cursor = conn.cursor()
        
        # 检查重复数据
        cursor.execute(f"SELECT date, COUNT(*) FROM {TABLE_NAME} GROUP BY date HAVING COUNT(*) > 1")
        duplicates = cursor.fetchall()
        if duplicates:
            print(f"\n⚠️  发现 {len(duplicates)} 个重复日期，将自动更新...")
        
        insert_sql = f'''
        INSERT OR REPLACE INTO {TABLE_NAME} (
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
        
        # 统计新增/更新
        cursor.execute(f"SELECT date FROM {TABLE_NAME}")
        existing_dates = set(row[0] for row in cursor.fetchall())
        
        cursor.executemany(insert_sql, records)
        conn.commit()
        
        new_count = sum(1 for r in records if r['date'] not in existing_dates)
        update_count = len(records) - new_count
        
        if update_count > 0:
            print(f"   📝 更新 {update_count} 条已有记录")
        if new_count > 0:
            print(f"   ➕ 新增 {new_count} 条记录")
        
        print(f"\n✅ 共处理 {len(records):,} 条记录")
        
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
        print(f"✅ 数据导入完成！")
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
