#!/usr/bin/env python3
"""
Ingredient Radar Analysis Script
Analyzes ingredients across all layers for monthly ingredient radar report
"""

import os
import re
from pathlib import Path
from collections import defaultdict, Counter
from datetime import datetime
import yaml

# Ingredient normalization mapping
INGREDIENT_MAPPING = {
    # Vitamin D
    "vitamin d3": "Vitamin D3",
    "cholecalciferol": "Vitamin D3",
    "コレカルシフェロール": "Vitamin D3",
    "vitamin d": "Vitamin D",

    # Omega fatty acids
    "dha": "DHA",
    "docosahexaenoic acid": "DHA",
    "epa": "EPA",
    "eicosapentaenoic acid": "EPA",

    # Vitamin C
    "vitamin c": "Vitamin C",
    "ビタミンc": "Vitamin C",
    "ascorbic acid": "Vitamin C",

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
    "glucosamine": "Glucosamine",
    "グルコサミン": "Glucosamine",
    "calcium": "Calcium",
    "カルシウム": "Calcium",
    "vitamin e": "Vitamin E",
    "ビタミンe": "Vitamin E",
    "vitamin b12": "Vitamin B12",
    "ビタミンb12": "Vitamin B12",
    "vitamin b6": "Vitamin B6",
    "ビタミンb6": "Vitamin B6",
    "iron": "Iron",
    "鉄": "Iron",
    "zinc": "Zinc",
    "亜鉛": "Zinc",
    "magnesium": "Magnesium",
    "マグネシウム": "Magnesium",
    "coenzyme q10": "Coenzyme Q10",
    "コエンザイムq10": "Coenzyme Q10",
    "coq10": "Coenzyme Q10",

    # Korean ingredients
    "비타민c": "Vitamin C",
    "비타민d": "Vitamin D",
    "비타민e": "Vitamin E",
    "비타민b1": "Vitamin B1",
    "비타민b2": "Vitamin B2",
    "비타민b6": "Vitamin B6",
    "비타민b12": "Vitamin B12",
    "비타민a": "Vitamin A",
    "비타민k": "Vitamin K",
    "판토텐산": "Pantothenic Acid",
    "나이아신": "Niacin",
    "엽산": "Folate",
    "비오틴": "Biotin",
    "유산균": "Lactobacillus",
    "홍삼": "Red Ginseng",
    "오메가3": "Omega-3",
    "omega-3": "Omega-3",
    "프로바이오틱스": "Probiotics",
    "실리마린": "Silymarin",
    "아연": "Zinc",
    "칼슘": "Calcium",
    "마그네슘": "Magnesium",
    "철": "Iron",
    "셀레늄": "Selenium",
    "망간": "Manganese",
    "요오드": "Iodine",
    "구리": "Copper",
    "크롬": "Chromium",
}

def normalize_ingredient(ingredient_raw):
    """Normalize ingredient name"""
    # Remove dosage information (numbers, units)
    ingredient = re.sub(r'\d+\.?\d*\s*(mg|g|kg|mcg|ug|μg|iu|ml|l).*', '', ingredient_raw, flags=re.IGNORECASE)
    # Remove parenthetical form information
    ingredient = re.sub(r'\s*\([^)]*form[^)]*\)', '', ingredient, flags=re.IGNORECASE)
    # Clean up
    ingredient = ingredient.strip().strip('()（）').strip()

    # Normalize to lowercase for lookup
    ingredient_lower = ingredient.lower()

    # Check mapping
    if ingredient_lower in INGREDIENT_MAPPING:
        return INGREDIENT_MAPPING[ingredient_lower]

    # Check if any key is contained in the ingredient
    for key, value in INGREDIENT_MAPPING.items():
        if key in ingredient_lower:
            return value

    # Return title-cased original if no mapping found
    return ingredient.title() if ingredient else None

def extract_ingredients_from_file(filepath):
    """Extract ingredients from a markdown file"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        # Check for REVIEW_NEEDED
        if '[REVIEW_NEEDED]' in content:
            return None, None, None

        # Extract frontmatter
        match = re.match(r'^---\n(.*?)\n---', content, re.DOTALL)
        if not match:
            return None, None, None

        frontmatter = yaml.safe_load(match.group(1))
        category = frontmatter.get('category', 'other')
        market = frontmatter.get('market', 'unknown')

        # Extract ingredients section
        ingredients = []

        # For us_dsld and ca_lnhpd: look for "## 成分"
        if '## 成分' in content:
            section_match = re.search(r'## 成分\n(.*?)(?=\n##|\Z)', content, re.DOTALL)
            if section_match:
                section = section_match.group(1)
                # Extract ingredient lines (starting with -)
                for line in section.split('\n'):
                    line = line.strip()
                    if line.startswith('-'):
                        # Extract ingredient name (before （ or — symbol)
                        ingredient_match = re.match(r'-\s*([^(（—]+)', line)
                        if ingredient_match:
                            ingredient_raw = ingredient_match.group(1).strip()
                            # Skip placeholder text
                            if ingredient_raw in ['成分資料需額外擷取', '']:
                                continue
                            if '參見' in ingredient_raw or 'API' in ingredient_raw:
                                continue
                            # Skip nutritional values that aren't real supplements
                            skip_items = ['calories', 'calories from fat', 'total fat', 'total carbohydrates',
                                        'sodium', 'potassium', 'protein', 'dietary fiber', 'sugars', 'cholesterol']
                            if ingredient_raw.lower() in skip_items:
                                continue
                            ingredients.append(ingredient_raw)

        # For jp_foshu, jp_fnfc: look for "## 機能性成分"
        if '## 機能性成分' in content:
            section_match = re.search(r'## 機能性成分\n(.*?)(?=\n##|\Z)', content, re.DOTALL)
            if section_match:
                section = section_match.group(1).strip()
                # For single ingredient
                if section and not section.startswith('-'):
                    ingredients.append(section)
                # For multiple ingredients (list)
                else:
                    for line in section.split('\n'):
                        line = line.strip()
                        if line.startswith('-'):
                            ingredient = line.lstrip('-').strip()
                            if ingredient:
                                ingredients.append(ingredient)

        # For kr_hff: extract from "## 主要功能" (Main Function) section
        # Korean products list ingredients in square brackets like [비타민E], [유산균]
        if market == 'kr' and '## 主要功能' in content:
            section_match = re.search(r'## 主要功能\n(.*?)(?=\n##|\Z)', content, re.DOTALL)
            if section_match:
                section = section_match.group(1)
                # Extract ingredients in square brackets
                kr_ingredients = re.findall(r'\[([^\]]+)\]', section)
                for ing in kr_ingredients:
                    ing = ing.strip()
                    if ing:
                        ingredients.append(ing)

        # Also extract from "## 規格基準" (Specification Standard) for Korean products
        if market == 'kr' and '## 規格基準' in content:
            section_match = re.search(r'## 規格基準\n(.*?)(?=\n##|\Z)', content, re.DOTALL)
            if section_match:
                section = section_match.group(1)
                # Extract ingredients from lines like "② 비타민B1 : 표시량의..."
                spec_ingredients = re.findall(r'[①②③④⑤⑥⑦⑧⑨⑩]\s*([^:：\s]+)\s*[:：]', section)
                for ing in spec_ingredients:
                    ing = ing.strip()
                    # Skip non-ingredient items
                    if ing not in ['성상', '헥산', '납', '카드뮴', '수은', '비소', '대장균군', '붕해', '붕해시험',
                                   '세균수', '대장균', '황색포도상구균', '살모넬라', '아플라톡신']:
                        if ing not in ingredients:  # Avoid duplicates
                            ingredients.append(ing)

        return ingredients, category, market

    except Exception as e:
        print(f"Error processing {filepath}: {e}")
        return None, None, None

def analyze_layer(layer_path, layer_name):
    """Analyze all files in a layer"""
    ingredients_counter = Counter()
    ingredient_products = defaultdict(set)  # ingredient -> set of product files
    ingredient_markets = defaultdict(set)   # ingredient -> set of markets
    ingredient_categories = defaultdict(Counter)  # ingredient -> category counter

    total_files = 0
    valid_files = 0
    review_needed_files = 0

    # Process all markdown files in the layer
    for md_file in Path(layer_path).rglob('*.md'):
        if md_file.parent.name == 'raw':
            continue

        total_files += 1

        ingredients, category, market = extract_ingredients_from_file(md_file)

        if ingredients is None:
            review_needed_files += 1
            continue

        if not ingredients:
            continue

        valid_files += 1

        # Process each ingredient
        for ing_raw in ingredients:
            ing_normalized = normalize_ingredient(ing_raw)
            if ing_normalized:
                ingredients_counter[ing_normalized] += 1
                ingredient_products[ing_normalized].add(str(md_file))
                ingredient_markets[ing_normalized].add(market)
                ingredient_categories[ing_normalized][category] += 1

    return {
        'layer': layer_name,
        'total_files': total_files,
        'valid_files': valid_files,
        'review_needed_files': review_needed_files,
        'ingredients': ingredients_counter,
        'ingredient_products': ingredient_products,
        'ingredient_markets': ingredient_markets,
        'ingredient_categories': ingredient_categories,
    }

def main():
    base_path = Path('/Users/lightman/weiqi.kids/agent.supplement-product/docs/Extractor')
    layers = ['us_dsld', 'ca_lnhpd', 'kr_hff', 'jp_foshu', 'jp_fnfc']

    print("Starting ingredient analysis...")
    print("=" * 80)

    # Analyze each layer
    layer_results = {}
    for layer in layers:
        layer_path = base_path / layer
        if not layer_path.exists():
            print(f"Warning: {layer} not found")
            continue

        print(f"\nAnalyzing {layer}...")
        result = analyze_layer(layer_path, layer)
        layer_results[layer] = result
        print(f"  Total files: {result['total_files']}")
        print(f"  Valid files: {result['valid_files']}")
        print(f"  Unique ingredients: {len(result['ingredients'])}")

    print("\n" + "=" * 80)
    print("Aggregating results...")

    # Aggregate across all layers
    global_ingredients = Counter()
    global_ingredient_markets = defaultdict(set)
    global_ingredient_categories = defaultdict(Counter)
    global_ingredient_products = defaultdict(set)

    for layer_name, result in layer_results.items():
        for ing, count in result['ingredients'].items():
            global_ingredients[ing] += count
            global_ingredient_markets[ing].update(result['ingredient_markets'][ing])
            for cat, cat_count in result['ingredient_categories'][ing].items():
                global_ingredient_categories[ing][cat] += cat_count
            global_ingredient_products[ing].update(result['ingredient_products'][ing])

    # Generate report data
    report_data = {
        'timestamp': datetime.utcnow().isoformat() + 'Z',
        'layer_results': layer_results,
        'global_top_20': global_ingredients.most_common(20),
        'global_ingredients': global_ingredients,
        'global_ingredient_markets': global_ingredient_markets,
        'global_ingredient_categories': global_ingredient_categories,
        'global_ingredient_products': global_ingredient_products,
    }

    # Save to file for report generation
    import pickle
    output_file = '/Users/lightman/weiqi.kids/agent.supplement-product/scripts/ingredient_analysis_result.pkl'
    with open(output_file, 'wb') as f:
        pickle.dump(report_data, f)

    print(f"\nAnalysis complete. Results saved to {output_file}")
    print("\nGlobal Top 20 Ingredients:")
    for i, (ing, count) in enumerate(report_data['global_top_20'], 1):
        markets = sorted(global_ingredient_markets[ing])
        print(f"{i:2d}. {ing:30s} - {count:6d} products - Markets: {', '.join(markets)}")

if __name__ == '__main__':
    main()
