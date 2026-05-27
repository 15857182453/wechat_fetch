"""
禅道质量看板 - Streamlit 主应用
"""

import sqlite3
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st

DB_PATH = Path(__file__).parent / "data" / "zentao.db"

st.set_page_config(
    page_title="禅道质量看板",
    page_icon="📊",
    layout="wide",
)

st.markdown("""
<style>
    .metric-card { background: #1E1E2E; padding: 1.2rem; border-radius: 10px; }
    div[data-testid="stMetricValue"] { font-size: 2rem !important; }
</style>
""", unsafe_allow_html=True)


@st.cache_data(ttl=3600)
def load_all_data():
    """加载所有数据"""
    if not DB_PATH.exists():
        return None, None, None, None
    conn = sqlite3.connect(str(DB_PATH))
    versions = pd.read_sql("SELECT * FROM version ORDER BY version_code", conn)
    reqs = pd.read_sql("SELECT * FROM requirement", conn)
    bugs = pd.read_sql("SELECT * FROM bug", conn)
    staff = pd.read_sql("SELECT * FROM staff", conn)
    conn.close()
    return versions, reqs, bugs, staff


# ════════════════════════════════════════════
# 主界面
# ════════════════════════════════════════════

st.title("📊 禅道质量看板")
st.markdown("---")

versions, reqs, bugs, staff = load_all_data()

if reqs is None or reqs.empty:
    st.warning(
        "⚠️ 数据库为空或不存在。请先导入数据：\n\n"
        "```bash\n"
        "# 导入单个文件\n"
        "python scripts/import_data.py <文件.xlsx>\n\n"
        "# 批量导入整个目录\n"
        "python scripts/import_data.py --dir <目录路径>\n"
        "```"
    )
    st.stop()

# ── 侧边栏筛选 ──
st.sidebar.header("🔍 筛选条件")

# 版本筛选 - 默认选最新版本
version_list = ['全部'] + sorted(versions['version_code'].unique().tolist())
latest_version = version_list[-1] if len(version_list) > 1 else '全部'
sel_version_list = st.sidebar.selectbox(
    "版本",
    version_list,
    index=version_list.index(latest_version),
    key="zentao_version_filter",
    help="查看特定版本数据，默认显示最新版本"
)
sel_version = [sel_version_list]  # 统一用 list 格式兼容下方逻辑
if '全部' not in sel_version:
    reqs = reqs[reqs['version_id'].isin(
        versions[versions['version_code'].isin(sel_version)]['id'].tolist()
    )]
    bugs = bugs[bugs['version_id'].isin(
        versions[versions['version_code'].isin(sel_version)]['id'].tolist()
    )]

# 部门筛选
if 'dept_level1' in reqs.columns:
    depts = ['全部'] + sorted(reqs['dept_level1'].dropna().unique().tolist())
    sel_dept = st.sidebar.multiselect("一级部门", depts, default=['全部'], key="zentao_dept_filter")
    if '全部' not in sel_dept:
        reqs = reqs[reqs['dept_level1'].isin(sel_dept)]

# 需求类型筛选
if 'req_type' in reqs.columns:
    req_types = ['全部'] + sorted(reqs['req_type'].dropna().unique().tolist())
    sel_req_type = st.sidebar.multiselect("需求类型", req_types, default=['全部'], key="zentao_type_filter")
    if '全部' not in sel_req_type:
        reqs = reqs[reqs['req_type'].isin(sel_req_type)]

st.sidebar.info(f"筛选后: **{len(reqs)}** 条需求, **{len(bugs)}** 条Bug")

# 重置筛选按钮
st.sidebar.divider()
if st.sidebar.button("🔄 重置所有筛选", type="secondary", use_container_width=True):
    st.session_state.zentao_version_filter = None
    st.session_state.zentao_dept_filter = None
    st.session_state.zentao_type_filter = None
    st.rerun()

# ════════════════════════════════════════════
# Tab 布局
# ════════════════════════════════════════════

tab_overview, tab_req, tab_bug, tab_staff, tab_compare, tab_metrics, tab_analysis = st.tabs([
    "📊 总览", "📋 需求", "🐛 Bug", "👥 人员", "📈 版本对比", "🎯 质量评分指标", "🔍 Bug 深度分析"
])

# ── Tab 1: 总览 ──
with tab_overview:
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("📋 需求总数", len(reqs))
    col2.metric("🐛 Bug总数", len(bugs))
    col3.metric("📁 版本数", len(versions))
    col4.metric("👥 人员数", len(staff) if staff is not None and not staff.empty else "—")

    st.markdown("---")

    # 版本统计
    st.subheader("📁 各版本概况")
    version_stats = []
    for _, v in versions.iterrows():
        vc = v['version_code']
        vn = v['version_name'] or ''
        n_req = len(reqs[reqs['version_id'] == v['id']]) if 'version_id' in reqs.columns else 0
        n_bug = len(bugs[bugs['version_id'] == v['id']]) if 'version_id' in bugs.columns else 0
        hours = reqs[reqs['version_id'] == v['id']]['consumed_hours'].sum() if 'version_id' in reqs.columns else 0
        version_stats.append({
            '版本': vc,
            '名称': vn,
            '需求数': n_req,
            'Bug数': n_bug,
            '消耗工时': round(hours, 1),
            'Bug/需求比': round(n_bug / n_req, 2) if n_req > 0 else 0,
        })
    st.dataframe(pd.DataFrame(version_stats), use_container_width=True, hide_index=True)

    st.markdown("---")

    # 需求状态分布
    if 'req_status' in reqs.columns:
        st.subheader("📊 需求状态分布")
        status_counts = reqs['req_status'].value_counts()
        st.bar_chart(status_counts, height=300, use_container_width=True, horizontal=True)

    # Bug严重程度分布
    if 'severity' in bugs.columns:
        st.subheader("📊 Bug严重程度分布")
        severity_counts = bugs['severity'].value_counts().sort_index()
        severity_labels = {1: '1级-致命', 2: '2级-严重', 3: '3级-一般', 4: '4级-轻微'}
        severity_counts.index = severity_counts.index.map(lambda x: severity_labels.get(x, f'{x}级'))
        st.bar_chart(severity_counts, height=300, use_container_width=True)

# ── Tab 2: 需求 ──
with tab_req:
    st.subheader("📋 需求明细")

    # 选择显示的列
    display_cols = []
    for col in ['req_id', 'req_title', 'req_type', 'req_status', 'priority',
                'product_manager', 'developer', 'tester', 'dept_level1',
                'business_module', 'consumed_hours', 'acceptance_result',
                'req_submit_time', 'release_time', 'remark']:
        if col in reqs.columns:
            display_cols.append(col)

    display_df = reqs[display_cols].copy()
    # 格式化日期列
    for col in ['req_submit_time', 'release_time', 'test_submit_time']:
        if col in display_df.columns:
            display_df[col] = pd.to_datetime(display_df[col], errors='coerce').dt.strftime('%Y-%m-%d')

    st.dataframe(display_df, use_container_width=True, height=600)

    # 导出
    st.download_button(
        label="📥 导出需求 (CSV)",
        data=display_df.to_csv(index=False).encode('utf-8-sig'),
        file_name=f"zentao_reqs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
        mime="text/csv",
    )

# ── Tab 3: Bug ──
with tab_bug:
    st.subheader("🐛 Bug明细")

    bug_display_cols = []
    for col in ['bug_id', 'bug_title', 'test_stage', 'severity', 'bug_type',
                'bug_status', 'solution', 'resolver', 'assignee',
                'module_path', 'product', 'activate_count',
                'create_time', 'resolve_date', 'close_date']:
        if col in bugs.columns:
            bug_display_cols.append(col)

    bug_df = bugs[bug_display_cols].copy()
    for col in ['create_time', 'resolve_date', 'close_date', 'assign_date']:
        if col in bug_df.columns:
            bug_df[col] = pd.to_datetime(bug_df[col], errors='coerce').dt.strftime('%Y-%m-%d %H:%M')

    st.dataframe(bug_df, use_container_width=True, height=600)

    # Bug质量分析
    if 'resolver' in bugs.columns and 'severity' in bugs.columns:
        st.markdown("---")
        st.subheader("📊 Bug质量分析 (按解决者)")
        quality = bugs[bugs['resolver'].notna() & (bugs['resolver'] != '') & (bugs['resolver'] != '已知问题延期处理')].copy()
        if not quality.empty:
            quality_stats = quality.groupby('resolver').agg(
                total_bugs=('bug_id', 'count'),
                reopened=('activate_count', lambda x: (x > 0).sum()),
                avg_severity=('severity', 'mean'),
            ).reset_index()
            quality_stats = quality_stats.sort_values('total_bugs', ascending=False)
            st.dataframe(quality_stats, use_container_width=True, hide_index=True)

# ── Tab 4: 人员 ──
with tab_staff:
    if staff is not None and not staff.empty:
        st.subheader("👥 人员信息")
        st.dataframe(staff[['name', 'dept_level1', 'dept_level2', 'business_line', 'role']],
                     use_container_width=True, hide_index=True)

        st.markdown("---")
        st.subheader("📊 人员工作量 Top 20")
        if 'developer' in reqs.columns and 'consumed_hours' in reqs.columns:
            workload = reqs[reqs['developer'].notna() & (reqs['developer'] != '') & (reqs['developer'] != '/')].copy()
            workload_stats = workload.groupby('developer').agg(
                req_count=('req_id', 'count'),
                total_hours=('consumed_hours', 'sum'),
                avg_hours=('consumed_hours', 'mean'),
            ).reset_index()
            workload_stats = workload_stats.sort_values('req_count', ascending=False).head(20)
            st.dataframe(workload_stats, use_container_width=True, hide_index=True)
            st.bar_chart(
                workload_stats.set_index('developer')[['req_count', 'total_hours']],
                height=400,
                use_container_width=True,
            )
    else:
        st.info("未导入人员数据。导入 Bug 文件时会自动提取人员资料表。")

# ── Tab 5: 研发质量指标 ──
with tab_metrics:
    st.subheader("🎯 研发质量指标")
    st.caption("所有指标按版本计算 | 数据来源: 研发中心质控部基础数据")

    # ════════════════════════════════════════════
    # 公式定义（折叠说明）
    # ════════════════════════════════════════════
    with st.expander("📐 查看指标计算公式"):
        st.markdown("""
| # | 指标 | 公式 |
|---|------|------|
| 1 | 交付需求数 | 需求类型∈{业务需求,开发优化,项目需求} 且 需求状态∈{原始,新增,(修改)} |
| 2 | 延期交付率 | 暂未计算 |
| 3 | 延期提测率 | COUNT(是否延期提测='是') / 交付需求数 |
| 4 | 需求交付周期 | response_days分档统计（单位：天） |
| 5 | 需求变更率 | COUNT(需求类型≠bug修复 且 需求状态≠原始) / 交付需求数 |
| 6 | 缺陷密度 | Bug总数 / 交付需求数 |
| 7 | 缺陷激活率 | SUM(activate_count) / Bug总数 |
| 8 | 缺陷逃逸率 | 暂未计算 |
        """)

    # ════════════════════════════════════════════
    # 按版本计算所有指标
    # ════════════════════════════════════════════
    VALID_REQ_TYPES = ['业务需求', '开发优化', '项目需求']
    DELIVERED_STATUSES = ['原始', '新增']

    metric_rows = []
    for _, v in versions.iterrows():
        vc = v['version_code']
        vid = v['id']
        v_reqs = reqs[reqs['version_id'] == vid]
        v_bugs = bugs[bugs['version_id'] == vid]

        # 1. 交付需求数
        v_delivered = v_reqs[
            v_reqs['req_type'].isin(VALID_REQ_TYPES) &
            v_reqs['req_status'].isin(DELIVERED_STATUSES)
        ]
        n_delivered = len(v_delivered)

        # 3. 延期提测率
        v_delayed_test = v_reqs[v_reqs['is_delayed_test'] == '是']
        n_delayed_test = len(v_delayed_test)
        delay_test_rate = round(n_delayed_test / n_delivered * 100, 1) if n_delivered > 0 else 0

        # 4. 需求交付周期 (response_days, 单位:天)
        v_resp = v_delivered[v_delivered['response_days'].notna() & (v_delivered['response_days'] > 0)]['response_days']
        if not v_resp.empty:
            avg_resp = round(v_resp.mean(), 1)
            b_lt15 = int((v_resp < 15).sum())
            b_1530 = int(((v_resp >= 15) & (v_resp < 30)).sum())
            b_3060 = int(((v_resp >= 30) & (v_resp < 60)).sum())
            b_6090 = int(((v_resp >= 60) & (v_resp < 90)).sum())
            b_gt90 = int((v_resp >= 90).sum())
        else:
            avg_resp = '—'
            b_lt15 = b_1530 = b_3060 = b_6090 = b_gt90 = 0

        # 5. 需求变更率: 需求类型≠bug修复 且 需求状态≠原始
        v_changed = v_reqs[
            (v_reqs['req_type'] != 'bug修复') &
            (v_reqs['req_status'] != '原始') &
            v_reqs['req_status'].notna()
        ]
        n_changed = len(v_changed)
        change_rate = round(n_changed / n_delivered * 100, 1) if n_delivered > 0 else 0

        # 6. 缺陷密度
        n_bugs = len(v_bugs)
        bug_density = round(n_bugs / n_delivered, 2) if n_delivered > 0 else 0

        # 7. 缺陷激活率: SUM(activate_count) / Bug总数
        total_activate = int(v_bugs['activate_count'].sum()) if 'activate_count' in v_bugs.columns else 0
        activate_rate = round(total_activate / n_bugs * 100, 1) if n_bugs > 0 else 0

        metric_rows.append({
            'version_code': vc, 'n_delivered': n_delivered,
            'n_delayed_test': n_delayed_test, 'delay_test_rate': delay_test_rate,
            'avg_resp': avg_resp,
            'bucket_lt15': b_lt15, 'bucket_15_30': b_1530,
            'bucket_30_60': b_3060, 'bucket_60_90': b_6090, 'bucket_gt90': b_gt90,
            'n_changed': n_changed, 'change_rate': change_rate,
            'n_bugs': n_bugs, 'bug_density': bug_density,
            'total_activate': total_activate, 'activate_rate': activate_rate,
        })

    metrics_df = pd.DataFrame(metric_rows)

    # ════════════════════════════════════════════
    # 第一行: 需求侧指标
    # ════════════════════════════════════════════
    st.markdown("### 📋 需求侧指标")

    sel_ver = st.selectbox("选择版本", ['全部'] + sorted(metrics_df['version_code'].tolist()), index=0)

    if sel_ver == '全部':
        t_del = int(metrics_df['n_delivered'].sum())
        t_delayed = int(metrics_df['n_delayed_test'].sum())
        t_rate = round(t_delayed / t_del * 100, 1) if t_del > 0 else 0
        t_changed = int(metrics_df['n_changed'].sum())
        t_change = round(t_changed / t_del * 100, 1) if t_del > 0 else 0
        valid_r = metrics_df[metrics_df['avg_resp'] != '—']
        avg_all = round(valid_r['avg_resp'].mean(), 1) if not valid_r.empty else '—'
    else:
        row = metrics_df[metrics_df['version_code'] == sel_ver].iloc[0]
        t_del = int(row['n_delivered']); t_delayed = int(row['n_delayed_test'])
        t_rate = row['delay_test_rate']; t_changed = int(row['n_changed'])
        t_change = row['change_rate']; avg_all = row['avg_resp']

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("1. 交付需求数", t_del, sel_ver)
    c2.metric("3. 延期提测率", f"{t_rate}%", f"{t_delayed}/{t_del}", delta_color="inverse")
    c3.metric("4. 需求交付周期", f"{avg_all}天" if avg_all != '—' else '—', "响应时长均值")
    c4.metric("5. 需求变更率", f"{t_change}%", f"{t_changed}/{t_del}", delta_color="inverse")

    st.divider()

    # 交付周期分布 - 分档比例
    st.markdown("### 📊 需求交付周期分布")
    st.caption("按 response_days（天）分档统计，显示各区间占比")
    if sel_ver == '全部':
        blt = int(metrics_df['bucket_lt15'].sum()); b15 = int(metrics_df['bucket_15_30'].sum())
        b30 = int(metrics_df['bucket_30_60'].sum()); b60 = int(metrics_df['bucket_60_90'].sum())
        bgt = int(metrics_df['bucket_gt90'].sum())
        resp_total = blt + b15 + b30 + b60 + bgt
    else:
        blt = int(row['bucket_lt15']); b15 = int(row['bucket_15_30'])
        b30 = int(row['bucket_30_60']); b60 = int(row['bucket_60_90']); bgt = int(row['bucket_gt90'])
        resp_total = blt + b15 + b30 + b60 + bgt

    # 比例卡片
    p1, p2, p3, p4, p5 = st.columns(5)
    def pct(n, total): return round(n/total*100,1) if total > 0 else 0
    p1.metric("<15天", f"{pct(blt, resp_total)}%", f"{blt}条")
    p2.metric("15-30天", f"{pct(b15, resp_total)}%", f"{b15}条")
    p3.metric("30-60天", f"{pct(b30, resp_total)}%", f"{b30}条")
    p4.metric("60-90天", f"{pct(b60, resp_total)}%", f"{b60}条")
    p5.metric(">90天", f"{pct(bgt, resp_total)}%", f"{bgt}条")

    # 柱状图 + 比例标注
    resp_df = pd.DataFrame({
        '区间': ['<15天', '15-30天', '30-60天', '60-90天', '>90天'],
        '需求数': [blt, b15, b30, b60, bgt],
        '占比': [pct(blt, resp_total), pct(b15, resp_total), pct(b30, resp_total), pct(b60, resp_total), pct(bgt, resp_total)]
    }).set_index('区间')
    st.bar_chart(resp_df[['需求数']], height=300, use_container_width=True, color=['#3B82F6'])

    st.divider()

    # ════════════════════════════════════════════
    # 第二行: 缺陷侧指标
    # ════════════════════════════════════════════
    st.markdown("### 🐛 缺陷侧指标")

    if sel_ver == '全部':
        t_bugs = int(metrics_df['n_bugs'].sum())
        t_activate = int(metrics_df['total_activate'].sum())
        t_density = round(t_bugs / t_del, 2) if t_del > 0 else 0
        t_arate = round(t_activate / t_bugs * 100, 1) if t_bugs > 0 else 0
    else:
        t_bugs = int(row['n_bugs']); t_activate = int(row['total_activate'])
        t_density = row['bug_density']; t_arate = row['activate_rate']

    d1, d2, d3, d4 = st.columns(4)
    d1.metric("6. 缺陷密度", t_density, f"{t_bugs}Bug / {t_del}需求")
    d2.metric("7. 缺陷激活率", f"{t_arate}%", f"激活{t_activate}次 / {t_bugs}Bug", delta_color="inverse")
    d3.metric("2. 延期交付率", "—", "暂未计算", delta_color="off")
    d4.metric("8. 缺陷逃逸率", "—", "暂未计算", delta_color="off")

    st.divider()

    # ════════════════════════════════════════════
    # 各版本指标明细表
    # ════════════════════════════════════════════
    st.subheader("📋 各版本指标明细")
    disp = pd.DataFrame()
    disp['版本'] = metrics_df['version_code']
    disp['交付需求数'] = metrics_df['n_delivered']
    disp['延期提测数'] = metrics_df['n_delayed_test']
    disp['延期提测率'] = metrics_df['delay_test_rate'].astype(str) + '%'
    disp['交付周期(天)'] = metrics_df['avg_resp'].astype(str)
    disp['<15天'] = metrics_df['bucket_lt15']
    disp['15-30天'] = metrics_df['bucket_15_30']
    disp['30-60天'] = metrics_df['bucket_30_60']
    disp['60-90天'] = metrics_df['bucket_60_90']
    disp['>90天'] = metrics_df['bucket_gt90']
    disp['需求变更率'] = metrics_df['change_rate'].astype(str) + '%'
    disp['Bug总数'] = metrics_df['n_bugs']
    disp['缺陷密度'] = metrics_df['bug_density']
    disp['激活总次数'] = metrics_df['total_activate']
    disp['缺陷激活率'] = metrics_df['activate_rate'].astype(str) + '%'
    st.dataframe(disp, use_container_width=True, hide_index=True)

# ── Tab 6: 版本对比 ──
with tab_compare:
    st.subheader("📈 版本对比分析")
    st.caption("对比各版本的需求、Bug、工时等关键指标")

    if len(versions) >= 2:
        compare_data = []
        for _, v in versions.iterrows():
            vc = v['version_code']
            vn = v['version_name'] or ''
            v_reqs = reqs[reqs['version_id'] == v['id']] if 'version_id' in reqs.columns else pd.DataFrame()
            v_bugs = bugs[bugs['version_id'] == v['id']] if 'version_id' in bugs.columns else pd.DataFrame()

            n_req = len(v_reqs)
            n_bug = len(v_bugs)
            hours = v_reqs['consumed_hours'].sum() if 'consumed_hours' in v_reqs.columns else 0
            delayed = len(v_reqs[v_reqs['is_delayed_test'] == '是']) if 'is_delayed_test' in v_reqs.columns else 0
            delivered = len(v_reqs[v_reqs['release_time'].notna() & (v_reqs['release_time'] != '')]) if 'release_time' in v_reqs.columns else 0

            compare_data.append({
                '版本': vc,
                '名称': vn,
                '需求数': n_req,
                '交付数': delivered,
                'Bug数': n_bug,
                'Bug/需求比': round(n_bug / n_req, 2) if n_req > 0 else 0,
                '消耗工时': round(hours, 1),
                '延期提测': delayed,
            })
        st.dataframe(pd.DataFrame(compare_data), use_container_width=True, hide_index=True)

        st.divider()

        # 对比柱状图
        st.subheader("📊 版本指标对比")
        compare_df = pd.DataFrame(compare_data).set_index('版本')
        st.bar_chart(compare_df[['需求数', 'Bug数']], height=350, use_container_width=True)

        st.divider()

        # 版本趋势图
        st.subheader("📈 版本趋势")
        trend_fig_col1, trend_fig_col2 = st.columns(2)
        with trend_fig_col1:
            st.markdown("**需求数 & Bug数趋势**")
            st.bar_chart(compare_df[['需求数', 'Bug数']], height=300, use_container_width=True)
        with trend_fig_col2:
            st.markdown("**工时 & 交付数趋势**")
            st.bar_chart(compare_df[['消耗工时', '交付数']], height=300, use_container_width=True)

    else:
        st.info(f"当前只有 {len(versions)} 个版本数据，导入更多版本后可进行对比分析。")

# ── Tab 7: 深度分析 ──
with tab_analysis:
    # ════════════════════════════════════════════
    # 面板 1: 🏥 模块 Bug 热力图
    # ════════════════════════════════════════════
    st.subheader("🏥 模块 Bug 热力图")
    st.caption("识别 Bug 最密集的功能模块，定位质量重灾区")

    if 'module_path' in bugs.columns:
        # 提取模块名（去掉路径前缀和ID）
        bugs_mod = bugs.copy()
        bugs_mod['module_short'] = bugs_mod['module_path'].str.extract(r'/([^/]+)\(')[0]
        bugs_mod['module_short'] = bugs_mod['module_short'].fillna(bugs_mod['module_path'])

        col_a1, col_a2 = st.columns([1, 1])

        with col_a1:
            st.markdown("**📊 模块 Bug 分布 (Top 15)**")
            module_stats = bugs_mod.groupby('module_short').agg(
                total=('bug_id', 'count'),
                s1=('severity', lambda x: (x == 1).sum()),
                s2=('severity', lambda x: (x == 2).sum()),
                s3=('severity', lambda x: (x == 3).sum()),
                s4=('severity', lambda x: (x == 4).sum()),
            ).reset_index().sort_values('total', ascending=False).head(15)

            # 柱状图
            fig_mod = st.bar_chart(
                module_stats.set_index('module_short')[['total']],
                height=400, use_container_width=True
            )

        with col_a2:
            st.markdown("**📋 模块明细**")
            module_detail = module_stats.rename(columns={
                'module_short': '模块', 'total': 'Bug总数',
                's1': 'S1致命', 's2': 'S2严重', 's3': 'S3一般', 's4': 'S4轻微'
            })
            st.dataframe(module_detail, use_container_width=True, hide_index=True)

        st.divider()

        # 版本 × 模块热力表
        st.markdown("**🔥 版本 × 模块 Bug 矩阵**")
        if 'version_id' in bugs.columns and 'module_path' in bugs.columns:
            bug_matrix = bugs_mod.groupby(['version_id', 'module_short']).size().unstack(fill_value=0)
            bug_matrix = bug_matrix.merge(versions[['id', 'version_code']], left_on='version_id', right_on='id')
            bug_matrix = bug_matrix.set_index('version_code').drop(columns=['id', 'version_id'], errors='ignore')
            bug_matrix = bug_matrix.reindex(bug_matrix.sum().sort_values(ascending=False).index, axis=1).head(10)
            st.dataframe(bug_matrix, height=250, use_container_width=True)

    else:
        st.warning("⚠️ 缺少 module_path 字段")

    st.divider()

    # ════════════════════════════════════════════
    # 面板 2: 📊 Bug 解决方案分析
    # ════════════════════════════════════════════
    st.subheader("📊 Bug 解决方案分析")
    st.caption("分析 Bug 解决方式分布，评估提测质量和无效 Bug 比例")

    if 'solution' in bugs.columns:
        col_b1, col_b2 = st.columns([1, 1])

        with col_b1:
            sol_counts = bugs['solution'].fillna('未解决').value_counts()
            fig_sol = st.bar_chart(sol_counts, height=350, use_container_width=True, horizontal=True)

        with col_b2:
            st.markdown("**📋 解决方案明细**")
            sol_detail = bugs['solution'].fillna('未解决').value_counts().reset_index()
            sol_detail.columns = ['解决方案', '数量']
            sol_detail['占比'] = (sol_detail['数量'] / len(bugs) * 100).round(1).astype(str) + '%'
            st.dataframe(sol_detail, use_container_width=True, hide_index=True)

        st.divider()

        # 有效 vs 无效 Bug 分析
        st.markdown("**📈 有效 Bug vs 无效 Bug 分析**")
        valid_solutions = ['已解决']
        invalid_solutions = ['设计如此', '无法重现', '重复Bug', '不予解决', '非BUG设计不合理', '转为需求', '外部原因']
        other_solutions = ['延期处理', '已知问题延期处理', '配置问题', 'his原因', '未解决']

        bugs_analysis = bugs.copy()
        bugs_analysis['category'] = bugs_analysis['solution'].map(
            lambda x: '✅ 有效Bug' if x in valid_solutions
            else '❌ 无效Bug' if x in invalid_solutions
            else '⏳ 其他' if x in other_solutions else '❓ 未解决'
        )

        cat_counts = bugs_analysis['category'].value_counts()
        c1, c2, c3 = st.columns(3)
        for col, label in zip([c1, c2, c3], ['✅ 有效Bug', '❌ 无效Bug', '⏳ 其他']):
            cnt = cat_counts.get(label, 0)
            pct = round(cnt / len(bugs) * 100, 1)
            col.metric(label, cnt, f"占比 {pct}%")

        # 无效 Bug 类型分布
        invalid_bugs = bugs_analysis[bugs_analysis['category'] == '❌ 无效Bug']
        if not invalid_bugs.empty:
            st.divider()
            st.markdown("**❌ 无效 Bug 类型分布**")
            inv_detail = invalid_bugs['solution'].value_counts().reset_index()
            inv_detail.columns = ['原因', '数量']
            st.bar_chart(inv_detail.set_index('原因'), height=250, use_container_width=True)

    st.divider()

    # ════════════════════════════════════════════
    # 面板 3: 🧪 测试阶段 Bug 分布
    # ════════════════════════════════════════════
    st.subheader("🧪 测试阶段 Bug 分布")
    st.caption("评估测试效率：多少 Bug 在早期阶段发现？多少逃逸到后期？")

    if 'test_stage' in bugs.columns and 'severity' in bugs.columns:
        col_c1, col_c2 = st.columns([1, 1])

        with col_c1:
            st.markdown("**📊 各测试阶段 Bug 数量**")
            stage_order = ['一测', '二测', '三测', '灰度', '正式']
            stage_counts = bugs['test_stage'].value_counts()
            stage_counts = stage_counts.reindex([s for s in stage_order if s in stage_counts.index])
            st.bar_chart(stage_counts, height=300, use_container_width=True)

        with col_c2:
            st.markdown("**📋 阶段 × 严重度矩阵**")
            stage_sev = bugs.groupby(['test_stage', 'severity']).size().unstack(fill_value=0)
            stage_sev = stage_sev.reindex([s for s in stage_order if s in stage_sev.index])
            stage_sev.columns = [f'S{s}' for s in stage_sev.columns]
            st.dataframe(stage_sev, height=300, use_container_width=True)

        st.divider()

        # 测试逃逸分析
        st.markdown("**🚨 测试逃逸分析**")
        stage_stats = bugs.groupby('test_stage').agg(
            total=('bug_id', 'count'),
            s1=('severity', lambda x: (x == 1).sum()),
            s2=('severity', lambda x: (x == 2).sum()),
        ).reset_index()
        stage_stats['占比'] = (stage_stats['total'] / len(bugs) * 100).round(1).astype(str) + '%'
        stage_stats = stage_stats.rename(columns={
            'test_stage': '测试阶段', 'total': 'Bug数',
            's1': 'S1', 's2': 'S2', '占比': '占比'
        })
        st.dataframe(stage_stats, use_container_width=True, hide_index=True)

        # 逃逸率说明
        total_early = len(bugs[bugs['test_stage'].isin(['一测', '二测'])])
        total_late = len(bugs[bugs['test_stage'].isin(['三测', '灰度', '正式'])])
        early_pct = round(total_early / len(bugs) * 100, 1)
        late_pct = round(total_late / len(bugs) * 100, 1)
        c1, c2 = st.columns(2)
        c1.metric("🟢 早期发现率 (一测+二测)", f"{early_pct}%", f"{total_early} 条")
        c2.metric("🔴 后期逃逸率 (三测+灰度+正式)", f"{late_pct}%", f"{total_late} 条", delta_color="inverse")

    else:
        st.warning("⚠️ 缺少 test_stage 或 severity 字段")

    # ════════════════════════════════════════════
    # 分隔线 - 新增三个面板
    # ════════════════════════════════════════════
    st.markdown("---")

    # ════════════════════════════════════════════
    # 面板 4: 👨‍💻 人员质量画像
    # ════════════════════════════════════════════
    st.subheader("👨‍💻 人员质量画像")
    st.caption("个人效能与质量对比：需求交付数、Bug修复数、返工率")

    if 'developer' in reqs.columns and 'resolver' in bugs.columns:
        # 需求侧：按开发者统计
        dev_reqs = reqs[reqs['developer'].notna() & (reqs['developer'] != '') & (reqs['developer'] != '/')].copy()
        dev_req_stats = dev_reqs.groupby('developer').agg(
            req_total=('req_id', 'count'),
            req_delivered=('req_status', lambda x: x.isin(['原始','新增']).sum()),
            delayed_test=('is_delayed_test', lambda x: (x == '是').sum()),
            consumed_hours=('consumed_hours', 'sum'),
        ).reset_index()

        # Bug侧：按解决者统计
        dev_bugs = bugs[bugs['resolver'].notna() & (bugs['resolver'] != '') & (bugs['resolver'] != '已知问题延期处理')].copy()
        dev_bug_stats = dev_bugs.groupby('resolver').agg(
            bug_total=('bug_id', 'count'),
            bug_reopened=('activate_count', lambda x: (x > 0).sum()),
            bug_severity=('severity', 'mean'),
        ).reset_index()

        # 合并
        people_df = dev_req_stats.merge(dev_bug_stats, left_on='developer', right_on='resolver', how='outer')
        people_df['developer'] = people_df['developer'].fillna(people_df['resolver'])
        people_df['resolver'] = people_df['developer']
        people_df = people_df.fillna(0)

        # 计算指标
        people_df['bug_per_req'] = (people_df['bug_total'] / people_df['req_total']).round(2)
        people_df['reopen_rate'] = (people_df['bug_reopened'] / people_df['bug_total'] * 100).round(1)
        people_df['delivery_rate'] = (people_df['req_delivered'] / people_df['req_total'] * 100).round(1)
        people_df['delay_rate'] = (people_df['delayed_test'] / people_df['req_total'] * 100).round(1)
        people_df = people_df.sort_values('req_total', ascending=False)

        # 选择显示字段
        display_people = people_df[['developer', 'req_total', 'req_delivered', 'delivery_rate',
                                     'delayed_test', 'delay_rate', 'bug_total', 'bug_reopened',
                                     'reopen_rate', 'bug_per_req', 'consumed_hours']].copy()
        display_people.columns = ['人员', '需求总数', '交付数', '交付率%',
                                   '延期提测数', '延期率%', 'Bug总数', '返工Bug',
                                   '返工率%', 'Bug/需求', '消耗工时']

        # Top 20
        st.dataframe(display_people.head(20), use_container_width=True, hide_index=True)

        st.divider()

        # 散点图: 需求数 vs Bug数
        st.markdown("**📊 需求数 vs Bug数 散点图**")
        scatter_df = people_df[(people_df['req_total'] > 0) | (people_df['bug_total'] > 0)].copy()
        scatter_df = scatter_df[scatter_df['developer'] != '']
        st.scatter_chart(
            scatter_df.set_index('developer')[['req_total', 'bug_total']],
            height=400, use_container_width=True
        )
    else:
        st.warning("⚠️ 缺少 developer 或 resolver 字段")

    st.divider()

    # ════════════════════════════════════════════
    # 面板 5: 🏢 部门效能对比
    # ════════════════════════════════════════════
    st.subheader("🏢 部门效能对比")
    st.caption("一级部门横向对比：需求交付、Bug密度、响应效率")

    if 'dept_level1' in reqs.columns:
        dept_reqs = reqs[reqs['dept_level1'].notna() & (reqs['dept_level1'] != '')].copy()

        # 部门维度统计
        dept_stats = []
        for dept in sorted(dept_reqs['dept_level1'].unique()):
            d_reqs = dept_reqs[dept_reqs['dept_level1'] == dept]
            d_bugs = bugs[bugs['dept_level1_bug'] == dept] if 'dept_level1_bug' in bugs.columns else pd.DataFrame()

            n_total = len(d_reqs)
            n_delivered = len(d_reqs[d_reqs['req_status'].isin(['原始', '新增'])])
            n_delayed = len(d_reqs[d_reqs['is_delayed_test'] == '是'])
            n_bugs = len(d_bugs)
            avg_hours = round(d_reqs['consumed_hours'].mean(), 1) if 'consumed_hours' in d_reqs.columns else '—'

            # 响应时长
            resp = d_reqs[d_reqs['response_days'].notna() & (d_reqs['response_days'] > 0)]['response_days']
            avg_resp = round(resp.mean(), 1) if not resp.empty else '—'

            # 验收通过
            accept_pass = len(d_reqs[d_reqs['acceptance_result'] == '通过'])
            accept_total = len(d_reqs[d_reqs['acceptance_result'].notna()])
            accept_rate = round(accept_pass / accept_total * 100, 1) if accept_total > 0 else '—'

            dept_stats.append({
                '部门': dept,
                '需求总数': n_total,
                '交付数': n_delivered,
                '交付率': round(n_delivered / n_total * 100, 1) if n_total > 0 else 0,
                '延期提测': n_delayed,
                '延期率': round(n_delayed / n_total * 100, 1) if n_total > 0 else 0,
                'Bug总数': n_bugs,
                '缺陷密度': round(n_bugs / n_delivered, 2) if n_delivered > 0 else 0,
                '平均响应(天)': avg_resp,
                '验收通过率': f"{accept_rate}%" if accept_rate != '—' else '—',
                '人均工时': avg_hours,
            })

        dept_df = pd.DataFrame(dept_stats)
        st.dataframe(dept_df, use_container_width=True, hide_index=True)

        st.divider()

        # 部门对比柱状图
        st.markdown("**📊 部门需求与Bug对比**")
        dept_bar = dept_df.set_index('部门')[['需求总数', 'Bug总数', '交付数']]
        st.bar_chart(dept_bar, height=350, use_container_width=True)
    else:
        st.warning("⚠️ 缺少 dept_level1 字段")

    st.divider()

    # ════════════════════════════════════════════
    # 面板 6: ✅ 验收质量分析
    # ════════════════════════════════════════════
    st.subheader("✅ 验收质量分析")
    st.caption("验收结果分布、未通过原因、各版本验收通过率")

    if 'acceptance_result' in reqs.columns:
        accept_reqs = reqs[reqs['acceptance_result'].notna()].copy()

        # 验收结果分布
        accept_counts = accept_reqs['acceptance_result'].value_counts()
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("✅ 通过", int(accept_counts.get('通过', 0)),
                  f"占比 {round(accept_counts.get('通过', 0)/len(accept_reqs)*100,1)}%")
        c2.metric("⏳ 未验证", int(accept_counts.get('未验证', 0)),
                  f"占比 {round(accept_counts.get('未验证', 0)/len(accept_reqs)*100,1)}%")
        c3.metric("❌ 不具备验证条件", int(accept_counts.get('不具备验证条件', 0)),
                  f"占比 {round(accept_counts.get('不具备验证条件', 0)/len(accept_reqs)*100,1)}%")
        total_accept = len(accept_reqs)
        pass_count = int(accept_counts.get('通过', 0))
        c4.metric("📊 验收通过率",
                  f"{round(pass_count/total_accept*100,1) if total_accept > 0 else 0}%",
                  f"{pass_count}/{total_accept}")

        st.divider()

        # 按版本验收通过率
        st.markdown("**📋 各版本验收情况**")
        version_accept = []
        for _, v in versions.iterrows():
            vc = v['version_code']
            v_accept = accept_reqs[accept_reqs['version_id'] == v['id']]
            if len(v_accept) == 0:
                continue
            n_pass = len(v_accept[v_accept['acceptance_result'] == '通过'])
            n_no_verify = len(v_accept[v_accept['acceptance_result'] == '未验证'])
            n_no_cond = len(v_accept[v_accept['acceptance_result'] == '不具备验证条件'])
            version_accept.append({
                '版本': vc,
                '总验收': len(v_accept),
                '通过': n_pass,
                '未验证': n_no_verify,
                '不具备条件': n_no_cond,
                '通过率': f"{round(n_pass/len(v_accept)*100,1)}%",
            })
        st.dataframe(pd.DataFrame(version_accept), use_container_width=True, hide_index=True)

        st.divider()

        # 按部门验收通过率
        if 'dept_level1' in reqs.columns:
            st.markdown("**🏢 各部门验收通过率**")
            dept_accept = []
            for dept in sorted(accept_reqs['dept_level1'].dropna().unique()):
                d_accept = accept_reqs[accept_reqs['dept_level1'] == dept]
                n_pass = len(d_accept[d_accept['acceptance_result'] == '通过'])
                dept_accept.append({
                    '部门': dept,
                    '总验收': len(d_accept),
                    '通过': n_pass,
                    '未通过': len(d_accept) - n_pass,
                    '通过率': f"{round(n_pass/len(d_accept)*100,1)}%",
                })
            st.dataframe(pd.DataFrame(dept_accept), use_container_width=True, hide_index=True)
    else:
        st.warning("⚠️ 缺少 acceptance_result 字段")

# ── 底部 ──
st.markdown("---")
st.caption("禅道质量看板 | 数据更新时间: " + datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
