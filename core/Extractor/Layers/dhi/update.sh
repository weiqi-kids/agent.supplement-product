#!/bin/bash
# dhi 資料更新腳本 - 批次處理版本
# 職責：Qdrant 更新 + REVIEW_NEEDED 檢查

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../../.." && pwd)"

source "$PROJECT_ROOT/lib/args.sh"
source "$PROJECT_ROOT/lib/core.sh"
source "$PROJECT_ROOT/lib/qdrant.sh"
source "$PROJECT_ROOT/lib/chatgpt.sh"

require_cmd jq

LAYER_NAME="dhi"
DOCS_DIR="$PROJECT_ROOT/docs/Extractor/$LAYER_NAME"
BATCH_SIZE=200
LAST_UPDATE_FILE="$DOCS_DIR/.last_qdrant_update"

# === 解析參數 ===
parse_args "$@"
arg_optional "full" FULL_MODE "false"
arg_optional "category" CATEGORY_FILTER ""

########################################
# Helper: 批次 ID 轉 UUID
########################################
_batch_ids_to_uuids() {
  python3 -c '
import sys
import uuid

for line in sys.stdin:
    point_id = line.strip()
    if not point_id:
        continue
    point_uuid = str(uuid.uuid5(uuid.NAMESPACE_URL, point_id))
    print(point_uuid)
'
}

# === 取得要處理的 .md 檔案 ===
MD_FILES=()
POSITIONAL_ARGS=("${POSITIONAL_ARGS[@]:-}")

# 決定搜尋目錄
if [[ -n "$CATEGORY_FILTER" ]]; then
  SEARCH_DIR="$DOCS_DIR/$CATEGORY_FILTER"
else
  SEARCH_DIR="$DOCS_DIR"
fi

if [[ ${#POSITIONAL_ARGS[@]} -gt 0 ]]; then
  MD_FILES=("${POSITIONAL_ARGS[@]}")
elif [[ "$FULL_MODE" != "false" ]] || [[ ! -f "$LAST_UPDATE_FILE" ]]; then
  echo "📂 全量模式：掃描所有 .md 檔案"
  while IFS= read -r -d '' f; do
    MD_FILES+=("$f")
  done < <(find "$SEARCH_DIR" -name "*.md" -not -path "*/raw/*" -type f -print0 2>/dev/null)
else
  echo "📂 增量模式：只處理新增/修改的檔案"
  while IFS= read -r -d '' f; do
    MD_FILES+=("$f")
  done < <(find "$SEARCH_DIR" -name "*.md" -not -path "*/raw/*" -type f -newer "$LAST_UPDATE_FILE" -print0 2>/dev/null)
fi

if [[ ${#MD_FILES[@]} -eq 0 ]]; then
  echo "ℹ️  沒有找到 .md 檔案需要處理"
  exit 0
fi

echo "📋 待處理：${#MD_FILES[@]} 個 .md 檔案"

# === Qdrant 更新 ===
QDRANT_OK=false
if [[ -n "${QDRANT_URL:-}" ]]; then
  if qdrant_init_env 2>/dev/null; then
    QDRANT_OK=true
    echo "✅ Qdrant 連線就緒"
    COLLECTION="${QDRANT_COLLECTION:-supplement-product}"
    DIMENSION="${EMBEDDING_DIMENSION:-1536}"
    qdrant_create_collection "$COLLECTION" "$DIMENSION" 2>/dev/null || true
  else
    echo "⚠️  Qdrant 連線失敗，跳過向量更新" >&2
  fi
fi

EMBED_OK=false
if [[ -n "${OPENAI_API_KEY:-}" ]]; then
  if chatgpt_init_env 2>/dev/null; then
    EMBED_OK=true
    echo "✅ OpenAI embedding 就緒"
  fi
fi

# === 處理計數器 ===
PROCESSED=0
SKIPPED=0
ERRORS=0

# === 批次處理主循環 ===
total_files="${#MD_FILES[@]}"
batch_start=0

while [[ $batch_start -lt $total_files ]]; do
  batch_end=$((batch_start + BATCH_SIZE))
  if [[ $batch_end -gt $total_files ]]; then
    batch_end=$total_files
  fi

  echo ""
  echo "處理批次：$((batch_start + 1))-${batch_end}/${total_files}"

  # === Phase 1: 收集 ID 與檔案路徑映射 ===
  declare -a point_ids=()
  declare -a batch_files=()

  for ((i=batch_start; i<batch_end; i++)); do
    md_file="${MD_FILES[$i]}"

    if [[ ! -f "$md_file" ]]; then
      ((ERRORS++)) || true
      continue
    fi

    batch_files+=("$md_file")

    SOURCE_ID="$(sed -n 's/^source_id: *"\{0,1\}\([^"]*\)"\{0,1\} *$/\1/p' "$md_file" | head -1)"
    if [[ -z "$SOURCE_ID" ]]; then
      echo "⚠️  無法提取 source_id：$md_file" >&2
      ((ERRORS++)) || true
      continue
    fi

    POINT_ID="dhi-${SOURCE_ID}"
    point_ids+=("$POINT_ID")
  done

  if [[ ${#point_ids[@]} -eq 0 ]]; then
    echo "⚠️  本批次無有效檔案，跳過"
    batch_start=$batch_end
    continue
  fi

  # 批次轉換 ID 到 UUID
  declare -a point_uuids=()
  while IFS= read -r uuid; do
    [[ -z "$uuid" ]] && continue
    point_uuids+=("$uuid")
  done < <(printf '%s\n' "${point_ids[@]}" | _batch_ids_to_uuids)

  if [[ ${#point_uuids[@]} -ne ${#point_ids[@]} ]]; then
    echo "❌ UUID 轉換失敗：期望 ${#point_ids[@]} 個，得到 ${#point_uuids[@]} 個" >&2
    ((ERRORS+=${#batch_files[@]})) || true
    batch_start=$batch_end
    continue
  fi

  # === Phase 2: 批次查重 ===
  declare -a indices_to_process=()

  if [[ "$QDRANT_OK" == "true" && "$EMBED_OK" == "true" ]]; then
    IDS_JSON="$(printf '%s\n' "${point_uuids[@]}" | jq -Rsc 'split("\n") | map(select(length > 0))')"

    EXISTING_IDS="$(qdrant_get_existing_ids "$COLLECTION" "$IDS_JSON" 2>/dev/null)" || {
      echo "⚠️  批次查詢失敗，假設所有檔案都需處理" >&2
      EXISTING_IDS="[]"
    }

    for ((i=0; i<${#point_uuids[@]}; i++)); do
      uuid="${point_uuids[$i]}"

      if echo "$EXISTING_IDS" | jq -e --arg uuid "$uuid" '. | index($uuid)' >/dev/null 2>&1; then
        ((SKIPPED++)) || true
      else
        indices_to_process+=("$i")
      fi
    done
  else
    for ((i=0; i<${#batch_files[@]}; i++)); do
      indices_to_process+=("$i")
    done
    ((PROCESSED+=${#indices_to_process[@]})) || true
    batch_start=$batch_end
    continue
  fi

  if [[ ${#indices_to_process[@]} -eq 0 ]]; then
    echo "✓ 本批次所有檔案已存在，跳過"
    batch_start=$batch_end
    continue
  fi

  echo "需處理：${#indices_to_process[@]} 個檔案"

  # === Phase 3: 提取文本與 metadata ===
  tmp_texts_file="$(mktemp)"
  declare -a process_metadata=()

  jq -n '[]' > "$tmp_texts_file"

  for idx in "${indices_to_process[@]}"; do
    file="${batch_files[$idx]}"
    SOURCE_ID="$(sed -n 's/^source_id: *"\{0,1\}\([^"]*\)"\{0,1\} *$/\1/p' "$file" | head -1)"
    DRUG="$(sed -n 's/^drug: *"\{0,1\}\([^"]*\)"\{0,1\} *$/\1/p' "$file" | head -1)"
    SUPPLEMENT="$(sed -n 's/^supplement: *"\{0,1\}\([^"]*\)"\{0,1\} *$/\1/p' "$file" | head -1)"
    SUPPLEMENT_CATEGORY="$(sed -n 's/^supplement_category: *"\{0,1\}\([^"]*\)"\{0,1\} *$/\1/p' "$file" | head -1)"
    SEVERITY="$(sed -n 's/^severity: *"\{0,1\}\([^"]*\)"\{0,1\} *$/\1/p' "$file" | head -1)"
    SOURCE_URL="$(sed -n 's/^source_url: *"\{0,1\}\([^"]*\)"\{0,1\} *$/\1/p' "$file" | head -1)"
    PUB_DATE="$(sed -n 's/^pub_date: *"\{0,1\}\([^"]*\)"\{0,1\} *$/\1/p' "$file" | head -1)"
    FETCHED_AT="$(sed -n 's/^fetched_at: *"\{0,1\}\([^"]*\)"\{0,1\} *$/\1/p' "$file" | head -1)"

    BODY_TEXT="$(sed -n '/^---$/,/^---$/!p' "$file" | head -500)"

    jq --arg text "$BODY_TEXT" '. += [$text]' "$tmp_texts_file" > "${tmp_texts_file}.tmp"
    mv "${tmp_texts_file}.tmp" "$tmp_texts_file"

    METADATA="$(jq -nc \
      --arg source_id "$SOURCE_ID" \
      --arg drug "$DRUG" \
      --arg supplement "$SUPPLEMENT" \
      --arg supplement_category "$SUPPLEMENT_CATEGORY" \
      --arg severity "$SEVERITY" \
      --arg source_url "$SOURCE_URL" \
      --arg pub_date "$PUB_DATE" \
      --arg fetched_at "$FETCHED_AT" \
      '{
        source_id: $source_id,
        source_layer: "dhi",
        interaction_type: "DHI",
        source_url: $source_url,
        market: "global",
        drug: $drug,
        supplement: $supplement,
        supplement_category: $supplement_category,
        severity: $severity,
        date_entered: $pub_date,
        fetched_at: $fetched_at
      }'
    )"
    process_metadata+=("$METADATA")
  done

  # === Phase 4: 批次 embedding ===
  echo "產生 embeddings..."
  tmp_embeddings_file="$(mktemp)"

  if ! chatgpt_embed_batch "$tmp_texts_file" > "$tmp_embeddings_file" 2>/dev/null; then
    echo "❌ 批次 embedding 失敗，本批次計入錯誤" >&2
    ((ERRORS+=${#indices_to_process[@]})) || true
    rm -f "$tmp_texts_file" "$tmp_embeddings_file"
    batch_start=$batch_end
    continue
  fi

  # === Phase 5: 批次 upsert ===
  echo "批次寫入 Qdrant..."

  POINTS_JSON="$(
    paste \
      <(for idx in "${indices_to_process[@]}"; do echo "${point_uuids[$idx]}"; done) \
      <(printf '%s\n' "${process_metadata[@]}") \
      <(jq -c '.[]' "$tmp_embeddings_file") \
    | while IFS=$'\t' read -r uuid metadata_json embedding_json; do
        jq -n \
          --arg id "$uuid" \
          --argjson vector "$embedding_json" \
          --argjson payload "$metadata_json" \
          '{
            id: $id,
            vector: $vector,
            payload: $payload
          }'
      done | jq -sc '.'
  )"

  if qdrant_upsert_points_batch "$COLLECTION" "$POINTS_JSON" 2>/dev/null; then
    ((PROCESSED+=${#indices_to_process[@]})) || true
    echo "✓ 成功寫入 ${#indices_to_process[@]} 個 points"
  else
    echo "❌ 批次 upsert 失敗" >&2
    ((ERRORS+=${#indices_to_process[@]})) || true
  fi

  rm -f "$tmp_texts_file" "$tmp_embeddings_file"

  batch_start=$batch_end
done

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📊 Update 結果："
echo "   已處理：${PROCESSED}"
echo "   已跳過（已存在）：${SKIPPED}"
echo "   錯誤：${ERRORS}"

# === REVIEW_NEEDED 檢查 ===
REVIEW_FILES=""
while IFS= read -r -d '' f; do
  if grep -q "\[REVIEW_NEEDED\]" "$f" 2>/dev/null; then
    REVIEW_FILES+="  - $f\n"
  fi
done < <(find "$DOCS_DIR" -name "*.md" -not -path "*/raw/*" -type f -print0 2>/dev/null)

if [[ -n "$REVIEW_FILES" ]]; then
  echo ""
  echo "⚠️  需要審核："
  echo -e "$REVIEW_FILES"
fi

# === 更新時間戳 ===
if [[ "$QDRANT_OK" == "true" && "$EMBED_OK" == "true" && $ERRORS -eq 0 ]]; then
  touch "$LAST_UPDATE_FILE"
  echo "📌 已更新時間戳：$LAST_UPDATE_FILE"
fi

echo ""
echo "✅ Update completed: $LAYER_NAME"
