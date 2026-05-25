#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Phase 2: 数据同步脚本
功能：从禅道远程数据库拉取核心数据，清洗后存入本地 SQLite 缓存库
数据源：仅来自 172.16.21.180 (zentao_new)
"""

import sys
import os
import sqlite3
import pandas as pd
import warnings
from datetime import datetime

warnings.filterwarnings('ignore')
sys.path.append(os.path.dirname(__file__))

import pymysql
from config import ZEN_TAO_DB, LOCAL_CACHE_DB, TARGET_PROJECT_IDS, OUTPUT_DIR

def init_local_db():
    """初始化本地 SQLite 缓存库"""
    os.makedirs(os.path.dirname(LOCAL_CACHE_DB), exist_ok=True)
    conn = sqlite3.connect(LOCAL_CACHE_DB)
    cursor = conn.cursor()

    # 创建核心表
    tables_sql = [
        """CREATE TABLE IF NOT EXISTS zt_project (
            id INTEGER PRIMARY KEY,
            name TEXT,
            `begin` TEXT,
            `end` TEXT,
            status TEXT,
            type TEXT,
            sync_time TEXT
        )""",
        """CREATE TABLE IF NOT EXISTS zt_story (
            id INTEGER PRIMARY KEY,
            product INTEGER,
            title TEXT,
            type TEXT,
            pri INTEGER,
            estimate REAL,
            status TEXT,
            stage TEXT,
            openedBy TEXT,
            openedDate TEXT,
            assignedTo TEXT,
            assignedDate TEXT,
            reviewedBy TEXT,
            reviewedDate TEXT,
            closedBy TEXT,
            closedDate TEXT,
            module INTEGER,
            feedback INTEGER,
            source TEXT,
            version INTEGER,
            deleted TEXT,
            sync_time TEXT
        )""",
        """CREATE TABLE IF NOT EXISTS zt_task (
            id INTEGER PRIMARY KEY,
            project INTEGER,
            story INTEGER,
            name TEXT,
            type TEXT,
            pri INTEGER,
            estimate REAL,
            consumed REAL,
            `left` REAL,
            status TEXT,
            openedBy TEXT,
            openedDate TEXT,
            assignedTo TEXT,
            realStarted TEXT,
            finishedBy TEXT,
            finishedDate TEXT,
            closedDate TEXT,
            deleted TEXT,
            sync_time TEXT
        )""",
        """CREATE TABLE IF NOT EXISTS zt_bug (
            id INTEGER PRIMARY KEY,
            product INTEGER,
            module INTEGER,
            story INTEGER,
            title TEXT,
            severity INTEGER,
            pri INTEGER,
            type TEXT,
            found TEXT,
            status TEXT,
            openedBy TEXT,
            openedDate TEXT,
            assignedTo TEXT,
            assignedDate TEXT,
            resolvedBy TEXT,
            resolvedDate TEXT,
            closedBy TEXT,
            closedDate TEXT,
            resolution TEXT,
            activatedCount INTEGER,
            feedback INTEGER,
            deleted TEXT,
            sync_time TEXT
        )""",
        """CREATE TABLE IF NOT EXISTS zt_user (
            account TEXT PRIMARY KEY,
            realname TEXT,
            dept INTEGER,
            role TEXT,
            sync_time TEXT
        )""",
        """CREATE TABLE IF NOT EXISTS zt_module (
            id INTEGER PRIMARY KEY,
            name TEXT,
            type TEXT,
            parent INTEGER,
            root INTEGER,
            sync_time TEXT
        )""",
        """CREATE TABLE IF NOT EXISTS zt_projectstory (
            project INTEGER,
            story INTEGER,
            version INTEGER,
            sync_time TEXT,
            PRIMARY KEY (project, story)
        )""",
        """CREATE TABLE IF NOT EXISTS zt_action (
            id INTEGER PRIMARY KEY,
            objectType TEXT,
            objectID INTEGER,
            actor TEXT,
            action TEXT,
            date TEXT,
            comment TEXT,
            extra TEXT,
            sync_time TEXT
        )""",
        """CREATE TABLE IF NOT EXISTS zt_feedback (
            id INTEGER PRIMARY KEY,
            product INTEGER,
            module INTEGER,
            title TEXT,
            organization TEXT,
            region TEXT,
            PRJLevel TEXT,
            pri INTEGER,
            openedBy TEXT,
            openedDate TEXT,
            status TEXT,
            sync_time TEXT
        )""",
        """CREATE TABLE IF NOT EXISTS zt_team (
            root INTEGER,
            type TEXT,
            account TEXT,
            role TEXT,
            days INTEGER,
            hours REAL,
            sync_time TEXT
        )""",
        """CREATE TABLE IF NOT EXISTS zt_product (
            id INTEGER PRIMARY KEY,
            name TEXT,
            code TEXT,
            line TEXT,
            status TEXT,
            sync_time TEXT
        )"""
    ]

    for sql in tables_sql:
        cursor.execute(sql)
    conn.commit()
    conn.close()
    print(f"✅ 本地缓存库初始化完成：{LOCAL_CACHE_DB}")

def fetch_remote_data():
    """从禅道远程库拉取数据"""
    print("📥 开始从禅道远程库拉取数据...")
    conn = pymysql.connect(**ZEN_TAO_DB)
    data = {}

    target_ids = ','.join(map(str, TARGET_PROJECT_IDS))
    sync_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    try:
        with conn.cursor(pymysql.cursors.DictCursor) as cursor:
            # 1. 项目表
            print("  [1/7] 拉取 zt_project...")
            cursor.execute(f"SELECT id, `name`, `begin`, `end`, status, type FROM zt_project WHERE id IN ({target_ids}) AND deleted='0'")
            data['project'] = pd.DataFrame(cursor.fetchall())

            # 2. 需求 - 项目关联
            print("  [2/7] 拉取 zt_projectstory...")
            cursor.execute(f"SELECT project, story, version FROM zt_projectstory WHERE project IN ({target_ids})")
            data['projectstory'] = pd.DataFrame(cursor.fetchall())

            # 3. 需求表 (只拉取关联到目标项目的需求)
            if not data['projectstory'].empty:
                story_ids = ','.join(map(str, data['projectstory']['story'].unique().tolist()))
                print(f"  [3/11] 拉取 zt_story ({len(data['projectstory']['story'].unique())} 个需求)...")
                cursor.execute(f"""
                    SELECT id, product, title, type, pri, estimate, status, stage, openedBy, openedDate,
                           assignedTo, assignedDate, reviewedBy, reviewedDate, closedBy, closedDate,
                           module, feedback, source, version, deleted
                    FROM zt_story
                    WHERE id IN ({story_ids})
                """)
                data['story'] = pd.DataFrame(cursor.fetchall())
            else:
                data['story'] = pd.DataFrame()

            # 4. 任务表 (关联到目标项目或目标需求)
            print("  [4/7] 拉取 zt_task...")
            if not data['story'].empty:
                task_story_ids = ','.join(map(str, data['story']['id'].tolist()))
                cursor.execute(f"""
                    SELECT id, project, story, `name`, type, pri, estimate, consumed, `left`,
                           status, openedBy, openedDate, assignedTo, realStarted,
                           finishedBy, finishedDate, closedDate, deleted
                    FROM zt_task
                    WHERE project IN ({target_ids}) AND deleted='0'
                """)
                data['task'] = pd.DataFrame(cursor.fetchall())
            else:
                data['task'] = pd.DataFrame()

            # 5. Bug 表
            print("  [5/11] 拉取 zt_bug...")
            if not data['story'].empty:
                product_ids = ','.join(map(str, data['story']['product'].unique().tolist()))
                cursor.execute(f"""
                    SELECT id, product, module, story, title, severity, pri, `type`, found,
                           status, openedBy, openedDate, assignedTo, assignedDate,
                           resolvedBy, resolvedDate, closedBy, closedDate,
                           resolution, activatedCount, feedback, deleted
                    FROM zt_bug
                    WHERE product IN ({product_ids}) AND deleted='0'
                    ORDER BY id DESC LIMIT 5000
                """)
                data['bug'] = pd.DataFrame(cursor.fetchall())
            else:
                data['bug'] = pd.DataFrame()

            # 6. 用户表
            print("  [6/11] 拉取 zt_user...")
            cursor.execute("SELECT account, realname, dept, role FROM zt_user WHERE deleted='0'")
            data['user'] = pd.DataFrame(cursor.fetchall())

            # 7. 模块表
            print("  [7/11] 拉取 zt_module...")
            cursor.execute("SELECT id, `name`, type, parent, root FROM zt_module WHERE type IN ('story', 'bug')")
            data['module'] = pd.DataFrame(cursor.fetchall())

            # 8. Action 表
            print("  [8/11] 拉取 zt_action (流转记录)...")
            if not data['story'].empty:
                action_ids = ','.join(map(str, data['story']['id'].tolist()))
                cursor.execute(f"""
                    SELECT id, objectType, objectID, actor, `action`, `date`, comment, extra
                    FROM zt_action
                    WHERE objectType='story' AND objectID IN ({action_ids})
                    ORDER BY date DESC
                """)
                data['action'] = pd.DataFrame(cursor.fetchall())
            else:
                data['action'] = pd.DataFrame()

            # 9. Feedback 表 (关联到目标需求的反馈)
            print("  [9/11] 拉取 zt_feedback...")
            if not data['story'].empty:
                feedback_ids = ','.join(map(str, data['story'][data['story']['feedback'] > 0]['feedback'].unique().tolist()))
                if feedback_ids:
                    cursor.execute(f"""
                        SELECT id, product, module, title, organization, region, PRJLevel, pri,
                               openedBy, openedDate, status
                        FROM zt_feedback
                        WHERE id IN ({feedback_ids})
                    """)
                    data['feedback'] = pd.DataFrame(cursor.fetchall())
                else:
                    data['feedback'] = pd.DataFrame()
            else:
                data['feedback'] = pd.DataFrame()

            # 10. 团队表 (目标项目成员，用于开发负载率)
            print("  [10/11] 拉取 zt_team...")
            cursor.execute(f"""
                SELECT root, `type`, account, role, days, hours
                FROM zt_team
                WHERE type='project' AND root IN ({target_ids})
            """)
            data['team'] = pd.DataFrame(cursor.fetchall())

            # 11. 产品表 (用于产品维度分析)
            print("  [11/11] 拉取 zt_product...")
            if not data['story'].empty:
                product_ids = ','.join(map(str, data['story']['product'].unique().tolist()))
                cursor.execute(f"SELECT id, `name`, code, line, status FROM zt_product WHERE id IN ({product_ids})")
                data['product'] = pd.DataFrame(cursor.fetchall())
            else:
                data['product'] = pd.DataFrame()

    finally:
        conn.close()

    # 添加同步时间戳
    for key in data:
        if not data[key].empty:
            data[key]['sync_time'] = sync_time

    return data

def save_to_local(data):
    """存入本地 SQLite，使用 UPSERT 策略"""
    print("\n💾 开始存入本地缓存库...")
    conn = sqlite3.connect(LOCAL_CACHE_DB)

    for table_name, df in data.items():
        if df.empty:
            print(f"  ⚠️ {table_name}: 无数据")
            continue

        # 加上 zt_ 前缀，与 init 创建的表名一致
        full_name = f"zt_{table_name}"

        # 删除旧表重新创建（replace 模式）
        cursor = conn.cursor()
        cursor.execute(f"DROP TABLE IF EXISTS {full_name}")
        conn.commit()

        df.to_sql(full_name, conn, if_exists='append', index=False)
        print(f"  ✅ {full_name}: {len(df)} 条记录")

    conn.close()
    print("✅ 数据同步完成！")

def main():
    print("="*50)
    print("🚀 禅道数据同步脚本 (Phase 2)")
    print("="*50)

    # 1. 初始化本地库
    init_local_db()

    # 2. 拉取远程数据
    data = fetch_remote_data()

    # 3. 存入本地
    save_to_local(data)

    print("\n🎉 同步流程结束！")

if __name__ == '__main__':
    main()
