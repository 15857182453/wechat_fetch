#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
医院智能分级 - 使用纯Python K-Means聚类算法
A类：订单量TOP 10
B类：增长快
C类：潜力股
D类：需关注
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
    COUNT(*) as 订单数,
    SUM(amount) as 金额,
    ROUND(SUM(amount)/COUNT(*), 2) as 客单价
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
HAVING COUNT(*) >= 20  -- 至少20单，排除极小样本
"""

df = pd.read_sql_query(query, conn)
conn.close()

if df.empty:
    print("❌ 无足够数据进行分级")
    exit()

print(f"📊 医院智能分级分析")
print(f"统计医院: {len(df)}")
print(f"{'='*60}\n")

# 特征工程
df_features = df.copy()

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
    
    if len(daily_df) < 7:
        return 0
    
    recent_7 = daily_df.head(7)['单日订单数'].mean()
    historical = daily_df.tail(14)['单日订单数'].mean() if len(daily_df) > 7 else recent_7
    
    if historical > 0:
        return ((recent_7 - historical) / historical) * 100
    return 0

conn = sqlite3.connect(DB_PATH)

# 计算增长特征
growth_rates = []
for hospital in df_features['医院']:
    growth_rates.append(calculate_growth_rate(hospital))

df_features['增长率'] = growth_rates

conn.close()

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
            # 分配簇
            distances = np.zeros((n_samples, self.n_clusters))
            for i in range(self.n_clusters):
                distances[:, i] = np.sum((X - centers[i])**2, axis=1)
            
            labels = np.argmin(distances, axis=1)
            
            # 更新质心
            new_centers = np.zeros_like(centers)
            for i in range(self.n_clusters):
                cluster_points = X[labels == i]
                if len(cluster_points) > 0:
                    new_centers[i] = cluster_points.mean(axis=0)
            
            # 检查是否收敛
            if np.allclose(centers, new_centers, rtol=1e-4):
                break
            
            centers = new_centers
        
        self.labels_ = labels
        self.cluster_centers_ = centers
        return labels
    
    def silhouette_score(self, X):
        """计算轮廓系数"""
        n_samples = X.shape[0]
        labels = self.labels_
        
        a = np.zeros(n_samples)  # 同簇平均距离
        b = np.zeros(n_samples)  # 最近异簇平均距离
        
        for i in range(n_samples):
            # 计算同簇平均距离
            same_cluster = X[labels == labels[i]]
            if len(same_cluster) > 1:
                a[i] = np.mean(np.sqrt(np.sum((same_cluster - X[i])**2, axis=1)))
            else:
                a[i] = 0
            
            # 计算最近异簇平均距离
            b[i] = np.inf
            for j in range(self.n_clusters):
                if j != labels[i]:
                    other_cluster = X[labels == j]
                    if len(other_cluster) > 0:
                        avg_dist = np.mean(np.sqrt(np.sum((other_cluster - X[i])**2, axis=1)))
                        b[i] = min(b[i], avg_dist)
        
        # 轮廓系数
        s = np.zeros(n_samples)
        for i in range(n_samples):
            if max(a[i], b[i]) > 0:
                s[i] = (b[i] - a[i]) / max(a[i], b[i])
        
        return np.mean(s)

# 标准化特征
features_for_clustering = df_features[['订单数', '金额', '客单价', '增长率']].copy()

# 归一化到 0-1
def normalize(df):
    return (df - df.min()) / (df.max() - df.min())

features_normalized = normalize(features_for_clustering).values

# 确定最优K值（纯Python实现）
k_range = range(2, 6)
best_k = 4
best_score = -1

print("🔍 寻找最优K值...")
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

# 使用最优K值进行聚类
kmeans = SimpleKMeans(n_clusters=best_k, max_iter=100, random_state=42)
df_features['聚类标签'] = kmeans.fit_predict(features_normalized)

# 按聚类质心排序
centroids = kmeans.cluster_centers_
centroid_scores = centroids.sum(axis=1)  # 总分
sorted_indices = np.argsort(centroid_scores)[::-1]  # 降序

# 创建映射：0=A, 1=B, 2=C, 3=D
reverse_map = {v: k for k, v in enumerate(sorted_indices)}
df_features['医院等级'] = df_features['聚类标签'].map(reverse_map)

# 映射到A/B/C/D
level_map = {0: 'A类', 1: 'B类', 2: 'C类', 3: 'D类'}
df_features['医院等级'] = df_features['医院等级'].map(level_map)

# 输出结果
print(f"🏥 医院分级结果")
print(f"{'='*60}\n")

for level in ['A类', 'B类', 'C类', 'D类']:
    level_df = df_features[df_features['医院等级'] == level]
    if len(level_df) > 0:
        print(f"🏆 {level}: {len(level_df)}家医院")
        level_df_sorted = level_df.sort_values('订单数', ascending=False)
        for idx, row in level_df_sorted.iterrows():
            print(f"  • {row['医院']}: 订单{int(row['订单数']):,}, 金额{row['金额']:,.0f}元, 增长{row['增长率']:.1f}%")
        print()

# 详细数据表格
print(f"📋 详细数据表格")
print(f"{'='*60}")
df_result = df_features[['医院', '医院等级', '订单数', '金额', '客单价', '增长率']]
df_result = df_result.sort_values(['医院等级', '订单数'], ascending=[True, False])
df_result.index = range(1, len(df_result) + 1)
print(df_result.to_string())

# 保存结果
output_file = "/home/openclaw/.openclaw/workspace/医院分级报告.xlsx"
df_features[['医院', '医院等级', '订单数', '金额', '客单价', '增长率']].sort_values('医院等级').to_excel(
    output_file, index=False
)
print(f"\n📄 报告已保存至: {output_file}")
