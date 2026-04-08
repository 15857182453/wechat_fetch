# 📦 GitHub 项目索引

本文档索引所有上传到 GitHub 的代码项目和任务。

**仓库地址**: https://github.com/15857182453/wechat_fetch

**最后更新**: 2026-04-08

---

## 📁 项目结构

```
wechat_fetch/
├── 📊 数据分析与报表
│   ├── dashboard_v3.py              # Streamlit 医院数据仪表板
│   ├── import_duizhang_robust.py    # 对账数据导入脚本（健壮版）
│   ├── daily_import.sh              # 每日导入快捷脚本
│   └── business_flow.db             # SQLite 数据库
│
├── 🏥 医院数据管理
│   ├── analyze_hospital_*.py        # 医院数据分析脚本
│   ├── auto-reconcile-*.py          # 自动对账脚本
│   └── import_*.py                  # 数据导入脚本
│
├── 💬 微信公 众号数据
│   ├── wechat-hangzhou-normal-university/
│   ├── multi-wechat-hospitals/
│   └── media-crawler/
│
├── 📈 图表与可视化
│   ├── huhuan_chart_*.png           # 环湖图表
│   └── business_chart.png           # 业务图表
│
├── 🤖 智能体与技能
│   ├── skills/                      # OpenClaw 技能
│   └── data-import-agent/           # 数据导入智能体
│
└── 📝 文档
    ├── GITHUB_PROJECTS.md           # 本文档
    ├── 每日导入 - 使用说明.md        # 导入指南
    └── api 接口文档.md               # GrowingIO API 文档
```

---

## 📋 任务清单

### 1. 医院数据 Dashboard

**文件**: `dashboard_v3.py`

**功能**:
- 📊 6 个标签页（总览、趋势、异常监控、排行、区域分布、月环比）
- ⚠️ 4 种异常检测算法（Z-Score、IQR、动态阈值、环比暴增）
- 📈 月环比自动计算（动态到最新数据日期）
- 🗺️ 区域分布可视化

**访问**: http://localhost:8501

**相关文档**: `每日导入 - 使用说明.md`

---

### 2. 对账数据导入系统

**文件**: 
- `import_duizhang_robust.py` (健壮版导入脚本)
- `daily_import.sh` (一键导入)

**功能**:
- ✅ 自动单位检测（元/万元）
- ✅ 数据验证（范围、环比、分项之和）
- ✅ 自动去重更新
- ✅ 删除未来空数据

**使用**:
```bash
./daily_import.sh
```

---

### 3. 医院数据分析

**文件**:
- `analyze_hospital_classification.py` - 医院分级分析
- `analyze_hospital_classification_v2.py` - 增强版
- `analyze_hospital_daily.py` - 每日分析
- `analyze_hospital_structure.py` - 结构分析
- `analyze_anomaly.py` - 异常分析

**输出**:
- 医院分级报告
- 异常监控报告
- 每日业务报表

---

### 4. 自动对账系统

**文件**:
- `auto-reconcile-simple.py` - 简单对账
- `auto-reconcile-v2.py` - v2 版本
- `auto-reconcile-v3.py` - v3 版本
- `auto-reconcile-final.py` - 最终版
- `auto-reconcile-local.py` - 本地对账

**功能**: 自动比对流水和订单数据，生成对账报告

---

### 5. 微信公众号数据抓取

**目录**:
- `multi-wechat-hospitals/` - 多医院公众号数据
- `wechat-hangzhou-normal-university/` - 杭州师范大学
- `media-crawler/` - 媒体爬虫框架

**功能**:
- 自动抓取公众号文章数据
- 同步到 GrowingIO 分析平台
- 生成阅读/分享报表

**配置**: `multi-wechat-hospitals/hospitals.yml`

---

### 6. 数据导入智能体

**目录**: `data-import-agent/`

**功能**: 自动化数据导入流程

---

### 7. GrowingIO 集成

**文件**: `api 接口文档.md`

**支持接口**:
- 事件分析
- 漏斗分析
- 留存分析
- 分布分析

**API 地址**: https://api-portal.fenxiti.com/v1/api/

---

## 🔄 上传流程

### 首次上传

```bash
cd /home/openclaw/.openclaw/workspace

# 1. 添加文件
git add dashboard_v3.py
git add import_duizhang_robust.py
git add daily_import.sh
git add 每日导入 - 使用说明.md

# 2. 提交
git commit -m "feat: 添加医院数据 Dashboard 和导入系统

- dashboard_v3.py: Streamlit 仪表板（6 个标签页）
- import_duizhang_robust.py: 健壮版导入脚本（自动单位检测）
- daily_import.sh: 一键导入脚本
- 每日导入 - 使用说明.md: 使用文档

功能:
✅ 自动单位检测（元/万元）
✅ 数据验证（范围、环比、分项之和）
✅ 4 种异常检测算法
✅ 月环比自动计算

作者：OpenClaw
日期：2026-04-08"

# 3. 推送
git push origin master
```

### 日常更新

```bash
cd /home/openclaw/.openclaw/workspace

# 添加修改的文件
git add <文件名>

# 提交
git commit -m "fix/update: 简要描述修改内容"

# 推送
git push origin master
```

---

## 📝 任务文档模板

为每个任务创建对应的 `.md` 文档：

```markdown
# 任务名称

## 📁 文件位置

- 主文件：`路径/文件名.py`
- 配置：`路径/配置.yml`
- 文档：`路径/说明.md`

## 🎯 功能描述

简要描述任务功能

## 🚀 使用方法

```bash
# 运行命令
python3 文件名.py
```

## 📊 输出结果

描述输出内容

## 📅 创建日期

YYYY-MM-DD

## 🔄 更新历史

- YYYY-MM-DD: 初始版本
- YYYY-MM-DD: 功能更新
```

---

## ⚠️ 注意事项

1. **不要上传的文件**:
   - `*.db` (数据库文件，可能包含敏感数据)
   - `*.xlsx` (Excel 文件，体积大)
   - `__pycache__/` (Python 缓存)
   - `*.png` (图表文件，可选上传)

2. **敏感信息**:
   - API Token
   - 数据库密码
   - 个人隐私数据

3. **大文件**:
   - 使用 Git LFS 管理
   - 或放在 releases 中

---

## 📞 支持

如有问题，请查看：
- 各任务的 `.md` 文档
- `每日导入 - 使用说明.md`
- `api 接口文档.md`

**维护者**: OpenClaw
**最后更新**: 2026-04-08
