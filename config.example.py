# 禅道自动化数据项目 - 核心配置（模板）
# 注意：请勿将此文件提交到公共代码仓库！
# 使用方法：复制此文件为 config.py，并填入实际的数据库密码

# === 禅道数据库配置 ===
ZEN_TAO_DB = {
    'host': '172.16.21.180',
    'port': 3507,
    'user': 'yangkr',
    'password': 'YOUR_PASSWORD_HERE',
    'database': 'zentao_new',
    'charset': 'utf8mb4'
}

# === 文件路径配置 ===
import os

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
LOCAL_CACHE_DB = os.path.join(PROJECT_ROOT, 'data', 'zentao_new_cache.db')
OUTPUT_DIR = os.path.join(PROJECT_ROOT, 'output')

TEMPLATE_MATRIX_PATH = r"E:\禅道自动化数据项目\1 研发中心质控部基础数据\需求表\2026-1-V1 版本-01-需求跟踪矩阵.xlsx"

# === 业务配置 ===
TARGET_PROJECT_IDS = [1970, 1977, 1984, 1990, 1996, 2002, 2007, 2012, 2019, 2025]
TARGET_PRODUCT_ID = 32
