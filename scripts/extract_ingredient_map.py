#!/usr/bin/env python3
"""成分標準化萃取腳本 — 將 JSONL 轉換為 .md 檔"""
import json
import os
import re
import sys
import argparse
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
RAW_DIR = BASE_DIR / "docs" / "Extractor" / "ingredient_map" / "raw"
OUTPUT_DIR = BASE_DIR / "docs" / "Extractor" / "ingredient_map"

# 成分分類關鍵詞
INGREDIENT_CATEGORY_KEYWORDS = {
    "vitamin": ["vitamin", "ascorbic", "tocopherol", "retinol", "folate", "biotin",
                "niacin", "riboflavin", "thiamin", "cobalamin", "pyridoxine"],
    "mineral": ["calcium", "magnesium", "zinc", "iron", "selenium", "chromium",
                "copper", "manganese", "potassium", "iodine", "sodium"],
    "fatty_acid": ["omega", "epa", "dha", "fatty acid", "fish oil", "krill",
                   "flaxseed", "ala", "linoleic"],
    "amino_acid": ["amino", "glutamine", "arginine", "lysine", "bcaa", "leucine",
                   "carnitine", "tryptophan", "tyrosine", "glycine"],
    "protein": ["protein", "collagen", "whey", "casein", "albumin"],
    "botanical": ["extract", "herb", "plant", "root", "leaf", "flower", "berry",
                  "ginseng", "ginkgo", "turmeric", "curcumin", "green tea"],
    "probiotic": ["probiotic", "lactobacillus", "bifidobacterium", "acidophilus",
                  "rhamnosus", "saccharomyces"],
    "enzyme": ["enzyme", "nattokinase", "bromelain", "papain", "lipase", "protease"],
    "hormone": ["dhea", "melatonin", "pregnenolone"],
}


def slugify(text: str) -> str:
    """轉換為 URL-safe 的 slug"""
    text = text.lower()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[-\s]+", "-", text)
    return text.strip("-")


def categorize_ingredient(name: str) -> str:
    """分類成分"""
    name_lower = name.lower()

    for category, keywords in INGREDIENT_CATEGORY_KEYWORDS.items():
        for kw in keywords:
            if kw in name_lower:
                return category

    return "other"


def check_review_needed(item: dict) -> list:
    """檢查是否需要標記 REVIEW_NEEDED"""
    reasons = []

    if not item.get("rxnorm_id") and item.get("confidence") == "low":
        reasons.append("無 RxNorm ID 且信心度低")

    if item.get("match_type") == "approximate" and item.get("confidence") == "low":
        reasons.append("模糊匹配且信心度低")

    return reasons


def generate_markdown(item: dict) -> str:
    """生成 Markdown 內容"""
    term = item.get("term", "")
    standard_name = item.get("standard_name") or term
    rxnorm_id = item.get("rxnorm_id", "")
    confidence = item.get("confidence", "low")
    match_type = item.get("match_type", "")
    frequency = item.get("frequency", 0)

    slug = slugify(term)
    category = categorize_ingredient(standard_name)

    review_reasons = check_review_needed(item)
    review_marker = "[REVIEW_NEEDED]\n\n" if review_reasons else ""

    source_url = f"https://rxnav.nlm.nih.gov/REST/rxcui/{rxnorm_id}" if rxnorm_id else ""

    md = f"""{review_marker}---
source_id: "{slug}"
source_layer: "ingredient_map"
source_url: "{source_url}"
standard_name: "{standard_name}"
standard_name_zh: ""
rxnorm_id: "{rxnorm_id or ''}"
original_term: "{term}"
category: "{category}"
confidence: "{confidence}"
match_type: "{match_type or ''}"
frequency: {frequency}
fetched_at: "{item.get('queried_at', datetime.now().isoformat())}"
---

# {standard_name}

## 基本資訊
- 標準名稱：{standard_name}
- 原始查詢：{term}
- RxNorm ID：{rxnorm_id or 'N/A'}
- 分類：{category}
- 匹配類型：{match_type or 'N/A'}
- 匹配信心度：{confidence}
- 出現頻率：{frequency} 次

## 別名
- {term}
"""

    if review_reasons:
        md += f"""
## 需要審核
- {chr(10).join('- ' + r for r in review_reasons)}
"""

    return md


def get_existing_source_ids() -> dict:
    """取得已存在的 source_id 及其路徑"""
    existing = {}

    for category_dir in OUTPUT_DIR.iterdir():
        if not category_dir.is_dir() or category_dir.name == "raw":
            continue

        for md_file in category_dir.glob("*.md"):
            try:
                content = md_file.read_text(encoding="utf-8")
                for line in content.split("\n"):
                    if line.startswith("source_id:"):
                        sid = line.split(":", 1)[1].strip().strip('"')
                        existing[sid] = md_file
                        break
            except Exception:
                pass

    return existing


def process_jsonl_file(jsonl_path: Path, force: bool = False) -> dict:
    """處理單一 JSONL 檔案"""
    stats = {"processed": 0, "skipped": 0, "review_needed": 0, "new": 0}

    existing = {} if force else get_existing_source_ids()

    with open(jsonl_path, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue

            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                continue

            term = item.get("term", "")
            if not term:
                stats["skipped"] += 1
                continue

            slug = slugify(term)

            # 檢查是否已存在
            if slug in existing and not force:
                stats["skipped"] += 1
                continue

            # 分類
            standard_name = item.get("standard_name") or term
            category = categorize_ingredient(standard_name)

            # 建立目錄
            category_dir = OUTPUT_DIR / category
            category_dir.mkdir(parents=True, exist_ok=True)

            # 生成 Markdown
            md_content = generate_markdown(item)

            # 寫入檔案
            output_path = category_dir / f"{slug}.md"
            output_path.write_text(md_content, encoding="utf-8")

            stats["processed"] += 1
            stats["new"] += 1

            if check_review_needed(item):
                stats["review_needed"] += 1

    return stats


def main():
    parser = argparse.ArgumentParser(description="成分標準化萃取")
    parser.add_argument("jsonl_file", nargs="?", help="指定 JSONL 檔案")
    parser.add_argument("--all", action="store_true", help="處理所有 JSONL 檔案")
    parser.add_argument("--force", action="store_true", help="強制覆蓋已存在的檔案")
    args = parser.parse_args()

    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("🧪 成分標準化萃取")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

    # 找到要處理的檔案
    if args.jsonl_file:
        jsonl_files = [Path(args.jsonl_file)]
    elif args.all:
        jsonl_files = list(RAW_DIR.glob("normalized_*.jsonl"))
    else:
        # 找最新的
        jsonl_files = sorted(RAW_DIR.glob("normalized_*.jsonl"),
                            key=lambda x: x.stat().st_mtime,
                            reverse=True)[:1]

    if not jsonl_files:
        print("  找不到 JSONL 檔案，請先執行 fetch.sh", file=sys.stderr)
        sys.exit(1)

    total_stats = {"processed": 0, "skipped": 0, "review_needed": 0, "new": 0}

    for jsonl_path in jsonl_files:
        print(f"\n  處理: {jsonl_path.name}")
        stats = process_jsonl_file(jsonl_path, args.force)

        for k, v in stats.items():
            total_stats[k] += v

        print(f"    ✅ 處理: {stats['processed']}, 跳過: {stats['skipped']}, REVIEW: {stats['review_needed']}")

    print("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print(f"✅ 萃取完成")
    print(f"   處理: {total_stats['processed']}")
    print(f"   跳過: {total_stats['skipped']}")
    print(f"   REVIEW_NEEDED: {total_stats['review_needed']}")


if __name__ == "__main__":
    main()
