#!/bin/bash
# us_dsld 資料擷取腳本（使用 Bulk Download）
# 從 NIH DSLD 完整資料庫下載膳食補充品標籤資料
#
# 用法：
#   ./fetch.sh              # 增量更新（比對差異，只處理變更）
#   ./fetch.sh --full       # 全量更新（處理所有產品）
#   ./fetch.sh --api        # 使用舊版 API 模式（限制 10,000 筆）
#   ./fetch.sh --limit 100  # 限制筆數（測試用，僅 API 模式）
#
# 資料來源：
#   - Bulk Download: https://api.ods.od.nih.gov/dsld/s3/data/DSLD-full-database-JSON.zip
#   - 完整資料庫約 214,000+ 筆產品

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../../.." && pwd)"

source "$PROJECT_ROOT/lib/args.sh"
source "$PROJECT_ROOT/lib/core.sh"
source "$PROJECT_ROOT/lib/api.sh"

require_cmd jq
require_cmd python3
require_cmd unzip

LAYER_NAME="us_dsld"
RAW_DIR="$PROJECT_ROOT/docs/Extractor/$LAYER_NAME/raw"
LAST_FETCH_FILE="$RAW_DIR/.last_fetch"
LATEST_LINK="$RAW_DIR/latest.jsonl"  # 指向最新完整 JSONL 的符號連結

# Bulk Download URL
DSLD_BULK_URL="https://api.ods.od.nih.gov/dsld/s3/data/DSLD-full-database-JSON.zip"
# API URL (deprecated due to 10,000 limit)
DSLD_API_BASE="https://api.ods.od.nih.gov/dsld/v9/search-filter"
PAGE_SIZE=1000

mkdir -p "$RAW_DIR"

# === 解析參數 ===
parse_args "$@"
arg_optional "limit" FETCH_LIMIT "0"
arg_optional "full" FULL_UPDATE "false"
arg_optional "api" USE_API "false"

TODAY="$(date +%Y-%m-%d)"
OUTPUT_JSONL="$RAW_DIR/dsld-${TODAY}.jsonl"
DELTA_DIR="$RAW_DIR/delta-${TODAY}"
DELTA_JSONL="$DELTA_DIR/delta.jsonl"
ZIP_FILE="$RAW_DIR/DSLD-full-database-JSON.zip"
EXTRACT_DIR="$RAW_DIR/DSLD-full-database-JSON"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📡 DSLD 資料擷取"
if [[ "$USE_API" != "false" ]]; then
  echo "   來源: API（⚠️ 限制 10,000 筆）"
  echo "   API: ${DSLD_API_BASE}"
else
  echo "   來源: Bulk Download（完整資料庫）"
  echo "   URL: ${DSLD_BULK_URL}"
fi
echo "   輸出：${OUTPUT_JSONL}"
if [[ "$FULL_UPDATE" != "false" ]]; then
  echo "   模式：全量更新"
else
  echo "   模式：增量更新"
fi
if [[ "$FETCH_LIMIT" -gt 0 ]] && [[ "$USE_API" != "false" ]]; then
  echo "   限制：${FETCH_LIMIT} 筆（測試用）"
fi
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# === 擷取 ===
if [[ "$USE_API" != "false" ]]; then
  # API 模式（已棄用，受限於 10,000 筆）
  if [[ "$FETCH_LIMIT" -gt 0 ]]; then
    echo ""
    echo "📥 API 限量模式：擷取前 ${FETCH_LIMIT} 筆..."
    TMP_PAGE="$(mktemp)"
    api_fetch "${DSLD_API_BASE}?q=*&from=0&size=${FETCH_LIMIT}" "$TMP_PAGE"
    jq -c '.hits[] | ._source + {dsld_id: ._id}' < "$TMP_PAGE" > "$OUTPUT_JSONL"
    rm -f "$TMP_PAGE"
  else
    echo ""
    echo "📥 API 全量模式：分頁擷取（⚠️ 上限 10,000 筆）..."
    api_paginate_to_jsonl \
      "${DSLD_API_BASE}?q=*" \
      "$OUTPUT_JSONL" \
      '.hits[] | ._source + {dsld_id: ._id}' \
      "$PAGE_SIZE"
  fi
else
  # Bulk Download 模式（推薦）
  echo ""
  echo "📥 下載完整資料庫 ZIP..."
  curl -L -o "$ZIP_FILE" "$DSLD_BULK_URL" --progress-bar

  echo ""
  echo "📦 解壓縮..."
  rm -rf "$EXTRACT_DIR"
  unzip -q -o "$ZIP_FILE" -d "$RAW_DIR"

  echo ""
  echo "🔄 轉換為 JSONL 格式..."
  python3 "$PROJECT_ROOT/scripts/convert_dsld_bulk_to_jsonl.py" \
    "$EXTRACT_DIR" "$OUTPUT_JSONL"

  echo ""
  echo "🧹 清理暫存檔案..."
  rm -rf "$EXTRACT_DIR"
  rm -f "$ZIP_FILE"
fi

TOTAL="$(wc -l < "$OUTPUT_JSONL" | tr -d ' ')"
echo "✅ 下載完成：${TOTAL} 筆產品"

# === 差異比對（增量模式）===
DELTA_COUNT="$TOTAL"

if [[ "$FULL_UPDATE" == "false" ]] && [[ -L "$LATEST_LINK" ]] && [[ -f "$LATEST_LINK" ]]; then
  PREV_JSONL="$(readlink -f "$LATEST_LINK")"

  if [[ "$PREV_JSONL" != "$OUTPUT_JSONL" ]] && [[ -f "$PREV_JSONL" ]]; then
    echo ""
    echo "🔍 比對差異（與上次擷取比較）..."
    echo "   舊檔：$PREV_JSONL"
    echo "   新檔：$OUTPUT_JSONL"

    mkdir -p "$DELTA_DIR"

    python3 "$PROJECT_ROOT/scripts/diff_dsld.py" \
      "$PREV_JSONL" "$OUTPUT_JSONL" "$DELTA_DIR"

    if [[ -f "$DELTA_JSONL" ]]; then
      DELTA_COUNT="$(wc -l < "$DELTA_JSONL" | tr -d ' ')"

      if [[ "$DELTA_COUNT" -gt 0 ]]; then
        echo ""
        echo "📊 增量更新：只處理 ${DELTA_COUNT} 筆（共 ${TOTAL} 筆）"
      else
        echo ""
        echo "ℹ️  無變更：所有產品資料與上次相同"
      fi
    fi
  fi
else
  if [[ "$FULL_UPDATE" != "false" ]]; then
    echo ""
    echo "📊 全量更新模式：處理所有 ${TOTAL} 筆"
  else
    echo ""
    echo "ℹ️  首次擷取，無舊資料可比對，處理所有 ${TOTAL} 筆"
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
echo "   總產品數：${TOTAL}"
echo "   需處理數：${DELTA_COUNT}"
echo "   完整檔案：${OUTPUT_JSONL}"
if [[ -f "$DELTA_JSONL" ]] && [[ "$DELTA_COUNT" -gt 0 ]]; then
  echo "   差異檔案：${DELTA_JSONL}"
fi
echo ""
echo "💡 後續步驟："
echo "   1. 執行萃取：python3 scripts/extract_us_dsld.py"
if [[ -f "$DELTA_JSONL" ]] && [[ "$DELTA_COUNT" -gt 0 ]]; then
  echo "      或指定差異檔：python3 scripts/extract_us_dsld.py --delta $DELTA_JSONL"
fi
echo "   2. 執行更新：./core/Extractor/Layers/us_dsld/update.sh"
