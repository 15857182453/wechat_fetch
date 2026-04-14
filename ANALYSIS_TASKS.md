# 运营数据分析任务清单

## 1️⃣ 医院日度绩效监控（每日）

**执行时间**：每天上午10点前

**目的**：监控各医院昨日业务表现，及时发现异常

**数据源**：
- `daily_flow_2025` (2025年)
- `daily_flow_2026_jan_feb` (2026年1-2月)
- `daily_flow_2026_mar` (2026年3月)
- `daily_flow_apr1` (2026年4月1日)

**SQL查询**：
```sql
SELECT 
    institution as 医院,
    COUNT(*) as 订单数,
    SUM(amount) as 实际支付金额,
    SUM(amount)/COUNT(*) as 客单价
FROM daily_flow_2025
WHERE yewu_wancheng_shijian LIKE '%2025-04-02%'
  AND ye_wu_lei_mu LIKE '%处方%'
  AND pay_status = '收费'
GROUP BY institution
ORDER BY 实际支付金额 DESC
```

**输出**：
- Excel表格：医院、订单数、金额、客单价
- 简短文字报告：Top 10医院 + 异常预警

---

## 2️⃣ 各医院处方服务结构分析（周度）

**执行时间**：每周一

**目的**：了解各医院处方服务内部构成

**数据源**：所有2025-2026年数据

**SQL查询**：
```sql
SELECT 
    institution as 医院,
    ye_wu_zi_lei_mu as 子类目,
    COUNT(*) as 订单数,
    SUM(amount) as 金额,
    SUM(amount)/SUM(SUM(amount)) OVER(PARTITION BY institution) as 占比
FROM daily_flow_2025
WHERE ye_wu_lei_mu LIKE '%处方服务%'
  AND pay_status = '收费'
GROUP BY institution, ye_wu_zi_lei_mu
ORDER BY institution, 金额 DESC
```

**输出**：
- Excel表格：医院、子类目、订单数、金额、占比
- 饼图：各医院处方服务结构

---

## 3️⃣ 医院排名分析（月度）

**执行时间**：每月5日前

**目的**：识别高潜力医院，支持业务拓展

**数据源**：近3个月数据

**SQL查询**：
```sql
SELECT 
    institution as 医院,
    COUNT(*) as 订单数,
    SUM(amount) as 金额,
    (COUNT(*) - LAG(COUNT(*), 1) OVER(PARTITION BY institution ORDER BY SUBSTR(yewu_wancheng_shijian, 1, 7))) / 
        LAG(COUNT(*), 1) OVER(PARTITION BY institution ORDER BY SUBSTR(yewu_wancheng_shijian, 1, 7)) as 月环比增长率
FROM daily_flow_2025
WHERE SUBSTR(yewu_wancheng_shijian, 1, 7) >= '2025-12'
  AND pay_status = '收费'
GROUP BY institution
ORDER BY 金额 DESC
```

**输出**：
- Excel表格：医院排名、关键指标、增长率
- 热力图：颜色标注高增长医院

---

## 4️⃣ 异常值预警（每日/每周）

**执行时间**：每天/每周一

**目的**：自动识别异常业务表现

**检测逻辑**：
- 单日订单数 > 前7天平均 ± 50%
- 单日金额 > 前7天平均 ± 50%
- 新增医院（首次有数据）

**Excel输出**：
| 医院 | 日期 | 订单数 | 环比变化 | 异常类型 |
|------|------|--------|---------|---------|
| ... | ... | ... | ... | ... |

---

## 5️⃣ 处方服务趋势分析（月度）

**执行时间**：每月5日前

**目的**：跟踪处方服务业务发展趋势

**数据源**：近12个月数据

**查询维度**：
- 时间（年-月）
- 处方服务整体
- 便捷购药 vs 院内处方

**输出**：
- 折线图：月度订单数趋势
- 双轴图：订单数+金额趋势
- 附表：详细月度数据

---

## 任务执行方式

### 方式1：手动执行（当前）
直接运行SQL查询，复制结果

### 方式2：自动化脚本（推荐）
创建 `analyze_performance.py` 脚本
- 参数化任务ID
- 自动选择时间范围
- 生成Excel报告
- 发送简短分析报告

### 方式3：集成到 daily heartbeat
在HEARTBEAT.md中添加分析任务

---

## 优先级排序

1. **任务1：医院日度绩效监控** - 最重要，日常 monitoring
2. **任务4：异常值预警** - 紧急，问题发现
3. **任务3：医院排名分析** - 每月运营决策
4. **任务5：处方服务趋势分析** - 策略制定
5. **任务2：处方服务结构分析** - 理解业务