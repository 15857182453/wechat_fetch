# 多医院微信公众号数据抓取系统 - 更新日志

## 2026-03-30 v1.0.0 - 初始版本

### 新增功能
- ✅ 支持多医院配置文件管理
- ✅ YAML 格式配置文件，易于维护
- ✅ 每家医院独立的日志和数据目录
- ✅ 自动去重机制，避免重复上报
- ✅ 灵活的执行方式（批量/单个/日期范围）
- ✅ 钉钉通知支持

### 文件结构
```
multi-wechat-hospitals/
├── hospitals.yml              # 医院配置文件
├── run_hospitals.py           # 批量执行脚本
├── templates/
│   └── wechat_fetch_hospital.py  # 单医院执行模板
└── README.md                  # 使用文档
```

### 使用示例
```bash
# 执行所有医院（默认最近7天）
python3 run_hospitals.py

# 执行指定医院
python3 run_hospitals.py --hospital "医院1名称"

# 指定日期范围
python3 run_hospitals.py --start 2026-03-01 --end 2026-03-30

# Dry-run 模式
python3 run_hospitals.py --dry-run
```

### 注意事项
- ⚠️ 需要手动开启 VPN 才能上传到 GrowingIO
- ⚠️ 配置文件包含敏感信息，请妥善保管
