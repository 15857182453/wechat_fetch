# 🧠 长期记忆

**创建日期**: 2026-04-08  
**最后更新**: 2026-04-10

---

## 🔑 永久规则（最高优先级）

### 文件路径
- **Windows**: `C:\Users\44238\Desktop\业务对账数据\`
- **Linux 挂载**: `/mnt/c/Users/44238/Desktop/业务对账数据/`
- 用户发 Windows 路径 → 自动转 `/mnt/c/...` 直接读取
- **不要问用户文件在哪**，自己去 `/mnt/c/` 找

### 每日导入流程
1. 扫描 `/mnt/c/.../业务对账数据/` 找最新 `业务对账统计明细-*.xlsx`
2. `cp` 到工作区
3. 识别文件类型：
   - **明细表**（54列）：交易明细 → `daily_flow_2026_apr`（增量 INSERT）
   - **汇总表**（28列）：`新流水2026.xlsx` → `duizhang_summary_2026`（INSERT OR REPLACE）
4. 增量导入（**绝不删表！**）
5. 更新汇总表
6. 重启 Dashboard

### 三大禁忌
1. ❌ 绝对不要 `DELETE FROM` 清表（4/9 犯过错，丢了 4/1-7 数据）
2. ❌ 不要问用户文件在哪，自己去 `/mnt/c/` 找
3. ❌ 启动会话必须先读 memory 文件

### Dashboard 版本
- **活跃**: `dashboard_v4.py`（42KB，4月9日修复版）
- **❌ 不要跑 v3**（12KB，老版本）
- 重启: `tmux kill-session -t dashboard` → `streamlit run dashboard_v4.py`

---

## 📊 核心业务

### 医院数据 Dashboard（v4）
- **文件**: `/home/openclaw/.openclaw/workspace/dashboard_v4.py`
- **访问**: http://localhost:8501
- **6 个标签页**: 总览、趋势、异常监控、排行、区域分布、月环比
- **异常检测**: 4 种算法（Z-Score、IQR、动态阈值、环比暴增）
- **v4 新增**: 患者地域分布、药品 TOP10 排行、就诊时段热力图、季节性药品分析

### 数据导入
- **健壮版脚本**: `import_duizhang_robust.py` — 自动检测单位（元/万元）、数据验证、去重
- **快捷脚本**: `daily_import.sh`
- **明细导入**: `import_detail_*.py`（54列 → `daily_flow_2026_apr`）

### 数据库
- **路径**: `/home/openclaw/.openclaw/workspace/business_flow.db`
- **主要表**:
  - `duizhang_summary_2026` — 每日汇总（~100 条，单位：万元）
  - `duizhang_summary_2025` — 2025 全年（365 条）
  - `daily_flow_2026_apr` — 4 月明细（~31,000+ 条，单位：元）
  - `ningxia_orders_2026_apr` — 宁夏订单明细

### 数据单位
- **明细表**: `amount` 原始单位是**元**
- **汇总表**: `daily_total_flow` 单位是**万元**
- Excel 表头写"万元"但实际是"元"，导入需 ÷10000

---

## 🏥 医院数据

### 宁夏医院
- `ningxia_orders_2026_apr`: 4 月 1-7 日 19,230 条，¥673,811.44
- 开方医生：杨锦亮（100%）
- 宣传后用户增长 +278%（3.24-31 → 4.1-6）

---

## 📚 GitHub

- **仓库**: https://github.com/15857182453/wechat_fetch
- **代码**: Dashboard + 导入脚本 + 分析工具

---

## 🔧 技能

1. self-improving-agent-cn — 自我改进
2. data-analysis — 数据分析
3. rupert-data-analysis — 数据分析（定制）

---

## 📝 记忆蒸馏

每两天执行一次，读取最近 7 天 `memory/*.md`，蒸馏到本文件。

---

**维护者**: OpenClaw 🐾
