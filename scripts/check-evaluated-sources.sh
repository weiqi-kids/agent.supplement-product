#!/bin/bash
# check-evaluated-sources.sh
# 檢查 docs/explored.md 中「已採用」和「評估中」的資料源連線狀態
# 由 GitHub Actions 每日排程執行

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
EXPLORED_FILE="$PROJECT_ROOT/docs/explored.md"

if [[ ! -f "$EXPLORED_FILE" ]]; then
  echo "❌ docs/explored.md not found"
  exit 1
fi

TIMEOUT=15
TOTAL=0
OK=0
FAIL=0
CHANGED=false

echo "=== 資料源連線檢查 $(date -u '+%Y-%m-%d %H:%M UTC') ==="
echo ""

# 從 explored.md 提取 URL 並測試
# 格式: | 資料源名稱 | 類型 | URL | ... |
# 已採用表格的 URL 在「對應 Layer」欄之前的 RSS URL（從 fetch.sh 取）
# 評估中表格的 URL 在第 3 欄

check_url() {
  local url="$1"
  local name="$2"

  # 跳過空值和佔位符
  [[ -z "$url" ]] && return 0
  [[ "$url" == "N/A" ]] && return 0
  [[ "$url" != http* ]] && return 0

  ((TOTAL++)) || true

  local http_code
  http_code="$(curl -sS -L -o /dev/null -w '%{http_code}' \
    --connect-timeout "$TIMEOUT" \
    --max-time 30 \
    -H "User-Agent: RiskResponsibilityBot/1.0 (source-check)" \
    "$url" 2>/dev/null)" || http_code="000"

  if [[ "$http_code" =~ ^(200|301|302|304)$ ]]; then
    echo "  ✅ [$http_code] $name"
    ((OK++)) || true
  else
    echo "  ❌ [$http_code] $name — $url"
    ((FAIL++)) || true
  fi
}

# === 檢查已採用來源 ===
echo "## 已採用"

# 從 fetch.sh 中提取實際 RSS URL
for layer_dir in "$PROJECT_ROOT"/core/Extractor/Layers/*/; do
  [[ -d "$layer_dir" ]] || continue
  layer_name="$(basename "$layer_dir")"

  # 跳過 disabled layers
  [[ -f "$layer_dir/.disabled" ]] && continue

  fetch_script="$layer_dir/fetch.sh"
  [[ -f "$fetch_script" ]] || continue

  # 從 fetch.sh 提取 FEED_URL
  while IFS= read -r url; do
    [[ -n "$url" ]] && check_url "$url" "$layer_name"
  done < <(grep -oE 'https?://[^ "]+' "$fetch_script" | grep -iE 'rss|xml|feed|atom|api' || true)
done

echo ""

# === 檢查評估中來源 ===
echo "## 評估中"

in_evaluated=false
while IFS= read -r line; do
  # 偵測段落
  if echo "$line" | grep -q '^## 評估中'; then
    in_evaluated=true
    continue
  fi
  if echo "$line" | grep -q '^## ' && [[ "$in_evaluated" == "true" ]]; then
    break
  fi

  # 跳過表頭和分隔線
  [[ "$in_evaluated" != "true" ]] && continue
  echo "$line" | grep -qE '^\|[-: ]+\|' && continue
  echo "$line" | grep -q '資料源' && continue

  # 提取 URL（第 3 欄）
  url="$(echo "$line" | awk -F'|' '{gsub(/^ +| +$/, "", $4); print $4}')"
  name="$(echo "$line" | awk -F'|' '{gsub(/^ +| +$/, "", $2); print $2}')"

  [[ -n "$url" ]] && check_url "$url" "$name"
done < "$EXPLORED_FILE"

echo ""
echo "=== 結果: $TOTAL 個來源, $OK 正常, $FAIL 異常 ==="

if [[ $FAIL -gt 0 ]]; then
  echo "⚠️  有 $FAIL 個來源連線異常，請檢查"
  exit 0  # 不以失敗退出，讓 workflow 繼續 commit
fi
