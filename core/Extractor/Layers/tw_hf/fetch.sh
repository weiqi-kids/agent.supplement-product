#!/bin/bash
# tw_hf 資料擷取腳本
# 從衛福部食藥署「健康食品資料集」API 下載資料
#
# 用法：
#   ./fetch.sh              # 下載並轉換為 JSONL
#   ./fetch.sh --limit 10   # 限制筆數（測試用）
#
# 依賴：python3, curl
# 無需 API Key

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../../.." && pwd)"

source "$PROJECT_ROOT/lib/args.sh"
source "$PROJECT_ROOT/lib/core.sh"

require_cmd python3
require_cmd curl

LAYER_NAME="tw_hf"
RAW_DIR="$PROJECT_ROOT/docs/Extractor/$LAYER_NAME/raw"
LAST_FETCH_FILE="$RAW_DIR/.last_fetch"

# 衛福部食藥署健康食品資料集 API (JSON 格式)
API_URL="http://data.fda.gov.tw/data/opendata/export/19/json"

mkdir -p "$RAW_DIR"

# === 解析參數 ===
parse_args "$@"
arg_optional "limit" FETCH_LIMIT "0"

TODAY="$(date +%Y-%m-%d)"
OUTPUT_JSONL="$RAW_DIR/tw_hf-${TODAY}.jsonl"
TEMP_JSON="$RAW_DIR/tw_hf-${TODAY}.json"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📡 台灣健康食品資料庫 資料擷取"
echo "   來源：衛福部食藥署健康食品資料集"
echo "   輸出：${OUTPUT_JSONL}"
if [[ "$FETCH_LIMIT" -gt 0 ]]; then
  echo "   限制：${FETCH_LIMIT} 筆"
fi
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# === Step 1: 下載 JSON ===
echo "📥 下載資料..."

if curl -L -f -o "$TEMP_JSON" \
  --retry 3 \
  --retry-delay 5 \
  --connect-timeout 30 \
  --max-time 120 \
  "$API_URL" 2>/dev/null; then

  FILE_SIZE=$(du -h "$TEMP_JSON" | cut -f1)
  echo "✅ 下載完成：${FILE_SIZE}"
else
  echo "❌ 下載失敗" >&2
  exit 1
fi

# === Step 2: JSON Array → JSONL ===
echo "🔄 轉換 JSON → JSONL..."

FETCHED=$(TEMP_JSON="$TEMP_JSON" OUTPUT_JSONL="$OUTPUT_JSONL" FETCH_LIMIT="$FETCH_LIMIT" python3 << 'PYEOF'
import json
import sys
import os

temp_json = os.environ["TEMP_JSON"]
output_path = os.environ["OUTPUT_JSONL"]
fetch_limit = int(os.environ.get("FETCH_LIMIT", "0"))

count = 0

try:
    # 嘗試多種編碼（台灣政府 API 常帶 BOM）
    for encoding in ["utf-8-sig", "utf-8"]:
        try:
            with open(temp_json, "r", encoding=encoding) as f:
                data = json.load(f)
            break
        except (json.JSONDecodeError, UnicodeDecodeError):
            continue
    else:
        raise json.JSONDecodeError("無法解析", "", 0)
except json.JSONDecodeError as e:
    print(f"JSON 解析錯誤: {e}", file=sys.stderr)
    print("0")
    sys.exit(1)

if not isinstance(data, list):
    print("API 回傳格式異常：預期為陣列", file=sys.stderr)
    print("0")
    sys.exit(1)

with open(output_path, "w", encoding="utf-8") as out_f:
    for item in data:
        if fetch_limit > 0 and count >= fetch_limit:
            break

        # 確保有許可證字號
        license_no = item.get("許可證字號", "")
        if not license_no:
            continue

        out_f.write(json.dumps(item, ensure_ascii=False) + "\n")
        count += 1

print(count)
PYEOF
)

# 清理暫存檔
rm -f "$TEMP_JSON"

# === 更新 .last_fetch ===
echo "$TODAY" > "$LAST_FETCH_FILE"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Fetch completed: $LAYER_NAME"
echo "   總筆數：${FETCHED}"
echo "   輸出檔：${OUTPUT_JSONL}"
