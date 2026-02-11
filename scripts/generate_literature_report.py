#!/usr/bin/env python3
"""文獻薈萃報告產出腳本 — 統計分析 PubMed 文獻資料"""
import json
import os
import sys
import glob
import argparse
import re
from datetime import datetime, timezone
from collections import defaultdict

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PUBMED_DIR = os.path.join(BASE_DIR, "docs/Extractor/pubmed")
TOPICS_DIR = os.path.join(BASE_DIR, "core/Narrator/Modes/topic_tracking/topics")
OUTPUT_DIR = os.path.join(BASE_DIR, "docs/Narrator/literature_review")

# 功效分類中文名稱
CLAIM_CATEGORY_NAMES = {
    "anti_aging": "抗衰老",
    "cardiovascular": "心血管",
    "cognitive": "認知功能",
    "immune": "免疫調節",
    "metabolic": "代謝",
    "musculoskeletal": "肌肉骨骼",
    "sexual": "性功能",
    "skin": "皮膚",
    "digestive": "消化",
    "energy": "活力",
    "other": "其他",
}

# 研究類型中文名稱
STUDY_TYPE_NAMES = {
    "meta_analysis": "Meta-Analysis",
    "systematic_review": "Systematic Review",
    "rct": "RCT",
    "clinical_trial": "Clinical Trial",
    "observational": "Observational",
    "review": "Review",
    "case_report": "Case Report",
    "other": "Other",
}


def load_topic_config(topic_id: str) -> dict:
    """載入主題設定檔"""
    import yaml
    topic_file = os.path.join(TOPICS_DIR, f"{topic_id}.yaml")
    if not os.path.exists(topic_file):
        return {"name": {"zh": topic_id, "en": topic_id}}

    with open(topic_file, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def parse_frontmatter(content: str) -> dict:
    """解析 Markdown frontmatter"""
    if not content.startswith("---"):
        return {}

    lines = content.split("\n")
    frontmatter = {}
    in_frontmatter = False
    fm_lines = []

    for line in lines:
        if line.strip() == "---":
            if in_frontmatter:
                break
            in_frontmatter = True
            continue
        if in_frontmatter:
            fm_lines.append(line)

    for line in fm_lines:
        if ":" in line:
            key, value = line.split(":", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            # 處理 JSON 陣列
            if value.startswith("[") and value.endswith("]"):
                try:
                    frontmatter[key] = json.loads(value)
                except:
                    frontmatter[key] = value
            else:
                frontmatter[key] = value

    return frontmatter


def load_articles(topic_id: str) -> list:
    """載入特定主題的所有文獻"""
    topic_dir = os.path.join(PUBMED_DIR, topic_id)
    if not os.path.exists(topic_dir):
        return []

    articles = []
    for md_file in glob.glob(os.path.join(topic_dir, "*.md")):
        try:
            with open(md_file, "r", encoding="utf-8") as f:
                content = f.read()

            # 跳過 REVIEW_NEEDED
            if content.startswith("[REVIEW_NEEDED]"):
                continue

            fm = parse_frontmatter(content)
            if fm:
                # 提取摘要（第一個 ## 摘要 之後的內容）
                abstract_match = re.search(r"## 摘要\n(.+?)(?=\n## |$)", content, re.DOTALL)
                fm["abstract_text"] = abstract_match.group(1).strip() if abstract_match else ""
                articles.append(fm)
        except Exception as e:
            print(f"  載入失敗: {md_file}: {e}", file=sys.stderr)

    return articles


def calculate_statistics(articles: list) -> dict:
    """計算文獻統計資料"""
    stats = {
        "total": len(articles),
        "by_evidence_level": defaultdict(int),
        "by_study_type": defaultdict(int),
        "by_claim_category": defaultdict(int),
        "by_ingredient": defaultdict(int),
        "level_1_articles": [],
        "level_2_articles": [],
    }

    for article in articles:
        # 證據等級統計
        level = article.get("evidence_level", 5)
        try:
            level = int(level)
        except:
            level = 5
        stats["by_evidence_level"][level] += 1

        # 研究類型統計
        study_type = article.get("study_type", "other")
        stats["by_study_type"][study_type] += 1

        # 功效分類統計
        categories = article.get("claim_categories", [])
        if isinstance(categories, str):
            categories = [categories]
        for cat in categories:
            stats["by_claim_category"][cat] += 1

        # 成分統計
        ingredients = article.get("ingredients_mentioned", [])
        if isinstance(ingredients, str):
            ingredients = [ingredients]
        for ing in ingredients:
            stats["by_ingredient"][ing] += 1

        # 收集高證據等級文獻
        if level == 1:
            stats["level_1_articles"].append(article)
        elif level == 2:
            stats["level_2_articles"].append(article)

    return stats


def generate_report(topic_id: str, period: str) -> str:
    """產生文獻薈萃報告"""
    # 載入主題設定
    config = load_topic_config(topic_id)
    topic_name = config.get("name", {}).get("zh", topic_id)

    # 載入文獻
    articles = load_articles(topic_id)
    if not articles:
        return ""

    # 計算統計
    stats = calculate_statistics(articles)
    now = datetime.now(timezone.utc).isoformat()

    # 解析期間
    year, month = period.split("-")

    # 計算百分比的輔助函數
    def pct(count, total):
        return f"{count/total*100:.1f}%" if total > 0 else "0%"

    # 構建報告
    report = f"""---
topic: "{topic_id}"
period: "{period}"
generated_at: "{now}"
total_articles: {stats['total']}
---

# {topic_name}文獻薈萃報告 — {year} 年 {int(month)} 月

## 摘要

本月共收錄 {topic_name} 相關文獻 {stats['total']} 篇，其中 Level 1 證據（Meta-Analysis/Systematic Review）{stats['by_evidence_level'].get(1, 0)} 篇，RCT {stats['by_study_type'].get('rct', 0)} 篇。

## 證據等級分布

| 證據等級 | 文獻數 | 佔比 |
|----------|--------|------|
| Level 1 (Meta-Analysis/Systematic Review) | {stats['by_evidence_level'].get(1, 0)} | {pct(stats['by_evidence_level'].get(1, 0), stats['total'])} |
| Level 2 (RCT) | {stats['by_evidence_level'].get(2, 0)} | {pct(stats['by_evidence_level'].get(2, 0), stats['total'])} |
| Level 3 (Clinical Trial) | {stats['by_evidence_level'].get(3, 0)} | {pct(stats['by_evidence_level'].get(3, 0), stats['total'])} |
| Level 4 (Observational) | {stats['by_evidence_level'].get(4, 0)} | {pct(stats['by_evidence_level'].get(4, 0), stats['total'])} |
| Level 5 (Review/Case Report/Other) | {stats['by_evidence_level'].get(5, 0)} | {pct(stats['by_evidence_level'].get(5, 0), stats['total'])} |

## 功效分類統計

| 功效分類 | 中文 | 文獻數 | 佔比 |
|----------|------|--------|------|
"""

    # 功效分類統計（排序）
    sorted_categories = sorted(stats['by_claim_category'].items(), key=lambda x: -x[1])
    for cat, count in sorted_categories:
        cat_name = CLAIM_CATEGORY_NAMES.get(cat, cat)
        report += f"| {cat} | {cat_name} | {count} | {pct(count, stats['total'])} |\n"

    report += """
## 成分搭配統計

| 成分 | 文獻數 |
|------|--------|
"""

    # 成分統計（取前 10）
    sorted_ingredients = sorted(stats['by_ingredient'].items(), key=lambda x: -x[1])[:10]
    for ing, count in sorted_ingredients:
        report += f"| {ing} | {count} |\n"

    report += """
## 研究類型分布

| 研究類型 | 文獻數 | 佔比 |
|----------|--------|------|
"""

    # 研究類型統計
    for study_type in ["meta_analysis", "systematic_review", "rct", "clinical_trial",
                       "observational", "review", "case_report", "other"]:
        count = stats['by_study_type'].get(study_type, 0)
        type_name = STUDY_TYPE_NAMES.get(study_type, study_type)
        report += f"| {type_name} | {count} | {pct(count, stats['total'])} |\n"

    # Level 1 文獻列表
    if stats['level_1_articles']:
        report += """
## 近期重要文獻

### Level 1 證據（Meta-Analysis / Systematic Review）

"""
        for i, article in enumerate(stats['level_1_articles'][:5], 1):
            title = article.get('title', 'Unknown')
            url = article.get('source_url', '')
            journal = article.get('journal', '')
            pub_date = article.get('pub_date', '')
            categories = article.get('claim_categories', [])
            if isinstance(categories, list):
                categories = ", ".join(categories)

            report += f"{i}. **[{title}]({url})** — {journal}, {pub_date}\n"
            report += f"   - 功效分類：{categories}\n\n"

    # Level 2 文獻列表
    if stats['level_2_articles']:
        report += """
### Level 2 證據（RCT）

"""
        for i, article in enumerate(stats['level_2_articles'][:5], 1):
            title = article.get('title', 'Unknown')
            url = article.get('source_url', '')
            journal = article.get('journal', '')
            pub_date = article.get('pub_date', '')
            categories = article.get('claim_categories', [])
            if isinstance(categories, list):
                categories = ", ".join(categories)

            report += f"{i}. **[{title}]({url})** — {journal}, {pub_date}\n"
            report += f"   - 功效分類：{categories}\n\n"

    return report


def list_topics() -> list:
    """列出有 pubmed 文獻的主題"""
    topics = []
    if not os.path.exists(PUBMED_DIR):
        return topics

    for item in os.listdir(PUBMED_DIR):
        item_path = os.path.join(PUBMED_DIR, item)
        if os.path.isdir(item_path) and item != "raw":
            # 確認目錄下有 .md 檔案
            if glob.glob(os.path.join(item_path, "*.md")):
                topics.append(item)

    return topics


def main():
    parser = argparse.ArgumentParser(description="文獻薈萃報告產出")
    parser.add_argument("--topic", help="指定主題 ID")
    parser.add_argument("--all", action="store_true", help="產出所有主題報告")
    parser.add_argument("--period", help="報告期間 (YYYY-MM)，預設為本月")
    parser.add_argument("--list", action="store_true", help="列出可用主題")
    args = parser.parse_args()

    if args.list:
        topics = list_topics()
        print("有文獻資料的主題:")
        for t in topics:
            print(f"  - {t}")
        return

    # 決定期間
    if args.period:
        period = args.period
    else:
        period = datetime.now().strftime("%Y-%m")

    # 決定主題
    if args.all:
        topics = list_topics()
    elif args.topic:
        topics = [args.topic]
    else:
        print("請指定 --topic 或 --all", file=sys.stderr)
        sys.exit(1)

    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("📊 文獻薈萃報告產出")
    print(f"   主題數：{len(topics)}")
    print(f"   報告期間：{period}")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

    for topic_id in topics:
        print(f"\n📖 處理主題: {topic_id}")

        report = generate_report(topic_id, period)
        if not report:
            print("  無文獻資料，跳過")
            continue

        # 確保輸出目錄存在
        topic_output_dir = os.path.join(OUTPUT_DIR, topic_id)
        os.makedirs(topic_output_dir, exist_ok=True)

        # 寫入報告
        output_file = os.path.join(topic_output_dir, f"{period}.md")
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(report)

        print(f"  ✅ 產出報告：{output_file}")

    print("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("✅ 報告產出完成")


if __name__ == "__main__":
    main()
