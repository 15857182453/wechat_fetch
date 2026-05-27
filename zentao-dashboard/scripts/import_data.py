"""
禅道质量数据导入脚本 - Excel → SQLite

支持格式:
  需求表: "2026-1-V1版本-01-需求跟踪矩阵.xlsx" → requirement 表
  Bug表:  "2026-1-V1版本-Bug总数及分布.xlsx"  → bug 表

用法:
    python scripts/import_data.py "2026-1-V1版本-01-需求跟踪矩阵.xlsx"
    python scripts/import_data.py --dir "/mnt/d/钉钉下载/1研发中心质控部基础数据"
    python scripts/import_data.py --stats
"""

import argparse
import re
import sqlite3
import sys
from pathlib import Path

import pandas as pd

SCRIPT_DIR = Path(__file__).parent
PROJECT_DIR = SCRIPT_DIR.parent
DB_PATH = PROJECT_DIR / "data" / "zentao.db"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

VERSION_RE = re.compile(r'(\d{4})-(\d+)-V(\d+)')


def parse_version_code(filename: str) -> str:
    m = VERSION_RE.search(filename)
    if m:
        return f"{m.group(1)}-{m.group(2)}-V{m.group(3)}"
    return Path(filename).stem


def detect_file_type(filepath: str) -> str:
    name = Path(filepath).stem
    if '需求' in filepath:
        return 'requirement'
    if 'bug' in name.lower():
        return 'bug'
    if VERSION_RE.search(name):
        return 'bug' if 'bug' in name.lower() else 'requirement'
    return 'unknown'


def init_db(db_path: str) -> sqlite3.Connection:
    schema_file = PROJECT_DIR / "db_schema.sql"
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    if schema_file.exists():
        conn.executescript(schema_file.read_text(encoding='utf-8'))
    conn.commit()
    return conn


def get_or_create_version(conn, version_code, version_name=None,
                          version_type=None, project_id=None, source_file=None):
    row = conn.execute("SELECT id FROM version WHERE version_code = ?", (version_code,)).fetchone()
    if row:
        return row[0]
    release_date = None
    m = re.search(r'（(\d{4})）', version_name or '')
    if m:
        ds = m.group(1)
        if len(ds) == 4:
            release_date = f"2026-{ds[:2]}-{ds[2:]}"
    conn.execute(
        "INSERT INTO version (version_code, version_name, release_date, version_type, project_id, source_file) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (version_code, version_name, release_date, version_type, project_id, source_file))
    return conn.execute("SELECT last_insert_rowid()").fetchone()[0]


def clean_value(val, dtype=str):
    if pd.isna(val):
        return None
    if dtype == str:
        s = str(val).strip()
        return s if s else None
    if dtype == float:
        try:
            return float(val)
        except (ValueError, TypeError):
            return None
    if dtype == int:
        try:
            return int(float(val))
        except (ValueError, TypeError):
            return None
    return val


def to_datetime_str(val):
    if val is None or pd.isna(val):
        return None
    if isinstance(val, pd.Timestamp):
        return val.strftime('%Y-%m-%d %H:%M:%S')
    if isinstance(val, (int, float)):
        if val < 1000:
            return str(val)
        try:
            dt = pd.to_datetime('1899-12-30') + pd.Timedelta(days=val)
            return dt.strftime('%Y-%m-%d %H:%M:%S')
        except Exception:
            return str(val)
    s = str(val).strip()
    if s in ('0000-00-00', '0000-00-00 00:00:00', ''):
        return None
    return s


def import_requirements(conn, filepath):
    source_file = Path(filepath).name
    version_code = parse_version_code(source_file)
    try:
        df = pd.read_excel(filepath, sheet_name='需求跟踪矩阵', header=0)
        df = df[pd.to_numeric(df['月度'], errors='coerce').notna()].copy()
    except Exception as e:
        print(f"  ❌ 读取失败: {e}")
        return {'total': 0, 'success': 0, 'skipped': 0}

    total = len(df)
    print(f"  📋 需求数据: {total} 行")

    version_name = clean_value(df['版本名称'].dropna().iloc[0])
    version_type = clean_value(df['类型'].dropna().iloc[0])
    project_id = clean_value(df['项目ID'].dropna().iloc[0], float)
    if project_id:
        project_id = int(project_id)
    version_id = get_or_create_version(conn, version_code, version_name,
                                       version_type, project_id, source_file)

    existing_ids = set()  # (version_id, req_id)
    existing_title_pm = set()  # (version_id, title, pm) - only used when req_id is None
    for req_id, title, pm in conn.execute(
            "SELECT req_id, req_title, product_manager FROM requirement WHERE version_id = ?", (version_id,)):
        if req_id:
            existing_ids.add((version_id, req_id))
        if title and pm:
            existing_title_pm.add((version_id, title, pm))

    columns = [
        'version_id', 'yuedu', 'zhoushu', 'banben_name', 'leixing', 'project_id_raw',
        'dept_level1', 'dept_level2', 'business_module', 'req_type', 'req_status',
        'product_manager', 'req_id', 'bug_id', 'priority', 'project_rating',
        'is_third_party', 'is_customized', 'is_disputed', 'req_title',
        'req_submit_time', 'developer', 'tester', 'test_submit_time',
        'assign_time', 'release_time', 'acceptance_result', 'accept_fail_type',
        'accept_fail_reason', 'is_delayed_test', 'remark',
        'response_days', 'consumed_hours',
        'org_name', 'region', 'sub_region', 'feedback_priority', 'feedback_time',
    ]
    placeholders = ', '.join(['?'] * len(columns))
    insert_sql = f"INSERT INTO requirement ({', '.join(columns)}) VALUES ({placeholders})"

    rows = []
    success = 0
    skipped = 0

    for _, row in df.iterrows():
        req_id_val = clean_value(row['需求ID'])
        if req_id_val:
            req_id_val = str(int(float(req_id_val)))
        req_title_val = clean_value(row['需求名称'])
        product_mgr_val = clean_value(row['产品经理'])

        dup_key_id = (version_id, req_id_val) if req_id_val else None

        # req_id 存在时只检查 req_id 重复（不同 req_id 但相同 title+PM 是合法数据）
        if dup_key_id and dup_key_id in existing_ids:
            skipped += 1
            continue

        # req_id 为空时，用 title+PM 作为去重键
        if not req_id_val:
            dup_key_name = (version_id, req_title_val, product_mgr_val)
            if dup_key_name and dup_key_name in existing_title_pm:
                skipped += 1
                continue
            if dup_key_name:
                existing_title_pm.add(dup_key_name)

        if dup_key_id:
            existing_ids.add(dup_key_id)

        rows.append((
            version_id,
            clean_value(row['月度']), clean_value(row['周数']),
            clean_value(row['版本名称']), clean_value(row['类型']),
            clean_value(row['项目ID'], float),
            clean_value(row['一级部门']), clean_value(row['二级部门']),
            clean_value(row['所属业务模块']),
            clean_value(row['需求类型']), clean_value(row['需求状态']),
            product_mgr_val, req_id_val,
            clean_value(row['bugID']), clean_value(row['优先级']),
            clean_value(row['项目需求评级']),
            clean_value(row['是否对接第三方']), clean_value(row['是否为个性化']),
            clean_value(row['是否为争议']),
            req_title_val,
            to_datetime_str(row.get('需求提交时间')),
            clean_value(row['对应研发']), clean_value(row['对应测试']),
            to_datetime_str(row.get('提测时间')),
            to_datetime_str(row.get('被指派时间')),
            to_datetime_str(row.get('发版完成时间')),
            clean_value(row['验收是否通过']),
            clean_value(row['未通过分类']), clean_value(row['未通过原因']),
            clean_value(row['是否延期提测']), clean_value(row['备注']),
            clean_value(row['响应时长'], float),
            clean_value(row['消耗工时'], float),
            clean_value(row.get('机构名称-zentao_new-zt_feedback.organization')),
            clean_value(row['大区']), clean_value(row['分区']),
            clean_value(row.get('反馈优先级', row.get('分区'))),
            to_datetime_str(row.get('反馈创建时间')),
        ))
        success += 1

    if rows:
        conn.executemany(insert_sql, rows)
    conn.commit()
    print(f"  ✅ 新增 {success}, 跳过 {skipped}")
    return {'total': total, 'success': success, 'skipped': skipped}


def find_bug_sheet(filepath):
    xls = pd.ExcelFile(filepath)
    for name in xls.sheet_names:
        if '原始' in name or '原始bug' in name:
            return name
    max_rows, max_name = 0, xls.sheet_names[0]
    for name in xls.sheet_names:
        n = len(pd.read_excel(filepath, sheet_name=name, header=None))
        if n > max_rows:
            max_rows, max_name = n, name
    return max_name


def import_bugs(conn, filepath):
    source_file = Path(filepath).name
    version_code = parse_version_code(source_file)
    sheet_name = find_bug_sheet(filepath)
    print(f"  🐛 Bug sheet: '{sheet_name}'")

    try:
        df = pd.read_excel(filepath, sheet_name=sheet_name, header=0)
        df = df[pd.to_numeric(df['Bug编号'], errors='coerce').notna()].copy()
    except Exception as e:
        print(f"  ❌ 读取失败: {e}")
        return {'total': 0, 'success': 0, 'skipped': 0}

    total = len(df)
    print(f"  📋 Bug数据: {total} 行")
    version_id = get_or_create_version(conn, version_code, source_file=source_file)

    existing_ids = {r[0] for r in conn.execute("SELECT bug_id FROM bug WHERE version_id = ?", (version_id,))}

    columns = [
        'version_id', 'test_stage', 'bug_id', 'product', 'module_path', 'project_name',
        'related_req', 'related_task', 'bug_title', 'severity', 'bug_priority', 'bug_type',
        'os', 'browser', 'bug_status', 'deadline', 'activate_count', 'is_confirmed',
        'assignee', 'assign_date', 'resolver', 'solution', 'resolve_version', 'resolve_date',
        'closer', 'close_date', 'duplicate_id', 'related_bug', 'related_case',
        'creator', 'create_time', 'last_modifier', 'modify_time',
        'keywords', 'cc_to', 'impact_version', 'has_attachment',
        'role', 'dept_level2_bug', 'dept_level1_bug', 'business_line',
    ]
    placeholders = ', '.join(['?'] * len(columns))
    insert_sql = f"INSERT INTO bug ({', '.join(columns)}) VALUES ({placeholders})"

    rows = []
    success = 0
    skipped = 0

    for _, row in df.iterrows():
        bug_id_val = clean_value(row['Bug编号'], int)
        if bug_id_val and bug_id_val in existing_ids:
            skipped += 1
            continue
        if bug_id_val:
            existing_ids.add(bug_id_val)

        attach_val = clean_value(row.get('附件'))
        has_attachment = 1 if attach_val and str(attach_val).strip() else 0

        rows.append((
            version_id,
            clean_value(row.get('测试阶段')), bug_id_val,
            clean_value(row.get('所属产品')), clean_value(row.get('所属模块')),
            clean_value(row.get('所属项目')),
            clean_value(row.get('相关需求')), clean_value(row.get('相关任务')),
            clean_value(row.get('Bug标题')),
            clean_value(row.get('严重程度'), int), clean_value(row.get('优先级'), int),
            clean_value(row.get('Bug类型')),
            clean_value(row.get('操作系统')), clean_value(row.get('浏览器')),
            clean_value(row.get('Bug状态')), clean_value(row.get('截止日期')),
            clean_value(row.get('激活次数'), int), clean_value(row.get('是否确认')),
            clean_value(row.get('指派给')), to_datetime_str(row.get('指派日期')),
            clean_value(row.get('解决者')), clean_value(row.get('解决方案')),
            clean_value(row.get('解决版本')), to_datetime_str(row.get('解决日期')),
            clean_value(row.get('由谁关闭')), to_datetime_str(row.get('关闭日期')),
            clean_value(row.get('重复ID')), clean_value(row.get('相关Bug')),
            clean_value(row.get('相关用例')),
            clean_value(row.get('由谁创建')), to_datetime_str(row.get('创建日期')),
            clean_value(row.get('最后修改者')), to_datetime_str(row.get('修改日期')),
            clean_value(row.get('关键词')), clean_value(row.get('抄送给')),
            clean_value(row.get('影响版本')), has_attachment,
            clean_value(row.get('所属岗位')), clean_value(row.get('所属二级部门')),
            clean_value(row.get('所属一级部门')), clean_value(row.get('所属业务线')),
        ))
        success += 1

    if rows:
        conn.executemany(insert_sql, rows)
    conn.commit()
    print(f"  ✅ 新增 {success}, 跳过 {skipped}")
    return {'total': total, 'success': success, 'skipped': skipped}


def import_staff(conn, filepath):
    try:
        df = pd.read_excel(filepath, sheet_name='人员资料表', header=None)
    except Exception:
        return {'total': 0, 'success': 0, 'skipped': 0}

    header_row = None
    for i in range(min(5, len(df))):
        row_str = ' '.join(str(x) for x in df.iloc[i])
        if '姓名' in row_str and '一级部门' in row_str:
            header_row = i
            break
    if header_row is None:
        return {'total': 0, 'success': 0, 'skipped': 0}

    df = df.iloc[header_row + 1:].copy()
    df.columns = ['idx', 'name', 'dept_level1', 'dept_level2', 'business_line', 'role']
    df = df[df['name'].notna() & (df['name'] != '')].copy()

    total = len(df)
    success = 0
    for _, row in df.iterrows():
        name = clean_value(row['name'])
        if not name:
            continue
        existing = conn.execute("SELECT id FROM staff WHERE name = ?", (name,)).fetchone()
        if existing:
            conn.execute(
                "UPDATE staff SET dept_level1=?, dept_level2=?, business_line=?, role=? WHERE name=?",
                (clean_value(row['dept_level1']), clean_value(row['dept_level2']),
                 clean_value(row['business_line']), clean_value(row['role']), name))
        else:
            conn.execute(
                "INSERT INTO staff (name, dept_level1, dept_level2, business_line, role) VALUES (?,?,?,?,?)",
                (name, clean_value(row['dept_level1']), clean_value(row['dept_level2']),
                 clean_value(row['business_line']), clean_value(row['role'])))
        success += 1
    conn.commit()
    return {'total': total, 'success': success, 'skipped': 0}


def show_stats(db_path):
    if not Path(db_path).exists():
        print("数据库不存在, 请先导入数据。")
        return
    conn = sqlite3.connect(db_path)
    print("\n📊 数据库统计:")
    for table in ['version', 'requirement', 'bug', 'staff']:
        count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        print(f"  {table}: {count} 条")
    print("\n📋 版本列表:")
    for row in conn.execute(
            "SELECT version_code, version_name, "
            "(SELECT COUNT(*) FROM requirement r WHERE r.version_id = v.id) AS reqs, "
            "(SELECT COUNT(*) FROM bug b WHERE b.version_id = v.id) AS bugs "
            "FROM version v ORDER BY version_code"):
        print(f"  {row[0]}  reqs={row[2]}  bugs={row[3]}")
    conn.close()


def main():
    parser = argparse.ArgumentParser(description='禅道质量数据导入工具')
    parser.add_argument('filepath', nargs='?', help='Excel 文件路径')
    parser.add_argument('--dir', help='批量导入整个目录')
    parser.add_argument('--db', default=str(DB_PATH), help='SQLite 数据库路径')
    parser.add_argument('--stats', action='store_true', help='仅查看数据库统计')
    args = parser.parse_args()

    if args.stats:
        show_stats(args.db)
        return
    if not args.filepath and not args.dir:
        parser.print_help()
        sys.exit(1)

    conn = init_db(args.db)
    files = []
    if args.dir:
        dir_path = Path(args.dir)
        if not dir_path.is_dir():
            print(f"❌ 目录不存在: {args.dir}")
            sys.exit(1)
        for f in sorted(dir_path.rglob('*.xlsx')):
            if not f.name.startswith('~$'):
                files.append(str(f))
    if args.filepath:
        files.append(args.filepath)

    print(f"📂 待处理文件: {len(files)} 个")
    for filepath in files:
        print(f"\n{'='*60}")
        print(f"📄 {Path(filepath).name}")
        file_type = detect_file_type(filepath)
        try:
            if file_type == 'requirement':
                import_requirements(conn, filepath)
            elif file_type == 'bug':
                import_bugs(conn, filepath)
                sr = import_staff(conn, filepath)
                if sr['total'] > 0:
                    print(f"  👥 人员: {sr['success']} 人")
            else:
                print("  ⚠️  无法识别文件类型, 跳过")
        except Exception as e:
            print(f"  ❌ 导入失败: {e}")

    conn.close()
    print(f"\n{'='*60}")
    show_stats(args.db)


if __name__ == '__main__':
    main()
