#!/usr/bin/env python3
"""收集所有 Layer 的成分資料，用於 ingredient_radar 月報"""
import os, re, json
from collections import Counter, defaultdict

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXTRACTOR_DIR = os.path.join(BASE_DIR, "docs/Extractor")

# Ingredient section headers per layer
INGREDIENT_SECTIONS = {
    "us_dsld": "## 成分",
    "ca_lnhpd": "## 成分",
    "kr_hff": "## 主要功能",
    "jp_foshu": "## 機能性成分",
    "jp_fnfc": "## 機能性成分",
}

# Synonym mapping for standardization (from ingredient_radar CLAUDE.md)
SYNONYMS = {
    "vitamin d3": "Vitamin D3", "cholecalciferol": "Vitamin D3", "コレカルシフェロール": "Vitamin D3",
    "dha": "DHA", "docosahexaenoic acid": "DHA",
    "epa": "EPA", "eicosapentaenoic acid": "EPA",
    "ビタミンc": "Vitamin C", "vitamin c": "Vitamin C", "ascorbic acid": "Vitamin C",
    "ビフィズス菌": "Bifidobacterium", "bifidobacterium": "Bifidobacterium",
    "乳酸菌": "Lactobacillus", "lactobacillus": "Lactobacillus",
    "gaba": "GABA", "γ-アミノ酪酸": "GABA",
    "ルテイン": "Lutein", "lutein": "Lutein",
    "難消化性デキストリン": "Indigestible Dextrin", "indigestible dextrin": "Indigestible Dextrin",
    "茶カテキン": "Tea Catechins", "tea catechins": "Tea Catechins",
    "イソフラボン": "Isoflavone", "isoflavone": "Isoflavone",
    "葉酸": "Folate", "folic acid": "Folate", "folate": "Folate",
    "コラーゲン": "Collagen", "collagen": "Collagen",
    "グルコサミン": "Glucosamine", "glucosamine": "Glucosamine",
    "vitamin d": "Vitamin D", "ビタミンd": "Vitamin D",
    "calcium": "Calcium", "カルシウム": "Calcium",
    "iron": "Iron", "鉄": "Iron",
    "zinc": "Zinc", "亜鉛": "Zinc",
    "magnesium": "Magnesium", "マグネシウム": "Magnesium",
    "vitamin a": "Vitamin A", "ビタミンa": "Vitamin A",
    "vitamin e": "Vitamin E", "ビタミンe": "Vitamin E",
    "vitamin b6": "Vitamin B6", "vitamin b12": "Vitamin B12",
    "biotin": "Biotin", "ビオチン": "Biotin",
    "selenium": "Selenium", "セレン": "Selenium",
    "プロバイオティクス": "Probiotics", "probiotic": "Probiotics", "probiotics": "Probiotics",
    "유산균": "Lactobacillus", "프로바이오틱스": "Probiotics",
    "비타민": "Vitamins (General)", "미네랄": "Minerals (General)",
    "홍삼": "Red Ginseng", "인삼": "Ginseng",
    "omega-3": "Omega-3", "오메가": "Omega-3",
    "fish oil": "Fish Oil",
}

def standardize(name):
    """Standardize ingredient name using synonym mapping."""
    key = name.lower().strip()
    return SYNONYMS.get(key, name.strip())

def extract_ingredients_us_dsld(section_text):
    """Parse us_dsld ingredient list: '- Name（Group）'"""
    ingredients = []
    for line in section_text.split("\n"):
        line = line.strip()
        if line.startswith("- "):
            # Extract name before parentheses
            m = re.match(r"-\s+(.+?)(?:（|$)", line)
            if m:
                name = m.group(1).strip()
                if name and name not in ("（無成分資料）",):
                    ingredients.append(standardize(name))
    return ingredients

def extract_ingredients_jp(section_text):
    """Parse Japanese ingredient text (◆-separated or plain text)."""
    ingredients = []
    text = section_text.strip()
    if not text or text == "（無資料）":
        return []
    # Split by ◆ or 、or comma
    parts = re.split(r'[◆、,，\n]', text)
    for part in parts:
        part = part.strip().strip("-").strip()
        if part and len(part) > 1:
            ingredients.append(standardize(part))
    return ingredients

def extract_ingredients_kr(section_text):
    """Parse Korean functional ingredient text."""
    ingredients = []
    text = section_text.strip()
    if not text or text == "（無資料）":
        return []
    # Look for bracketed product types like [프로바이오틱스 제품]
    brackets = re.findall(r'\[([^\]]+)\]', text)
    for b in brackets:
        b = b.replace("제품", "").strip()
        if b:
            ingredients.append(standardize(b))
    # Also look for specific Korean ingredient keywords
    kr_keywords = {
        "유산균": "Lactobacillus", "프로바이오틱스": "Probiotics",
        "비타민": "Vitamins (General)", "홍삼": "Red Ginseng",
        "인삼": "Ginseng", "오메가": "Omega-3", "EPA": "EPA", "DHA": "DHA",
        "칼슘": "Calcium", "철": "Iron", "아연": "Zinc",
        "콜라겐": "Collagen", "루테인": "Lutein",
        "비피더스": "Bifidobacterium", "식이섬유": "Dietary Fiber",
        "밀크씨슬": "Milk Thistle", "쏘팔메토": "Saw Palmetto",
        "코엔자임": "Coenzyme Q10", "글루코사민": "Glucosamine",
        "단백질": "Protein", "아미노산": "Amino Acids",
    }
    for kw, std in kr_keywords.items():
        if kw in text:
            if std not in ingredients:
                ingredients.append(std)
    return ingredients if ingredients else []

def extract_section(content, section_header):
    """Extract content of a markdown section."""
    lines = content.split("\n")
    in_section = False
    section_lines = []
    for line in lines:
        if line.strip() == section_header:
            in_section = True
            continue
        if in_section:
            if line.startswith("## ") and line.strip() != section_header:
                break
            section_lines.append(line)
    return "\n".join(section_lines)

def is_review_needed(content):
    return content.strip().startswith("[REVIEW_NEEDED]")

def get_category_from_path(filepath):
    parts = filepath.split(os.sep)
    for i, p in enumerate(parts):
        if p in ("vitamins_minerals", "botanicals", "protein_amino", "probiotics",
                  "omega_fatty_acids", "specialty", "sports_fitness", "other"):
            return p
    return "unknown"

def process():
    global_counter = Counter()
    market_counters = defaultdict(Counter)  # market -> Counter
    category_ingredients = defaultdict(Counter)  # category -> Counter
    total_products = defaultdict(int)
    review_needed = defaultdict(int)

    for layer, section_header in INGREDIENT_SECTIONS.items():
        layer_dir = os.path.join(EXTRACTOR_DIR, layer)
        if not os.path.exists(layer_dir):
            continue

        market = {"us_dsld": "US", "ca_lnhpd": "CA", "kr_hff": "KR",
                  "jp_foshu": "JP", "jp_fnfc": "JP"}.get(layer, "??")

        for root, dirs, files in os.walk(layer_dir):
            if "raw" in root:
                continue
            for fname in files:
                if not fname.endswith(".md"):
                    continue
                filepath = os.path.join(root, fname)
                try:
                    with open(filepath, "r", encoding="utf-8") as f:
                        content = f.read()
                except:
                    continue

                total_products[layer] += 1

                if is_review_needed(content):
                    review_needed[layer] += 1
                    continue

                category = get_category_from_path(filepath)
                section = extract_section(content, section_header)

                if layer in ("us_dsld", "ca_lnhpd"):
                    ingredients = extract_ingredients_us_dsld(section)
                elif layer in ("jp_foshu", "jp_fnfc"):
                    ingredients = extract_ingredients_jp(section)
                elif layer == "kr_hff":
                    ingredients = extract_ingredients_kr(section)
                else:
                    ingredients = []

                seen = set()
                for ing in ingredients:
                    if ing not in seen:
                        seen.add(ing)
                        global_counter[ing] += 1
                        market_counters[market][ing] += 1
                        category_ingredients[category][ing] += 1

    # Output results
    print("=" * 60)
    print("GLOBAL TOP 30 INGREDIENTS")
    print("=" * 60)
    for rank, (ing, count) in enumerate(global_counter.most_common(30), 1):
        markets = []
        for mkt in ["US", "CA", "KR", "JP"]:
            if market_counters[mkt][ing] > 0:
                markets.append(f"{mkt}({market_counters[mkt][ing]})")
        print(f"{rank:2d}. {ing}: {count} [{', '.join(markets)}]")

    for market in ["US", "CA", "KR", "JP"]:
        print(f"\n{'=' * 60}")
        print(f"{market} TOP 15 INGREDIENTS")
        print(f"{'=' * 60}")
        for rank, (ing, count) in enumerate(market_counters[market].most_common(15), 1):
            print(f"{rank:2d}. {ing}: {count}")

    print(f"\n{'=' * 60}")
    print("CATEGORY BREAKDOWN (top 5 per category)")
    print(f"{'=' * 60}")
    for cat in ["vitamins_minerals", "botanicals", "protein_amino", "probiotics",
                "omega_fatty_acids", "specialty", "sports_fitness", "other"]:
        if category_ingredients[cat]:
            print(f"\n--- {cat} ---")
            for rank, (ing, count) in enumerate(category_ingredients[cat].most_common(5), 1):
                print(f"  {rank}. {ing}: {count}")

    print(f"\n{'=' * 60}")
    print("CROSS-MARKET ANALYSIS (ingredients with significant market differences)")
    print(f"{'=' * 60}")
    for ing, total in global_counter.most_common(50):
        present = {mkt: market_counters[mkt][ing] for mkt in ["US", "CA", "KR", "JP"]}
        markets_with = [m for m, c in present.items() if c > 0]
        markets_without = [m for m, c in present.items() if c == 0]
        if markets_without and total >= 10:
            print(f"  {ing}: total={total} | " + " | ".join(f"{m}={c}" for m, c in present.items()))

    print(f"\n{'=' * 60}")
    print("PRODUCT & REVIEW COUNTS")
    print(f"{'=' * 60}")
    for layer in ["us_dsld", "ca_lnhpd", "kr_hff", "jp_foshu", "jp_fnfc"]:
        print(f"  {layer}: total={total_products.get(layer,0)}, review_needed={review_needed.get(layer,0)}")

    # Also output as JSON for programmatic use
    result = {
        "global_top30": global_counter.most_common(30),
        "market_top15": {m: market_counters[m].most_common(15) for m in ["US", "CA", "KR", "JP"]},
        "category_top5": {c: category_ingredients[c].most_common(5) for c in
                          ["vitamins_minerals", "botanicals", "protein_amino", "probiotics",
                           "omega_fatty_acids", "specialty", "sports_fitness", "other"]},
        "total_products": dict(total_products),
        "review_needed": dict(review_needed),
        "cross_market": {}
    }
    for ing, total in global_counter.most_common(50):
        present = {mkt: market_counters[mkt][ing] for mkt in ["US", "CA", "KR", "JP"]}
        result["cross_market"][ing] = present

    with open(os.path.join(BASE_DIR, "scripts", "ingredient_data.json"), "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"\nJSON output: scripts/ingredient_data.json")

if __name__ == "__main__":
    process()
