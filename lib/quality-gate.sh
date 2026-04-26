#!/bin/bash
# quality-gate.sh - 品質關卡驗證腳本（通用版）
# 用途：提供可執行的驗證指令，取代手動勾選
# 使用方式：source lib/quality-gate.sh && qg_run_all

set -euo pipefail

# 顏色定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 計數器
PASS_COUNT=0
FAIL_COUNT=0
RESULTS=()

# === 輔助函式 ===

qg_pass() {
    local check_name="$1"
    PASS_COUNT=$((PASS_COUNT + 1))
    RESULTS+=("✅|$check_name|PASS")
    echo -e "${GREEN}✅ PASS${NC}: $check_name"
}

qg_fail() {
    local check_name="$1"
    local reason="$2"
    FAIL_COUNT=$((FAIL_COUNT + 1))
    RESULTS+=("❌|$check_name|$reason")
    echo -e "${RED}❌ FAIL${NC}: $check_name - $reason"
}

qg_warn() {
    local check_name="$1"
    local note="$2"
    RESULTS+=("⚠️|$check_name|$note")
    echo -e "${YELLOW}⚠️ WARN${NC}: $check_name - $note"
}

# === 1. YMYL 檢查 ===

qg_check_ymyl() {
    echo "=== YMYL 欄位檢查 ==="
    local docs_dir="docs"
    local missing_files=()

    while IFS= read -r file; do
        [[ "$file" == *"/raw/"* ]] && continue
        [[ "$file" == *"lessons-learned.md" ]] && continue

        if ! grep -q "lastReviewed:" "$file" 2>/dev/null; then
            missing_files+=("$file (缺少 lastReviewed)")
        fi
        if ! grep -q "reviewedBy:" "$file" 2>/dev/null; then
            missing_files+=("$file (缺少 reviewedBy)")
        fi
    done < <(find "$docs_dir" -name "*.md" -type f 2>/dev/null | grep -v "/raw/")

    if [[ ${#missing_files[@]} -eq 0 ]]; then
        qg_pass "YMYL 欄位完整"
    else
        qg_fail "YMYL 欄位缺失" "${#missing_files[@]} 個檔案缺少 YMYL 欄位"
        for f in "${missing_files[@]:0:5}"; do
            echo "  - $f"
        done
        [[ ${#missing_files[@]} -gt 5 ]] && echo "  ... 還有 $((${#missing_files[@]} - 5)) 個"
    fi
}

# === 2. Frontmatter 檢查 ===

qg_check_frontmatter() {
    echo "=== Frontmatter 必填欄位檢查 ==="
    local docs_dir="docs/Extractor"
    local missing_nav_exclude=()

    if [[ ! -d "$docs_dir" ]]; then
        qg_warn "Frontmatter" "docs/Extractor 目錄不存在"
        return
    fi

    while IFS= read -r file; do
        [[ "$file" == *"/raw/"* ]] && continue
        [[ "$file" == *"index.md" ]] && continue

        if ! grep -q "nav_exclude: true" "$file" 2>/dev/null; then
            missing_nav_exclude+=("$file")
        fi
    done < <(find "$docs_dir" -name "*.md" -type f 2>/dev/null | grep -v "/raw/")

    if [[ ${#missing_nav_exclude[@]} -eq 0 ]]; then
        qg_pass "Frontmatter nav_exclude 完整"
    else
        qg_fail "Frontmatter 缺少 nav_exclude" "${#missing_nav_exclude[@]} 個檔案"
        for f in "${missing_nav_exclude[@]:0:5}"; do
            echo "  - $f"
        done
    fi
}

# === 3. 連結格式檢查（離線檢查） ===

qg_check_link_format() {
    echo "=== 連結格式檢查（尾部斜線）==="
    local docs_dir="docs"
    local bad_links=()

    while IFS= read -r file; do
        if grep -E '\]\([^)]+/\)' "$file" 2>/dev/null | grep -v "http" | grep -q .; then
            bad_links+=("$file")
        fi
    done < <(find "$docs_dir" -name "*.md" -type f 2>/dev/null)

    if [[ ${#bad_links[@]} -eq 0 ]]; then
        qg_pass "連結格式正確（無尾部斜線）"
    else
        qg_fail "連結帶尾部斜線" "${#bad_links[@]} 個檔案"
        for f in "${bad_links[@]:0:3}"; do
            echo "  - $f"
            grep -n -E '\]\([^)]+/\)' "$f" 2>/dev/null | head -2 | sed 's/^/    /'
        done
    fi
}

# === 4. Git 狀態檢查 ===

qg_check_git_status() {
    echo "=== Git 狀態檢查 ==="

    local uncommitted
    uncommitted=$(git status --porcelain 2>/dev/null | wc -l | tr -d ' ')

    if [[ "$uncommitted" -eq 0 ]]; then
        qg_pass "所有變更已提交"
    else
        qg_fail "有未提交的變更" "$uncommitted 個檔案"
        git status --porcelain | head -5
    fi

    local ahead
    ahead=$(git rev-list --count @{upstream}..HEAD 2>/dev/null || echo "0")

    if [[ "$ahead" -eq 0 ]]; then
        qg_pass "所有提交已推送"
    else
        qg_fail "有未推送的提交" "$ahead 個提交"
    fi
}

# === 5. Schema 檢查（首頁） ===

qg_check_schema_index() {
    echo "=== Schema 檢查（首頁）==="
    local index_file="docs/index.md"

    if [[ ! -f "$index_file" ]]; then
        qg_fail "首頁不存在" "$index_file"
        return
    fi

    local required_schemas=("WebSite" "WebPage")
    local missing_schemas=()

    for schema in "${required_schemas[@]}"; do
        if ! grep -q "'@type': '$schema'" "$index_file" 2>/dev/null; then
            missing_schemas+=("$schema")
        fi
    done

    if [[ ${#missing_schemas[@]} -eq 0 ]]; then
        qg_pass "首頁 Schema 完整"
    else
        qg_fail "首頁缺少 Schema" "${missing_schemas[*]}"
    fi
}

# === 6. 內容更新確認 ===

qg_check_content_updated() {
    echo "=== 內容更新確認 ==="
    local today
    today=$(date +%Y-%m-%d)

    if grep -q "$today" docs/index.md 2>/dev/null; then
        qg_pass "首頁包含今日日期"
    else
        qg_warn "首頁日期" "首頁未包含今日日期 $today（可能正常）"
    fi
}

# === 7. 萃取結果統計（自動發現 Layers） ===

qg_check_extraction_stats() {
    echo "=== 萃取結果統計 ==="
    local total=0

    if [[ ! -d "docs/Extractor" ]]; then
        qg_warn "萃取結果" "docs/Extractor 目錄不存在"
        return
    fi

    for layer_dir in docs/Extractor/*/; do
        [[ ! -d "$layer_dir" ]] && continue
        local layer_name
        layer_name=$(basename "$layer_dir")
        local count
        count=$(find "$layer_dir" -name "*.md" -type f 2>/dev/null | grep -v "index.md" | grep -v "/raw/" | wc -l | tr -d ' ')
        total=$((total + count))
        echo "  $layer_name: $count 篇"
    done

    echo "  總計: $total 篇萃取結果"

    if [[ $total -gt 0 ]]; then
        qg_pass "萃取結果存在"
    else
        qg_warn "萃取結果" "總數為 0（可能是正常的）"
    fi
}

# === 8. E-E-A-T 外部連結 ===

qg_check_eeat_links() {
    echo "=== E-E-A-T 外部連結檢查 ==="
    local index_file="docs/index.md"

    local gov_links
    gov_links=$(grep -o 'https://[^)]*\.gov[^)]*' "$index_file" 2>/dev/null | wc -l | tr -d ' ')

    if [[ "$gov_links" -ge 2 ]]; then
        qg_pass "高權威連結足夠 ($gov_links 個 .gov)"
    else
        qg_warn "高權威連結不足" "只有 $gov_links 個 .gov 連結"
    fi
}

# === 執行所有檢查 ===

qg_run_all() {
    echo ""
    echo "======================================"
    echo "     品質關卡驗證 - Quality Gate"
    echo "======================================"
    echo ""

    PASS_COUNT=0
    FAIL_COUNT=0
    RESULTS=()

    qg_check_ymyl
    echo ""
    qg_check_frontmatter
    echo ""
    qg_check_link_format
    echo ""
    qg_check_git_status
    echo ""
    qg_check_schema_index
    echo ""
    qg_check_content_updated
    echo ""
    qg_check_extraction_stats
    echo ""
    qg_check_eeat_links
    echo ""

    # 輸出報告
    echo "======================================"
    echo "              檢查報告"
    echo "======================================"
    echo ""
    printf "| %-6s | %-30s | %-30s |\n" "狀態" "檢查項目" "結果"
    printf "|--------|--------------------------------|--------------------------------|\n"
    for result in "${RESULTS[@]}"; do
        IFS='|' read -r status check_name detail <<< "$result"
        printf "| %-6s | %-30s | %-30s |\n" "$status" "$check_name" "$detail"
    done
    echo ""

    local total=$((PASS_COUNT + FAIL_COUNT))
    echo "總結：$PASS_COUNT/$total 項通過"
    echo ""

    if [[ $FAIL_COUNT -eq 0 ]]; then
        echo -e "${GREEN}✅ 品質關卡通過！可以回報完成。${NC}"
        return 0
    else
        echo -e "${RED}❌ 品質關卡未通過！有 $FAIL_COUNT 項需要修正。${NC}"
        return 1
    fi
}

# 如果直接執行此腳本
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    qg_run_all
fi
