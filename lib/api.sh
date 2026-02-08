#!/usr/bin/env bash
# api.sh - REST API 擷取工具
# 注意：預期被其他 script 用 `source` 載入
# 不在這裡 set -euo pipefail，交給呼叫端決定。

if [[ -n "${API_SH_LOADED:-}" ]]; then
  return 0 2>/dev/null || exit 0
fi
API_SH_LOADED=1

_api_lib_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
. "${_api_lib_dir}/core.sh"

########################################
# api_fetch URL OUTPUT_FILE [HEADERS...]
#
# 功能：
#   - 從指定 URL 下載 JSON 回應到檔案
#   - 自動重試（3 次，2s 間隔）
#   - 驗證 HTTP 200
#
# 參數：
#   URL: API endpoint URL
#   OUTPUT_FILE: 輸出檔案路徑
#   HEADERS: 額外 HTTP headers（選填，格式："Header: Value"）
#
# 回傳值：
#   0  = 成功
#   >0 = 失敗
########################################
api_fetch() {
  local url="$1"
  local output_file="$2"
  shift 2

  require_cmd curl || return 1

  local max_retries=3
  local retry_delay=2
  local http_code

  local curl_args=(
    -sS -L
    -H "User-Agent: SupplementProductIntelligence/1.0"
    -H "Accept: application/json"
    --connect-timeout 15
    --max-time 120
  )

  # 附加額外 headers
  while (( $# > 0 )); do
    curl_args+=( -H "$1" )
    shift
  done

  for ((attempt=1; attempt<=max_retries; attempt++)); do
    http_code="$(
      curl "${curl_args[@]}" \
        -w '%{http_code}' \
        -o "$output_file" \
        "$url" 2>/dev/null
    )" || {
      local rc=$?
      if [[ $attempt -lt $max_retries ]]; then
        echo "⚠️  [api_fetch] curl 失敗 (exit=$rc)，重試 $attempt/$max_retries..." >&2
        sleep $retry_delay
        continue
      fi
      echo "❌ [api_fetch] curl 失敗 (exit=$rc)，已重試 $max_retries 次" >&2
      return 1
    }

    if [[ "$http_code" == "200" ]]; then
      return 0
    fi

    if [[ $attempt -lt $max_retries ]]; then
      echo "⚠️  [api_fetch] HTTP=${http_code}，重試 $attempt/$max_retries..." >&2
      sleep $retry_delay
    else
      echo "❌ [api_fetch] HTTP=${http_code}，已重試 $max_retries 次" >&2
      rm -f "$output_file"
      return 1
    fi
  done

  return 1
}

########################################
# api_fetch_json URL [HEADERS...]
#
# 功能：
#   - 從指定 URL 擷取 JSON 並輸出到 stdout
#   - 使用臨時檔案，自動清理
#
# stdout:
#   JSON 回應內容
#
# 回傳值：
#   0  = 成功
#   >0 = 失敗
########################################
api_fetch_json() {
  local url="$1"
  shift

  local tmp_file
  tmp_file="$(mktemp)"

  if api_fetch "$url" "$tmp_file" "$@"; then
    cat "$tmp_file"
    rm -f "$tmp_file"
    return 0
  else
    rm -f "$tmp_file"
    return 1
  fi
}

########################################
# api_paginate_to_jsonl BASE_URL OUTPUT_JSONL JQ_HITS_EXPR PAGE_SIZE [HEADERS...]
#
# 功能：
#   - 通用分頁擷取，將每筆 item 輸出為 JSONL
#   - 使用 from/size 分頁模式
#   - 自動偵測總筆數並分頁到底
#
# 參數：
#   BASE_URL: API base URL（不含分頁參數，但可含其他 query params）
#   OUTPUT_JSONL: 輸出 JSONL 檔案路徑
#   JQ_HITS_EXPR: jq 表達式，從回應中提取 items array（例如 ".hits[]"）
#   PAGE_SIZE: 每頁筆數
#   HEADERS: 額外 HTTP headers
#
# stdout:
#   進度訊息
#
# 回傳值：
#   0  = 成功
#   >0 = 失敗
########################################
api_paginate_to_jsonl() {
  local base_url="$1"
  local output_jsonl="$2"
  local jq_hits_expr="$3"
  local page_size="${4:-1000}"
  shift 4

  require_cmd jq || return 1

  local separator="?"
  if [[ "$base_url" == *"?"* ]]; then
    separator="&"
  fi

  local from=0
  local total=-1
  local fetched=0
  local tmp_page
  tmp_page="$(mktemp)"

  # 清空輸出檔
  > "$output_jsonl"

  while true; do
    local url="${base_url}${separator}from=${from}&size=${page_size}"

    if ! api_fetch "$url" "$tmp_page" "$@"; then
      echo "❌ [api_paginate_to_jsonl] 擷取失敗 from=${from}" >&2
      rm -f "$tmp_page"
      return 1
    fi

    # 第一頁時取得總筆數
    if [[ $total -lt 0 ]]; then
      total="$(jq -r '.stats.count // .total // 0' < "$tmp_page" 2>/dev/null)"
      echo "📊 總筆數: ${total}" >&2
    fi

    # 提取 hits 並寫入 JSONL
    local page_count
    page_count="$(jq -c "$jq_hits_expr" < "$tmp_page" 2>/dev/null | tee -a "$output_jsonl" | wc -l | tr -d ' ')"

    fetched=$((fetched + page_count))
    echo "📥 已擷取: ${fetched}/${total} (from=${from})" >&2

    # 沒有更多結果時停止
    if [[ "$page_count" -eq 0 ]] || [[ $fetched -ge $total ]]; then
      break
    fi

    from=$((from + page_size))

    # 防止 API rate limit
    sleep 0.5
  done

  rm -f "$tmp_page"
  echo "✅ 分頁擷取完成: ${fetched} 筆 → ${output_jsonl}" >&2
  return 0
}
