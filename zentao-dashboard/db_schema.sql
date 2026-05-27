-- ============================================================
-- 禅道质量看板数据库 Schema
-- 引擎: SQLite 3
-- 数据源: 研发中心质控部基础数据 (Excel 导出)
-- ============================================================

PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;

-- ============================================================
-- 1. 版本表
-- ============================================================
CREATE TABLE IF NOT EXISTS version (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    version_code  TEXT UNIQUE NOT NULL,      -- 如 2026-1-V1
    version_name  TEXT,                       -- 如 2026-1-V1版本（0112）
    release_date  TEXT,                       -- 发版日期 YYYY-MM-DD
    version_type  TEXT,                       -- 常规版/需求紧急版/bug紧急版/个性化版本
    project_id    INTEGER,                    -- 禅道项目ID
    source_file   TEXT,                       -- 原始Excel文件名
    imported_at   TEXT DEFAULT (datetime('now', 'localtime'))
);

-- ============================================================
-- 2. 需求表
-- 1:1 映射 Excel "需求跟踪矩阵" sheet 的 38 列
-- ============================================================
CREATE TABLE IF NOT EXISTS requirement (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    version_id        INTEGER REFERENCES version(id) ON DELETE CASCADE,

    -- 版本标识 (col 0-4)
    yuedu             TEXT,                   -- 月度 (Excel序列号)
    zhoushu           TEXT,                   -- 周数
    banben_name       TEXT,                   -- 版本名称
    leixing           TEXT,                   -- 类型
    project_id_raw    INTEGER,                -- 项目ID

    -- 组织信息 (col 5-7)
    dept_level1       TEXT,                   -- 一级部门
    dept_level2       TEXT,                   -- 二级部门
    business_module   TEXT,                   -- 所属业务模块

    -- 需求核心 (col 8-18)
    req_type          TEXT,                   -- 需求类型
    req_status        TEXT,                   -- 需求状态
    product_manager   TEXT,                   -- 产品经理
    req_id            TEXT,                   -- 需求ID (禅道)
    bug_id            TEXT,                   -- bugID/反馈ID
    priority          TEXT,                   -- 优先级: P0/P1/P2/P3
    project_rating    TEXT,                   -- 项目需求评级
    is_third_party    TEXT,                   -- 是否对接第三方
    is_customized     TEXT,                   -- 是否为个性化
    is_disputed       TEXT,                   -- 是否为争议
    req_title         TEXT,                   -- 需求名称

    -- 时间节点 (col 19-22, 28, 31)
    req_submit_time   TEXT,                   -- 需求提交时间
    developer         TEXT,                   -- 对应研发
    tester            TEXT,                   -- 对应测试
    test_submit_time  TEXT,                   -- 提测时间
    assign_time       TEXT,                   -- 被指派时间
    release_time      TEXT,                   -- 发版完成时间

    -- 验收 (col 23-27)
    acceptance_result TEXT,                   -- 验收是否通过
    accept_fail_type  TEXT,                   -- 未通过分类
    accept_fail_reason TEXT,                  -- 未通过原因
    is_delayed_test   TEXT,                   -- 是否延期提测
    remark            TEXT,                   -- 备注

    -- 效率指标 (col 29-30)
    response_days     REAL,                   -- 响应时长 (天)
    consumed_hours    REAL,                   -- 消耗工时

    -- 禅道反馈关联 (col 32-36)
    org_name          TEXT,                   -- 机构名称
    region            TEXT,                   -- 大区
    sub_region        TEXT,                   -- 分区
    feedback_priority TEXT,                   -- 反馈优先级
    feedback_time     TEXT,                   -- 反馈创建时间

    created_at        TEXT DEFAULT (datetime('now', 'localtime'))
);

-- ============================================================
-- 3. Bug表
-- 1:1 映射 Excel "原始bug-193" sheet 的 40 列
-- ============================================================
CREATE TABLE IF NOT EXISTS bug (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    version_id        INTEGER REFERENCES version(id) ON DELETE CASCADE,

    -- 测试信息 (col 0-1)
    test_stage        TEXT,                   -- 测试阶段
    bug_id            INTEGER,                -- Bug编号

    -- 禅道层级 (col 2-4)
    product           TEXT,                   -- 所属产品
    module_path       TEXT,                   -- 所属模块
    project_name      TEXT,                   -- 所属项目

    -- 关联 (col 5-6)
    related_req       TEXT,                   -- 相关需求
    related_task      TEXT,                   -- 相关任务

    -- Bug核心 (col 7-11)
    bug_title         TEXT,                   -- Bug标题
    severity          INTEGER,                -- 严重程度: 1/2/3/4
    bug_priority      INTEGER,                -- 优先级: 1/2/3/4
    bug_type          TEXT,                   -- Bug类型

    -- 环境 (col 12-13, 全空但保留)
    os                TEXT,                   -- 操作系统
    browser           TEXT,                   -- 浏览器

    -- 状态流转
    bug_status        TEXT,                   -- Bug状态
    deadline          TEXT,                   -- 截止日期
    activate_count    INTEGER,                -- 激活次数
    is_confirmed      TEXT,                   -- 是否确认
    assignee          TEXT,                   -- 指派给
    assign_date       TEXT,                   -- 指派日期

    -- 解决
    resolver          TEXT,                   -- 解决者
    solution          TEXT,                   -- 解决方案
    resolve_version   TEXT,                   -- 解决版本
    resolve_date      TEXT,                   -- 解决日期

    -- 关闭
    closer            TEXT,                   -- 由谁关闭
    close_date        TEXT,                   -- 关闭日期

    -- 关联 (保留)
    duplicate_id      TEXT,                   -- 重复ID
    related_bug       TEXT,                   -- 相关Bug
    related_case      TEXT,                   -- 相关用例

    -- 审计
    creator           TEXT,                   -- 由谁创建
    create_time       TEXT,                   -- 创建日期
    last_modifier     TEXT,                   -- 最后修改者
    modify_time       TEXT,                   -- 修改日期

    -- 其他
    keywords          TEXT,                   -- 关键词
    cc_to             TEXT,                   -- 抄送给
    impact_version    TEXT,                   -- 影响版本
    has_attachment    INTEGER,                -- 附件 (0/1)

    -- 组织
    role              TEXT,                   -- 所属岗位
    dept_level2_bug   TEXT,                   -- 所属二级部门
    dept_level1_bug   TEXT,                   -- 所属一级部门
    business_line     TEXT,                   -- 所属业务线

    created_at        TEXT DEFAULT (datetime('now', 'localtime'))
);

-- ============================================================
-- 4. 人员表
-- ============================================================
CREATE TABLE IF NOT EXISTS staff (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    name          TEXT,
    dept_level1   TEXT,
    dept_level2   TEXT,
    business_line TEXT,
    role          TEXT,                   -- 岗位
    source_file   TEXT,
    created_at    TEXT DEFAULT (datetime('now', 'localtime'))
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_staff_name ON staff(name);

-- ============================================================
-- 5. 导入审计表
-- ============================================================
CREATE TABLE IF NOT EXISTS import_audit (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    version_code  TEXT,
    source_type   TEXT,                   -- requirement/bug/staff
    source_file   TEXT,
    import_status TEXT,                   -- success/partial/failed
    total_rows    INTEGER,
    success_rows  INTEGER,
    skipped_rows  INTEGER,
    failed_rows   INTEGER,
    error_details TEXT,
    started_at    TEXT,
    completed_at  TEXT
);

CREATE INDEX IF NOT EXISTS idx_audit_version ON import_audit(version_code);

-- ============================================================
-- 索引 (只建实际查询会用到的)
-- ============================================================

-- requirement 索引
CREATE INDEX IF NOT EXISTS idx_req_version ON requirement(version_id);
CREATE INDEX IF NOT EXISTS idx_req_version_status ON requirement(version_id, req_status);
CREATE INDEX IF NOT EXISTS idx_req_version_type ON requirement(version_id, req_type);
CREATE INDEX IF NOT EXISTS idx_req_developer ON requirement(version_id, developer);
CREATE INDEX IF NOT EXISTS idx_req_dept ON requirement(version_id, dept_level1, dept_level2);
CREATE INDEX IF NOT EXISTS idx_req_product_mgr ON requirement(version_id, product_manager);
CREATE INDEX IF NOT EXISTS idx_req_req_id ON requirement(req_id);

-- bug 索引
CREATE INDEX IF NOT EXISTS idx_bug_version ON bug(version_id);
CREATE INDEX IF NOT EXISTS idx_bug_version_severity ON bug(version_id, severity);
CREATE INDEX IF NOT EXISTS idx_bug_version_status ON bug(version_id, bug_status);
CREATE INDEX IF NOT EXISTS idx_bug_resolver ON bug(version_id, resolver);
CREATE INDEX IF NOT EXISTS idx_bug_assignee ON bug(version_id, assignee);
CREATE INDEX IF NOT EXISTS idx_bug_dept ON bug(version_id, dept_level1_bug, dept_level2_bug);
CREATE INDEX IF NOT EXISTS idx_bug_test_stage ON bug(version_id, test_stage);
CREATE INDEX IF NOT EXISTS idx_bug_bug_id ON bug(bug_id);

-- ============================================================
-- 视图 (只建真正有用的)
-- ============================================================

-- 1. 版本统计
CREATE VIEW IF NOT EXISTS v_version_summary AS
SELECT
    v.version_code,
    v.version_name,
    v.release_date,
    v.version_type,
    COUNT(DISTINCT r.id) AS req_count,
    COUNT(DISTINCT CASE WHEN r.req_status != '原始' THEN r.id END) AS active_req_count,
    COUNT(DISTINCT b.id) AS bug_count,
    COALESCE(ROUND(SUM(r.consumed_hours), 1), 0) AS total_hours,
    CASE WHEN COUNT(DISTINCT r.id) > 0
        THEN ROUND(COUNT(DISTINCT b.id) * 1.0 / COUNT(DISTINCT r.id), 2)
        ELSE 0 END AS bugs_per_req
FROM version v
LEFT JOIN requirement r ON v.id = r.version_id
LEFT JOIN bug b ON v.id = b.version_id
GROUP BY v.id;

-- 2. 人员工作量
CREATE VIEW IF NOT EXISTS v_staff_workload AS
SELECT
    r.developer AS person,
    r.version_id,
    v.version_code,
    COUNT(DISTINCT r.id) AS req_count,
    COALESCE(ROUND(SUM(r.consumed_hours), 1), 0) AS req_hours,
    COALESCE(b2.bug_count, 0) AS bug_count
FROM requirement r
JOIN version v ON r.version_id = v.id
LEFT JOIN (
    SELECT resolver, version_id, COUNT(*) AS bug_count
    FROM bug
    WHERE resolver IS NOT NULL AND resolver != '' AND resolver != '已知问题延期处理'
    GROUP BY resolver, version_id
) b2 ON r.developer = b2.resolver AND r.version_id = b2.version_id
WHERE r.developer IS NOT NULL AND r.developer != '' AND r.developer != '/'
GROUP BY r.developer, r.version_id;

-- 3. 需求状态分布
CREATE VIEW IF NOT EXISTS v_req_status_distribution AS
SELECT
    v.version_code,
    r.dept_level1,
    r.req_type,
    r.req_status,
    COUNT(*) AS req_count
FROM requirement r
JOIN version v ON r.version_id = v.id
GROUP BY v.version_code, r.dept_level1, r.req_type, r.req_status;

-- 4. Bug质量分析 (按解决者)
CREATE VIEW IF NOT EXISTS v_bug_quality AS
SELECT
    v.version_code,
    b.resolver,
    COUNT(*) AS total_bugs,
    SUM(CASE WHEN b.activate_count > 0 THEN 1 ELSE 0 END) AS reopened_count,
    SUM(CASE WHEN b.solution IN ('重复Bug', 'Duplicate') THEN 1 ELSE 0 END) AS duplicate_count,
    SUM(CASE WHEN b.solution = '已解决' THEN 1 ELSE 0 END) AS resolved_count,
    ROUND(AVG(b.severity * 1.0), 2) AS avg_severity
FROM bug b
JOIN version v ON b.version_id = v.id
WHERE b.resolver IS NOT NULL AND b.resolver != '' AND b.resolver != '已知问题延期处理'
GROUP BY v.version_code, b.resolver;

-- 5. 需求响应时间分析
CREATE VIEW IF NOT EXISTS v_req_response_time AS
SELECT
    v.version_code,
    r.developer,
    ROUND(AVG(r.response_days), 1) AS avg_response_days,
    ROUND(MAX(r.response_days), 1) AS max_response_days,
    ROUND(AVG(r.consumed_hours), 1) AS avg_hours
FROM requirement r
JOIN version v ON r.version_id = v.id
WHERE r.response_days IS NOT NULL AND r.response_days > 0
GROUP BY v.version_code, r.developer;
