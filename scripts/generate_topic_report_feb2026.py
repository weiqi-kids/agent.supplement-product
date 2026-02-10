#!/usr/bin/env python3
"""
Generate topic tracking reports for February 2026
"""

import os
import re
import yaml
from pathlib import Path
from datetime import datetime
from collections import defaultdict, Counter
from typing import Dict, List, Set, Tuple

# Base paths
BASE_DIR = Path("/Users/lightman/weiqi.kids/agent.supplement-product")
EXTRACTOR_DIR = BASE_DIR / "docs" / "Extractor"
TOPICS_DIR = BASE_DIR / "core" / "Narrator" / "Modes" / "topic_tracking" / "topics"
OUTPUT_DIR = BASE_DIR / "docs" / "Narrator" / "topic_tracking"

# Layer mapping
LAYERS = {
    "us_dsld": "🇺🇸 美國",
    "ca_lnhpd": "🇨🇦 加拿大",
    "kr_hff": "🇰🇷 韓國",
    "jp_fnfc": "🇯🇵 日本 (FNFC)",
    "jp_foshu": "🇯🇵 日本 (FOSHU)"
}

def load_topic(topic_file: Path) -> Dict:
    """Load topic definition from YAML file"""
    with open(topic_file, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

def extract_field(content: str, field_name: str) -> str:
    """Extract field value from markdown content"""
    pattern = rf'^##\s+{re.escape(field_name)}\s*\n+(.*?)(?=\n##|\Z)'
    match = re.search(pattern, content, re.MULTILINE | re.DOTALL)
    if match:
        return match.group(1).strip()
    return ""

def extract_list_items(content: str, section: str) -> List[str]:
    """Extract list items from a section"""
    section_content = extract_field(content, section)
    if not section_content:
        return []

    items = []
    for line in section_content.split('\n'):
        line = line.strip()
        if line.startswith('- '):
            items.append(line[2:].strip())
        elif line.startswith('* '):
            items.append(line[2:].strip())
    return items

def matches_keyword(text: str, keywords: List[str], case_sensitive: bool = False) -> Tuple[bool, List[str]]:
    """Check if text matches any keyword"""
    if not text:
        return False, []

    matched = []
    search_text = text if case_sensitive else text.lower()

    for keyword in keywords:
        search_keyword = keyword if case_sensitive else keyword.lower()
        if search_keyword in search_text:
            matched.append(keyword)

    return len(matched) > 0, matched

def process_product(file_path: Path, topic: Dict) -> Tuple[bool, Dict]:
    """Check if product matches topic and extract data"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Skip REVIEW_NEEDED products
        if '[REVIEW_NEEDED]' in content.split('\n')[0]:
            return False, {}

        # Try to extract from frontmatter first
        frontmatter = {}
        if content.startswith('---'):
            try:
                parts = content.split('---', 2)
                if len(parts) >= 3:
                    frontmatter = yaml.safe_load(parts[1])
            except:
                pass

        # Extract metadata from frontmatter or markdown sections
        product_name = frontmatter.get('product_name') or extract_field(content, '產品名稱') or extract_field(content, '產品名') or extract_field(content, '品名')
        brand = frontmatter.get('brand') or extract_field(content, '品牌') or extract_field(content, '製造商') or extract_field(content, '申請者')
        product_form = frontmatter.get('product_form') or extract_field(content, '劑型')
        date_entered = frontmatter.get('date_entered') or extract_field(content, '登錄日期') or extract_field(content, '許可日期') or extract_field(content, '受理日')

        # Extract ingredients
        ingredients_str = extract_field(content, '成分') or extract_field(content, '機能性成分') or extract_field(content, '關與表示の科学的根拠等に関する基本情報')
        ingredients = extract_list_items(content, '成分') or extract_list_items(content, '機能性成分')

        # Check exact match (ingredients)
        exact_match, exact_keywords = matches_keyword(ingredients_str, topic['keywords'].get('exact', []))

        # Check fuzzy match (product name)
        fuzzy_match, fuzzy_keywords = matches_keyword(product_name, topic['keywords'].get('fuzzy', []))

        if not (exact_match or fuzzy_match):
            return False, {}

        return True, {
            'file': file_path.name,
            'product_name': product_name,
            'brand': brand,
            'product_form': product_form,
            'date_entered': date_entered,
            'ingredients': ingredients,
            'matched_exact': exact_keywords,
            'matched_fuzzy': fuzzy_keywords
        }

    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return False, {}

def scan_layer(layer: str, topic: Dict) -> List[Dict]:
    """Scan a layer for products matching the topic"""
    layer_dir = EXTRACTOR_DIR / layer
    if not layer_dir.exists():
        return []

    matched_products = []
    category_filters = topic.get('category_filter', [])

    # If no filter, scan all categories
    if not category_filters:
        category_filters = [d.name for d in layer_dir.iterdir() if d.is_dir() and d.name != 'raw']

    for category in category_filters:
        category_dir = layer_dir / category
        if not category_dir.exists():
            continue

        for md_file in category_dir.glob('*.md'):
            is_match, data = process_product(md_file, topic)
            if is_match:
                data['layer'] = layer
                data['category'] = category
                matched_products.append(data)

    return matched_products

def generate_report(topic_id: str, topic: Dict, products_by_layer: Dict[str, List[Dict]]) -> str:
    """Generate markdown report for a topic"""

    # Calculate total
    total_products = sum(len(prods) for prods in products_by_layer.values())

    if total_products == 0:
        return None

    # Analyze data
    all_products = []
    for prods in products_by_layer.values():
        all_products.extend(prods)

    # Brand analysis
    brand_counter = Counter()
    for prod in all_products:
        if prod['brand']:
            brand_counter[prod['brand']] += 1

    # Product form analysis
    form_counter = Counter()
    for prod in all_products:
        if prod['product_form']:
            form_counter[prod['product_form']] += 1

    # Market distribution
    market_stats = []
    for layer, prods in products_by_layer.items():
        if prods:
            brands = [p['brand'] for p in prods if p['brand']]
            top_brands = Counter(brands).most_common(3)
            market_stats.append({
                'layer': layer,
                'count': len(prods),
                'brands': [b[0] for b in top_brands]
            })

    # Generate report
    report_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    report = f"""---
topic: {topic_id}
period: "2026-02"
generated_at: "{report_date}"
---

# {topic['name']['zh']}市場報告 — 2026 年 2 月

## 摘要

本報告追蹤全球五大市場（美國、加拿大、韓國、日本）的{topic['name']['zh']}相關保健食品。截至 2026 年 2 月，共識別出 {total_products} 筆符合主題的產品資料，涵蓋 {len([l for l, p in products_by_layer.items() if p])} 個市場。

{topic['name']['zh']}產品在各市場呈現不同特色：美國與加拿大市場產品種類豐富，韓國與日本市場則以機能性明確的產品為主。

## 各國產品統計

| 市場 | 產品數 | 主要品牌 |
|------|--------|----------|
"""

    for stat in sorted(market_stats, key=lambda x: x['count'], reverse=True):
        brands_str = "、".join(stat['brands'][:3]) if stat['brands'] else "—"
        report += f"| {LAYERS[stat['layer']]} | {stat['count']} | {brands_str} |\n"

    report += f"\n**統計說明**：本統計排除標記為 `[REVIEW_NEEDED]` 的產品。\n\n"

    # Top brands
    if brand_counter:
        report += "## 熱門品牌/製造商\n\n"
        report += "| 排名 | 品牌/製造商 | 產品數 | 主要市場 |\n"
        report += "|------|-------------|--------|----------|\n"

        for rank, (brand, count) in enumerate(brand_counter.most_common(10), 1):
            # Find markets for this brand
            markets = set()
            for prod in all_products:
                if prod['brand'] == brand:
                    markets.add(prod['layer'])

            market_flags = " ".join([LAYERS[m].split()[0] for m in sorted(markets)])
            report += f"| {rank} | {brand} | {count} | {market_flags} |\n"

        report += "\n"

    # Product forms
    if form_counter:
        report += "## 劑型分布\n\n"
        report += "| 劑型 | 產品數 | 佔比 |\n"
        report += "|------|--------|------|\n"

        for form, count in form_counter.most_common(10):
            percentage = (count / total_products) * 100
            report += f"| {form} | {count} | {percentage:.1f}% |\n"

        report += "\n"

    # Recent products (if date_entered available)
    recent_products = [p for p in all_products if p.get('date_entered')]
    if recent_products:
        # Try to parse dates and sort
        dated_products = []
        for p in recent_products:
            date_str = p['date_entered']
            # Try to extract year-month
            match = re.search(r'(202[0-9])[/-]?([0-1][0-9])', date_str)
            if match:
                year, month = match.groups()
                dated_products.append((f"{year}-{month}", p))

        if dated_products:
            dated_products.sort(reverse=True, key=lambda x: x[0])

            # Filter for recent entries (2025-12 onwards)
            new_products = [(d, p) for d, p in dated_products if d >= "2025-12"]

            if new_products:
                report += "## 新品上市\n\n"
                report += "以下為近期新增的產品登錄：\n\n"

                for date, prod in new_products[:10]:
                    market = LAYERS[prod['layer']].split()[0]
                    report += f"- **{prod['product_name']}**（{prod['brand'] or '未標示'}）— {market} {date}\n"

                report += "\n"

    # Trend observations
    report += "## 趨勢觀察\n\n"

    # Analyze by market
    observations = []

    for layer, prods in products_by_layer.items():
        if not prods:
            continue

        market_name = LAYERS[layer]

        # Dominant forms
        forms = [p['product_form'] for p in prods if p['product_form']]
        if forms:
            top_form = Counter(forms).most_common(1)[0]
            if top_form[1] >= len(prods) * 0.3:  # If >30% are same form
                observations.append(f"{market_name}市場以 **{top_form[0]}** 為主要劑型（{top_form[1]} 筆，{top_form[1]/len(prods)*100:.1f}%）")

    if observations:
        for obs in observations:
            report += f"- {obs}\n"
    else:
        report += f"- {topic['name']['zh']}產品在各市場呈現多樣化的劑型與配方\n"
        report += f"- 產品總數達 {total_products} 筆，顯示市場對此類產品有穩定需求\n"

    # Matching keywords analysis
    exact_matches = sum(1 for p in all_products if p.get('matched_exact'))
    fuzzy_matches = sum(1 for p in all_products if p.get('matched_fuzzy') and not p.get('matched_exact'))

    report += f"\n**匹配說明**：{exact_matches} 筆產品透過成分精確匹配識別，{fuzzy_matches} 筆透過產品名稱模糊匹配識別。\n\n"

    # Footer
    report += "---\n\n"
    report += "*本報告由 AI 自動產出，資料來源為各國保健食品官方資料庫。報告內容僅供市場研究參考，不構成產品推薦或健康建議。*\n"

    return report

def main():
    """Main execution"""
    print("=== 主題追蹤報告產出 — 2026 年 2 月 ===\n")

    # Load topics
    topic_files = list(TOPICS_DIR.glob("*.yaml"))
    print(f"發現 {len(topic_files)} 個追蹤主題\n")

    results = []

    for topic_file in topic_files:
        topic = load_topic(topic_file)
        topic_id = topic['topic_id']

        print(f"處理主題: {topic['name']['zh']} ({topic_id})")
        print(f"  精確關鍵詞: {len(topic['keywords'].get('exact', []))} 個")
        print(f"  模糊關鍵詞: {len(topic['keywords'].get('fuzzy', []))} 個")
        print(f"  分類篩選: {', '.join(topic.get('category_filter', ['全部']))}")

        # Scan each layer
        products_by_layer = {}
        total_matched = 0

        for layer in LAYERS.keys():
            print(f"  掃描 {LAYERS[layer]}...", end=" ")
            matched = scan_layer(layer, topic)
            products_by_layer[layer] = matched
            print(f"{len(matched)} 筆")
            total_matched += len(matched)

        print(f"  總計匹配: {total_matched} 筆產品\n")

        if total_matched > 0:
            # Generate report
            report = generate_report(topic_id, topic, products_by_layer)

            if report:
                # Write to file
                output_dir = OUTPUT_DIR / topic_id
                output_dir.mkdir(parents=True, exist_ok=True)
                output_file = output_dir / "2026-02.md"

                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(report)

                print(f"  ✅ 報告已產出: {output_file}\n")

                results.append({
                    'topic': topic['name']['zh'],
                    'topic_id': topic_id,
                    'count': total_matched,
                    'file': str(output_file)
                })
            else:
                print(f"  ⚠️  無有效資料，跳過報告產出\n")
        else:
            print(f"  ⚠️  未找到匹配產品，跳過報告產出\n")

    # Summary
    print("=" * 60)
    print("執行完成\n")
    print("## 產出報告摘要\n")

    if results:
        for r in results:
            print(f"- **{r['topic']}** ({r['topic_id']}): {r['count']} 筆產品")
            print(f"  檔案: {r['file']}")
        print()
    else:
        print("無報告產出（未找到匹配產品）\n")

    return results

if __name__ == "__main__":
    main()
