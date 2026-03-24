#!/bin/bash
# 钉钉机器人 Webhook 通知脚本
# 用法：./dingtalk-notify.sh "消息内容"

# ========== 配置区 ==========
DINGTALK_WEBHOOK="https://oapi.dingtalk.com/robot/send?access_token=84f55b1393f892b7859aca7692fc9e94a69280def75f72c90c1ebf40c9878e31"
KEYWORD="微信数据"
# ===========================

MESSAGE="${1:-OpenClaw: 测试消息}"

# 检查是否有消息参数
if [ -z "$1" ]; then
    echo "用法：$0 \"消息内容\""
    echo "示例：$0 \"服务器状态正常\""
    exit 1
fi

# 发送消息（自动添加关键词）
echo "发送消息：$KEYWORD: $MESSAGE"
RESPONSE=$(curl -s "$DINGTALK_WEBHOOK" \
  -H 'Content-Type: application/json' \
  -d "{
    \"msgtype\": \"text\",
    \"text\": {
      \"content\": \"$KEYWORD: $MESSAGE\"
    }
  }")

echo "$RESPONSE"
echo ""
echo "✓ 消息已发送"
