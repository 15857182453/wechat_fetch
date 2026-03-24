# 钉钉桥接服务器

将钉钉群消息转发给 OpenClaw，实现双向通信。

## 功能

- ✅ 接收钉钉群消息（包括@机器人）
- ✅ 转发给 OpenClaw 处理
- ✅ 发送回复回钉钉群

## 快速开始

### 1. 安装依赖

```bash
cd /home/openclaw/.openclaw/workspace/dingtalk-bridge
npm install
```

### 2. 配置

```bash
# 复制配置模板
cp config.example.js config.js

# 编辑配置
nano config.js
```

填入你的钉钉应用配置（见下方"获取钉钉配置"）。

### 3. 启动服务器

```bash
npm start
```

### 4. 配置钉钉回调 URL

在钉钉开放平台 → 事件订阅 → 回调配置：

```
http://YOUR_PUBLIC_IP:3001/dingtalk/callback
```

**注意**：需要公网 IP 或使用内网穿透工具（如 ngrok）。

---

## 获取钉钉配置

### 步骤 1：创建企业内部应用

1. 登录 [钉钉开放平台](https://open-dev.dingtalk.com/)
2. 进入 **应用开发** → **企业内部开发**
3. 点击 **创建应用**
4. 填写应用名称、图标等

### 步骤 2：获取凭证

在应用管理页面：
- **AppKey**：直接复制
- **AppSecret**：点击查看并复制

### 步骤 3：配置机器人

1. 在应用管理 → **添加机器人能力**
2. 设置机器人名字（如 "OpenClaw 助手"）
3. 配置 **消息接收模式**：
   - 勾选 "接收消息"
   - 设置回调 URL（你的服务器地址）

### 步骤 4：配置事件订阅

1. 在应用管理 → **事件订阅**
2. 设置回调 URL 和 Token
3. 订阅事件：
   - `im/chat/message/read`
   - `im/chat/message/send`
   - 或直接用机器人消息接收

### 步骤 5：发布应用

1. 在应用管理 → **版本管理与发布**
2. 创建版本并发布
3. 将机器人添加到钉钉群

---

## 内网穿透（开发测试用）

如果你没有公网 IP，可以用 ngrok：

```bash
# 安装 ngrok
npm install -g ngrok

# 启动穿透
ngrok http 3001
```

然后把 ngrok 给的地址（如 `https://xxx.ngrok.io`）配置到钉钉回调 URL。

---

## 测试

### 测试消息接收

在钉钉群@机器人并发送消息：
```
@OpenClaw 助手 今天天气怎么样？
```

查看服务器日志，应该能看到消息被接收并转发。

### 测试 OpenClaw 集成

确保 OpenClaw 的 API 端点能接收并处理消息。

---

## 高级功能

### 支持的消息类型

- 文本消息 ✅
- Markdown 消息 ✅
- 链接消息 🚧
- 卡片消息 🚧

### 安全配置

- ✅ 签名验证
- ✅ AES 加密（可选）
- ✅ IP 白名单（钉钉端配置）

---

## 发送消息到钉钉群

使用脚本 `scripts/dingtalk-notify.sh`：

```bash
# 基本用法
./scripts/dingtalk-notify.sh "你的消息内容"

# 示例
./scripts/dingtalk-notify.sh "✅ 微信文章数据抓取完成"
```

**注意**：如果钉钉机器人配置了关键词过滤，消息内容必须包含该关键词。遇到 `errcode:310000 "关键词不匹配"` 错误时，请：
1. 查看机器人设置中的关键词配置
2. 在消息中包含该关键词
3. 或移除机器人关键词限制

详细配置说明见：`DINGTALK-notification-configuration.md`

---

## 故障排查

### 收不到消息？

1. 检查钉钉回调 URL 是否公网可访问
2. 检查签名验证是否通过
3. 查看服务器日志

### 回复发送失败？

1. 检查 access_token 是否有效
2. 检查 agentId 是否正确
3. 确认机器人已添加到群

### 发送消息到群失败？

1. 检查 webhook URL 是否正确
2. 检查消息内容是否包含机器人配置的关键词
3. 确认机器人已添加到目标群

---

## 许可证

MIT
