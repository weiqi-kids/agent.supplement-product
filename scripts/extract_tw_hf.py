#!/usr/bin/env python3
"""tw_hf 萃取腳本 — 依據 Layer CLAUDE.md 規則將 JSONL 轉換為 .md 檔"""
import json, os, sys, re, glob
from datetime import datetime, timezone

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_DIR = os.path.join(BASE_DIR, "docs/Extractor/tw_hf/raw")
OUTPUT_DIR = os.path.join(BASE_DIR, "docs/Extractor/tw_hf")
SOURCE_URL = "https://consumer.fda.gov.tw/Food/InfoHealthFood.aspx?nodeID=162"

# Category 推斷規則 (from CLAUDE.md)
CATEGORY_RULES = [
    # probiotics 優先（益生菌產品常見）
    (["胃腸", "益生菌", "腸道", "乳酸菌", "雙歧桿菌"], "probiotics"),
    # omega
    (["血脂", "調節血脂", "膽固醇", "魚油"], "omega_fatty_acids"),
    # vitamins_minerals
    (["骨質", "牙齒", "鈣質", "鈣", "鐵", "維生素"], "vitamins_minerals"),
    # botanicals
    (["護肝", "體脂肪", "茶多酚", "抗氧化", "輔助調節血壓"], "botanicals"),
    # specialty (複合功效)
    (["免疫", "血糖", "抗疲勞", "調節免疫"], "specialty"),
]

# Product Form 推斷規則
def infer_product_form(product_name):
    """從中文品名推斷 product_form"""
    if not product_name:
        return "other"

    if any(kw in product_name for kw in ["錠", "片"]):
        return "tablet"
    if "膠囊" in product_name:
        return "capsule"
    if any(kw in product_name for kw in ["粉", "顆粒"]):
        return "powder"
    if any(kw in product_name for kw in ["飲", "飲料", "液", "乳", "發酵乳", "優酪乳"]):
        return "liquid"
    if any(kw in product_name for kw in ["軟糖", "果凍", "凝膠"]):
        return "gummy"

    return "other"

def s(val):
    """Safely convert to string, handling None."""
    return str(val).strip() if val is not None else ""

def infer_category(health_effect):
    """從保健功效推斷 category"""
    if not health_effect:
        return "other"

    matched_cats = set()
    for keywords, cat in CATEGORY_RULES:
        for kw in keywords:
            if kw in health_effect:
                matched_cats.add(cat)
                break

    if len(matched_cats) == 0:
        return "other"
    if len(matched_cats) == 1:
        return matched_cats.pop()
    return "specialty"  # 多功效複合

def format_date(date_str):
    """Convert YYYYMMDD to YYYY-MM-DD"""
    if not date_str:
        return ""
    date_str = date_str.strip()

    # 處理 YYYYMMDD 格式
    if len(date_str) == 8 and date_str.isdigit():
        return f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"

    # 處理已有 - 或 / 的格式
    if "/" in date_str:
        return date_str.replace("/", "-")

    return date_str

def check_review_needed(rec):
    """檢查是否需要標記 REVIEW_NEEDED"""
    reasons = []
    if not s(rec.get("許可證字號")):
        reasons.append("許可證字號為空")
    if not s(rec.get("中文品名")):
        reasons.append("中文品名為空")
    if not s(rec.get("保健功效")):
        reasons.append("保健功效為空")
    return reasons

def get_existing_source_ids():
    """取得已存在的 source_id"""
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
    pattern = os.path.join(RAW_DIR, "tw_hf-*.jsonl")
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

            # Extract fields
            source_id = s(rec.get("許可證字號"))
            if not source_id:
                stats["errors"] += 1
                continue

            if source_id in existing_ids:
                stats["skipped"] += 1
                continue

            product_name = s(rec.get("中文品名"))
            company_name = s(rec.get("申請商"))  # API 欄位為「申請商」
            approval_date = s(rec.get("核可日期"))
            health_ingredient = s(rec.get("保健功效相關成分"))
            health_effect = s(rec.get("保健功效"))
            health_claim = s(rec.get("保健功效宣稱"))
            precautions = s(rec.get("注意事項"))
            warnings = s(rec.get("警語"))
            product_url = s(rec.get("網址"))

            # Date formatting
            date_entered = format_date(approval_date)

            # Infer category and product form
            category = infer_category(health_effect)
            product_form = infer_product_form(product_name)

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

            # Use product URL from API if available, otherwise fallback
            source_url = product_url if product_url else SOURCE_URL
            safe_source_url = source_url.replace('"', '\\"')

            # Build markdown
            md = f"""{review_prefix}---
source_id: "{safe_source_id}"
source_layer: "tw_hf"
source_url: "{safe_source_url}"
market: "tw"
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
- 申請商：{company_name}
- 劑型：{product_form}
- 市場：台灣
- 許可證字號：{source_id}

## 保健功效成分
{health_ingredient if health_ingredient else "（無資料）"}

## 保健功效
{health_effect if health_effect else "（無資料）"}

## 保健功效宣稱
{health_claim if health_claim else "（無資料）"}

## 警語
{warnings if warnings else "（無資料）"}

## 注意事項
{precautions if precautions else "（無資料）"}
"""

            # Sanitize filename (replace special characters)
            safe_id = re.sub(r'[^\w\-.]', '_', source_id)
            filepath = os.path.join(OUTPUT_DIR, category, f"{safe_id}.md")
            with open(filepath, "w", encoding="utf-8") as out:
                out.write(md)

            existing_ids.add(source_id)
            stats["extracted"] += 1

    print(f"\n━━━ tw_hf 萃取完成 ━━━")
    print(f"  總行數：{stats['total']}")
    print(f"  跳過（已存在）：{stats['skipped']}")
    print(f"  新萃取：{stats['extracted']}")
    print(f"  REVIEW_NEEDED：{stats['review_needed']}")
    print(f"  錯誤：{stats['errors']}")

if __name__ == "__main__":
    process()
