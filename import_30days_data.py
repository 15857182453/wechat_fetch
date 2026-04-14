#!/usr/bin/env python3
"""
导入30天业务对账明细数据到SQLite数据库
功能：读取业务对账统计明细-20260401121717.xlsx
"""

import pandas as pd
import sqlite3
import os
from pathlib import Path
from datetime import datetime

# ==================== 配置 ====================
WORKSPACE = Path('/home/openclaw/.openclaw/workspace')
EXCEL_FILE_30DAYS = '/mnt/c/Users/44238/Desktop/业务对账数据/30天业务数据/业务对账统计明细-20260401121717.xlsx'
DB_FILE = WORKSPACE / 'business_flow.db'

def main():
    print("="*60)
    print("📝 导入30天业务对账明细数据")
    print("="*60)
    
    # 检查文件
    if not os.path.exists(EXCEL_FILE_30DAYS):
        print(f"❌ Excel文件不存在: {EXCEL_FILE_30DAYS}")
        return
    
    # 连接数据库
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    print(f"📁 数据库文件: {DB_FILE}")
    
    try:
        # 创建明细表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS daily_flow_details (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id TEXT,              -- 商户订单号
            trans_no TEXT,              -- 交易流水号
            refund_batch_no TEXT,       -- 退费批次号
            biz_order_no TEXT,          -- 业务订单号
            pay_method TEXT,            -- 支付方式/账号
            pay_status TEXT,            -- 收退标识 (收费/退费)
            institution TEXT,           -- 机构名称
            institution_code TEXT,      -- 机构编码
            province TEXT,              --所在省份
            oper_person TEXT,           -- 运营负责人
            yewu_fumian TEXT,           -- 业务面
            ye_wu_lei_mu TEXT,          -- 业务类目
            ye_wu_zi_lei_mu TEXT,       -- 业务子类目
            pay_time TEXT,              -- 支付时间
            amount REAL,                -- 实际支付金额
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_pay_time ON daily_flow_details(pay_time)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_institution ON daily_flow_details(institution)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_pay_status ON daily_flow_details(pay_status)')
        
        print("✅ 创建明细表完成")
        
        # 读取Excel数据
        print(f"\n📊 正在读取 Excel 数据...")
        df = pd.read_excel(EXCEL_FILE_30DAYS, engine='openpyxl')
        
        print(f"数据行数: {len(df)}")
        print(f"数据列名: {df.columns.tolist()[:20]}")
        
        # 选择需要的列
        selected_cols = [
            '商户订单号', '交易流水号', '退费批次号', '业务订单号',
            '支付方式/账号', '收退标识', '机构名称', '机构编码', '所在省份', '运营负责人',
            '业务面', '业务类目', '业务子类目', '支付时间', '实际支付金额'
        ]
        
        # 重命名列
        rename_map = {
            '商户订单号': 'order_id',
            '交易流水号': 'trans_no',
            '退费批次号': 'refund_batch_no',
            '业务订单号': 'biz_order_no',
            '支付方式/账号': 'pay_method',
            '收退标识': 'pay_status',
            '机构名称': 'institution',
            '机构编码': 'institution_code',
            '所在省份': 'province',
            '运营负责人': 'oper_person',
            '业务面': 'yewu_fumian',
            '业务类目': 'ye_wu_lei_mu',
            '业务子类目': 'ye_wu_zi_lei_mu',
            '支付时间': 'pay_time',
            '实际支付金额': 'amount'
        }
        
        # 过选需要的列
        available_cols = [col for col in selected_cols if col in df.columns]
        print(f"可用列: {available_cols}")
        
        df_selected = df[available_cols].copy()
        df_selected = df_selected.rename(columns=rename_map)
        
        # 处理日期
        if 'pay_time' in df_selected.columns:
            df_selected['pay_time'] = pd.to_datetime(df_selected['pay_time']).dt.strftime('%Y-%m-%d %H:%M:%S')
        
        # 处理金额
        if 'amount' in df_selected.columns:
            df_selected['amount'] = pd.to_numeric(df_selected['amount'], errors='coerce').fillna(0)
        
        # 填充空值
        df_selected = df_selected.fillna('')
        
        print(f"处理后数据行数: {len(df_selected)}")
        print("前5行预览:")
        print(df_selected.head())
        
        # 转换为记录列表
        records = []
        for _, row in df_selected.iterrows():
            record = (
                str(row['order_id']) if 'order_id' in row else '',
                str(row['trans_no']) if 'trans_no' in row else '',
                str(row['refund_batch_no']) if 'refund_batch_no' in row else '',
                str(row['biz_order_no']) if 'biz_order_no' in row else '',
                str(row['pay_method']) if 'pay_method' in row else '',
                str(row['pay_status']) if 'pay_status' in row else '',
                str(row['institution']) if 'institution' in row else '',
                str(row['institution_code']) if 'institution_code' in row else '',
                str(row['province']) if 'province' in row else '',
                str(row['oper_person']) if 'oper_person' in row else '',
                str(row['yewu_fumian']) if 'yewu_fumian' in row else '',
                str(row['ye_wu_lei_mu']) if 'ye_wu_lei_mu' in row else '',
                str(row['ye_wu_zi_lei_mu']) if 'ye_wu_zi_lei_mu' in row else '',
                str(row['pay_time']) if 'pay_time' in row else '',
                float(row['amount']) if 'amount' in row else 0
            )
            records.append(record)
        
        print(f"\n✅ 记录数: {len(records)}")
        
        # 插入数据
        print("正在插入数据库...")
        cursor.executemany('''
        INSERT OR REPLACE INTO daily_flow_details (
            order_id, trans_no, refund_batch_no, biz_order_no,
            pay_method, pay_status, institution, institution_code,
            province, oper_person, yewu_fumian, ye_wu_lei_mu,
            ye_wu_zi_lei_mu, pay_time, amount
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        ''', records)
        
        conn.commit()
        
        # 验证
        cursor.execute('SELECT COUNT(*) FROM daily_flow_details')
        count = cursor.fetchone()[0]
        print(f"\n✅ 导入完成: {count} 行数据")
        
        # 汇总统计
        print("\n📊 数据概览:")
        
        # 按收退标识统计
        cursor.execute('SELECT pay_status, COUNT(*), SUM(amount) FROM daily_flow_details GROUP BY pay_status')
        for row in cursor.fetchall():
            status, cnt, total = row
            print(f"  {status}: {cnt:,} 笔, {total:,.2f} 元")
        
        # 按机构统计（前5）
        cursor.execute('''
        SELECT institution, COUNT(*), SUM(amount) 
        FROM daily_flow_details 
        GROUP BY institution 
        ORDER BY SUM(amount) DESC 
        LIMIT 5
        ''')
        print("\n  机构 TOP 5:")
        for row in cursor.fetchall():
            inst, cnt, total = row
            print(f"    {inst}: {cnt:,} 笔, {total:,.2f} 元")
        
        # 按支付方式统计
        cursor.execute('''
        SELECT SUBSTR(pay_method, 1, INSTR(pay_method || '/', '/') - 1) as method, 
               COUNT(*), SUM(amount) 
        FROM daily_flow_details 
        GROUP BY method 
        ORDER BY SUM(amount) DESC
        ''')
        print("\n  支付方式:")
        for row in cursor.fetchall():
            method, cnt, total = row
            print(f"    {method}: {cnt:,} 笔, {total:,.2f} 元")
        
        print("\n✨ 导入完成！")
        
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()
    finally:
        conn.close()

if __name__ == '__main__':
    main()
