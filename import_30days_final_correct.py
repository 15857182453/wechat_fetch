#!/usr/bin/env python3
"""
导入30天业务对账明细数据 - 正确版本
列结构（从openpyxl确认）:
0: 商户订单号
1: 交易流水号
5: 收退标识
6: 机构名称
7: 机构编码
8: 所在省份
9: 运营负责人
10: 业绩类目
11: 业绩子类目
12: 业务类型
20: 业务完成时间
24: 实际支付金额
"""

import pandas as pd
import sqlite3
import os

def safe_datetime(dt):
    """安全地处理日期，对于非日期值返回空字符串"""
    try:
        return pd.to_datetime(dt).strftime('%Y-%m-%d %H:%M:%S') if pd.notna(dt) else ''
    except:
        return str(dt) if pd.notna(dt) else ''

EXCEL_FILE_30DAYS = '/mnt/c/Users/44238/Desktop/业务对账数据/30天业务数据/业务对账统计明细-20260401121717.xlsx'
DB_FILE = '/home/openclaw/.openclaw/workspace/business_flow.db'

def main():
    print("="*60)
    print("📝 导入30天业务对账明细数据 - 正确版本")
    print("="*60)
    
    if not os.path.exists(EXCEL_FILE_30DAYS):
        print(f"❌ Excel文件不存在: {EXCEL_FILE_30DAYS}")
        return
    
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    try:
        # 创建表 - 使用原始列名作为字段名
        cursor.execute('DROP TABLE IF EXISTS daily_flow_details')
        cursor.execute('''
        CREATE TABLE daily_flow_details (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id TEXT,              -- 商户订单号
            trans_no TEXT,              -- 交易流水号
            refund_batch_no TEXT,       -- 退费批次号
            biz_order_no TEXT,          -- 业务订单号
            pay_method TEXT,            -- 支付方式/账号
            pay_status TEXT,            -- 收退标识
            institution TEXT,           -- 机构名称
            institution_code TEXT,      -- 机构编码
            province TEXT,              -- 所在省份
            oper_person TEXT,           -- 运营负责人
            ye_wu_lei_mu TEXT,          -- 业绩类目
            ye_wu_zi_lei_mu TEXT,       -- 业绩子类目
            yewu_leixing TEXT,          -- 业务类型
            yewu_wancheng_shijian TEXT, -- 业务完成时间
            caiwu_ruzhang_shijian TEXT, -- 财务入账时间
            shoukuan_shanghu TEXT,      -- 收款商户
            order_amount REAL,          -- 订单金额
            amount REAL,                -- 实际支付金额
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        cursor.execute('CREATE INDEX idx_institution ON daily_flow_details(institution)')
        cursor.execute('CREATE INDEX idx_pay_status ON daily_flow_details(pay_status)')
        cursor.execute('CREATE INDEX idx_ye_wu_lei_mu ON daily_flow_details(ye_wu_lei_mu)')
        cursor.execute('CREATE INDEX idx_yewu_wancheng_shijian ON daily_flow_details(yewu_wancheng_shijian)')
        
        print("✅ 创建表完成")
        
        # 读取Excel
        print(f"\n📊 正在读取 Excel 数据...")
        df = pd.read_excel(EXCEL_FILE_30DAYS, engine='openpyxl')
        
        print(f"总行数: {len(df)}")
        print(f"总列数: {len(df.columns)}")
        
        # 使用原始列名映射到拼音字段名
        # 根据openpyxl确认的列索引:
        # 0: order_id, 1: trans_no, 5: pay_status, 6: institution, 7: institution_code
        # 8: province, 9: oper_person, 10: ye_wu_lei_mu, 11: ye_wu_zi_lei_mu
        # 12: yewu_leixing, 20: yewu_wancheng_shijian, 21: caiwu_ruzhang_shijian
        # 22: shoukuan_shanghu, 23: 订单金额, 24: 实际支付金额
        
        # 构建DataFrame
        new_df = pd.DataFrame()
        
        # 读取所有需要的列
        new_df['order_id'] = df.iloc[:, 0]
        new_df['trans_no'] = df.iloc[:, 1]
        new_df['refund_batch_no'] = df.iloc[:, 3]  # 列3是退费批次号
        new_df['biz_order_no'] = df.iloc[:, 4]      # 列4是业务订单号
        new_df['pay_method'] = df.iloc[:, 5]        # 列5是支付方式/账号
        new_df['pay_status'] = df.iloc[:, 6]        # 列6是收退标识
        new_df['institution'] = df.iloc[:, 7]       # 列7是机构名称
        new_df['institution_code'] = df.iloc[:, 8]  # 列8是机构编码
        new_df['province'] = df.iloc[:, 9]
        new_df['oper_person'] = df.iloc[:, 10]
        new_df['ye_wu_lei_mu'] = df.iloc[:, 11]     # 列11是业绩类目
        new_df['ye_wu_zi_lei_mu'] = df.iloc[:, 12]  # 列12是业绩子类目
        new_df['yewu_leixing'] = df.iloc[:, 13]
        new_df['yewu_wancheng_shijian'] = df.iloc[:, 20]
        new_df['caiwu_ruzhang_shijian'] = df.iloc[:, 21]
        new_df['shoukuan_shanghu'] = df.iloc[:, 22]
        new_df['order_amount'] = df.iloc[:, 23]     # 列23是订单金额
        new_df['amount'] = df.iloc[:, 24]           # 列24是实际支付金额
        
        print(f"✅ 提取列数: {len(new_df.columns)}")
        
        # 处理数据 - 确保文本字段是字符串
        for col in ['order_id', 'trans_no', 'pay_method', 'pay_status', 'institution', 
                    'institution_code', 'province', 'oper_person', 'ye_wu_lei_mu', 
                    'ye_wu_zi_lei_mu', 'yewu_leixing', 'yewu_wancheng_shijian', 
                    'caiwu_ruzhang_shijian', 'shoukuan_shanghu']:
            new_df[col] = new_df[col].astype(str)
        
        new_df['yewu_wancheng_shijian'] = new_df['yewu_wancheng_shijian'].apply(safe_datetime)
        new_df['caiwu_ruzhang_shijian'] = new_df['caiwu_ruzhang_shijian'].apply(safe_datetime)
        new_df['order_amount'] = pd.to_numeric(new_df['order_amount'], errors='coerce').fillna(0)
        new_df['amount'] = pd.to_numeric(new_df['amount'], errors='coerce').fillna(0)
        new_df = new_df.fillna('')
        
        print("\n前5行关键字段:")
        print(new_df[['pay_status', 'institution', 'ye_wu_lei_mu', 'amount']].head())
        
        # 检查浙江省中医院数据
        zjzyc = new_df[new_df['institution'].str.contains('浙江省中医院', na=False, case=False)]
        print(f"\n浙江省中医院相关行数: {len(zjzyc)}")
        
        # 转换为记录
        records = []
        for _, row in new_df.iterrows():
            record = (
                str(row['order_id']),
                str(row['trans_no']),
                str(row['refund_batch_no']),
                str(row['biz_order_no']),
                str(row['pay_method']),
                str(row['pay_status']),
                str(row['institution']),
                str(row['institution_code']),
                str(row['province']),
                str(row['oper_person']),
                str(row['ye_wu_lei_mu']),
                str(row['ye_wu_zi_lei_mu']),
                str(row['yewu_leixing']),
                str(row['yewu_wancheng_shijian']),
                str(row['caiwu_ruzhang_shijian']),
                str(row['shoukuan_shanghu']),
                float(row['order_amount']),
                float(row['amount'])
            )
            records.append(record)
        
        print(f"\n✅ 插入 {len(records)} 行数据...")
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
        print(f"✅ 导入完成: {cursor.fetchone()[0]} 行数据")
        
        # 查询浙江省中医院数据
        print("\n=== 浙江省中医院（湖滨院区）数据 ===")
        
        # 按 pay_status 统计
        cursor.execute('''
        SELECT pay_status, COUNT(*), SUM(amount)
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
        SELECT pay_status, ye_wu_lei_mu, COUNT(*) as count, SUM(amount) as total
        FROM daily_flow_details 
        WHERE institution = '浙江省中医院（湖滨院区）'
          AND ye_wu_lei_mu LIKE '%电子处方%'
        GROUP BY pay_status, ye_wu_lei_mu
        ORDER BY total DESC
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
            SUM(amount) as total
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
