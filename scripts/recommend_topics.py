#!/usr/bin/env python3
"""
主題推薦腳本

功能：
1. 讀取 ingredient_radar 報告，取得成分排名
2. 比對上期報告，計算成長趨勢
3. 排除已追蹤主題 (topics/*.yaml)
4. 輸出推薦清單

用法：
  python3 scripts/recommend_topics.py              # 輸出推薦清單
  python3 scripts/recommend_topics.py --json       # JSON 格式輸出
  python3 scripts/recommend_topics.py --top 10     # 顯示前 10 個推薦
"""

import argparse
import json
import re
import yaml
from pathlib import Path
from datetime import datetime
from collections import defaultdict
from typing import Optional


# 路徑配置
PROJECT_ROOT = Path(__file__).parent.parent
TOPICS_DIR = PROJECT_ROOT / "core" / "Narrator" / "Modes" / "topic_tracking" / "topics"
RADAR_DIR = PROJECT_ROOT / "docs" / "Narrator" / "ingredient_radar"

# 已知的多語言成分對照表
INGREDIENT_ALIASES = {
    "vitamin c": ["ascorbic acid", "ビタミンC", "비타민C", "維生素C"],
    "vitamin d": ["vitamin d3", "cholecalciferol", "ビタミンD", "비타민D"],
    "fish oil": ["omega-3", "EPA", "DHA", "魚油", "フィッシュオイル"],
    "probiotics": ["lactobacillus", "bifidobacterium", "乳酸菌", "益生菌"],
    "collagen": ["コラーゲン", "콜라겐", "膠原蛋白"],
    "lutein": ["ルテイン", "루테인", "葉黃素"],
    "gaba": ["γ-aminobutyric acid", "γ-アミノ酪酸"],
    "nmn": ["nicotinamide mononucleotide", "β-NMN", "β-烟酰胺单核苷酸"],
    "coq10": ["coenzyme q10", "ubiquinone", "ユビキノン"],
    "curcumin": ["turmeric", "ウコン", "薑黃"],
}

# 市場旗幟
MARKET_FLAGS = {
    "us_dsld": "🇺🇸",
    "ca_lnhpd": "🇨🇦",
    "kr_hff": "🇰🇷",
    "jp_fnfc": "🇯🇵",
    "jp_foshu": "🇯🇵",
}


def load_existing_topics() -> set:
    """載入現有追蹤主題的關鍵詞"""
    keywords = set()
    for yaml_file in TOPICS_DIR.glob("*.yaml"):
        with open(yaml_file, "r", encoding="utf-8") as f:
            topic = yaml.safe_load(f)
            for kw in topic.get("keywords", {}).get("exact", []):
                keywords.add(kw.lower())
    return keywords


def parse_ingredient_radar(file_path: Path) -> dict:
    """解析 ingredient_radar 報告"""
    content = file_path.read_text(encoding="utf-8")

    result = {
        "period": "",
        "global_top": [],
        "market_top": defaultdict(list),
    }

    # 提取期間
    match = re.search(r"period:\s*[\"']?(\d{4}-\d{2})[\"']?", content)
    if match:
        result["period"] = match.group(1)

    # 提取全球 Top 20
    global_match = re.search(
        r"## 全球熱門成分[^\n]*\n\n\|[^\n]+\n\|[-\s|]+\n([\s\S]*?)(?=\n##|\Z)",
        content
    )
    if global_match:
        table_content = global_match.group(1)
        for line in table_content.strip().split("\n"):
            if line.startswith("|"):
                cols = [c.strip() for c in line.split("|")]
                if len(cols) >= 5:
                    try:
                        rank = int(cols[1])
                        ingredient = cols[2]
                        count = cols[3]
                        markets = cols[4] if len(cols) > 4 else ""
                        result["global_top"].append({
                            "rank": rank,
                            "ingredient": ingredient,
                            "count": count,
                            "markets": markets,
                        })
                    except (ValueError, IndexError):
                        pass

    return result


def get_latest_reports() -> tuple[Optional[dict], Optional[dict]]:
    """取得最新和上一期的報告"""
    reports = sorted(RADAR_DIR.glob("*.md"), reverse=True)

    current = None
    previous = None

    for report_file in reports[:2]:
        parsed = parse_ingredient_radar(report_file)
        if current is None:
            current = parsed
        else:
            previous = parsed

    return current, previous


def calculate_recommendations(
    current: dict,
    previous: Optional[dict],
    existing_keywords: set,
    top_n: int = 5
) -> list[dict]:
    """計算推薦主題"""
    recommendations = []

    # 建立上期排名對照
    prev_ranks = {}
    if previous:
        for item in previous.get("global_top", []):
            prev_ranks[item["ingredient"].lower()] = item["rank"]

    # 分析當前成分
    for item in current.get("global_top", []):
        ingredient = item["ingredient"]
        ingredient_lower = ingredient.lower()

        # 跳過已追蹤的成分
        is_tracked = False
        for kw in existing_keywords:
            if kw in ingredient_lower or ingredient_lower in kw:
                is_tracked = True
                break

            # 檢查別名
            for canonical, aliases in INGREDIENT_ALIASES.items():
                if kw == canonical or kw in [a.lower() for a in aliases]:
                    if ingredient_lower == canonical or ingredient_lower in [a.lower() for a in aliases]:
                        is_tracked = True
                        break

        if is_tracked:
            continue

        # 計算推薦原因
        reasons = []
        rank_change = 0

        # 成長趨勢
        if ingredient_lower in prev_ranks:
            prev_rank = prev_ranks[ingredient_lower]
            rank_change = prev_rank - item["rank"]
            if rank_change >= 5:
                reasons.append(f"成長趨勢 (+{rank_change}位)")

        # 新進榜
        if ingredient_lower not in prev_ranks and previous:
            reasons.append("新進榜")

        # 跨國熱門
        markets = item.get("markets", "")
        market_count = len(re.findall(r"🇺🇸|🇨🇦|🇰🇷|🇯🇵", markets))
        if market_count >= 3:
            reasons.append(f"跨國熱門 ({market_count}市場)")

        if reasons:
            # 產生建議關鍵詞
            suggested_keywords = {
                "exact": [ingredient],
                "fuzzy": [],
            }

            # 加入已知別名
            for canonical, aliases in INGREDIENT_ALIASES.items():
                if ingredient_lower == canonical or ingredient_lower in [a.lower() for a in aliases]:
                    suggested_keywords["exact"].extend([canonical] + aliases)
                    break

            recommendations.append({
                "ingredient": ingredient,
                "rank": item["rank"],
                "reasons": reasons,
                "rank_change": rank_change,
                "markets": markets,
                "suggested_keywords": suggested_keywords,
            })

    # 排序：優先成長趨勢，其次跨國熱門
    recommendations.sort(key=lambda x: (-x["rank_change"], -len(x["reasons"])))

    return recommendations[:top_n]


def main():
    parser = argparse.ArgumentParser(description="主題推薦腳本")
    parser.add_argument("--json", action="store_true", help="JSON 格式輸出")
    parser.add_argument("--top", type=int, default=5, help="顯示前 N 個推薦")
    args = parser.parse_args()

    # 載入現有主題
    existing_keywords = load_existing_topics()

    # 取得報告
    current, previous = get_latest_reports()

    if not current:
        print("❌ 找不到 ingredient_radar 報告")
        return

    # 計算推薦
    recommendations = calculate_recommendations(
        current, previous, existing_keywords, args.top
    )

    if args.json:
        output = {
            "generated_at": datetime.now().isoformat(),
            "current_period": current.get("period", ""),
            "previous_period": previous.get("period", "") if previous else None,
            "recommendations": recommendations,
        }
        print(json.dumps(output, ensure_ascii=False, indent=2))
    else:
        print("=" * 60)
        print("📊 推薦新增追蹤主題")
        print("=" * 60)
        print(f"分析期間: {current.get('period', 'N/A')}")
        print(f"已追蹤主題關鍵詞: {len(existing_keywords)} 個")
        print()

        if not recommendations:
            print("✅ 目前沒有新的推薦主題")
            return

        print(f"| {'排名':^4} | {'成分':^20} | {'推薦原因':^25} | {'涵蓋市場':^12} |")
        print("|" + "-" * 6 + "|" + "-" * 22 + "|" + "-" * 27 + "|" + "-" * 14 + "|")

        for rec in recommendations:
            reasons_str = ", ".join(rec["reasons"])
            print(f"| {rec['rank']:^4} | {rec['ingredient']:<20} | {reasons_str:<25} | {rec['markets']:<12} |")

        print()
        print("建議關鍵詞:")
        for rec in recommendations:
            print(f"  {rec['ingredient']}:")
            print(f"    exact: {rec['suggested_keywords']['exact']}")

        print()
        print("使用以下指令新增追蹤:")
        for rec in recommendations:
            topic_id = rec["ingredient"].lower().replace(" ", "-")
            print(f"  python3 scripts/create_topic.py --name \"{rec['ingredient']}\" --id {topic_id}")


if __name__ == "__main__":
    main()
