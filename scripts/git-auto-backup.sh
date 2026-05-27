#!/bin/bash
# Git 自动备份 — 每小时检查 workspace 是否有未提交的变更
# 如果有，自动 commit 但**不会 push**，作为安全网

set -euo pipefail

WORKSPACE="/home/openclaw/.openclaw/workspace"
LOG_FILE="$WORKSPACE/logs/git-auto-backup.log"

mkdir -p "$WORKSPACE/logs"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" >> "$LOG_FILE"
}

cd "$WORKSPACE"

# 检查是否有未提交的变更（不包括 untracked）
if git diff --quiet && git diff --cached --quiet; then
    log "无未提交的变更"
    exit 0
fi

# 自动 commit
git add .
git commit -m "auto-backup: $(date '+%Y-%m-%d %H:%M') 未提交变更自动备份"
log "已自动备份: $(git log --oneline -1)"
