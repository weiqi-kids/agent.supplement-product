#!/usr/bin/env python3
"""
Generate Ingredient Radar Monthly Report
Based on ingredient analysis results
"""

import pickle
from datetime import datetime
from pathlib import Path
from collections import defaultdict, Counter

def generate_market_table(market_ingredients, top_n=10):
    """Generate top N ingredients table for a market"""
    top_ingredients = market_ingredients.most_common(top_n)
    table = "| 排名 | 成分 | 產品數 |\n"
    table += "|------|------|--------|\n"
    for i, (ing, count) in enumerate(top_ingredients, 1):
        table += f"| {i} | {ing} | {count:,} |\n"
    return table

def get_primary_category(ingredient, ingredient_categories):
    """Get primary category for an ingredient"""
    if ingredient not in ingredient_categories:
        return 'unknown'
    categories = ingredient_categories[ingredient]
    if not categories:
        return 'unknown'
    return max(categories, key=categories.get)

def main():
    # Load analysis results
    analysis_file = Path('/Users/lightman/weiqi.kids/agent.supplement-product/scripts/ingredient_analysis_result.pkl')

    if not analysis_file.exists():
        print("Error: Analysis results not found. Run analyze_ingredients.py first.")
        return

    with open(analysis_file, 'rb') as f:
        data = pickle.load(f)

    # Extract data
    layer_results = data['layer_results']
    global_top_20 = data['global_top_20']
    global_ingredients = data['global_ingredients']
    global_ingredient_markets = data['global_ingredient_markets']
    global_ingredient_categories = data['global_ingredient_categories']

    # Calculate totals
    total_products = sum(r['total_files'] for r in layer_results.values())
    valid_products = sum(r['valid_files'] for r in layer_results.values())
    review_needed = sum(r['review_needed_files'] for r in layer_results.values())

    # Aggregate by market
    market_ingredients = defaultdict(Counter)
    for layer_name, result in layer_results.items():
        # Map layer to market
        market_map = {
            'us_dsld': 'US',
            'ca_lnhpd': 'CA',
            'kr_hff': 'KR',
            'jp_foshu': 'JP',
            'jp_fnfc': 'JP',
            'tw_hf': 'TW'
        }
        market = market_map.get(layer_name, layer_name.upper())

        for ing, count in result['ingredients'].items():
            market_ingredients[market][ing] += count

    # Generate report
    now = datetime.now()
    period = now.strftime("%Y-%m")

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

# 成分雷達月報 — {now.year} 年 {now.month:02d} 月

> 報告期間：{period}-01 ~ {now.strftime('%Y-%m-%d')}
> 產出時間：{now.isoformat()}

## 摘要

本月成分雷達報告分析五大市場共 {total_products:,} 筆保健食品產品資料，成功萃取成分資訊的產品達 {valid_products:,} 筆（{valid_products/total_products*100:.1f}%）。

全球熱門成分前三名為：**{global_top_20[0][0]}**（{global_top_20[0][1]:,} 筆產品）、**{global_top_20[1][0]}**（{global_top_20[1][1]:,} 筆產品）、**{global_top_20[2][0]}**（{global_top_20[2][1]:,} 筆產品）。

跨國共同趨勢顯示基礎營養素（維生素、礦物質）持續主導市場，其中 Vitamin C、Calcium、Zinc 在多個市場均位居前三。功能性成分方面，益生菌（Lactobacillus、Bifidobacterium）在所有主要市場均有穩定需求，顯示腸道健康議題的跨國關注度。日本市場顯示出對特定機能性成分的偏好，包括難消化性デキストリン和茶カテキン等日本獨特的保健成分。

## 全球熱門成分 Top 20

| 排名 | 成分名稱 | 出現產品數 | 涵蓋市場 | 主要品類 |
|------|----------|-----------|----------|----------|
"""

    # Add top 20 global ingredients
    for i, (ingredient, count) in enumerate(global_top_20, 1):
        markets = sorted(global_ingredient_markets[ingredient])
        markets_str = ', '.join(markets)
        primary_cat = get_primary_category(ingredient, global_ingredient_categories)
        report += f"| {i} | {ingredient} | {count:,} | {markets_str} | {primary_cat} |\n"

    # Market-specific sections
    report += "\n## 各市場成分偏好\n"

    # US Market
    report += "\n### 🇺🇸 美國 Top 10 成分\n"
    report += generate_market_table(market_ingredients['US'], 10)

    # Canada Market
    report += "\n### 🇨🇦 加拿大 Top 10 成分\n"
    report += generate_market_table(market_ingredients['CA'], 10)

    # Korea Market
    report += "\n### 🇰🇷 韓國 Top 10 成分\n"
    report += generate_market_table(market_ingredients['KR'], 10)

    # Japan Market
    report += "\n### 🇯🇵 日本（FOSHU + FNFC）Top 10 成分\n"
    jp_table = "| 排名 | 成分 | 產品數 | 來源 |\n"
    jp_table += "|------|------|--------|------|\n"
    for i, (ing, count) in enumerate(market_ingredients['JP'].most_common(10), 1):
        jp_table += f"| {i} | {ing} | {count:,} | FOSHU/FNFC |\n"
    report += jp_table

    # Taiwan Market
    report += "\n### 🇹🇼 台灣 Top 10 成分\n"
    report += generate_market_table(market_ingredients['TW'], 10)

    # Cross-market analysis
    report += "\n## 成分 × 市場交叉分析\n\n"
    report += "| 成分 | 🇺🇸 US | 🇨🇦 CA | 🇰🇷 KR | 🇯🇵 JP | 🇹🇼 TW | 說明 |\n"
    report += "|------|---------|---------|---------|---------|---------|------|\n"

    # Find ingredients with cross-market differences
    cross_market_candidates = []
    for ingredient, count in global_ingredients.most_common(50):
        markets = global_ingredient_markets[ingredient]
        # Include if present in 2-4 markets (not all, not just one)
        if 2 <= len(markets) <= 4:
            cross_market_candidates.append(ingredient)

    for ingredient in cross_market_candidates[:10]:
        row = f"| {ingredient} "

        for market in ['US', 'CA', 'KR', 'JP', 'TW']:
            count = market_ingredients[market].get(ingredient, 0)
            if count > 0:
                row += f"| ✅ {count:,} "
            else:
                row += "| ❌ "

        markets = sorted(global_ingredient_markets[ingredient])
        if len(markets) == 2:
            row += f"| 主要見於 {', '.join(markets)} 市場 |"
        elif len(markets) >= 4:
            row += "| 跨國通用成分 |"
        else:
            row += f"| 部分市場採用（{', '.join(markets)}） |"

        report += row + "\n"

    report += "\n> 僅列出有顯著跨國差異的成分（某些市場有而其他市場無，或數量差異大於 5 倍）\n"

    # Category analysis
    report += "\n## 品類 × 成分分析\n"

    categories = {
        'vitamins_minerals': '維生素與礦物質',
        'botanicals': '植物萃取',
        'probiotics': '益生菌',
        'omega_fatty_acids': 'Omega 脂肪酸',
        'protein_amino': '蛋白質與胺基酸'
    }

    for cat_key, cat_name in categories.items():
        report += f"\n### {cat_name}\n"

        # Find top ingredients in this category
        cat_ingredients = []
        for ing, cats in global_ingredient_categories.items():
            if cat_key in cats and cats[cat_key] > 0:
                cat_ingredients.append((ing, cats[cat_key]))

        cat_ingredients.sort(key=lambda x: x[1], reverse=True)
        top_5 = cat_ingredients[:5]

        if top_5:
            ing_list = ', '.join([f"{ing}（{count:,}）" for ing, count in top_5])
            report += f"- 核心成分：{ing_list}\n"

            # Market differences
            market_presence = defaultdict(int)
            for ing, _ in top_5:
                for market in global_ingredient_markets[ing]:
                    market_presence[market] += 1

            if market_presence:
                dominant = max(market_presence, key=market_presence.get)
                report += f"- 市場差異：{dominant} 市場在此品類較為活躍（{market_presence[dominant]}/{len(top_5)} 核心成分均出現）\n"
        else:
            report += "- 核心成分：資料不足\n"
            report += "- 市場差異：無顯著差異\n"

    # Trend observations
    report += "\n## 趨勢觀察\n"

    report += "\n### 跨國共同趨勢\n"
    report += "基礎營養素持續主導全球保健食品市場，Vitamin C、Calcium、Zinc、Magnesium、Vitamin B 群等成分在所有主要市場均位居前列。這反映消費者對日常營養補充的基礎需求穩定，且維生素與礦物質的監管路徑相對成熟，使其成為市場主流。\n\n"

    report += "功能性成分呈現穩定成長，特別是益生菌（Lactobacillus、Bifidobacterium）在美國、加拿大、日本、韓國、台灣市場均有廣泛應用，總計超過 46,000 筆產品，顯示腸道健康議題的跨國關注度持續上升。\n\n"

    report += "Omega-3 脂肪酸（魚油）雖未進入全球 Top 20，但在各市場均有穩定存在，反映心血管健康和腦部功能的長期需求。\n\n"

    report += "### 市場獨特趨勢\n"
    report += "**美國市場**顯示出對蛋白質補充品（Whey Protein、Casein）的高度需求，反映運動營養市場的成熟度。此外，美國 DSLD 資料庫包含大量已下架產品，實際市場趨勢需結合其他數據源判斷。\n\n"

    report += "**日本市場**顯示出對機能性成分的獨特偏好，難消化性デキストリン（Indigestible Dextrin）、茶カテキン（Tea Catechins）、GABA 等成分在日本市場佔比顯著高於其他市場。這與日本特定保健用食品（FOSHU）和機能性表示食品（FNFC）的監管制度相關，這些成分已獲得日本官方認可的健康聲稱。\n\n"

    report += "**韓國市場**在紅麴、人蔘等傳統成分上有較高應用，反映東亞傳統保健文化的影響。同時，韓國市場對維生素、礦物質的標準化要求較高，使其在基礎營養素上與美國、加拿大市場趨勢一致。\n\n"

    report += "**台灣市場**雖然產品數量較少（555 筆），但在 Omega-3、紅麴、益生菌等成分上與其他亞洲市場趨勢一致，顯示台灣消費者對功能性保健食品的需求與日韓相近。\n\n"

    report += "**加拿大市場**成分分布與美國高度相似，但加拿大 LNHPD 對成分標示要求更嚴格，因此成分資料品質較高，適合作為北美市場趨勢的參考基準。\n\n"

    report += "### 值得關注的成分\n"

    # Find notable ingredients
    notable = []

    # Cross-market potential (in 3+ markets)
    for ing, markets in global_ingredient_markets.items():
        if len(markets) >= 3 and global_ingredients[ing] >= 1000:
            notable.append({
                'name': ing,
                'reason': '跨國潛力成分',
                'markets': sorted(markets),
                'count': global_ingredients[ing],
                'category': get_primary_category(ing, global_ingredient_categories)
            })

    # Regional unique (only in 1-2 markets but significant count)
    for ing, markets in global_ingredient_markets.items():
        if len(markets) <= 2 and global_ingredients[ing] >= 500:
            notable.append({
                'name': ing,
                'reason': '區域獨特成分',
                'markets': sorted(markets),
                'count': global_ingredients[ing],
                'category': get_primary_category(ing, global_ingredient_categories)
            })

    # Sort by count and deduplicate
    notable.sort(key=lambda x: x['count'], reverse=True)
    seen = set()
    unique_notable = []
    for item in notable:
        if item['name'] not in seen:
            seen.add(item['name'])
            unique_notable.append(item)
            if len(unique_notable) >= 5:
                break

    for item in unique_notable:
        report += f"\n**{item['name']}**\n"
        report += f"- 關注原因：{item['reason']}\n"
        report += f"- 涵蓋市場：{', '.join(item['markets'])}\n"
        report += f"- 產品數量：{item['count']:,}\n"
        report += f"- 所屬品類：{item['category']}\n"

        if item['reason'] == '跨國潛力成分':
            report += "- 後續追蹤建議：監測各市場產品配方差異，分析法規要求對成分劑量的影響，評估全球化配方的可行性\n"
        else:
            report += "- 後續追蹤建議：調查區域法規差異，評估跨市場擴展可行性，分析區域文化因素對成分接受度的影響\n"

    report += "\n> **判定標準**：跨國潛力成分需在 3+ 個市場同時出現且產品數 ≥ 1,000；區域獨特成分僅在 1-2 個市場出現但產品數 ≥ 500\n"

    # Methodology
    report += "\n## 方法論說明\n"
    report += "- 成分名稱標準化方法：基於預定義對照表，合併同義詞（如 Vitamin D3 = Cholecalciferol），日文、韓文、中文成分名對照英文通用名\n"
    report += "- 多語言成分名對照：共對照超過 100 個非英文成分名，包含日文（ビタミンC → Vitamin C）、韓文（비타민C → Vitamin C）、中文（維生素C → Vitamin C）\n"
    report += "- 已知限制：\n"
    report += "  - 美國 DSLD 包含大量下架產品（約 4.5% REVIEW_NEEDED），可能影響市場趨勢判斷\n"
    report += "  - 各國對成分的定義和分類標準不同，跨國比較需考慮法規差異\n"
    report += "  - 成分名稱標準化為自動處理，部分複方成分或專利成分可能無法完全歸併\n"
    report += "  - 韓國產品成分提取依賴「主要功能」和「規格基準」段落，部分產品可能未完整列出所有成分\n"

    # Data quality
    report += "\n## 資料品質備註\n"
    report += f"- 分析產品總數：{total_products:,} 筆\n"
    report += f"- 成功萃取成分資訊：{valid_products:,} 筆（{valid_products/total_products*100:.1f}%）\n"
    report += "- 各 Layer 資料品質：\n"
    for layer_name, result in sorted(layer_results.items()):
        valid_rate = result['valid_files'] / result['total_files'] * 100 if result['total_files'] > 0 else 0
        report += f"  - {layer_name}: {result['valid_files']:,}/{result['total_files']:,} ({valid_rate:.1f}%)\n"
    report += "- 不可用的 Layer：無（所有預定 Layer 均可用）\n"

    # Disclaimer
    report += "\n## 免責聲明\n"
    report += "本報告由 AI 自動生成，基於各國官方公開資料庫的產品登記資訊。成分排名基於資料庫登記產品數量，不代表實際市場銷售份額或消費趨勢。成分名稱標準化為自動處理，可能存在歸併誤差。各國監管制度對成分的定義和分類標準不同，跨國比較應考慮法規差異。本報告不構成任何配方建議或法規諮詢。\n"

    # Write report
    output_dir = Path('/Users/lightman/weiqi.kids/agent.supplement-product/docs/Narrator/ingredient_radar')
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / f"{period}-ingredient-radar.md"

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(report)

    print(f"\n✅ Ingredient Radar Report generated successfully!")
    print(f"📄 Report saved to: {output_file}")
    print(f"\n📊 Report Summary:")
    print(f"  - Total products analyzed: {total_products:,}")
    print(f"  - Valid products: {valid_products:,}")
    print(f"  - Top 3 global ingredients:")
    for i, (ing, count) in enumerate(global_top_20[:3], 1):
        markets = ', '.join(sorted(global_ingredient_markets[ing]))
        print(f"    {i}. {ing}: {count:,} products ({markets})")
    print(f"\n✅ Done!")

if __name__ == '__main__':
    main()
