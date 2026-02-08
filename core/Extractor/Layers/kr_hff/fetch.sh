#!/bin/bash
# kr_hff 資料擷取腳本（支援增量更新）
# 從 MFDS data.go.kr API 擷取韓國健康機能食品資料
#
# 用法：
#   ./fetch.sh              # 增量更新（比對差異，只處理變更）
#   ./fetch.sh --full       # 全量更新（處理所有產品）
#   ./fetch.sh --limit 100  # 限制筆數（測試用）
#   ./fetch.sh --resume     # 續傳模式（從既有 JSONL 繼續）
#
# 需要 .env 設定：
#   MFDS_API_KEY=...  (data.go.kr 服務金鑰)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../../.." && pwd)"

source "$PROJECT_ROOT/lib/args.sh"
source "$PROJECT_ROOT/lib/core.sh"
source "$PROJECT_ROOT/lib/api.sh"

require_cmd jq
require_cmd python3

LAYER_NAME="kr_hff"
RAW_DIR="$PROJECT_ROOT/docs/Extractor/$LAYER_NAME/raw"
LAST_FETCH_FILE="$RAW_DIR/.last_fetch"
LATEST_LINK="$RAW_DIR/latest.jsonl"  # 指向最新完整 JSONL 的符號連結

MFDS_API_BASE="https://apis.data.go.kr/1471000/HtfsInfoService03/getHtfsItem01"
PAGE_SIZE=100

mkdir -p "$RAW_DIR"

# === 檢查 API Key ===
if [[ -z "${MFDS_API_KEY:-}" ]]; then
  echo "❌ 未設定 MFDS_API_KEY" >&2
  echo "   請在 .env 加入：MFDS_API_KEY=<your data.go.kr service key>" >&2
  exit 1
fi

# === 解析參數 ===
parse_args "$@"
arg_optional "limit" FETCH_LIMIT "0"
arg_optional "full" FULL_UPDATE "false"
arg_optional "resume" RESUME_MODE "false"

TODAY="$(date +%Y-%m-%d)"
OUTPUT_JSONL="$RAW_DIR/hff-${TODAY}.jsonl"
DELTA_DIR="$RAW_DIR/delta-${TODAY}"
DELTA_JSONL="$DELTA_DIR/delta.jsonl"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📡 MFDS 건강기능식품 資料擷取"
echo "   API: ${MFDS_API_BASE}"
echo "   輸出：${OUTPUT_JSONL}"
if [[ "$FULL_UPDATE" != "false" ]]; then
  echo "   模式：全量更新"
elif [[ "$RESUME_MODE" != "false" ]]; then
  echo "   模式：續傳"
else
  echo "   模式：增量更新"
fi
if [[ "$FETCH_LIMIT" -gt 0 ]]; then
  echo "   限制：${FETCH_LIMIT} 筆（測試用）"
fi
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# === 分頁擷取 ===
# 檢查是否有既有資料，支援續傳
if [[ "$RESUME_MODE" != "false" ]] && [[ -f "$OUTPUT_JSONL" ]] && [[ -s "$OUTPUT_JSONL" ]]; then
  EXISTING_LINES="$(wc -l < "$OUTPUT_JSONL" | tr -d ' ')"
  FETCHED=$EXISTING_LINES
  PAGE=$(( (EXISTING_LINES / PAGE_SIZE) + 1 ))
  echo ""
  echo "📎 續傳模式：偵測到既有資料 ${EXISTING_LINES} 筆，從第 ${PAGE} 頁繼續" >&2
else
  > "$OUTPUT_JSONL"
  PAGE=1
  FETCHED=0
fi
TOTAL=-1

echo ""
echo "📥 開始分頁擷取..."

while true; do
  TMP_PAGE="$(mktemp)"

  FETCH_URL="${MFDS_API_BASE}?serviceKey=${MFDS_API_KEY}&pageNo=${PAGE}&numOfRows=${PAGE_SIZE}&type=json"

  # 重試邏輯
  MAX_RETRIES=5
  RETRY_OK=false

  for ((retry=1; retry<=MAX_RETRIES; retry++)); do
    if curl -sS -L \
      -H "User-Agent: SupplementProductIntelligence/1.0" \
      --connect-timeout 30 \
      --max-time 120 \
      -o "$TMP_PAGE" \
      "$FETCH_URL" 2>/dev/null; then

      # 檢查回應是否為有效 JSON
      if jq -e . < "$TMP_PAGE" >/dev/null 2>&1; then
        RETRY_OK=true
        break
      else
        echo "⚠️  第 ${PAGE} 頁回應非 JSON，重試 ${retry}/${MAX_RETRIES}..." >&2
      fi
    else
      echo "⚠️  第 ${PAGE} 頁下載失敗，重試 ${retry}/${MAX_RETRIES}..." >&2
    fi

    sleep $((retry * 3))  # 遞增延遲：3, 6, 9, 12, 15 秒
  done

  if [[ "$RETRY_OK" != "true" ]]; then
    echo "❌ 第 ${PAGE} 頁下載失敗（已重試 ${MAX_RETRIES} 次）" >&2
    echo "💡 可使用 --resume 參數從目前進度繼續" >&2
    rm -f "$TMP_PAGE"
    break
  fi

  # 第一頁取得總筆數
  if [[ $TOTAL -lt 0 ]]; then
    TOTAL="$(jq -r '.body.totalCount // 0' < "$TMP_PAGE" 2>/dev/null)"
    echo "📊 總筆數: ${TOTAL}" >&2
  fi

  # 提取 items
  PAGE_COUNT="$(jq -c '.body.items[]' < "$TMP_PAGE" 2>/dev/null | tee -a "$OUTPUT_JSONL" | wc -l | tr -d ' ')"

  FETCHED=$((FETCHED + PAGE_COUNT))
  echo "📥 已擷取: ${FETCHED}/${TOTAL} (page=${PAGE})" >&2

  rm -f "$TMP_PAGE"

  # 檢查是否結束
  if [[ "$PAGE_COUNT" -eq 0 ]] || [[ $FETCHED -ge $TOTAL ]]; then
    break
  fi

  # 限量模式
  if [[ "$FETCH_LIMIT" -gt 0 ]] && [[ $FETCHED -ge $FETCH_LIMIT ]]; then
    TMP="$(mktemp)"
    head -n "$FETCH_LIMIT" "$OUTPUT_JSONL" > "$TMP"
    mv "$TMP" "$OUTPUT_JSONL"
    FETCHED="$FETCH_LIMIT"
    break
  fi

  PAGE=$((PAGE + 1))
  sleep 1.5
done

FINAL_COUNT="$(wc -l < "$OUTPUT_JSONL" | tr -d ' ')"
echo ""
echo "✅ 下載完成：${FINAL_COUNT} 筆產品"

# === 差異比對（增量模式）===
DELTA_COUNT="$FINAL_COUNT"

if [[ "$FULL_UPDATE" == "false" ]] && [[ -L "$LATEST_LINK" ]] && [[ -f "$LATEST_LINK" ]]; then
  PREV_JSONL="$(readlink -f "$LATEST_LINK")"

  if [[ "$PREV_JSONL" != "$OUTPUT_JSONL" ]] && [[ -f "$PREV_JSONL" ]]; then
    echo ""
    echo "🔍 比對差異（與上次擷取比較）..."
    echo "   舊檔：$PREV_JSONL"
    echo "   新檔：$OUTPUT_JSONL"

    mkdir -p "$DELTA_DIR"

    python3 "$PROJECT_ROOT/scripts/diff_kr_hff.py" \
      "$PREV_JSONL" "$OUTPUT_JSONL" "$DELTA_DIR"

    if [[ -f "$DELTA_JSONL" ]]; then
      DELTA_COUNT="$(wc -l < "$DELTA_JSONL" | tr -d ' ')"

      if [[ "$DELTA_COUNT" -gt 0 ]]; then
        echo ""
        echo "📊 增量更新：只處理 ${DELTA_COUNT} 筆（共 ${FINAL_COUNT} 筆）"
      else
        echo ""
        echo "ℹ️  無變更：所有產品資料與上次相同"
      fi
    fi
  fi
else
  if [[ "$FULL_UPDATE" != "false" ]]; then
    echo ""
    echo "📊 全量更新模式：處理所有 ${FINAL_COUNT} 筆"
  else
    echo ""
    echo "ℹ️  首次擷取，無舊資料可比對，處理所有 ${FINAL_COUNT} 筆"
  fi
fi

# === 更新符號連結 ===
ln -sf "$OUTPUT_JSONL" "$LATEST_LINK"
echo "🔗 更新 latest.jsonl → $(basename "$OUTPUT_JSONL")"

# === 更新 .last_fetch ===
echo "$TODAY" > "$LAST_FETCH_FILE"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Fetch completed: $LAYER_NAME"
echo "   總產品數：${FINAL_COUNT}"
echo "   需處理數：${DELTA_COUNT}"
echo "   完整檔案：${OUTPUT_JSONL}"
if [[ -f "$DELTA_JSONL" ]] && [[ "$DELTA_COUNT" -gt 0 ]]; then
  echo "   差異檔案：${DELTA_JSONL}"
fi
echo ""
echo "💡 後續步驟："
echo "   1. 執行萃取：python3 scripts/extract_kr_hff.py"
if [[ -f "$DELTA_JSONL" ]] && [[ "$DELTA_COUNT" -gt 0 ]]; then
  echo "      或指定差異檔：python3 scripts/extract_kr_hff.py --delta $DELTA_JSONL"
fi
echo "   2. 執行更新：./core/Extractor/Layers/kr_hff/update.sh"
