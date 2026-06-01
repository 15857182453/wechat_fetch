# 金佰川鞋业数据看板 — 设计文档

> **日期**: 2026-06-01  
> **状态**: 待审核  
> **版本**: v1.0

---

## 1. 项目概述

### 1.1 目标
为金佰川鞋业公司构建运营数据分析看板，支持销售数据、库存数据、门店流水的多维度分析与实时监控。

### 1.2 业务背景
- **公司**: 金佰川（鞋业零售连锁）
- **规模**: 54 家门店，109 个品牌，9 个品类
- **当前数据量**: 5 月 ~28 万笔交易，月销额 ¥5891 万
- **预期增长**: 日增数十万行，累积千万级

### 1.3 用户角色
| 角色 | 权限 | 典型用户 |
|------|------|---------|
| `admin` | 全部数据 + 用户管理 | 系统管理员 |
| `editor` | 全部数据 + 导入权限 | 数据运营 |
| `viewer` | 按配置限制数据可见范围 | 大区经理/品牌经理/领导 |

---

## 2. 数据源

### 2.1 当前文件
| 文件 | 大小 | 行数 | 列数 | 内容 |
|------|------|------|------|------|
| `5月流水号销售.xlsx` | 55MB | 279,989 | 11 | 交易明细：仓店、单据、营业员、品类、品牌、商品、数量、金额、毛利、时间 |
| `5月每日销售.xlsx` | 16MB | 62 | 34 | 日汇总透视表：54门店 × 31天，值=销额(元) |
| `童鞋上市时间.xlsx` | 18KB | 191 | 7 | 商品上市参考：品类、品牌、年份、季节、商品、上市日期 |

### 2.2 字段映射（交易明细）

| Excel 列名 | 数据库列名 | 类型 | 说明 |
|-----------|-----------|------|------|
| 仓店全称 | store_name | VARCHAR(100) | 54 家门店 |
| 单据编号 | doc_no | VARCHAR(50) | 唯一交易号 |
| 营业员名称 | salesperson | VARCHAR(50) | |
| 部组名称 | dept_name | VARCHAR(30) | 9 个品类 |
| 品牌名称 | brand_name | VARCHAR(60) | 109 个品牌 |
| 商品名称 | product_name | VARCHAR(200) | |
| 助记码 | mnemonic | VARCHAR(50) | ~5700 NULL |
| 销售数量 | quantity | INTEGER | |
| 结算金额 | settle_amount | NUMERIC(12,2) | 单位：元 |
| 毛利 | gross_profit | NUMERIC(12,2) | 单位：元 |
| 单据提交时间 | submit_time | TIMESTAMP | |

### 2.3 已知数据问题
- **金额差异**: 交易明细月总额 ¥5891 万 vs 每日销售透视表月总额 ¥2945 万，差额约 50%，待确认原因（可能是净额 vs 原价，或含退款）
- **助记码空值**: 约 5,700 行 (~2%)
- **每日销售表结构**: 为 Excel 透视表，非规范数据格式，需转置后入库

---

## 3. 技术架构

### 3.1 技术栈
```
前端:      Streamlit (Python) — 复用医院看板经验
数据库:    PostgreSQL 16 — 千万级数据性能保障
认证:      auth_system.py — 已有架构，SQLite 存储用户
可视化:    Plotly — 交互式图表
数据处理:  pandas + psycopg2
部署:      WSL/Linux 本地，tmux 管理进程
```

### 3.2 架构图
```
用户浏览器 :8502
    ↓
Streamlit Dashboard (dashboard_jbc.py)
    ├── auth_system.py (用户认证 → SQLite)
    ├── db_utils.py (PostgreSQL 连接池)
    └── 12 个 Tab 模块
    ↓
┌──────────────────────────────┐
│ PostgreSQL (业务数据)         │
│ ├── sales_detail (分区表)     │
│ ├── sales_daily (日汇总)      │
│ ├── mv_* (物化视图)           │
│ ├── dim_* (维度表)            │
│ └── alert_* (预警)            │
├──────────────────────────────┤
│ SQLite (用户数据)              │
│ └── dashboard_users           │
└──────────────────────────────┘
```

---

## 4. 数据库设计

### 4.1 交易明细表（核心大表，按月分区）

```sql
CREATE TABLE sales_detail (
    id              BIGSERIAL,
    store_name      VARCHAR(100) NOT NULL,
    doc_no          VARCHAR(50)  NOT NULL,
    salesperson     VARCHAR(50),
    dept_name       VARCHAR(30)  NOT NULL,
    brand_name      VARCHAR(60)  NOT NULL,
    product_name    VARCHAR(200) NOT NULL,
    mnemonic        VARCHAR(50),
    quantity        INTEGER      NOT NULL,
    settle_amount   NUMERIC(12,2) NOT NULL,
    gross_profit    NUMERIC(12,2) NOT NULL,
    submit_time     TIMESTAMP    NOT NULL,
    submit_date     DATE         NOT NULL,
    hour            SMALLINT     NOT NULL,
    created_at      TIMESTAMP    DEFAULT NOW()
) PARTITION BY RANGE (submit_date);

-- 分区示例
CREATE TABLE sales_detail_2026_05 
    PARTITION OF sales_detail 
    FOR VALUES FROM ('2026-05-01') TO ('2026-06-01');
```

**索引策略**:
```sql
-- 高频查询: 日期+门店+品牌
CREATE INDEX idx_sd_date_store_brand ON sales_detail (submit_date, store_name, brand_name);
-- 品类下钻
CREATE INDEX idx_sd_date_dept ON sales_detail (submit_date, dept_name);
-- 单据追溯
CREATE INDEX idx_sd_doc_no ON sales_detail (doc_no);
-- 品牌趋势
CREATE INDEX idx_sd_brand_date ON sales_detail (brand_name, submit_date);
-- BRIN 范围扫描（千万行仅占几MB）
CREATE INDEX idx_sd_date_brin ON sales_detail USING BRIN (submit_date) WITH (pages_per_range=32);
-- 实时监控
CREATE INDEX idx_sd_hour ON sales_detail (submit_date, hour);
```

### 4.2 日汇总表

```sql
CREATE TABLE sales_daily (
    id            SERIAL PRIMARY KEY,
    store_name    VARCHAR(100) NOT NULL,
    sale_date     DATE NOT NULL,
    total_amount  NUMERIC(14,2) NOT NULL,
    total_profit  NUMERIC(14,2),
    order_count   INTEGER,
    item_count    INTEGER,
    dept_json     JSONB,
    brand_json    JSONB,
    UNIQUE (store_name, sale_date)
);
CREATE INDEX idx_sdly_date ON sales_daily (sale_date);
```

### 4.3 维度表

```sql
CREATE TABLE dim_store (
    store_name  VARCHAR(100) PRIMARY KEY,
    region      VARCHAR(50),
    city        VARCHAR(30),
    store_type  VARCHAR(20),
    is_active   BOOLEAN DEFAULT TRUE
);

CREATE TABLE dim_brand (
    brand_name  VARCHAR(60) PRIMARY KEY,
    brand_type  VARCHAR(30),    -- 自有/联营/经销/租赁
    dept_main   VARCHAR(30)
);

CREATE TABLE dim_dept (
    dept_name   VARCHAR(30) PRIMARY KEY,
    sort_order  SMALLINT
);

CREATE TABLE prod_launch (
    id            SERIAL PRIMARY KEY,
    dept_name     VARCHAR(30),
    brand_name    VARCHAR(60),
    launch_year   SMALLINT,
    season        VARCHAR(10),
    product_name  VARCHAR(200),
    mnemonic      VARCHAR(50),
    launch_date   DATE
);
```

### 4.4 物化视图（Dashboard 加速）

```sql
CREATE MATERIALIZED VIEW mv_brand_daily AS
SELECT submit_date, brand_name, dept_name,
    COUNT(DISTINCT doc_no) AS order_cnt,
    SUM(quantity) AS total_qty,
    SUM(settle_amount) AS total_amt,
    SUM(gross_profit) AS total_profit,
    COUNT(DISTINCT store_name) AS store_cnt
FROM sales_detail
GROUP BY submit_date, brand_name, dept_name;

CREATE UNIQUE INDEX idx_mv_brand_daily ON mv_brand_daily (submit_date, brand_name, dept_name);

CREATE MATERIALIZED VIEW mv_store_daily AS
SELECT submit_date, store_name,
    COUNT(DISTINCT doc_no) AS order_cnt,
    SUM(quantity) AS total_qty,
    SUM(settle_amount) AS total_amt,
    SUM(gross_profit) AS total_profit
FROM sales_detail
GROUP BY submit_date, store_name;

CREATE UNIQUE INDEX idx_mv_store_daily ON mv_store_daily (submit_date, store_name);
```

### 4.5 预警表

```sql
CREATE TABLE alert_rules (
    id            SERIAL PRIMARY KEY,
    rule_name     VARCHAR(100) NOT NULL,
    metric        VARCHAR(50) NOT NULL,
    dimension     VARCHAR(50),
    condition     VARCHAR(20) NOT NULL,
    threshold     NUMERIC(12,2) NOT NULL,
    compare_period VARCHAR(20) DEFAULT '1_day',
    is_enabled    BOOLEAN DEFAULT TRUE
);

CREATE TABLE alert_log (
    id              SERIAL PRIMARY KEY,
    rule_id         INTEGER REFERENCES alert_rules(id),
    alert_time      TIMESTAMP DEFAULT NOW(),
    metric_value    NUMERIC(12,2),
    threshold_value NUMERIC(12,2),
    description     TEXT,
    is_read         BOOLEAN DEFAULT FALSE
);
```

### 4.6 用户表（SQLite，复用现有架构）

```sql
-- 沿用 auth_system.py 中的 dashboard_users 表结构
CREATE TABLE dashboard_users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'viewer',
    display_name TEXT,
    allowed_institutions TEXT,   -- JSON array: ["门店A","门店B"] 或品牌
    hidden_tabs TEXT,            -- JSON array: ["Tab名称1"]
    created_at TEXT DEFAULT (datetime('now')),
    is_active INTEGER DEFAULT 1
);
```

---

## 5. Dashboard Tab 结构（12 个）

| # | Tab | 功能 | 数据源 |
|---|-----|------|--------|
| 1 | 📊 总览 KPI | 月销额/毛利/利润率/订单数，同比环比，门店在线数 | mv_store_daily + sales_daily |
| 2 | 📈 趋势分析 | 日销售额趋势线，可切门店/品牌/品类维度 | sales_detail + mv_brand_daily |
| 3 | ⚠️ 异常监控 | Z-Score/IQR/环比暴增/骤降，4种算法 | mv_store_daily |
| 4 | 🏆 排行榜 | Top N 门店/品牌/品类/单品，可切换 | sales_detail + mv_brand_daily |
| 5 | 🔍 多维下钻 | 品牌→门店→商品，逐层穿透 | sales_detail |
| 6 | 📉 月度环比 | 按门店/品牌环比变化，热力图 | mv_store_daily |
| 7 | 🏪 门店分析 | 单门店详情，日趋势 | sales_detail |
| 8 | 🏷️ 品牌分析 | 品牌表现矩阵，自有 vs 联营 vs 经销 | sales_detail + dim_brand |
| 9 | 📦 商品分析 | 新品上市追踪，爆款/滞销识别 | sales_detail + prod_launch |
| 10 | 🔔 实时预警 | 预警规则配置 + 预警历史 | alert_rules + alert_log |
| 11 | 👥 用户管理 | admin可见，增删改用户/权限配置 | dashboard_users (SQLite) |
| 12 | 📋 数据导入 | 导入新月份数据，刷新物化视图 | - |

---

## 6. 复用架构

### 6.1 直接复用
- **auth_system.py**: 整体复用，仅需将 `institution` → `store_name` 参数化
- **CSS 主题**: 医院看板 v6 的 custom_css 直接复用
- **Plotly 图表主题**: CHART_LAYOUT 配色方案复用
- **Sparkline 组件**: make_sparkline() 函数直接复用

### 6.2 适配修改
- `build_institution_filter()` → 改为 `build_store_filter()` 或参数化
- `filter_dataframe()` → `institution_column` 默认值改为 `store_name`
- SQLite DB_PATH → `business_flow.db` 仅存用户表，业务数据走 PG

### 6.3 新增
- `db_pg.py` — PostgreSQL 连接管理模块
- `import_jbc.py` — 数据导入脚本（Excel → PostgreSQL）
- `refresh_mv.py` — 物化视图刷新脚本
- `alert_checker.py` — 预警检查定时脚本

---

## 7. 关键设计决策

| 决策 | 选择 | 原因 |
|------|------|------|
| 数据库 | PostgreSQL | 千万级性能 + 分区表 + BRIN + 物化视图 |
| 用户存储 | SQLite | 用户表 < 100 行，不需迁移 |
| 前端 | Streamlit | 复用经验，开发快 |
| 认证 | SHA-256 + session_state | 内部系统够用，复用现有架构 |
| 金额单位 | 统一存"元" | 展示时按需转"万元" |
| 分区策略 | 按月 RANGE | 查询模式以月为单位，方便数据管理 |
| 预聚合 | 物化视图 | 日汇总查询从 ~2s 降到 ~10ms |

---

## 8. 待确认事项
1. ✅ 技术栈选型（Streamlit + PostgreSQL）
2. ⚠️ 交易明细 ¥5891万 vs 日汇总 ¥2945万 差额原因 — 导入前确认
3. ⚠️ 是否需要退款/退货过滤逻辑（类似医院看板的 `pay_status='收费'`）
4. ⚠️ 门店大区/城市映射表 — 需从业务方获取或从现有数据推断
5. ⚠️ 后续数据文件交付频率（每日？每周？每月？）
