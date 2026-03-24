#!/bin/bash
# 微信数据抓取 + GrowingIO 上报 + 钉钉通知
# 每天执行，报告结果到钉钉

# ========== 配置区 ==========
SCRIPT_DIR="/home/openclaw/.openclaw/workspace/media-crawler"
PYTHON_BIN="/usr/bin/python3"
DINGTALK_WEBHOOK="https://oapi.dingtalk.com/robot/send?access_token=84f55b1393f892b7859aca7692fc9e94a69280def75f72c90c1ebf40c9878e31"
# ===========================

# 日期配置（抓取昨天的数据）
YESTERDAY=$(date -d "yesterday" +%Y-%m-%d)

echo "🚀 开始执行微信数据抓取"
echo "📅 数据日期：$YESTERDAY"

cd "$SCRIPT_DIR"
OUTPUT=$($PYTHON_BIN wechat_fetch.py --start "$YESTERDAY" --end "$YESTERDAY" 2>&1)
EXIT_CODE=$?

echo "$OUTPUT"
echo ""

# 解析结果
SUCCESS_COUNT=$(echo "$OUTPUT" | grep -oP '成功 \K[0-9]+ 条' | head -1)
FAIL_COUNT=$(echo "$OUTPUT" | grep -oP '失败 \K[0-9]+ 条' | head -1)
TOTAL_COUNT=$(echo "$OUTPUT" | grep -oP '共 \K[0-9]+ 条记录' | head -1)

if [ $EXIT_CODE -eq 0 ]; then
    STATUS="✅ 执行成功"
else
    STATUS="❌ 执行失败"
fi

# 发送钉钉通知
if [ "$DINGTALK_WEBHOOK" != "YOUR_ACCESS_TOKEN_HERE" ]; then
    curl -s "$DINGTALK_WEBHOOK" -H 'Content-Type: application/json' -d "{
        \"msgtype\": \"markdown\",
        \"markdown\": {
            \"title\": \"【微信数据】执行报告\",
            \"text\": \"#### 【微信数据】$STATUS\\n\\n| 项目 | 值 |\\n|------|-----|\\n| 数据日期 | $YESTERDAY |\\n| 总记录数 | ${TOTAL_COUNT:-0} |\\n| 上报成功 | ${SUCCESS_COUNT:-0} |\\n| 上报失败 | ${FAIL_COUNT:-0} |\\n\\n时间: $(date '+%Y-%m-%d %H:%M:%S')\"
        }
    }" > /dev/null
    echo "📤 钉钉通知已发送"
fi

echo "✅ 完成"
