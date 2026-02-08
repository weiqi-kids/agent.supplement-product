#!/bin/bash
# jp_fnfc 資料擷取腳本
# 自動下載 CSV 並轉換為 JSONL
#
# 用法：
#   ./fetch.sh              # 自動下載並轉換
#   ./fetch.sh --no-download # 使用現有 CSV（不下載）
#   ./fetch.sh --csv /path/to/file.csv  # 指定 CSV 檔案
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

LAYER_NAME="jp_fnfc"
RAW_DIR="$PROJECT_ROOT/docs/Extractor/$LAYER_NAME/raw"
LAST_FETCH_FILE="$RAW_DIR/.last_fetch"

# Salesforce Content Document Download URL
# 優先從 .env 讀取，若未設定則使用預設值
# 注意：此 Document ID 可能會變更，如果下載失敗請更新
DEFAULT_DOWNLOAD_URL="https://www.fld.caa.go.jp/caaks/sfc/servlet.shepherd/document/download/069RA00000n6SLZYA2?operationContext=S1"
DOWNLOAD_URL="${JP_FNFC_DOWNLOAD_URL:-$DEFAULT_DOWNLOAD_URL}"

# === URL 健康檢查 ===
_check_url_health() {
  local url="$1"
  local http_code

  http_code=$(curl -sS -o /dev/null -w '%{http_code}' --head --connect-timeout 10 "$url" 2>/dev/null) || return 1

  # 200, 301, 302 都算成功（Salesforce 可能重導向）
  if [[ "$http_code" =~ ^(200|301|302)$ ]]; then
    return 0
  else
    echo "⚠️  URL 健康檢查失敗 (HTTP $http_code): $url" >&2
    return 1
  fi
}

# 執行健康檢查
if ! _check_url_health "$DOWNLOAD_URL"; then
  echo "" >&2
  echo "╔══════════════════════════════════════════════════════════════════╗" >&2
  echo "║  ⚠️  jp_fnfc 下載 URL 可能已失效                                 ║" >&2
  echo "║                                                                  ║" >&2
  echo "║  Salesforce Document ID 可能已變更。                             ║" >&2
  echo "║                                                                  ║" >&2
  echo "║  解決方法：                                                      ║" >&2
  echo "║  1. 前往 https://www.fld.caa.go.jp/caaks/cssc01/                ║" >&2
  echo "║  2. 點選「全届出の全項目出力(CSV 出力)」                         ║" >&2
  echo "║  3. 取得新的下載 URL                                             ║" >&2
  echo "║  4. 更新 .env 中的 JP_FNFC_DOWNLOAD_URL                         ║" >&2
  echo "║                                                                  ║" >&2
  echo "║  目前 URL: $DOWNLOAD_URL" >&2
  echo "╚══════════════════════════════════════════════════════════════════╝" >&2
  echo "" >&2
fi

mkdir -p "$RAW_DIR"

# === 解析參數 ===
parse_args "$@"
arg_optional "limit" FETCH_LIMIT "0"
arg_optional "csv" CSV_FILE ""
arg_optional "no-download" NO_DOWNLOAD "false"

TODAY="$(date +%Y-%m-%d)"
OUTPUT_JSONL="$RAW_DIR/fnfc-${TODAY}.jsonl"
DOWNLOADED_CSV="$RAW_DIR/fnfc-${TODAY}.csv"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📡 CAA 機能性表示食品 資料擷取"
echo "   來源：消費者庁 機能性表示食品資料庫"
echo "   輸出：${OUTPUT_JSONL}"
if [[ "$FETCH_LIMIT" -gt 0 ]]; then
  echo "   限制：${FETCH_LIMIT} 筆"
fi
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# === Step 1: 下載或尋找 CSV 檔案 ===
if [[ -n "$CSV_FILE" ]]; then
  # 使用者指定 CSV 檔案
  echo "📄 使用指定 CSV: ${CSV_FILE}"
elif [[ "$NO_DOWNLOAD" != "false" ]]; then
  # 不下載，尋找現有 CSV
  CSV_FILE=$(find "$RAW_DIR" -name "*.csv" -type f 2>/dev/null | sort -r | head -1)
  if [[ -z "$CSV_FILE" ]] || [[ ! -f "$CSV_FILE" ]]; then
    echo "❌ 未找到 CSV 檔案，請移除 --no-download 參數以自動下載" >&2
    exit 1
  fi
  echo "📄 使用現有 CSV: ${CSV_FILE}"
else
  # 自動下載 CSV
  echo "📥 下載 CSV 檔案..."

  if curl -L -f -o "$DOWNLOADED_CSV" \
    --retry 3 \
    --retry-delay 5 \
    --connect-timeout 30 \
    --max-time 300 \
    "$DOWNLOAD_URL" 2>/dev/null; then

    CSV_FILE="$DOWNLOADED_CSV"
    FILE_SIZE=$(du -h "$CSV_FILE" | cut -f1)
    echo "✅ 下載完成：${FILE_SIZE}"
  else
    echo "⚠️  自動下載失敗，嘗試尋找現有 CSV..." >&2
    CSV_FILE=$(find "$RAW_DIR" -name "*.csv" -type f 2>/dev/null | sort -r | head -1)

    if [[ -z "$CSV_FILE" ]] || [[ ! -f "$CSV_FILE" ]]; then
      echo "" >&2
      echo "❌ 下載失敗且無現有 CSV 檔案" >&2
      echo "" >&2
      echo "📋 請手動下載 CSV：" >&2
      echo "   1. 前往 https://www.fld.caa.go.jp/caaks/cssc01/" >&2
      echo "   2. 點選「全届出の全項目出力(CSV 出力)」" >&2
      echo "   3. 將下載的 CSV 放入：" >&2
      echo "      ${RAW_DIR}/" >&2
      echo "   4. 重新執行此腳本" >&2
      echo "" >&2
      echo "   或者如果 Document ID 已變更，請更新 fetch.sh 中的 DOWNLOAD_URL" >&2
      exit 1
    fi

    echo "📄 使用現有 CSV: ${CSV_FILE}"
  fi
fi

if [[ ! -f "$CSV_FILE" ]]; then
  echo "❌ CSV 檔案不存在：${CSV_FILE}" >&2
  exit 1
fi

# === Step 2: CSV → JSONL ===
echo "🔄 轉換 CSV → JSONL..."

FETCHED=$(CSV_FILE="$CSV_FILE" OUTPUT_JSONL="$OUTPUT_JSONL" FETCH_LIMIT="$FETCH_LIMIT" python3 << 'PYEOF'
import csv
import json
import sys
import os

csv_path = os.environ["CSV_FILE"]
output_path = os.environ["OUTPUT_JSONL"]
fetch_limit = int(os.environ.get("FETCH_LIMIT", "0"))

count = 0

# FNFC CSV 可能是 Shift_JIS 或 UTF-8 編碼
encodings = ["utf-8-sig", "utf-8", "shift_jis", "cp932"]
content = None

for enc in encodings:
    try:
        with open(csv_path, "r", encoding=enc) as f:
            content = f.read()
        break
    except (UnicodeDecodeError, UnicodeError):
        continue

if content is None:
    print("0")
    sys.exit(0)

with open(output_path, "w", encoding="utf-8") as out_f:
    reader = csv.DictReader(content.splitlines())

    for row in reader:
        if fetch_limit > 0 and count >= fetch_limit:
            break

        # 清理欄位名（移除 BOM 和空白）
        cleaned = {}
        for k, v in row.items():
            if k is None:
                continue
            clean_key = k.strip().replace("\ufeff", "")
            cleaned[clean_key] = v.strip() if v else None

        # 跳過空行
        notification_no = cleaned.get("届出番号") or cleaned.get("notification_no")
        product_name = cleaned.get("商品名") or cleaned.get("product_name")

        if not notification_no and not product_name:
            continue

        out_f.write(json.dumps(cleaned, ensure_ascii=False) + "\n")
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
