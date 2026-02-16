#!/usr/bin/env python3
"""
主題報告產出腳本

功能：
1. 讀取 topics/*.yaml 取得追蹤主題定義
2. 從 docs/Extractor/{layer}/{category}/*.md 篩選符合關鍵詞的產品
3. 產出月度市場報告

用法：
  python3 scripts/generate_topic_report.py                    # 產出所有主題報告
  python3 scripts/generate_topic_report.py --topic exosomes   # 產出特定主題
  python3 scripts/generate_topic_report.py --dry-run          # Dry run 模式
"""

import argparse
import re
import yaml
from pathlib import Path
from datetime import datetime
from collections import defaultdict
from typing import Optional


# 路徑配置
PROJECT_ROOT = Path(__file__).parent.parent
TOPICS_DIR = PROJECT_ROOT / "core" / "Narrator" / "Modes" / "topic_tracking" / "topics"
EXTRACTOR_DIR = PROJECT_ROOT / "docs" / "Extractor"
OUTPUT_DIR = PROJECT_ROOT / "docs" / "Narrator" / "topic_tracking"
DHI_DIR = EXTRACTOR_DIR / "dhi"

# 主題與 DHI 類別對照
TOPIC_DHI_CATEGORIES = {
    "fish-oil": ["omega_fatty_acid"],
    "curcumin": ["botanical"],
    "nattokinase": ["enzyme"],
    "glucosamine": ["amino_acid"],
    "collagen": ["protein"],
    "lutein": ["vitamin"],
    "nmn": ["other"],
    "red-yeast-rice": ["botanical"],
    "exosomes": ["other"],
}

# Layer 對應市場
LAYER_MARKET = {
    "us_dsld": {"name": "美國", "flag": "🇺🇸", "code": "US"},
    "ca_lnhpd": {"name": "加拿大", "flag": "🇨🇦", "code": "CA"},
    "kr_hff": {"name": "韓國", "flag": "🇰🇷", "code": "KR"},
    "jp_fnfc": {"name": "日本 FNFC", "flag": "🇯🇵", "code": "JP"},
    "jp_foshu": {"name": "日本 FOSHU", "flag": "🇯🇵", "code": "JP"},
    "tw_hf": {"name": "台灣", "flag": "🇹🇼", "code": "TW"},
}


def load_topic(topic_path: Path) -> dict:
    """載入主題定義"""
    with open(topic_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_all_topics() -> list[dict]:
    """載入所有主題定義"""
    topics = []
    for yaml_file in TOPICS_DIR.glob("*.yaml"):
        topic = load_topic(yaml_file)
        topic["_file"] = yaml_file.name
        topics.append(topic)
    return topics


def parse_product_file(file_path: Path) -> dict:
    """解析產品 Markdown 檔案"""
    content = file_path.read_text(encoding="utf-8")

    # 檢查 REVIEW_NEEDED 標記
    if "[REVIEW_NEEDED]" in content:
        return None

    product = {
        "file_path": str(file_path),
        "content": content,
        "name": "",
        "brand": "",
        "manufacturer": "",
        "ingredients": [],
        "form": "",
        "layer": file_path.parent.parent.name,
        "category": file_path.parent.name,
    }

    # 解析 frontmatter
    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            try:
                fm = yaml.safe_load(parts[1])
                if fm:
                    product["name"] = fm.get("product_name", "")
                    product["brand"] = fm.get("brand", "")
                    product["manufacturer"] = fm.get("manufacturer", "")
                    product["form"] = fm.get("product_form", "")
            except yaml.YAMLError:
                pass

    # 提取成分（從 ## 成分 或 ## 機能性成分 段落）
    ingredient_patterns = [
        r"## 成分\s*\n([\s\S]*?)(?=\n##|\Z)",
        r"## 機能性成分\s*\n([\s\S]*?)(?=\n##|\Z)",
        r"## 機能性関与成分\s*\n([\s\S]*?)(?=\n##|\Z)",
        r"## Ingredients\s*\n([\s\S]*?)(?=\n##|\Z)",
    ]

    for pattern in ingredient_patterns:
        match = re.search(pattern, content, re.IGNORECASE)
        if match:
            ingredients_text = match.group(1)
            # 提取列表項目
            for line in ingredients_text.split("\n"):
                line = line.strip()
                if line.startswith("- "):
                    product["ingredients"].append(line[2:].strip())
                elif line and not line.startswith("#"):
                    product["ingredients"].append(line)

    return product


def match_product(product: dict, topic: dict) -> bool:
    """檢查產品是否匹配主題關鍵詞"""
    if not product:
        return False

    keywords = topic.get("keywords", {})
    exact_keywords = [k.lower() for k in keywords.get("exact", [])]
    fuzzy_keywords = [k.lower() for k in keywords.get("fuzzy", [])]

    # 精確匹配成分
    for ingredient in product.get("ingredients", []):
        ingredient_lower = ingredient.lower()
        for keyword in exact_keywords:
            if keyword in ingredient_lower:
                return True

    # 模糊匹配產品名稱和內容
    search_text = " ".join([
        product.get("name", ""),
        product.get("content", ""),
    ]).lower()

    for keyword in exact_keywords + fuzzy_keywords:
        if keyword in search_text:
            return True

    return False


def load_interaction_data(topic_id: str) -> list[dict]:
    """
    從 docs/Extractor/dhi/{category}/*.md 讀取交互資料
    根據主題 ID 篩選相關類別
    """
    interactions = []
    categories = TOPIC_DHI_CATEGORIES.get(topic_id, [])

    if not categories:
        return interactions

    for category in categories:
        category_dir = DHI_DIR / category
        if not category_dir.exists():
            continue

        for md_file in category_dir.glob("*.md"):
            content = md_file.read_text(encoding="utf-8")

            # 跳過 REVIEW_NEEDED（但仍解析以獲取資訊）
            is_review_needed = "[REVIEW_NEEDED]" in content

            # 解析 frontmatter
            interaction = {
                "file_path": str(md_file),
                "pmid": md_file.stem,
                "is_review_needed": is_review_needed,
            }

            if content.startswith("---") or content.startswith("[REVIEW_NEEDED]\n\n---"):
                # 處理 [REVIEW_NEEDED] 標記後的 frontmatter
                clean_content = content.replace("[REVIEW_NEEDED]\n\n", "")
                parts = clean_content.split("---", 2)
                if len(parts) >= 3:
                    try:
                        fm = yaml.safe_load(parts[1])
                        if fm:
                            interaction["title"] = fm.get("title", "")
                            interaction["severity"] = fm.get("severity", "unknown")
                            interaction["evidence_level"] = fm.get("evidence_level", 5)
                            interaction["study_type"] = fm.get("study_type", "other")
                            interaction["source_url"] = fm.get("source_url", "")
                            interaction["journal"] = fm.get("journal", "")
                            interaction["pub_date"] = fm.get("pub_date", "")
                    except yaml.YAMLError:
                        pass

            # 提取摘要（用於推斷風險描述）
            abstract_match = re.search(r"## 摘要\s*\n([\s\S]*?)(?=\n---|\Z)", content)
            if abstract_match:
                interaction["abstract"] = abstract_match.group(1).strip()
            else:
                interaction["abstract"] = ""

            interactions.append(interaction)

    return interactions


def infer_risk_description(interaction: dict) -> str:
    """從摘要推斷風險描述"""
    abstract = interaction.get("abstract", "").lower()
    title = interaction.get("title", "").lower()
    text = f"{title} {abstract}"

    # 常見風險關鍵詞
    if any(kw in text for kw in ["bleeding", "hemorrhag", "coagulopathy"]):
        return "增加出血風險"
    if any(kw in text for kw in ["hypoglycemia", "blood glucose", "blood sugar"]):
        return "影響血糖控制"
    if any(kw in text for kw in ["hypotension", "blood pressure"]):
        return "影響血壓"
    if any(kw in text for kw in ["hepatotoxic", "liver"]):
        return "肝臟代謝影響"
    if any(kw in text for kw in ["no effect", "no significant", "did not affect"]):
        return "無顯著交互"
    return "交互機轉待釐清"


def format_interaction_section(topic_name: str, interactions: list[dict]) -> str:
    """產生交互作用章節 Markdown"""
    if not interactions:
        return ""

    # 按嚴重程度分組
    by_severity = defaultdict(list)
    for interaction in interactions:
        severity = interaction.get("severity", "unknown")
        by_severity[severity].append(interaction)

    section = f"""
## ⚠️ 藥物交互提醒

本章節整理{topic_name}相關的藥物交互文獻，供參考。

"""

    severity_order = ["major", "moderate", "minor", "unknown"]
    severity_labels = {
        "major": "高風險交互 (Major)",
        "moderate": "中等風險交互 (Moderate)",
        "minor": "低風險/無交互 (Minor)",
        "unknown": "待評估 (Unknown)",
    }

    has_content = False
    for severity in severity_order:
        items = by_severity.get(severity, [])
        if not items:
            continue

        has_content = True
        section += f"### {severity_labels[severity]}\n\n"
        section += "| 文獻標題 | 風險描述 | 證據等級 | 來源 |\n"
        section += "|----------|----------|----------|------|\n"

        for item in items:
            title = item.get("title", "")[:50]
            if len(item.get("title", "")) > 50:
                title += "..."
            risk_desc = infer_risk_description(item)
            level = item.get("evidence_level", 5)
            pmid = item.get("pmid", "")
            url = item.get("source_url", f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/")
            section += f"| {title} | {risk_desc} | Level {level} | [PMID:{pmid}]({url}) |\n"

        section += "\n"

    if not has_content:
        return ""

    section += """> ⚠️ **免責聲明**：本資訊僅供教育和研究目的，不構成醫療建議。
> 任何用藥或補充劑變更應諮詢專業醫療人員。

"""

    return section


def scan_products(topic: dict, dry_run: bool = False) -> list[dict]:
    """掃描並篩選符合主題的產品"""
    matched_products = []
    category_filter = topic.get("category_filter", [])

    for layer_dir in EXTRACTOR_DIR.iterdir():
        if not layer_dir.is_dir():
            continue
        if layer_dir.name not in LAYER_MARKET:
            continue

        # 遍歷分類目錄
        for category_dir in layer_dir.iterdir():
            if not category_dir.is_dir():
                continue
            if category_dir.name == "raw":
                continue

            # 如果有分類過濾，檢查是否符合
            if category_filter and category_dir.name not in category_filter:
                continue

            # 掃描產品檔案
            for product_file in category_dir.glob("*.md"):
                product = parse_product_file(product_file)
                if product and match_product(product, topic):
                    matched_products.append(product)

    return matched_products


def generate_report(topic: dict, products: list[dict]) -> str:
    """產生市場報告"""
    topic_id = topic["topic_id"]
    topic_name = topic["name"]["zh"]
    now = datetime.now()
    period = now.strftime("%Y-%m")

    # 統計數據
    by_layer = defaultdict(list)
    by_brand = defaultdict(int)
    by_form = defaultdict(int)

    for product in products:
        layer = product["layer"]
        by_layer[layer].append(product)

        brand = product.get("brand") or product.get("manufacturer") or "未知"
        by_brand[brand] += 1

        form = product.get("form") or "未知"
        by_form[form] += 1

    # 產生報告
    report = f"""---
topic: {topic_id}
period: "{period}"
generated_at: "{now.isoformat()}"
source_layers:
"""
    for layer in LAYER_MARKET.keys():
        if layer in by_layer:
            report += f"  - {layer}\n"

    report += f"""---

# {topic_name}市場報告 — {now.year} 年 {now.month} 月

> 報告期間：{now.strftime("%Y-%m")}-01 ~ {now.strftime("%Y-%m-%d")}
> 產出時間：{now.isoformat()}

## 摘要

本月{topic_name}主題追蹤共篩選出 {len(products)} 筆相關產品，涵蓋 {len(by_layer)} 個市場。
"""

    # 市場概況
    if by_layer:
        top_market = max(by_layer.items(), key=lambda x: len(x[1]))
        market_info = LAYER_MARKET.get(top_market[0], {})
        report += f"{market_info.get('name', top_market[0])} 市場以 {len(top_market[1])} 筆產品居首。"

    report += """

## 各國產品統計

| 市場 | 產品數 | 主要品牌 |
|------|--------|----------|
"""

    for layer, layer_products in sorted(by_layer.items(), key=lambda x: -len(x[1])):
        market_info = LAYER_MARKET.get(layer, {"flag": "", "name": layer})

        # 統計該市場的品牌
        layer_brands = defaultdict(int)
        for p in layer_products:
            brand = p.get("brand") or p.get("manufacturer") or "未知"
            layer_brands[brand] += 1
        top_brands = sorted(layer_brands.items(), key=lambda x: -x[1])[:3]
        brands_str = ", ".join([b[0] for b in top_brands if b[0] != "未知"][:2]) or "-"

        report += f"| {market_info['flag']} {market_info['name']} | {len(layer_products)} | {brands_str} |\n"

    # 熱門品牌
    report += """
## 熱門品牌/製造商

| 排名 | 品牌/製造商 | 產品數 |
|------|-------------|--------|
"""

    top_brands = sorted(by_brand.items(), key=lambda x: -x[1])[:10]
    for i, (brand, count) in enumerate(top_brands, 1):
        if brand != "未知":
            report += f"| {i} | {brand} | {count} |\n"

    # 劑型分布
    report += """
## 劑型分布

| 劑型 | 產品數 | 佔比 |
|------|--------|------|
"""

    total = len(products)
    for form, count in sorted(by_form.items(), key=lambda x: -x[1]):
        pct = count / total * 100 if total > 0 else 0
        report += f"| {form} | {count} | {pct:.1f}% |\n"

    # 藥物交互章節
    interactions = load_interaction_data(topic_id)
    if interactions:
        interaction_section = format_interaction_section(topic_name, interactions)
        report += interaction_section

    # 趨勢觀察
    report += f"""
## 趨勢觀察

本月{topic_name}相關產品主要集中在以下市場與類型：

"""

    if by_layer:
        for layer in list(by_layer.keys())[:3]:
            market_info = LAYER_MARKET.get(layer, {"name": layer})
            report += f"- **{market_info['name']}**：{len(by_layer[layer])} 筆產品\n"

    report += """
---

*本報告由系統自動產生，資料來源為各國官方保健食品資料庫。*
"""

    return report


def main():
    parser = argparse.ArgumentParser(description="主題報告產出腳本")
    parser.add_argument("--topic", help="指定主題 ID（不指定則處理所有主題）")
    parser.add_argument("--dry-run", action="store_true", help="Dry run 模式，僅顯示匹配結果")
    args = parser.parse_args()

    print("=" * 50)
    print("主題報告產出")
    print("=" * 50)

    # 載入主題
    topics = load_all_topics()
    if args.topic:
        topics = [t for t in topics if t["topic_id"] == args.topic]
        if not topics:
            print(f"❌ 找不到主題: {args.topic}")
            return

    print(f"📋 載入 {len(topics)} 個主題定義")

    for topic in topics:
        topic_id = topic["topic_id"]
        topic_name = topic["name"]["zh"]

        print(f"\n{'='*50}")
        print(f"📊 處理主題: {topic_name} ({topic_id})")
        print(f"{'='*50}")

        # 掃描產品
        products = scan_products(topic, args.dry_run)
        print(f"✅ 匹配產品: {len(products)} 筆")

        if args.dry_run:
            # 顯示匹配結果
            by_layer = defaultdict(int)
            for p in products:
                by_layer[p["layer"]] += 1

            print("\n各市場匹配數量:")
            for layer, count in sorted(by_layer.items(), key=lambda x: -x[1]):
                market_info = LAYER_MARKET.get(layer, {"flag": "", "name": layer})
                print(f"  {market_info['flag']} {market_info['name']}: {count}")

            print("\n範例產品 (前 5 筆):")
            for p in products[:5]:
                print(f"  - [{p['layer']}] {p['name'][:50]}...")
        else:
            # 產生報告
            report = generate_report(topic, products)

            # 寫入檔案
            output_dir = OUTPUT_DIR / topic_id
            output_dir.mkdir(parents=True, exist_ok=True)

            period = datetime.now().strftime("%Y-%m")
            output_file = output_dir / f"{period}.md"
            output_file.write_text(report, encoding="utf-8")

            print(f"📝 報告已寫入: {output_file.relative_to(PROJECT_ROOT)}")

    print("\n" + "=" * 50)
    print("✅ 完成")
    print("=" * 50)


if __name__ == "__main__":
    main()
