# 杭州师范大学附属医院微信公众号数据抓取工作区

## 项目说明

此工作区专用于杭州师范大学附属医院微信公众号的数据抓取和 GrowingIO 数据上报。

## 目录结构

```
wechat-hangzhou-normal-university/
├── wechat_fetch.py      # 主要的抓取和上报脚本
├── client.py            # OpenAPI 客户端
├── logs/                # 数据和日志保存目录
│   ├── wechat_report_state.json  # 去重记录
│   ├── daily_report_*.json       # 上传数据快照
│   └── wechat_article_stats_*.csv # 汇总数据
```

## 使用方法

```bash
# 指定日期范围
python3 wechat_fetch.py --start 2026-02-14 --end 2026-02-14

# 最近 N 天
python3 wechat_fetch.py --days 7

# 仅今天
python3 wechat_fetch.py --today

# 调试模式
python3 wechat_fetch.py --days 7 --debug

# 干跑模式（不上传）
python3 wechat_fetch.py --days 7 --dry-run
```

## 配置说明

在 `wechat_fetch.py` 文件顶部修改配置：

```python
# 微信公众号配置
HOSPITAL_ORG_ID = "1005657"
OFFICIAL_ACCOUNT_NAME = "杭州师范大学附属医院"
OFFICIAL_ACCOUNT_TYPE = "订阅号"
APPID = "wxb946acbb0c6d9de6"

# OpenAPI 配置
OPENAPI_CONFIG = { ... }

# GrowingIO 配置
GROWINGIO_CONFIG = {
    "product_id": "98b451a0ec02c41a",
    "data_source_id": "b7f6d83f9c9734b6",
    "server_host": "https://ngari-collect.fenxiti.com/",
    "event_name": "OA_officialNewsDailyData2",
}
```

## 注意事项

- 所有数据（去重记录、JSON、CSV）都保存在 `logs/` 目录中
- 去重记录使用 `orgId` 标识，支持多医院数据隔离
- 如需修改为其他医院，请确保更新 `HOSPITAL_ORG_ID` 和 `APPID`
