#!/bin/bash
# jp_foshu 資料擷取腳本
# 從消費者庁 (CAA) 下載特定保健用食品許可品目一覧 Excel，轉換為 JSONL
#
# 依賴：python3, openpyxl (pip3 install openpyxl)
# 無需 API Key

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../../.." && pwd)"

source "$PROJECT_ROOT/lib/args.sh"
source "$PROJECT_ROOT/lib/core.sh"

require_cmd python3
require_cmd curl
require_cmd jq

LAYER_NAME="jp_foshu"
RAW_DIR="$PROJECT_ROOT/docs/Extractor/$LAYER_NAME/raw"
LAST_FETCH_FILE="$RAW_DIR/.last_fetch"

# CAA FOSHU 頁面（從此頁面解析 Excel 下載連結）
CAA_FOSHU_PAGE="https://www.caa.go.jp/policies/policy/food_labeling/foods_for_specified_health_uses/"

mkdir -p "$RAW_DIR"

# === 確認 openpyxl 已安裝 ===
if ! python3 -c "import openpyxl" 2>/dev/null; then
  echo "📦 安裝 openpyxl..." >&2
  pip3 install openpyxl -q 2>/dev/null
fi

# === 解析參數 ===
parse_args "$@"
arg_optional "limit" FETCH_LIMIT "0"

TODAY="$(date +%Y-%m-%d)"
OUTPUT_JSONL="$RAW_DIR/foshu-${TODAY}.jsonl"
EXCEL_FILE="$RAW_DIR/foshu-${TODAY}.xlsx"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📡 CAA 特定保健用食品 資料擷取"
echo "   來源：${CAA_FOSHU_PAGE}"
echo "   輸出：${OUTPUT_JSONL}"
if [[ "$FETCH_LIMIT" -gt 0 ]]; then
  echo "   限制：${FETCH_LIMIT} 筆"
fi
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# === Step 1: 從頁面解析 Excel 下載連結 ===
echo "🔍 解析 Excel 下載連結..." >&2

EXCEL_URL=$(curl -sS "$CAA_FOSHU_PAGE" 2>/dev/null \
  | grep -oE 'href="[^"]*\.xlsx"' \
  | head -1 \
  | sed 's/href="//;s/"$//')

if [[ -z "$EXCEL_URL" ]]; then
  echo "⚠️  無法從頁面解析 Excel 連結，使用已知 URL" >&2
  EXCEL_URL="/policies/policy/food_labeling/health_promotion/assets/food_labeling_cms206_260127_01.xlsx"
fi

# 補全為絕對 URL
if [[ "$EXCEL_URL" != http* ]]; then
  EXCEL_URL="https://www.caa.go.jp${EXCEL_URL}"
fi

echo "📥 下載 Excel: ${EXCEL_URL}" >&2

# === Step 2: 下載 Excel ===
if ! curl -sS -L \
  --connect-timeout 30 \
  --max-time 120 \
  -o "$EXCEL_FILE" \
  "$EXCEL_URL" 2>/dev/null; then
  echo "❌ Excel 下載失敗" >&2
  exit 1
fi

FILE_SIZE=$(wc -c < "$EXCEL_FILE" | tr -d ' ')
echo "📄 Excel 大小: ${FILE_SIZE} bytes" >&2

# === Step 3: Excel → JSONL ===
echo "🔄 轉換 Excel → JSONL..." >&2

FETCHED=$(EXCEL_FILE="$EXCEL_FILE" OUTPUT_JSONL="$OUTPUT_JSONL" FETCH_LIMIT="$FETCH_LIMIT" python3 << 'PYEOF'
import openpyxl
import json
import sys
import os

excel_path = os.environ["EXCEL_FILE"]
output_path = os.environ["OUTPUT_JSONL"]
fetch_limit = int(os.environ.get("FETCH_LIMIT", "0"))

wb = openpyxl.load_workbook(excel_path, data_only=True)
ws = wb.worksheets[0]

headers = [
    "serial_no", "product_name", "applicant", "corporate_no",
    "food_type", "functional_ingredient", "health_claim",
    "precautions", "daily_intake", "foshu_category",
    "approval_date", "approval_no", "sales_record"
]

count = 0
with open(output_path, "w", encoding="utf-8") as f:
    for row_idx, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=1):
        if fetch_limit > 0 and count >= fetch_limit:
            break

        record = {}
        for i, val in enumerate(row):
            if i < len(headers):
                if val is None:
                    record[headers[i]] = None
                elif hasattr(val, 'strftime'):
                    record[headers[i]] = val.strftime("%Y-%m-%d")
                else:
                    record[headers[i]] = str(val).strip() if val else None

        if not record.get("product_name"):
            continue

        if record.get("serial_no") and record["serial_no"].startswith("="):
            record["serial_no"] = str(row_idx)

        f.write(json.dumps(record, ensure_ascii=False) + "\n")
        count += 1

print(count)
PYEOF
)

# === 更新 .last_fetch ===
echo "$TODAY" > "$LAST_FETCH_FILE"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Fetch completed: $LAYER_NAME"
echo "   總筆數：${FETCHED}"
echo "   輸出檔：${OUTPUT_JSONL}"
