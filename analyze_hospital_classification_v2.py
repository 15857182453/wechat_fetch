#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
医院智能分级 - 增强版（多维度聚类）
维度包括：
1. 订单量指标：总订单数、日均订单数、订单稳定性
2. 金额指标：总金额、日均金额、客单价
3. 增长指标：周增长率、环比增长率
4. 结构指标：处方结构多样性、 Dienstleistung分布
5. 时间指标：最近活跃时间、活跃天数
"""

import sqlite3
import pandas as pd
import numpy as np
from collections import defaultdict
import random

# 连接数据库
DB_PATH = "/home/openclaw/.openclaw/workspace/business_flow.db"
conn = sqlite3.connect(DB_PATH)

# 查询所有医院的综合数据
query = """
SELECT 
    institution as 医院,
    COUNT(*) as 总订单数,
    SUM(amount) as 总金额,
    ROUND(SUM(amount)/COUNT(*), 2) as 客单价,
    MIN(SUBSTR(yewu_wancheng_shijian, 1, 10)) as 首单日期,
    MAX(SUBSTR(yewu_wancheng_shijian, 1, 10)) as 最近订单日期,
    COUNT(DISTINCT SUBSTR(yewu_wancheng_shijian, 1, 10)) as 活跃天数
FROM (
    SELECT * FROM daily_flow_2025
    UNION ALL
    SELECT * FROM daily_flow_2026_jan_feb
    UNION ALL
    SELECT * FROM daily_flow_2026_mar
    UNION ALL
    SELECT * FROM daily_flow_2026_apr
)
WHERE ye_wu_lei_mu LIKE '%处方服务%'
  AND pay_status = '收费'
GROUP BY institution
HAVING COUNT(*) >= 30  -- 至少30单，排除极小样本
"""

df = pd.read_sql_query(query, conn)
conn.close()

if df.empty:
    print("❌ 无足够数据进行分级")
    exit()

print(f"📊 医院智能分级分析（增强版）")
print(f"统计医院: {len(df)}")
print(f"{'='*70}\n")

# 特征工程
df_features = df.copy()

# 计算运营时长和日均指标
df_features['运营天数'] = (pd.to_datetime(df_features['最近订单日期']) - pd.to_datetime(df_features['首单日期'])).dt.days + 1
df_features['日均订单数'] = df_features['总订单数'] / df_features['运营天数']
df_features['日均金额'] = df_features['总金额'] / df_features['运营天数']

# 计算订单稳定性（标准差/均值）
def calculate_order_stability(hospital):
    hospital_query = f"""
    SELECT 
        SUBSTR(yewu_wancheng_shijian, 1, 10) as 日期,
        COUNT(*) as 单日订单数
    FROM (
        SELECT * FROM daily_flow_2025
        UNION ALL
        SELECT * FROM daily_flow_2026_jan_feb
        UNION ALL
        SELECT * FROM daily_flow_2026_mar
        UNION ALL
        SELECT * FROM daily_flow_2026_apr
    )
    WHERE institution = '{hospital.replace("'", "''")}'
      AND ye_wu_lei_mu LIKE '%处方服务%'
      AND pay_status = '收费'
    GROUP BY SUBSTR(yewu_wancheng_shijian, 1, 10)
    """
    daily_df = pd.read_sql_query(hospital_query, conn)
    
    if len(daily_df) < 7:
        return 0
    
    std_orders = daily_df['单日订单数'].std()
    mean_orders = daily_df['单日订单数'].mean()
    
    if mean_orders > 0:
        return std_orders / mean_orders  # 变异系数，越小越稳定
    return 0

conn = sqlite3.connect(DB_PATH)
df_features['订单稳定性'] = df_features['医院'].apply(calculate_order_stability)
conn.close()

# 计算增长趋势（最近7天 vs 历史平均）
def calculate_growth_rate(hospital):
    hospital_query = f"""
    SELECT 
        SUBSTR(yewu_wancheng_shijian, 1, 10) as 日期,
        COUNT(*) as 单日订单数
    FROM (
        SELECT * FROM daily_flow_2025
        UNION ALL
        SELECT * FROM daily_flow_2026_jan_feb
        UNION ALL
        SELECT * FROM daily_flow_2026_mar
        UNION ALL
        SELECT * FROM daily_flow_2026_apr
    )
    WHERE institution = '{hospital.replace("'", "''")}'
      AND ye_wu_lei_mu LIKE '%处方服务%'
      AND pay_status = '收费'
    GROUP BY SUBSTR(yewu_wancheng_shijian, 1, 10)
    ORDER BY 日期 DESC
    """
    daily_df = pd.read_sql_query(hospital_query, conn)
    
    if len(daily_df) < 14:
        return 0
    
    recent_7 = daily_df.head(7)['单日订单数'].mean()
    historical = daily_df.tail(7)['单日订单数'].mean()  # 用最近7天对比再前7天
    
    if historical > 0 and recent_7 > historical:
        return ((recent_7 - historical) / historical) * 100
    return 0

conn = sqlite3.connect(DB_PATH)
df_features['周增长率'] = df_features['医院'].apply(calculate_growth_rate)
conn.close()

# 计算客单价稳定性
def calculate_price_stability(hospital):
    hospital_query = f"""
    SELECT 
        SUBSTR(yewu_wancheng_shijian, 1, 10) as 日期,
        COUNT(*) as 单日订单数,
        SUM(amount)/COUNT(*) as 单日客单价
    FROM (
        SELECT * FROM daily_flow_2025
        UNION ALL
        SELECT * FROM daily_flow_2026_jan_feb
        UNION ALL
        SELECT * FROM daily_flow_2026_mar
        UNION ALL
        SELECT * FROM daily_flow_2026_apr
    )
    WHERE institution = '{hospital.replace("'", "''")}'
      AND ye_wu_lei_mu LIKE '%处方服务%'
      AND pay_status = '收费'
    GROUP BY SUBSTR(yewu_wancheng_shijian, 1, 10)
    """
    daily_df = pd.read_sql_query(hospital_query, conn)
    
    if len(daily_df) < 7:
        return 0
    
    std_price = daily_df['单日客单价'].std()
    mean_price = daily_df['单日客单价'].mean()
    
    if mean_price > 0:
        return std_price / mean_price
    return 0

conn = sqlite3.connect(DB_PATH)
df_features['客单价稳定性'] = df_features['医院'].apply(calculate_price_stability)
conn.close()

# 计算每周活跃天数（衡量活跃度）
def calculate_weekly_active_days(hospital):
    hospital_query = f"""
    SELECT 
        strftime('%Y-%W', SUBSTR(yewu_wancheng_shijian, 1, 10)) as 周,
        COUNT(DISTINCT SUBSTR(yewu_wancheng_shijian, 1, 10)) as 活跃天数
    FROM (
        SELECT * FROM daily_flow_2025
        UNION ALL
        SELECT * FROM daily_flow_2026_jan_feb
        UNION ALL
        SELECT * FROM daily_flow_2026_mar
        UNION ALL
        SELECT * FROM daily_flow_2026_apr
    )
    WHERE institution = '{hospital.replace("'", "''")}'
      AND ye_wu_lei_mu LIKE '%处方服务%'
      AND pay_status = '收费'
    GROUP BY strftime('%Y-%W', SUBSTR(yewu_wancheng_shijian, 1, 10))
    ORDER BY 周 DESC
    """
    weekly_df = pd.read_sql_query(hospital_query, conn)
    
    if len(weekly_df) < 2:
        return 0
    
    avg_active_days = weekly_df['活跃天数'].mean()
    return avg_active_days

conn = sqlite3.connect(DB_PATH)
df_features['周均活跃天数'] = df_features['医院'].apply(calculate_weekly_active_days)
conn.close()

# 计算订单集中度（前30%订单占总量比例）
def calculate_concentration(hospital):
    hospital_query = f"""
    SELECT 
        SUBSTR(yewu_wancheng_shijian, 1, 10) as 日期,
        COUNT(*) as 单日订单数
    FROM (
        SELECT * FROM daily_flow_2025
        UNION ALL
        SELECT * FROM daily_flow_2026_jan_feb
        UNION ALL
        SELECT * FROM daily_flow_2026_mar
        UNION ALL
        SELECT * FROM daily_flow_2026_apr
    )
    WHERE institution = '{hospital.replace("'", "''")}'
      AND ye_wu_lei_mu LIKE '%处方服务%'
      AND pay_status = '收费'
    GROUP BY SUBSTR(yewu_wancheng_shijian, 1, 10)
    ORDER BY 单日订单数 DESC
    """
    daily_df = pd.read_sql_query(hospital_query, conn)
    
    if len(daily_df) < 7:
        return 0
    
    total_orders = daily_df['单日订单数'].sum()
    top_30_pct = int(len(daily_df) * 0.3)
    if top_30_pct < 1:
        top_30_pct = 1
    
    top_orders = daily_df.head(top_30_pct)['单日订单数'].sum()
    
    if total_orders > 0:
        return top_orders / total_orders
    return 0

conn = sqlite3.connect(DB_PATH)
df_features['订单集中度'] = df_features['医院'].apply(calculate_concentration)
conn.close()

# 增长潜力评分（低基数高增长）
df_features['增长潜力'] = df_features['日均订单数'] * (1 + df_features['周增长率'] / 100)

# 标准化特征
features_cols = [
    '总订单数', '总金额', '客单价', 
    '日均订单数', '日均金额',
    '周增长率', '订单稳定性', '客单价稳定性',
    '周均活跃天数', '订单集中度', '增长潜力'
]

features_for_clustering = df_features[features_cols].copy()

# 归一化到 0-1
def normalize(df):
    return (df - df.min()) / (df.max() - df.min())

features_normalized = normalize(features_for_clustering).values

# 纯Python K-Means实现
class SimpleKMeans:
    def __init__(self, n_clusters=4, max_iter=100, random_state=42):
        self.n_clusters = n_clusters
        self.max_iter = max_iter
        self.random_state = random_state
        self.labels_ = None
        self.cluster_centers_ = None
    
    def fit_predict(self, X):
        random.seed(self.random_state)
        n_samples, n_features = X.shape
        
        # 随机初始化质心
        indices = random.sample(range(n_samples), self.n_clusters)
        centers = X[indices].copy().astype(float)
        
        for iteration in range(self.max_iter):
            distances = np.zeros((n_samples, self.n_clusters))
            for i in range(self.n_clusters):
                distances[:, i] = np.sum((X - centers[i])**2, axis=1)
            
            labels = np.argmin(distances, axis=1)
            
            new_centers = np.zeros_like(centers)
            for i in range(self.n_clusters):
                cluster_points = X[labels == i]
                if len(cluster_points) > 0:
                    new_centers[i] = cluster_points.mean(axis=0)
            
            if np.allclose(centers, new_centers, rtol=1e-4):
                break
            
            centers = new_centers
        
        self.labels_ = labels
        self.cluster_centers_ = centers
        return labels
    
    def silhouette_score(self, X):
        n_samples = X.shape[0]
        labels = self.labels_
        
        a = np.zeros(n_samples)
        b = np.zeros(n_samples)
        
        for i in range(n_samples):
            same_cluster = X[labels == labels[i]]
            if len(same_cluster) > 1:
                a[i] = np.mean(np.sqrt(np.sum((same_cluster - X[i])**2, axis=1)))
            else:
                a[i] = 0
            
            b[i] = np.inf
            for j in range(self.n_clusters):
                if j != labels[i]:
                    other_cluster = X[labels == j]
                    if len(other_cluster) > 0:
                        avg_dist = np.mean(np.sqrt(np.sum((other_cluster - X[i])**2, axis=1)))
                        b[i] = min(b[i], avg_dist)
        
        s = np.zeros(n_samples)
        for i in range(n_samples):
            if max(a[i], b[i]) > 0:
                s[i] = (b[i] - a[i]) / max(a[i], b[i])
        
        return np.mean(s)

# 寻找最优K值
print("🔍 寻找最优K值...")
k_range = range(2, 6)
best_k = 4
best_score = -1

for k in k_range:
    kmeans = SimpleKMeans(n_clusters=k, max_iter=50, random_state=42)
    labels = kmeans.fit_predict(features_normalized)
    score = kmeans.silhouette_score(features_normalized)
    print(f"  K={k}: 轮廓系数 = {score:.3f}")
    if score > best_score:
        best_score = score
        best_k = k

print(f"\n✅ 最优K值: {best_k}")
print(f"  最佳轮廓系数: {best_score:.3f}\n")

# 聚类
kmeans = SimpleKMeans(n_clusters=best_k, max_iter=100, random_state=42)
df_features['聚类标签'] = kmeans.fit_predict(features_normalized)

# 按质心总分排序
centroids = kmeans.cluster_centers_
centroid_scores = centroids.sum(axis=1)
sorted_indices = np.argsort(centroid_scores)[::-1]

reverse_map = {v: k for k, v in enumerate(sorted_indices)}
df_features['医院等级'] = df_features['聚类标签'].map(reverse_map)

level_map = {0: 'A类', 1: 'B类', 2: 'C类', 3: 'D类'}
df_features['医院等级'] = df_features['医院等级'].map(level_map)

# 输出结果
print(f"🏥 医院分级结果（{len(df_features)}家医院）")
print(f"{'='*70}\n")

for level in ['A类', 'B类', 'C类', 'D类']:
    level_df = df_features[df_features['医院等级'] == level]
    if len(level_df) > 0:
        print(f"🏆 {level}: {len(level_df)}家医院")
        level_df_sorted = level_df.sort_values('总订单数', ascending=False)
        for _, row in level_df_sorted.head(10).iterrows():  # 只显示前10个
            print(f"  • {row['医院'][:30]:<30} | 订单:{int(row['总订单数']):<5} | 增长:{row['周增长率']:<6.1f}%")
        if len(level_df) > 10:
            print(f"    ... 还有 {len(level_df)-10} 家医院")
        print()

# 详细数据表格
print(f"📋 完整分级数据")
print(f"{'='*70}")
df_result = df_features[['医院', '医院等级', '总订单数', '总金额', '日均订单数', '周增长率', '订单稳定性']]
df_result = df_result.sort_values(['医院等级', '总订单数'], ascending=[True, False])
df_result.index = range(1, len(df_result) + 1)
print(df_result.to_string())

# 保存结果
output_file = "/home/openclaw/.openclaw/workspace/医院分级报告_增强版.xlsx"
df_features[['医院', '医院等级', '总订单数', '总金额', '日均订单数', '周增长率', '订单稳定性']].sort_values('医院等级').to_excel(
    output_file, index=False
)
print(f"\n📄 报告已保存至: {output_file}")
