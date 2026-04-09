# 🏥 医院运营数据 Dashboard

医院业务对账数据可视化和导入工具集。

## 📁 文件说明

### Dashboard 应用

| 文件 | 说明 |
|------|------|
| `dashboard_v3.py` | 基础版 Dashboard（6 个标签页） |
| `dashboard_v4.py` | 增强版 Dashboard（白色主题、侧边栏筛选、优化环比分析） |

### 数据导入脚本

| 文件 | 说明 |
|------|------|
| `import_duizhang_robust.py` | 对账汇总数据导入（增量模式） |
| `import_duizhang_detail.py` | 对账明细数据导入（54 列完整字段） |

## 🚀 使用方法

### 启动 Dashboard

```bash
# 基础版
streamlit run dashboard_v3.py --server.port 8501

# 增强版（推荐）
streamlit run dashboard_v4.py --server.port 8501
```

访问：http://localhost:8501

### 导入数据

```bash
# 导入对账汇总数据（增量）
python3 import_duizhang_robust.py

# 导入对账明细数据
python3 import_duizhang_detail.py 业务对账统计明细-20260409085322.xlsx
```

## 📊 Dashboard 功能

### dashboard_v3.py（6 个标签页）
1. 📊 总览分析
2. 📈 趋势洞察
3. ⚠️ 异常监控
4. 🏆 医院排行
5. 🌍 区域分布
6. 📉 月度环比

### dashboard_v4.py（增强功能）
- ✅ 侧边栏：医院选择、日期选择
- ✅ 白色主题 UI
- ✅ 优化的月环比页面布局
- ✅ 7 天运营趋势分析
- ✅ 4 种异常检测算法

## 📋 数据要求

### 对账汇总 Excel
- 文件名：`新流水 2026.xlsx`
- 位置：`/home/openclaw/.openclaw/workspace/`
- 格式：包含日期、各业务流水、总计等列

### 对账明细 Excel
- 文件名：`业务对账统计明细-*.xlsx`
- 54 列完整字段
- 包含商户订单号、机构名称、金额等

## 🗄️ 数据库

- 路径：`/home/openclaw/.openclaw/workspace/business_flow.db`
- 主要表：
  - `duizhang_summary_2026` - 对账汇总
  - `daily_flow_2026_apr` - 4 月明细
  - `duizhang_detail_2026` - 完整对账明细

## 📝 更新日志

**2026-04-09**
- ✅ 新增 dashboard_v4.py（增强版）
- ✅ 修复 SQL 列名问题（institution → prescribing_org）
- ✅ 改为增量导入模式
- ✅ 优化月环比页面布局
- ✅ 清理未来日期空数据

---

**维护者**: OpenClaw  
**最后更新**: 2026-04-09
