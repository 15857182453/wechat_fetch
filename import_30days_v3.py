#!/usr/bin/env python3
"""
重新导入30天业务对账明细数据到SQLite数据库
功能：根据真实Excel列结构导入，确保 业绩类目 和 业绩子类目 字段正确
"""

import pandas as pd
import sqlite3
import os
from pathlib import Path

# ==================== 配置 ====================
WORKSPACE = Path('/home/openclaw/.openclaw/workspace')
EXCEL_FILE_30DAYS = '/mnt/c/Users/44238/Desktop/业务对账数据/30天业务数据/业务对账统计明细-20260401121717.xlsx'
DB_FILE = WORKSPACE / 'business_flow.db'

def main():
    print("="*60)
    print("📝 重新导入30天业务对账明细数据")
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
        # 创建明细表（使用正确的字段名）
        cursor.execute('DROP TABLE IF EXISTS daily_flow_details')
        
        cursor.execute('''
        CREATE TABLE daily_flow_details (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id TEXT,              -- 商户订单号
            trans_no TEXT,              -- 交易流水号
            refund_batch_no TEXT,       -- 退费批次号
            biz_order_no TEXT,          -- 业务订单号
            pay_method TEXT,            -- 支付方式/账号
            pay_status TEXT,            -- 收退标识 (收费/退费)
            institution TEXT,           -- 机构名称
            institution_code TEXT,      -- 机构编码
            province TEXT,              -- 所在省份
            oper_person TEXT,           -- 运营负责人
            ye_wu_lei_mu TEXT,          -- 业绩类目
            ye_wu_zi_lei_mu TEXT,       -- 业绩子类目
            yewu_leixing TEXT,          -- 业务类型
            yewu_wancheng_shijian TEXT, -- 业务完成时间
            caiwu_ruzhang_shijian TEXT, -- 财务入账时间
            amount REAL,                -- 实际支付金额
            order_amount REAL,          -- 订单金额
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        cursor.execute('CREATE INDEX idx_pay_status ON daily_flow_details(pay_status)')
        cursor.execute('CREATE INDEX idx_institution ON daily_flow_details(institution)')
        cursor.execute('CREATE INDEX idx_ye_wu_lei_mu ON daily_flow_details(ye_wu_lei_mu)')
        cursor.execute('CREATE INDEX idx_yewu_wancheng_shijian ON daily_flow_details(yewu_wancheng_shijian)')
        
        print("✅ 创建明细表完成")
        
        # 读取Excel数据
        print(f"\n📊 正在读取 Excel 数据...")
        df = pd.read_excel(EXCEL_FILE_30DAYS, engine='openpyxl')
        
        print(f"数据行数: {len(df)}")
        print(f"数据列数: {len(df.columns)}")
        
        # 根据实际Excel列索引选择数据
        # 0:商户订单号, 1:交易流水号, 3:退费批次号, 4:业务订单号, 5:支付方式/账号
        # 6:收退标识, 7:机构名称, 8:机构编码, 9:所在省份, 10:运营负责人
        # 11:业绩类目, 12:业绩子类目, 13:业务类型
        # 20:业务完成时间, 21:财务入账时间, 26:实际支付金额, 24:订单金额
        
        new_df = pd.DataFrame()
        new_df['order_id'] = df.iloc[:, 0]  # 商户订单号
        new_df['trans_no'] = df.iloc[:, 1]  # 交易流水号
        new_df['refund_batch_no'] = df.iloc[:, 3]  # 退费批次号
        new_df['biz_order_no'] = df.iloc[:, 4]  # 业务订单号
        new_df['pay_method'] = df.iloc[:, 5]  # 支付方式/账号
        new_df['pay_status'] = df.iloc[:, 6]  # 收退标识
        new_df['institution'] = df.iloc[:, 7]  # 机构名称
        new_df['institution_code'] = df.iloc[:, 8]  # 机构编码
        new_df['province'] = df.iloc[:, 9]  # 所在省份
        new_df['oper_person'] = df.iloc[:, 10]  # 运营负责人
        new_df['ye_wu_lei_mu'] = df.iloc[:, 11]  # 业绩类目 ⭐ 关键字段
        new_df['ye_wu_zi_lei_mu'] = df.iloc[:, 12]  # 业绩子类目 ⭐ 关键字段
        new_df['yewu_leixing'] = df.iloc[:, 13]  # 业务类型
        new_df['yewu_wancheng_shijian'] = df.iloc[:, 20]  # 业务完成时间
        new_df['caiwu_ruzhang_shijian'] = df.iloc[:, 21]  # 财务入账时间
        new_df['amount'] = df.iloc[:, 26]  # 实际支付金额
        new_df['order_amount'] = df.iloc[:, 24]  # 订单金额
        
        print(f"\n✅ 新DataFrame列名: {list(new_df.columns)}")
        print(f"✅ 数据行数: {len(new_df)}")
        
        # 处理日期字段 - 跳过无法解析的值
        def safe_datetime(dt):
            try:
                return pd.to_datetime(dt).strftime('%Y-%m-%d %H:%M:%S') if pd.notna(dt) else ''
            except:
                return str(dt) if pd.notna(dt) else ''
        
        new_df['yewu_wancheng_shijian'] = new_df['yewu_wancheng_shijian'].apply(safe_datetime)
        new_df['caiwu_ruzhang_shijian'] = new_df['caiwu_ruzhang_shijian'].apply(safe_datetime)
        
        # 处理金额字段
        for col in ['amount', 'order_amount']:
            new_df[col] = pd.to_numeric(new_df[col], errors='coerce').fillna(0)
        
        # 填充空值
        new_df = new_df.fillna('')
        
        print("\n前5行数据预览:")
        print(new_df.head())
        
        print("\n业绩类目(unique):", new_df['ye_wu_lei_mu'].unique()[:10])
        print("业绩子类目(unique):", new_df['ye_wu_zi_lei_mu'].unique()[:10])
        
        # 转换为记录列表
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
                float(row['amount']),
                float(row['order_amount'])
            )
            records.append(record)
        
        print(f"\n✅ 记录数: {len(records)}")
        
        # 插入数据
        print("正在插入数据库...")
        cursor.executemany('''
        INSERT INTO daily_flow_details (
            order_id, trans_no, refund_batch_no, biz_order_no, pay_method,
            pay_status, institution, institution_code, province, oper_person,
            ye_wu_lei_mu, ye_wu_zi_lei_mu, yewu_leixing, yewu_wancheng_shijian,
            caiwu_ruzhang_shijian, amount, order_amount
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
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
            print(f"  {status or 'NULL'}: {cnt:,} 笔, {total:,.2f} 元")
        
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
            print(f"    {inst or 'NULL'}: {cnt:,} 笔, {total:,.2f} 元")
        
        # 按业绩类目统计
        cursor.execute('''
        SELECT ye_wu_lei_mu, COUNT(*), SUM(amount) 
        FROM daily_flow_details 
        WHERE ye_wu_lei_mu IS NOT NULL AND ye_wu_lei_mu != ''
        GROUP BY ye_wu_lei_mu 
        ORDER BY COUNT(*) DESC
        ''')
        print("\n  业绩类目:")
        for row in cursor.fetchall():
            cat, cnt, total = row
            print(f"    {cat}: {cnt:,} 笔, {total:,.2f} 元")
        
        # 浙江省中医院统计
        cursor.execute('''
        SELECT ye_wu_lei_mu, COUNT(*), SUM(amount) 
        FROM daily_flow_details 
        WHERE institution = '浙江省中医院（湖滨院区）'
        GROUP BY ye_wu_lei_mu
        ORDER BY SUM(amount) DESC
        ''')
        print("\n  浙江省中医院（湖滨院区）- 按业绩类目:")
        for row in cursor.fetchall():
            cat, cnt, total = row
            print(f"    {cat}: {cnt:,} 笔, {total:,.2f} 元")
        
        print("\n✨ 导入完成！")
        
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()
    finally:
        conn.close()

if __name__ == '__main__':
    main()
