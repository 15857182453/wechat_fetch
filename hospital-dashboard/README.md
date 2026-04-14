# 🏥 医院运营数据 Dashboard

## 版本历史

### v4.0 (2026-04-14) - 当前版本
- 8 个功能标签页
- 新增机构趋势图（8 家医院 2x2 网格布局）
- 蓝色标题条 + HTML 转置透视表
- 月环比动态计算（排除空数据）
- 订单数过滤退款（只统计收费）

### v3.0 (2026-04-09)
- 7 个功能标签页
- 动态环比计算

## 文件说明
- `dashboard_v4.py` - 主应用（Streamlit）
- `import_duizhang_summary.py` - 汇总表导入脚本
- `import_duizhang_robust.py` - 健壮版导入脚本

## 运行
```bash
streamlit run dashboard_v4.py
```

访问：http://localhost:8501
