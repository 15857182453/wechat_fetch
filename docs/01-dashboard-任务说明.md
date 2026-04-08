# 📊 医院数据 Dashboard

## 📁 文件位置

- **主文件**: `/home/openclaw/workspace/dashboard_v3.py`
- **数据库**: `/home/openclaw/.openclaw/workspace/business_flow.db`
- **导入脚本**: `/home/openclaw/.openclaw/workspace/import_duizhang_robust.py`
- **使用文档**: `/home/openclaw/.openclaw/workspace/每日导入 - 使用说明.md`

## 🎯 功能描述

基于 Streamlit 构建的医院数据可视化仪表板，提供 6 个分析标签页和实时监控功能。

## ✨ 核心功能

### 1. 📊 总览
- KPI 指标卡片（总流水、订单数、日均流水）
- 各医院数据汇总表格
- 最新数据日期显示

### 2. 📈 趋势分析
- 每日流水趋势图（折线图）
- 每日订单趋势图
- 每日数据明细表

### 3. ⚠️ 异常监控
**4 种检测算法**:
- **Z-Score 检测**: 统计学异常（|Z| > 2.0）
- **IQR 检测**: 极端值检测（> Q3 + 1.5×IQR）
- **动态阈值检测**: 业务规则（min(中位数×1.3, 均值 +1.5×标准差)）
- **环比暴增 ⭐**: 前一日≥10 单 且 增长>200%

### 4. 🏆 医院排行
- 按流水金额排序
- 柱状图可视化
- Top 10 医院详情

### 5. 🗺️ 区域分布
- 各省份订单分布
- 饼图/柱状图展示
- 区域数据明细

### 6. 📉 月环比分析
**动态计算逻辑**:
- 自动计算到最新数据日期
- 本月 vs 上月同期
- 同比 vs 去年同期（2025 年 12 月）

**示例**:
```
最新数据：4 月 7 日
本月：4 月 1-7 日（7 天）
上月同期：3 月 1-7 日（7 天）
去年同期：2025-12-01 ~ 2025-12-07（7 天）
```

## 🚀 使用方法

### 启动 Dashboard

```bash
# 方法 1：使用 tmux（推荐，后台运行）
tmux new-session -d -s dashboard "streamlit run /home/openclaw/workspace/dashboard_v3.py --server.port 8501 --server.address 0.0.0.0"

# 方法 2：前台运行
streamlit run /home/openclaw/workspace/dashboard_v3.py --server.port 8501 --server.address 0.0.0.0
```

### 访问地址

- **本地**: http://localhost:8501
- **网络**: http://172.22.253.216:8501
- **外部**: http://39.170.7.143:8501

### 每日数据导入

```bash
# 一键导入
cd /home/openclaw/.openclaw/workspace
./daily_import.sh

# 或手动导入
python3 import_duizhang_robust.py
```

## 📊 数据源

**数据库**: SQLite
**路径**: `/home/openclaw/.openclaw/workspace/business_flow.db`

**主要表**:
- `duizhang_summary_2026`: 2026 年对账汇总（97 条记录）
- `duizhang_summary_2025`: 2025 年对账汇总（365 条记录）
- `daily_flow_2026_apr`: 4 月明细数据
- `ningxia_orders_2026_apr`: 宁夏订单数据

## 📋 配置说明

### 缓存设置

```python
@st.cache_data(ttl=300)  # 5 分钟缓存
def load_hospital_data():
    ...
```

### 数据库连接

```python
DB_PATH = "/home/openclaw/.openclaw/workspace/business_flow.db"
```

## 🐛 故障排查

### 问题 1：无法访问 Dashboard

```bash
# 检查进程
ps aux | grep streamlit

# 重启 Dashboard
tmux kill-session -t dashboard
tmux new-session -d -s dashboard "streamlit run /home/openclaw/workspace/dashboard_v3.py --server.port 8501 --server.address 0.0.0.0"
```

### 问题 2：数据不更新

```bash
# 清除缓存并重新导入
python3 import_duizhang_robust.py

# 重启 Dashboard
tmux kill-session -t dashboard
tmux new-session -d -s dashboard "streamlit run /home/openclaw/workspace/dashboard_v3.py --server.port 8501 --server.address 0.0.0.0"
```

### 问题 3：环比计算错误

检查 `duizhang_summary_2026` 表是否有数据：

```bash
python3 -c "
import sqlite3
conn = sqlite3.connect('/home/openclaw/.openclaw/workspace/business_flow.db')
c = conn.cursor()
c.execute('SELECT COUNT(*) FROM duizhang_summary_2026')
print(f'记录数：{c.fetchone()[0]}')
c.execute('SELECT MAX(date) FROM duizhang_summary_2026')
print(f'最新日期：{c.fetchone()[0]}')
"
```

## 📅 更新历史

- **2026-04-08**: 
  - ✅ 修复单位转换问题（元→万元）
  - ✅ 添加自动单位检测
  - ✅ 添加数据验证
  - ✅ 创建健壮版导入脚本

- **2026-04-07**: 
  - ✅ 初始版本（dashboard_v3.py）
  - ✅ 6 个标签页功能完成
  - ✅ 月环比动态计算

## 📞 支持

- 使用文档：`每日导入 - 使用说明.md`
- API 文档：`api 接口文档.md`
- 项目索引：`GITHUB_PROJECTS.md`

---

**创建日期**: 2026-04-07  
**最后更新**: 2026-04-08  
**维护者**: OpenClaw
