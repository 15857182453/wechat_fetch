#!/usr/bin/env python3
"""
重新导入30天业务对账明细数据到SQLite数据库
功能：修复列名映射，确保 业绩类目 和 业绩子类目 字段正确导入
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
        # 创建/重建明细表
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
            ye_wu_fumian TEXT,          -- 业务面
            ye_wu_lei_mu TEXT,          -- 业绩类目
            ye_wu_zi_lei_mu TEXT,       -- 业绩子类目
            yewu_leixing TEXT,          -- 业务类型
            shangpin_zileibie TEXT,     -- 商品子类别
            yunying_fenlei TEXT,        -- 运营分类
            shangpin_id TEXT,           -- 商品id
            shangpin_mingchen TEXT,     -- 商品名称
            yewu_wancheng_zhuangtai TEXT, -- 业务完成状态
            yewu_wancheng_shijian TEXT,   -- 业务完成时间
            caiwu_ruzhang_shijian TEXT,   -- 财务入账时间
            data_zhuangtai TEXT,        -- 数据状态
            shoukuan_shanghu TEXT,      -- 收款商户
            order_amount REAL,          -- 订单金额
            youhui_amount REAL,         -- 优惠金额
            amount REAL,                -- 实际支付金额
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # 创建索引
        cursor.execute('CREATE INDEX idx_pay_time ON daily_flow_details(yewu_wancheng_shijian)')
        cursor.execute('CREATE INDEX idx_institution ON daily_flow_details(institution)')
        cursor.execute('CREATE INDEX idx_pay_status ON daily_flow_details(pay_status)')
        cursor.execute('CREATE INDEX idx_ye_wu_lei_mu ON daily_flow_details(ye_wu_lei_mu)')
        
        print("✅ 创建明细表完成")
        
        # 读取Excel数据
        print(f"\n📊 正在读取 Excel 数据...")
        df = pd.read_excel(EXCEL_FILE_30DAYS, engine='openpyxl')
        
        print(f"数据行数: {len(df)}")
        print(f"数据列数: {len(df.columns)}")
        
        # 定义列名映射（根据Excel列索引）
        col_map = {
            0: 'order_id',           # 商户订单号
            1: 'trans_no',           # 交易流水号
            3: 'refund_batch_no',    # 退费批次号
            4: 'biz_order_no',       # 业务订单号
            5: 'pay_method',         # 支付方式/账号
            6: 'pay_status',         # 收退标识
            7: 'institution',        # 机构名称
            8: 'institution_code',   # 机构编码
            9: 'province',           # 所在省份
            10: 'oper_person',       # 运营负责人
            11: 'ye_wu_fumian',      # 业务面
            12: 'ye_wu_lei_mu',      # 业绩类目
            13: 'ye_wu_zi_lei_mu',   # 业绩子类目
            14: 'yewu_leixing',      # 业务类型
            15: 'shangpin_zileibie', # 商品子类别
            16: 'yunying_fenlei',    # 运营分类
            17: 'shangpin_id',       # 商品id
            18: 'shangpin_mingchen', # 商品名称
            19: 'yewu_wancheng_zhuangtai', # 业务完成状态
            20: 'yewu_wancheng_shijian',   # 业务完成时间
            21: 'caiwu_ruzhang_shijian',   # 财务入账时间
            22: 'data_zhuangtai',        # 数据状态
            23: 'shoukuan_shanghu',      # 收款商户
            24: 'order_amount',          # 订单金额
            25: 'youhui_amount',         # 优惠金额
            26: 'amount'                 # 实际支付金额
        }
        
        # 选择需要的列
        selected_indices = sorted(col_map.keys())
        selected_cols = [df.columns[i] for i in selected_indices]
        
        print(f"\n选择的列 ({len(selected_cols)}个):")
        for i, idx in enumerate(selected_indices):
            print(f"  [{idx}] {df.columns[idx]} -> {col_map[idx]}")
        
        # 创建新DataFrame，使用新的列名
        new_df = pd.DataFrame()
        for idx, new_name in col_map.items():
            if idx < len(df.columns):
                new_df[new_name] = df.iloc[:, idx]
        
        print(f"\n新DataFrame列名: {list(new_df.columns)}")
        print(f"新DataFrame行数: {len(new_df)}")
        
        # 处理日期字段
        if 'yewu_wancheng_shijian' in new_df.columns:
            new_df['yewu_wancheng_shijian'] = pd.to_datetime(new_df['yewu_wancheng_shijian']).dt.strftime('%Y-%m-%d %H:%M:%S')
        
        # 处理金额字段
        for amount_col in ['order_amount', 'youhui_amount', 'amount']:
            if amount_col in new_df.columns:
                new_df[amount_col] = pd.to_numeric(new_df[amount_col], errors='coerce').fillna(0)
        
        # 填充空值
        new_df = new_df.fillna('')
        
        # 显示前5行
        print("\n前5行数据预览:")
        print(new_df.head())
        
        # 转换为记录列表
        records = []
        for _, row in new_df.iterrows():
            record = tuple(row[col] if col in row else '' for col in new_df.columns)
            records.append(record)
        
        print(f"\n✅ 记录数: {len(records)}")
        
        # 插入数据
        print("正在插入数据库...")
        placeholders = ','.join(['?' for _ in new_df.columns])
        column_names = ','.join(new_df.columns)
        
        sql = f'INSERT INTO daily_flow_details ({column_names}) VALUES ({placeholders})'
        cursor.executemany(sql, records)
        
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
        GROUP BY ye_wu_lei_mu 
        ORDER BY COUNT(*) DESC
        ''')
        print("\n  业绩类目:")
        for row in cursor.fetchall():
            cat, cnt, total = row
            if cat and cat.strip():
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
