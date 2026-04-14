#!/usr/bin/env python3
"""
导入30天业务对账明细数据 - 最终版本
列结构（从openpyxl确认的正确顺序）:
6: pay_status (收退标识)
7: institution (机构名称)
8: institution_code (机构编码)
10: ye_wu_lei_mu (业绩类目)
24: order_amount (订单金额)
26: amount (实际支付金额)

注意：Excel中第6列实际是"收退标识"，但值是"广州市红十字会医院"这样的机构名
这可能是Excel导出时的bug，我们直接按原始顺序导入
"""

import pandas as pd
import sqlite3
import os

EXCEL_FILE_30DAYS = '/mnt/c/Users/44238/Desktop/业务对账数据/30天业务数据/业务对账统计明细-20260401121717.xlsx'
DB_FILE = '/home/openclaw/.openclaw/workspace/business_flow.db'

def safe_datetime(dt):
    try:
        return pd.to_datetime(dt).strftime('%Y-%m-%d %H:%M:%S') if pd.notna(dt) else ''
    except:
        return str(dt) if pd.notna(dt) else ''

def main():
    print("="*60)
    print("📝 导入30天业务对账明细数据")
    print("="*60)
    
    if not os.path.exists(EXCEL_FILE_30DAYS):
        print(f"❌ Excel文件不存在: {EXCEL_FILE_30DAYS}")
        return
    
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    try:
        # 创建表
        cursor.execute('DROP TABLE IF EXISTS daily_flow_details')
        cursor.execute('''
        CREATE TABLE daily_flow_details (
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
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        cursor.execute('CREATE INDEX idx_institution ON daily_flow_details(institution)')
        cursor.execute('CREATE INDEX idx_pay_status ON daily_flow_details(pay_status)')
        cursor.execute('CREATE INDEX idx_ye_wu_lei_mu ON daily_flow_details(ye_wu_lei_mu)')
        
        print("✅ 创建表完成")
        
        # 读取Excel
        print(f"\n📊 正在读取 Excel 数据...")
        df = pd.read_excel(EXCEL_FILE_30DAYS, engine='openpyxl')
        
        print(f"总行数: {len(df)}")
        
        # 按列索引直接提取（0-based）
        columns = {
            'order_id': 0,
            'trans_no': 1,
            'refund_batch_no': 3,
            'biz_order_no': 4,
            'pay_method': 5,
            'pay_status': 6,
            'institution': 7,
            'institution_code': 8,
            'province': 9,
            'oper_person': 10,
            'ye_wu_lei_mu': 11,
            'ye_wu_zi_lei_mu': 12,
            'yewu_leixing': 13,
            'yewu_wancheng_shijian': 20,
            'caiwu_ruzhang_shijian': 21,
            'shoukuan_shanghu': 22,
            'order_amount': 24,
            'amount': 26
        }
        
        new_df = pd.DataFrame()
        for col_name, idx in columns.items():
            new_df[col_name] = df.iloc[:, idx]
        
        print(f"✅ 提取列数: {len(new_df.columns)}")
        print(f"pay_status 前5值: {new_df['pay_status'].head().tolist()}")
        print(f"institution 前5值: {new_df['institution'].head().tolist()}")
        
        # 转换数据类型
        for col in ['pay_status', 'institution', 'institution_code', 'province', 
                    'oper_person', 'ye_wu_lei_mu', 'ye_wu_zi_lei_mu', 'yewu_leixing',
                    'yewu_wancheng_shijian', 'caiwu_ruzhang_shijian', 'shoukuan_shanghu']:
            new_df[col] = new_df[col].astype(str)
        
        new_df['yewu_wancheng_shijian'] = new_df['yewu_wancheng_shijian'].apply(safe_datetime)
        new_df['caiwu_ruzhang_shijian'] = new_df['caiwu_ruzhang_shijian'].apply(safe_datetime)
        new_df['order_amount'] = pd.to_numeric(new_df['order_amount'], errors='coerce').fillna(0)
        new_df['amount'] = pd.to_numeric(new_df['amount'], errors='coerce').fillna(0)
        new_df = new_df.fillna('')
        
        # 转换为记录
        records = []
        for _, row in new_df.iterrows():
            record = (
                str(row['order_id']), str(row['trans_no']), str(row['refund_batch_no']),
                str(row['biz_order_no']), str(row['pay_method']), str(row['pay_status']),
                str(row['institution']), str(row['institution_code']), str(row['province']),
                str(row['oper_person']), str(row['ye_wu_lei_mu']), str(row['ye_wu_zi_lei_mu']),
                str(row['yewu_leixing']), str(row['yewu_wancheng_shijian']),
                str(row['caiwu_ruzhang_shijian']), str(row['shoukuan_shanghu']),
                float(row['order_amount']), float(row['amount'])
            )
            records.append(record)
        
        print(f"\n✅ 插入 {len(records):,} 行数据...")
        cursor.executemany('''
        INSERT INTO daily_flow_details (
            order_id, trans_no, refund_batch_no, biz_order_no, pay_method,
            pay_status, institution, institution_code, province, oper_person,
            ye_wu_lei_mu, ye_wu_zi_lei_mu, yewu_leixing, yewu_wancheng_shijian,
            caiwu_ruzhang_shijian, shoukuan_shanghu, order_amount, amount
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        ''', records)
        
        conn.commit()
        cursor.execute('SELECT COUNT(*) FROM daily_flow_details')
        print(f"✅ 导入完成: {cursor.fetchone()[0]:,} 行数据")
        
        # 验证查询
        print("\n=== 验证查询 ===")
        
        # 检查浙江省中医院的数据
        cursor.execute('''
        SELECT institution, pay_status, COUNT(*)
        FROM daily_flow_details 
        WHERE institution LIKE '%浙江省中医院%'
        GROUP BY institution, pay_status
        LIMIT 5
        ''')
        
        rows = cursor.fetchall()
        print(f"\n浙江省中医院数据: {len(rows)} 行")
        for row in rows:
            print(f"  {row[0]} | {row[1]} | {row[2]:,}")
        
        # 电子处方统计
        cursor.execute('''
        SELECT ye_wu_lei_mu, COUNT(*), SUM(order_amount), SUM(amount)
        FROM daily_flow_details 
        WHERE institution = '浙江省中医院（湖滨院区）'
          AND ye_wu_lei_mu LIKE '%电子处方%'
          AND pay_status = '收费'
        GROUP BY ye_wu_lei_mu
        ''')
        
        rows = cursor.fetchall()
        print(f"\n✅ 电子处方收费: {len(rows)} 个类目")
        for row in rows:
            print(f"  {row[0]}: {row[1]:,} 笔, 订单:{row[2]:,.2f}, 实际:{row[3]:,.2f}")
        
        print("\n✨ 导入完成！")
        
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()
    finally:
        conn.close()

if __name__ == '__main__':
    main()
