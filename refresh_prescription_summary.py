#!/usr/bin/env python3
"""
刷新预聚合表 prescription_summary
用于每次导入明细数据后更新 Dashboard 的预聚合表

用法:
  python3 refresh_prescription_summary.py              # 全量刷新
  python3 refresh_prescription_summary.py --incremental  # 仅刷新当前月
  python3 refresh_prescription_summary.py --incremental 202604  # 刷新指定月

性能: 全量刷新约 1.2s（替代 Dashboard 每次启动时的 0.85s 全表扫描）
"""

import sqlite3
import sys
import time

DB_PATH = '/home/openclaw/.openclaw/workspace/business_flow.db'

FLOW_TABLES = {
    '2025': 'daily_flow_2025',
    '202601': 'daily_flow_2026_jan',
    '202602': 'daily_flow_2026_feb',
    '202603': 'daily_flow_2026_mar',
    '202604': 'daily_flow_2026_apr',
    '202605': 'daily_flow_2026_may',
}


def aggregate_sql(yr, table):
    return f'''
        INSERT INTO prescription_summary (yr, institution, cnt, amt, avg_amt, dt)
        SELECT '{yr}',
               institution,
               COUNT(*),
               SUM(amount),
               ROUND(SUM(amount)*1.0/COUNT(*), 2),
               SUBSTR(yewu_wancheng_shijian, 1, 10)
        FROM {table}
        WHERE ye_wu_lei_mu LIKE '%处方服务%'
          AND pay_status = '收费'
          AND yewu_wancheng_shijian IS NOT NULL
          AND yewu_wancheng_shijian != ''
          AND yewu_wancheng_shijian != 'NaT'
          AND yewu_wancheng_shijian LIKE '____-__-__%'
        GROUP BY institution, SUBSTR(yewu_wancheng_shijian, 1, 10)
    '''


def refresh_full():
    """全量刷新预聚合表"""
    print("=" * 60)
    print("🔄 全量刷新预聚合表 prescription_summary")
    print("=" * 60)

    conn = sqlite3.connect(DB_PATH)
    start = time.time()

    # 删除旧表重建
    print("\n🗑️  删除旧表...")
    conn.execute('DROP TABLE IF EXISTS prescription_summary')
    conn.commit()

    print("📊 创建新表...")
    conn.execute('''
        CREATE TABLE prescription_summary (
            yr TEXT, institution TEXT, cnt INTEGER,
            amt REAL, avg_amt REAL, dt TEXT
        )
    ''')
    conn.commit()

    # 聚合各月数据
    for yr, tbl in FLOW_TABLES.items():
        print(f"  处理 {tbl}...", end=" ")
        conn.execute(aggregate_sql(yr, tbl))
        conn.commit()
        c = conn.execute('SELECT COUNT(*) FROM prescription_summary WHERE yr=?', (yr,)).fetchone()[0]
        print(f"{c} 条")

    # 索引
    print("🔨 创建索引...")
    conn.execute('CREATE INDEX idx_pres_dt ON prescription_summary(dt)')
    conn.execute('CREATE INDEX idx_pres_inst ON prescription_summary(institution)')
    conn.execute('CREATE INDEX idx_pres_yr ON prescription_summary(yr)')
    conn.commit()

    total = conn.execute('SELECT COUNT(*) FROM prescription_summary').fetchone()[0]
    elapsed = time.time() - start
    print(f"\n✅ 刷新完成!")
    print(f"   总行数: {total:,} | 耗时: {elapsed:.2f}s")

    # 查询验证
    test_start = time.time()
    r = conn.execute(
        'SELECT dt, institution, cnt, amt FROM prescription_summary ORDER BY dt DESC LIMIT 3'
    ).fetchall()
    print(f"   查询验证: {time.time()-test_start:.4f}s")
    for row in r:
        print(f"     {row[0]} | {row[1]} | 订单{row[2]} | ¥{row[3]:,.2f}")

    conn.close()
    print("\n" + "=" * 60)


def refresh_incremental(year_month='202605'):
    """仅刷新指定月份"""
    if year_month not in FLOW_TABLES:
        print(f"❌ 不支持: {year_month} | 支持: {list(FLOW_TABLES.keys())}")
        return

    tbl = FLOW_TABLES[year_month]
    print(f"🔄 增量刷新: {year_month} ({tbl})")

    conn = sqlite3.connect(DB_PATH)
    start = time.time()

    conn.execute('DELETE FROM prescription_summary WHERE yr = ?', (year_month,))
    conn.commit()
    conn.execute(aggregate_sql(year_month, tbl))
    conn.commit()

    c = conn.execute('SELECT COUNT(*) FROM prescription_summary WHERE yr=?', (year_month,)).fetchone()[0]
    elapsed = time.time() - start
    print(f"  ✅ {year_month}: {c} 条 | {elapsed:.3f}s")

    total = conn.execute('SELECT COUNT(*) FROM prescription_summary').fetchone()[0]
    print(f"  📊 总计: {total:,} 条")

    conn.close()


if __name__ == '__main__':
    if '--incremental' in sys.argv:
        month = sys.argv[2] if len(sys.argv) > 2 else '202605'
        refresh_incremental(month)
    else:
        refresh_full()
