# 微信公众号数据抓取脚本

## 功能

- 抓取微信公众号历史文章数据
- 每日自动上报到 GrowingIO
- 去重机制，避免重复上报
- 钉钉机器人通知任务完成情况

## 使用方法

```bash
# 抓取最近 30 天数据
python3 wechat_fetch.py --days 30

# 抓取指定日期范围
python3 wechat_fetch.py --start 2026-02-15 --end 2026-03-16

# 抓取今天
python3 wechat_fetch.py --today

# 仅抓取不上报（测试用）
python3 wechat_fetch.py --days 7 --dry-run
```

## 配置说明

在脚本顶部配置以下信息：

```python
HOSPITAL_ORG_ID = "医院组织 ID"
OFFICIAL_ACCOUNT_NAME = "公众号名称"
OFFICIAL_ACCOUNT_TYPE = "公众号类型"
APPID = "公众号 AppID"

OPENAPI_CONFIG = {
    "api_url": "微信 OpenAPI 地址",
    "app_key": "应用 Key",
    "app_secret": "应用 Secret",
    "wx_app_id": "目标公众号 AppID",
}

GROWINGIO_CONFIG = {
    "product_id": "GrowingIO 产品 ID",
    "data_source_id": "数据源 ID",
    "server_host": "数据接收地址",
    "event_name": "事件名称",
}
```

## 定时任务配置

添加到 crontab 每天 10 点运行：

```
0 10 * * * cd /home/openclaw/.openclaw/workspace/media-crawler && python3 wechat_fetch.py --days 30 >> /tmp/wechat-growio.log 2>&1
```

## 文件说明

| 文件 | 说明 |
|------|------|
| `wechat_fetch.py` | 主脚本 |
| `client.py` | 微信 OpenAPI 客户端 |
| `wechat_report_state.json` | 去重状态文件（本地） |
| `daily_report_*.json` | 上报数据文件（可删除） |
| `wechat_article_stats_*.csv` | CSV 汇总文件（可删除） |
