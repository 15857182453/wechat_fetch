# 🏪 金佰川鞋业运营数据看板 v1.0

> **技术栈**: Streamlit + PostgreSQL 16 + Plotly + Playwright  
> **部署**: WSL2/Linux 本地，ngrok 内网穿透  
> **访问**: http://localhost:8502  
> **公网**: https://clobber-backspace-catcall.ngrok-free.dev (ngrok 动态)

---

## 📦 项目文件清单

| 文件 | 用途 |
|------|------|
| `dashboard_jbc.py` | 主看板应用（Streamlit, ~680行, 12个Tab） |
| `auth_jbc.py` | 多用户认证系统（SQLite, 角色权限, 门店/品牌过滤） |
| `import_jbc.py` | 标准化数据导入脚本（扫描→识别→预览→去重导入→验证） |
| `init_jbc_db.sql` | 数据库初始化（12表 + 3物化视图 + 17索引） |
| `alert_checker.py` | 预警检查脚本（库存/退货率/日销骤降暴增） |
| `verify_dashboard.py` | Playwright 自动化验证（登录+12Tab截图+异常检测） |
| `test_concurrency.py` | 并发压力测试（模拟多用户同时访问） |
| `jbc_users.db` | 用户数据库（SQLite, dashboard_users表） |

---

## 🗄️ 数据库设计

**数据库**: PostgreSQL 16 `jinbaichuan`  
**连接池**: psycopg2 ThreadedConnectionPool (min=2, max=20)

### 表结构 (13张表)

| 表名 | 类型 | 行数 | 说明 |
|------|------|------|------|
| `sales_detail` | 分区表(按月) | 279,988 | 交易明细，14列 |
| `sales_daily` | 普通表 | 1,634 | 日汇总透视表 |
| `inventory_snapshot` | 普通表 | 104 | 库存快照（品牌×地点） |
| `dim_store` | 维度表 | 54 | 门店维度 |
| `dim_brand` | 维度表 | 109 | 品牌维度 |
| `dim_dept` | 维度表 | 9 | 品类维度 |
| `prod_launch` | 维度表 | 189 | 商品上市时间 |
| `alert_rules` | 规则表 | 4 | 预警规则配置 |
| `alert_log` | 日志表 | - | 预警历史记录 |
| `metrics_registry` | 元数据 | 20 | 指标注册表 |
| `mv_brand_daily` | 物化视图 | 3,038 | 品牌×日×品类聚合 |
| `mv_store_daily` | 物化视图 | 1,640 | 门店×日聚合 |
| `mv_dept_daily` | 物化视图 | 277 | 品类×日聚合 |

### 索引策略 (17个)

- 主力查询: `(submit_date, store_name, brand_name)`, `(submit_date, dept_name)`, `(brand_name, submit_date)`
- 单据追溯: `(doc_no)` UNIQUE
- 商品追踪: `(mnemonic)` 部分索引 WHERE NOT NULL
- 范围扫描: BRIN 索引（千万行仅占几MB）
- 实时监控: `(submit_date, hour)`
- 退款分析: `(submit_date, is_return)` 部分索引

---

## 🔐 用户权限系统

### 角色体系

| 角色 | 权限 |
|------|------|
| `admin` | 全部数据 + 用户管理 + 数据导入 |
| `editor` | 全部数据 + 数据导入 |
| `viewer` | 仅授权门店/品牌的数据 |

### 数据过滤机制

- `allowed_stores`: JSON数组，指定可访问门店，null=全部
- `allowed_brands`: JSON数组，指定可访问品牌，null=全部
- `hidden_tabs`: JSON数组，隐藏指定Tab
- SQL层过滤: `build_store_filter()` → `AND store_name IN (...)`
- DataFrame层过滤: `filter_dataframe(df, store_col, brand_col)`

### 默认账号

| 用户名 | 密码 | 角色 | 权限范围 |
|--------|------|------|---------|
| admin | admin | 管理员 | 全部 |
| xibei | jbc2026 | 西北大区经理 | 5个门店 |

---

## 📊 12个看板标签页

### Tab 1: 📊 总览KPI
- **5个核心指标**: 销售额、毛利、订单数、件数、件单价
- **环形图**: 品类占比（9品类）
- **双轴图**: 日销售额柱状图 + 毛利率折线

### Tab 2: 📈 趋势分析
- 4维度切换: 门店/品牌/品类/时段
- Top N 滑块（5-30）
- 时段分布: 高峰15:00-16:00（12.2%/11.6%）

### Tab 3: ⚠️ 业务预警
- **库存告急**: 紧急(<30天) / 偏低(30-60天) / 正常(>60天)
- **退货率监控**: 日退货额 + 退货率折线 + 5%警戒线
- **日销波动**: Top10 变异系数（识别不稳定门店）
- **预警日志**: 最近20条预警记录

### Tab 4: 🏆 排行榜
- 5维度: 门店/品牌/品类/单品/营业员
- 3指标切换: 销售额/毛利/订单数
- 水平柱状图 Top20

### Tab 5: 🔍 多维下钻
- 路径1: 品牌→门店→商品明细
- 路径2: 品类→品牌分布(Treemap)

### Tab 6: 📉 月度环比
- 日销售额柱状图
- 环比分析（需2个月以上数据激活）

### Tab 7: 🏪 门店分析
- 任选门店查看: KPI卡片 + 日趋势 + 品类结构(饼图) + Top10品牌(柱状图)

### Tab 8: 🏷️ 品牌分析
- 品牌总览: 109品牌，Top10占比46.7%
- 品牌排行 + 毛利率热力色
- 品牌日趋势对比（多选，最多5个）

### Tab 9: 📦 商品分析
- **爆款排行**: 过滤脏数据（排除门店名/联营/租赁/折扣率标签）
- **新品追踪**: JOIN prod_launch 表，上市商品×实际销售
- **库存分析**: 品牌×门店可售天数，颜色标记（🔴<30 🟡30-60 🟢>60）

### Tab 10: 🔔 实时预警
- 一键运行预警检查（库存告急/退货率异常/日销骤降/暴增）
- 4条预设规则 + 去重机制（同规则+同门店+同天只一次）
- 预警历史列表

### Tab 11: 👥 用户管理
- 仅admin可见
- 查看/禁用/新增用户
- 配置门店授权、隐藏Tab

### Tab 12: 📋 数据导入
- 数据库状态总览（6张表行数）
- 一键刷新物化视图
- 重新导入按钮

---

## 📥 数据导入标准化流程

```
扫描目录 → 识别文件类型 → 预览报告 → 确认 → 导入(ON CONFLICT去重) → 刷新维度 → 刷新物化视图 → 验证
```

### 命令

```bash
# 预览（不导入）
python3 import_jbc.py --dry-run

# 交互确认后导入
python3 import_jbc.py

# 跳过确认直接导入
python3 import_jbc.py --yes
```

### 支持的文件类型

| 文件名关键词 | 目标表 | 去重策略 |
|------------|--------|---------|
| `流水号` | sales_detail | ON CONFLICT (doc_no, product_name, submit_time) |
| `每日` | sales_daily | ON CONFLICT (store_name, sale_date) DO UPDATE |
| `库存` | inventory_snapshot | ON CONFLICT (brand_name, location, snapshot_date) DO UPDATE |
| `上市` | prod_launch | 全量刷新(小表) |

---

## 🔔 预警系统

### 4条预设规则

| 规则 | 条件 | 阈值 | 说明 |
|------|------|------|------|
| 库存告急 | stock_days < 30 | 30天 | 门店×品牌可售天数 |
| 退货率异常 | return_rate > 5 | 5% | 昨日退货/销售额 |
| 日销骤降 | change < -50 | -50% | 同比上周同日 |
| 日销暴增 | change > 200 | 200% | 同比上周同日 |

### 运行方式

```bash
python3 alert_checker.py           # 手动执行
# 或通过 Dashboard Tab10 点击按钮
```

---

## ✅ 自动化验证

```bash
python3 verify_dashboard.py
```

Playwright 自动化：
1. 打开浏览器 → 登录页截图
2. admin/admin 登录 → 登录成功截图
3. 逐个点击12个Tab → 截图 + Streamlit异常检测
4. 汇总通过/失败

---

## 🔬 并发测试

```bash
python3 test_concurrency.py
```

| 并发数 | 成功率 | 适用场景 |
|--------|--------|---------|
| 1人 | 100% | 个人使用 |
| 5人 | ~40-80% | 小团队 |
| 10人+ | 不稳定 | 需升级架构 |

> Streamlit 单进程限制，5-10人团队够用。

---

## 🚀 启动 & 管理

```bash
# 启动看板
tmux new-session -d -s jbc "streamlit run dashboard_jbc.py --server.port 8502 --server.headless true"

# 查看日志
tail -f /tmp/jbc_dashboard.log

# 停止
tmux kill-session -t jbc

# 内网穿透
ngrok http 8502            # 公网分享
pkill ngrok                # 关闭穿透

# 预警定时检查（每30分钟）
*/30 * * * * python3 /home/openclaw/.openclaw/workspace/alert_checker.py
```

---

## ⚙️ Streamlit 配置

`~/.streamlit/config.toml`:
```toml
[server]
maxUploadSize = 200
maxMessageSize = 200
enableCORS = true
headless = true

[browser]
gatherUsageStats = false
```

---

## 📊 核心业务数据（5月）

| 指标 | 数值 |
|------|------|
| 月销售额 | ¥3,013万 |
| 月毛利 | ¥1,250万 (41.5%) |
| 订单数 | 166,027 |
| 销售件数 | 379,630 |
| 客单价 | ¥181.5 |
| 连带率 | 2.3件/单 |
| 退货率 | 2.2% |
| 门店 | 54家 |
| 品牌 | 109个 |
| 品类 | 9个 |
| 营业员 | 672人 |

---

## ⚠️ 已知限制

- 数据库采用 `pd.read_sql_query` + 原生 psycopg2（非SQLAlchemy），有 UserWarning（不影响功能）
- 日期筛选使用自定义模板引擎 `_template()` + f-string 混合模式
- 仅5月数据，同比/环比功能需后续月份数据

---

**版本**: v1.0  
**日期**: 2026-06-02  
**作者**: OpenClaw AI + 人工协作
