#!/usr/bin/env python3
"""
导入新流水数据到SQLite数据库
功能：读取新流水2026.xlsx的3个sheet，以及30天业务对账明细
"""

import pandas as pd
import sqlite3
import os
from pathlib import Path
from datetime import datetime

# ==================== 配置 ====================
WORKSPACE = Path('/home/openclaw/.openclaw/workspace')
EXCEL_FILE = '/mnt/c/Users/44238/Desktop/业务对账数据/对账业务总表/新流水2026.xlsx'
EXCEL_FILE_30DAYS = '/mnt/c/Users/44238/Desktop/业务对账数据/30天业务数据/业务对账统计明细-20260401121717.xlsx'
DB_FILE = WORKSPACE / 'business_flow.db'

# ==================== 创建数据库表 ====================
def create_tables(conn):
    """创建数据库表结构"""
    cursor = conn.cursor()
    
    # 1. 总表：101行数据 (26个字段)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS daily_flow_total (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT UNIQUE NOT NULL,
        consult REAL,
        consult_orders INTEGER,
        prescription REAL,
        prescription_orders INTEGER,
        self_tiyu REAL,
        self_tiyu_orders INTEGER,
        self_jianguan REAL,
        self_jianguan_orders INTEGER,
        third_service REAL,
        third_service_orders INTEGER,
        psychology REAL,
        psychology_orders INTEGER,
        payment REAL,
        payment_orders INTEGER,
        remote REAL,
        remote_orders INTEGER,
        membership REAL,
        membership_orders INTEGER,
        third_tiyu REAL,
        third_tiyu_orders INTEGER,
        online_mall REAL,
        online_mall_orders INTEGER,
        total_flow REAL,
        total_increment REAL,
        total_lh REAL,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # 2. 扩展表：35行数据
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS daily_flow_extended (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT UNIQUE NOT NULL,
        year INTEGER,
        consult REAL,
        consult_orders INTEGER,
        prescription REAL,
        prescription_orders INTEGER,
        self_tiyu REAL,
        self_tiyu_orders INTEGER,
        self_jianguan REAL,
        self_jianguan_orders INTEGER,
        third_service REAL,
        third_service_orders INTEGER,
        psychology REAL,
        psychology_orders INTEGER,
        payment REAL,
        payment_orders INTEGER,
        remote REAL,
        remote_orders INTEGER,
        membership REAL,
        membership_orders INTEGER,
        third_tiyu REAL,
        third_tiyu_orders INTEGER,
        online_mall REAL,
        online_mall_orders INTEGER,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # 3. 心理咨询表：26行数据
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS psychology_detail (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        period TEXT,
        hang_qiyuan REAL,
        hang_qiyuan_orders INTEGER,
        shao_xing_qiyuan REAL,
        shao_xing_qiyuan_orders INTEGER,
        hai_ning_si_yuan REAL,
        hai_ning_si_yuan_orders INTEGER,
        total_flow REAL,
        total_orders INTEGER,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # 创建索引
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_date_total ON daily_flow_total(date)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_date_ext ON daily_flow_extended(date)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_period ON psychology_detail(period)')
    
    conn.commit()
    print('✅ 数据库表创建完成')

# ==================== 处理总表 ====================
def import_total_sheet(conn):
    """导入总表数据（101行，只取前26个业务字段）"""
    print('\n📊 正在导入 Sheet: 总表')
    
    df = pd.read_excel(EXCEL_FILE, sheet_name='总表')
    
    # 只取前26列
    df = df.iloc[:, :26]
    
    # 构建列名（英文）
    cols = ['date', 'consult', 'consult_orders', 'prescription', 'prescription_orders',
            'self_tiyu', 'self_tiyu_orders', 'self_jianguan', 'self_jianguan_orders',
            'third_service', 'third_service_orders', 'psychology', 'psychology_orders',
            'payment', 'payment_orders', 'remote', 'remote_orders', 'membership', 'membership_orders',
            'third_tiyu', 'third_tiyu_orders', 'online_mall', 'online_mall_orders',
            'total_flow', 'total_increment', 'total_lh']
    df.columns = cols
    
    print(f'列数: {len(df.columns)}')
    print(f'列名: {cols}')
    
    # 去除前3行表头行，并过滤掉汇总行
    df = df.iloc[3:].copy()
    # 过滤掉汇总行（包含"总计"、"流水汇总"等非日期行）
    df = df[df['date'].notna()].copy()
    df = df[~df['date'].astype(str).str.contains('总计|汇总|合计', na=False)].copy()
    df = df.reset_index(drop=True)
    
    print(f'数据行数: {len(df)}')
    print('前5行预览:')
    print(df.head().to_string())
    
    # 处理日期
    df['date'] = pd.to_datetime(df['date']).dt.strftime('%Y-%m-%d')
    
    # 数值列转为数字，NaN转0
    numeric_cols = [col for col in df.columns if col != 'date']
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    
    # 转为记录列表（26个值）
    records = []
    for _, row in df.iterrows():
        record = (
            row['date'],
            float(row['consult']), int(row['consult_orders']),
            float(row['prescription']), int(row['prescription_orders']),
            float(row['self_tiyu']), int(row['self_tiyu_orders']),
            float(row['self_jianguan']), int(row['self_jianguan_orders']),
            float(row['third_service']), int(row['third_service_orders']),
            float(row['psychology']), int(row['psychology_orders']),
            float(row['payment']), int(row['payment_orders']),
            float(row['remote']), int(row['remote_orders']),
            float(row['membership']), int(row['membership_orders']),
            float(row['third_tiyu']), int(row['third_tiyu_orders']),
            float(row['online_mall']), int(row['online_mall_orders']),
            float(row['total_flow']), float(row['total_increment']), float(row['total_lh'])
        )
        records.append(record)
    
    print(f'\n✅ 总表数据行数: {len(records)}')
    
    # 插入数据 - 26个?
    cursor = conn.cursor()
    cursor.executemany('''
    INSERT OR REPLACE INTO daily_flow_total 
    (date, consult, consult_orders, prescription, prescription_orders,
     self_tiyu, self_tiyu_orders, self_jianguan, self_jianguan_orders,
     third_service, third_service_orders, psychology, psychology_orders,
     payment, payment_orders, remote, remote_orders, membership, membership_orders,
     third_tiyu, third_tiyu_orders, online_mall, online_mall_orders,
     total_flow, total_increment, total_lh)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', records)
    
    conn.commit()
    print(f'✅ 总表导入完成: {len(records)} 行')

# ==================== 处理Sheet2 ====================
def import_sheet2(conn):
    """导入Sheet2数据（35行）"""
    print('\n📊 正在导入 Sheet: Sheet2')
    
    # 暂时不处理，结构复杂
    
    print('⚠️ Sheet2结构复杂，暂未导入')

# ==================== 处理心理咨询 ====================
def import_psychology(conn):
    """导入心理咨询数据（26行）"""
    print('\n📊 正在导入 Sheet: 心理咨询')
    
    df = pd.read_excel(EXCEL_FILE, sheet_name='心理咨询')
    
    print('心理咨询Sheet:')
    print(df.to_string())
    
    # 解析表头
    dates = df.iloc[2:, 0].values
    hang_qiyuan = df.iloc[2:, 1].values
    hang_qiyuan_orders = df.iloc[2:, 2].values
    shao_xing = df.iloc[2:, 3].values
    shao_xing_orders = df.iloc[2:, 4].values
    hai_ning = df.iloc[2:, 5].values
    hai_ning_orders = df.iloc[2:, 6].values
    total_flow = df.iloc[2:, 7].values
    total_orders = df.iloc[2:, 8].values
    
    records = []
    for i in range(len(dates)):
        record = (
            str(dates[i]),
            float(hang_qiyuan[i]) if pd.notna(hang_qiyuan[i]) else 0,
            int(hang_qiyuan_orders[i]) if pd.notna(hang_qiyuan_orders[i]) else 0,
            float(shao_xing[i]) if pd.notna(shao_xing[i]) else 0,
            int(shao_xing_orders[i]) if pd.notna(shao_xing_orders[i]) else 0,
            float(hai_ning[i]) if pd.notna(hai_ning[i]) else 0,
            int(hai_ning_orders[i]) if pd.notna(hai_ning_orders[i]) else 0,
            float(total_flow[i]) if pd.notna(total_flow[i]) else 0,
            int(total_orders[i]) if pd.notna(total_orders[i]) else 0
        )
        records.append(record)
    
    # 插入数据
    cursor = conn.cursor()
    cursor.executemany('''
    INSERT OR REPLACE INTO psychology_detail (
        period, hang_qiyuan, hang_qiyuan_orders,
        shao_xing_qiyuan, shao_xing_qiyuan_orders,
        hai_ning_si_yuan, hai_ning_si_yuan_orders,
        total_flow, total_orders
    ) VALUES (?,?,?,?,?,?,?,?,?)
    ''', records)
    
    conn.commit()
    print(f'✅ 心理咨询导入完成: {len(records)} 行')

# ==================== 验证数据 ====================
def verify_data(conn):
    """验证数据完整性"""
    print('\n🔍 数据验证')
    cursor = conn.cursor()
    
    # 检查各表行数
    cursor.execute('SELECT COUNT(*) FROM daily_flow_total')
    count_total = cursor.fetchone()[0]
    print(f'  daily_flow_total: {count_total} 行 (预期: 101)')
    
    cursor.execute('SELECT COUNT(*) FROM daily_flow_extended')
    count_ext = cursor.fetchone()[0]
    print(f'  daily_flow_extended: {count_ext} 行 (预期: 35)')
    
    cursor.execute('SELECT COUNT(*) FROM psychology_detail')
    count_psy = cursor.fetchone()[0]
    print(f'  psychology_detail: {count_psy} 行 (预期: 26)')
    
    # 检查数据范围
    print('\n📅 日期范围:')
    cursor.execute('SELECT MIN(date), MAX(date) FROM daily_flow_total')
    min_date, max_date = cursor.fetchone()
    print(f'  总表: {min_date} ~ {max_date}')
    
    # 示例查询
    print('\n📊 示例数据（总表前5行）:')
    cursor.execute('SELECT date, total_flow, consult FROM daily_flow_total ORDER BY date LIMIT 5')
    for row in cursor.fetchall():
        print(f'  {row[0]}: {row[1]:.2f}万元（咨询: {row[2]:.2f}万元）')

# ==================== 主程序 ====================
def main():
    print('='*60)
    print('📝 导入新流水2026.xlsx到SQLite数据库')
    print('='*60)
    
    # 检查文件
    if not os.path.exists(EXCEL_FILE):
        print(f'❌ Excel文件不存在: {EXCEL_FILE}')
        return
    
    # 删除旧数据库
    if DB_FILE.exists():
        print(f'⚠️  删除旧数据库: {DB_FILE}')
        DB_FILE.unlink()
    
    # 连接数据库
    conn = sqlite3.connect(DB_FILE)
    print(f'📁 数据库文件: {DB_FILE}')
    
    try:
        # 1. 创建表
        create_tables(conn)
        
        # 2. 导入数据
        import_total_sheet(conn)
        import_sheet2(conn)
        import_psychology(conn)
        
        # 3. 验证
        verify_data(conn)
        
        print('\n✨ 导入完成！')
        print('💡 使用 DB Browser for SQLite 打开数据库查看数据')
        
    except Exception as e:
        print(f'\n❌ 错误: {e}')
        import traceback
        traceback.print_exc()
    finally:
        conn.close()

if __name__ == '__main__':
    main()
