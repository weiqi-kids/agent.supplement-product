#!/usr/bin/env python3
"""PubMed 萃取腳本 — 將 JSONL 轉換為 .md 檔並分析內容"""
import json
import os
import sys
import re
import glob
import argparse
from datetime import datetime, timezone

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_DIR = os.path.join(BASE_DIR, "docs/Extractor/pubmed/raw")
OUTPUT_DIR = os.path.join(BASE_DIR, "docs/Extractor/pubmed")

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

# Claim Category 關鍵詞對應
CLAIM_CATEGORY_KEYWORDS = {
    "anti_aging": ["aging", "longevity", "senescence", "telomere", "anti-aging", "lifespan"],
    "cardiovascular": ["cardiovascular", "lipid", "cholesterol", "blood pressure", "heart",
                       "triglyceride", "atherosclerosis", "hypertension"],
    "cognitive": ["cognitive", "memory", "brain", "neurological", "neurodegenerative",
                  "alzheimer", "dementia", "neuroprotective"],
    "immune": ["immune", "inflammation", "inflammatory", "autoimmune", "cytokine",
               "immunomodulat"],
    "metabolic": ["glucose", "diabetes", "metabolism", "obesity", "insulin", "glycemic",
                  "weight loss", "body weight", "metabolic syndrome"],
    "musculoskeletal": ["muscle", "bone", "joint", "osteoporosis", "arthritis", "skeletal",
                        "sarcopenia", "bone density"],
    "sexual": ["sexual", "erectile", "libido", "testosterone", "fertility"],
    "skin": ["skin", "dermatological", "collagen", "wrinkle", "photoaging"],
    "digestive": ["gut", "intestinal", "microbiome", "digestive", "gastrointestinal",
                  "probiotic", "prebiotic"],
    "energy": ["fatigue", "energy", "vitality", "physical performance", "exercise capacity"],
}

# 常見補充劑成分
COMMON_INGREDIENTS = [
    "omega-3", "omega-6", "EPA", "DHA", "fish oil", "krill oil",
    "vitamin D", "vitamin C", "vitamin E", "vitamin B12", "vitamin B6",
    "vitamin A", "vitamin K", "folate", "folic acid",
    "calcium", "magnesium", "zinc", "iron", "selenium", "chromium",
    "curcumin", "resveratrol", "quercetin", "CoQ10", "coenzyme Q10",
    "glucosamine", "chondroitin", "collagen", "hyaluronic acid",
    "probiotics", "prebiotics", "fiber", "psyllium",
    "melatonin", "valerian", "ashwagandha", "ginseng", "ginkgo",
    "green tea", "EGCG", "caffeine", "L-theanine",
    "creatine", "BCAA", "whey protein", "casein",
    "astaxanthin", "lutein", "zeaxanthin", "beta-carotene",
    "NAC", "glutathione", "alpha-lipoic acid",
    "berberine", "cinnamon", "bitter melon",
    "saw palmetto", "maca", "tribulus",
    "garlic", "turmeric", "ginger",
    "exosome", "exosomes", "stem cell",
]


def s(val):
    """Safely convert to string, handling None."""
    return str(val).strip() if val is not None else ""


def infer_study_type(publication_types: list, title: str, abstract: str) -> tuple:
    """推斷研究類型與證據等級"""
    combined_text = f"{title} {abstract}".lower()
    pub_types_str = " ".join(publication_types).lower()

    for keywords, study_type, level in STUDY_TYPE_RULES:
        for kw in keywords:
            if kw.lower() in pub_types_str:
                return study_type, level
            # 也檢查標題中的 systematic review
            if study_type == "systematic_review" and "systematic review" in combined_text:
                return study_type, level
            if study_type == "meta_analysis" and "meta-analysis" in combined_text:
                return study_type, level

    return "other", 5


def analyze_claim_categories(title: str, abstract: str) -> list:
    """分析摘要內容，識別健康功效分類"""
    combined_text = f"{title} {abstract}".lower()
    categories = []

    for category, keywords in CLAIM_CATEGORY_KEYWORDS.items():
        for kw in keywords:
            if kw.lower() in combined_text:
                categories.append(category)
                break

    return categories if categories else ["other"]


def extract_ingredients(title: str, abstract: str) -> list:
    """從標題和摘要中提取提及的成分"""
    combined_text = f"{title} {abstract}".lower()
    found = []

    for ingredient in COMMON_INGREDIENTS:
        if ingredient.lower() in combined_text:
            found.append(ingredient)

    return found


def check_review_needed(article: dict) -> list:
    """檢查是否需要標記 REVIEW_NEEDED"""
    reasons = []
    if not s(article.get("pmid")):
        reasons.append("PMID 為空")
    if not s(article.get("title")):
        reasons.append("標題為空")
    if not s(article.get("abstract")):
        reasons.append("摘要為空")
    return reasons


def get_existing_source_ids(topic_id: str) -> set:
    """取得特定主題已存在的 source_id"""
    ids = set()
    topic_dir = os.path.join(OUTPUT_DIR, topic_id)
    if not os.path.exists(topic_dir):
        return ids

    for f in os.listdir(topic_dir):
        if f.endswith(".md"):
            path = os.path.join(topic_dir, f)
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


def find_jsonl_files(topic_id: str = None) -> list:
    """找到要處理的 JSONL 檔案"""
    if topic_id:
        pattern = os.path.join(RAW_DIR, f"{topic_id}-*.jsonl")
    else:
        pattern = os.path.join(RAW_DIR, "*.jsonl")

    files = glob.glob(pattern)
    return sorted(files, key=os.path.getmtime, reverse=True)


def process_file(jsonl_file: str, force: bool = False) -> dict:
    """處理單一 JSONL 檔案"""
    stats = {"total": 0, "skipped": 0, "extracted": 0, "review_needed": 0, "errors": 0}
    now = datetime.now(timezone.utc).isoformat()

    # 從檔名取得 topic_id（格式：{topic_id}-YYYY-MM.jsonl）
    basename = os.path.basename(jsonl_file)
    # 移除 .jsonl 和日期部分 (YYYY-MM)
    name_without_ext = basename.replace(".jsonl", "")
    # 日期格式是 YYYY-MM，所以移除最後兩個用 - 分隔的部分
    parts = name_without_ext.rsplit("-", 2)
    if len(parts) >= 3 and parts[-2].isdigit() and parts[-1].isdigit():
        topic_id = "-".join(parts[:-2])
    else:
        topic_id = parts[0]

    # 確保輸出目錄存在
    topic_output_dir = os.path.join(OUTPUT_DIR, topic_id)
    os.makedirs(topic_output_dir, exist_ok=True)

    # 取得已存在的 ID
    existing_ids = get_existing_source_ids(topic_id) if not force else set()

    with open(jsonl_file, "r", encoding="utf-8") as f:
        for line_num, raw_line in enumerate(f, 1):
            stats["total"] += 1
            raw_line = raw_line.strip()
            if not raw_line:
                continue

            try:
                article = json.loads(raw_line)
            except json.JSONDecodeError as e:
                print(f"  Line {line_num}: JSON parse error: {e}", file=sys.stderr)
                stats["errors"] += 1
                continue

            pmid = s(article.get("pmid"))
            if not pmid:
                stats["errors"] += 1
                continue

            if pmid in existing_ids:
                stats["skipped"] += 1
                continue

            title = s(article.get("title"))
            journal = s(article.get("journal"))
            pub_date = s(article.get("pub_date"))
            authors = article.get("authors", [])
            abstract = s(article.get("abstract"))
            pub_types = article.get("publication_types", [])

            # 推斷研究類型
            study_type, evidence_level = infer_study_type(pub_types, title, abstract)

            # 分析功效分類
            claim_categories = analyze_claim_categories(title, abstract)

            # 提取成分
            ingredients = extract_ingredients(title, abstract)

            # 檢查 REVIEW_NEEDED
            review_reasons = check_review_needed(article)
            review_prefix = ""
            if review_reasons:
                review_prefix = "[REVIEW_NEEDED]\n\n"
                stats["review_needed"] += 1

            # 安全處理字串
            safe_title = title.replace('"', '\\"')
            source_url = f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"

            # 格式化作者列表
            authors_str = ", ".join(authors[:5])
            if len(authors) > 5:
                authors_str += f" et al. (+{len(authors)-5})"

            # 格式化 claim_categories 為 YAML 列表
            categories_yaml = json.dumps(claim_categories, ensure_ascii=False)
            ingredients_yaml = json.dumps(ingredients, ensure_ascii=False)

            # 建構 Markdown
            md = f"""{review_prefix}---
source_id: "{pmid}"
source_layer: "pubmed"
source_url: "{source_url}"
market: "global"
title: "{safe_title}"
journal: "{journal}"
pub_date: "{pub_date}"
study_type: "{study_type}"
evidence_level: {evidence_level}
topic: "{topic_id}"
claim_categories: {categories_yaml}
ingredients_mentioned: {ingredients_yaml}
fetched_at: "{now}"
---

# {title}

## 基本資訊
- 期刊：{journal}
- 發表日期：{pub_date}
- 研究類型：{study_type}
- 證據等級：Level {evidence_level}
- 主題：{topic_id}
- PMID：{pmid}

## 作者
{authors_str if authors_str else "（無資料）"}

## 摘要
{abstract if abstract else "（無資料）"}

## 功效分類
{", ".join(claim_categories)}

## 提及成分
{", ".join(ingredients) if ingredients else "（無明確成分提及）"}
"""

            # 寫入檔案
            filepath = os.path.join(topic_output_dir, f"{pmid}.md")
            with open(filepath, "w", encoding="utf-8") as out:
                out.write(md)

            existing_ids.add(pmid)
            stats["extracted"] += 1

    return stats


def main():
    parser = argparse.ArgumentParser(description="PubMed 萃取")
    parser.add_argument("--topic", help="指定主題 ID")
    parser.add_argument("--file", help="指定 JSONL 檔案")
    parser.add_argument("--force", action="store_true", help="強制覆蓋已存在檔案")
    args = parser.parse_args()

    if args.file:
        files = [args.file] if os.path.exists(args.file) else []
    else:
        files = find_jsonl_files(args.topic)

    if not files:
        print("未找到 JSONL 檔案", file=sys.stderr)
        sys.exit(1)

    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("📚 PubMed 萃取")
    print(f"   檔案數：{len(files)}")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

    total_stats = {"total": 0, "skipped": 0, "extracted": 0, "review_needed": 0, "errors": 0}

    for jsonl_file in files:
        print(f"\n📖 處理: {os.path.basename(jsonl_file)}")
        stats = process_file(jsonl_file, force=args.force)

        for k in total_stats:
            total_stats[k] += stats[k]

        print(f"  總行數：{stats['total']}")
        print(f"  跳過：{stats['skipped']}")
        print(f"  萃取：{stats['extracted']}")
        print(f"  REVIEW_NEEDED：{stats['review_needed']}")

    print("\n━━━ pubmed 萃取完成 ━━━")
    print(f"  總行數：{total_stats['total']}")
    print(f"  跳過（已存在）：{total_stats['skipped']}")
    print(f"  新萃取：{total_stats['extracted']}")
    print(f"  REVIEW_NEEDED：{total_stats['review_needed']}")
    print(f"  錯誤：{total_stats['errors']}")


if __name__ == "__main__":
    main()
