#!/usr/bin/env bash
# rss.sh - RSS XML 解析工具
# 注意：預期被其他 script 用 `source` 載入
# 不在這裡 set -euo pipefail，交給呼叫端決定。

if [[ -n "${RSS_SH_LOADED:-}" ]]; then
  return 0 2>/dev/null || exit 0
fi
RSS_SH_LOADED=1

_rss_lib_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
. "${_rss_lib_dir}/core.sh"

########################################
# rss_fetch URL OUTPUT_FILE
#
# 功能：
#   - 從指定 URL 下載 RSS XML 檔案
#
# 參數：
#   URL: RSS feed URL
#   OUTPUT_FILE: 輸出檔案路徑
#
# 回傳值：
#   0  = 成功
#   >0 = 失敗
########################################
rss_fetch() {
  local url="$1"
  local output_file="$2"

  require_cmd curl || return 1

  local max_retries=3
  local retry_delay=2
  local http_code

  for ((attempt=1; attempt<=max_retries; attempt++)); do
    http_code="$(
      curl -sS -L \
        -H "User-Agent: IndustryIntelligenceArchitect/1.0" \
        -w '%{http_code}' \
        -o "$output_file" \
        --connect-timeout 15 \
        --max-time 60 \
        "$url" 2>/dev/null
    )" || {
      local rc=$?
      if [[ $attempt -lt $max_retries ]]; then
        echo "⚠️  [rss_fetch] curl 失敗 (exit=$rc)，重試 $attempt/$max_retries..." >&2
        sleep $retry_delay
        continue
      fi
      echo "❌ [rss_fetch] curl 失敗 (exit=$rc)，已重試 $max_retries 次" >&2
      return 1
    }

    if [[ "$http_code" == "200" ]]; then
      return 0
    fi

    if [[ $attempt -lt $max_retries ]]; then
      echo "⚠️  [rss_fetch] HTTP=${http_code}，重試 $attempt/$max_retries..." >&2
      sleep $retry_delay
    else
      echo "❌ [rss_fetch] HTTP=${http_code}，已重試 $max_retries 次" >&2
      rm -f "$output_file"
      return 1
    fi
  done

  return 1
}

########################################
# rss_count_items XML_FILE
#
# 功能：
#   - 計算 RSS feed 中的 item 數量
#
# 參數：
#   XML_FILE: RSS XML 檔案路徑
#
# stdout:
#   item 數量（整數）
########################################
rss_count_items() {
  local xml_file="$1"

  if [[ ! -f "$xml_file" ]]; then
    echo "0"
    return 1
  fi

  # 使用 grep 計算 <item> 標籤數量
  grep -c '<item>' "$xml_file" 2>/dev/null || echo "0"
}

########################################
# rss_extract_titles XML_FILE
#
# 功能：
#   - 從 RSS XML 中提取所有 item 的 title
#
# 參數：
#   XML_FILE: RSS XML 檔案路徑
#
# stdout:
#   每行一個 title
########################################
rss_extract_titles() {
  local xml_file="$1"

  if [[ ! -f "$xml_file" ]]; then
    return 1
  fi

  # 簡易 XML title 提取（在 <item> 區塊內的 <title>）
  # 注意：這是簡化實作，複雜 XML 建議使用 xmllint
  sed -n '/<item>/,/<\/item>/{ /<title>/{ s/.*<title>\(.*\)<\/title>.*/\1/; s/<!\[CDATA\[//g; s/\]\]>//g; p; } }' "$xml_file"
}

########################################
# rss_extract_links XML_FILE
#
# 功能：
#   - 從 RSS XML 中提取所有 item 的 link
#
# 參數：
#   XML_FILE: RSS XML 檔案路徑
#
# stdout:
#   每行一個 link
########################################
rss_extract_links() {
  local xml_file="$1"

  if [[ ! -f "$xml_file" ]]; then
    return 1
  fi

  sed -n '/<item>/,/<\/item>/{ /<link>/{ s/.*<link>\(.*\)<\/link>.*/\1/; p; } }' "$xml_file"
}

########################################
# rss_extract_items_jsonl XML_FILE
#
# 功能：
#   - 將 RSS XML items 轉為 JSONL（每行一筆 JSON）
#   - 每個 item 包含 title, link, description, pubDate
#
# 參數：
#   XML_FILE: RSS XML 檔案路徑
#
# stdout:
#   每行一個 compact JSON object
#
# 依賴：
#   xmllint (libxml2) — 若不存在則回退到 sed 簡易解析
########################################
rss_extract_items_jsonl() {
  local xml_file="$1"

  require_cmd jq || return 1

  if [[ ! -f "$xml_file" ]]; then
    return 1
  fi

  # 優先使用 xmllint（精確度較高）
  if command -v xmllint >/dev/null 2>&1; then
    _rss_extract_via_xmllint "$xml_file"
    return $?
  fi

  # 回退到 sed 簡易解析
  _rss_extract_via_sed "$xml_file"
}

# 使用 xmllint 解析（較精確）— 輸出 JSONL
_rss_extract_via_xmllint() {
  local xml_file="$1"

  # 取得 item 數量
  local count
  count="$(xmllint --xpath 'count(//item)' "$xml_file" 2>/dev/null)" || {
    return 1
  }

  for ((i=1; i<=count; i++)); do
    local title link description pubDate
    title="$(xmllint --xpath "string(//item[$i]/title)" "$xml_file" 2>/dev/null || echo "")"
    link="$(xmllint --xpath "string(//item[$i]/link)" "$xml_file" 2>/dev/null || echo "")"
    description="$(xmllint --xpath "string(//item[$i]/description)" "$xml_file" 2>/dev/null || echo "")"
    pubDate="$(xmllint --xpath "string(//item[$i]/pubDate)" "$xml_file" 2>/dev/null || echo "")"

    jq -c -n \
      --arg title "$title" \
      --arg link "$link" \
      --arg description "$description" \
      --arg pubDate "$pubDate" \
      '{title: $title, link: $link, description: $description, pubDate: $pubDate}'
  done
}

# 使用 sed 簡易解析（回退方案）— 輸出 JSONL
_rss_extract_via_sed() {
  local xml_file="$1"

  local in_item=false
  local title="" link="" description="" pubDate=""

  while IFS= read -r line; do
    if [[ "$line" =~ \<item\> ]]; then
      in_item=true
      title="" link="" description="" pubDate=""
      continue
    fi

    if [[ "$line" =~ \</item\> ]]; then
      in_item=false
      # 清理 CDATA
      title="${title//<![CDATA[/}"
      title="${title//]]>/}"
      description="${description//<![CDATA[/}"
      description="${description//]]>/}"

      jq -c -n \
        --arg title "$title" \
        --arg link "$link" \
        --arg description "$description" \
        --arg pubDate "$pubDate" \
        '{title: $title, link: $link, description: $description, pubDate: $pubDate}'
      continue
    fi

    if [[ "$in_item" == "true" ]]; then
      if [[ "$line" =~ \<title\>(.*)\</title\> ]]; then
        title="${BASH_REMATCH[1]}"
      elif [[ "$line" =~ \<link\>(.*)\</link\> ]]; then
        link="${BASH_REMATCH[1]}"
      elif [[ "$line" =~ \<description\>(.*)\</description\> ]]; then
        description="${BASH_REMATCH[1]}"
      elif [[ "$line" =~ \<pubDate\>(.*)\</pubDate\> ]]; then
        pubDate="${BASH_REMATCH[1]}"
      fi
    fi
  done < "$xml_file"
}

########################################
# rss_validate XML_FILE
#
# 功能：
#   - 驗證 RSS XML 檔案基本結構
#
# 參數：
#   XML_FILE: RSS XML 檔案路徑
#
# 回傳值：
#   0  = 有效
#   1  = 無效
########################################
rss_validate() {
  local xml_file="$1"

  if [[ ! -f "$xml_file" ]]; then
    echo "❌ [rss_validate] 檔案不存在：$xml_file" >&2
    return 1
  fi

  if [[ ! -s "$xml_file" ]]; then
    echo "❌ [rss_validate] 檔案為空：$xml_file" >&2
    return 1
  fi

  # 檢查是否包含基本 RSS 結構
  if ! grep -q '<rss\|<feed\|<channel' "$xml_file" 2>/dev/null; then
    echo "❌ [rss_validate] 不是有效的 RSS/Atom 格式：$xml_file" >&2
    return 1
  fi

  return 0
}
