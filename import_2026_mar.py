#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
导入2026年3月数据到数据库 - 新表避免重复
"""

import sqlite3
import pandas as pd
import time
import os

start_time = time.time()

# 连接数据库
db_path = "/home/openclaw/.openclaw/workspace/business_flow.db"
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# 创建表 - 使用新表名避免与daily_flow_30day冲突
print("创建数据表 daily_flow_2026_mar...")
cursor.execute('''
CREATE TABLE IF NOT EXISTS daily_flow_2026_mar (
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

# 文件
file_path = "/home/openclaw/.openclaw/workspace/2026年3月.xlsx"
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
    INSERT INTO daily_flow_2026_mar 
    (order_id, trans_no, refund_batch_no, biz_order_no, pay_method, pay_status, 
     institution, institution_code, province, oper_person, ye_wu_lei_mu, 
     ye_wu_zi_lei_mu, yewu_leixing, yewu_wancheng_shijian, caiwu_ruzhang_shijian,
     shoukuan_shanghu, order_amount, amount, created_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
''', records)

inserted = len(records)
conn.commit()
print(f"  插入: {inserted} 行, 耗时: {time.time() - start:.2f}秒")

conn.close()
print(f"\n导入完成！总耗时: {time.time() - start_time:.2f}秒")
print(f"新表 daily_flow_2026_mar 总记录数: {inserted:,}")
