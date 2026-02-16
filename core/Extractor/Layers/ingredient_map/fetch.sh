#!/bin/bash
# ingredient_map 資料擷取腳本
# 從現有產品萃取成分並透過 RxNorm API 標準化
#
# 用法：
#   ./fetch.sh --extract-all    # 萃取所有產品成分
#   ./fetch.sh --normalize      # 標準化成分（預設前 500 名）
#   ./fetch.sh --normalize --top 1000  # 標準化前 1000 名
#   ./fetch.sh --full           # 完整流程
#   ./fetch.sh --stats          # 顯示統計資訊
#
# 依賴：python3, requests

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../../.." && pwd)"

source "$PROJECT_ROOT/lib/args.sh"
source "$PROJECT_ROOT/lib/core.sh"

require_cmd python3

LAYER_NAME="ingredient_map"
RAW_DIR="$PROJECT_ROOT/docs/Extractor/$LAYER_NAME/raw"
LAST_FETCH_FILE="$RAW_DIR/.last_fetch"

mkdir -p "$RAW_DIR"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🧪 成分標準化擷取"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# 檢查 requests
python3 -c "import requests" 2>/dev/null || {
  echo "⚠️  缺少 requests，正在安裝..."
  pip3 install --quiet requests
}

# 執行 Python 腳本，傳遞所有參數
python3 "$PROJECT_ROOT/scripts/fetch_ingredient_map.py" "$@"

# 更新 .last_fetch
date +%Y-%m-%d > "$LAST_FETCH_FILE"

echo ""
echo "✅ Fetch completed: $LAYER_NAME"
