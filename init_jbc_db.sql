-- ============================================================
-- 金佰川鞋业数据看板 — 数据库初始化
-- Database: jinbaichuan
-- 指标覆盖: 10大类 32个指标
-- ============================================================

-- ============================================================
-- 1. 交易明细表（核心大表，按月分区）
-- ============================================================
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
    is_return       BOOLEAN      DEFAULT FALSE,   -- 退款标记 (settle_amount<0)
    created_at      TIMESTAMP    DEFAULT NOW()
) PARTITION BY RANGE (submit_date);

-- 分区
CREATE TABLE sales_detail_2026_05 PARTITION OF sales_detail
    FOR VALUES FROM ('2026-05-01') TO ('2026-06-01');
CREATE TABLE sales_detail_2026_06 PARTITION OF sales_detail
    FOR VALUES FROM ('2026-06-01') TO ('2026-07-01');
CREATE TABLE sales_detail_2026_07 PARTITION OF sales_detail
    FOR VALUES FROM ('2026-07-01') TO ('2026-08-01');

-- 索引: 主力查询
CREATE INDEX idx_sd_date_store   ON sales_detail (submit_date, store_name);
CREATE INDEX idx_sd_date_brand   ON sales_detail (submit_date, brand_name);
CREATE INDEX idx_sd_date_dept    ON sales_detail (submit_date, dept_name);
CREATE INDEX idx_sd_doc_no       ON sales_detail (doc_no);
CREATE INDEX idx_sd_brand_date   ON sales_detail (brand_name, submit_date);
CREATE INDEX idx_sd_product      ON sales_detail (product_name);
CREATE INDEX idx_sd_salesperson  ON sales_detail (salesperson) WHERE salesperson IS NOT NULL;
CREATE INDEX idx_sd_mnemonic     ON sales_detail (mnemonic) WHERE mnemonic IS NOT NULL;
CREATE INDEX idx_sd_hour         ON sales_detail (submit_date, hour);
CREATE INDEX idx_sd_return       ON sales_detail (submit_date, is_return) WHERE is_return = TRUE;
-- BRIN: 千万行仅占几MB
CREATE INDEX idx_sd_date_brin    ON sales_detail USING BRIN (submit_date) WITH (pages_per_range = 32);

-- ============================================================
-- 2. 日汇总表（来自 Excel 透视表）
-- ============================================================
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
    created_at    TIMESTAMP DEFAULT NOW(),
    UNIQUE (store_name, sale_date)
);
CREATE INDEX idx_sdly_date  ON sales_daily (sale_date);
CREATE INDEX idx_sdly_store ON sales_daily (store_name);

-- ============================================================
-- 3. 库存快照表
-- ============================================================
CREATE TABLE inventory_snapshot (
    id            SERIAL PRIMARY KEY,
    brand_name    VARCHAR(60) NOT NULL,
    location      VARCHAR(100) NOT NULL,
    stock_qty     INTEGER NOT NULL,
    snapshot_date DATE DEFAULT CURRENT_DATE,
    UNIQUE (brand_name, location, snapshot_date)
);
CREATE INDEX idx_inv_brand    ON inventory_snapshot (brand_name);
CREATE INDEX idx_inv_location ON inventory_snapshot (location);
CREATE INDEX idx_inv_date     ON inventory_snapshot (snapshot_date);

-- ============================================================
-- 4. 维度表
-- ============================================================
CREATE TABLE dim_store (
    store_name    VARCHAR(100) PRIMARY KEY,
    region        VARCHAR(50),
    city          VARCHAR(30),
    store_type    VARCHAR(20) DEFAULT 'store',  -- store/warehouse
    is_active     BOOLEAN DEFAULT TRUE
);

CREATE TABLE dim_brand (
    brand_name    VARCHAR(60) PRIMARY KEY,
    brand_type    VARCHAR(30),    -- 自有/联营/经销/租赁 (待业务确认)
    dept_main     VARCHAR(30)
);

CREATE TABLE dim_dept (
    dept_name     VARCHAR(30) PRIMARY KEY,
    sort_order    SMALLINT DEFAULT 0
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
CREATE INDEX idx_pl_brand ON prod_launch (brand_name);
CREATE INDEX idx_pl_date  ON prod_launch (launch_date);

-- ============================================================
-- 5. 物化视图（Dashboard 性能核心）
-- ============================================================
-- 品牌×日×品类
CREATE MATERIALIZED VIEW mv_brand_daily AS
SELECT submit_date, brand_name, dept_name,
    COUNT(DISTINCT doc_no) AS order_cnt,
    SUM(quantity)          AS total_qty,
    SUM(settle_amount)     AS total_amt,
    SUM(gross_profit)      AS total_profit,
    COUNT(DISTINCT store_name) AS store_cnt
FROM sales_detail
WHERE NOT is_return
GROUP BY submit_date, brand_name, dept_name;
CREATE UNIQUE INDEX idx_mv_brand_daily ON mv_brand_daily (submit_date, brand_name, dept_name);

-- 门店×日
CREATE MATERIALIZED VIEW mv_store_daily AS
SELECT submit_date, store_name,
    COUNT(DISTINCT doc_no) AS order_cnt,
    SUM(quantity)          AS total_qty,
    SUM(settle_amount)     AS total_amt,
    SUM(gross_profit)      AS total_profit
FROM sales_detail
WHERE NOT is_return
GROUP BY submit_date, store_name;
CREATE UNIQUE INDEX idx_mv_store_daily ON mv_store_daily (submit_date, store_name);

-- 品类×日
CREATE MATERIALIZED VIEW mv_dept_daily AS
SELECT submit_date, dept_name,
    COUNT(DISTINCT doc_no) AS order_cnt,
    SUM(quantity)          AS total_qty,
    SUM(settle_amount)     AS total_amt,
    SUM(gross_profit)      AS total_profit,
    COUNT(DISTINCT store_name) AS store_cnt
FROM sales_detail
WHERE NOT is_return
GROUP BY submit_date, dept_name;
CREATE UNIQUE INDEX idx_mv_dept_daily ON mv_dept_daily (submit_date, dept_name);

-- ============================================================
-- 6. 预警表
-- ============================================================
CREATE TABLE alert_rules (
    id              SERIAL PRIMARY KEY,
    rule_name       VARCHAR(100) NOT NULL,
    metric          VARCHAR(50) NOT NULL,
    dimension       VARCHAR(50),
    condition       VARCHAR(20) NOT NULL,
    threshold       NUMERIC(12,2) NOT NULL,
    compare_period  VARCHAR(20) DEFAULT '1_day',
    is_enabled      BOOLEAN DEFAULT TRUE,
    created_at      TIMESTAMP DEFAULT NOW()
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
CREATE INDEX idx_alert_time ON alert_log (alert_time);
CREATE INDEX idx_alert_read ON alert_log (is_read);

-- ============================================================
-- 7. 指标注册表（为后期扩展预留）
-- ============================================================
CREATE TABLE metrics_registry (
    id            SERIAL PRIMARY KEY,
    metric_key    VARCHAR(50) UNIQUE NOT NULL,
    metric_name   VARCHAR(100) NOT NULL,
    unit          VARCHAR(20) DEFAULT '元',
    category      VARCHAR(30) DEFAULT 'sales',
    is_active     BOOLEAN DEFAULT TRUE,
    sort_order    SMALLINT DEFAULT 0
);

-- 预置指标
INSERT INTO metrics_registry (metric_key, metric_name, unit, category, sort_order) VALUES
('daily_sales',       '日销售额',     '元',   'sales',      1),
('daily_profit',      '日毛利',       '元',   'profit',     2),
('profit_rate',       '毛利率',       '%',    'profit',     3),
('order_count',       '订单数',       '单',   'sales',      4),
('total_qty',         '销售件数',     '件',   'sales',      5),
('avg_order_value',   '客单价',       '元',   'efficiency', 6),
('items_per_order',   '连带率',       '件/单','efficiency', 7),
('avg_item_price',    '件单价',       '元',   'efficiency', 8),
('store_count',       '活跃门店数',   '家',   'store',      9),
('sales_per_store',   '店均销售',     '元',   'store',     10),
('return_rate',       '退货率',       '%',    'quality',   11),
('return_amount',     '退货金额',     '元',   'quality',   12),
('top10_ratio',       'Top10品牌集中度','%',  'brand',     13),
('weekend_ratio',     '周末/工作日比','倍',   'time',      14),
('peak_hour',         '销售高峰时段', '时',   'time',      15),
('brand_count',       '活跃品牌数',   '个',   'brand',     16),
('sku_count',         'SKU数',       '个',   'product',   17),
('stock_days',        '库存可售天数', '天',   'inventory', 18),
('sell_through',      '售罄率',       '%',    'inventory', 19),
('mom_change',        '环比变化',     '%',    'sales',     20);
