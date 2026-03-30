#!/bin/bash
# 多医院微信公众号数据抓取批处理脚本
# 使用前请先修改配置文件 hospitals/hospitals.yml

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# 检查 Python3 是否可用
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 未找到"
    exit 1
fi

# 解析参数
HOSPITAL_NAME=""
DATE_RANGE=7
START_DATE=""
END_DATE=""
DRY_RUN=""
DEBUG=""
CONFIG_FILE="hospitals.yml"

while [[ $# -gt 0 ]]; do
    case $1 in
        --hospital)
            HOSPITAL_NAME="$2"
            shift 2
            ;;
        --days)
            DATE_RANGE="$2"
            shift 2
            ;;
        --start)
            START_DATE="$2"
            shift 2
            ;;
        --end)
            END_DATE="$2"
            shift 2
            ;;
        --dry-run)
            DRY_RUN="--dry-run"
            shift
            ;;
        --debug)
            DEBUG="--debug"
            shift
            ;;
        --config)
            CONFIG_FILE="$2"
            shift 2
            ;;
        *)
            shift
            ;;
    esac
done

# 构建 Python 命令
PYTHON_CMD="python3 $(pwd)/run_hospitals.py"
PYTHON_CMD="$PYTHON_CMD --config $CONFIG_FILE"
PYTHON_CMD="$PYTHON_CMD --days $DATE_RANGE"

if [ -n "$START_DATE" ]; then
    PYTHON_CMD="$PYTHON_CMD --start $START_DATE"
fi

if [ -n "$END_DATE" ]; then
    PYTHON_CMD="$PYTHON_CMD --end $END_DATE"
fi

if [ -n "$DRY_RUN" ]; then
    PYTHON_CMD="$PYTHON_CMD --dry-run"
fi

if [ -n "$DEBUG" ]; then
    PYTHON_CMD="$PYTHON_CMD --debug"
fi

if [ -n "$HOSPITAL_NAME" ]; then
    PYTHON_CMD="$PYTHON_CMD --hospital \"$HOSPITAL_NAME\""
fi

echo "🚀 开始执行多医院数据抓取..."
echo "📅 日期范围: 最近 $DATE_RANGE 天"
if [ -n "$START_DATE" ] && [ -n "$END_DATE" ]; then
    echo "📅 日期范围: $START_DATE 至 $END_DATE"
fi
if [ -n "$HOSPITAL_NAME" ]; then
    echo "🏥 指定医院: $HOSPITAL_NAME"
fi
echo ""

# 执行
eval $PYTHON_CMD

# 检查退出状态
if [ $? -eq 0 ]; then
    echo ""
    echo "✅ 所有任务执行完成"
else
    echo ""
    echo "❌ 执行过程中出现错误"
    exit 1
fi
