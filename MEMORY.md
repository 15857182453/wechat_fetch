# 🧠 长期记忆

**创建日期**: 2026-04-08  
**最后更新**: 2026-04-16

---

## 🔑 永久规则（最高优先级）

### 文件路径
- **Windows**: `C:\Users\44238\Desktop\业务对账数据\`
- **Linux 挂载**: `/mnt/c/Users/44238/Desktop/业务对账数据/`
- 子文件夹: `3-月/`、`4-月/`、`4-1/`、`4-2/`... 按日期分
- 用户发 Windows 路径 → 自动转 `/mnt/c/...` 直接读取
- **不要问用户文件在哪**，自己去 `/mnt/c/` 找

### 每日导入流程
1. 扫描 `/mnt/c/.../业务对账数据/` 找最新 `业务对账统计明细-*.xlsx`
2. `cp` 到工作区
3. 识别文件类型：
   - **明细表**（54列）：交易明细 → `daily_flow_2026_apr`（增量 INSERT）
   - **汇总表**（28列）：`新流水2026.xlsx` → `duizhang_summary_2026`（INSERT OR REPLACE）
4. **导入前识别业务日期**：先读取文件内部"业务完成时间"字段，报告日期分布和金额，用户确认后再导入
5. 增量导入（**绝不删表！**）
6. 更新汇总表
7. 重启 Dashboard

### 🚫 血的教训
1. ❌ 绝对不要 `DELETE FROM` 清表（4/9 犯过错，丢了 4/1-7 数据）
2. ❌ 不要问用户文件在哪，自己去 `/mnt/c/` 找
3. ❌ 启动会话必须先读 memory 文件
4. ❌ SQL 双聚合陷阱：UNION ALL 子查询内层返回原始行（`1 as cnt, amount as amt`），聚合只在外层做一次
5. ❌ 不要跑 dashboard_v3.py，始终用 v4
6. ❌ OpenCode 不适合生成完整 Python 文件（缩进错误），适合代码审查/重构
7. ❌ Plotly Y 轴用 `title_font` 不是 `titlefont`（下划线分隔）
8. ❌ SQLite 查询用独立 conn/cursor，不要用已关闭的连接
9. ❌ pd.to_datetime() 后才能用 .dt accessor
10. ⚠️ 汇总表 Excel 列映射可能变化，导入前需验证列结构
11. ❌ 订单数统计必须过滤退款，加 `pay_status='收费'` 条件
12. ❌ 月环比计算排除未来/空数据，`WHERE date < date('now') AND daily_total_flow > 0`
13. ❌ 医院名称必须精确匹配（青岛中心医院≠青岛市中医医院海慈医院）

### Dashboard 版本
- **活跃**: `dashboard_v4.py`
- **重启**: `tmux kill-session -t dashboard` → `streamlit run dashboard_v4.py`

---

## 📊 核心业务

### 医院数据 Dashboard（v4）
- **文件**: `/home/openclaw/.openclaw/workspace/dashboard_v4.py`
- **访问**: http://localhost:8501
- **9 个标签页**:
  1. 📊 总览 — KPI + 医院详情
  2. 📈 趋势 — 近 7 天订单/金额
  3. ⚠️ 异常监控 — 4 种算法
  4. 🏆 排行 — Top 10 + 近 7 天
  5. 🗺️ 区域分布 — 省份地图
  6. 📉 月环比 — 动态计算（排除空数据）
  7. 👤 患者地域分布 — 饼图 TOP10
  8. 💊 便捷配药 — 8 张机构趋势图（4 常规 + 4 新增）
  9. 📋 运营快报 — 每日运营概览（流水/订单/类目/省份/退款）

### 数据源
- **汇总表** `新流水2026.xlsx`（28列）：权威数据源
- **明细表** `业务对账统计明细-*.xlsx`（54列）：交易明细

### 数据单位（⚠️ 容易踩坑）
- **明细表**: `amount` 原始单位是**元**
- **汇总表**: `daily_total_flow` 单位是**万元**
- Excel 表头写"万元"但实际是"元"，导入需 ÷10000

### 数据加载逻辑
1. 优先从明细表 UNION ALL 获取数据
2. 检查缺失日期
3. 仅查询缺失日期从汇总表补充（非全表扫描）
4. 单位统一为元

### 月环比计算逻辑
- 排除未来/空数据：`WHERE date < date('now') AND daily_total_flow > 0`
- 锁定到昨天，对比上月同期

### 异常检测算法（4 种）
1. **Z-Score**: |Z| > 2.0（排除今日计算均值）
2. **IQR**: 当前值 > Q3 + 1.5×IQR
3. **动态阈值**: min(中位数×1.3, 均值+1.5×标准差)
4. **环比暴增**: 前一日≥10 单 且 增长>200%

### 数据导入
- **健壮版脚本**: `import_duizhang_robust.py` — 自动检测单位、数据验证、去重
- **明细导入**: `import_detail_*.py`

### 数据库
- **路径**: `/home/openclaw/.openclaw/workspace/business_flow.db`
- **主要表**:
  - `duizhang_summary_2026` — 每日汇总（万元），最新 4/16
  - `duizhang_summary_2025` — 2025 全年（365 条）
  - `daily_flow_2026_apr` — 4 月明细（51,313+ 条，元）
  - `daily_flow_2026_mar` — 3 月明细（186,939 条）
  - `daily_flow_2026_jan_feb` — 1-2 月明细（42,885 条）
  - `ningxia_orders_2026_apr` — 宁夏订单（20,670 条）
  - `community_orders` — 社群订单（216,339 条，57 字段）

### 💊 便捷配药机构（8 家）
- **常规 4 家**: 浙江省中医院（湖滨院区）、杭州师范大学附属医院、青岛中心医院、宁夏医科大学总医院
- **新增 4 家**: 齐鲁德医、齐鲁第二医院、安徽省立医院、青岛中心
- **样式**: 蓝色标题条 + HTML 转置透视表 + 近 15 天折线图
- **汇总卡片**: 2026 年累计数据（订单总数/总流水）
- **订单过滤**: 必须加 `pay_status='收费'` 排除退款

### 自动化导出
- **脚本**: `auto_export_ngari_win.py`（Windows 本地运行）
- **依赖**: Playwright + Chromium
- **首次**: 手动登录完成验证，保存 Cookie
- **之后**: 自动登录，只需选择日期、点击导出

### 数据维度（约 100+ 个字段）
- **明细表**: institution, province, pay_status, ye_wu_lei_mu, yewu_leixing, oper_person, pay_method
- **汇总表**: 11 个业务类型流水 + 日总流水 + 环比
- **宁夏订单**: 57 个字段（患者、处方、物流完整信息）

---

## 🏥 宁夏医院数据（历史参考）
- `ningxia_orders_2026_apr`: 4 月 1-7 日 19,230 条，¥673,811.44
- 开方医生：杨锦亮（100%）
- 宣传后用户增长 +278%（3.24-31 → 4.1-7）
- TOP5 增长省份：宁夏(+337%)、内蒙古(+741%)、陕西(+454%)、甘肃(+758%)、新疆(+490%)

---

## 📚 GitHub
- **仓库**: https://github.com/15857182453/wechat_fetch
- **Dashboard**: `/hospital-dashboard/` 独立文件夹
- **代码**: Dashboard + 导入脚本 + 分析工具 + 文档

---

## 🔧 技能
1. self-improving-agent-cn — 自我改进
2. data-analysis — 数据分析

---

## 🔧 模型配置
- **当前模型**: qwen/qwen3.6-plus（默认）
- **Provider**: qwen:default（有 API key）
- 配置文件: `~/.openclaw/agents/main/agent/models.json`

### 🔐 纳里健康 API
- **网站**: https://yypt.ngarihealth.com
- **账号**: zly_yyzx
- **AES 密钥**: ms4gxansxo459uom（ECB 模式）
- **API**: `/ehealth-opbase/openapi/gateway`
- **导出方法**: `exportFinanceBillOrderExcel`
- **自动化脚本**: `auto_export_ngari_win.py`（Windows 本地运行）
- **Cookie 文件**: `cookies.json`（保存登录状态）

---

## 📝 记忆蒸馏
每两天执行一次，读取最近 7 天 `memory/*.md`，蒸馏到本文件。

---

**维护者**: OpenClaw 🐾
