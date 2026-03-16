#!/bin/bash
# 微信文章数据抓取 + GrowingIO 上报 + 钉钉通知
# 每天自动执行，执行后发送结果到钉钉

# ========== 配置区 ==========
SCRIPT_DIR="/home/openclaw/.openclaw/workspace/media-crawler"
PYTHON_BIN="/usr/bin/python3"
LOG_FILE="/tmp/wechat-growio.log"
DINGTALK_WEBHOOK="https://oapi.dingtalk.com/robot/send?access_token=84f55b1393f892b7859aca7692fc9e94a69280def75f72c90c1ebf40c9878e31"
# ===========================

# 日期配置（抓取昨天的数据）
YESTERDAY=$(date -d "yesterday" +%Y-%m-%d)

echo "🚀 开始执行微信文章数据抓取任务"
echo "📅 数据日期：$YESTERDAY"
echo "⏰ 执行时间：$(date '+%Y-%m-%d %H:%M:%S')"
echo ""

# 执行抓取脚本
cd "$SCRIPT_DIR"
OUTPUT=$($PYTHON_BIN wechat_fetch.py --start "$YESTERDAY" --end "$YESTERDAY" 2>&1)
EXIT_CODE=$?

echo "$OUTPUT" | tee "$LOG_FILE"
echo ""

# 解析结果
SUCCESS_COUNT=$(echo "$OUTPUT" | grep -oP '成功 \K[0-9]+ 条' | head -1)
FAIL_COUNT=$(echo "$OUTPUT" | grep -oP '失败 \K[0-9]+ 条' | head -1)
TOTAL_COUNT=$(echo "$OUTPUT" | grep -oP '共 \K[0-9]+ 条记录' | head -1)

# 构建钉钉消息
if [ $EXIT_CODE -eq 0 ]; then
    STATUS="✅ 执行成功"
    STATUS_EMOJI="✅"
else
    STATUS="❌ 执行失败"
    STATUS_EMOJI="❌"
fi

# 发送钉钉通知
if [ "$DINGTALK_WEBHOOK" != "YOUR_ACCESS_TOKEN_HERE" ]; then
    # 发送 Markdown 消息到钉钉，确保包含关键词【微信数据】
    LOG_PATH="/tmp/wechat-growio.log"
    curl -s "$DINGTALK_WEBHOOK" \
      -H 'Content-Type: application/json' \
      -d "{
        \"msgtype\": \"markdown\",
        \"markdown\": {
          \"title\": \"【微信数据】执行报告\",
          \"text\": \"#### 【微信数据】执行报告\\n\\n**${STATUS}**\\n\\n| 项目 | 值 |\\n|------|-----|\\n| 数据日期 | ${YESTERDAY} |\\n| 执行时间 | $(date '+%Y-%m-%d %H:%M:%S') |\\n| 总记录数 | ${TOTAL_COUNT:-0} |\\n| 上报成功 | ${SUCCESS_COUNT:-0} |\\n| 上报失败 | ${FAIL_COUNT:-0} |\\n\\n📁 日志：${LOG_PATH}\"
        }
      }" > /dev/null
    
    echo "📤 钉钉通知已发送"
else
    echo "⚠️  钉钉 Webhook 未配置，跳过通知"
    echo "   请编辑 $0 配置 DINGTALK_WEBHOOK"
fi

echo ""
echo "✅ 任务完成"
