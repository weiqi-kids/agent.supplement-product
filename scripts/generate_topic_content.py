#!/usr/bin/env python3
"""
AI 產生主題首頁和選購指南

結合產品資料與網路搜尋，用 AI 自動產生 index.md 和 guide.md 的內容。

用法：
  python3 scripts/generate_topic_content.py --topic exosomes
  python3 scripts/generate_topic_content.py --all
  python3 scripts/generate_topic_content.py --topic fish-oil --skip-web

流程：
1. 讀取 topics/{topic_id}.yaml 取得主題定義
2. 掃描產品資料，篩選匹配的產品
3. 彙整產品的 health_claim, ingredients, form 等欄位
4. 執行網路搜尋（可選）
5. 整合所有資料，呼叫 Claude API 產生內容
6. 寫入 docs/reports/{topic_id}/index.md 和 guide.md
"""

import argparse
import json
import os
import re
import yaml
from pathlib import Path
from datetime import datetime
from collections import defaultdict
from typing import Optional

try:
    import anthropic
    HAS_ANTHROPIC = True
except ImportError:
    HAS_ANTHROPIC = False

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False


# 路徑配置
PROJECT_ROOT = Path(__file__).parent.parent
TOPICS_DIR = PROJECT_ROOT / "core" / "Narrator" / "Modes" / "topic_tracking" / "topics"
EXTRACTOR_DIR = PROJECT_ROOT / "docs" / "Extractor"
REPORTS_DIR = PROJECT_ROOT / "docs" / "reports"

# Layer 對應市場
LAYER_MARKET = {
    "us_dsld": {"name": "美國", "flag": "🇺🇸", "code": "US"},
    "ca_lnhpd": {"name": "加拿大", "flag": "🇨🇦", "code": "CA"},
    "kr_hff": {"name": "韓國", "flag": "🇰🇷", "code": "KR"},
    "jp_fnfc": {"name": "日本 FNFC", "flag": "🇯🇵", "code": "JP"},
    "jp_foshu": {"name": "日本 FOSHU", "flag": "🇯🇵", "code": "JP"},
    "tw_hf": {"name": "台灣", "flag": "🇹🇼", "code": "TW"},
}

# 網路搜尋查詢模板
SEARCH_QUERIES = {
    "science": [
        "{topic_en} mechanism of action",
        "{topic_en} clinical study benefits",
        "{topic_en} research 2024 2025",
    ],
    "safety": [
        "{topic_zh} 副作用 注意事項",
        "{topic_en} side effects contraindications",
    ],
    "consumer": [
        "{topic_zh} 推薦 評價",
        "{topic_zh} PTT 心得",
        "{topic_en} review comparison",
    ],
    "market": [
        "{topic_en} market size trend",
        "{topic_zh} 市場規模 趨勢",
    ],
}


def load_topic(topic_id: str) -> Optional[dict]:
    """載入主題定義"""
    yaml_path = TOPICS_DIR / f"{topic_id}.yaml"
    if not yaml_path.exists():
        return None
    with open(yaml_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_all_topics() -> list[dict]:
    """載入所有主題定義"""
    topics = []
    for yaml_file in TOPICS_DIR.glob("*.yaml"):
        with open(yaml_file, "r", encoding="utf-8") as f:
            topic = yaml.safe_load(f)
            topics.append(topic)
    return topics


def parse_product_file(file_path: Path) -> Optional[dict]:
    """解析產品 Markdown 檔案"""
    content = file_path.read_text(encoding="utf-8")

    # 跳過 REVIEW_NEEDED 產品
    if "[REVIEW_NEEDED]" in content:
        return None

    product = {
        "file_path": str(file_path),
        "name": "",
        "brand": "",
        "manufacturer": "",
        "ingredients": [],
        "health_claim": "",
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
                    product["health_claim"] = fm.get("health_claim", "")
            except yaml.YAMLError:
                pass

    # 提取成分
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
            for line in ingredients_text.split("\n"):
                line = line.strip()
                if line.startswith("- "):
                    product["ingredients"].append(line[2:].strip())
                elif line and not line.startswith("#"):
                    product["ingredients"].append(line)

    # 提取健康聲明（如果 frontmatter 沒有）
    if not product["health_claim"]:
        claim_patterns = [
            r"## 健康聲明\s*\n([\s\S]*?)(?=\n##|\Z)",
            r"## Health Claim\s*\n([\s\S]*?)(?=\n##|\Z)",
            r"## 届出表示\s*\n([\s\S]*?)(?=\n##|\Z)",
        ]
        for pattern in claim_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                product["health_claim"] = match.group(1).strip()[:500]
                break

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

    # 模糊匹配產品名稱和健康聲明
    search_text = " ".join([
        product.get("name", ""),
        product.get("health_claim", ""),
    ]).lower()

    for keyword in exact_keywords + fuzzy_keywords:
        if keyword in search_text:
            return True

    return False


def scan_products(topic: dict, sample_limit: int = 0) -> list[dict]:
    """掃描並篩選符合主題的產品

    Args:
        topic: 主題定義
        sample_limit: 取樣上限，0 表示不限制
    """
    matched_products = []
    category_filter = topic.get("category_filter", [])
    scanned = 0

    print("  ", end="", flush=True)

    for layer_dir in EXTRACTOR_DIR.iterdir():
        if not layer_dir.is_dir():
            continue
        if layer_dir.name not in LAYER_MARKET:
            continue

        for category_dir in layer_dir.iterdir():
            if not category_dir.is_dir():
                continue
            if category_dir.name == "raw":
                continue
            if category_filter and category_dir.name not in category_filter:
                continue

            for product_file in category_dir.glob("*.md"):
                scanned += 1
                if scanned % 10000 == 0:
                    print(".", end="", flush=True)

                product = parse_product_file(product_file)
                if product and match_product(product, topic):
                    matched_products.append(product)

                    # 取樣限制
                    if sample_limit > 0 and len(matched_products) >= sample_limit:
                        print(f" (取樣 {sample_limit} 筆)")
                        return matched_products

    print(f" (掃描 {scanned} 筆)")
    return matched_products


def summarize_products(products: list[dict]) -> dict:
    """彙整產品資料統計"""
    summary = {
        "count": len(products),
        "markets": defaultdict(int),
        "forms": defaultdict(int),
        "brands": defaultdict(int),
        "health_claims": [],
        "ingredients": defaultdict(int),
    }

    for product in products:
        # 市場統計
        layer = product.get("layer", "")
        if layer in LAYER_MARKET:
            summary["markets"][LAYER_MARKET[layer]["name"]] += 1

        # 劑型統計
        form = product.get("form") or "未知"
        summary["forms"][form] += 1

        # 品牌統計
        brand = product.get("brand") or product.get("manufacturer") or "未知"
        summary["brands"][brand] += 1

        # 健康聲明收集
        claim = product.get("health_claim", "")
        if claim and len(claim) > 10:
            summary["health_claims"].append(claim[:200])

        # 成分統計
        for ingredient in product.get("ingredients", []):
            summary["ingredients"][ingredient.lower()[:50]] += 1

    # 轉換為排序列表
    summary["markets"] = dict(sorted(summary["markets"].items(), key=lambda x: -x[1]))
    summary["forms"] = dict(sorted(summary["forms"].items(), key=lambda x: -x[1])[:10])
    summary["brands"] = dict(sorted(summary["brands"].items(), key=lambda x: -x[1])[:20])
    summary["ingredients"] = dict(sorted(summary["ingredients"].items(), key=lambda x: -x[1])[:30])

    # 取代表性健康聲明
    summary["health_claims"] = summary["health_claims"][:10]

    return summary


def format_product_summary(summary: dict, topic: dict) -> str:
    """格式化產品摘要供 AI 使用"""
    output = f"""## 產品資料摘要（來自官方資料庫）

- **產品數量**：{summary['count']} 筆
- **涵蓋市場**：{', '.join([f"{k}({v}筆)" for k, v in list(summary['markets'].items())[:5]])}

### 常見劑型
{chr(10).join([f"- {k}: {v} 筆" for k, v in list(summary['forms'].items())[:5]])}

### 常見品牌/製造商
{chr(10).join([f"- {k}: {v} 筆" for k, v in list(summary['brands'].items())[:10] if k != '未知'])}

### 常見成分
{chr(10).join([f"- {k}: {v} 次" for k, v in list(summary['ingredients'].items())[:15]])}

### 代表性健康聲明
"""
    for i, claim in enumerate(summary["health_claims"][:5], 1):
        output += f"{i}. {claim}\n"

    return output


def generate_search_queries(topic: dict) -> dict[str, list[str]]:
    """產生網路搜尋查詢"""
    topic_zh = topic["name"].get("zh", "")
    topic_en = topic["name"].get("en", "")

    queries = {}
    for category, templates in SEARCH_QUERIES.items():
        queries[category] = [
            t.format(topic_zh=topic_zh, topic_en=topic_en)
            for t in templates
        ]

    return queries


def format_web_results_placeholder(topic: dict) -> str:
    """產生網路搜尋結果的佔位符（提示需要手動搜尋）"""
    queries = generate_search_queries(topic)

    output = """## 網路搜尋結果

> 以下為建議搜尋的查詢，請使用 WebSearch 工具執行搜尋後補充：

### 科學研究
"""
    for q in queries["science"]:
        output += f"- [ ] `{q}`\n"

    output += "\n### 安全資訊\n"
    for q in queries["safety"]:
        output += f"- [ ] `{q}`\n"

    output += "\n### 消費者評價\n"
    for q in queries["consumer"]:
        output += f"- [ ] `{q}`\n"

    output += "\n### 市場趨勢\n"
    for q in queries["market"]:
        output += f"- [ ] `{q}`\n"

    return output


def generate_index_prompt(topic: dict, product_summary: str, web_results: str) -> str:
    """產生 index.md 的 AI prompt"""
    topic_name = topic["name"]["zh"]

    return f"""你是保健食品專家。根據以下 {topic_name} 相關資料，
撰寫一份客觀中立的主題介紹頁面。

{product_summary}

{web_results}

## 輸出格式

請使用繁體中文，依照以下結構撰寫。每個段落 150-300 字，盡量引用具體數據：

```markdown
# {topic_name}

## 要解決什麼問題？

（結合健康聲明分析消費者的主要需求，說明這類產品主要針對什麼問題）

## 造成問題的原因

（說明為什麼會有這些健康問題，可能的成因）

## 市面解決方案分析

（客觀比較市面上不同類型的產品，包括劑型、劑量、品牌特點）

## 作用機轉

（說明主要成分如何發揮作用的科學原理）

## 發展歷史與現況

（根據產品統計數據，分析市場發展趨勢）

## 參考文獻

（列出資料來源）
```

注意：
1. 保持客觀中立，不做療效宣稱
2. 引用具體的產品統計數據
3. 標註資訊來源
4. 若資料不足，請標註「待補充」
"""


def generate_guide_prompt(topic: dict, product_summary: str, web_results: str) -> str:
    """產生 guide.md 的 AI prompt"""
    topic_name = topic["name"]["zh"]

    return f"""你是保健食品選購顧問。根據以下 {topic_name} 相關資料，
撰寫一份實用的選購指南。

{product_summary}

{web_results}

## 輸出格式

請使用繁體中文，依照以下結構撰寫：

```markdown
# {topic_name}選購指南

## 決策樹

（用文字描述選購決策流程，幫助消費者根據自身需求選擇合適的產品）

## 選購要點

### 劑量建議
（根據產品資料統計，說明常見劑量範圍）

### 劑型比較
（比較不同劑型的優缺點：膠囊、錠劑、液態等）

### 認證標準
（說明各國的認證標準和意義）

### 價格帶參考
（若有資料，提供價格參考）

## 常見問題 FAQ

Q1: （根據消費者可能的疑問，提供 5-10 個常見問題與解答）
A1:

Q2:
A2:

...
```

注意：
1. 提供實用的選購建議
2. 保持客觀，不推薦特定品牌
3. 若資料不足，請標註「待補充」
"""


def call_claude_api(prompt: str, max_tokens: int = 4000) -> Optional[str]:
    """呼叫 Claude API 產生內容"""
    if not HAS_ANTHROPIC:
        print("⚠️  anthropic 套件未安裝，無法呼叫 API")
        return None

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("⚠️  ANTHROPIC_API_KEY 未設定")
        return None

    try:
        client = anthropic.Anthropic(api_key=api_key)
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=max_tokens,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        return message.content[0].text
    except Exception as e:
        print(f"❌ API 呼叫失敗: {e}")
        return None


def generate_content(topic: dict, skip_web: bool = False, dry_run: bool = False, sample_limit: int = 0) -> dict:
    """產生主題內容

    Args:
        topic: 主題定義
        skip_web: 是否跳過網路搜尋
        dry_run: 是否為 dry run 模式
        sample_limit: 取樣上限，0 表示不限制
    """
    topic_id = topic["topic_id"]
    topic_name = topic["name"]["zh"]

    print(f"\n📝 處理主題: {topic_name} ({topic_id})")

    # 掃描產品
    print("  📂 掃描產品資料...")
    products = scan_products(topic, sample_limit=sample_limit)
    print(f"  ✅ 找到 {len(products)} 筆匹配產品")

    if len(products) == 0:
        print("  ⚠️  沒有找到匹配的產品，跳過")
        return {"success": False, "reason": "no_products"}

    # 彙整統計
    summary = summarize_products(products)
    product_summary = format_product_summary(summary, topic)

    # 網路搜尋結果
    if skip_web:
        web_results = "\n## 網路搜尋結果\n\n（已跳過網路搜尋）\n"
    else:
        web_results = format_web_results_placeholder(topic)

    # Dry run 模式
    if dry_run:
        print("\n" + "=" * 50)
        print("DRY RUN - 產品摘要")
        print("=" * 50)
        print(product_summary)
        print("\n" + "=" * 50)
        print("DRY RUN - 建議搜尋查詢")
        print("=" * 50)
        print(web_results)
        return {"success": True, "dry_run": True}

    # 產生 prompts
    index_prompt = generate_index_prompt(topic, product_summary, web_results)
    guide_prompt = generate_guide_prompt(topic, product_summary, web_results)

    # 確保輸出目錄存在
    output_dir = REPORTS_DIR / topic_id
    output_dir.mkdir(parents=True, exist_ok=True)

    results = {"success": True, "files": []}

    # 產生 index.md
    print("  🤖 產生 index.md...")
    index_content = call_claude_api(index_prompt)
    if index_content:
        # 加入 frontmatter
        frontmatter = f"""---
layout: default
title: {topic_name}
nav_order: 10
parent: 報告總覽
has_children: true
generated_at: "{datetime.now().isoformat()}"
product_count: {summary['count']}
---

"""
        index_path = output_dir / "index.md"
        index_path.write_text(frontmatter + index_content, encoding="utf-8")
        print(f"  ✅ 已寫入: {index_path.relative_to(PROJECT_ROOT)}")
        results["files"].append(str(index_path))
    else:
        print("  ⚠️  index.md 產生失敗")

    # 產生 guide.md
    print("  🤖 產生 guide.md...")
    guide_content = call_claude_api(guide_prompt)
    if guide_content:
        # 加入 frontmatter
        frontmatter = f"""---
layout: default
title: 選購指南
nav_order: 2
parent: {topic_name}
grand_parent: 報告總覽
generated_at: "{datetime.now().isoformat()}"
---

"""
        guide_path = output_dir / "guide.md"
        guide_path.write_text(frontmatter + guide_content, encoding="utf-8")
        print(f"  ✅ 已寫入: {guide_path.relative_to(PROJECT_ROOT)}")
        results["files"].append(str(guide_path))
    else:
        print("  ⚠️  guide.md 產生失敗")

    return results


def main():
    parser = argparse.ArgumentParser(description="AI 產生主題首頁和選購指南")
    parser.add_argument("--topic", help="指定主題 ID")
    parser.add_argument("--all", action="store_true", help="處理所有主題")
    parser.add_argument("--skip-web", action="store_true", help="跳過網路搜尋")
    parser.add_argument("--dry-run", action="store_true", help="僅顯示會產生的內容，不實際執行")
    parser.add_argument("--sample", type=int, default=0, help="取樣上限（用於快速測試）")
    args = parser.parse_args()

    print("=" * 50)
    print("主題內容產生")
    print("=" * 50)

    if not HAS_ANTHROPIC and not args.dry_run:
        print("⚠️  需要安裝 anthropic 套件: pip install anthropic")
        print("   或使用 --dry-run 模式查看資料摘要")

    # 載入主題
    if args.topic:
        topic = load_topic(args.topic)
        if not topic:
            print(f"❌ 找不到主題: {args.topic}")
            return
        topics = [topic]
    elif args.all:
        topics = load_all_topics()
    else:
        parser.print_help()
        return

    print(f"📋 載入 {len(topics)} 個主題")
    if args.sample > 0:
        print(f"📊 取樣模式：每主題最多 {args.sample} 筆產品")

    for topic in topics:
        generate_content(
            topic,
            skip_web=args.skip_web,
            dry_run=args.dry_run,
            sample_limit=args.sample
        )

    print("\n" + "=" * 50)
    print("✅ 完成")
    print("=" * 50)


if __name__ == "__main__":
    main()
