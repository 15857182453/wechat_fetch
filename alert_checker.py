#!/usr/bin/env python3
"""金佰川预警检查脚本"""
import psycopg2
from datetime import datetime

DB = "host=localhost dbname=jinbaichuan user=openclaw password=jbc2026"

def log(cursor, rule_id, value, threshold, desc):
    # 严格去重：同规则+同描述+同天只写一次
    cursor.execute("""
        SELECT COUNT(*) FROM alert_log
        WHERE rule_id=%s AND description=%s AND alert_time::date = CURRENT_DATE
    """, (rule_id, desc))
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO alert_log (rule_id, metric_value, threshold_value, description) VALUES (%s,%s,%s,%s)",
            (rule_id, value, threshold, desc))
        print(f"  ⚠️ {desc}")

def check():
    c = psycopg2.connect(DB); cur = c.cursor()

    # 加载规则
    cur.execute("SELECT id, rule_name, metric, condition, threshold FROM alert_rules WHERE is_enabled")
    rules = {(r[2], r[3]): (r[0], r[4]) for r in cur.fetchall()}  # {(metric, cond): (id, threshold)}

    # 1. 库存告急 (查一次)
    if ('stock_days', 'lt') in rules:
        rid, thr = rules[('stock_days', 'lt')]
        cur.execute("""
            SELECT i.brand_name, i.location,
                   CASE WHEN COALESCE(s.month_qty,0)>0
                        THEN ROUND(i.stock_qty::numeric/(s.month_qty::numeric/31),0) ELSE 999 END as days
            FROM inventory_snapshot i
            LEFT JOIN (SELECT brand_name, store_name, SUM(quantity) as month_qty
                FROM sales_detail WHERE submit_date>=date_trunc('month',current_date) AND NOT is_return
                GROUP BY 1,2) s ON i.brand_name=s.brand_name AND i.location=s.store_name
            WHERE i.snapshot_date=(SELECT MAX(snapshot_date) FROM inventory_snapshot) AND i.location NOT LIKE '%仓'
              AND COALESCE(s.month_qty,0)>0
        """)
        for brand, loc, days in cur.fetchall():
            if int(days) < float(thr):
                log(cur, rid, days, thr, f"库存告急: {loc} {brand} 仅剩{int(days)}天")

    # 2. 退货率异常 (查一次)
    if ('return_rate', 'gt') in rules:
        rid, thr = rules[('return_rate', 'gt')]
        cur.execute("""
            SELECT COALESCE(SUM(CASE WHEN is_return THEN ABS(settle_amount) ELSE 0 END),0),
                   COALESCE(SUM(CASE WHEN NOT is_return THEN settle_amount ELSE 0 END),0)
            FROM sales_detail WHERE submit_date = CURRENT_DATE - 1
        """)
        ret, sales = cur.fetchone()
        if sales and float(ret)/float(sales)*100 > float(thr):
            log(cur, rid, round(float(ret)/float(sales)*100,1), thr,
                f"昨日退货率 {float(ret)/float(sales)*100:.1f}%")

    # 3. 日销变化 (查一次，同时检查骤降和暴增)
    cur.execute("""
        WITH yesterday AS (SELECT store_name, SUM(total_amt) as amt FROM mv_store_daily WHERE submit_date=CURRENT_DATE-1 GROUP BY 1),
             last_week AS (SELECT store_name, SUM(total_amt) as amt FROM mv_store_daily WHERE submit_date=CURRENT_DATE-8 GROUP BY 1)
        SELECT y.store_name, y.amt, lw.amt, CASE WHEN lw.amt>0 THEN (y.amt-lw.amt)/lw.amt*100 ELSE 0 END
        FROM yesterday y JOIN last_week lw ON y.store_name=lw.store_name WHERE y.amt>0 AND lw.amt>0
    """)
    for store, today, last_wk, change in cur.fetchall():
        change = float(change)
        # 骤降
        if ('daily_sales', 'drop_below') in rules:
            rid, thr = rules[('daily_sales', 'drop_below')]
            if change < -float(thr):
                log(cur, rid, round(change,1), thr,
                    f"{store} 日销周同比骤降{abs(change):.0f}% (¥{float(today):,.0f} vs ¥{float(last_wk):,.0f})")
        # 暴增
        if ('daily_sales', 'spike_above') in rules:
            rid, thr = rules[('daily_sales', 'spike_above')]
            if change > float(thr):
                log(cur, rid, round(change,1), thr,
                    f"{store} 日销周同比暴增{change:.0f}% (¥{float(today):,.0f} vs ¥{float(last_wk):,.0f})")

    c.commit(); cur.close(); c.close()

if __name__ == '__main__':
    print(f"🔔 预警检查 {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    check()
    print("✅ 完成")
