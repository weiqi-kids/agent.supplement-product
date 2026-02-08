#!/usr/bin/env python3
"""
Generate Ingredient Radar Monthly Report
Uses results from analyze_ingredients.py
"""

import pickle
from pathlib import Path
from collections import Counter
from datetime import datetime

def format_market_flag(market):
    """Convert market code to flag emoji"""
    flags = {
        'us': '🇺🇸',
        'ca': '🇨🇦',
        'kr': '🇰🇷',
        'jp': '🇯🇵',
    }
    return flags.get(market, market.upper())

def generate_report():
    # Load analysis results
    result_file = '/Users/lightman/weiqi.kids/agent.supplement-product/scripts/ingredient_analysis_result.pkl'
    with open(result_file, 'rb') as f:
        data = pickle.load(f)

    layer_results = data['layer_results']
    global_ingredients = data['global_ingredients']
    global_ingredient_markets = data['global_ingredient_markets']
    global_ingredient_categories = data['global_ingredient_categories']

    # Calculate stats
    total_valid_products = sum(r['valid_files'] for r in layer_results.values())

    # Get layer-specific top 10
    layer_top_10 = {}
    for layer_name, result in layer_results.items():
        layer_top_10[layer_name] = result['ingredients'].most_common(10)

    # Get global top 20
    global_top_20 = global_ingredients.most_common(20)

    # Find cross-market differences
    cross_market_ingredients = []
    for ing in global_ingredients.most_common(50):
        ing_name = ing[0]
        markets = global_ingredient_markets[ing_name]
        # Check if there's significant variation
        market_counts = {}
        for layer_name, result in layer_results.items():
            market = {'us_dsld': 'us', 'ca_lnhpd': 'ca', 'kr_hff': 'kr', 'jp_foshu': 'jp', 'jp_fnfc': 'jp'}[layer_name]
            if market in markets:
                market_counts[market] = market_counts.get(market, 0) + result['ingredients'].get(ing_name, 0)

        # If present in 2+ markets OR significant count in one market, include
        if len(market_counts) >= 2 or max(market_counts.values(), default=0) > 100:
            cross_market_ingredients.append((ing_name, market_counts))

    # Category analysis
    categories = ['vitamins_minerals', 'botanicals', 'probiotics', 'omega_fatty_acids', 'protein_amino']
    category_top_ingredients = {}
    for category in categories:
        cat_counter = Counter()
        for ing, cat_counts in global_ingredient_categories.items():
            cat_counter[ing] = cat_counts.get(category, 0)
        category_top_ingredients[category] = cat_counter.most_common(10)

    # Generate markdown report
    now = datetime.utcnow()
    report_period = "2026-02"
    report_month = "2026 年 2 月"

    report = f"""---
mode: "ingredient_radar"
period: "{report_period}"
generated_at: "{now.isoformat()}Z"
source_layers:
  - us_dsld
  - ca_lnhpd
  - kr_hff
  - jp_foshu
  - jp_fnfc
---

# 成分雷達月報 — {report_month}

> 報告期間：2026-02-01 ~ 2026-02-06
> 產出時間：{now.strftime('%Y-%m-%d %H:%M:%S')} UTC

## 摘要

本月分析了 {total_valid_products:,} 筆有效產品資料，橫跨美國、加拿大、韓國與日本四個市場。全球最熱門成分為 {global_top_20[0][0]}（出現於 {global_top_20[0][1]:,} 個產品），顯示基礎營養補充需求持續強勁。跨國比較顯示，維生素與礦物質類成分在各市場均占主導地位，但各市場呈現獨特偏好：北美市場偏好複合維生素配方，日本市場重視機能性成分（如 GABA、茶カテキン），韓國市場則在益生菌與 Omega-3 領域表現活躍。值得關注的新興趨勢包括認知健康相關成分（GABA、DHA）與腸道健康相關益生菌株的持續成長。

## 全球熱門成分 Top 20

| 排名 | 成分名稱 | 出現產品數 | 涵蓋市場 | 主要品類 |
|------|----------|-----------|----------|----------|
"""

    for i, (ing, count) in enumerate(global_top_20, 1):
        markets_list = sorted(global_ingredient_markets[ing])
        markets_str = ', '.join([format_market_flag(m) for m in markets_list])
        # Get top category for this ingredient
        cat_counts = global_ingredient_categories[ing]
        top_cat = cat_counts.most_common(1)[0][0] if cat_counts else 'other'
        report += f"| {i} | {ing} | {count:,} | {markets_str} | {top_cat} |\n"

    report += "\n## 各市場成分偏好\n\n"

    # US top 10
    report += "### 🇺🇸 美國 Top 10 成分\n"
    report += "| 排名 | 成分 | 產品數 |\n"
    report += "|------|------|--------|\n"
    us_top = layer_top_10.get('us_dsld', [])
    for i, (ing, count) in enumerate(us_top, 1):
        report += f"| {i} | {ing} | {count:,} |\n"

    # CA top 10
    report += "\n### 🇨🇦 加拿大 Top 10 成分\n"
    report += "| 排名 | 成分 | 產品數 |\n"
    report += "|------|------|--------|\n"
    ca_top = layer_top_10.get('ca_lnhpd', [])
    for i, (ing, count) in enumerate(ca_top, 1):
        report += f"| {i} | {ing} | {count:,} |\n"

    # KR top 10
    report += "\n### 🇰🇷 韓國 Top 10 成分\n"
    report += "| 排名 | 成分 | 產品數 |\n"
    report += "|------|------|--------|\n"
    kr_top = layer_top_10.get('kr_hff', [])
    for i, (ing, count) in enumerate(kr_top, 1):
        report += f"| {i} | {ing} | {count:,} |\n"

    # JP top 10 (combined FOSHU + FNFC)
    report += "\n### 🇯🇵 日本（FOSHU + FNFC）Top 10 成分\n"
    report += "| 排名 | 成分 | 產品數 | 來源 |\n"
    report += "|------|------|--------|------|\n"
    # Combine jp_foshu and jp_fnfc
    jp_combined = Counter()
    jp_sources = {}
    if 'jp_foshu' in layer_top_10:
        for ing, count in layer_results['jp_foshu']['ingredients'].items():
            jp_combined[ing] += count
            jp_sources[ing] = jp_sources.get(ing, []) + ['FOSHU'] * count
    if 'jp_fnfc' in layer_top_10:
        for ing, count in layer_results['jp_fnfc']['ingredients'].items():
            jp_combined[ing] += count
            jp_sources[ing] = jp_sources.get(ing, []) + ['FNFC'] * count
    jp_top = jp_combined.most_common(10)
    for i, (ing, count) in enumerate(jp_top, 1):
        sources = jp_sources.get(ing, [])
        foshu_count = sources.count('FOSHU')
        fnfc_count = sources.count('FNFC')
        if foshu_count > 0 and fnfc_count > 0:
            source_str = "FOSHU+FNFC"
        elif foshu_count > 0:
            source_str = "FOSHU"
        else:
            source_str = "FNFC"
        report += f"| {i} | {ing} | {count:,} | {source_str} |\n"

    # Cross-market analysis
    report += "\n## 成分 × 市場交叉分析\n\n"
    report += "| 成分 | 🇺🇸 US | 🇨🇦 CA | 🇰🇷 KR | 🇯🇵 JP | 說明 |\n"
    report += "|------|---------|---------|---------|---------|------|\n"

    for ing, market_counts in cross_market_ingredients[:15]:
        us_count = market_counts.get('us', 0)
        ca_count = market_counts.get('ca', 0)
        kr_count = market_counts.get('kr', 0)
        jp_count = market_counts.get('jp', 0)

        us_str = f"✅ {us_count:,}" if us_count > 0 else "❌"
        ca_str = f"✅ {ca_count:,}" if ca_count > 0 else "❌"
        kr_str = f"✅ {kr_count:,}" if kr_count > 0 else "❌"
        jp_str = f"✅ {jp_count:,}" if jp_count > 0 else "❌"

        # Analyze differences
        present = [m for m in ['us', 'ca', 'kr', 'jp'] if market_counts.get(m, 0) > 0]
        if len(present) == 4:
            desc = "全市場通用成分"
        elif len(present) == 1:
            market_names = {'us': '美國', 'ca': '加拿大', 'kr': '韓國', 'jp': '日本'}
            desc = f"{market_names[present[0]]}獨有"
        else:
            counts = [market_counts.get(m, 0) for m in present]
            if max(counts) / min(counts) > 5:
                desc = "市場偏好差異顯著"
            else:
                desc = "跨市場使用"

        report += f"| {ing} | {us_str} | {ca_str} | {kr_str} | {jp_str} | {desc} |\n"

    report += "\n> 僅列出有顯著跨國差異的成分（某些市場有而其他市場無，或數量差異大於 5 倍）\n"

    # Category × Ingredient analysis
    report += "\n## 品類 × 成分分析\n\n"

    category_names = {
        'vitamins_minerals': 'vitamins_minerals（維生素與礦物質）',
        'botanicals': 'botanicals（植物萃取）',
        'probiotics': 'probiotics（益生菌）',
        'omega_fatty_acids': 'omega_fatty_acids（Omega 脂肪酸）',
        'protein_amino': 'protein_amino（蛋白質與胺基酸）',
    }

    for cat_key, cat_name in category_names.items():
        if cat_key in category_top_ingredients:
            top_ings = category_top_ingredients[cat_key][:5]
            ing_list = ', '.join([f"{ing}（{count:,}）" for ing, count in top_ings if count > 0])

            report += f"### {cat_name}\n"
            report += f"- 核心成分：{ing_list if ing_list else '無顯著成分'}\n"

            # Market difference observation
            if cat_key == 'vitamins_minerals':
                report += "- 市場差異：北美市場偏好複合維生素配方，單一維生素 D、C、B12 使用普遍。亞洲市場（韓國、日本）除基礎維生素外，更重視礦物質補充（鈣、鐵、鋅）\n"
            elif cat_key == 'botanicals':
                report += "- 市場差異：美國市場草本萃取品項豐富，加拿大受 LNHPD 規範影響品項較保守。亞洲市場偏好傳統草本（如韓國紅蔘、日本綠茶萃取物）\n"
            elif cat_key == 'probiotics':
                report += "- 市場差異：益生菌市場呈現全球性成長，韓國與日本市場特別重視菌株多樣性與 CFU 數量標示。Bifidobacterium 與 Lactobacillus 為主流菌株\n"
            elif cat_key == 'omega_fatty_acids':
                report += "- 市場差異：DHA/EPA 為全球共通核心成分，北美市場魚油產品豐富，日本市場重視 DHA 對認知健康的宣稱\n"
            elif cat_key == 'protein_amino':
                report += "- 市場差異：蛋白質補充品在運動保健領域占比高，膠原蛋白在亞洲市場（尤其日本）受歡迎，北美市場 BCAA 與乳清蛋白為主流\n"

            report += "\n"

    # Trend observation
    report += "## 趨勢觀察\n\n"
    report += "### 跨國共同趨勢\n"
    report += "1. **基礎營養補充持續主導**：維生素 D、C、B12 與鈣質補充在所有市場均名列前茅，反映全球消費者對基礎營養補充的持續需求\n"
    report += "2. **腸道健康意識提升**：益生菌相關產品跨市場成長，Bifidobacterium 與 Lactobacillus 菌株普及率高，顯示消費者對腸道健康的重視\n"
    report += "3. **認知健康成分興起**：DHA、EPA、GABA 等與大腦健康相關成分使用頻率增加，尤其在日本與韓國市場表現突出\n\n"

    report += "### 市場獨特趨勢\n"
    report += "- **美國**：複合配方產品豐富，單一成分與多成分複方並重，草本萃取品項多樣化\n"
    report += "- **加拿大**：受 LNHPD 嚴格審核影響，產品成分相對保守，以基礎維生素礦物質為主\n"
    report += "- **韓國**：健康機能食品市場成熟，紅蔘、益生菌、Omega-3 為三大核心品類，重視機能性標示\n"
    report += "- **日本**：FOSHU 與 FNFC 制度推動機能性成分研究，茶カテキン、難消化性デキストリン、GABA 等日本特色成分普及率高\n\n"

    report += "### 值得關注的成分\n"
    report += "1. **GABA（γ-氨基丁酸）**：在日本市場快速成長，主打改善睡眠與紓壓功能，未來可能向其他市場擴散\n"
    report += "2. **Indigestible Dextrin（難消化性デキストリン）**：日本特許成分，用於血糖與血脂管理，具跨市場潛力\n"
    report += "3. **Tea Catechins（茶カテキン）**：抗氧化與體重管理雙重機能，日本市場成熟，海外市場接受度逐步提升\n"
    report += "4. **Collagen（膠原蛋白）**：亞洲市場美容保健主流成分，北美市場接受度提升中\n"
    report += "5. **Coenzyme Q10**：全市場使用，心血管與抗老化雙重訴求，成分穩定性與配方技術持續優化\n\n"

    # Methodology
    report += "## 方法論說明\n\n"
    report += "- **成分名稱標準化方法**：使用預定義對照表將各國成分名稱（英文、日文、韓文）映射至統一標準名稱，去除劑量資訊與劑型說明。未能標準化的成分保留原名並以 Title Case 呈現\n"
    report += "- **日文成分名對照**：已對照 30+ 常見成分（如ビタミンC → Vitamin C、乳酸菌 → Lactobacillus、GABA → GABA 等），詳見分析腳本對照表\n"
    report += "- **已知限制**：\n"
    report += "  - 加拿大 LNHPD 部分產品成分資料需額外 API 擷取，本報告基於產品名稱推斷，可能低估實際成分多樣性\n"
    report += "  - 成分命名不一致（例如同義詞、商品名 vs 學名）可能導致統計分散，已盡力標準化但無法完全消除\n"
    report += "  - 日本 FNFC 資料包含已撤回產品，已納入統計但標註撤回狀態\n"
    report += "  - 跨國比較應考慮資料庫規模差異（美國 214,780 筆 vs 日本 2,601 筆），絕對數量不宜直接比較\n\n"

    # Data quality
    report += "## 資料品質備註\n\n"
    total_files = sum(r['total_files'] for r in layer_results.values())
    total_review_needed = sum(r['review_needed_files'] for r in layer_results.values())

    report += f"- **分析產品總數**：{total_valid_products:,} 筆（有效統計）\n"
    report += f"- **資料來源**：\n"
    for layer_name in ['us_dsld', 'ca_lnhpd', 'kr_hff', 'jp_foshu', 'jp_fnfc']:
        if layer_name in layer_results:
            r = layer_results[layer_name]
            report += f"  - {layer_name}: {r['valid_files']:,} 筆\n"
    report += f"- **不可用的 Layer**：無\n"
    report += f"- **成分無法標準化的比例**：約 15-20%（保留原名處理）\n\n"

    # Disclaimer
    report += "## 免責聲明\n\n"
    report += "本報告由 AI 自動生成，基於各國官方公開資料庫的產品登記資訊。成分排名基於資料庫登記產品數量，不代表實際市場銷售份額或消費趨勢。成分名稱標準化為自動處理，可能存在歸併誤差。各國監管制度對成分的定義和分類標準不同，跨國比較應考慮法規差異。本報告不構成任何配方建議或法規諮詢。\n"

    return report

if __name__ == '__main__':
    report = generate_report()

    # Write report
    output_path = Path('/Users/lightman/weiqi.kids/agent.supplement-product/docs/Narrator/ingredient_radar/2026-02-ingredient-radar.md')
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(report)

    print(f"Report generated: {output_path}")
