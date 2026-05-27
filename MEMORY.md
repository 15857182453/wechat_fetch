# 🧠 长期记忆

**创建日期**: 2026-04-08  
**最后更新**: 2026-05-27

---

## 🔑 永久规则（最高优先级）

### 文件路径
- **Windows**: `C:\Users\44238\Desktop\业务对账数据\`
- **Linux 挂载**: `/mnt/c/Users/44238/Desktop/业务对账数据/`
- 子文件夹: `3-月/`、`4-月/`、`4-1/`、`4-2/`... 按日期分
- 用户发 Windows 路径 → 自动转 `/mnt/c/...` 直接读取
- **不要问用户文件在哪**，自己去 `/mnt/c/` 或 `/mnt/e/` 找

### 每日导入流程
1. 扫描 `/mnt/e/办公资料/业务对账数据/` 找最新明细文件
2. `cp` 到工作区
3. 识别文件类型：
   - **明细表**（54列）：交易明细 → `daily_flow_2026_*.py` 增量导入
   - **汇总表**（28列）：`新流水2026.xlsx` → `duizhang_summary_2026`（UPSERT）
4. **导入前识别业务日期**：报告日期分布和金额，用户确认后再导入
5. 增量导入（**绝不删表！**）
6. 更新汇总表
7. 重启 Dashboard + 刷新预聚合表

### 🚫 血的教训
1. ❌ 绝对不要 `DELETE FROM` 清表（4/9 犯过错，丢了 4/1-7 数据）
2. ❌ 不要问用户文件在哪，自己去 `/mnt/c/` 或 `/mnt/e/` 找
3. ❌ 启动会话必须先读 memory 文件
4. ❌ SQL 双聚合陷阱：UNION ALL 子查询内层返回原始行（`1 as cnt, amount as amt`），聚合只在外层做一次
5. ❌ 不要跑 dashboard_v3.py，始终用 v4
6. ❌ OpenCode 不适合生成完整 Python 文件（缩进错误），适合代码审查/重构
7. ❌ Plotly Y 轴用 `title_font` 不是 `titlefont`（下划线分隔）
8. ❌ SQLite 查询用独立 conn/cursor，不要用已关闭的连接
9. ❌ pd.to_datetime() 后才能用 .dt accessor
10. ⚠️ 汇总表 Excel 是 3 行复杂表头（标题行 + 业务大类行 + 流水/订单子列行），读取时需 `skiprows=4`。c23=日总流水(万元)，业务流水列(c1-c22)单位是**元**需÷10000
11. ❌ 订单数统计必须过滤退款，加 `pay_status='收费'` 条件
12. ❌ 月环比计算排除未来/空数据，`WHERE date < date('now') AND daily_total_flow > 0`
13. ❌ 医院名称必须精确匹配（青岛中心医院≠青岛市中医医院海慈医院）
14. ❌ 汇总表 c24（日总流水）已经是万元，不要 ÷10000！（5/20 踩坑）
15. ❌ 明细表列名问题：数据库明细表**只有英文列名**（`yewu_wancheng_shijian` 等），没有中文列。`refresh_prescription_summary.py` 的 SQL 中 `COALESCE(NULLIF(TRIM(yewu_wancheng_shijian),''), NULLIF(TRIM("业务完成时间"),''))` 会因 `"业务完成时间"` 列不存在被 SQLite 当作字符串字面量回退！根因修复：移除中文列名引用，改用纯英文列 + `LIKE '____-__-__%'` 格式校验
16. ❌ 绝对不要直接修改原始文档！必须先备份再操作！（5/12 踩坑）
17. ⚠️ 定期校验汇总表与 Excel 源文件一致性，DB 可能落后于更新过的 Excel（5/18 踩坑）
18. ⚠️ 汇总表列索引澄清（skiprows=4 后）：c23(列索引23)=日总流水(元)、c24(列索引24)=日总流水(万元)。业务流水列(c1-c22)单位是元需÷10000。c24已经是万元不要÷10000。
19. ❌ Claude 可能误删数据库/改代码，导入前务必确认数据状态！5/21 因此丢了 3.6 万条明细
20. ❌ `trans_no`（交易流水号）是大整数，SQLite INTEGER 会溢出，必须用 TEXT 存储（5/11 踩坑）

### Dashboard 版本
- **活跃**: `dashboard_v4.py`（3021 行，11 个 tab，已加登录守卫 auth_guard.py）
- **禅道看板**: `app_v2.py`（端口 8503）
- **重启**: `tmux kill-session -t dashboard` → `streamlit run dashboard_v4.py --server.port 8501 --server.headless true`
- **内网穿透**: ngrok 可用（`ngrok http 8501`）；cpolar 曾有配置文件但二进制未安装
- **安全**: `auth_guard.py` 登录守卫，Dashboard(8501) 和禅道(8503) 均需认证，密码：`admin`
- **git 版本**: `76a113c` (master)，仓库: https://github.com/15857182453/wechat_fetch
- **11 个 tab**: 总览分析 / 趋势洞察 / 异常监控 / 医院排行 / 月度环比 / 便捷配药数据统计 / 每日运营快报 / 本周总结 / 第三方服务分析 / 用户行为分析

### 预聚合表
- **表名**: `prescription_summary`（yr, institution, cnt, amt, avg_amt, dt）
- **用途**: 70x 查询加速（0.85s → 0.012s），替代 Dashboard 每次启动的全表扫描
- **刷新脚本**: `refresh_prescription_summary.py`（全量 ~1s / 增量 ~0.05s）
- **每次导入明细数据后必须刷新**
- ⚠️ 异常 dt='业务完成时间' 曾混入 23 行，根因已在 `refresh_prescription_summary.py` 修复（移除中文列名引用 + 格式校验），Dashboard 保留正则防御性过滤

---

## 📊 核心业务

### 医院数据 Dashboard（v4）
- **文件**: `/home/openclaw/.openclaw/workspace/dashboard_v4.py`
- **访问**: http://localhost:8501
- **10 个标签页**:
  1. 📊 总览分析 — KPI + 医院详情
  2. 📈 趋势洞察 — 近 7 天订单/金额
  3. ⚠️ 异常监控 — 4 种算法
  4. 🏆 医院排行 — Top 10 + 近 7 天
  5. 📉 月度环比 — 动态计算（排除空数据）
  6. 💊 便捷配药 — 8 张机构趋势图
  7. 📋 运营快报 — 每日运营概览
  8. 📊 本周总结
  9. 🔗 第三方服务分析
  10. 📊 用户行为分析 — fenxiti.com API

### 数据源
- **汇总表** `新流水2026.xlsx`（28列）：权威数据源
- **明细表** `业务对账统计明细-*.xlsx`（54列）：交易明细

### 数据单位（⚠️ 容易踩坑）
- **明细表**: `amount` 原始单位是**元**
- **汇总表** (skiprows=4 后): c23=日总流水(元)、c24=日总流水(万元)
- 业务流水列(c1-c22)单位是**元**，需 ÷10000
- ⚠️ 汇总表 c24 列已经是**万元**，不要 ÷10000！

### 明细表列名（⚠️ 关键！）
- **Excel 源文件**：使用中文列名（`业务完成时间`、`业绩类目`、`订单金额`、`机构名称`、`收退标识`）
- **数据库明细表**：只有英文列名（`yewu_wancheng_shijian`、`ye_wu_lei_mu`、`amount`、`institution`、`pay_status`）
- **导入脚本**：负责将 Excel 中文列映射到英文列
- **查询注意事项**：直接查询数据库时**只使用英文列名**。`COALESCE` 中英文列名回退是错误的——因为中文列不存在，SQLite 会将其当作字符串字面量返回！（5/22 根因修复：`refresh_prescription_summary.py` 已移除所有中文列名引用）

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
- **汇总导入流程**: 读 Excel → c24 已经是万元（直接读，不要 ÷10000）→ UPSERT → 清理异常 → 验证
- **文件路径**: E 盘路径 `/mnt/e/办公资料/业务对账数据/` 也可用，不要只认 C 盘

### 数据库
- **路径**: `/home/openclaw/.openclaw/workspace/business_flow.db`
- **主要表**:
  - `duizhang_summary_2026` — 每日汇总（万元），152 条，最新有数据 5/25（31.52万），5/26-6/1 为 0 占位
  - `duizhang_summary_2025` — 2025 全年（365 条）
  - `daily_flow_2026_may` — 5 月明细（99,261 条，¥448.41万，含第三方分账）
  - `daily_flow_2026_apr` — 4 月明细（91,549 条，¥500.48万）
  - `daily_flow_2026_mar` — 3 月明细（235,843 条，¥780.63万）
  - `daily_flow_2026_jan` — 1 月明细（69,634 条，¥492.38万）
  - `daily_flow_2026_feb` — 2 月明细（54,177 条，¥344.47万）
  - ⚠️ `daily_flow_2026_jan_feb` / `jan_feb_old` / `jan_old` / `feb_old` / `mar_old` 为旧版备份表，查询时排除
  - `prescription_summary` — 预聚合表（11,814 行）
  - `ningxia_orders_2026_apr` — 宁夏订单
  - `community_orders` — 社群订单（216,339 条，57 字段）
  - **注意**: 汇总表 5/21 日总流水 44.91 万 > 明细表同日 ~34 万（差额 ~10.8 万），因汇总表是纳里系统全量统计，可能包含明细未覆盖的记录
  - **注意**: 明细表中部分记录 `yewu_wancheng_shijian` 为 NULL（~17,000 条），预聚合查询已用 `LIKE '____-__-__%'` 格式校验过滤

### 💊 便捷配药机构（8 家）
- **常规 4 家**: 浙江省中医院（湖滨院区）、杭州师范大学附属医院、青岛中心医院、宁夏医科大学总医院
- **新增 4 家**: 齐鲁德医、齐鲁第二医院、安徽省立医院、青岛中心
- **样式**: 蓝色标题条 + HTML 转置透视表 + 近 15 天折线图
- **汇总卡片**: 2026 年累计数据（订单总数/总流水）
- **订单过滤**: 必须加 `pay_status='收费'` 排除退款

### 自动检查与修复 (auto_audit_repair.py v2)
- **脚本**: `auto_audit_repair.py`
- **运行频率**: 每半月一次（1日/15日 22:00）或手动触发
- **检查项**: 数据库全表脏数据 → 汇总表 vs Excel 一致性 → 当月完整性 → 预聚合表 → Dashboard 代码
- **修复项**: 脏表重新导入 → 汇总表缺失日期补全 → 分类流水补充 → 预聚合表刷新 → Dashboard 重启
- **特性**: 递归文件发现、动态月份映射、Excel"总计"行过滤、修复后验证、日志轮转（5000行）

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
- ⚠️ 宁夏明细数据缺失：所有月份明细表中无宁夏记录（需用户提供源文件导入）

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

### 禅道质量看板
- **文件**: `app_v2.py`（端口 8503）
- 研发质量指标按版本计算
- 数据源：`E:\办公资料\1研发中心质控部基础数据\需求表\`
- 质量健康指数公式已调优（缺陷密度基准 5.0、延期率系数 300、激活率系数 200）

### 内网穿透
- **ngrok**: 可用（`ngrok http 8501`）
- cpolar: 配置文件存在但二进制未安装

### 第三方 API
- **fenxiti.com（分析体）**: Token=`fvoaF0c7BPS5va8Ijxd9T_jsiZU`, spaceId=`aYMlRm4x`
- Dashboard Tab 11 使用其 API 做用户行为分析（医院专属月报模式）
- **数据刷新**: `fetch_fenxiti_data.py` 拉取 4 个事件分析图表 → 4 个 JSON 文件
  - 4月核心: `GMJJWkMP` → `data_fenxiti_monthly_4.json` (66行)
  - 5月核心: `Dp2jw0pJ` → `data_fenxiti_monthly_5.json` (65行)
  - 4月药方: `DpBqejMk` → `data_fenxiti_rx_4.json` (1204行, 15列含最小起定量)
  - 5月药方: `Y4YEJj4m` → `data_fenxiti_rx_5.json` (1195行, 13列无最小起定量)
  - ⚠️ rx_4 和 rx_5 列结构不同，Tab 11 用 resultHeader 动态匹配列名

## 🔧 模型配置
- **默认模型**: bailian/qwen3.6-plus（已删除 deepseek provider）
- 配置文件: `~/.openclaw/agents/main/agent/models.json` 和 `~/.openclaw/openclaw.json`
- **已删除的 provider**: deepseek（无可用 key/模型不可用）
- **可用 provider**: bailian, codex, qwen, modelstudio, xiaomi

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
