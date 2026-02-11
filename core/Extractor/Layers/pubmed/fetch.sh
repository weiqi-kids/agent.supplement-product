#!/bin/bash
# pubmed 資料擷取腳本
# 從 NCBI E-utilities API 查詢主題相關學術文獻
#
# 用法：
#   ./fetch.sh --topic fish-oil     # 擷取特定主題
#   ./fetch.sh --all                # 擷取所有主題
#   ./fetch.sh --topic exosomes --limit 100  # 限制結果數
#   ./fetch.sh --list               # 列出可用主題
#
# 依賴：python3, pyyaml
# 建議設定 NCBI_API_KEY 提高速率

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../../.." && pwd)"

source "$PROJECT_ROOT/lib/args.sh"
source "$PROJECT_ROOT/lib/core.sh"

require_cmd python3

LAYER_NAME="pubmed"
RAW_DIR="$PROJECT_ROOT/docs/Extractor/$LAYER_NAME/raw"
LAST_FETCH_FILE="$RAW_DIR/.last_fetch"

mkdir -p "$RAW_DIR"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📚 PubMed 文獻擷取"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# 檢查 pyyaml
python3 -c "import yaml" 2>/dev/null || {
  echo "⚠️  缺少 pyyaml，正在安裝..."
  pip3 install --quiet pyyaml
}

# 執行 Python 腳本，傳遞所有參數
python3 "$PROJECT_ROOT/scripts/fetch_pubmed.py" "$@"

# 更新 .last_fetch
date +%Y-%m-%d > "$LAST_FETCH_FILE"

echo ""
echo "✅ Fetch completed: $LAYER_NAME"
