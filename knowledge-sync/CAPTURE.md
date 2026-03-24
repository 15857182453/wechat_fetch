# 微信公众号文章抓取工具

## 📋 功能

批量抓取微信公众号文章内容，保存到飞书多维表格。

---

## 🚀 快速开始

### 1️⃣ 安装依赖

```bash
pip3 install requests beautifulsoup4
```

### 2️⃣ 准备文章链接

创建链接文件 `links.txt`，每行一个文章链接：

```txt
https://mp.weixin.qq.com/s/RWZ5lqpI-xvULskU0gUhUQ
https://mp.weixin.qq.com/s/xxx2
https://mp.weixin.qq.com/s/xxx3
```

### 3️⃣ 运行抓取

```bash
# 抓取并保存到飞书表格
python3 wechat-capture.py --links links.txt

# 抓取单篇文章
python3 wechat-capture.py --url "https://mp.weixin.qq.com/s/xxx"

# 仅抓取不保存（测试用）
python3 wechat-capture.py --links links.txt --dry-run
```

---

## 📊 输出

### 飞书多维表格

文章会自动保存到配置的多维表格中，字段包括：
- 标题
- 文章内容
- 文章总结
- 文章地址
- 封面地址
- 发表时间

### 本地文件

同时保存 `articles.json` 备份：

```json
[
  {
    "title": "文章标题",
    "content": "文章内容...",
    "summary": "文章摘要...",
    "url": "https://...",
    "publish_date": "2024-01-15",
    "author": "浙江省中医院"
  }
]
```

---

## 🔧 配置

编辑脚本顶部的 `FEISHU_CONFIG`：

```python
FEISHU_CONFIG = {
    'app_id': 'cli_a924dc7790625bd3',
    'app_secret': 'KfKqczGdsExKvXMq4m8HafrFc3WQx7t1',
    'app_token': 'BKABw6CJriaeYtkE9v9cjy4wneg',
    'table_id': 'tblhWgNl1uLYa4GL',
}
```

---

## 💡 获取文章链接

### 方法 1：从公众号历史消息

1. 打开"浙江省中医院"公众号
2. 查看历史消息
3. 复制文章链接

### 方法 2：从搜狗微信搜索

1. 访问 https://weixin.sogou.com/
2. 搜索"浙江省中医院"
3. 复制文章链接

### 方法 3：从现有数据

如果已有飞书表格，可以导出文章链接列。

---

## ⚠️ 注意事项

1. **抓取频率**：建议每次不超过 50 篇，避免被封
2. **时间间隔**：脚本已内置 1 秒延迟
3. **反爬机制**：微信公众号有反爬，可能偶尔失败
4. **合法性**：仅用于个人学习和研究

---

## 🔄 自动化方案

### 结合 Coze 工作流

```
Coze 工作流（自动发现新文章）
        ↓
  飞书多维表格
        ↓
OpenClaw 同步脚本
        ↓
    知识库
```

### 定时抓取

```bash
# 每天凌晨 3 点抓取
crontab -e

# 添加：
0 3 * * * cd /home/openclaw/.openclaw/workspace/knowledge-sync && python3 wechat-capture.py --links /path/to/new-links.txt >> /tmp/wechat-capture.log 2>&1
```

---

## 🛠️ 故障排查

### 抓取失败

- 检查链接是否正确
- 检查网络连接
- 增加延迟时间

### 保存失败

- 检查飞书 App ID/Secret
- 确认应用权限
- 查看错误日志

---

## 📞 需要帮助？

运行测试：
```bash
python3 wechat-capture.py --help
```

查看完整文档：
```bash
cat README.md
```

---

## 🎉 示例

### 抓取 10 篇最新文章

```bash
# 创建链接文件
cat > links.txt << EOF
https://mp.weixin.qq.com/s/link1
https://mp.weixin.qq.com/s/link2
...
EOF

# 运行抓取
python3 wechat-capture.py --links links.txt
```

### 从 Coze 工作流补充

如果 Coze 工作流漏了一些文章，可以用这个脚本补充抓取。
