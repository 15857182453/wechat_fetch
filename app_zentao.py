#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Phase 4+5: 禅道研发质量看板 (Streamlit Dashboard)
数据源：本地 SQLite 缓存库 (zentao_new_cache.db)
"""

import sys
import os
import sqlite3
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from datetime import datetime, timedelta

sys.path.append(os.path.dirname(__file__))
import warnings
warnings.filterwarnings('ignore')

from config import LOCAL_CACHE_DB

import streamlit as st

st.set_page_config(page_title="禅道研发质量看板", page_icon="📊", layout="wide")

# === 认证守卫 ===
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.title("🔐 禅道研发质量看板")
    pwd = st.text_input("请输入密码", type="password")
    if st.button("登录"):
        if pwd == "admin":
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error("密码错误")
    st.stop()

# === 数据加载 ===
@st.cache_data(ttl=300)
def load_all_data():
    """从本地缓存加载所有数据"""
    conn = sqlite3.connect(LOCAL_CACHE_DB)
    data = {}
    for table in ['project', 'projectstory', 'story', 'task', 'bug',
                  'user', 'module', 'action', 'feedback']:
        data[table] = pd.read_sql(f'SELECT * FROM zt_{table}', conn)
    conn.close()
    return data

data = load_all_data()
project = data['project']
projectstory = data['projectstory']
story = data['story']
task = data['task']
bug = data['bug']
action = data['action']
feedback = data['feedback']

# === 侧边栏 ===
st.sidebar.title("🎯 筛选条件")
version_options = project['name'].tolist()
selected_versions = st.sidebar.multiselect(
    "选择版本", options=version_options, default=version_options
)

if not selected_versions:
    st.warning("请至少选择一个版本")
    st.stop()

selected_project_ids = project[project['name'].isin(selected_versions)]['id'].tolist()

# 筛选关联的需求
ps_filtered = projectstory[projectstory['project'].isin(selected_project_ids)]
story_ids = ps_filtered['story'].unique().tolist()
story_filtered = story[story['id'].isin(story_ids)]
task_filtered = task[task['project'].isin(selected_project_ids)]
bug_filtered = bug[bug['product'].isin(story_filtered['product'].unique())]

# === 主页面 ===
st.title("📊 禅道研发质量看板")
st.markdown(f"**数据同步时间**: {story_filtered['sync_time'].max() if not story_filtered.empty else '无数据'} | "
            f"**筛选版本**: {', '.join(selected_versions)}")

# === Tab 布局 ===
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📋 总览", "📈 需求分析", "🐛 Bug 分析", "⚡ 研发效能", "📊 版本对比"
])

# ========== TAB 1: 总览 ==========
with tab1:
    st.header("📋 研发质量总览")

    # KPI 卡片
    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("需求总数", len(story_filtered))
    col2.metric("已关闭需求", len(story_filtered[story_filtered['status'] == 'closed']))
    col3.metric("任务总数", len(task_filtered))
    col4.metric("Bug总数", len(bug_filtered))
    col5.metric("涉及产品数", story_filtered['product'].nunique())

    st.divider()

    # 需求 vs 任务 vs Bug 对比
    col1, col2 = st.columns(2)

    with col1:
        fig = go.Figure(data=[
            go.Bar(name='需求', x=['总数'], y=[len(story_filtered)], marker_color='#636EFA'),
            go.Bar(name='已关闭', x=['总数'], y=[len(story_filtered[story_filtered['status']=='closed'])], marker_color='#00CC96'),
            go.Bar(name='任务', x=['总数'], y=[len(task_filtered)], marker_color='#EF553B'),
            go.Bar(name='Bug', x=['总数'], y=[len(bug_filtered)], marker_color='#FFA15A'),
        ])
        fig.update_layout(title="需求/任务/Bug 对比", barmode='group', height=350)
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        # 需求状态饼图
        status_counts = story_filtered['status'].value_counts()
        fig = go.Figure(data=[
            go.Pie(labels=status_counts.index, values=status_counts.values,
                   hole=0.4, marker_colors=['#00CC96', '#EF553B', '#636EFA'])
        ])
        fig.update_layout(title="需求状态分布", height=350)
        st.plotly_chart(fig, use_container_width=True)

    # 各版本需求分布
    st.subheader("📅 各版本需求分布")
    version_story = pd.merge(ps_filtered, story, left_on='story', right_on='id', how='left')
    version_proj = pd.merge(version_story, project, left_on='project', right_on='id', how='left', suffixes=('', '_proj'))
    version_count = version_proj.groupby('name')['id'].count().reset_index()
    version_count.columns = ['版本', '需求数']

    fig = go.Figure(data=[
        go.Bar(x=version_count['版本'], y=version_count['需求数'],
               marker_color='#636EFA', text=version_count['需求数'], textposition='auto')
    ])
    fig.update_layout(title="各版本需求数量", height=350,
                      xaxis_title="版本", yaxis_title="需求数")
    st.plotly_chart(fig, use_container_width=True)

# ========== TAB 2: 需求分析 ==========
with tab2:
    st.header("📈 需求分析")

    col1, col2 = st.columns(2)

    with col1:
        # 需求优先级分布
        pri_map = {0: 'P0', 1: 'P0', 2: 'P1', 3: 'P2', 4: 'P3'}
        story_filtered = story_filtered.copy()
        story_filtered['优先级'] = story_filtered['pri'].map(pri_map).fillna('未知')
        pri_counts = story_filtered['优先级'].value_counts().sort_index()

        fig = go.Figure(data=[
            go.Bar(x=pri_counts.index, y=pri_counts.values,
                   marker_color=['#EF553B', '#FFA15A', '#636EFA', '#00CC96', '#AB63FA'],
                   text=pri_counts.values, textposition='auto')
        ])
        fig.update_layout(title="需求优先级分布", height=350)
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        # 需求阶段分布
        stage_counts = story_filtered['stage'].value_counts()
        fig = go.Figure(data=[
            go.Pie(labels=stage_counts.index, values=stage_counts.values,
                   hole=0.4)
        ])
        fig.update_layout(title="需求阶段分布", height=350)
        st.plotly_chart(fig, use_container_width=True)

    # 需求时间趋势
    st.subheader("📅 需求创建时间趋势")
    story_filtered['openedDate'] = pd.to_datetime(story_filtered['openedDate'], errors='coerce')
    story_by_date = story_filtered.dropna(subset=['openedDate']).groupby(
        story_filtered['openedDate'].dt.date
    ).size().reset_index(name='count')
    story_by_date.columns = ['日期', '需求数']

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=story_by_date['日期'], y=story_by_date['需求数'],
                             mode='lines+markers', name='需求数',
                             line=dict(color='#636EFA', width=2),
                             fill='tozeroy'))
    fig.update_layout(title="需求创建时间趋势", height=350,
                      xaxis_title="日期", yaxis_title="需求数")
    st.plotly_chart(fig, use_container_width=True)

    # Top 评审人（产品经理）
    st.subheader("👤 Top 需求评审人（产品经理）")
    reviewer_counts = story_filtered['reviewedBy'].value_counts().head(10)
    fig = go.Figure(data=[
        go.Bar(x=reviewer_counts.index, y=reviewer_counts.values,
               marker_color='#00CC96', text=reviewer_counts.values, textposition='auto')
    ])
    fig.update_layout(title="Top 10 需求评审人", height=350,
                      xaxis_tickangle=-45)
    st.plotly_chart(fig, use_container_width=True)

# ========== TAB 3: Bug 分析 ==========
with tab3:
    st.header("🐛 Bug 分析")

    col1, col2, col3 = st.columns(3)
    col1.metric("Bug总数", len(bug_filtered))
    active_bugs = len(bug_filtered[bug_filtered['status'] == 'active'])
    col2.metric("活跃Bug", active_bugs)
    closed_bugs = len(bug_filtered[bug_filtered['status'] == 'closed'])
    col3.metric("已关闭", closed_bugs)

    st.divider()

    col1, col2 = st.columns(2)

    with col1:
        # Bug 状态分布
        bug_status = bug_filtered['status'].value_counts()
        fig = go.Figure(data=[
            go.Pie(labels=bug_status.index, values=bug_status.values,
                   hole=0.4, marker_colors=['#EF553B', '#00CC96', '#FFA15A'])
        ])
        fig.update_layout(title="Bug 状态分布", height=350)
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        # Bug 严重程度分布
        bug_sev = bug_filtered['severity'].value_counts().sort_index()
        sev_labels = {1: '致命', 2: '严重', 3: '一般', 4: '提示'}
        bug_sev.index = bug_sev.index.map(lambda x: sev_labels.get(x, f'L{x}'))
        fig = go.Figure(data=[
            go.Bar(x=bug_sev.index, y=bug_sev.values,
                   marker_color=['#EF553B', '#FFA15A', '#636EFA', '#00CC96'],
                   text=bug_sev.values, textposition='auto')
        ])
        fig.update_layout(title="Bug 严重程度分布", height=350)
        st.plotly_chart(fig, use_container_width=True)

    # Bug 创建趋势
    st.subheader("📅 Bug 创建时间趋势")
    bug_filtered = bug_filtered.copy()
    bug_filtered['openedDate'] = pd.to_datetime(bug_filtered['openedDate'], errors='coerce')
    bug_by_date = bug_filtered.dropna(subset=['openedDate']).groupby(
        bug_filtered['openedDate'].dt.date
    ).size().reset_index(name='count')
    bug_by_date.columns = ['日期', 'Bug数']

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=bug_by_date['日期'], y=bug_by_date['Bug数'],
                             mode='lines+markers', name='Bug数',
                             line=dict(color='#EF553B', width=2),
                             fill='tozeroy'))
    fig.update_layout(title="Bug 创建时间趋势", height=350)
    st.plotly_chart(fig, use_container_width=True)

    # Top Bug 创建者
    st.subheader("👤 Top Bug 创建者")
    bug_opener = bug_filtered['openedBy'].value_counts().head(10)
    fig = go.Figure(data=[
        go.Bar(x=bug_opener.index, y=bug_opener.values,
               marker_color='#FFA15A', text=bug_opener.values, textposition='auto')
    ])
    fig.update_layout(title="Top 10 Bug 创建者", height=350,
                      xaxis_tickangle=-45)
    st.plotly_chart(fig, use_container_width=True)

# ========== TAB 4: 研发效能 ==========
with tab4:
    st.header("⚡ 研发效能指标")

    # 1. 需求-任务关联率
    story_with_task = story_filtered[story_filtered['id'].isin(task_filtered['story'])]
    assoc_rate = len(story_with_task) / len(story_filtered) * 100 if len(story_filtered) > 0 else 0

    # 2. 任务完成率
    task_done = len(task_filtered[task_filtered['status'].isin(['done', 'closed'])])
    task_complete_rate = task_done / len(task_filtered) * 100 if len(task_filtered) > 0 else 0

    # 3. Bug 解决率
    bug_resolved = len(bug_filtered[bug_filtered['status'].isin(['resolved', 'closed'])])
    bug_resolve_rate = bug_resolved / len(bug_filtered) * 100 if len(bug_filtered) > 0 else 0

    # 4. 评审通过率
    reviewed_actions = action[action['action'] == 'reviewed']
    story_reviewed = reviewed_actions[reviewed_actions['objectID'].isin(story_ids)]
    pass_count = len(story_reviewed[story_reviewed['extra'] == 'Pass'])
    review_pass_rate = pass_count / len(story_reviewed) * 100 if len(story_reviewed) > 0 else 0

    # 5. 平均消耗工时
    avg_consumed = task_filtered['consumed'].mean()
    total_consumed = task_filtered['consumed'].sum()

    # 6. 平均预估工时
    avg_estimate = task_filtered['estimate'].mean()

    # KPI 卡片
    st.subheader("🎯 核心指标")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("需求-任务关联率", f"{assoc_rate:.1f}%")
    col2.metric("任务完成率", f"{task_complete_rate:.1f}%")
    col3.metric("Bug 解决率", f"{bug_resolve_rate:.1f}%")
    col4.metric("评审通过率", f"{review_pass_rate:.1f}%")

    col1, col2 = st.columns(2)
    col1.metric("平均消耗工时", f"{avg_consumed:.1f}h")
    col2.metric("总消耗工时", f"{total_consumed:.1f}h")

    st.divider()

    # 效能指标雷达图
    st.subheader("🕸️ 效能雷达图")
    metrics = ['需求关联率', '任务完成率', 'Bug解决率', '评审通过率']
    values = [assoc_rate, task_complete_rate, bug_resolve_rate, review_pass_rate]

    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(
        r=values, theta=metrics, fill='toself',
        name='当前版本', line=dict(color='#636EFA'),
        marker=dict(color='#636EFA')
    ))
    fig.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
        showlegend=True, height=400
    )
    st.plotly_chart(fig, use_container_width=True)

    # 任务工时分布
    st.subheader("⏱️ 任务工时分布")
    col1, col2 = st.columns(2)
    with col1:
        fig = go.Figure()
        fig.add_trace(go.Histogram(x=task_filtered['consumed'].dropna(),
                                    nbinsx=30, marker_color='#636EFA'))
        fig.update_layout(title="消耗工时分布", height=350,
                          xaxis_title="工时(h)", yaxis_title="任务数")
        st.plotly_chart(fig,use_container_width=True)

    with col2:
        # 任务状态分布
        task_status = task_filtered['status'].value_counts()
        fig = go.Figure(data=[
            go.Pie(labels=task_status.index, values=task_status.values,
                   hole=0.4, marker_colors=['#00CC96', '#636EFA', '#EF553B', '#FFA15A', '#AB63FA'])
        ])
        fig.update_layout(title="任务状态分布", height=350)
        st.plotly_chart(fig, use_container_width=True)

    # 评审记录详情
    st.subheader("📝 评审记录详情")
    if not story_reviewed.empty:
        review_summary = story_reviewed.groupby(['extra']).size().reset_index(name='count')
        fig = go.Figure(data=[
            go.Bar(x=review_summary['extra'], y=review_summary['count'],
                   marker_color=['#00CC96' if x == 'Pass' else '#EF553B' for x in review_summary['extra']],
                   text=review_summary['count'], textposition='auto')
        ])
        fig.update_layout(title="评审结果分布", height=350)
        st.plotly_chart(fig, use_container_width=True)

# ========== TAB 5: 版本对比 ==========
with tab5:
    st.header("📊 版本对比")

    # 按版本聚合指标
    version_metrics = []
    for _, proj in project.iterrows():
        pid = proj['id']
        ps = projectstory[projectstory['project'] == pid]
        sids = ps['story'].unique()

        v_stories = story[story['id'].isin(sids)]
        v_tasks = task[task['project'] == pid]
        v_bugs = bug[bug['product'].isin(v_stories['product'].unique())]

        v_stories_closed = len(v_stories[v_stories['status'] == 'closed'])
        v_tasks_done = len(v_tasks[v_tasks['status'].isin(['done', 'closed'])])
        v_bugs_resolved = len(v_bugs[v_bugs['status'].isin(['resolved', 'closed'])])

        v_reviewed = action[(action['action'] == 'reviewed') & (action['objectID'].isin(sids))]
        v_pass = len(v_reviewed[v_reviewed['extra'] == 'Pass'])

        version_metrics.append({
            '版本': proj['name'],
            '需求数': len(v_stories),
            '已关闭需求': v_stories_closed,
            '任务数': len(v_tasks),
            '已完成任务': v_tasks_done,
            'Bug数': len(v_bugs),
            '已解决Bug': v_bugs_resolved,
            '评审次数': len(v_reviewed),
            '评审通过': v_pass,
            '总工时': v_tasks['consumed'].sum(),
            '平均工时': v_tasks['consumed'].mean(),
        })

    vm_df = pd.DataFrame(version_metrics)

    # 版本对比表格
    st.dataframe(vm_df, use_container_width=True, height=400)

    # 版本对比图表
    col1, col2 = st.columns(2)

    with col1:
        fig = go.Figure()
        fig.add_trace(go.Bar(x=vm_df['版本'], y=vm_df['需求数'],
                             name='需求数', marker_color='#636EFA'))
        fig.add_trace(go.Bar(x=vm_df['版本'], y=vm_df['Bug数'],
                             name='Bug数', marker_color='#EF553B'))
        fig.update_layout(title="各版本需求 vs Bug", height=350,
                          barmode='group', xaxis_tickangle=-30)
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        fig = go.Figure()
        fig.add_trace(go.Bar(x=vm_df['版本'], y=vm_df['总工时'],
                             name='总工时', marker_color='#00CC96'))
        fig.update_layout(title="各版本总工时", height=350,
                          xaxis_tickangle=-30)
        st.plotly_chart(fig, use_container_width=True)

    # 版本完成率对比
    st.subheader("📈 版本完成率对比")
    vm_df = vm_df.copy()
    vm_df['需求完成率'] = (vm_df['已关闭需求'] / vm_df['需求数'] * 100).round(1)
    vm_df['任务完成率'] = (vm_df['已完成任务'] / vm_df['任务数'] * 100).round(1)
    vm_df['Bug解决率'] = (vm_df['已解决Bug'] / vm_df['Bug数'] * 100).round(1)

    fig = go.Figure()
    fig.add_trace(go.Bar(x=vm_df['版本'], y=vm_df['需求完成率'],
                         name='需求完成率', marker_color='#636EFA'))
    fig.add_trace(go.Bar(x=vm_df['版本'], y=vm_df['任务完成率'],
                         name='任务完成率', marker_color='#00CC96'))
    fig.add_trace(go.Bar(x=vm_df['版本'], y=vm_df['Bug解决率'],
                         name='Bug解决率', marker_color='#FFA15A'))
    fig.update_layout(title="各版本完成率对比", height=350,
                      barmode='group', xaxis_tickangle=-30,
                      yaxis=dict(title='完成率 (%)'))
    st.plotly_chart(fig, use_container_width=True)
