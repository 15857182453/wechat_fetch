#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Phase 1: 禅道远程数据库连通性测试
目标：验证能否连接到 172.16.21.180:3507 并读取表结构
"""

import sys
import os

# 添加当前目录到路径以导入 config
sys.path.append(os.path.dirname(__file__))

try:
    import pymysql
except ImportError:
    print(" 缺少 pymysql 库，请先运行: pip install pymysql")
    sys.exit(1)

from config import ZEN_TAO_DB

def test_connection():
    print("="*50)
    print("🚀 开始测试禅道远程数据库连接...")
    print(f" 地址：{ZEN_TAO_DB['host']}:{ZEN_TAO_DB['port']}")
    print(f"👤 用户：{ZEN_TAO_DB['user']}")
    print(f"💾 库名：{ZEN_TAO_DB['database']}")
    print("="*50)

    try:
        # 尝试连接
        conn = pymysql.connect(
            host=ZEN_TAO_DB['host'],
            port=ZEN_TAO_DB['port'],
            user=ZEN_TAO_DB['user'],
            password=ZEN_TAO_DB['password'],
            database=ZEN_TAO_DB['database'],
            charset=ZEN_TAO_DB['charset'],
            connect_timeout=10
        )
        print("\n✅ 数据库连接成功！")

        with conn.cursor() as cursor:
            # 1. 检查数据库版本
            cursor.execute("SELECT VERSION()")
            version = cursor.fetchone()
            print(f" 数据库版本：{version[0]}")

            # 2. 列出所有表
            cursor.execute("SHOW TABLES")
            tables = [row[0] for row in cursor.fetchall()]
            print(f"📋 发现表数量：{len(tables)}")

            # 3. 检查核心业务表是否存在
            core_tables = ['zt_story', 'zt_bug', 'zt_task', 'zt_project', 'zt_user', 'zt_action']
            found_tables = [t for t in core_tables if t in tables]
            missing_tables = [t for t in core_tables if t not in tables]

            print("\n🔍 核心表检查：")
            if found_tables:
                print(f"   ✅ 存在：{', '.join(found_tables)}")
            if missing_tables:
                print(f"   ⚠️ 未找到：{', '.join(missing_tables)}")

            # 4. 简单数据采样 (zt_project)
            if 'zt_project' in tables:
                cursor.execute("SELECT id, `name`, `begin`, `end` FROM zt_project ORDER BY id DESC LIMIT 3")
                projects = cursor.fetchall()
                print("\n📅 最新项目样本 (zt_project):")
                for p in projects:
                    print(f"   ID: {p[0]} | 名称：{p[1]} | 周期：{p[2]} ~ {p[3]}")

        conn.close()
        print("\n🎉 测试完成！连接正常，可以开始开发同步脚本。")
        return True

    except pymysql.err.OperationalError as e:
        print(f"\n 连接失败 (OperationalError): {e}")
        print("   可能原因：IP 不通、端口错误、账号密码错误、数据库不存在")
        return False
    except Exception as e:
        print(f"\n❌ 发生未知错误：{e}")
        return False

if __name__ == '__main__':
    test_connection()
