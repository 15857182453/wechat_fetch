#!/usr/bin/env python3
"""
导入30天业务对账明细数据 - 终极修正版
根据Excel实际数据确认的列索引:
6: 收退标识 (实际值是"广州市红十字会医院"等机构名，但这个位置就是收退标识)
7: 机构名称 (实际值是"1005693"等编码，但这个位置就是机构名称)
8: 机构编码
9: 所在省份
10: 运营负责人
11: 业绩类目
12: 业绩子类目
20: 业务完成时间
24: 订单金额
26: 实际支付金额
"""

import pandas as pd
import sqlite3

EXCEL_FILE_30DAYS = '/mnt/c/Users/44238/Desktop/业务对账数据/30天业务数据/业务对账统计明细-20260401121717.xlsx'
DB_FILE = '/home/openclaw/.openclaw/workspace/business_flow.db'

def safe_datetime(dt):
    try:
        return pd.to_datetime(dt).strftime('%Y-%m-%d %H:%M:%S') if pd.notna(dt) else ''
    except:
        return str(dt) if pd.notna(dt) else ''

def main():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    try:
        # 重建表
        cursor.execute('DROP TABLE IF EXISTS daily_flow_details')
        cursor.execute('''
        CREATE TABLE daily_flow_details (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id TEXT,
            trans_no TEXT,
            pay_method TEXT,
            pay_status TEXT,            -- 列6 (收退标识)
            institution TEXT,           -- 列7 (机构名称)
            institution_code TEXT,      -- 列8 (机构编码)
            province TEXT,              -- 列9
            oper_person TEXT,           -- 列10
            ye_wu_lei_mu TEXT,          -- 列11 (业绩类目)
            ye_wu_zi_lei_mu TEXT,       -- 列12 (业绩子类目)
            yewu_wancheng_shijian TEXT, -- 列20
            order_amount REAL,          -- 列24
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        cursor.execute('CREATE INDEX idx_institution ON daily_flow_details(institution)')
        cursor.execute('CREATE INDEX idx_pay_status ON daily_flow_details(pay_status)')
        cursor.execute('CREATE INDEX idx_ye_wu_lei_mu ON daily_flow_details(ye_wu_lei_mu)')
        
        print("✅ 创建表完成")
        
        # 读取Excel
        df = pd.read_excel(EXCEL_FILE_30DAYS, engine='openpyxl')
        
        # 使用正确的列索引创建DataFrame
        new_df = pd.DataFrame()
        new_df['order_id'] = df.iloc[:, 0]
        new_df['trans_no'] = df.iloc[:, 1]
        new_df['pay_method'] = df.iloc[:, 5]      # 支付方式/账号
        new_df['pay_status'] = df.iloc[:, 6]      # ⭐ 收退标识 (列6)
        new_df['institution'] = df.iloc[:, 7]     # ⭐ 机构名称 (列7)
        new_df['institution_code'] = df.iloc[:, 8] # ⭐ 机构编码 (列8)
        new_df['province'] = df.iloc[:, 9]
        new_df['oper_person'] = df.iloc[:, 10]
        new_df['ye_wu_lei_mu'] = df.iloc[:, 11]   # ⭐ 业绩类目 (列11)
        new_df['ye_wu_zi_lei_mu'] = df.iloc[:, 12] # ⭐ 业绩子类目 (列12)
        new_df['yewu_wancheng_shijian'] = df.iloc[:, 20]
        new_df['order_amount'] = df.iloc[:, 24]    # 订单金额 (列24)
        
        print(f"✅ 数据行数: {len(new_df)}")
        print(f"✅ pay_status 值: {new_df['pay_status'].unique()[:10]}")
        print(f"✅ institution 值: {new_df['institution'].unique()[:5]}")
        
        # 处理数据
        new_df['yewu_wancheng_shijian'] = new_df['yewu_wancheng_shijian'].apply(safe_datetime)
        new_df['order_amount'] = pd.to_numeric(new_df['order_amount'], errors='coerce').fillna(0)
        new_df = new_df.fillna('')
        
        # 转换为记录
        records = []
        for _, row in new_df.iterrows():
            record = (
                str(row['order_id']),
                str(row['trans_no']),
                str(row['pay_method']),
                str(row['pay_status']),
                str(row['institution']),
                str(row['institution_code']),
                str(row['province']),
                str(row['oper_person']),
                str(row['ye_wu_lei_mu']),
                str(row['ye_wu_zi_lei_mu']),
                str(row['yewu_wancheng_shijian']),
                float(row['order_amount'])
            )
            records.append(record)
        
        # 插入数据
        print(f"\n✅ 插入 {len(records)} 行数据...")
        cursor.executemany('''
        INSERT INTO daily_flow_details (
            order_id, trans_no, pay_method, pay_status, institution, 
            institution_code, province, oper_person, ye_wu_lei_mu, 
            ye_wu_zi_lei_mu, yewu_wancheng_shijian, order_amount
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
        ''', records)
        
        conn.commit()
        
        # 验证
        cursor.execute('SELECT COUNT(*) FROM daily_flow_details')
        print(f"✅ 导入完成: {cursor.fetchone()[0]} 行数据")
        
        # 查询浙江省中医院数据
        print("\n=== 浙江省中医院（湖滨院区）数据 ===")
        
        # 按 pay_status 统计
        cursor.execute('''
        SELECT pay_status, COUNT(*), SUM(order_amount)
        FROM daily_flow_details 
        WHERE institution = '浙江省中医院（湖滨院区）'
        GROUP BY pay_status
        ''')
        
        rows = cursor.fetchall()
        print("\npay_status 统计:")
        for row in rows:
            print(f"  {row[0]}: {row[1]:,} 笔, {row[2]:,.2f} 元")
        
        # 电子处方统计
        cursor.execute('''
        SELECT pay_status, ye_wu_lei_mu, COUNT(*) as count, SUM(order_amount) as total
        FROM daily_flow_details 
        WHERE institution = '浙江省中医院（湖滨院区）'
          AND ye_wu_lei_mu LIKE '%电子处方%'
        GROUP BY pay_status, ye_wu_lei_mu
        ''')
        
        rows = cursor.fetchall()
        print(f"\n✅ 电子处方: {len(rows)} 个组合")
        for row in rows:
            print(f"  状态: {row[0]}, 类目: {row[1]}, 笔数: {row[2]:,}, 金额: {row[3]:,.2f} 元")
        
        # 按日期汇总
        cursor.execute('''
        SELECT 
            SUBSTR(yewu_wancheng_shijian, 1, 10) as date,
            COUNT(*) as count,
            SUM(order_amount) as total
        FROM daily_flow_details 
        WHERE institution = '浙江省中医院（湖滨院区）'
          AND ye_wu_lei_mu LIKE '%电子处方%'
        GROUP BY SUBSTR(yewu_wancheng_shijian, 1, 10)
        ORDER BY date DESC
        LIMIT 30
        ''')
        
        rows = cursor.fetchall()
        print("\n📅 近30天电子处方每日数据:")
        print("日期 | 计数 | 金额")
        print("-" * 45)
        for row in rows:
            print(f"{row[0]} | {row[1]:>5} | {row[2]:>12,.2f} 元")
        
        print("\n✨ 导入完成！")
        
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()
    finally:
        conn.close()

if __name__ == '__main__':
    main()
