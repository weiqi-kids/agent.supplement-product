#!/usr/bin/env python3
"""交互作用萃取腳本 — 將 JSONL 轉換為 .md 檔並分析內容"""
import json
import os
import re
import sys
import argparse
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent

# Study Type 判定規則
STUDY_TYPE_RULES = [
    (["Meta-Analysis"], "meta_analysis", 1),
    (["Systematic Review"], "systematic_review", 1),
    (["Randomized Controlled Trial"], "rct", 2),
    (["Clinical Trial"], "clinical_trial", 3),
    (["Observational Study", "Cohort Study"], "observational", 4),
    (["Case Reports"], "case_report", 5),
    (["Review"], "review", 5),
]

# 嚴重程度關鍵詞
SEVERITY_KEYWORDS = {
    "major": ["contraindicated", "life-threatening", "serious adverse", "fatal",
              "avoid concomitant", "significantly increase", "bleeding risk",
              "hospitalization", "death", "hemorrhage"],
    "moderate": ["monitor", "caution", "dose adjustment", "clinical significance",
                 "reduce dose", "increased effect", "decreased effect",
                 "should be aware", "consider alternative"],
    "minor": ["minimal", "unlikely", "no significant", "limited clinical",
              "unlikely to be clinically significant"],
}

# 藥物類別關鍵詞
DRUG_CLASS_KEYWORDS = {
    "anticoagulant": ["warfarin", "heparin", "anticoagulant", "blood thinner",
                      "coumadin", "enoxaparin", "rivaroxaban", "apixaban"],
    "antiplatelet": ["aspirin", "clopidogrel", "plavix", "antiplatelet", "ticagrelor"],
    "antihypertensive": ["ace inhibitor", "arb", "beta blocker", "calcium channel",
                         "antihypertensive", "lisinopril", "amlodipine", "losartan"],
    "antidiabetic": ["metformin", "insulin", "sulfonylurea", "antidiabetic",
                     "glipizide", "glimepiride", "diabetes"],
    "statin": ["statin", "atorvastatin", "simvastatin", "rosuvastatin", "pravastatin"],
    "antidepressant": ["ssri", "snri", "maoi", "antidepressant", "sertraline",
                       "fluoxetine", "escitalopram", "venlafaxine"],
    "immunosuppressant": ["cyclosporine", "tacrolimus", "immunosuppressant",
                          "mycophenolate", "sirolimus"],
    "thyroid": ["levothyroxine", "synthroid", "thyroid", "liothyronine"],
}

# 補充劑類別關鍵詞
SUPPLEMENT_CATEGORY_KEYWORDS = {
    "omega_fatty_acid": ["omega-3", "omega 3", "fish oil", "epa", "dha", "krill"],
    "botanical": ["herb", "botanical", "ginkgo", "ginseng", "curcumin", "turmeric",
                  "garlic", "st john", "hypericum", "echinacea", "valerian",
                  "saw palmetto", "green tea"],
    "vitamin": ["vitamin", "ascorbic", "tocopherol", "retinol"],
    "mineral": ["calcium", "magnesium", "zinc", "iron", "selenium"],
    "amino_acid": ["amino acid", "arginine", "glutamine", "carnitine"],
    "enzyme": ["enzyme", "coq10", "nattokinase", "bromelain"],
    "probiotic": ["probiotic", "lactobacillus", "bifidobacterium"],
}

# 食物類別關鍵詞
FOOD_CATEGORY_KEYWORDS = {
    "citrus": ["grapefruit", "citrus", "seville orange", "pomelo"],
    "dairy": ["dairy", "milk", "cheese", "yogurt", "calcium-fortified"],
    "leafy_greens": ["leafy green", "spinach", "kale", "broccoli", "vitamin k food"],
    "high_fat": ["high fat", "fatty meal", "high-fat"],
    "caffeine": ["caffeine", "coffee", "tea", "energy drink"],
    "alcohol": ["alcohol", "ethanol", "wine", "beer"],
    "fermented": ["fermented", "natto", "kimchi", "sauerkraut"],
    "fiber": ["fiber", "whole grain", "bran"],
}


def slugify(text: str) -> str:
    """轉換為 URL-safe 的 slug"""
    text = text.lower()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[-\s]+", "-", text)
    return text.strip("-")[:80]  # 限制長度


def infer_study_type(publication_types: list, title: str, abstract: str) -> tuple:
    """推斷研究類型與證據等級"""
    combined_text = f"{title} {abstract}".lower()
    pub_types_str = " ".join(publication_types).lower()

    for keywords, study_type, level in STUDY_TYPE_RULES:
        for kw in keywords:
            if kw.lower() in pub_types_str:
                return study_type, level
            if kw.lower() in combined_text:
                return study_type, level

    return "other", 5


def infer_severity(title: str, abstract: str) -> str:
    """推斷交互嚴重程度"""
    combined_text = f"{title} {abstract}".lower()

    for severity, keywords in SEVERITY_KEYWORDS.items():
        for kw in keywords:
            if kw in combined_text:
                return severity

    return "unknown"


def categorize_by_keywords(text: str, keyword_map: dict) -> str:
    """根據關鍵詞分類"""
    text_lower = text.lower()

    for category, keywords in keyword_map.items():
        for kw in keywords:
            if kw in text_lower:
                return category

    return "other"


def check_review_needed(article: dict) -> list:
    """檢查是否需要標記 REVIEW_NEEDED"""
    reasons = []

    if not article.get("pmid"):
        reasons.append("PMID 為空")
    if not article.get("title"):
        reasons.append("標題為空")
    if not article.get("abstract"):
        reasons.append("摘要為空")

    return reasons


def generate_markdown(article: dict, interaction_type: str, category: str) -> str:
    """生成 Markdown 內容"""
    pmid = article.get("pmid", "")
    title = article.get("title", "")
    abstract = article.get("abstract", "")
    journal = article.get("journal", "")
    pub_date = article.get("pub_date", "")
    authors = article.get("authors", [])
    publication_types = article.get("publication_types", [])

    # 推斷研究類型和證據等級
    study_type, evidence_level = infer_study_type(publication_types, title, abstract)

    # 推斷嚴重程度
    severity = infer_severity(title, abstract)

    review_reasons = check_review_needed(article)
    if severity == "unknown" and not review_reasons:
        review_reasons.append("嚴重程度無法判定")

    review_marker = "[REVIEW_NEEDED]\n\n" if review_reasons else ""

    # 格式化作者
    authors_str = ", ".join(authors[:5])
    if len(authors) > 5:
        authors_str += f" et al. ({len(authors)} authors)"

    md = f"""{review_marker}---
source_id: "{pmid}"
source_layer: "{interaction_type}"
source_url: "https://pubmed.ncbi.nlm.nih.gov/{pmid}/"
interaction_type: "{interaction_type.upper()}"
category: "{category}"
title: "{title.replace('"', "'")}"
journal: "{journal}"
pub_date: "{pub_date}"
study_type: "{study_type}"
evidence_level: {evidence_level}
severity: "{severity}"
fetched_at: "{article.get('fetched_at', datetime.now().isoformat())}"
---

# {title}

## 基本資訊
- 交互類型：{interaction_type.upper()}
- 類別：{category}
- PMID：{pmid}
- 期刊：{journal}
- 發表日期：{pub_date}
- 研究類型：{study_type}
- 證據等級：Level {evidence_level}
- 嚴重程度：{severity.capitalize()}

## 作者
{authors_str}

## 摘要
{abstract}

---

⚠️ **免責聲明**：本資訊僅供教育和研究目的，不構成醫療建議。
任何用藥或補充劑變更應諮詢專業醫療人員。
"""

    return md


def get_existing_source_ids(layer_dir: Path) -> set:
    """取得已存在的 source_id"""
    existing = set()

    for category_dir in layer_dir.iterdir():
        if not category_dir.is_dir() or category_dir.name == "raw":
            continue

        for md_file in category_dir.glob("*.md"):
            try:
                content = md_file.read_text(encoding="utf-8")
                for line in content.split("\n"):
                    if line.startswith("source_id:"):
                        sid = line.split(":", 1)[1].strip().strip('"')
                        existing.add(sid)
                        break
            except Exception:
                pass

    return existing


def process_jsonl_file(jsonl_path: Path, interaction_type: str, force: bool = False) -> dict:
    """處理單一 JSONL 檔案"""
    stats = {"processed": 0, "skipped": 0, "review_needed": 0, "new": 0}

    layer_dir = BASE_DIR / "docs" / "Extractor" / interaction_type
    existing = set() if force else get_existing_source_ids(layer_dir)

    # 根據交互類型選擇分類方式
    if interaction_type == "dhi":
        category_keywords = SUPPLEMENT_CATEGORY_KEYWORDS
    elif interaction_type == "dfi":
        category_keywords = FOOD_CATEGORY_KEYWORDS
    else:  # ddi
        category_keywords = DRUG_CLASS_KEYWORDS

    with open(jsonl_path, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue

            try:
                article = json.loads(line)
            except json.JSONDecodeError:
                continue

            pmid = article.get("pmid", "")
            if not pmid:
                stats["skipped"] += 1
                continue

            # 檢查是否已存在
            if pmid in existing and not force:
                stats["skipped"] += 1
                continue

            # 分類
            title = article.get("title", "")
            abstract = article.get("abstract", "")
            combined_text = f"{title} {abstract}"

            file_category = article.get("category", "general")
            content_category = categorize_by_keywords(combined_text, category_keywords)

            # 使用檔案類別或內容分類
            category = content_category if content_category != "other" else file_category

            # 建立目錄
            category_dir = layer_dir / category
            category_dir.mkdir(parents=True, exist_ok=True)

            # 生成 Markdown
            md_content = generate_markdown(article, interaction_type, category)

            # 寫入檔案
            output_path = category_dir / f"{pmid}.md"
            output_path.write_text(md_content, encoding="utf-8")

            stats["processed"] += 1
            stats["new"] += 1

            if check_review_needed(article):
                stats["review_needed"] += 1

    return stats


def main():
    parser = argparse.ArgumentParser(description="交互作用萃取")
    parser.add_argument("--type", required=True, choices=["ddi", "dfi", "dhi"],
                       help="交互類型")
    parser.add_argument("jsonl_file", nargs="?", help="指定 JSONL 檔案")
    parser.add_argument("--all", action="store_true", help="處理所有 JSONL 檔案")
    parser.add_argument("--force", action="store_true", help="強制覆蓋已存在的檔案")
    args = parser.parse_args()

    interaction_type = args.type
    raw_dir = BASE_DIR / "docs" / "Extractor" / interaction_type / "raw"

    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print(f"💊 {interaction_type.upper()} 萃取")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

    # 找到要處理的檔案
    if args.jsonl_file:
        jsonl_files = [Path(args.jsonl_file)]
    elif args.all:
        jsonl_files = list(raw_dir.glob("*.jsonl"))
    else:
        # 找最新的
        jsonl_files = sorted(raw_dir.glob("*.jsonl"),
                            key=lambda x: x.stat().st_mtime,
                            reverse=True)

    if not jsonl_files:
        print(f"  找不到 JSONL 檔案於 {raw_dir}", file=sys.stderr)
        print("  請先執行 fetch.sh", file=sys.stderr)
        sys.exit(1)

    total_stats = {"processed": 0, "skipped": 0, "review_needed": 0, "new": 0}

    for jsonl_path in jsonl_files:
        print(f"\n  處理: {jsonl_path.name}")
        stats = process_jsonl_file(jsonl_path, interaction_type, args.force)

        for k, v in stats.items():
            total_stats[k] += v

        print(f"    ✅ 處理: {stats['processed']}, 跳過: {stats['skipped']}, REVIEW: {stats['review_needed']}")

    print("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print(f"✅ 萃取完成: {interaction_type.upper()}")
    print(f"   處理: {total_stats['processed']}")
    print(f"   跳過: {total_stats['skipped']}")
    print(f"   REVIEW_NEEDED: {total_stats['review_needed']}")


if __name__ == "__main__":
    main()
