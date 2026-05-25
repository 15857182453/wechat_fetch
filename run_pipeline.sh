#!/bin/bash
# 禅道数据自动化流水线
# 用法: bash run_pipeline.sh [--sync] [--assemble] [--dashboard]
# 默认: 执行全流程（同步 → 组装 → 启动看板）

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

RUN_SYNC=true
RUN_ASSEMBLE=true
RUN_DASHBOARD=false

for arg in "$@"; do
    case "$arg" in
        --sync)     RUN_SYNC=true; RUN_ASSEMBLE=false; RUN_DASHBOARD=false ;;
        --assemble) RUN_SYNC=false; RUN_ASSEMBLE=true; RUN_DASHBOARD=false ;;
        --dashboard) RUN_SYNC=false; RUN_ASSEMBLE=false; RUN_DASHBOARD=true ;;
    esac
done

echo "============================================"
echo "🚀 禅道数据自动化流水线"
echo "============================================"

if $RUN_SYNC; then
    echo ""
    echo "📥 Step 1: 数据同步..."
    python3 sync_data.py
    echo "✅ 同步完成"
fi

if $RUN_ASSEMBLE; then
    echo ""
    echo "📦 Step 2: 数据组装..."
    python3 assemble_matrix.py
    echo "✅ 组装完成"
fi

if $RUN_DASHBOARD; then
    echo ""
    echo "📊 Step 3: 启动禅道看板..."
    streamlit run app_zentao.py --server.port 8503
fi

if ! $RUN_DASHBOARD; then
    echo ""
    echo "🎉 流水线完成！运行以下命令启动看板："
    echo "   streamlit run app_zentao.py --server.port 8503"
fi
