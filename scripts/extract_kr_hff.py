#!/usr/bin/env python3
"""
kr_hff 萃取腳本 — 依據 Layer CLAUDE.md 規則將 JSONL 轉換為 .md 檔

用法：
  python3 extract_kr_hff.py                    # 使用 latest.jsonl，跳過已存在
  python3 extract_kr_hff.py <jsonl_file>       # 指定 JSONL 檔案
  python3 extract_kr_hff.py --delta <jsonl>    # Delta 模式（自動 force）
  python3 extract_kr_hff.py --force            # 強制覆蓋已存在的檔案
"""
import json, os, sys, re, argparse
from datetime import datetime, timezone

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_DIR = os.path.join(BASE_DIR, "docs/Extractor/kr_hff")
RAW_DIR = os.path.join(OUTPUT_DIR, "raw")
LATEST_LINK = os.path.join(RAW_DIR, "latest.jsonl")
SOURCE_URL = "https://www.data.go.kr/data/15056760/openapi.do"

# Category 推斷規則 (from CLAUDE.md)
CATEGORY_RULES = [
    (["유산균", "프로바이오틱스", "비피더스"], "probiotics"),
    (["오메가", "EPA", "DHA", "지방산"], "omega_fatty_acids"),
    (["인삼", "홍삼", "녹차", "쏘팔메토", "식물"], "botanicals"),
    (["비타민", "미네랄", "칼슘", "철", "아연", "마그네슘"], "vitamins_minerals"),
    (["단백질", "아미노산", "콜라겐"], "protein_amino"),
    (["운동", "체력", "근력", "스포츠"], "sports_fitness"),
]

# Product Form 推斷規則
FORM_RULES = [
    (["연질캡슐"], "softgel"),
    (["캡슐"], "capsule"),
    (["정제"], "tablet"),
    (["분말"], "powder"),
    (["액상", "액제"], "liquid"),
    (["젤리"], "gummy"),
]

def s(val):
    """Safely convert to string, handling None."""
    return str(val).strip() if val is not None else ""

def infer_category(main_fnctn):
    if not main_fnctn:
        return "other"
    matched_cats = set()
    for keywords, cat in CATEGORY_RULES:
        for kw in keywords:
            if kw in main_fnctn:
                matched_cats.add(cat)
                break
    if len(matched_cats) == 0:
        return "other"
    if len(matched_cats) == 1:
        return matched_cats.pop()
    return "specialty"

def infer_product_form(sungsang):
    if not sungsang:
        return "other"
    for keywords, form in FORM_RULES:
        for kw in keywords:
            if kw in sungsang:
                return form
    return "other"

def check_review_needed(item):
    reasons = []
    if not s(item.get("PRDUCT")):
        reasons.append("PRDUCT 為空")
    if not s(item.get("MAIN_FNCTN")):
        reasons.append("MAIN_FNCTN 為空")
    return reasons

def get_existing_source_ids():
    ids = set()
    for root, dirs, files in os.walk(OUTPUT_DIR):
        if "raw" in root:
            continue
        for f in files:
            if f.endswith(".md"):
                path = os.path.join(root, f)
                with open(path, "r", encoding="utf-8") as fh:
                    for line in fh:
                        if line.startswith("source_id:"):
                            sid = line.split(":", 1)[1].strip().strip('"')
                            ids.add(sid)
                            break
    return ids

def resolve_jsonl_file(jsonl_arg):
    """Resolve the JSONL file path from argument or latest.jsonl symlink"""
    if jsonl_arg:
        return jsonl_arg
    if os.path.islink(LATEST_LINK) and os.path.exists(LATEST_LINK):
        return os.path.realpath(LATEST_LINK)
    # Fallback: find most recent hff-*.jsonl
    jsonl_files = sorted(
        [f for f in os.listdir(RAW_DIR) if f.startswith("hff-") and f.endswith(".jsonl")],
        reverse=True
    )
    if jsonl_files:
        return os.path.join(RAW_DIR, jsonl_files[0])
    return None

def process(jsonl_file, force=False):
    if not os.path.exists(jsonl_file):
        print(f"JSONL not found: {jsonl_file}", file=sys.stderr)
        sys.exit(1)

    print(f"📂 JSONL 檔案：{jsonl_file}")
    print(f"📁 輸出目錄：{OUTPUT_DIR}")
    print(f"🔄 強制覆蓋：{'是' if force else '否'}")
    print()

    existing_ids = set() if force else get_existing_source_ids()
    if not force:
        print(f"📊 既有 .md 檔案：{len(existing_ids)} 筆")

    now = datetime.now(timezone.utc).isoformat()
    stats = {"total": 0, "skipped": 0, "extracted": 0, "review_needed": 0, "errors": 0}

    with open(jsonl_file, "r", encoding="utf-8", errors="replace") as f:
        for line_num, raw_line in enumerate(f, 1):
            stats["total"] += 1
            raw_line = raw_line.strip()
            if not raw_line:
                continue
            try:
                rec = json.loads(raw_line)
            except json.JSONDecodeError as e:
                print(f"  Line {line_num}: JSON parse error: {e}", file=sys.stderr)
                stats["errors"] += 1
                continue

            item = rec.get("item", rec)  # kr_hff wraps data in "item"

            source_id = str(item.get("STTEMNT_NO", "")).strip()
            if not source_id:
                stats["errors"] += 1
                continue

            if not force and source_id in existing_ids:
                stats["skipped"] += 1
                continue

            product_name = s(item.get("PRDUCT"))
            entrps = s(item.get("ENTRPS"))
            regist_dt = s(item.get("REGIST_DT"))
            distb_pd = s(item.get("DISTB_PD"))
            sungsang = s(item.get("SUNGSANG"))
            srv_use = s(item.get("SRV_USE"))
            main_fnctn = s(item.get("MAIN_FNCTN"))
            intake_hint1 = s(item.get("INTAKE_HINT1"))
            base_standard = s(item.get("BASE_STANDARD"))

            category = infer_category(main_fnctn)
            product_form = infer_product_form(sungsang)

            # Escape double quotes for YAML frontmatter
            safe_source_id = source_id.replace('"', '\\"')
            safe_product_name = product_name.replace('"', '\\"')
            safe_entrps = entrps.replace('"', '\\"')
            safe_regist_dt = regist_dt.replace('"', '\\"')

            review_reasons = check_review_needed(item)
            review_prefix = ""
            if review_reasons:
                review_prefix = "[REVIEW_NEEDED]\n\n"
                stats["review_needed"] += 1

            cat_dir = os.path.join(OUTPUT_DIR, category)
            os.makedirs(cat_dir, exist_ok=True)

            md = f"""{review_prefix}---
source_id: "{safe_source_id}"
source_layer: "kr_hff"
source_url: "{SOURCE_URL}"
market: "kr"
product_name: "{safe_product_name}"
brand: "{safe_entrps}"
manufacturer: "{safe_entrps}"
category: "{category}"
product_form: "{product_form}"
date_entered: "{safe_regist_dt}"
fetched_at: "{now}"
---

# {product_name}

## 基本資訊
- 製造商：{entrps}
- 劑型：{product_form}
- 市場：韓國
- 品目番號：{source_id}
- 性狀：{sungsang}

## 主要功能
{main_fnctn if main_fnctn else "（無資料）"}

## 用法用量
{srv_use if srv_use else "（無資料）"}

## 注意事項
{intake_hint1 if intake_hint1 else "（無資料）"}

## 規格基準
{base_standard if base_standard else "（無資料）"}

## 備註
{f"流通期限：{distb_pd}" if distb_pd else "（無流通期限資訊）"}
"""

            safe_id = re.sub(r'[^\w\-.]', '_', source_id)
            filepath = os.path.join(cat_dir, f"{safe_id}.md")
            with open(filepath, "w", encoding="utf-8") as out:
                out.write(md)

            existing_ids.add(source_id)
            stats["extracted"] += 1

            if stats["extracted"] % 1000 == 0:
                print(f"  進度：{stats['extracted']} 筆已萃取...")

    print(f"\n━━━ kr_hff 萃取完成 ━━━")
    print(f"  總行數：{stats['total']}")
    print(f"  跳過（已存在）：{stats['skipped']}")
    print(f"  新萃取：{stats['extracted']}")
    print(f"  REVIEW_NEEDED：{stats['review_needed']}")
    print(f"  錯誤：{stats['errors']}")

def main():
    parser = argparse.ArgumentParser(description="kr_hff JSONL → Markdown 萃取")
    parser.add_argument("jsonl", nargs="?", help="JSONL 檔案路徑（預設使用 latest.jsonl）")
    parser.add_argument("-f", "--force", action="store_true", help="強制覆蓋已存在的檔案")
    parser.add_argument("-d", "--delta", action="store_true", help="Delta 模式（自動啟用 --force）")
    args = parser.parse_args()

    force = args.force or args.delta
    jsonl_file = resolve_jsonl_file(args.jsonl)

    if not jsonl_file:
        print("❌ 找不到 JSONL 檔案", file=sys.stderr)
        print("   請指定檔案路徑或確認 raw/latest.jsonl 存在", file=sys.stderr)
        sys.exit(1)

    process(jsonl_file, force=force)

if __name__ == "__main__":
    main()
