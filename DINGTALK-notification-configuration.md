# 钉钉Webhook通知配置

## 问题说明

wechat_fetch.py 执行后没有钉钉通知的原因是：**脚本没有集成钉钉Webhook通知功能**。

## 当前状态

- ✅ `scripts/dingtalk-notify.sh` - 通用钉钉通知脚本（已配置Webhook URL）
- ✅ wechat_fetch.py - 数据抓取脚本（暂无通知功能）
- ❌ Cron任务 - 未配置自动通知

## 快速解决方案

### 方案1：修改Cron任务，添加通知（推荐）✅ **已配置**

编辑crontab：
```bash
crontab -e
```

添加以下任务（在原命令后添加通知）：
```bash
# 每天9:00执行微信文章数据抓取并发送通知
0 9 * * * cd /home/openclaw/.openclaw/workspace/media-crawler && python3 wechat_fetch.py --days 1 >> /tmp/wechat-growio.log 2>&1 && /home/openclaw/.openclaw/workspace/scripts/dingtalk-notify.sh "✅ 微信文章数据抓取完成（\$(date +\%Y-\%m-\%d)）- 抓取 \$count 条记录"
```

**当前Cron配置**：已添加到 crontab -l

### 方案2：修改wechat_fetch.py，集成通知功能

在脚本末尾添加钉威通知调用：
```python
# 在 main() 函数的末尾，保存数据之后添加：
import os

# 保存数据后发送通知
Notification_count = len(all_events)
if Notification_count > 0:
    os.system(f'bash {args.output}/../scripts/dingtalk-notify.sh "✅ 抓取完成：{Notification_count} 条文章数据已上报 GrowingIO"')
```

## 钉钉机器人关键词配置

- **关键词**: `微信数据`
- **消息格式**: 自动在消息前添加关键词，例如：`微信数据: ✅ 抓取完成`

如果需要修改关键词，请编辑脚本中的 `KEYWORD` 变量。

---

## 测试通知

```bash
# 测试通知脚本
cd /home/openclaw/.openclaw/workspace
./scripts/dingtalk-notify.sh "✅ 测试消息：钉钉通知配置成功"
```

## 预期效果

配置完成后，每天9:00执行任务时会：
1. 抓取微信文章数据
2. 保存到 `/tmp/wechat-growio.log`
3. 发送钉钉通知到配置的群

---

**注意**：当前钉钉Webhook URL 已在脚本中配置，无需再次修改。
