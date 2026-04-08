#!/bin/bash
# 自动化对账流程
# 使用前确保：1. 已下载 4 个源文件到 workspace；2. 流水test.xlsx 存在

set -e

WORKSPACE="/home/openclaw/.openclaw/workspace"
cd "$WORKSPACE"

echo "🔍 自动对账流程"
echo "==============="
echo "1. 检查文件..."
python3 -c "
from pathlib import Path
workspace = Path('$WORKSPACE')
required = [
    '业务对账统计明细*.xlsx',
    '订单明细表*.xlsx',
    '流水test.xlsx'
]
import glob
for pattern in required:
    files = list(workspace.glob(pattern))
    if not files:
        print(f'❌ 缺少: {pattern}')
        exit(1)
    print(f'✅ 找到: {files[0].name}')
print('✅ 所有文件就绪')
"

echo ""
echo "2. 运行自动化对账脚本..."
python3 业务对账透视汇总.py

echo ""
echo "3. 生成完成！"
ls -lh "流水-"*.xlsx | tail -3

echo ""
echo "💡 下一步：检查流水-*.xlsx 是否符合预期"
