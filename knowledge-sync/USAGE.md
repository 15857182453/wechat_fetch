# 知识库使用指南

## ✅ 同步完成！

你的飞书多维表格已成功同步到 OpenClaw 知识库！

### 📊 同步结果

- **数据源**: 飞书多维表格
- **记录数**: 58 条
- **输出目录**: `/home/openclaw/.openclaw/workspace/knowledge/`
- **文件格式**: Markdown（带 Frontmatter 元数据）

---

## 📁 知识库结构

```
/home/openclaw/.openclaw/workspace/knowledge/
├── 打工人的无奈！医生：这种病，很多人都搞错了！.md
├── 这个部位总有异物感？！医生：早查！.md
├── 甲流阳性率超 45%！有人次次中招，有人完美避开，诀窍是…….md
└── ... (共 58 个文件)
```

每个文件包含：
- **Frontmatter 元数据**: 标题、发布日期、原文链接、封面图等
- **AI 摘要**: 自动生成的内容摘要
- **正文**: 完整的文章内容
- **原文链接**: 指向原始公众号文章

---

## 🚀 在 OpenClaw 中使用

### 方法 1：自动参考（推荐）

OpenClaw 会自动读取工作空间中的 Markdown 文件作为上下文。

在飞书/钉钉聊天时，直接提问即可：

```
你：肩周炎怎么治疗？
OpenClaw: 根据知识库中的文章，肩周炎的治疗方法包括...
```

### 方法 2：搜索特定内容

```bash
# 搜索包含关键词的文章
grep -l "肩周炎" /home/openclaw/.openclaw/workspace/knowledge/*.md

# 查看某篇文章
cat "/home/openclaw/.openclaw/workspace/knowledge/打工人的无奈！医生：这种病，很多人都搞错了！.md"
```

### 方法 3：使用 OpenClaw 命令

如果配置了知识库插件，可以用：
```
/知识库 搜索 肩周炎
```

---

## 🔄 定期同步

### 手动同步

```bash
cd /home/openclaw/.openclaw/workspace/knowledge-sync
node sync-final.js
```

### 自动同步（推荐）

配置 cron 定时任务，每天凌晨 2 点自动同步：

```bash
crontab -e
```

添加：
```bash
# 每天 2:00 同步飞书知识库
0 2 * * * cd /home/openclaw/.openclaw/workspace/knowledge-sync && /usr/bin/node sync-final.js >> /tmp/knowledge-sync.log 2>&1
```

### 使用 OpenClaw cron

也可以用 OpenClaw 的 cron 功能管理同步任务。

---

## 📝 自定义配置

### 修改字段映射

编辑 `sync-final.js` 中的 `recordToMarkdown` 函数：

```javascript
function recordToMarkdown(record, index) {
  const fields = record.fields;
  
  const title = fields['标题'] || `文档-${index + 1}`;
  const content = fields['文章内容'] || '';
  const summary = fields['文章总结'] || '';
  // ... 根据需要调整
}
```

### 修改输出目录

编辑 `CONFIG.output.dir`：

```javascript
const CONFIG = {
  output: {
    dir: '/your/custom/path/knowledge',
  },
};
```

---

## 🛠️ 故障排查

### 同步失败：403 Forbidden

- 检查应用权限是否配置正确
- 确认应用已重新发布
- 等待 3-5 分钟让权限生效

### 同步失败：404 Not Found

- 检查 App Token 和 Table ID 是否正确
- 确认多维表格对应用可见

### 数据为空

- 检查表格是否有数据
- 确认字段名称匹配

---

## 📈 统计信息

查看知识库统计：

```bash
cd /home/openclaw/.openclaw/workspace/knowledge
echo "文件总数：$(ls -1 *.md | wc -l)"
echo "总大小：$(du -sh . | cut -f1)"
```

---

## 💡 进阶用法

### 1. 知识库分类

可以按主题手动整理：

```bash
mkdir -p /home/openclaw/.openclaw/workspace/knowledge/骨科
mkdir -p /home/openclaw/.openclaw/workspace/knowledge/内科
mv *肩周炎*.md /home/openclaw/.openclaw/workspace/knowledge/骨科/
```

### 2. 添加标签

在 Frontmatter 中添加自定义标签：

```markdown
---
title: "文章标题"
tags: ["骨科", "肩周炎", "康复"]
---
```

### 3. 导出为其他格式

可以用 Pandoc 转换为 PDF、HTML 等：

```bash
pandoc "文章.md" -o "文章.pdf"
```

---

## 🎉 下一步

现在你可以：

1. **在聊天中使用** - OpenClaw 会自动参考知识库内容
2. **配置自动同步** - 保持知识库最新
3. **扩展知识库** - 添加更多数据源

有任何问题随时问我！🚀
