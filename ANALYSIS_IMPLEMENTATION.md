# 运营数据分析任务 - 实施文档

## 📅 任务1：医院日度绩效监控（每日）

**脚本**：`analyze_hospital_daily.py`

**执行方式**：
```bash
# 查询指定日期
python3 analyze_hospital_daily.py 2025-12-31

# 查询默认日期（昨天）
python3 analyze_hospital_daily.py
```

**输出**：
- 各医院订单数、金额、客单价
- 汇总数据（总订单、总金额、平均客单价）
- Top 5医院

**插件**：可集成到健康检查中

---

## ✅ 环节2：各医院处方服务结构分析（待实现）

**目标**：统计各医院处方服务的内部构成（便捷购药 vs 院内处方）

**执行方式**（待创建脚本）：
```bash
python3 analyze_hospital_structure.py [医院名称] [时间范围]
```

---

## ✅ 环节3：医院排名分析（待实现）

**目标**：近3个月医院排名，含增长率

**执行方式**（待创建脚本）：
```bash
python3 analyze_ranking.py [时间范围]
```

---

## ✅ 环节4：异常值预警（待实现）

**目标**：检测订单数/金额异常变化

**执行方式**（待创建脚本）：
```bash
python3 analyze_anomaly.py [时间范围]
```

---

## ✅ 环节5：处方服务趋势分析（待实现）

**目标**：近12个月处方服务趋势

**执行方式**（待创建脚本）：
```bash
python3 analyze_trend.py
```

---

## 📊 当前进度

✅ 任务1已完成并测试通过
⏳ 任务2-5 待实现

## 📁 文件位置

- `/home/openclaw/.openclaw/workspace/analyze_hospital_daily.py`
- `/home/openclaw/.openclaw/workspace/DATA_ANALYSIS_PROCESS.md`
- `/home/openclaw/.openclaw/workspace/ANALYSIS_TASKS.md`