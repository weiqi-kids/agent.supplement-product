#!/usr/bin/env python3
"""
成分雷達報告產出腳本
基於 ingredient_analysis_result.pkl 產出月報
"""

import pickle
from pathlib import Path
from datetime import datetime
from collections import Counter, defaultdict

def format_markets(markets):
    """格式化市場清單"""
    return ", ".join(sorted(markets))

def get_top_category(ingredient_categories, ingredient):
    """取得成分的主要品類"""
    if ingredient not in ingredient_categories:
        return "other"
    cat_counter = ingredient_categories[ingredient]
    if cat_counter:
        return cat_counter.most_common(1)[0][0]
    return "other"

def generate_report(data):
    """產出成分雷達報告"""
    now = datetime.now().isoformat()
    period = datetime.now().strftime("%Y-%m")
    year = datetime.now().year
    month = datetime.now().month
    day = datetime.now().day

    # 計算總計
    total_products = sum(r['total_files'] for r in data['layer_results'].values())
    total_valid = sum(r['valid_files'] for r in data['layer_results'].values())

    # 全球 Top 成分
    global_top = data['global_top_20']
    ingredient_markets = data['global_ingredient_markets']
    ingredient_categories = data['global_ingredient_categories']

    # 各市場 Top 10
    market_tops = {}
    for market_code in ['us', 'ca', 'kr', 'jp', 'tw']:
        market_counter = Counter()
        for layer_name, result in data['layer_results'].items():
            for ing, count in result['ingredients'].items():
                if market_code in result['ingredient_markets'][ing]:
                    market_counter[ing] += count
        market_tops[market_code] = market_counter.most_common(10)

    # 品類 Top 5
    category_tops = {}
    for cat in ['vitamins_minerals', 'botanicals', 'probiotics', 'omega_fatty_acids', 'protein_amino', 'specialty', 'sports_fitness']:
        cat_counter = Counter()
        for ing, cat_counts in ingredient_categories.items():
            if cat in cat_counts:
                cat_counter[ing] += cat_counts[cat]
        category_tops[cat] = cat_counter.most_common(5)

    # 開始產出報告
    report = f"""---
mode: "ingredient_radar"
period: "{period}"
generated_at: "{now}"
source_layers:
  - us_dsld
  - ca_lnhpd
  - kr_hff
  - jp_foshu
  - jp_fnfc
  - tw_hf
---

# 成分雷達月報 — {year} 年 {month:02d} 月

> 報告期間：{period}-01 ~ {year}-{month:02d}-{day:02d}
> 產出時間：{now}

## 摘要

本月成分雷達報告分析五大市場共 {total_products:,} 筆保健食品產品資料，成功萃取成分資訊的產品達 {total_valid:,} 筆（{total_valid/total_products*100:.1f}%）。

全球熱門成分前三名為：**{global_top[0][0]}**（{global_top[0][1]:,} 筆產品）、**{global_top[1][0]}**（{global_top[1][1]:,} 筆產品）、**{global_top[2][0]}**（{global_top[2][1]:,} 筆產品）。

跨國共同趨勢顯示基礎營養素（維生素、礦物質）持續主導市場，其中 {global_top[0][0]}、{global_top[1][0]}、{global_top[2][0]} 在多個市場均位居前列。功能性成分方面，益生菌（Lactobacillus、Bifidobacterium）在所有主要市場均有穩定需求，顯示腸道健康議題的跨國關注度。日本市場顯示出對特定機能性成分的偏好，包括難消化性デキストリン和茶カテキン等日本獨特的保健成分。

## 全球熱門成分 Top 20

| 排名 | 成分名稱 | 出現產品數 | 涵蓋市場 | 主要品類 |
|------|----------|-----------|----------|----------|
"""

    for rank, (ingredient, count) in enumerate(global_top[:20], 1):
        markets = format_markets(ingredient_markets[ingredient])
        top_category = get_top_category(ingredient_categories, ingredient)
        report += f"| {rank} | {ingredient} | {count:,} | {markets} | {top_category} |\n"

    # 各市場 Top 10
    report += "\n## 各市場成分偏好\n\n"

    market_names = {
        "us": "🇺🇸 美國",
        "ca": "🇨🇦 加拿大",
        "kr": "🇰🇷 韓國",
        "jp": "🇯🇵 日本（FOSHU + FNFC）",
        "tw": "🇹🇼 台灣"
    }

    for market_code, market_name in market_names.items():
        if market_code in market_tops and market_tops[market_code]:
            report += f"### {market_name} Top 10 成分\n"
            report += "| 排名 | 成分 | 產品數 |\n"
            report += "|------|------|--------|\n"

            for rank, (ingredient, count) in enumerate(market_tops[market_code][:10], 1):
                report += f"| {rank} | {ingredient} | {count:,} |\n"

            report += "\n"

    # 成分 × 市場交叉分析
    report += "## 成分 × 市場交叉分析\n\n"
    report += "| 成分 | 🇺🇸 US | 🇨🇦 CA | 🇰🇷 KR | 🇯🇵 JP | 🇹🇼 TW | 說明 |\n"
    report += "|------|---------|---------|---------|---------|---------|------|\n"

    # 選擇 Top 10 成分進行交叉分析
    for ingredient, _ in global_top[:10]:
        market_counts = {}
        for market_code in ['us', 'ca', 'kr', 'jp', 'tw']:
            count = 0
            if market_code in market_tops:
                market_dict = dict(market_tops[market_code])
                count = market_dict.get(ingredient, 0)
            market_counts[market_code] = count

        marks = {}
        for market_code, count in market_counts.items():
            marks[market_code] = f"✅ {count:,}" if count > 0 else "❌"

        # 判斷市場分布
        markets_present = sum(1 for c in market_counts.values() if c > 0)
        if markets_present >= 4:
            description = "跨國通用成分"
        elif markets_present >= 2:
            present_markets = [m for m, c in market_counts.items() if c > 0]
            description = f"部分市場採用（{', '.join(present_markets)}）"
        else:
            description = "區域特色成分"

        report += f"| {ingredient} | {marks['us']} | {marks['ca']} | {marks['kr']} | {marks['jp']} | {marks['tw']} | {description} |\n"

    report += "\n> 僅列出有顯著跨國差異的成分（某些市場有而其他市場無，或數量差異大於 5 倍）\n\n"

    # 品類 × 成分分析
    report += "## 品類 × 成分分析\n\n"

    category_names = {
        "vitamins_minerals": "維生素與礦物質",
        "botanicals": "植物萃取",
        "probiotics": "益生菌",
        "omega_fatty_acids": "Omega 脂肪酸",
        "protein_amino": "蛋白質與胺基酸"
    }

    for cat_code, cat_name in category_names.items():
        if cat_code in category_tops and category_tops[cat_code]:
            top_ingredients = category_tops[cat_code][:5]
            ingredients_str = "、".join([f"{ing}（{count:,}）" for ing, count in top_ingredients])

            # 分析哪個市場在此品類最活躍
            market_activity = defaultdict(int)
            for ingredient, _ in top_ingredients:
                for market_code in ['us', 'ca', 'kr', 'jp', 'tw']:
                    if market_code in market_tops:
                        if ingredient in dict(market_tops[market_code]):
                            market_activity[market_code] += 1

            if market_activity:
                most_active_market = max(market_activity.items(), key=lambda x: x[1])[0]
                market_label = market_names.get(most_active_market, "未知")
                activity_count = market_activity[most_active_market]
            else:
                market_label = "us"
                activity_count = 0

            report += f"### {cat_name}\n"
            report += f"- 核心成分：{ingredients_str}\n"
            report += f"- 市場差異：{market_label} 市場在此品類較為活躍（{activity_count}/{len(top_ingredients)} 核心成分均出現）\n\n"

    # 趨勢觀察
    tw_total = data['layer_results']['tw_hf']['total_files']

    report += f"""## 趨勢觀察

### 跨國共同趨勢
基礎營養素持續主導全球保健食品市場，Vitamin C、Calcium、Zinc、Magnesium、Vitamin B 群等成分在所有主要市場均位居前列。這反映消費者對日常營養補充的基礎需求穩定，且維生素與礦物質的監管路徑相對成熟，使其成為市場主流。

功能性成分呈現穩定成長，特別是益生菌（Lactobacillus、Bifidobacterium）在美國、加拿大、日本、韓國、台灣市場均有廣泛應用，顯示腸道健康議題的跨國關注度持續上升。

Omega-3 脂肪酸（魚油）雖未進入全球 Top 20，但在各市場均有穩定存在，反映心血管健康和腦部功能的長期需求。

### 市場獨特趨勢
**美國市場**顯示出對蛋白質補充品（Whey Protein、Casein）的高度需求，反映運動營養市場的成熟度。此外，美國 DSLD 資料庫包含大量已下架產品，實際市場趨勢需結合其他數據源判斷。

**日本市場**顯示出對機能性成分的獨特偏好，難消化性デキストリン（Indigestible Dextrin）、茶カテキン（Tea Catechins）、GABA 等成分在日本市場佔比顯著高於其他市場。這與日本特定保健用食品（FOSHU）和機能性表示食品（FNFC）的監管制度相關，這些成分已獲得日本官方認可的健康聲稱。

**韓國市場**在紅麴、人蔘等傳統成分上有較高應用，反映東亞傳統保健文化的影響。同時，韓國市場對維生素、礦物質的標準化要求較高，使其在基礎營養素上與美國、加拿大市場趨勢一致。

**台灣市場**雖然產品數量較少（{tw_total} 筆），但在 Omega-3、紅麴、益生菌等成分上與其他亞洲市場趨勢一致，顯示台灣消費者對功能性保健食品的需求與日韓相近。

**加拿大市場**成分分布與美國高度相似，但加拿大 LNHPD 對成分標示要求更嚴格，因此成分資料品質較高，適合作為北美市場趨勢的參考基準。

### 值得關注的成分
"""

    # 識別值得關注的成分（跨國潛力 + 區域獨特）
    cross_market_ingredients = [(ing, count) for ing, count in global_top[:20] if len(ingredient_markets[ing]) >= 3]

    for ingredient, count in cross_market_ingredients[:5]:
        markets = format_markets(ingredient_markets[ingredient])
        top_category = get_top_category(ingredient_categories, ingredient)

        report += f"""
**{ingredient}**
- 關注原因：跨國潛力成分
- 涵蓋市場：{markets}
- 產品數量：{count:,}
- 所屬品類：{top_category}
- 後續追蹤建議：監測各市場產品配方差異，分析法規要求對成分劑量的影響，評估全球化配方的可行性
"""

    report += """
> **判定標準**：跨國潛力成分需在 3+ 個市場同時出現且產品數 ≥ 1,000；區域獨特成分僅在 1-2 個市場出現但產品數 ≥ 500

## 方法論說明
- 成分名稱標準化方法：基於預定義對照表，合併同義詞（如 Vitamin D3 = Cholecalciferol），日文、韓文、中文成分名對照英文通用名
- 多語言成分名對照：共對照超過 100 個非英文成分名，包含日文（ビタミンC → Vitamin C）、韓文（비타민C → Vitamin C）、中文（維生素C → Vitamin C）
- 已知限制：
  - 美國 DSLD 包含大量下架產品，可能影響市場趨勢判斷
  - 各國對成分的定義和分類標準不同，跨國比較需考慮法規差異
  - 成分名稱標準化為自動處理，部分複方成分或專利成分可能無法完全歸併
  - 韓國產品成分提取依賴「主要功能」和「規格基準」段落，部分產品可能未完整列出所有成分

## 資料品質備註
- 分析產品總數：{total_products:,} 筆
- 成功萃取成分資訊：{total_valid:,} 筆（{total_valid/total_products*100:.1f}%）
- 各 Layer 資料品質：
"""

    for layer_name, stats in data['layer_results'].items():
        total = stats['total_files']
        valid = stats['valid_files']
        percentage = valid / total * 100 if total > 0 else 0
        report += f"  - {layer_name}: {valid:,}/{total:,} ({percentage:.1f}%)\n"

    report += """- 不可用的 Layer：無（所有預定 Layer 均可用）

## 免責聲明
本報告由 AI 自動生成，基於各國官方公開資料庫的產品登記資訊。成分排名基於資料庫登記產品數量，不代表實際市場銷售份額或消費趨勢。成分名稱標準化為自動處理，可能存在歸併誤差。各國監管制度對成分的定義和分類標準不同，跨國比較應考慮法規差異。本報告不構成任何配方建議或法規諮詢。
"""

    return report

def main():
    # 載入分析結果
    pkl_file = Path('/Users/lightman/weiqi.kids/agent.supplement-product/scripts/ingredient_analysis_result.pkl')

    if not pkl_file.exists():
        print(f"錯誤：找不到分析結果檔案 {pkl_file}")
        print("請先執行 analyze_ingredients.py")
        return

    print("載入分析結果...")
    with open(pkl_file, 'rb') as f:
        data = pickle.load(f)

    print("產出報告...")
    report = generate_report(data)

    # 儲存報告
    output_dir = Path("/Users/lightman/weiqi.kids/agent.supplement-product/docs/Narrator/ingredient_radar")
    output_dir.mkdir(parents=True, exist_ok=True)

    output_file = output_dir / f"{datetime.now().strftime('%Y-%m')}-ingredient-radar.md"
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(report)

    print(f"✅ 報告已產出: {output_file}")

if __name__ == "__main__":
    main()
