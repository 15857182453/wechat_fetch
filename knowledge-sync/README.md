# 飞书多维表格 → OpenClaw 知识库同步工具

将飞书多维表格（Bitable）的数据自动同步为 OpenClaw 知识库（Markdown 文件）。

## 功能

- ✅ 自动读取飞书多维表格数据
- ✅ 转换为 Markdown 格式知识库
- ✅ 按分类自动组织目录结构
- ✅ 支持定时同步（cron）
- ✅ 保留元数据（标题、分类、标签、更新时间）

---

## 快速开始

### 1️⃣ 安装依赖

```bash
cd /home/openclaw/.openclaw/workspace/knowledge-sync
npm install
```

### 2️⃣ 配置飞书应用

#### 在飞书开放平台创建应用

1. 访问 [飞书开放平台](https://open.feishu.cn/)
2. 创建企业应用（或选择已有应用）
3. 获取 **App ID** 和 **App Secret**

#### 添加权限

在 **应用权限** 页面，添加以下权限：

```
bitable:app          - 读取多维表格
bitable:table        - 读取数据表
```

#### 发布应用

创建版本并发布，等待审核（企业应用通常自动通过）。

### 3️⃣ 获取多维表格信息

打开你的多维表格，URL 长这样：

```
https://xxx.feishu.cn/base/bascnXXXXXXXX?table=tblXXXXXXXX&view=vewXXXXXX
```

- **App Token**: `bascnXXXXXXXX`（base 后面的部分）
- **Table ID**: `tblXXXXXXXX`（table 参数值）

### 4️⃣ 配置同步脚本

```bash
# 复制配置模板
cp config.example.js config.js

# 编辑配置
nano config.js
```

填入你的配置：

```javascript
module.exports = {
  feishu: {
    appId: 'cli_xxxxxxxxxxxxx',
    appSecret: 'xxxxxxxxxxxxxxxxxxxxxxxx',
    domain: 'https://open.feishu.cn',
  },
  
  bitable: {
    appToken: 'bascnxxxxxxxxxxxxx',
    tableId: 'tblxxxxxxxxxxxxxx',
    fields: {
      title: '标题',
      content: '内容',
      category: '分类',
      tags: '标签',
    },
  },
  
  output: {
    dir: '/home/openclaw/.openclaw/workspace/knowledge',
    byCategory: true,
  },
};
```

### 5️⃣ 运行同步

```bash
npm run sync
```

同步完成后，知识库文件会保存在配置的输出目录。

---

## 表格结构示例

你的飞书多维表格应该包含以下列：

| 标题 | 内容 | 分类 | 标签 | 更新时间 |
|------|------|------|------|----------|
| 如何重置密码 | 重置密码的步骤如下... | 账号管理 | 密码，安全 | 2024-01-15 |
| 产品定价说明 | 我们的产品分为三个版本... | 产品信息 | 价格，版本 | 2024-01-14 |

**必填字段**：标题、内容  
**可选字段**：分类、标签、更新时间

---

## 输出文件结构

同步后的知识库文件结构：

```
knowledge/
├── 账号管理/
│   ├── 如何重置密码.md
│   └── 账号安全问题.md
├── 产品信息/
│   ├── 产品定价说明.md
│   └── 功能对比表.md
└── 未分类/
    └── 其他文档.md
```

每个 Markdown 文件包含 Frontmatter 元数据：

```markdown
---
title: "如何重置密码"
category: "账号管理"
tags: ["密码", "安全"]
updatedAt: "2024-01-15T10:30:00.000Z"
source: "飞书多维表格"
---

# 如何重置密码

重置密码的步骤如下...
```

---

## 定时同步

### 配置 cron 定时任务

```bash
crontab -e
```

添加每天凌晨 2 点同步的任务：

```bash
# 每天 2:00 同步飞书知识库
0 2 * * * cd /home/openclaw/.openclaw/workspace/knowledge-sync && /usr/bin/node feishu-bitable-sync.js >> /tmp/feishu-sync.log 2>&1
```

### 或使用 OpenClaw cron

可以用 OpenClaw 的 cron 功能管理同步任务。

---

## 在 OpenClaw 中使用知识库

### 方法 1：让 OpenClaw 自动读取

OpenClaw 会自动读取工作空间中的 Markdown 文件作为上下文。确保：

1. 知识库目录在 `SOUL.md` 或 `AGENTS.md` 中配置
2. 文件放在工作空间内（如 `knowledge/` 目录）

### 方法 2：在聊天时引用

在飞书/钉钉聊天时，OpenClaw 会自动参考知识库内容回答问题。

示例对话：
```
用户：如何重置密码？
OpenClaw: 根据知识库中的文档，重置密码的步骤如下...
```

---

## 故障排查

### 获取 Token 失败

- 检查 App ID 和 App Secret 是否正确
- 确认应用已发布
- 检查权限是否已添加

### 获取数据失败

- 检查 App Token 和 Table ID 是否正确
- 确认机器人/应用有表格访问权限
- 检查表格是否可见

### 字段映射错误

- 检查 `config.js` 中的字段名是否与表格列名完全一致
- 注意中文字段名要完全匹配

---

## 高级配置

### 自定义字段映射

如果你的表格列名不同，修改 `fields` 配置：

```javascript
fields: {
  title: '问题标题',    // 你的列名
  content: '详细解答',  // 你的列名
  category: '问题分类',
  tags: '关键字',
},
```

### 不使用分类目录

```javascript
output: {
  byCategory: false,  // 所有文件放在同一目录
},
```

### 使用记录 ID 作为文件名

```javascript
output: {
  filenameFormat: 'id',  // 用 record_id 而不是标题
},
```

---

## 许可证

MIT
