#!/usr/bin/env python3
"""jp_fnfc 萃取腳本 — 依據 Layer CLAUDE.md 規則將 JSONL 轉換為 .md 檔"""
import json, os, sys, re, glob
from datetime import datetime, timezone

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_DIR = os.path.join(BASE_DIR, "docs/Extractor/jp_fnfc/raw")
OUTPUT_DIR = os.path.join(BASE_DIR, "docs/Extractor/jp_fnfc")
SOURCE_URL_TEMPLATE = "https://www.fld.caa.go.jp/caaks/cssc02/?recordSeq={}"

# Category 推斷規則 (from CLAUDE.md)
CATEGORY_RULES = [
    # probiotics 優先
    (["乳酸菌", "ビフィズス菌", "プロバイオティクス"], "probiotics"),
    # omega
    (["DHA", "EPA", "オメガ", "n-3系脂肪酸"], "omega_fatty_acids"),
    # botanicals
    (["ルテイン", "イチョウ", "ブルーベリー", "クルクミン", "茶カテキン",
      "イソフラボン", "GABA", "難消化性デキストリン", "食物繊維", "ヒアルロン酸"], "botanicals"),
    # vitamins_minerals
    (["ビタミン", "葉酸", "カルシウム", "鉄", "亜鉛", "マグネシウム"], "vitamins_minerals"),
    # protein_amino
    (["コラーゲン", "ペプチド", "アミノ酸", "HMB"], "protein_amino"),
]

# Product Form 推斷規則
def infer_product_form(food_category, food_name):
    """從 食品の区分 和 名称 推斷 product_form"""
    food_category = food_category or ""
    food_name = food_name or ""
    combined = food_category + food_name

    if "サプリメント" in food_category or "錠剤" in food_category:
        if "カプセル" in combined:
            return "capsule"
        if "錠" in combined:
            return "tablet"
        if "粉末" in combined or "顆粒" in combined:
            return "powder"
        return "tablet"  # default for supplement

    if "飲料" in combined or "ドリンク" in combined:
        return "liquid"
    if "ゼリー" in combined:
        return "gummy"
    if "粉末" in combined or "顆粒" in combined:
        return "powder"

    return "other"

def s(val):
    """Safely convert to string, handling None."""
    return str(val).strip() if val is not None else ""

def infer_category(ingredient_str):
    if not ingredient_str:
        return "other"
    matched_cats = set()
    for keywords, cat in CATEGORY_RULES:
        for kw in keywords:
            if kw in ingredient_str:
                matched_cats.add(cat)
                break
    if len(matched_cats) == 0:
        return "other"
    if len(matched_cats) == 1:
        return matched_cats.pop()
    return "specialty"  # 多成分複合

def format_date(date_str):
    """Convert YYYY/MM/DD to YYYY-MM-DD"""
    if not date_str:
        return ""
    date_str = date_str.strip()
    if "/" in date_str:
        return date_str.replace("/", "-")
    return date_str

def check_review_needed(rec):
    reasons = []
    if not s(rec.get("商品名")):
        reasons.append("商品名為空")
    if not s(rec.get("届出番号")):
        reasons.append("届出番号為空")
    if not s(rec.get("機能性関与成分名")):
        reasons.append("機能性関与成分名為空")
    return reasons

def get_existing_source_ids():
    ids = set()
    for root, dirs, files in os.walk(OUTPUT_DIR):
        if "raw" in root:
            continue
        for f in files:
            if f.endswith(".md"):
                path = os.path.join(root, f)
                try:
                    with open(path, "r", encoding="utf-8") as fh:
                        for line in fh:
                            if line.startswith("source_id:"):
                                sid = line.split(":", 1)[1].strip().strip('"')
                                ids.add(sid)
                                break
                except:
                    pass
    return ids

def find_latest_jsonl():
    """Find the most recent JSONL file in raw directory"""
    pattern = os.path.join(RAW_DIR, "fnfc-*.jsonl")
    files = glob.glob(pattern)
    if not files:
        return None
    return max(files, key=os.path.getmtime)

def process():
    jsonl_file = find_latest_jsonl()
    if not jsonl_file:
        print(f"JSONL not found in: {RAW_DIR}", file=sys.stderr)
        sys.exit(1)

    print(f"Processing: {jsonl_file}")

    existing_ids = get_existing_source_ids()
    now = datetime.now(timezone.utc).isoformat()
    stats = {"total": 0, "skipped": 0, "extracted": 0, "review_needed": 0, "errors": 0}

    # Ensure category directories exist
    for cat in ["vitamins_minerals", "botanicals", "protein_amino", "probiotics",
                "omega_fatty_acids", "specialty", "sports_fitness", "other"]:
        os.makedirs(os.path.join(OUTPUT_DIR, cat), exist_ok=True)

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

            # Extract fields using Japanese column names
            source_id = s(rec.get("届出番号"))
            if not source_id:
                stats["errors"] += 1
                continue

            if source_id in existing_ids:
                stats["skipped"] += 1
                continue

            product_name = s(rec.get("商品名"))
            company_name = s(rec.get("法人名"))
            notification_date = s(rec.get("届出日"))
            withdrawal_date = s(rec.get("撤回日"))
            functional_ingredient = s(rec.get("機能性関与成分名"))
            functional_claim = s(rec.get("表示しようとする機能性"))
            food_category = s(rec.get("食品の区分"))
            food_name = s(rec.get("名称"))
            precautions = s(rec.get("摂取をする上での注意事項"))
            raw_materials = s(rec.get("機能性関与成分を含む原材料名"))

            # Date formatting
            date_entered = format_date(notification_date)

            # Infer category and product form
            category = infer_category(functional_ingredient)
            product_form = infer_product_form(food_category, food_name)

            # Build source URL
            source_url = SOURCE_URL_TEMPLATE.format(source_id)

            # Escape double quotes for YAML frontmatter
            safe_source_id = source_id.replace('"', '\\"')
            safe_product_name = product_name.replace('"', '\\"')
            safe_company_name = company_name.replace('"', '\\"')
            safe_date_entered = date_entered.replace('"', '\\"')

            review_reasons = check_review_needed(rec)
            review_prefix = ""
            if review_reasons:
                review_prefix = "[REVIEW_NEEDED]\n\n"
                stats["review_needed"] += 1

            # Withdrawal status note
            withdrawal_note = ""
            if withdrawal_date:
                withdrawal_note = f"已撤回（{format_date(withdrawal_date)}）"

            # Build markdown
            md = f"""{review_prefix}---
source_id: "{safe_source_id}"
source_layer: "jp_fnfc"
source_url: "{source_url}"
market: "jp"
product_name: "{safe_product_name}"
brand: "{safe_company_name}"
manufacturer: "{safe_company_name}"
category: "{category}"
product_form: "{product_form}"
date_entered: "{safe_date_entered}"
fetched_at: "{now}"
---

# {product_name}

## 基本資訊
- 屆出者：{company_name}
- 食品區分：{food_category}
- 劑型：{product_form}
- 市場：日本
- 屆出番號：{source_id}

## 機能性成分
{functional_ingredient if functional_ingredient else "（無資料）"}

## 機能性表示
{functional_claim if functional_claim else "（無資料）"}

## 攝取注意事項
{precautions if precautions else "（無資料）"}

## 原料
{raw_materials if raw_materials else "（無資料）"}

## 備註
{withdrawal_note if withdrawal_note else "（無特殊情況）"}
"""

            # Sanitize filename
            safe_id = re.sub(r'[^\w\-.]', '_', source_id)
            filepath = os.path.join(OUTPUT_DIR, category, f"{safe_id}.md")
            with open(filepath, "w", encoding="utf-8") as out:
                out.write(md)

            existing_ids.add(source_id)
            stats["extracted"] += 1

    print(f"\n━━━ jp_fnfc 萃取完成 ━━━")
    print(f"  總行數：{stats['total']}")
    print(f"  跳過（已存在）：{stats['skipped']}")
    print(f"  新萃取：{stats['extracted']}")
    print(f"  REVIEW_NEEDED：{stats['review_needed']}")
    print(f"  錯誤：{stats['errors']}")

if __name__ == "__main__":
    process()
