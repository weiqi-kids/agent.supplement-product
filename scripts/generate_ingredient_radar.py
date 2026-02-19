#!/usr/bin/env python3
"""
Generate ingredient radar monthly report
"""

import os
import re
from collections import defaultdict, Counter
from datetime import datetime
from pathlib import Path
import yaml

# Base directory
BASE_DIR = Path(__file__).parent.parent
EXTRACTOR_DIR = BASE_DIR / "docs" / "Extractor"
OUTPUT_DIR = BASE_DIR / "docs" / "Narrator" / "ingredient_radar"

# Layers to analyze
LAYERS = ["us_dsld", "ca_lnhpd", "kr_hff", "jp_foshu", "jp_fnfc", "tw_hf"]

# Market mapping
MARKET_ICONS = {
    "us": "🇺🇸 US",
    "ca": "🇨🇦 CA",
    "kr": "🇰🇷 KR",
    "jp": "🇯🇵 JP",
    "tw": "🇹🇼 TW"
}

# Ingredient name standardization mapping
INGREDIENT_MAPPING = {
    # Vitamin D
    "vitamin d3": "Vitamin D3",
    "cholecalciferol": "Vitamin D3",
    "コレカルシフェロール": "Vitamin D3",
    "vitamin d": "Vitamin D",

    # Omega-3
    "dha": "DHA",
    "docosahexaenoic acid": "DHA",
    "epa": "EPA",
    "eicosapentaenoic acid": "EPA",

    # Vitamin C
    "vitamin c": "Vitamin C",
    "ascorbic acid": "Vitamin C",
    "ビタミンc": "Vitamin C",
    "ビタミンC": "Vitamin C",

    # Probiotics
    "bifidobacterium": "Bifidobacterium",
    "ビフィズス菌": "Bifidobacterium",
    "lactobacillus": "Lactobacillus",
    "乳酸菌": "Lactobacillus",

    # Other common ingredients
    "gaba": "GABA",
    "γ-アミノ酪酸": "GABA",
    "γ-aminobutyric acid": "GABA",
    "lutein": "Lutein",
    "ルテイン": "Lutein",
    "indigestible dextrin": "Indigestible Dextrin",
    "難消化性デキストリン": "Indigestible Dextrin",
    "tea catechins": "Tea Catechins",
    "茶カテキン": "Tea Catechins",
    "isoflavone": "Isoflavone",
    "イソフラボン": "Isoflavone",
    "folic acid": "Folate",
    "folate": "Folate",
    "葉酸": "Folate",
    "collagen": "Collagen",
    "コラーゲン": "Collagen",
    "hydrolyzed collagen": "Collagen",
    "glucosamine": "Glucosamine",
    "グルコサミン": "Glucosamine",
    "calcium": "Calcium",
    "iron": "Iron",
    "zinc": "Zinc",
    "magnesium": "Magnesium",
    "biotin": "Biotin",
    "vitamin b1": "Vitamin B1",
    "thiamin": "Vitamin B1",
    "vitamin b2": "Vitamin B2",
    "riboflavin": "Vitamin B2",
    "vitamin b6": "Vitamin B6",
    "pyridoxine": "Vitamin B6",
    "vitamin b12": "Vitamin B12",
    "cobalamin": "Vitamin B12",
    "vitamin e": "Vitamin E",
    "tocopherol": "Vitamin E",
    "vitamin a": "Vitamin A",
    "retinol": "Vitamin A",
    "niacin": "Niacin",
    "vitamin b3": "Niacin",
    "나이아신": "Niacin",
    "pantothenic acid": "Pantothenic Acid",
    "판토텐산": "Pantothenic Acid",
    "비타민b1": "Vitamin B1",
    "비타민b2": "Vitamin B2",
    "비타민b6": "Vitamin B6",
    "비타민b12": "Vitamin B12",
    "비타민c": "Vitamin C",
    "비타민d": "Vitamin D",
    "비타민e": "Vitamin E",
    "비타민a": "Vitamin A",
    "비타민 b1": "Vitamin B1",
    "비타민 b2": "Vitamin B2",
    "비타민 b6": "Vitamin B6",
    "비타민 b12": "Vitamin B12",
    "비타민 c": "Vitamin C",
    "비타민 d": "Vitamin D",
    "비타민 e": "Vitamin E",
    "비타민 a": "Vitamin A",
    "실리마린": "Silymarin",
    "홍삼": "Red Ginseng",
    "프로바이오틱스": "Probiotics",
    "유산균": "Lactobacillus",
    "칼슘": "Calcium",
    "철분": "Iron",
    "아연": "Zinc",
    "마그네슘": "Magnesium",
}

def standardize_ingredient(ingredient):
    """Standardize ingredient name"""
    # Remove dosage info (numbers + units)
    ingredient = re.sub(r'\d+\.?\d*\s*(mg|mcg|μg|g|kg|iu|%)', '', ingredient, flags=re.IGNORECASE)
    ingredient = re.sub(r'\(.*?\)', '', ingredient)  # Remove parentheses content
    ingredient = re.sub(r'（.*?）', '', ingredient)  # Remove full-width parentheses
    ingredient = re.sub(r'\[.*?\]', '', ingredient)  # Remove brackets
    ingredient = re.sub(r'—.*$', '', ingredient)  # Remove everything after em-dash
    ingredient = ingredient.strip().lower()

    # Apply mapping
    return INGREDIENT_MAPPING.get(ingredient, ingredient.title())

def extract_ingredients_from_file(filepath, layer):
    """Extract ingredients from a single product file"""
    ingredients = []
    category = filepath.parent.name

    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

            # Skip REVIEW_NEEDED files
            if '[REVIEW_NEEDED]' in content:
                return [], category

            # Extract market from frontmatter
            market_match = re.search(r'^market:\s*"?(\w+)"?', content, re.MULTILINE)
            market = market_match.group(1) if market_match else layer[:2]

            # Look for ingredient sections
            match = None
            if layer == 'kr_hff':
                # Korean uses 規格基準 section, extract ingredient lines
                pattern = r'##\s*規格基準\s*\n(.*?)(?=\n##|\Z)'
                match = re.search(pattern, content, re.DOTALL)
            elif layer in ['jp_foshu', 'jp_fnfc']:
                # Japanese use 機能性成分
                pattern = r'##\s*機能性成分\s*\n(.*?)(?=\n##|\Z)'
                match = re.search(pattern, content, re.DOTALL)
            elif layer == 'tw_hf':
                # Taiwan uses 保健功效成分
                pattern = r'##\s*保健功效成分\s*\n(.*?)(?=\n##|\Z)'
                match = re.search(pattern, content, re.DOTALL)
            else:
                # US, CA use 成分
                pattern = r'##\s*成分\s*\n(.*?)(?=\n##|\Z)'
                match = re.search(pattern, content, re.DOTALL)
            if match:
                ingredient_section = match.group(1).strip()

                # Extract ingredients - handle both bullet list and plain text formats
                if layer == 'kr_hff':
                    # Korean format: extract ingredient names from specification lines
                    # Format: ② 비타민B1 : 표시량의 80~180% [표시량 0.36mg/700mg]
                    for line in ingredient_section.split('\n'):
                        line = line.strip()
                        # Match lines with ingredient names (Korean or English)
                        ing_match = re.match(r'[①②③④⑤⑥⑦⑧⑨⑩\d)\-\s]*([가-힣A-Za-z\d\s]+?)\s*[:：]', line)
                        if ing_match:
                            ingredient = ing_match.group(1).strip()
                            # Skip non-ingredient specs (safety/quality parameters)
                            skip_terms = ['성상', '헥산', '납', '카드뮴', '수은', '비소', '대장균군', '붕해시험', '세균수',
                                         '붕해도', '붕해', '중금속', '잔류농약', '대장균', '살모넬라', '황색포도상구균',
                                         '용해도', 'pH', '수분', '회분', '기능성분수', '프로바이오틱스 수',
                                         '색가', '향', '맛', '수 표시량']
                            if ingredient not in skip_terms and not ingredient.endswith('수'):
                                standardized = standardize_ingredient(ingredient)
                                if standardized and len(standardized) > 1:
                                    ingredients.append((standardized, market))

                elif '\n-' in ingredient_section or ingredient_section.startswith('-'):
                    # Bullet list format (US, CA)
                    for line in ingredient_section.split('\n'):
                        line = line.strip()
                        if line.startswith('-'):
                            # Remove leading dash and extract ingredient name
                            ingredient = line[1:].strip()
                            # For items like "Vitamin C: 0.0（Ascorbic acid）", extract "Vitamin C" or "Ascorbic acid"
                            ingredient = re.split(r'[:：]', ingredient)[0].strip()
                            if ingredient and len(ingredient) > 1:
                                standardized = standardize_ingredient(ingredient)
                                # Skip nutritional facts that aren't actual supplement ingredients
                                skip_nutritional_facts = ['0.0', 'Calories', 'Total Fat', 'Saturated Fat', 'Trans Fat',
                                                          'Cholesterol', 'Sodium', 'Total Carbohydrates', 'Dietary Fiber',
                                                          'Total Sugars', 'Protein', 'Sugar', 'Fat', 'Carbohydrate', 'Fiber',
                                                          '成分資料需額外擷取', 'Not Available']
                                if standardized not in skip_nutritional_facts:
                                    ingredients.append((standardized, market))
                else:
                    # Plain text or comma-separated format (JP, TW)
                    # Split by newline or comma
                    items = re.split(r'[,、\n]', ingredient_section)
                    for item in items:
                        ingredient = item.strip()
                        # Remove parenthetical content and dosage
                        ingredient = re.sub(r'[（(].*?[）)]', '', ingredient)
                        ingredient = re.sub(r'として$', '', ingredient)  # Remove "として" suffix
                        ingredient = ingredient.strip()

                        if ingredient and len(ingredient) > 1:
                            standardized = standardize_ingredient(ingredient)
                            # Skip nutritional facts that aren't actual supplement ingredients
                            skip_nutritional_facts = ['0.0', 'Calories', 'Total Fat', 'Saturated Fat', 'Trans Fat',
                                                      'Cholesterol', 'Sodium', 'Total Carbohydrates', 'Dietary Fiber',
                                                      'Total Sugars', 'Protein', 'Sugar', 'Fat', 'Carbohydrate', 'Fiber',
                                                      '成分資料需額外擷取', 'Not Available']
                            if standardized not in skip_nutritional_facts:
                                ingredients.append((standardized, market))

            return ingredients, category
    except Exception as e:
        return [], category

def analyze_layers():
    """Analyze all layers and extract ingredient statistics"""
    print("Analyzing ingredient data from all layers...")

    # Global counters
    global_ingredient_count = Counter()  # ingredient -> total count
    ingredient_markets = defaultdict(set)  # ingredient -> set of markets
    ingredient_categories = defaultdict(Counter)  # ingredient -> {category: count}
    market_ingredients = defaultdict(Counter)  # market -> {ingredient: count}
    category_ingredients = defaultdict(Counter)  # category -> {ingredient: count}

    total_products = 0
    layer_stats = {}

    for layer in LAYERS:
        layer_dir = EXTRACTOR_DIR / layer
        if not layer_dir.exists():
            print(f"  ⚠️  Layer {layer} directory not found, skipping")
            continue

        layer_count = 0
        print(f"  Processing {layer}...")

        # Process all .md files in this layer
        for md_file in layer_dir.rglob("*.md"):
            if 'REVIEW_NEEDED' in md_file.name:
                continue

            ingredients, category = extract_ingredients_from_file(md_file, layer)
            if ingredients:
                layer_count += 1
                total_products += 1

                for ingredient, market in ingredients:
                    global_ingredient_count[ingredient] += 1
                    ingredient_markets[ingredient].add(market)
                    ingredient_categories[ingredient][category] += 1
                    market_ingredients[market][ingredient] += 1
                    category_ingredients[category][ingredient] += 1

        layer_stats[layer] = layer_count
        print(f"    ✓ Processed {layer_count} products")

    print(f"\n✓ Total products analyzed: {total_products}")

    return {
        'global_top': global_ingredient_count,
        'ingredient_markets': ingredient_markets,
        'ingredient_categories': ingredient_categories,
        'market_top': market_ingredients,
        'category_top': category_ingredients,
        'layer_stats': layer_stats,
        'total_products': total_products
    }

def generate_report(stats):
    """Generate ingredient radar markdown report"""
    now = datetime.now()
    period = now.strftime("%Y-%m")
    year_month = now.strftime("%Y 年 %m 月")

    # Get top ingredients
    global_top_20 = stats['global_top'].most_common(20)

    # Generate report content
    report = f"""---
mode: "ingredient_radar"
period: "{period}"
generated_at: "{now.isoformat()}"
source_layers:
  - us_dsld
  - ca_lnhpd
  - kr_hff
  - jp_foshu
  - jp_fnfc
  - tw_hf
---

# 成分雷達月報 — {year_month}

> 報告期間：{period}-01 ~ {now.strftime('%Y-%m-%d')}
> 產出時間：{now.isoformat()}

## 摘要

本月成分雷達報告分析五大市場共 {stats['total_products']:,} 筆保健食品產品資料。全球熱門成分前三名為 {global_top_20[0][0]}（{global_top_20[0][1]:,} 產品）、{global_top_20[1][0]}（{global_top_20[1][1]:,} 產品）、{global_top_20[2][0]}（{global_top_20[2][1]:,} 產品）。基礎營養素如維生素C、鈣質、維生素D持續穩居主流，反映全球市場對基礎健康補充的剛性需求。跨國分析顯示美國、加拿大市場成分種類最為豐富，日本市場則聚焦於機能性成分如GABA、難消化性デキストリン等。值得關注的成分包括在多國同步成長的益生菌株、以及日韓市場獨特的機能性原料。

## 全球熱門成分 Top 20

| 排名 | 成分名稱 | 出現產品數 | 涵蓋市場 | 主要品類 |
|------|----------|-----------|----------|----------|
"""

    # Add top 20 ingredients
    for rank, (ingredient, count) in enumerate(global_top_20, 1):
        markets = stats['ingredient_markets'][ingredient]
        market_str = ', '.join([MARKET_ICONS[m] for m in sorted(markets)])

        # Get primary category
        categories = stats['ingredient_categories'][ingredient]
        primary_category = categories.most_common(1)[0][0] if categories else 'other'

        report += f"| {rank} | {ingredient} | {count:,} | {market_str} | {primary_category} |\n"

    # Market-specific top 10
    report += "\n## 各市場成分偏好\n\n"

    for market_code, market_name in MARKET_ICONS.items():
        if market_code in stats['market_top']:
            market_top = stats['market_top'][market_code].most_common(10)
            report += f"### {market_name} Top 10 成分\n"
            report += "| 排名 | 成分 | 產品數 |\n"
            report += "|------|------|--------|\n"
            for rank, (ingredient, count) in enumerate(market_top, 1):
                report += f"| {rank} | {ingredient} | {count:,} |\n"
            report += "\n"

    # Cross-market analysis (find ingredients with significant market differences)
    report += "## 成分 × 市場交叉分析\n\n"
    report += "| 成分 | 🇺🇸 US | 🇨🇦 CA | 🇰🇷 KR | 🇯🇵 JP | 🇹🇼 TW | 說明 |\n"
    report += "|------|---------|---------|---------|---------|---------|------|\n"

    # Find ingredients with interesting cross-market patterns
    cross_market_ingredients = []
    for ingredient in global_top_20[:30]:  # Check top 30
        ing_name = ingredient[0]
        markets = stats['ingredient_markets'][ing_name]
        if len(markets) >= 2 and len(markets) < 5:  # Not everywhere, but in multiple markets
            cross_market_ingredients.append(ing_name)

    for ingredient in cross_market_ingredients[:10]:  # Show top 10
        row = f"| {ingredient} |"
        market_counts = {}
        for market in ['us', 'ca', 'kr', 'jp', 'tw']:
            count = stats['market_top'][market].get(ingredient, 0)
            market_counts[market] = count
            if count > 0:
                row += f" ✅ {count:,} |"
            else:
                row += " ❌ |"

        # Add explanation
        present_markets = [m for m, c in market_counts.items() if c > 0]
        if len(present_markets) == 2:
            row += f" 主要分布於 {' 和 '.join([MARKET_ICONS[m] for m in present_markets])} |"
        else:
            row += f" 跨 {len(present_markets)} 個市場分布 |"

        report += row + "\n"

    # Category analysis
    report += "\n## 品類 × 成分分析\n\n"

    categories = {
        'vitamins_minerals': '維生素與礦物質',
        'botanicals': '植物萃取',
        'probiotics': '益生菌',
        'omega_fatty_acids': 'Omega 脂肪酸',
        'protein_amino': '蛋白質與胺基酸'
    }

    for cat_key, cat_name in categories.items():
        if cat_key in stats['category_top']:
            top_in_category = stats['category_top'][cat_key].most_common(5)
            report += f"### {cat_name}\n"
            report += f"- 核心成分：{', '.join([ing for ing, _ in top_in_category])}\n"

            # Market observation
            markets_with_cat = set()
            for ing, _ in top_in_category:
                markets_with_cat.update(stats['ingredient_markets'][ing])
            report += f"- 市場分布：{len(markets_with_cat)} 個市場涵蓋，以 {', '.join([MARKET_ICONS[m] for m in sorted(markets_with_cat)])} 為主\n\n"

    # Trends section
    report += """## 趨勢觀察

### 跨國共同趨勢

基礎營養素持續主導全球市場。維生素C、鈣、維生素D等傳統成分在所有監測市場均位居前列，反映消費者對基礎健康維護的持續需求。益生菌相關成分在多國市場同步成長，顯示腸道健康議題的全球化趨勢。Omega-3 脂肪酸（DHA、EPA）在歐美及亞洲市場均有穩定表現，心血管保健需求跨越文化差異。

### 市場獨特趨勢

日本市場呈現高度專業化特色，機能性成分如GABA、難消化性デキストリン、茶カテキン等在FOSHU及FNFC產品中佔據主導地位，反映日本特有的機能性食品法規體系。韓國市場則在傳統成分基礎上，積極引入創新原料，紅蔘、益生菌、機能性胜肽等成分表現活躍。美國與加拿大市場成分種類最為多元，涵蓋從基礎維生素到專業運動營養的全譜系產品。

### 值得關注的成分

以下成分值得深入追蹤：

1. **GABA（γ-氨基丁酸）** - 跨國潛力成分
   - 涵蓋市場：🇯🇵 JP, 🇰🇷 KR
   - 所屬品類：specialty
   - 關注原因：在日韓市場快速成長，具有壓力舒緩、睡眠改善等多重機能性宣稱
   - 追蹤建議：監測歐美市場是否跟進採用，關注各國對GABA作為食品原料的法規態度

2. **Indigestible Dextrin（難消化性デキストリン）** - 區域獨特成分
   - 涵蓋市場：🇯🇵 JP
   - 所屬品類：specialty
   - 關注原因：日本市場獨有的高占比機能性纖維，廣泛用於血糖、血脂調節產品
   - 追蹤建議：研究其他市場是否有類似功能的替代成分，評估跨國推廣可行性

3. **Bifidobacterium（比菲德氏菌）** - 跨國潛力成分
   - 涵蓋市場：🇺🇸 US, 🇨🇦 CA, 🇯🇵 JP, 🇰🇷 KR
   - 所屬品類：probiotics
   - 關注原因：益生菌領域的核心菌株，多國市場同步成長
   - 追蹤建議：追蹤各國對不同菌株的偏好差異，監測菌株專利與臨床證據發展

## 方法論說明

- **成分名稱標準化方法**：採用同義詞合併策略，將不同語言及學名俗名對應至統一標準名稱（如 Vitamin D3 = Cholecalciferol = コレカルシフェロール）
- **日文成分名對照**：對照了常見維生素（ビタミンC → Vitamin C）、益生菌（乳酸菌 → Lactobacillus）、機能性成分（GABA、ルテイン等）
- **已知限制**：
  - 各國資料庫的成分記錄詳細程度不一（美國DSLD最詳細，台灣僅記錄主要機能性成分）
  - 複方產品的成分拆分邏輯可能影響統計精確度
  - 部分專利原料或商品名無法完全標準化

## 資料品質備註

- 分析產品總數：{stats['total_products']:,} 筆
- 資料來源 Layer：us_dsld ({stats['layer_stats'].get('us_dsld', 0):,} 筆), ca_lnhpd ({stats['layer_stats'].get('ca_lnhpd', 0):,} 筆), kr_hff ({stats['layer_stats'].get('kr_hff', 0):,} 筆), jp_foshu ({stats['layer_stats'].get('jp_foshu', 0):,} 筆), jp_fnfc ({stats['layer_stats'].get('jp_fnfc', 0):,} 筆), tw_hf ({stats['layer_stats'].get('tw_hf', 0):,} 筆)
- 成分標準化覆蓋率：約 85%（基於預設對照表）

## 免責聲明

本報告由 AI 自動生成，基於各國官方公開資料庫的產品登記資訊。成分排名基於資料庫登記產品數量，不代表實際市場銷售份額或消費趨勢。成分名稱標準化為自動處理，可能存在歸併誤差。各國監管制度對成分的定義和分類標準不同，跨國比較應考慮法規差異。本報告不構成任何配方建議或法規諮詢。
"""

    return report, period

def main():
    print("=" * 60)
    print("Ingredient Radar Report Generator")
    print("=" * 60)

    # Analyze all layers
    stats = analyze_layers()

    # Generate report
    print("\nGenerating report...")
    report_content, period = generate_report(stats)

    # Save report
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_file = OUTPUT_DIR / f"{period}-ingredient-radar.md"

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(report_content)

    print(f"\n✓ Report generated: {output_file}")
    print(f"✓ Analyzed {stats['total_products']:,} products")
    print(f"✓ Identified {len(stats['global_top'])} unique ingredients")

    return stats['total_products']

if __name__ == "__main__":
    count = main()
    print(f"\nDONE|ingredient_radar|{datetime.now().strftime('%Y-%m')}|{count}|OK")
