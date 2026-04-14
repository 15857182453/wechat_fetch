#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
导入2025年全年数据到数据库 - 优化版本
"""

import sqlite3
import pandas as pd
import time
import glob
import os

start_time = time.time()

# 连接数据库
db_path = "/home/openclaw/.openclaw/workspace/business_flow.db"
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# 创建表
print("创建数据表 daily_flow_2025...")
cursor.execute('''
CREATE TABLE IF NOT EXISTS daily_flow_2025 (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id TEXT,
    trans_no TEXT,
    refund_batch_no TEXT,
    biz_order_no TEXT,
    pay_method TEXT,
    pay_status TEXT,
    institution TEXT,
    institution_code TEXT,
    province TEXT,
    oper_person TEXT,
    ye_wu_lei_mu TEXT,
    ye_wu_zi_lei_mu TEXT,
    yewu_leixing TEXT,
    yewu_wancheng_shijian TEXT,
    caiwu_ruzhang_shijian TEXT,
    shoukuan_shanghu TEXT,
    order_amount REAL,
    amount REAL,
    created_at TEXT
)
''')

# 获取已导入的记录数
cursor.execute("SELECT COUNT(*) FROM daily_flow_2025")
existing = cursor.fetchone()[0]
print(f"已存在记录: {existing}")

# 检查已处理的文件
cursor.execute("SELECT DISTINCT trans_no FROM daily_flow_2025 WHERE trans_no IS NOT NULL LIMIT 10")
cursor.execute("SELECT order_id FROM daily_flow_2025")
existing_ids = set(cursor.fetchall())

# 所有Excel文件
file_pattern = "/mnt/c/Users/44238/Desktop/业务对账数据/2025年/*.xlsx"
files = sorted(glob.glob(file_pattern))
print(f"\n找到 {len(files)} 个Excel文件")

total_rows = 0
total_inserted = 0

for file_path in files:
    filename = os.path.basename(file_path)
    print(f"\n处理: {filename}...")
    
    start = time.time()
    df = pd.read_excel(file_path, usecols=[
        '商户订单号', '交易流水号', '退费批次号', '业务订单号', '支付方式/账号', 
        '收退标识', '机构名称', '机构编码', '所在省份', '运营负责人', '业绩类目', 
        '业绩子类目', '业务类型', '业务完成时间', '财务入账时间', '收款商户',
        '订单金额', '实际支付金额', '交易时间'
    ])
    print(f"  读取: {len(df)} 行")
    
    # 转换数据类型
    df['订单金额'] = pd.to_numeric(df['订单金额'], errors='coerce').fillna(0)
    df['实际支付金额'] = pd.to_numeric(df['实际支付金额'], errors='coerce').fillna(0)
    
    # 转换日期格式
    df['业务完成时间'] = pd.to_datetime(df['业务完成时间'], errors='coerce').dt.strftime('%Y-%m-%d %H:%M:%S')
    df['财务入账时间'] = pd.to_datetime(df['财务入账时间'], errors='coerce').dt.strftime('%Y-%m-%d %H:%M:%S')
    df['交易时间'] = pd.to_datetime(df['交易时间'], errors='coerce').dt.strftime('%Y-%m-%d %H:%M:%S')
    
    # 填充NaN
    df = df.fillna('')
    
    # 转换为元组列表
    records = [
        (
            str(row['商户订单号']), str(row['交易流水号']), str(row['退费批次号']), str(row['业务订单号']),
            str(row['支付方式/账号']), str(row['收退标识']), str(row['机构名称']), str(row['机构编码']),
            str(row['所在省份']), str(row['运营负责人']), str(row['业绩类目']), str(row['业绩子类目']),
            str(row['业务类型']), str(row['业务完成时间']), str(row['财务入账时间']),
            str(row['收款商户']), float(row['订单金额']), float(row['实际支付金额']), str(row['交易时间'])
        )
        for _, row in df.iterrows()
    ]
    
    # 批量插入
    cursor.executemany('''
        INSERT INTO daily_flow_2025 
        (order_id, trans_no, refund_batch_no, biz_order_no, pay_method, pay_status, 
         institution, institution_code, province, oper_person, ye_wu_lei_mu, 
         ye_wu_zi_lei_mu, yewu_leixing, yewu_wancheng_shijian, caiwu_ruzhang_shijian,
         shoukuan_shanghu, order_amount, amount, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', records)
    
    inserted = len(records)
    total_rows += inserted
    total_inserted += inserted
    conn.commit()
    print(f"  插入: {inserted} 行, 耗时: {time.time() - start:.2f}秒")

conn.close()
print(f"\n导入完成！总耗时: {time.time() - start_time:.2f}秒")
print(f"总记录数: {total_inserted}")
