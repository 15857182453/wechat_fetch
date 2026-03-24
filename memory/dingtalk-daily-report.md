# 钉钉日报配置

## 当前状态

- ⚠️ **Webhook 未配置** - 脚本中仍是占位符 URL
- ⚠️ **Cron 任务未配置** - 没有自动发送任务

## 需要完成的配置

### 1️⃣ 配置钉钉 Webhook URL

编辑脚本 `/home/openclaw/.openclaw/workspace/scripts/dingtalk-notify.sh`：

```bash
nano /home/openclaw/.openclaw/workspace/scripts/dingtalk-notify.sh
```

替换这一行：
```bash
DINGTALK_WEBHOOK="https://oapi.dingtalk.com/robot/send?access_token=YOUR_ACCESS_TOKEN_HERE"
```

改成你的真实 Webhook URL（从钉钉群机器人获取）。

### 2️⃣ 测试发送

```bash
cd /home/openclaw/.openclaw/workspace
./scripts/dingtalk-notify.sh "测试消息 - 日报配置"
```

### 3️⃣ 配置自动发送（可选）

编辑 crontab：
```bash
crontab -e
```

添加每天下午 6 点发送日报的任务：
```bash
# 每天 18:00 发送日报
0 18 * * * /home/openclaw/.openclaw/workspace/scripts/dingtalk-notify.sh "📋 日报提醒：请提交今日工作总结"
```

---

## 日报模板

可以在这里自定义日报内容格式：

### 简单文本
```
OpenClaw: 📋 日报提醒
请各位同事提交今日工作总结，谢谢！
```

### Markdown 格式（如果钉钉机器人支持）
```
## 📋 日报提醒

**发送时间**: 每天 18:00
**截止时间**: 当天 20:00

请提交：
- 今日完成工作
- 遇到的问题
- 明日计划
```

---

## 待办事项

- [ ] 填入真实的钉钉 Webhook URL
- [ ] 测试发送功能
- [ ] 配置 cron 自动任务（可选）
- [ ] 自定义日报内容格式
