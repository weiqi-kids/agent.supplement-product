#!/bin/bash
# ca_lnhpd 資料擷取腳本（支援增量更新）
# 從 Health Canada LNHPD API 擷取已授權天然保健品資料
#
# 用法：
#   ./fetch.sh                   # 增量更新（比對差異，只處理變更）
#   ./fetch.sh --full            # 全量更新（處理所有產品）
#   ./fetch.sh --with-ingredients # 同時下載成分資料（約 810K 筆）
#   ./fetch.sh --limit 100       # 限制筆數（測試用）
#
# ProductLicence 端點回傳完整 JSON 陣列（~139MB），無分頁。
# MedicinalIngredient 端點為分頁 API（~810K 筆），需較長時間下載。
# 需要較長 timeout（600s）來完成下載，並啟用 retry 機制。

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../../.." && pwd)"

source "$PROJECT_ROOT/lib/args.sh"
source "$PROJECT_ROOT/lib/core.sh"

require_cmd jq
require_cmd python3

LAYER_NAME="ca_lnhpd"
RAW_DIR="$PROJECT_ROOT/docs/Extractor/$LAYER_NAME/raw"
LAST_FETCH_FILE="$RAW_DIR/.last_fetch"
LATEST_LINK="$RAW_DIR/latest.jsonl"  # 指向最新完整 JSONL 的符號連結

LNHPD_PRODUCT_URL="https://health-products.canada.ca/api/natural-licences/ProductLicence/?lang=en&type=json"

mkdir -p "$RAW_DIR"

# === 解析參數 ===
parse_args "$@"
arg_optional "limit" FETCH_LIMIT "0"
arg_optional "full" FULL_UPDATE "false"
arg_optional "timeout" DOWNLOAD_TIMEOUT "600"
arg_optional "with-ingredients" WITH_INGREDIENTS "false"

TODAY="$(date +%Y-%m-%d)"
PRODUCT_JSONL="$RAW_DIR/products-${TODAY}.jsonl"
DELTA_DIR="$RAW_DIR/delta-${TODAY}"
DELTA_JSONL="$DELTA_DIR/delta.jsonl"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📡 LNHPD 資料擷取"
echo "   產品 API: ${LNHPD_PRODUCT_URL}"
if [[ "$FULL_UPDATE" != "false" ]]; then
  echo "   模式：全量更新"
else
  echo "   模式：增量更新"
fi
if [[ "$WITH_INGREDIENTS" != "false" ]]; then
  echo "   成分：同步下載"
fi
if [[ "$FETCH_LIMIT" -gt 0 ]]; then
  echo "   限制：${FETCH_LIMIT} 筆"
fi
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# === 步驟一：下載 ProductLicence bulk ===
echo ""
echo "📥 下載產品資料（bulk JSON array ~139MB）..."

TMP_JSON="$(mktemp)"

curl -sS -L \
  -H "User-Agent: SupplementProductIntelligence/1.0" \
  -H "Accept: application/json" \
  --connect-timeout 30 \
  --max-time "$DOWNLOAD_TIMEOUT" \
  --retry 3 \
  --retry-delay 10 \
  -o "$TMP_JSON" \
  "$LNHPD_PRODUCT_URL" || {
    echo "❌ ProductLicence 下載失敗" >&2
    rm -f "$TMP_JSON"
    exit 1
  }

DOWNLOAD_SIZE="$(wc -c < "$TMP_JSON" | tr -d ' ')"
echo "   下載大小：$(( DOWNLOAD_SIZE / 1024 / 1024 )) MB"

# === 轉換 JSON array → JSONL ===
echo "🔄 轉換為 JSONL..."

if [[ "$FETCH_LIMIT" -gt 0 ]]; then
  jq -c ".[:${FETCH_LIMIT}][]" < "$TMP_JSON" > "$PRODUCT_JSONL"
else
  jq -c '.[]' < "$TMP_JSON" > "$PRODUCT_JSONL"
fi

rm -f "$TMP_JSON"

PRODUCT_COUNT="$(wc -l < "$PRODUCT_JSONL" | tr -d ' ')"
echo "✅ 產品：${PRODUCT_COUNT} 筆"

# === 步驟 1.5：下載成分資料（可選）===
INGREDIENTS_JSONL=""
if [[ "$WITH_INGREDIENTS" != "false" ]]; then
  echo ""
  echo "📥 下載成分資料（MedicinalIngredient API ~810K 筆）..."

  INGREDIENTS_JSONL="$RAW_DIR/ingredients-${TODAY}.jsonl"

  python3 "$PROJECT_ROOT/scripts/fetch_lnhpd_ingredients.py" \
    --output "$INGREDIENTS_JSONL" || {
      echo "❌ 成分資料下載失敗" >&2
      exit 1
    }

  if [[ -f "$INGREDIENTS_JSONL" ]]; then
    INGREDIENTS_COUNT="$(wc -l < "$INGREDIENTS_JSONL" | tr -d ' ')"
    echo "✅ 成分：${INGREDIENTS_COUNT} 筆"
  fi
fi

# === 步驟二：差異比對（增量模式）===
OUTPUT_JSONL="$PRODUCT_JSONL"  # 預設輸出完整 JSONL
DELTA_COUNT="$PRODUCT_COUNT"

if [[ "$FULL_UPDATE" == "false" ]] && [[ -L "$LATEST_LINK" ]] && [[ -f "$LATEST_LINK" ]]; then
  PREV_JSONL="$(readlink -f "$LATEST_LINK")"

  if [[ "$PREV_JSONL" != "$PRODUCT_JSONL" ]] && [[ -f "$PREV_JSONL" ]]; then
    echo ""
    echo "🔍 比對差異（與上次擷取比較）..."
    echo "   舊檔：$PREV_JSONL"
    echo "   新檔：$PRODUCT_JSONL"

    mkdir -p "$DELTA_DIR"

    python3 "$PROJECT_ROOT/scripts/diff_lnhpd.py" \
      "$PREV_JSONL" "$PRODUCT_JSONL" "$DELTA_DIR"

    if [[ -f "$DELTA_JSONL" ]]; then
      DELTA_COUNT="$(wc -l < "$DELTA_JSONL" | tr -d ' ')"

      if [[ "$DELTA_COUNT" -gt 0 ]]; then
        OUTPUT_JSONL="$DELTA_JSONL"
        echo ""
        echo "📊 增量更新：只處理 ${DELTA_COUNT} 筆（共 ${PRODUCT_COUNT} 筆）"
      else
        echo ""
        echo "ℹ️  無變更：所有產品資料與上次相同"
      fi
    fi
  fi
else
  if [[ "$FULL_UPDATE" != "false" ]]; then
    echo ""
    echo "📊 全量更新模式：處理所有 ${PRODUCT_COUNT} 筆"
  else
    echo ""
    echo "ℹ️  首次擷取，無舊資料可比對，處理所有 ${PRODUCT_COUNT} 筆"
  fi
fi

# === 步驟三：更新符號連結 ===
ln -sf "$PRODUCT_JSONL" "$LATEST_LINK"
echo "🔗 更新 latest.jsonl → $(basename "$PRODUCT_JSONL")"

# === 更新 .last_fetch ===
echo "$TODAY" > "$LAST_FETCH_FILE"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Fetch completed: $LAYER_NAME"
echo "   總產品數：${PRODUCT_COUNT}"
echo "   需處理數：${DELTA_COUNT}"
echo "   完整檔案：${PRODUCT_JSONL}"
if [[ "$OUTPUT_JSONL" != "$PRODUCT_JSONL" ]]; then
  echo "   差異檔案：${OUTPUT_JSONL}"
fi
echo ""
echo "💡 後續步驟："
if [[ -n "$INGREDIENTS_JSONL" ]] && [[ -f "$INGREDIENTS_JSONL" ]]; then
  echo "   1. 執行萃取（含成分）："
  echo "      python3 scripts/extract_ca_lnhpd.py --ingredients $INGREDIENTS_JSONL $OUTPUT_JSONL"
else
  echo "   1. 執行萃取：python3 scripts/extract_ca_lnhpd.py $OUTPUT_JSONL"
  if [[ -f "$RAW_DIR/latest-ingredients.jsonl" ]]; then
    echo "      若需整合成分：python3 scripts/extract_ca_lnhpd.py --ingredients $RAW_DIR/latest-ingredients.jsonl $OUTPUT_JSONL"
  fi
fi
echo "   2. 執行更新：./core/Extractor/Layers/ca_lnhpd/update.sh"
