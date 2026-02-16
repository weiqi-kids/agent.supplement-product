#!/usr/bin/env python3
"""成分標準化擷取腳本 — 從產品萃取成分並透過 RxNorm API 標準化"""
import json
import os
import re
import sys
import argparse
import time
from datetime import datetime
from collections import Counter
from pathlib import Path

try:
    import requests
except ImportError:
    print("請安裝 requests: pip3 install requests", file=sys.stderr)
    sys.exit(1)

BASE_DIR = Path(__file__).parent.parent
EXTRACTOR_DIR = BASE_DIR / "docs" / "Extractor"
RAW_DIR = EXTRACTOR_DIR / "ingredient_map" / "raw"

# RxNorm API
RXNORM_BASE = "https://rxnav.nlm.nih.gov/REST"
RATE_LIMIT = 0.1  # 10 requests/second

# 產品 Layer 清單
PRODUCT_LAYERS = ["us_dsld", "ca_lnhpd", "kr_hff", "jp_fnfc", "jp_foshu", "tw_hf"]


def extract_ingredients_from_file(filepath: Path) -> list:
    """從產品 .md 檔案萃取成分"""
    ingredients = []

    try:
        content = filepath.read_text(encoding="utf-8")
    except Exception:
        return []

    # 跳過 REVIEW_NEEDED 檔案
    if "[REVIEW_NEEDED]" in content[:500]:
        return []

    # 找到成分區塊
    in_ingredients = False
    for line in content.split("\n"):
        line = line.strip()

        # 成分區塊開始
        if line.startswith("## 成分") or line.startswith("## 機能性成分"):
            in_ingredients = True
            continue

        # 其他區塊開始，結束成分擷取
        if line.startswith("## ") and in_ingredients:
            break

        # 擷取成分項目
        if in_ingredients and line.startswith("- "):
            # 清理成分名稱
            ingredient = line[2:].strip()

            # 移除括號內容和劑量
            ingredient = re.sub(r"\s*[\(（].*?[\)）]", "", ingredient)
            ingredient = re.sub(r"\s*—.*$", "", ingredient)
            ingredient = re.sub(r"\s*-\s*\d+.*$", "", ingredient)
            ingredient = re.sub(r"\s+\d+\s*(mg|mcg|iu|g|ml).*$", "", ingredient, flags=re.IGNORECASE)

            ingredient = ingredient.strip()

            if ingredient and len(ingredient) > 1:
                ingredients.append(ingredient)

    return ingredients


def extract_all_ingredients() -> Counter:
    """從所有產品萃取成分頻率"""
    print("📊 萃取所有產品成分...")

    ingredient_counter = Counter()
    file_count = 0

    for layer in PRODUCT_LAYERS:
        layer_dir = EXTRACTOR_DIR / layer
        if not layer_dir.exists():
            continue

        print(f"  處理 {layer}...")

        # 遍歷所有子目錄（category）
        for category_dir in layer_dir.iterdir():
            if not category_dir.is_dir() or category_dir.name == "raw":
                continue

            for md_file in category_dir.glob("*.md"):
                ingredients = extract_ingredients_from_file(md_file)
                ingredient_counter.update(ingredients)
                file_count += 1

    print(f"  掃描 {file_count} 個產品檔案")
    print(f"  發現 {len(ingredient_counter)} 個獨特成分")

    return ingredient_counter


def query_rxnorm(term: str) -> dict:
    """查詢 RxNorm API"""
    result = {
        "term": term,
        "rxnorm_id": None,
        "standard_name": None,
        "match_type": None,
        "confidence": "low"
    }

    # 精確查詢
    try:
        url = f"{RXNORM_BASE}/rxcui.json"
        params = {"name": term, "search": 1}
        resp = requests.get(url, params=params, timeout=10)

        if resp.status_code == 200:
            data = resp.json()
            id_group = data.get("idGroup", {})
            rxnorm_ids = id_group.get("rxnormId", [])

            if rxnorm_ids:
                result["rxnorm_id"] = rxnorm_ids[0]
                result["match_type"] = "exact"
                result["confidence"] = "high"

                # 取得標準名稱
                prop_url = f"{RXNORM_BASE}/rxcui/{rxnorm_ids[0]}/properties.json"
                prop_resp = requests.get(prop_url, timeout=10)
                if prop_resp.status_code == 200:
                    props = prop_resp.json().get("properties", {})
                    result["standard_name"] = props.get("name", term)

                return result
    except Exception:
        pass

    # 模糊查詢
    try:
        url = f"{RXNORM_BASE}/approximateTerm.json"
        params = {"term": term, "maxEntries": 3}
        resp = requests.get(url, params=params, timeout=10)

        if resp.status_code == 200:
            data = resp.json()
            candidates = data.get("approximateGroup", {}).get("candidate", [])

            if candidates:
                best = candidates[0]
                result["rxnorm_id"] = best.get("rxcui")
                result["standard_name"] = best.get("name", term)
                result["match_type"] = "approximate"

                # 根據分數設定信心度
                score = int(best.get("score", 0))
                if score >= 90:
                    result["confidence"] = "high"
                elif score >= 70:
                    result["confidence"] = "medium"
                else:
                    result["confidence"] = "low"

                return result
    except Exception:
        pass

    return result


def normalize_ingredients(ingredients: Counter, top_n: int = 500) -> list:
    """標準化成分"""
    print(f"🔄 標準化前 {top_n} 名成分...")

    # 取前 N 名
    top_ingredients = ingredients.most_common(top_n)

    results = []

    for i, (ingredient, count) in enumerate(top_ingredients, 1):
        print(f"  [{i}/{len(top_ingredients)}] {ingredient} ({count})")

        rxnorm_result = query_rxnorm(ingredient)
        rxnorm_result["frequency"] = count
        rxnorm_result["queried_at"] = datetime.now().isoformat()

        results.append(rxnorm_result)

        # 速率限制
        time.sleep(RATE_LIMIT)

    return results


def save_results(frequency: Counter, normalized: list):
    """儲存結果"""
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    today = datetime.now().strftime("%Y-%m-%d")

    # 儲存頻率統計
    freq_file = RAW_DIR / f"ingredient_frequency_{today}.json"
    freq_data = [{"ingredient": ing, "count": cnt} for ing, cnt in frequency.most_common()]
    with open(freq_file, "w", encoding="utf-8") as f:
        json.dump(freq_data, f, ensure_ascii=False, indent=2)
    print(f"  📁 頻率統計 → {freq_file}")

    # 儲存標準化結果
    if normalized:
        norm_file = RAW_DIR / f"normalized_{today}.jsonl"
        with open(norm_file, "w", encoding="utf-8") as f:
            for item in normalized:
                f.write(json.dumps(item, ensure_ascii=False) + "\n")
        print(f"  📁 標準化結果 → {norm_file}")

        # 統計
        high_conf = sum(1 for x in normalized if x["confidence"] == "high")
        med_conf = sum(1 for x in normalized if x["confidence"] == "medium")
        low_conf = sum(1 for x in normalized if x["confidence"] == "low")
        matched = sum(1 for x in normalized if x["rxnorm_id"])

        print(f"\n📈 標準化統計:")
        print(f"   匹配成功：{matched}/{len(normalized)} ({100*matched/len(normalized):.1f}%)")
        print(f"   高信心度：{high_conf}")
        print(f"   中信心度：{med_conf}")
        print(f"   低信心度：{low_conf}")


def show_stats():
    """顯示統計資訊"""
    print("📊 成分統計資訊")
    print("━━━━━━━━━━━━━━━━━━━━━━━━")

    # 找最新的頻率檔案
    freq_files = list(RAW_DIR.glob("ingredient_frequency_*.json"))
    if not freq_files:
        print("  尚無統計資料，請先執行 --extract-all")
        return

    latest = max(freq_files, key=lambda x: x.stat().st_mtime)

    with open(latest, "r", encoding="utf-8") as f:
        data = json.load(f)

    print(f"  檔案：{latest.name}")
    print(f"  獨特成分：{len(data)}")
    print(f"\n  前 20 名成分：")

    for i, item in enumerate(data[:20], 1):
        print(f"    {i:2}. {item['ingredient']}: {item['count']}")


def main():
    parser = argparse.ArgumentParser(description="成分標準化擷取")
    parser.add_argument("--extract-all", action="store_true", help="萃取所有產品成分")
    parser.add_argument("--normalize", action="store_true", help="標準化成分（需先 --extract-all）")
    parser.add_argument("--top", type=int, default=500, help="標準化前 N 名成分")
    parser.add_argument("--full", action="store_true", help="完整流程（萃取 + 標準化）")
    parser.add_argument("--stats", action="store_true", help="顯示統計資訊")
    args = parser.parse_args()

    if args.stats:
        show_stats()
        return

    if args.full or args.extract_all:
        frequency = extract_all_ingredients()

        if args.full or args.normalize:
            normalized = normalize_ingredients(frequency, args.top)
            save_results(frequency, normalized)
        else:
            save_results(frequency, [])
        return

    if args.normalize:
        # 從現有檔案載入頻率
        freq_files = list(RAW_DIR.glob("ingredient_frequency_*.json"))
        if not freq_files:
            print("請先執行 --extract-all", file=sys.stderr)
            sys.exit(1)

        latest = max(freq_files, key=lambda x: x.stat().st_mtime)
        with open(latest, "r", encoding="utf-8") as f:
            data = json.load(f)

        frequency = Counter({item["ingredient"]: item["count"] for item in data})
        normalized = normalize_ingredients(frequency, args.top)
        save_results(frequency, normalized)
        return

    parser.print_help()


if __name__ == "__main__":
    main()
