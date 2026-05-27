# Git 工作规范

**仓库**: https://github.com/15857182453/wechat_fetch  
**分支**: master（单分支）  
**最后更新**: 2026-05-27

---

## 核心原则

### 1. 不要复制文件来保留版本

```
❌ dashboard_v4.py → dashboard_v4_v2.py → dashboard_v4_fixed.py → dashboard_v4_redesign.py
✅ git commit → git push
```

- 想保留历史版本？用 `git log` 和 `git show <commit>` 查看
- 想实验新想法？先 `git commit` 当前版本，然后在新分支上改，或改完再 commit

### 2. 改代码前先 commit 当前状态

```bash
git add dashboard_v4.py
git commit -m "feat: 备份当前状态，准备修改 XXX"
# 然后开始改
```

### 3. 改完测试 OK 再提交

```bash
# 测试通过后
git add dashboard_v4.py
git commit -m "fix: 修复 XXX 问题"
git push
```

---

## Commit Message 格式

```
type: 简短描述
```

| type | 含义 | 示例 |
|------|------|------|
| `feat` | 新功能 | `feat: 新增 Tab 11 用户行为分析` |
| `fix` | Bug 修复 | `fix: 修复月环比计算排除空数据` |
| `docs` | 文档 | `docs: 更新 MEMORY.md 导入流程` |
| `refactor` | 重构 | `refactor: 统一数据加载函数` |
| `chore` | 杂项 | `chore: 更新 .gitignore` |
| `📝` | 记忆更新 | `📝 更新记忆: 新增踩坑记录` |
| `🗂️` | 整理 | `🗂️ 整理项目结构` |

---

## 目录结构

```
workspace/
├── dashboard_v4.py           ← 主版本（唯一活跃的 Dashboard）
├── import_duizhang_*.py      ← 数据导入（主用）
├── refresh_prescription_summary.py
├── auth_guard.py
├── archive/                  ← 废弃文件归档（不进 commit 历史）
├── quant/                    ← A股量化交易
├── zentao-dashboard/         ← 禅道质量看板
├── memory/                   ← 本地记忆（不进 git）
├── logs/                     ← 运行日志（不进 git）
└── _memory_sync/             ← 自动同步目录（不进 git）
```

---

## 不被 git 跟踪的文件

| 类型 | 规则 | 原因 |
|------|------|------|
| 数据库 | `*.db` | 体积大、本地生成 |
| Excel | `*.xlsx` | 敏感数据 |
| PPT/图片 | `*.pptx *.png *.jpg` | 生成产物 |
| 备份 | `*.bak* *_backup*` | 进 archive/ |
| 嵌套 git | `MediaCrawler/.git/` 等 | 独立仓库 |
| 日志 | `*.log` | 运行时生成 |
| 记忆 | `memory/*.md` | 本地同步 |

---

## 自动备份（安全网）

**每小时自动 commit** 未提交的变更：`scripts/git-auto-backup.sh`

- 只 commit，**不 push**
- commit message: `auto-backup: YYYY-MM-DD HH:MM 未提交变更自动备份`
- 日志: `logs/git-auto-backup.log`
- 如果你忘记提交，最多丢一小时的改动（实际上不会丢，会自动备份）

## 自动同步

- **sync.sh**: 每小时同步 memory 到 `openclaw-memory` 仓库
- **不会自动提交代码变更**，代码必须手动 commit

---

## 常用命令

```bash
# 查看修改了哪些文件
git status

# 查看最近提交
git log --oneline -10

# 查看某个文件的修改历史
git log --follow dashboard_v4.py

# 查看某次提交的具体改动
git show <commit-hash>

# 对比工作区和最近提交的差异
git diff dashboard_v4.py

# 回退某个文件到最近一次提交的状态
git checkout -- dashboard_v4.py

# 一键提交
git add . && git commit -m "fix: 描述" && git push
```

---

## 红线

1. **不要 `DELETE FROM` 清表** — 增量导入
2. **不要直接改 `dashboard_v4.py` 不 commit** — 先 commit 再改
3. **不要创建 `*_v2.py` `*_backup.py`** — 用 git 管理版本
4. **不要 `git clean -fd`** — 会删除 untracked 文件
5. **不要 `git reset --hard`** — 会丢失已提交代码
