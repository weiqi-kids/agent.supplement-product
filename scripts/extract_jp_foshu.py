#!/usr/bin/env python3
"""jp_foshu 萃取腳本 — 依據 Layer CLAUDE.md 規則將 JSONL 轉換為 .md 檔

用法：
    python3 scripts/extract_jp_foshu.py [<jsonl_file>]

    若未指定 jsonl_file，自動尋找 raw/ 目錄下最新的 foshu-*.jsonl
"""
import json, os, sys, re, glob
from datetime import datetime, timezone

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_DIR = os.path.join(BASE_DIR, "docs/Extractor/jp_foshu/raw")
OUTPUT_DIR = os.path.join(BASE_DIR, "docs/Extractor/jp_foshu")


def find_latest_jsonl():
    """Find the most recent JSONL file in raw directory"""
    pattern = os.path.join(RAW_DIR, "foshu-*.jsonl")
    files = glob.glob(pattern)
    if not files:
        return None
    return max(files, key=os.path.getmtime)


SOURCE_URL = "https://www.caa.go.jp/policies/policy/food_labeling/foods_for_specified_health_uses/"

# Category 推斷規則 (from CLAUDE.md)
CATEGORY_RULES = [
    (["Lactobacillus", "ビフィズス菌", "乳酸菌", "Bifidobacterium", "L.カゼイ",
      "L.アシドフィルス", "B.ブレーベ", "B.ロンガム", "ラクトバチルス", "Streptococcus"], "probiotics"),
    (["DHA", "EPA", "脂肪酸", "フィッシュオイル"], "omega_fatty_acids"),
    (["茶カテキン", "イソフラボン", "植物ステロール", "ポリフェノール",
      "難消化性デキストリン", "食物繊維"], "botanicals"),
    (["ビタミン", "カルシウム", "鉄", "マグネシウム", "亜鉛"], "vitamins_minerals"),
    (["ペプチド", "アミノ酸", "たんぱく質", "コラーゲン", "カゼイン"], "protein_amino"),
]

# Product Form 推斷規則
FORM_RULES = [
    (["錠剤"], "tablet"),
    (["カプセル"], "capsule"),
    (["粉末", "顆粒"], "powder"),
    (["飲料", "清涼飲料水", "はっ酵乳", "乳酸菌飲料", "豆乳"], "liquid"),
    (["ゼリー"], "gummy"),
]

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

def infer_product_form(food_type_str):
    if not food_type_str:
        return "other"
    for keywords, form in FORM_RULES:
        for kw in keywords:
            if kw in food_type_str:
                return form
    return "other"

def check_review_needed(record):
    reasons = []
    if not s(record.get("product_name")):
        reasons.append("商品名為空")
    if not s(record.get("functional_ingredient")):
        reasons.append("関与する成分為空")
    if not s(record.get("approval_no")):
        reasons.append("許可番号為空")
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

def process():
    # 支援命令列參數或自動尋找最新檔案
    if len(sys.argv) > 1:
        jsonl_file = sys.argv[1]
    else:
        jsonl_file = find_latest_jsonl()

    if not jsonl_file or not os.path.exists(jsonl_file):
        print(f"JSONL not found in: {RAW_DIR}", file=sys.stderr)
        sys.exit(1)

    print(f"Processing: {jsonl_file}")

    existing_ids = get_existing_source_ids()
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

            source_id = str(rec.get("approval_no", "")).strip()
            if not source_id:
                source_id = str(rec.get("serial_no", "")).strip()

            if source_id in existing_ids:
                stats["skipped"] += 1
                continue

            product_name = s(rec.get("product_name"))
            applicant = s(rec.get("applicant"))
            corporate_no = s(rec.get("corporate_no"))
            food_type = s(rec.get("food_type"))
            functional_ingredient = s(rec.get("functional_ingredient"))
            health_claim = s(rec.get("health_claim"))
            precautions = s(rec.get("precautions"))
            daily_intake = s(rec.get("daily_intake"))
            foshu_category = s(rec.get("foshu_category"))
            approval_date_raw = s(rec.get("approval_date"))
            sales_record = s(rec.get("sales_record"))

            # Date formatting
            date_entered = approval_date_raw
            if date_entered and not re.match(r"\d{4}-\d{2}-\d{2}", date_entered):
                date_entered = date_entered  # keep as-is if not standard format

            category = infer_category(functional_ingredient)
            product_form = infer_product_form(food_type)

            # Escape double quotes for YAML frontmatter
            safe_source_id = source_id.replace('"', '\\"')
            safe_product_name = product_name.replace('"', '\\"')
            safe_applicant = applicant.replace('"', '\\"')
            safe_date_entered = date_entered.replace('"', '\\"')

            review_reasons = check_review_needed(rec)
            review_prefix = ""
            if review_reasons:
                review_prefix = "[REVIEW_NEEDED]\n\n"
                stats["review_needed"] += 1

            # Ensure category directory exists
            cat_dir = os.path.join(OUTPUT_DIR, category)
            os.makedirs(cat_dir, exist_ok=True)

            # Build markdown
            md = f"""{review_prefix}---
source_id: "{safe_source_id}"
source_layer: "jp_foshu"
source_url: "{SOURCE_URL}"
market: "jp"
product_name: "{safe_product_name}"
brand: "{safe_applicant}"
manufacturer: "{safe_applicant}"
category: "{category}"
product_form: "{product_form}"
date_entered: "{safe_date_entered}"
fetched_at: "{now}"
---

# {product_name}

## 基本資訊
- 申請者：{applicant}
- 食品種類：{food_type}
- 劑型：{product_form}
- 市場：日本
- 許可番號：{source_id}
- 區分：{foshu_category}
- 法人番號：{corporate_no}

## 機能性成分
{functional_ingredient if functional_ingredient else "（無資料）"}

## 保健宣稱
{health_claim if health_claim else "（無資料）"}

## 攝取注意事項
{precautions if precautions else "（無資料）"}

## 每日建議攝取量
{daily_intake if daily_intake else "（無資料）"}

## 備註
{f"銷售實績：{'有' if sales_record else '無資料'}" }
"""

            # Sanitize filename
            safe_id = re.sub(r'[^\w\-.]', '_', source_id)
            filepath = os.path.join(cat_dir, f"{safe_id}.md")
            with open(filepath, "w", encoding="utf-8") as out:
                out.write(md)

            existing_ids.add(source_id)
            stats["extracted"] += 1

    print(f"\n━━━ jp_foshu 萃取完成 ━━━")
    print(f"  總行數：{stats['total']}")
    print(f"  跳過（已存在）：{stats['skipped']}")
    print(f"  新萃取：{stats['extracted']}")
    print(f"  REVIEW_NEEDED：{stats['review_needed']}")
    print(f"  錯誤：{stats['errors']}")

if __name__ == "__main__":
    process()
