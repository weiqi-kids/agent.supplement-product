#!/usr/bin/env bash
# rss.sh - RSS XML 解析工具（統一版）
# 合併自：disease-and-advisory（Python parser）、cyber-security（Atom 支援）、
#          risk-and-responsibility（URL 正規化）
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
        --tlsv1.2 \
        -H "User-Agent: Mozilla/5.0 (compatible; IndustryIntelligenceArchitect/1.0; +https://github.com)" \
        -H "Accept: application/rss+xml, application/xml, application/atom+xml, text/xml, */*;q=0.1" \
        -H "Accept-Language: en-US,en;q=0.9" \
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
#   - 同時支援 RSS（<item>）和 Atom（<entry>）格式
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

  # 偵測 Atom 格式（<entry>）或 RSS 格式（<item>）
  # 注意：grep -c 無匹配時輸出 "0" 但 exit 1，不可用 || echo "0"（會產生 "0\n0"）
  local item_count=0
  local entry_count=0
  item_count="$(grep -c '<item>' "$xml_file" 2>/dev/null)" || item_count=0
  entry_count="$(grep -c '<entry>' "$xml_file" 2>/dev/null)" || entry_count=0

  if [[ "$entry_count" -gt 0 ]]; then
    echo "$entry_count"
  else
    echo "$item_count"
  fi
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
#   - 將 RSS/Atom XML items 轉為 JSONL（每行一筆 JSON）
#   - 每個 item 包含 title, link, description, pubDate
#   - 自動偵測 RSS（<item>）和 Atom（<entry>）格式
#
# 參數：
#   XML_FILE: RSS XML 檔案路徑
#
# stdout:
#   每行一個 compact JSON object
#
# 依賴優先順序：
#   1. Python（效率最高，O(n)）
#   2. xmllint (libxml2)
#   3. sed 簡易解析（回退方案）
########################################
rss_extract_items_jsonl() {
  local xml_file="$1"

  require_cmd jq || return 1

  if [[ ! -f "$xml_file" ]]; then
    return 1
  fi

  # 偵測 Atom 格式（<feed> + <entry>）vs RSS 格式（<rss> + <item>）
  if grep -q '<entry>' "$xml_file" 2>/dev/null; then
    # Atom 格式
    if command -v python3 >/dev/null 2>&1; then
      _rss_extract_atom_via_python "$xml_file"
      return $?
    fi
    if command -v xmllint >/dev/null 2>&1; then
      _rss_extract_atom_via_xmllint "$xml_file"
      return $?
    fi
    _rss_extract_atom_via_sed "$xml_file"
    return $?
  fi

  # RSS 格式 — 優先使用 Python（效率最高，O(n)）
  if command -v python3 >/dev/null 2>&1; then
    _rss_extract_via_python "$xml_file"
    return $?
  fi

  # 回退到 xmllint（效率差，O(n²)，僅在無 Python 時使用）
  if command -v xmllint >/dev/null 2>&1; then
    _rss_extract_via_xmllint "$xml_file"
    return $?
  fi

  # 最終回退到 sed 簡易解析
  _rss_extract_via_sed "$xml_file"
}

########################################
# RSS 格式解析器
########################################

# 使用 Python 解析 RSS（高效）— 一次解析，O(n) 輸出 JSONL
_rss_extract_via_python() {
  local xml_file="$1"

  python3 -c '
import xml.etree.ElementTree as ET
import json
import sys

def get_text(elem, tag):
    child = elem.find(tag)
    return (child.text or "") if child is not None else ""

tree = ET.parse(sys.argv[1])
for item in tree.findall(".//item"):
    link = get_text(item, "link")
    link = link.replace("/./", "/")  # URL 正規化
    obj = {
        "title": get_text(item, "title"),
        "link": link,
        "description": get_text(item, "description"),
        "pubDate": get_text(item, "pubDate")
    }
    print(json.dumps(obj, ensure_ascii=False))
' "$xml_file"
}

# 使用 xmllint 解析 RSS（已棄用，保留作為回退）— 效率差，O(n²)
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
    link="${link//\/.\//\/}"  # URL 正規化：移除 URL 中的 /./ 路徑片段
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

# 使用 sed 簡易解析 RSS（回退方案）— 輸出 JSONL
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
        link="${link//\/.\//\/}"  # URL 正規化：移除 URL 中的 /./ 路徑片段
      elif [[ "$line" =~ \<description\>(.*)\</description\> ]]; then
        description="${BASH_REMATCH[1]}"
      elif [[ "$line" =~ \<pubDate\>(.*)\</pubDate\> ]]; then
        pubDate="${BASH_REMATCH[1]}"
      fi
    fi
  done < "$xml_file"
}

########################################
# Atom 格式解析器
########################################

# 使用 Python 解析 Atom（高效）— 一次解析，O(n) 輸出 JSONL
_rss_extract_atom_via_python() {
  local xml_file="$1"

  python3 -c '
import xml.etree.ElementTree as ET
import json
import sys

tree = ET.parse(sys.argv[1])
root = tree.getroot()

# 處理 Atom 命名空間
ns = ""
if root.tag.startswith("{"):
    ns = root.tag.split("}")[0] + "}"

def find_text(elem, tag):
    child = elem.find(ns + tag)
    return (child.text or "") if child is not None else ""

def find_link(elem):
    # Atom <link> 使用 href 屬性
    for link in elem.findall(ns + "link"):
        href = link.get("href", "")
        rel = link.get("rel", "alternate")
        if rel == "alternate" and href:
            return href
    # fallback: 任意 link
    for link in elem.findall(ns + "link"):
        href = link.get("href", "")
        if href:
            return href
    return ""

for entry in root.findall(ns + "entry"):
    link = find_link(entry)
    link = link.replace("/./", "/")  # URL 正規化
    title = find_text(entry, "title")
    summary = find_text(entry, "summary")
    if not summary:
        summary = find_text(entry, "content")
    pub_date = find_text(entry, "updated")
    if not pub_date:
        pub_date = find_text(entry, "published")
    obj = {
        "title": title,
        "link": link,
        "description": summary,
        "pubDate": pub_date
    }
    print(json.dumps(obj, ensure_ascii=False))
' "$xml_file"
}

# 使用 xmllint 解析 Atom 格式 — 輸出 JSONL
_rss_extract_atom_via_xmllint() {
  local xml_file="$1"

  # Atom 命名空間處理：移除命名空間以簡化 XPath
  local tmp_file
  tmp_file="$(mktemp)"
  sed 's/ xmlns="[^"]*"//g; s/ xmlns:[a-zA-Z]*="[^"]*"//g' "$xml_file" > "$tmp_file"

  local count
  count="$(xmllint --xpath 'count(//entry)' "$tmp_file" 2>/dev/null)" || {
    rm -f "$tmp_file"
    # 回退到 sed
    _rss_extract_atom_via_sed "$xml_file"
    return $?
  }

  for ((i=1; i<=count; i++)); do
    local title link description pubDate
    title="$(xmllint --xpath "string(//entry[$i]/title)" "$tmp_file" 2>/dev/null || echo "")"

    # Atom <link> 可能是 href 屬性或文字內容
    link="$(xmllint --xpath "string(//entry[$i]/link/@href)" "$tmp_file" 2>/dev/null || echo "")"
    if [[ -z "$link" ]]; then
      link="$(xmllint --xpath "string(//entry[$i]/link)" "$tmp_file" 2>/dev/null || echo "")"
    fi
    link="${link//\/.\//\/}"  # URL 正規化

    # Atom 使用 <summary> 或 <content>
    description="$(xmllint --xpath "string(//entry[$i]/summary)" "$tmp_file" 2>/dev/null || echo "")"
    if [[ -z "$description" ]]; then
      description="$(xmllint --xpath "string(//entry[$i]/content)" "$tmp_file" 2>/dev/null || echo "")"
    fi

    # Atom 使用 <updated> 或 <published>
    pubDate="$(xmllint --xpath "string(//entry[$i]/updated)" "$tmp_file" 2>/dev/null || echo "")"
    if [[ -z "$pubDate" ]]; then
      pubDate="$(xmllint --xpath "string(//entry[$i]/published)" "$tmp_file" 2>/dev/null || echo "")"
    fi

    jq -c -n \
      --arg title "$title" \
      --arg link "$link" \
      --arg description "$description" \
      --arg pubDate "$pubDate" \
      '{title: $title, link: $link, description: $description, pubDate: $pubDate}'
  done

  rm -f "$tmp_file"
}

# 使用 sed 簡易解析 Atom 格式（回退方案）— 輸出 JSONL
_rss_extract_atom_via_sed() {
  local xml_file="$1"

  local in_entry=false
  local title="" link="" description="" pubDate=""

  while IFS= read -r line; do
    if [[ "$line" =~ \<entry ]]; then
      in_entry=true
      title="" link="" description="" pubDate=""
      continue
    fi

    if [[ "$line" =~ \</entry\> ]]; then
      in_entry=false
      # 清理 CDATA 和 HTML entities
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

    if [[ "$in_entry" == "true" ]]; then
      if [[ "$line" =~ \<title[^\>]*\>(.*)\</title\> ]]; then
        title="${BASH_REMATCH[1]}"
      elif [[ "$line" =~ href=\"([^\"]+)\" ]] && [[ "$line" =~ \<link ]]; then
        link="${BASH_REMATCH[1]}"
        link="${link//\/.\//\/}"  # URL 正規化
      elif [[ -z "$link" ]] && [[ "$line" =~ \<link\>(.*)\</link\> ]]; then
        link="${BASH_REMATCH[1]}"
        link="${link//\/.\//\/}"  # URL 正規化
      elif [[ "$line" =~ \<summary[^\>]*\>(.*)\</summary\> ]]; then
        description="${BASH_REMATCH[1]}"
      elif [[ -z "$description" ]] && [[ "$line" =~ \<content[^\>]*\>(.*)\</content\> ]]; then
        description="${BASH_REMATCH[1]}"
      elif [[ "$line" =~ \<updated\>(.*)\</updated\> ]]; then
        pubDate="${BASH_REMATCH[1]}"
      elif [[ -z "$pubDate" ]] && [[ "$line" =~ \<published\>(.*)\</published\> ]]; then
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

  # 檢查是否包含基本 RSS 結構（RSS 1.0/2.0、Atom、RDF）
  if ! grep -q '<rss\|<feed\|<channel\|<rdf:RDF' "$xml_file" 2>/dev/null; then
    echo "❌ [rss_validate] 不是有效的 RSS/Atom 格式：$xml_file" >&2
    return 1
  fi

  return 0
}
