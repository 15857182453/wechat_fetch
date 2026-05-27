# 禅道质量看板

研发中心质控部基础数据的可视化看板，基于 Streamlit + SQLite。

## 项目结构

```
zentao-dashboard/
├── app.py              # Streamlit 看板应用
├── db_schema.sql       # 数据库 Schema (4张表 + 5个视图)
├── data/
│   └── zentao.db       # SQLite 数据库 (自动生成)
├── scripts/
│   └── import_data.py  # Excel 导入脚本
└── templates/          # 模板文件
```

## 数据库设计

| 表 | 说明 | 字段数 |
|---|------|--------|
| version | 版本信息 | 8 |
| requirement | 需求 (1:1 映射 Excel 需求跟踪矩阵) | 37 |
| bug | Bug (1:1 映射 Excel 原始bug) | 53 |
| staff | 人员信息 | 7 |
| import_audit | 导入审计日志 | 11 |

## 快速开始

```bash
# 安装依赖
pip install -r requirements.txt

# 导入单个文件
python scripts/import_data.py "/mnt/d/钉钉下载/1研发中心质控部基础数据/需求表/2026-1-V1版本-01-需求跟踪矩阵.xlsx"

# 批量导入整个目录
python scripts/import_data.py --dir "/mnt/d/钉钉下载/1研发中心质控部基础数据"

# 查看统计
python scripts/import_data.py --stats

# 启动看板
streamlit run app.py
```

## 支持的文件

- **需求表**: `*需求跟踪矩阵.xlsx` — 读取 "需求跟踪矩阵" sheet
- **Bug表**: `*Bug总数及分布.xlsx` — 读取 "原始bug-xxx" sheet + "人员资料表"
- 自动跳过 `~$` 临时文件
- 增量导入，同版本同需求ID自动去重

## 注意事项

- `app.py` 为主入口，`app_v2.py` / `app_v3.py` 为开发历史版本
- 建议先运行 `python scripts/import_data.py --stats` 确认数据已导入
