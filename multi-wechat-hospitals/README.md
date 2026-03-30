# 多医院微信公众号数据抓取系统

通过配置文件批量处理多个医院的微信公众号文章数据抓取并上传到 GrowingIO。

## 功能特点

- ✅ **配置文件管理**：YAML 格式配置文件，易于维护
- ✅ **多医院支持**：同时管理多家医院的公众号账号
- ✅ **日志隔离**：每家医院独立的日志和数据保存目录
- ✅ **去重机制**：自动过滤已上报的数据，避免重复
- ✅ **钉钉通知**：每家医院可独立发送钉钉通知
- ✅ **灵活执行**：可批量执行或单独执行某家医院
- ✅ **日期范围可配置**：支持指定日期范围或最近 N 天

## 目录结构

```
multi-wechat-hospitals/
├── hospitals.yml              # 医院配置文件（YAML格式）
├── run_hospitals.py           # 批量执行脚本
├── hospitals/                 # 每个医院独立目录
│   ├── hospital_1/           # 医院1
│   │   └── logs/             # 日志目录
│   │       ├── hospital_name_daily_report_*.json
│   │       ├── hospital_name_wechat_article_stats_*.csv
│   │       └── wechat_report_state.json
│   ├── hospital_2/           # 医院2
│   │   └── logs/
│   └── hospital_3/           # 医院3
│       └── logs/
└── templates/
    └── wechat_fetch_hospital.py  # 单医院执行模板
```

## 配置文件说明

### hospitals.yml

```yaml
hospitals:
  # 医院1
  - name: "杭州师范大学附属医院"
    org_id: "1005657"
    account_name: "杭州师范大学附属医院"
    account_type: "订阅号"
    appid: "wxb946acbb0c6d9de6"
    openapi:
      api_url: "https://openapi.ngarihealth.com/openapi/gateway"
      app_key: "ngari5e93bcd7347bcc28"
      app_secret: "347bcc28d2e9d26b"
      wx_app_id: "wx530c8ee57cd2fa6e"
    growingio:
      product_id: "98b451a0ec02c41a"
      data_source_id: "b7f6d83f9c9734b6"
      server_host: "https://ngari-collect.fenxiti.com/"
      event_name: "OA_officialNewsDailyData2"
    output_dir: "hospitals/hospital_1"
    dingtalk:
      enabled: true
      webhook_url: "https://oapi.dingtalk.com/robot/send?access_token=XXXXXXXXXX"

  # 医院2...
  - name: "医院2名称"
    # ... 其他配置

# 全局设置
settings:
  default_date_range: 7
  log_level: "INFO"
```

### 配置项说明

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| name | string | ✅ | 医院名称 |
| org_id | string | ✅ | 医院组织 ID |
| account_name | string | ✅ | 公众号名称 |
| account_type | string | ✅ | 公众号类型（订阅号/服务号） |
| appid | string | ✅ | 微信 AppID |
| openapi | object | ✅ | OpenAPI 配置 |
| growingio | object | ✅ | GrowingIO 配置 |
| output_dir | string | ✅ | 输出目录（相对于 workspace） |
| dingtalk.enabled | boolean | ❌ | 是否启用钉钉通知 |
| dingtalk.webhook_url | string | ❌ | 钉钉机器人 webhook URL |

## 使用方法

### 1. 修改配置文件

编辑 `hospitals/hospitals.yml`，填入各医院的正确配置信息。

### 2. 执行抓取任务

#### 批量执行所有医院（默认最近7天）
```bash
cd /home/openclaw/.openclaw/workspace
python3 scripts/run_multi_hospitals.py
```

或使用 bash 脚本：
```bash
./scripts/run_multi_hospitals.sh
```

#### 指定医院执行
```bash
python3 scripts/run_multi_hospitals.py --hospital "杭州师范大学附属医院"
```

#### 指定日期范围
```bash
python3 scripts/run_multi_hospitals.py --start 2026-03-01 --end 2026-03-30
```

#### 指定最近 N 天
```bash
python3 scripts/run_multi_hospitals.py --days 14
```

#### Debug 模式
```bash
python3 scripts/run_multi_hospitals.py --debug
```

#### Dry-run 模式（只抓取不上传）
```bash
python3 scripts/run_multi_hospitals.py --dry-run
```

### 3. 输出文件

每家医院的输出文件组织在各自的 `logs/` 目录下：

```
hospitals/hospital_1/logs/
├── hospital_1_daily_report_20260330_20260323_20260330.json
├── hospital_1_wechat_article_stats_20260330_20260323_20260330.csv
└── wechat_report_state.json
```

- **JSON 文件**：上报到 GrowingIO 的事件数据
- **CSV 文件**：汇总数据，可用 Excel 打开查看
- **状态文件**：记录已上报的数据，用于去重

### 4. 钉钉通知

每家医院抓取完成后会发送钉钉通知（如果配置了 webhook）：

```
📊 杭州师范大学附属医院 数据抓取完成

## 🏥 医院名称
杭州师范大学附属医院

## 📢 微信数据
📅 抓取日期范围：03/23 - 03/30
📝 新增数据条数：42
✅ 上报成功：42
❌ 上报失败：0
⏱️ 执行时间：2026年03月30日
```

## Cron 定时任务

### 每天早上9点执行所有医院
```bash
# 编辑 crontab
crontab -e

# 添加任务（每天9:00执行）
0 9 * * * cd /home/openclaw/.openclaw/workspace && python3 scripts/run_multi_hospitals.py >> logs/multi_hospitals.log 2>&1
```

### 每天早上9:30执行指定医院
```bash
30 9 * * * cd /home/openclaw/.openclaw/workspace && python3 scripts/run_multi_hospitals.py --hospital "医院1名称" >> logs/hospital_1.log 2>&1
```

### 每周一开始执行上周数据（补充）
```bash
# 每周一早上8:00执行上周数据（假设上周一到周日）
0 8 * * 1 cd /home/openclaw/.openclaw/workspace && python3 scripts/run_multi_hospitals.py --days 7 >> logs/weekly.log 2>&1
```

## 注意事项

⚠️ **需要手动开启 VPN** 才能上传到 GrowingIO

### 重要提示

1. **配置文件安全**：配置文件中包含敏感信息（如 `app_secret`、`webhook_url`），请妥善保管
2. **日志隔离**：确保每家医院的 `output_dir` 不同，避免数据混淆
3. **去重机制**：重复执行不会重复上报，状态记录在 `wechat_report_state.json`
4. **Token 失效**：如果 Token 失效，请检查 `app_key` 和 `app_secret` 是否正确
5. **网络限制**： GrowingIO 上报需要网络访问权限，确保服务器能够访问 `ngari-collect.fenxiti.com`

## 故障排查

### 问题：获取 Token 失败

**解决方案**：
- 检查 `app_key` 和 `app_secret` 是否正确
- 确认 `wx_app_id` 是目标公众号的 AppID
- 检查网络连接

### 问题：重复数据未被过滤

**解决方案**：
- 检查 `logs/wechat_report_state.json` 文件是否存在
- 如果文件损坏，删除后会自动重置（但会重新上报之前的数据）

### 问题：钉钉通知未发送

**解决方案**：
- 检查 `dingtalk.enabled` 是否为 `true`
- 确认 `webhook_url` 正确且未过期
- 检查网络是否能访问钉钉服务器

## 扩展功能

### 添加新医院

1. 在 `hospitals.yml` 的 `hospitals` 列表中添加新医院配置
2. 设置唯一的 `output_dir`
3. 填入该医院的 OpenAPI 和 GrowingIO 配置
4. （可选）配置钉钉通知 webhook

### 自定义钉钉通知

如需为不同医院配置不同的钉钉 webhook，只需在对应医院的 `dingtalk.webhook_url` 中填入即可。

## 技术支持

如有问题，请检查：
1. Python 版本：`python3 --version`（推荐 >= 3.8）
2. 依赖包：`pip install requests pyyaml`
3. 日志文件：检查 `logs/` 目录下的详细日志