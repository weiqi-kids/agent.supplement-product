#!/bin/bash
# ddi 資料擷取腳本
# 從 PubMed 查詢 Drug-Drug Interaction 文獻
#
# 用法：
#   ./fetch.sh --all            # 擷取所有 DDI 文獻
#   ./fetch.sh --category anticoagulant  # 指定藥物類別
#   ./fetch.sh --limit 500      # 限制結果數
#
# 依賴：python3

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../../.." && pwd)"

source "$PROJECT_ROOT/lib/args.sh"
source "$PROJECT_ROOT/lib/core.sh"

require_cmd python3

LAYER_NAME="ddi"
RAW_DIR="$PROJECT_ROOT/docs/Extractor/$LAYER_NAME/raw"
LAST_FETCH_FILE="$RAW_DIR/.last_fetch"

mkdir -p "$RAW_DIR"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "💊 Drug-Drug Interaction 文獻擷取"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# 執行 Python 腳本，傳遞所有參數
python3 "$PROJECT_ROOT/scripts/fetch_interactions.py" --type ddi "$@"

# 更新 .last_fetch
date +%Y-%m-%d > "$LAST_FETCH_FILE"

echo ""
echo "✅ Fetch completed: $LAYER_NAME"
