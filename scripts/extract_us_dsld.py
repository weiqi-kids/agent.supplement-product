#!/usr/bin/env python3
"""
us_dsld 萃取腳本 — 依據 Layer CLAUDE.md 規則將 JSONL 轉換為 .md 檔

用法：
  python3 extract_us_dsld.py                    # 使用 latest.jsonl，跳過已存在
  python3 extract_us_dsld.py <jsonl_file>       # 指定 JSONL 檔案
  python3 extract_us_dsld.py --delta <jsonl>    # Delta 模式（自動 force）
  python3 extract_us_dsld.py --force            # 強制覆蓋已存在的檔案
"""
import json, os, sys, re, argparse
from datetime import datetime, timezone

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_DIR = os.path.join(BASE_DIR, "docs/Extractor/us_dsld")
RAW_DIR = os.path.join(OUTPUT_DIR, "raw")
LATEST_LINK = os.path.join(RAW_DIR, "latest.jsonl")

# Category 映射 (from CLAUDE.md)
CATEGORY_MAP = {
    "A1299": "vitamins_minerals",   # Mineral
    "A1302": "vitamins_minerals",   # Vitamin
    "A1305": "protein_amino",       # Amino acid/Protein
    "A1306": "botanicals",          # Botanical
    "A1309": "other",               # Non-Nutrient/Non-Botanical
    "A1310": "omega_fatty_acids",   # Fat/Fatty Acid
    "A1315": "vitamins_minerals",   # Multi-Vitamin and Mineral (MVM)
    "A1317": "botanicals",          # Botanical with Nutrients
    "A1325": "specialty",           # Other Combinations
    "A1326": "other",               # Fiber and Other Nutrients
}

# Product Form 映射
FORM_MAP = {
    "tablet": "tablet",
    "pill": "tablet",
    "capsule": "capsule",
    "softgel": "softgel",
    "powder": "powder",
    "liquid": "liquid",
    "gummy": "gummy",
}

# Ingredient group keywords that suggest misclassification (for REVIEW_NEEDED rule #4)
INGREDIENT_CATEGORY_HINTS = {
    "vitamins_minerals": ["vitamin", "mineral", "calcium", "iron", "zinc"],
    "botanicals": ["botanical", "herbal", "plant", "extract"],
    "protein_amino": ["protein", "amino", "collagen", "whey"],
    "probiotics": ["probiotic", "lactobacillus", "bifidobacterium"],
    "omega_fatty_acids": ["omega", "fish oil", "dha", "epa", "fatty acid"],
}

def s(val):
    """Safely convert to string, handling None."""
    return str(val).strip() if val is not None else ""

def infer_category(product_type):
    if not product_type:
        return None  # triggers REVIEW_NEEDED
    langual_code = ""
    if isinstance(product_type, dict):
        langual_code = product_type.get("langualCode", "")
    elif isinstance(product_type, list) and product_type:
        langual_code = product_type[0].get("langualCode", "")
    return CATEGORY_MAP.get(langual_code, "other")

def infer_product_form(physical_state):
    if not physical_state:
        return "other"
    desc = ""
    if isinstance(physical_state, dict):
        desc = physical_state.get("langualCodeDescription", "")
    elif isinstance(physical_state, list) and physical_state:
        desc = physical_state[0].get("langualCodeDescription", "")
    desc_lower = desc.lower()
    for keyword, form in FORM_MAP.items():
        if keyword in desc_lower:
            return form
    return "other"

def check_should_be_different_category(category, ingredients):
    """REVIEW_NEEDED rule #4: other category but ingredients suggest otherwise"""
    if category != "other" or not ingredients:
        return False
    ing_text = " ".join(
        ((i.get("ingredientGroup") or "") + " " + (i.get("name") or "")).lower()
        for i in ingredients if isinstance(i, dict)
    )
    for cat, hints in INGREDIENT_CATEGORY_HINTS.items():
        for hint in hints:
            if hint in ing_text:
                return True
    return False

def check_review_needed(rec, category):
    reasons = []
    if rec.get("productType") is None:
        reasons.append("productType 為 null")
    if not rec.get("fullName", "").strip():
        reasons.append("fullName 為空")
    ingredients = rec.get("allIngredients", [])
    if isinstance(ingredients, list) and len(ingredients) == 0:
        reasons.append("allIngredients 為空陣列")
    if check_should_be_different_category(category, ingredients):
        reasons.append("category=other 但成分顯示應歸入其他分類")
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

def format_ingredients(ingredients):
    if not ingredients or not isinstance(ingredients, list):
        return "（無成分資料）"
    lines = []
    for ing in ingredients:
        if isinstance(ing, dict):
            name = ing.get("name") or "Unknown"
            group = ing.get("ingredientGroup") or ""
            notes = ing.get("notes") or ""
            line = f"- {name}"
            if group:
                line += f"（{group}）"
            if notes:
                line += f" — {notes}"
            lines.append(line)
    return "\n".join(lines) if lines else "（無成分資料）"

def format_claims(claims):
    if not claims or not isinstance(claims, list):
        return "（無宣稱資料）"
    lines = []
    for c in claims:
        if isinstance(c, dict):
            desc = c.get("langualCodeDescription") or str(c)
            lines.append(f"- {desc}")
        else:
            lines.append(f"- {c}")
    return "\n".join(lines) if lines else "（無宣稱資料）"

def format_net_contents(net_contents):
    if not net_contents or not isinstance(net_contents, list):
        return "N/A"
    parts = []
    for nc in net_contents:
        if isinstance(nc, dict):
            display = nc.get("display", str(nc))
            parts.append(display)
    return ", ".join(parts) if parts else "N/A"

def resolve_jsonl_file(jsonl_arg):
    """Resolve the JSONL file path from argument or latest.jsonl symlink"""
    if jsonl_arg:
        return jsonl_arg
    if os.path.islink(LATEST_LINK) and os.path.exists(LATEST_LINK):
        return os.path.realpath(LATEST_LINK)
    # Fallback: find most recent dsld-*.jsonl
    jsonl_files = sorted(
        [f for f in os.listdir(RAW_DIR) if f.startswith("dsld-") and f.endswith(".jsonl")],
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

    with open(jsonl_file, "r", encoding="utf-8") as f:
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

            source_id = str(rec.get("dsld_id", "")).strip()
            if not source_id:
                stats["errors"] += 1
                continue

            if not force and source_id in existing_ids:
                stats["skipped"] += 1
                continue

            full_name = s(rec.get("fullName"))
            brand_name = s(rec.get("brandName"))
            entry_date = s(rec.get("entryDate"))
            off_market = rec.get("offMarket", 0)
            market_status = "Off Market" if off_market else "On Market"
            net_contents = rec.get("netContents", [])
            ingredients = rec.get("allIngredients", [])
            claims_data = rec.get("claims", [])
            product_type = rec.get("productType")
            physical_state = rec.get("physicalState")

            category = infer_category(product_type)
            if category is None:
                category = "other"
            product_form = infer_product_form(physical_state)

            review_reasons = check_review_needed(rec, category)
            review_prefix = ""
            if review_reasons:
                review_prefix = "[REVIEW_NEEDED]\n\n"
                stats["review_needed"] += 1

            cat_dir = os.path.join(OUTPUT_DIR, category)
            os.makedirs(cat_dir, exist_ok=True)

            source_url = f"https://dsld.od.nih.gov/label/{source_id}"
            ingredients_text = format_ingredients(ingredients)
            claims_text = format_claims(claims_data)
            net_contents_text = format_net_contents(net_contents)

            # Escape double quotes in YAML values
            safe_name = full_name.replace('"', '\\"')
            safe_brand = brand_name.replace('"', '\\"')

            md = f"""{review_prefix}---
source_id: "{source_id}"
source_layer: "us_dsld"
source_url: "{source_url}"
market: "us"
product_name: "{safe_name}"
brand: "{safe_brand}"
manufacturer: "{safe_brand}"
category: "{category}"
product_form: "{product_form}"
date_entered: "{entry_date}"
fetched_at: "{now}"
---

# {full_name}

## 基本資訊
- 品牌：{brand_name}
- 劑型：{product_form}
- 市場：美國
- 上市狀態：{market_status}
- 淨含量：{net_contents_text}

## 成分
{ingredients_text}

## 宣稱
{claims_text}

## 備註
{f"REVIEW: {', '.join(review_reasons)}" if review_reasons else "無特殊備註"}
"""

            safe_id = re.sub(r'[^\w\-.]', '_', source_id)
            filepath = os.path.join(cat_dir, f"{safe_id}.md")
            with open(filepath, "w", encoding="utf-8") as out:
                out.write(md)

            existing_ids.add(source_id)
            stats["extracted"] += 1

            if stats["extracted"] % 1000 == 0:
                print(f"  進度：{stats['extracted']} 筆已萃取...")

    print(f"\n━━━ us_dsld 萃取完成 ━━━")
    print(f"  總行數：{stats['total']}")
    print(f"  跳過（已存在）：{stats['skipped']}")
    print(f"  新萃取：{stats['extracted']}")
    print(f"  REVIEW_NEEDED：{stats['review_needed']}")
    print(f"  錯誤：{stats['errors']}")

def main():
    parser = argparse.ArgumentParser(description="us_dsld JSONL → Markdown 萃取")
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
