#!/usr/bin/env python3
"""ca_lnhpd 萃取腳本 — 依據 Layer CLAUDE.md 規則將 JSONL 轉換為 .md 檔

支援整合成分資料（MedicinalIngredient API）。

用法：
    python3 scripts/extract_ca_lnhpd.py <products.jsonl>
    python3 scripts/extract_ca_lnhpd.py --ingredients <ingredients.jsonl> <products.jsonl>
    python3 scripts/extract_ca_lnhpd.py --delta --ingredients <ingredients.jsonl> <delta.jsonl>
"""
import json, os, sys, re
from datetime import datetime, timezone
from collections import defaultdict

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_DIR = os.path.join(BASE_DIR, "docs/Extractor/ca_lnhpd")

# Category 推斷規則 (from CLAUDE.md)
CATEGORY_RULES = [
    (["probiotic", "lactobacillus", "bifidobacterium"], "probiotics"),
    (["omega", "fish oil", "dha", "epa", "flax"], "omega_fatty_acids"),
    (["herbal", "herb", "botanical", "ginseng", "echinacea", "turmeric", "st. john"], "botanicals"),
    (["vitamin", "vit", "multi-vitamin", "multivitamin", "mineral", "calcium", "iron", "zinc", "magnesium", "selenium"], "vitamins_minerals"),
    (["protein", "amino", "collagen", "bcaa", "whey"], "protein_amino"),
    (["sport", "creatine", "electrolyte", "pre-workout"], "sports_fitness"),
]

# Product Form 映射規則
FORM_MAPPING = {
    "tablet": "tablet",
    "capsule": "capsule",
    "softgel": "softgel",
    "powder": "powder",
    "liquid": "liquid",
    "gummy": "gummy",
    "cream": "other",
    "ointment": "other",
    "lotion": "other",
}

def s(val):
    """Safely convert to string, handling None."""
    return str(val).strip() if val is not None else ""


def load_ingredients_index(ingredients_file: str) -> dict:
    """
    載入成分 JSONL 並建立索引。

    Args:
        ingredients_file: 成分 JSONL 檔案路徑

    Returns:
        dict: lnhpd_id -> [ingredient_records] 的映射
    """
    if not ingredients_file or not os.path.exists(ingredients_file):
        return {}

    print(f"📖 載入成分索引: {ingredients_file}")
    index = defaultdict(list)
    count = 0

    with open(ingredients_file, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            try:
                record = json.loads(line)
                lnhpd_id = str(record.get("lnhpd_id", ""))
                if lnhpd_id:
                    index[lnhpd_id].append(record)
                    count += 1
            except json.JSONDecodeError:
                continue

    print(f"✅ 載入 {count:,} 筆成分，涵蓋 {len(index):,} 個產品")
    return dict(index)


def format_ingredients(ingredients: list) -> str:
    """
    格式化成分清單為 Markdown。

    Args:
        ingredients: 成分記錄列表

    Returns:
        格式化的 Markdown 字串
    """
    if not ingredients:
        return "成分資料需額外擷取（參見 MedicinalIngredient API）"

    lines = []
    for ing in ingredients:
        name = s(ing.get("ingredient_name", ""))
        potency_amount = ing.get("potency_amount")
        potency_unit = s(ing.get("potency_unit_of_measure", ""))
        source_material = s(ing.get("source_material", ""))

        if not name:
            continue

        # 格式化劑量
        if potency_amount is not None and potency_unit:
            dosage = f"{potency_amount} {potency_unit}"
        elif potency_amount is not None:
            dosage = str(potency_amount)
        else:
            dosage = ""

        # 格式化來源
        if source_material and source_material.lower() != name.lower():
            source_info = f"（{source_material}）"
        else:
            source_info = ""

        # 組合成分行
        if dosage:
            lines.append(f"- {name}: {dosage}{source_info}")
        else:
            lines.append(f"- {name}{source_info}")

    if not lines:
        return "成分資料需額外擷取（參見 MedicinalIngredient API）"

    return "\n".join(lines)

def infer_category(product_name):
    """依產品名稱推斷 category"""
    if not product_name:
        return "other"
    name_lower = product_name.lower()
    matched_cats = set()
    
    for keywords, cat in CATEGORY_RULES:
        for kw in keywords:
            if kw in name_lower:
                matched_cats.add(cat)
                break
    
    if len(matched_cats) == 0:
        return "other"
    if len(matched_cats) == 1:
        return matched_cats.pop()
    return "specialty"

def map_product_form(dosage_form):
    """映射 LNHPD dosage_form 到統一格式"""
    if not dosage_form:
        return "other"
    form_lower = dosage_form.lower()
    
    for key, value in FORM_MAPPING.items():
        if key in form_lower:
            return value
    return "other"

def check_review_needed(data, category):
    """檢查是否需要標記 REVIEW_NEEDED"""
    reasons = []
    
    # 1. product_name 為空
    if not data.get("product_name"):
        reasons.append("缺少產品名稱")
    
    # 2. dosage_form 為空
    if not data.get("dosage_form"):
        reasons.append("缺少劑型資訊")
    
    # 3. category 為 other 但名稱含保健食品相關詞彙
    if category == "other" and data.get("product_name"):
        name_lower = data["product_name"].lower()
        supplement_keywords = ["supplement", "health", "natural", "wellness", "nutraceutical", "dietary"]
        if any(kw in name_lower for kw in supplement_keywords):
            reasons.append("category 推斷為 other 但產品名稱含保健食品關鍵字")
    
    # 4. flag_product_status 欄位遺失
    if "flag_product_status" not in data:
        reasons.append("缺少產品狀態欄位")
    
    return reasons

def extract_product(line_num, line_content, ingredients_index=None):
    """萃取單一產品

    Args:
        line_num: 行號
        line_content: JSON 內容
        ingredients_index: 成分索引 dict（lnhpd_id -> [ingredient_records]）

    Returns:
        dict with extraction result, or None if skipped/error
        Special case: returns {"skip": True, "reason": "..."} for non-primary names
    """
    try:
        data = json.loads(line_content)
    except json.JSONDecodeError as e:
        print(f"❌ Line {line_num}: JSON decode error: {e}", file=sys.stderr)
        return None

    # 只處理主要名稱（flag_primary_name == 1）
    # 跳過替代名稱，避免同一產品出現在多個分類目錄
    if data.get("flag_primary_name") != 1:
        return {"skip": True, "reason": "non_primary_name"}

    # 提取基本欄位
    lnhpd_id = s(data.get("lnhpd_id", ""))
    if not lnhpd_id:
        print(f"⚠️  Line {line_num}: 缺少 lnhpd_id，跳過", file=sys.stderr)
        return None

    product_name = s(data.get("product_name", ""))
    company_name = s(data.get("company_name", ""))
    dosage_form = s(data.get("dosage_form", ""))
    licence_number = s(data.get("licence_number", ""))
    licence_date = s(data.get("licence_date", ""))
    flag_product_status = data.get("flag_product_status")
    sub_submission_type = s(data.get("sub_submission_type_desc", ""))

    # 推斷 category 和 product_form
    category = infer_category(product_name)
    product_form = map_product_form(dosage_form)

    # 檢查是否需要 REVIEW_NEEDED
    review_reasons = check_review_needed(data, category)
    review_needed = len(review_reasons) > 0

    # 組合 source_url
    source_url = f"https://health-products.canada.ca/lnhpd-bdpsnh/info.do?licence={licence_number}&lang=en" if licence_number else ""

    # 產生 ISO8601 timestamp
    fetched_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    # 授權狀態
    status_text = "有效" if flag_product_status == 1 else "無效" if flag_product_status == 0 else "未知"

    # 取得成分資料
    ingredients = []
    if ingredients_index:
        ingredients = ingredients_index.get(lnhpd_id, [])
    ingredients_md = format_ingredients(ingredients)

    # 組合 Markdown 內容
    frontmatter = f"""---
source_id: "{lnhpd_id}"
source_layer: "ca_lnhpd"
source_url: "{source_url}"
market: "ca"
product_name: "{product_name}"
brand: "{company_name}"
manufacturer: "{company_name}"
category: "{category}"
product_form: "{product_form}"
date_entered: "{licence_date}"
fetched_at: "{fetched_at}"
---"""

    body = f"""# {product_name}

## 基本資訊
- 公司：{company_name}
- 劑型：{product_form} ({dosage_form})
- 市場：加拿大
- NPN：{licence_number}
- 授權狀態：{status_text}
- 授權日期：{licence_date}
- 申請類型：{sub_submission_type}

## 成分
{ingredients_md}

## 宣稱
參見 [Health Canada 產品頁面]({source_url})

## 備註
- LNHPD 無獨立品牌欄位，使用 company_name 作為 brand
- Category 由產品名稱關鍵字推斷"""

    if review_needed:
        body = f"[REVIEW_NEEDED]\n原因：{', '.join(review_reasons)}\n\n" + body

    markdown_content = frontmatter + "\n\n" + body

    # 決定輸出路徑
    category_dir = os.path.join(OUTPUT_DIR, category)
    os.makedirs(category_dir, exist_ok=True)
    output_path = os.path.join(category_dir, f"{lnhpd_id}.md")

    return {
        "path": output_path,
        "content": markdown_content,
        "review_needed": review_needed,
        "category": category,
        "has_ingredients": len(ingredients) > 0
    }

def main():
    import argparse
    parser = argparse.ArgumentParser(description='ca_lnhpd JSONL to Markdown 萃取工具')
    parser.add_argument('jsonl_file', help='產品 JSONL 檔案路徑')
    parser.add_argument('--force', '-f', action='store_true',
                        help='強制覆蓋已存在的檔案（用於增量更新）')
    parser.add_argument('--delta', '-d', action='store_true',
                        help='Delta 模式：處理增量更新，自動啟用 --force')
    parser.add_argument('--ingredients', '-i', type=str, default='',
                        help='成分 JSONL 檔案路徑（可選，若提供將整合成分資料）')
    args = parser.parse_args()

    jsonl_file = args.jsonl_file
    force_overwrite = args.force or args.delta
    ingredients_file = args.ingredients

    if not os.path.exists(jsonl_file):
        print(f"❌ JSONL 檔案不存在: {jsonl_file}", file=sys.stderr)
        sys.exit(1)

    # 載入成分索引
    ingredients_index = {}
    if ingredients_file:
        if not os.path.exists(ingredients_file):
            print(f"⚠️  成分檔案不存在: {ingredients_file}，將跳過成分整合", file=sys.stderr)
        else:
            ingredients_index = load_ingredients_index(ingredients_file)

    mode_text = "增量更新（覆蓋模式）" if force_overwrite else "一般模式（跳過既有）"
    print(f"📖 讀取 JSONL: {jsonl_file}")
    print(f"📋 模式: {mode_text}")
    if ingredients_index:
        print(f"📋 成分整合: 已啟用（{len(ingredients_index):,} 個產品）")

    # 讀取已存在的檔案（去重用，僅在非 force 模式使用）
    existing_ids = set()
    if not force_overwrite:
        for category in ["vitamins_minerals", "botanicals", "protein_amino", "probiotics",
                         "omega_fatty_acids", "specialty", "sports_fitness", "other"]:
            cat_dir = os.path.join(OUTPUT_DIR, category)
            if os.path.exists(cat_dir):
                for fname in os.listdir(cat_dir):
                    if fname.endswith(".md"):
                        existing_ids.add(fname.replace(".md", ""))
    
    if not force_overwrite:
        print(f"📋 已存在 {len(existing_ids)} 筆產品，將跳過")
    else:
        print(f"📋 增量模式：所有記錄都會被處理（覆蓋既有檔案）")
    
    # 逐行處理
    stats = {
        "total": 0,
        "skipped": 0,
        "skipped_non_primary": 0,  # 跳過的替代名稱
        "extracted": 0,
        "updated": 0,  # 覆蓋更新的數量
        "review_needed": 0,
        "with_ingredients": 0,  # 含成分資料的產品數
        "by_category": {}
    }

    with open(jsonl_file, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            stats["total"] += 1

            if not line.strip():
                continue

            result = extract_product(line_num, line, ingredients_index)
            if not result:
                continue

            # 處理 skip 標記（替代名稱）
            if result.get("skip"):
                stats["skipped_non_primary"] += 1
                continue

            # 去重檢查（僅在非 force 模式）
            source_id = result["path"].split("/")[-1].replace(".md", "")
            is_existing = os.path.exists(result["path"])

            if not force_overwrite and source_id in existing_ids:
                stats["skipped"] += 1
                if stats["skipped"] % 10000 == 0:
                    print(f"⏭️  已跳過 {stats['skipped']} 筆既有資料...")
                continue

            # 寫入檔案
            with open(result["path"], "w", encoding="utf-8") as out:
                out.write(result["content"])

            if is_existing and force_overwrite:
                stats["updated"] += 1
            else:
                stats["extracted"] += 1
            stats["by_category"][result["category"]] = stats["by_category"].get(result["category"], 0) + 1

            if result.get("has_ingredients"):
                stats["with_ingredients"] += 1

            if result["review_needed"]:
                stats["review_needed"] += 1
            
            # 進度回報
            if stats["extracted"] % 1000 == 0:
                print(f"✅ 已萃取 {stats['extracted']} 筆...")
    
    # 最終統計
    total_processed = stats['extracted'] + stats['updated']
    print("\n" + "=" * 50)
    print("📊 萃取完成統計")
    print("=" * 50)
    print(f"總行數：{stats['total']}")
    print(f"跳過（替代名稱）：{stats['skipped_non_primary']}")
    print(f"跳過（已存在）：{stats['skipped']}")
    print(f"新增萃取：{stats['extracted']}")
    if stats['updated'] > 0:
        print(f"更新覆蓋：{stats['updated']}")
    print(f"需要審核：{stats['review_needed']}")
    if ingredients_index:
        pct = (stats['with_ingredients'] / total_processed * 100) if total_processed > 0 else 0
        print(f"含成分資料：{stats['with_ingredients']} ({pct:.1f}%)")
    print("\n分類統計：")
    for cat, count in sorted(stats["by_category"].items()):
        print(f"  - {cat}: {count}")
    print("=" * 50)

if __name__ == "__main__":
    main()
