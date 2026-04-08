#!/bin/bash
# 每日导入新流水 2026.xlsx
# 用法：./daily_import.sh

set -e

echo "=============================================="
echo "📊 每日对账数据导入"
echo "=============================================="
echo ""

WORKSPACE="/home/openclaw/.openclaw/workspace"
EXCEL_FILE="$WORKSPACE/新流水 2026.xlsx"

# 检查文件
if [ ! -f "$EXCEL_FILE" ]; then
    echo "❌ 错误：找不到 $EXCEL_FILE"
    echo "请确保文件已复制到工作区"
    exit 1
fi

echo "📁 文件：$EXCEL_FILE"
echo "📅 修改时间：$(stat -c '%y' "$EXCEL_FILE" | cut -d'.' -f1)"
echo ""

# 运行导入脚本（健壮版）
python3 "$WORKSPACE/import_duizhang_robust.py"

# 重启 Dashboard
echo ""
echo "🔄 重启 Dashboard..."
tmux kill-session -t dashboard 2>/dev/null || true
sleep 2
tmux new-session -d -s dashboard "streamlit run $WORKSPACE/dashboard_v3.py --server.port 8501 --server.address 0.0.0.0"
sleep 4

echo ""
echo "=============================================="
echo "✅ 导入完成！"
echo "=============================================="
echo ""
echo "🌐 Dashboard: http://localhost:8501"
echo ""
