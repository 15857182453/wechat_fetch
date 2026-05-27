#!/usr/bin/env python3
"""
医院数据 Dashboard 自动检查与修复流程 v2
运行频率：每半个月一次（1日和15日 22:00）
检查范围：数据库所有表 + 汇总表一致性 + 预聚合表 + Dashboard 代码
"""

import sqlite3
import pandas as pd
import os
import glob
import datetime
import re
import subprocess
import shutil
import json

# ════════════════════════════════════════════
# 配置
# ════════════════════════════════════════════
DB_PATH = '/home/openclaw/.openclaw/workspace/business_flow.db'
EXCEL_SUMMARY = '/mnt/e/办公资料/业务对账数据/对账业务总表/新流水2026.xlsx'
DASHBOARD_FILE = '/home/openclaw/.openclaw/workspace/dashboard_v4.py'
REFRESH_PRESCRIPTION = '/home/openclaw/.openclaw/workspace/refresh_prescription_summary.py'
LOG_FILE = '/home/openclaw/.openclaw/workspace/auto_audit_log.txt'
LOG_MAX_LINES = 5000          # 日志轮转阈值
STREAMLIT_PORT = 8501         # Dashboard 端口

# 多路径自动发现
SEARCH_ROOTS = [
    '/mnt/e/办公资料/业务对账数据/',
    '/mnt/c/Users/44238/Desktop/业务对账数据/',
]

DATE_COL = 'yewu_wancheng_shijian'
AMOUNT_COL = 'amount'

COLUMNS_54 = [
    (0,"order_id","TEXT"),(1,"trans_no","TEXT"),(2,"refund_batch_no","TEXT"),
    (3,"biz_order_no","TEXT"),(4,"pay_method","TEXT"),(5,"pay_status","TEXT"),
    (6,"institution","TEXT"),(7,"institution_code","TEXT"),(8,"province","TEXT"),
    (9,"oper_person","TEXT"),(10,"ye_wu_lei_mu","TEXT"),(11,"ye_wu_zi_lei_mu","TEXT"),
    (12,"yewu_leixing","TEXT"),(13,"product_subcategory","TEXT"),(14,"operation_category","TEXT"),
    (15,"product_id","TEXT"),(16,"product_name","TEXT"),(17,"completion_status","TEXT"),
    (18,"yewu_wancheng_shijian","TEXT"),(19,"caiwu_ruzhang_shijian","TEXT"),
    (20,"data_status","TEXT"),(21,"shoukuan_shanghu","TEXT"),(22,"order_amount","REAL"),
    (23,"discount_amount","REAL"),(24,"amount","REAL"),(25,"daijiao_amount","REAL"),
    (26,"deposit","REAL"),(27,"logistics_fee","REAL"),(28,"hospital_share","REAL"),
    (29,"hospital_share_status","TEXT"),(30,"hospital_ratio","REAL"),
    (31,"third_party_name","TEXT"),(32,"third_party_amount","REAL"),
    (33,"third_party_share_status","TEXT"),(34,"third_party_ratio","REAL"),
    (35,"doctor_points","REAL"),(36,"doctor_share_status","TEXT"),(37,"doctor_ratio","REAL"),
    (38,"platform_amount","REAL"),(39,"platform_status","TEXT"),(40,"transaction_time","TEXT"),
    (41,"payment_time","TEXT"),(42,"exec_doctor","TEXT"),(43,"exec_doctor_id","TEXT"),
    (44,"in_or_out","TEXT"),(45,"check_time","TEXT"),(46,"is_cancelled","TEXT"),
    (47,"channel_amount","REAL"),(48,"payment_ref_no","TEXT"),(49,"team","TEXT"),
    (50,"is_workday","TEXT"),(51,"ref_doctor","TEXT"),(52,"ref_doctor_id","TEXT"),
    (53,"online_offline","TEXT"),
]

EXCLUDE_PATTERNS = ['_backup_', '_old', 'daily_flow_apr1', 'daily_flow_details']

# ════════════════════════════════════════════
# 日志
# ════════════════════════════════════════════
def log(msg):
    ts = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    line = f'[{ts}] {msg}'
    print(line)
    with open(LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(line + '\n')

def rotate_log():
    """日志轮转：超过阈值时归档旧日志"""
    try:
        if os.path.exists(LOG_FILE):
            with open(LOG_FILE, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            if len(lines) > LOG_MAX_LINES:
                archive = f'{LOG_FILE}.{datetime.datetime.now().strftime("%Y%m%d_%H%M%S")}'
                with open(archive, 'w', encoding='utf-8') as f:
                    f.writelines(lines[-1000:])  # 保留最近 1000 行
                with open(LOG_FILE, 'w', encoding='utf-8') as f:
                    f.writelines(lines[-500:])
                log(f'  📦 日志已轮转，旧日志归档到 {os.path.basename(archive)}')
    except Exception as e:
        pass

# ════════════════════════════════════════════
# 工具
# ════════════════════════════════════════════
def get_conn():
    return sqlite3.connect(DB_PATH)

def get_all_tables(conn):
    """获取所有表名，分类为活跃表、备份表、其他表"""
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    all_tables = [r[0] for r in cur.fetchall()]
    active, backup, other = [], [], []
    for t in all_tables:
        if any(p in t for p in EXCLUDE_PATTERNS):
            backup.append(t)
        elif t.startswith('daily_flow_2026_') and not t.endswith('_old') and '_backup' not in t:
            active.append(t)
        elif t in ['duizhang_summary_2026', 'duizhang_summary_2025', 'duizhang_detail_2026']:
            active.append(t)
        else:
            other.append(t)
    return active, backup, other

# ════════════════════════════════════════════
# 自动发现明细文件
# ════════════════════════════════════════════
def discover_detail_files(month_num=None, min_cols=50):
    """
    自动扫描所有 SEARCH_ROOTS（递归），发现明细 Excel 文件
    month_num: 指定月份数字 (如 5)，None 表示发现所有
    """
    files = []
    for root in SEARCH_ROOTS:
        if not os.path.isdir(root):
            continue
        # 递归遍历所有子目录
        for dirpath, dirnames, filenames in os.walk(root):
            # 如果指定月份，只匹配月份文件夹
            if month_num:
                dirname = os.path.basename(dirpath)
                month_prefixes = [f'{month_num}-', f'{month_num}月']
                dir_match = any(dirname.startswith(p) for p in month_prefixes)
                # 也匹配父目录包含月份名的情况 (如 4月/4-1/)
                parent_match = any(str(month_num) == p for p in re.findall(r'(\d+)[-月/]', dirpath))
                if not (dir_match or parent_match):
                    continue
            # 查找明细文件
            for f in sorted(filenames):
                if f.startswith('业务对账统计明细') and f.endswith('.xlsx'):
                    fp = os.path.join(dirpath, f)
                    try:
                        df = pd.read_excel(fp, header=None, nrows=1)
                        if df.shape[1] >= min_cols:
                            files.append(fp)
                    except Exception:
                        pass
    # 去重
    seen_basenames = set()
    unique_files = []
    for f in files:
        bn = os.path.basename(f)
        if bn not in seen_basenames:
            seen_basenames.add(bn)
            unique_files.append(f)
    return unique_files

# ════════════════════════════════════════════
# 阶段1: 数据库全表检查
# ════════════════════════════════════════════
def check_all_tables():
    log('=== 阶段1: 数据库全表检查 ===')
    issues = []
    conn = get_conn()
    cur = conn.cursor()
    active_tables, backup_tables, other_tables = get_all_tables(conn)
    log(f'  活跃表: {len(active_tables)}个 | 备份表: {len(backup_tables)}个 | 其他表: {len(other_tables)}个')
    
    for tbl in active_tables:
        try:
            cur.execute(f"SELECT COUNT(*) FROM {tbl}")
            total = cur.fetchone()[0]
            cur.execute(f"PRAGMA table_info({tbl})")
            cols = cur.fetchall()
            col_names = [c[1] for c in cols]
            
            # 日期列检查
            if DATE_COL in col_names:
                cur.execute(f"SELECT COUNT(*) FROM {tbl} WHERE {DATE_COL} IS NULL OR {DATE_COL} = ''")
                null_count = cur.fetchone()[0]
                cur.execute(f"SELECT COUNT(*) FROM {tbl} WHERE {DATE_COL} = 'NaT'")
                nat_count = cur.fetchone()[0]
                cur.execute(f"SELECT COUNT(*) FROM {tbl} WHERE {DATE_COL} NOT LIKE '2026-%' AND {DATE_COL} != '' AND {DATE_COL} IS NOT NULL")
                bad_date = cur.fetchone()[0]
                
                dirty_pct = (null_count + nat_count + bad_date) / total * 100 if total > 0 else 0
                if null_count > 0 or nat_count > 0 or bad_date > 0:
                    issues.append(f'{tbl}: 日期脏数据 NULL={null_count} NaT={nat_count} 非日期={bad_date} ({dirty_pct:.0f}%)')
                    log(f'  ❌ {tbl} ({total}行): NULL={null_count} | NaT={nat_count} | 非日期={bad_date} ({dirty_pct:.0f}%)')
                else:
                    log(f'  ✅ {tbl} ({total}行): 日期干净')
            
            # amount 天文数字
            if AMOUNT_COL in col_names:
                cur.execute(f"SELECT COUNT(*) FROM {tbl} WHERE {AMOUNT_COL} > 1e15")
                huge = cur.fetchone()[0]
                if huge > 0:
                    issues.append(f'{tbl}: amount 天文数字 {huge} 条')
                    log(f'  ❌ {tbl}: amount 天文数字 {huge} 条')
            
            # third_party_name 异常
            if 'third_party_name' in col_names:
                cur.execute(f"SELECT COUNT(*) FROM {tbl} WHERE third_party_name = ''")
                empty_tp = cur.fetchone()[0]
                cur.execute(f"SELECT COUNT(*) FROM {tbl} WHERE third_party_name NOT GLOB '[a-zA-Z\u4e00-\u9fff]*' AND third_party_name IS NOT NULL AND third_party_name != ''")
                num_tp = cur.fetchone()[0]
                if empty_tp > total * 0.1 or num_tp > 0:
                    issues.append(f'{tbl}: third_party_name 异常 空串={empty_tp} 纯数字={num_tp}')
                    log(f'  ⚠️ {tbl}: third_party_name 空串={empty_tp} 纯数字={num_tp}')
                    
        except Exception as e:
            log(f'  ❌ 检查 {tbl} 失败: {e}')
            issues.append(f'{tbl}: 检查异常 {e}')
    
    if len(backup_tables) > 5:
        log(f'  ⚠️ 备份表过多 ({len(backup_tables)}个)，建议清理')
        issues.append(f'备份表过多: {len(backup_tables)}个')
    
    conn.close()
    return issues

# ════════════════════════════════════════════
# 阶段2: 汇总表 vs Excel 一致性
# ════════════════════════════════════════════
def check_summary_consistency():
    log('=== 阶段2: 汇总表 vs Excel 一致性 ===')
    issues = []
    if not os.path.exists(EXCEL_SUMMARY):
        log(f'  ⚠️ Excel 源文件不存在: {EXCEL_SUMMARY}')
        return [f'Excel 源文件缺失: {EXCEL_SUMMARY}']
    
    try:
        df = pd.read_excel(EXCEL_SUMMARY, header=None, skiprows=4)
        valid = df[pd.notna(df[0])].copy()
        # 过滤非日期行（"总计"、"流水汇总"等）
        valid = valid[valid[0].astype(str).str.match(r'^\d{4}-\d{2}-\d{2}')]
        valid['date'] = pd.to_datetime(valid[0]).dt.strftime('%Y-%m-%d')
        valid['flow'] = pd.to_numeric(valid[24], errors='coerce')
        valid = valid[valid['flow'].notna() & (valid['flow'] > 0)]
        
        conn = get_conn()
        cur = conn.cursor()
        cur.execute('SELECT date, daily_total_flow FROM duizhang_summary_2026 ORDER BY date')
        db_data = {r[0]: r[1] for r in cur.fetchall()}
        
        excel_data = valid.set_index('date')['flow'].to_dict()
        
        mismatches, missing_in_db = [], []
        for date_str, excel_val in excel_data.items():
            if date_str in db_data:
                if abs(db_data[date_str] - excel_val) > 0.01:
                    mismatches.append(f'{date_str}(数值不一致: DB={db_data[date_str]}, Excel={excel_val})')
            else:
                missing_in_db.append(date_str)
                mismatches.append(f'{date_str}(DB缺失)')
        
        missing_in_excel = [d for d in db_data if d not in excel_data]
        
        if mismatches:
            issues.append(f'汇总表不匹配 {len(mismatches)} 天: {mismatches[:3]}...')
            log(f'  ❌ 不匹配 {len(mismatches)} 天: {mismatches[:5]}')
        else:
            log('  ✅ 汇总表一致')
        
        if missing_in_excel:
            log(f'  ⚠️ DB有但Excel无: {missing_in_excel[:5]}')
        
        # 分类流水 NULL
        cur.execute('SELECT COUNT(*) FROM duizhang_summary_2026 WHERE ywul_class_flow IS NULL AND daily_total_flow > 0')
        null_cat = cur.fetchone()[0]
        if null_cat > 10:
            issues.append(f'{null_cat} 行分类流水为 NULL')
            log(f'  ❌ {null_cat} 行分类流水为 NULL')
        
        conn.close()
    except Exception as e:
        log(f'  ❌ 检查失败: {e}')
        issues.append(f'汇总表检查异常: {e}')
    return issues

# ════════════════════════════════════════════
# 阶段3: 当月数据完整性
# ════════════════════════════════════════════
def check_current_month_completeness(month=None):
    """检查当前月份汇总表 vs 明细表一致性"""
    if month is None:
        month = datetime.datetime.now().month
    log(f'=== 阶段3: {month}月数据完整性 ===')
    issues = []
    conn = get_conn()
    cur = conn.cursor()
    
    # 映射月份数字 -> 实际表名
    month_names = {1:'jan',2:'feb',3:'mar',4:'apr',5:'may',6:'jun',
                   7:'jul',8:'aug',9:'sep',10:'oct',11:'nov',12:'dec'}
    mname = month_names.get(month, f'{month:02d}')
    tbl = f'daily_flow_2026_{mname}'
    month_start = f'2026-{month:02d}-01'
    today = datetime.datetime.now().strftime('%Y-%m-%d')
    
    # 汇总表日期（有实际数据的）
    cur.execute('SELECT date FROM duizhang_summary_2026 WHERE date >= ? AND date <= ? AND daily_total_flow > 0 ORDER BY date',
                (month_start, today))
    summary_dates = set(r[0] for r in cur.fetchall())
    
    # 明细表日期
    if tbl in [r[0] for r in cur.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]:
        cur.execute(f'''SELECT DISTINCT substr(yewu_wancheng_shijian,1,10) FROM {tbl}
            WHERE yewu_wancheng_shijian >= ? AND yewu_wancheng_shijian IS NOT NULL 
            AND yewu_wancheng_shijian != "" AND yewu_wancheng_shijian != "NaT"''', (month_start,))
        detail_dates = set(r[0] for r in cur.fetchall())
        
        missing_detail = summary_dates - detail_dates
        if missing_detail:
            issues.append(f'{month}月明细表缺失 {len(missing_detail)} 天: {sorted(missing_detail)}')
            log(f'  ❌ 明细表缺失: {sorted(missing_detail)}')
        else:
            log(f'  ✅ {month}月数据完整')
    else:
        log(f'  ⚠️ 明细表 {tbl} 不存在')
    
    conn.close()
    return issues

# ════════════════════════════════════════════
# 阶段4: 预聚合表检查
# ════════════════════════════════════════════
def check_prescription_summary():
    log('=== 阶段4: 预聚合表检查 ===')
    issues = []
    conn = get_conn()
    cur = conn.cursor()
    
    # 检查表是否存在
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='prescription_summary'")
    if not cur.fetchone():
        issues.append('prescription_summary 表不存在')
        log('  ❌ 预聚合表不存在')
        conn.close()
        return issues
    
    # 检查异常 dt
    cur.execute("SELECT COUNT(*) FROM prescription_summary WHERE dt NOT LIKE '20%'")
    bad_dt = cur.fetchone()[0]
    if bad_dt > 0:
        cur.execute("SELECT DISTINCT dt FROM prescription_summary WHERE dt NOT LIKE '20%' LIMIT 5")
        bad_vals = [r[0] for r in cur.fetchall()]
        issues.append(f'预聚合表脏 dt={bad_dt} 条: {bad_vals}')
        log(f'  ❌ 预聚合表脏 dt={bad_dt} 条: {bad_vals}')
    else:
        log(f'  ✅ 预聚合表干净')
    
    # 检查最新日期
    cur.execute("SELECT MAX(dt) FROM prescription_summary WHERE dt LIKE '20%'")
    latest = cur.fetchone()[0]
    cur.execute("SELECT MAX(date(yewu_wancheng_shijian)) FROM daily_flow_2026_may WHERE yewu_wancheng_shijian IS NOT NULL")
    latest_detail = cur.fetchone()[0]
    if latest and latest_detail:
        log(f'  预聚合最新: {latest} | 明细最新: {latest_detail[:10]}')
        if latest < latest_detail[:10]:
            issues.append(f'预聚合表落后: {latest} < {latest_detail[:10]}')
            log(f'  ❌ 预聚合表落后')
    
    conn.close()
    return issues

# ════════════════════════════════════════════
# 阶段5: Dashboard 代码检查
# ════════════════════════════════════════════
def check_dashboard_code():
    log('=== 阶段5: Dashboard 代码检查 ===')
    issues = []
    
    if not os.path.exists(DASHBOARD_FILE):
        log(f'  ⚠️ Dashboard 文件不存在: {DASHBOARD_FILE}')
        return [f'Dashboard 文件不存在']
    
    try:
        with open(DASHBOARD_FILE, 'r', encoding='utf-8') as f:
            content = f.read()
        
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'daily_flow_2026_%' ORDER BY name")
        db_month_tables = set(r[0] for r in cur.fetchall() if '_backup' not in r[0] and '_old' not in r[0])
        conn.close()
        
        # 检查代码引用的月表
        code_tables = set()
        for t in ['daily_flow_2026_jan', 'daily_flow_2026_feb', 'daily_flow_2026_mar',
                   'daily_flow_2026_apr', 'daily_flow_2026_may', 'daily_flow_2026_jun',
                   'daily_flow_2026_jul', 'daily_flow_2026_aug', 'daily_flow_2026_sep',
                   'daily_flow_2026_oct', 'daily_flow_2026_nov', 'daily_flow_2026_dec',
                   'daily_flow_2026_jan_feb']:
            if t in content:
                code_tables.add(t)
        
        missing_in_code = db_month_tables - code_tables - {'daily_flow_2026_jan_feb'}
        if missing_in_code:
            issues.append(f'代码遗漏月表: {missing_in_code}')
            log(f'  ❌ 代码未引用: {missing_in_code}')
        else:
            log(f'  ✅ 代码引用了所有活跃月表 ({len(code_tables)}个)')
        
        # 检查硬编码单月查询
        functions = [
            'load_daily_express', 'load_week_hospital_top5', 'load_week_category',
            'load_week_province_top5', 'load_week_rx', 'load_tp_trend'
        ]
        for func in functions:
            if f'def {func}' in content:
                func_start = content.find(f'def {func}')
                next_def = content.find('\ndef ', func_start + 10)
                func_body = content[func_start:next_def] if next_def > 0 else content[func_start:func_start+2000]
                
                has_apr = 'daily_flow_2026_apr' in func_body
                has_union = 'UNION' in func_body
                has_tables = 'tables_2026' in func_body or 'table_names' in func_body
                
                if has_apr and not has_union and not has_tables:
                    issues.append(f'{func}: 疑似只查 apr 表')
                    log(f'  ❌ {func}: 疑似硬编码 apr')
        
        # 检查 auth_guard
        has_guard = 'auth_guard' in content or 'guard()' in content
        if has_guard:
            log('  ✅ 登录守卫已启用')
        
        # 检查硬编码过期日期
        import re
        hard_dates = re.findall(r'(?:5月|5/)\s*\d{1,2}\s*日', content)
        if hard_dates:
            issues.append(f'代码含硬编码日期: {hard_dates[:3]}')
            log(f'  ⚠️ 硬编码日期: {hard_dates[:3]}')
        
        if not issues:
            log('  ✅ 代码无已知问题')
            
    except Exception as e:
        log(f'  ❌ 检查失败: {e}')
        issues.append(f'代码检查异常: {e}')
    
    return issues

# ════════════════════════════════════════════
# 修复阶段
# ════════════════════════════════════════════
def repair_dirty_table(table_name, month_num=None):
    """重新导入指定表的数据（从自动发现的 Excel）"""
    log(f'=== 修复: {table_name} ===')
    try:
        if month_num is None:
            # 从表名推断月份
            m = re.search(r'daily_flow_2026_(\w+)', table_name)
            if m:
                mname = m.group(1)
                month_names = {'jan':1,'feb':2,'mar':3,'apr':4,'may':5,'jun':6,
                               'jul':7,'aug':8,'sep':9,'oct':10,'nov':11,'dec':12,
                               'jan_feb':1}
                month_num = month_names.get(mname)
        
        files = discover_detail_files(month_num)
        if not files:
            log(f'  ⚠️ 无有效源文件，跳过')
            return False
        
        log(f'  找到 {len(files)} 个源文件')
        
        conn = get_conn()
        cur = conn.cursor()
        
        # 备份
        backup_name = f'{table_name}_backup_{datetime.datetime.now().strftime("%Y%m%d_%H%M%S")}'
        cur.execute(f'CREATE TABLE IF NOT EXISTS {backup_name} AS SELECT * FROM {table_name}')
        conn.commit()
        log(f'  备份: {backup_name}')
        
        # 重建表
        cur.execute(f'DROP TABLE IF EXISTS {table_name}')
        cols_sql = ['id INTEGER PRIMARY KEY AUTOINCREMENT']
        for _, name, dtype in COLUMNS_54:
            cols_sql.append(f'{name} {dtype}')
        cols_sql.append('created_at TEXT')
        cur.execute(f'CREATE TABLE {table_name} ({", ".join(cols_sql)})')
        conn.commit()
        
        total_imported = 0
        for f in files:
            try:
                df = pd.read_excel(f, header=None, skiprows=1)
                if df.shape[1] < 50:
                    continue
                rows = []
                now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                for _, row in df.iterrows():
                    vals = []
                    for col_idx, col_name, col_type in COLUMNS_54:
                        v = row[col_idx] if col_idx < len(row) else None
                        if pd.notna(v):
                            vals.append(float(v) if col_type == 'REAL' else str(v))
                        else:
                            vals.append(None)
                    vals.append(now)
                    rows.append(tuple(vals))
                
                placeholders = ', '.join(['?'] * (len(COLUMNS_54) + 1))
                col_names = [c[1] for c in COLUMNS_54] + ['created_at']
                cur.executemany(f'INSERT INTO {table_name} ({", ".join(col_names)}) VALUES ({placeholders})', rows)
                total_imported += len(rows)
            except Exception as e:
                log(f'  ⚠️ 导入失败 {os.path.basename(f)}: {e}')
        
        conn.commit()
        cur.execute(f'SELECT COUNT(*) FROM {table_name}')
        final_count = cur.fetchone()[0]
        log(f'  ✅ 导入 {total_imported}行, 最终 {final_count}行')
        
        # 验证
        cur.execute(f"SELECT COUNT(*) FROM {table_name} WHERE {DATE_COL} IS NULL OR {DATE_COL} = ''")
        remaining_null = cur.fetchone()[0]
        cur.execute(f"SELECT COUNT(*) FROM {table_name} WHERE {DATE_COL} = 'NaT'")
        remaining_nat = cur.fetchone()[0]
        if remaining_null == 0 and remaining_nat == 0:
            log(f'  ✅ 验证通过: 日期干净')
        else:
            log(f'  ⚠️ 验证: 仍有 NULL={remaining_null} NaT={remaining_nat}')
        
        conn.close()
        return True
    except Exception as e:
        log(f'  ❌ 修复失败: {e}')
        return False

def repair_summary_missing_dates(missing_dates):
    """从 Excel 补入汇总表缺失日期"""
    log(f'=== 修复: 汇总表补全 {len(missing_dates)} 天 ===')
    try:
        df = pd.read_excel(EXCEL_SUMMARY, header=None, skiprows=4)
        valid = df[pd.notna(df[0])].copy()
        valid['date'] = pd.to_datetime(valid[0]).dt.strftime('%Y-%m-%d')
        
        # 列映射: Excel列索引 -> 数据库列名
        col_mapping = {
            1: 'ywul_class_flow', 2: 'ywul_class_orders',
            3: 'chufang_flow', 4: 'chufang_orders',
            5: 'tiujian_flow', 6: 'tiujian_orders',
            7: 'jianguan_flow', 8: 'jianguan_orders',
            9: 'disanfang_flow', 10: 'disanfang_orders',
            11: 'xinli_flow', 12: 'xinli_orders',
            13: 'zhifu_flow', 14: 'zhifu_orders',
            15: 'yuancheng_flow', 16: 'yuancheng_orders',
            17: 'huiyuan_flow', 18: 'huiyuan_orders',
            19: 'disanfang_tj_flow', 20: 'disanfang_tj_orders',
            21: 'shangcheng_flow', 22: 'shangcheng_orders',
            24: 'daily_total_flow', 25: 'daily_flow_increment', 26: 'daily_flow_ratio'
        }
        
        conn = get_conn()
        imported = 0
        for _, row in valid.iterrows():
            date_str = row['date']
            if date_str not in missing_dates:
                continue
            
            total = float(row[24]) if pd.notna(row[24]) else 0.0
            updates = {'daily_total_flow': total}
            for col_idx, db_col in col_mapping.items():
                if col_idx in [24]:
                    continue
                if col_idx < len(row) and pd.notna(row[col_idx]):
                    try:
                        val = float(row[col_idx])
                        updates[db_col] = val
                    except (ValueError, TypeError):
                        pass
            
            cols = list(updates.keys())
            vals = list(updates.values())
            placeholders = ','.join(['?'] * len(cols))
            cols_str = ','.join(cols)
            sql = f'INSERT OR REPLACE INTO duizhang_summary_2026 ({cols_str}) VALUES ({placeholders})'
            conn.execute(sql, vals)
            imported += 1
        
        conn.commit()
        log(f'  ✅ 已导入 {imported} 天')
        conn.close()
        return True
    except Exception as e:
        log(f'  ❌ 修复失败: {e}')
        return False

def repair_null_categories():
    """从 Excel 补充汇总表分类流水列"""
    log('=== 修复: 汇总表分类流水补充 ===')
    try:
        df = pd.read_excel(EXCEL_SUMMARY, header=None, skiprows=4)
        valid = df[pd.notna(df[0])].copy()
        valid['date'] = pd.to_datetime(valid[0]).dt.strftime('%Y-%m-%d')
        
        # ⚠️ 流量列需要 ÷10000（Excel 原始单位是元），增量/环比已是万元不需要除
        flow_cols = {1:'ywul_class_flow', 3:'chufang_flow', 5:'tiujian_flow',
                     7:'jianguan_flow', 9:'disanfang_flow', 11:'xinli_flow',
                     13:'zhifu_flow', 15:'yuancheng_flow', 17:'huiyuan_flow',
                     19:'disanfang_tj_flow', 21:'shangcheng_flow'}
        ratio_cols = {25:'daily_flow_increment', 26:'daily_flow_ratio'}
        
        conn = get_conn()
        updated = 0
        for _, row in valid.iterrows():
            date_str = row['date']
            updates = []
            for col_idx, db_col in flow_cols.items():
                if col_idx < len(row) and pd.notna(row[col_idx]):
                    val = float(row[col_idx]) / 10000
                    updates.append(f'{db_col} = {val}')
            for col_idx, db_col in ratio_cols.items():
                if col_idx < len(row) and pd.notna(row[col_idx]):
                    updates.append(f'{db_col} = {float(row[col_idx])}')
            
            if updates:
                sql = f'UPDATE duizhang_summary_2026 SET {", ".join(updates)} WHERE date = "{date_str}"'
                conn.execute(sql)
                updated += 1
        
        conn.commit()
        log(f'  ✅ 更新了 {updated} 行')
        conn.close()
        return True
    except Exception as e:
        log(f'  ❌ 修复失败: {e}')
        return False

def repair_prescription_summary():
    """刷新预聚合表"""
    log('=== 修复: 刷新预聚合表 ===')
    if not os.path.exists(REFRESH_PRESCRIPTION):
        log(f'  ⚠️ 脚本不存在: {REFRESH_PRESCRIPTION}')
        return False
    try:
        result = subprocess.run(
            ['python3', REFRESH_PRESCRIPTION],
            capture_output=True, text=True, timeout=120
        )
        if result.returncode == 0:
            log(f'  ✅ 预聚合表刷新成功')
            return True
        else:
            log(f'  ❌ 刷新失败: {result.stderr[-500:]}')
            return False
    except Exception as e:
        log(f'  ❌ 刷新失败: {e}')
        return False

def restart_dashboard():
    """重启 Dashboard"""
    log('=== 重启 Dashboard ===')
    try:
        subprocess.run(['lsof', '-ti', str(STREAMLIT_PORT)], capture_output=True, text=True)
        kill_result = subprocess.run(
            f'lsof -ti:{STREAMLIT_PORT} | xargs kill -9 2>/dev/null',
            shell=True, capture_output=True, text=True
        )
        subprocess.run(['sleep', '1'])
        
        workspace = os.path.dirname(DASHBOARD_FILE)
        subprocess.Popen(
            ['streamlit', 'run', DASHBOARD_FILE,
             '--server.port', str(STREAMLIT_PORT), '--server.headless', 'true'],
            cwd=workspace,
            stdout=open('/tmp/dashboard.log', 'w'),
            stderr=subprocess.STDOUT
        )
        subprocess.run(['sleep', '4'])
        
        import urllib.request
        try:
            code = urllib.request.urlopen(f'http://localhost:{STREAMLIT_PORT}', timeout=5).getcode()
            log(f'  ✅ Dashboard 已重启 (HTTP {code})')
            return True
        except Exception:
            log('  ⚠️ Dashboard 已启动，等待中...')
            return False
    except Exception as e:
        log(f'  ❌ 重启失败: {e}')
        return False

# ════════════════════════════════════════════
# 主流程
# ════════════════════════════════════════════
def main():
    rotate_log()
    
    log('='*60)
    log('🔍 自动检查与修复流程 v2 开始')
    log('='*60)
    
    all_issues = []
    
    # === 检查阶段 ===
    all_issues.extend(check_all_tables())
    all_issues.extend(check_summary_consistency())
    all_issues.extend(check_current_month_completeness())
    all_issues.extend(check_prescription_summary())
    all_issues.extend(check_dashboard_code())
    
    # === 修复阶段 ===
    if all_issues:
        log('')
        log('🔧 开始自动修复...')
        
        # 1. 修复脏数据表（所有 daily_flow_2026_* 表）
        dirty_tables = set()
        for issue in all_issues:
            if '日期脏数据' in issue:
                tbl = issue.split(':')[0]
                dirty_tables.add(tbl)
        
        for tbl in dirty_tables:
            month_num = None
            m = re.search(r'2026_(\w+)', tbl)
            if m:
                mname = m.group(1)
                month_names = {'jan':1,'feb':2,'mar':3,'apr':4,'may':5,'jun':6,
                               'jul':7,'aug':8,'sep':9,'oct':10,'nov':11,'dec':12,
                               'jan_feb':1}
                month_num = month_names.get(mname)
            repair_dirty_table(tbl, month_num)
        
        # 2. 修复汇总表缺失日期
        missing_dates = []
        for issue in all_issues:
            if 'DB缺失' in issue:
                parts = re.findall(r'(\d{4}-\d{2}-\d{2})\(DB缺失\)', issue)
                missing_dates.extend(parts)
        if missing_dates:
            repair_summary_missing_dates(set(missing_dates))
        
        # 3. 修复汇总表分类流水 NULL
        has_null_cat = any('分类流水' in i and 'NULL' in i for i in all_issues)
        if has_null_cat:
            repair_null_categories()
        
        # 4. 刷新预聚合表
        has_bad_dt = any('预聚合表' in i for i in all_issues)
        if has_bad_dt:
            repair_prescription_summary()
        else:
            # 即使没有明显问题，也定期刷新确保最新
            repair_prescription_summary()
        
        # 5. 重启 Dashboard
        restart_dashboard()
    else:
        log('')
        log('✅ 所有检查通过，无需修复')
        repair_prescription_summary()
    
    log('')
    log('='*60)
    if all_issues:
        log(f'📋 共发现 {len(all_issues)} 个问题')
        for i, issue in enumerate(all_issues, 1):
            log(f'  {i}. {issue}')
    log('🔍 自动检查与修复流程完成')
    log('='*60)

if __name__ == '__main__':
    main()
