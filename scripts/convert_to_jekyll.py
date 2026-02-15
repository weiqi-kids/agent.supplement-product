#!/usr/bin/env python3
"""
轉換 Narrator 報告為 Jekyll 格式

將 docs/Narrator/ 下的報告轉換為 Jekyll 格式，
加入適當的 frontmatter、JSON-LD Schema 並輸出到 docs/reports/ 目錄。

SEO 功能：
- 自動注入 JSON-LD Schema（WebPage, Article, BreadcrumbList 等）
- 加入 YMYL 免責聲明
- 計算字數和閱讀時間
"""

import os
import re
import json
import yaml
from pathlib import Path
from datetime import datetime


# 路徑配置
PROJECT_ROOT = Path(__file__).parent.parent
NARRATOR_DIR = PROJECT_ROOT / "docs" / "Narrator"
REPORTS_DIR = PROJECT_ROOT / "docs" / "reports"
SEO_CONFIG_PATH = PROJECT_ROOT / "seo" / "config.yaml"

# 全域 SEO 設定快取
_seo_config = None


def load_seo_config() -> dict:
    """載入 SEO 全域設定"""
    global _seo_config
    if _seo_config is None:
        if SEO_CONFIG_PATH.exists():
            with open(SEO_CONFIG_PATH, "r", encoding="utf-8") as f:
                _seo_config = yaml.safe_load(f)
        else:
            _seo_config = {}
    return _seo_config


def count_words(text: str) -> int:
    """計算中英文混合文字的字數"""
    # 移除 Markdown 標記
    text = re.sub(r"[#*_`\[\]()>-]", "", text)
    # 移除 URL
    text = re.sub(r"https?://\S+", "", text)
    # 計算中文字符
    chinese_chars = len(re.findall(r"[\u4e00-\u9fff]", text))
    # 計算英文單詞
    english_words = len(re.findall(r"[a-zA-Z]+", text))
    return chinese_chars + english_words


def estimate_reading_time(word_count: int) -> str:
    """估算閱讀時間（假設每分鐘 300 字）"""
    minutes = max(1, round(word_count / 300))
    return f"{minutes} 分鐘"


def generate_json_ld(
    page_type: str,
    title: str,
    description: str,
    canonical_url: str,
    date_published: str,
    date_modified: str,
    breadcrumb_items: list,
    word_count: int = 0,
    keywords: str = "",
    article_section: str = "",
) -> dict:
    """產生 JSON-LD Schema"""
    config = load_seo_config()
    site_url = config.get("site", {}).get("url", "https://supplement.weiqi.kids")

    graph = []

    # 1. WebPage Schema
    webpage = {
        "@type": "WebPage",
        "@id": f"{canonical_url}#webpage",
        "url": canonical_url,
        "name": title,
        "description": description[:155] if description else "",
        "inLanguage": "zh-TW",
        "isPartOf": {"@id": f"{site_url}#website"},
        "datePublished": date_published,
        "dateModified": date_modified,
        "speakable": {
            "@type": "SpeakableSpecification",
            "cssSelector": config.get("speakable", {}).get(
                "cssSelector",
                [".article-summary", ".key-takeaway", ".key-answer"],
            ),
        },
    }
    graph.append(webpage)

    # 2. Organization Schema
    org_config = config.get("organization", {})
    organization = {
        "@type": "Organization",
        "@id": f"{site_url}#organization",
        "name": org_config.get("name", "保健食品情報系統"),
        "alternateName": org_config.get("alternateName", "Supplement Intelligence"),
        "url": site_url,
        "logo": {
            "@type": "ImageObject",
            "url": f"{site_url}/assets/images/logo.png",
            "width": 600,
            "height": 60,
        },
        "sameAs": org_config.get("sameAs", []),
    }
    if org_config.get("contactPoint"):
        organization["contactPoint"] = org_config["contactPoint"]
    graph.append(organization)

    # 3. WebSite Schema (with SearchAction)
    website = {
        "@type": "WebSite",
        "@id": f"{site_url}#website",
        "name": config.get("site", {}).get("name", "保健食品情報系統"),
        "url": site_url,
        "potentialAction": {
            "@type": "SearchAction",
            "target": f"{site_url}/search?q={{search_term}}",
            "query-input": "required name=search_term",
        },
    }
    graph.append(website)

    # 4. Article Schema (for report pages)
    if page_type in ["report", "literature", "topic_index"]:
        ai_author = config.get("ai_author", {})
        article = {
            "@type": "Article",
            "@id": f"{canonical_url}#article",
            "mainEntityOfPage": {"@id": f"{canonical_url}#webpage"},
            "headline": title,
            "description": description[:155] if description else "",
            "author": {
                "@type": "Person",
                "@id": f"{site_url}/about#person",
                "name": ai_author.get("name", "保健食品情報 AI"),
                "url": f"{site_url}/about",
                "knowsAbout": ai_author.get(
                    "knowsAbout", ["保健食品市場分析", "成分趨勢研究"]
                ),
                "hasCredential": ai_author.get("hasCredential", []),
            },
            "publisher": {"@id": f"{site_url}#organization"},
            "datePublished": date_published,
            "dateModified": date_modified,
            "articleSection": article_section or "市場報告",
            "inLanguage": "zh-TW",
            "isAccessibleForFree": True,
            "isPartOf": {"@id": f"{site_url}#website"},
        }
        if word_count > 0:
            article["wordCount"] = word_count
        if keywords:
            article["keywords"] = keywords
        graph.append(article)

    # 5. BreadcrumbList Schema
    if breadcrumb_items:
        breadcrumb = {
            "@type": "BreadcrumbList",
            "itemListElement": [
                {
                    "@type": "ListItem",
                    "position": i + 1,
                    "name": item["name"],
                    "item": item["url"],
                }
                for i, item in enumerate(breadcrumb_items)
            ],
        }
        graph.append(breadcrumb)

    # 6. ImageObject Schema
    image_config = config.get("default_image", {})
    image = {
        "@type": "ImageObject",
        "@id": f"{canonical_url}#primaryimage",
        "url": f"{site_url}/assets/images/og-default.png",
        "width": 1200,
        "height": 630,
        "representativeOfPage": True,
        "license": image_config.get(
            "license", "https://creativecommons.org/licenses/by-nc/4.0/"
        ),
        "creditText": image_config.get("creditText", "保健食品情報系統"),
    }
    graph.append(image)

    return {"@context": "https://schema.org", "@graph": graph}


def get_ymyl_disclaimer() -> str:
    """取得 YMYL 免責聲明"""
    config = load_seo_config()
    ymyl = config.get("ymyl", {})
    medical = ymyl.get(
        "medical_disclaimer",
        "本網站內容由 AI 自動生成，僅供參考，不構成醫療建議。",
    )
    data = ymyl.get("data_disclaimer", "")

    disclaimer = "\n\n---\n\n"
    disclaimer += '<div class="disclaimer" markdown="1">\n\n'
    disclaimer += "**免責聲明**\n\n"
    disclaimer += medical.strip() + "\n\n"
    if data:
        disclaimer += data.strip() + "\n\n"
    disclaimer += "</div>\n"
    return disclaimer


def parse_frontmatter(content: str) -> tuple[dict, str]:
    """解析 YAML frontmatter"""
    if not content.startswith("---"):
        return {}, content

    parts = content.split("---", 2)
    if len(parts) < 3:
        return {}, content

    try:
        frontmatter = yaml.safe_load(parts[1])
        body = parts[2].lstrip("\n")
        return frontmatter or {}, body
    except yaml.YAMLError:
        return {}, content


def get_nav_order_from_period(period: str) -> int:
    """從期間字串計算 nav_order（數字越大越新）"""
    # 週報: 2026-W06 -> 202606
    # 月報: 2026-02 -> 202602
    if "-W" in period:
        # 週報
        year, week = period.split("-W")
        return int(year) * 100 + int(week)
    elif re.match(r"\d{4}-\d{2}", period):
        # 月報
        year, month = period.split("-")
        return int(year) * 100 + int(month)
    else:
        return 0


def convert_market_snapshot(source_path: Path, dest_dir: Path):
    """轉換市場快照報告"""
    content = source_path.read_text(encoding="utf-8")
    frontmatter, body = parse_frontmatter(content)
    config = load_seo_config()
    site_url = config.get("site", {}).get("url", "https://supplement.weiqi.kids")

    period = frontmatter.get("period", "")

    # 從檔名或 frontmatter 取得期間
    if not period:
        match = re.search(r"(\d{4}-W\d{2})", source_path.name)
        if match:
            period = match.group(1)

    title = f"市場快照 {period}"
    description = f"全球保健食品市場快照週報 {period}，涵蓋美國、加拿大、韓國、日本、台灣六大市場產品數據分析。"
    canonical_url = f"{site_url}/reports/market-snapshot/{period}"
    date_str = frontmatter.get("generated_at", datetime.now().isoformat())[:10]

    # 計算字數
    word_count = count_words(body)

    # 產生 JSON-LD
    breadcrumb = [
        {"name": "首頁", "url": site_url},
        {"name": "市場快照", "url": f"{site_url}/reports/market-snapshot"},
        {"name": title, "url": canonical_url},
    ]
    json_ld = generate_json_ld(
        page_type="report",
        title=title,
        description=description,
        canonical_url=canonical_url,
        date_published=date_str,
        date_modified=date_str,
        breadcrumb_items=breadcrumb,
        word_count=word_count,
        keywords="市場快照,保健食品,膳食補充劑,全球市場",
        article_section="市場快照",
    )

    # 建立新的 frontmatter
    new_frontmatter = {
        "layout": "default",
        "title": title,
        "description": description,
        "parent": "市場快照",
        "grand_parent": "報告總覽",
        "nav_order": get_nav_order_from_period(period),
        "json_ld": json_ld,
    }

    # 保留原始的 metadata
    if "generated_at" in frontmatter:
        new_frontmatter["generated_at"] = frontmatter["generated_at"]
    if "source_layers" in frontmatter:
        new_frontmatter["source_layers"] = frontmatter["source_layers"]

    # 輸出檔案
    dest_file = dest_dir / f"{period}.md"
    dest_file.parent.mkdir(parents=True, exist_ok=True)

    output = "---\n"
    output += yaml.dump(new_frontmatter, allow_unicode=True, default_flow_style=False)
    output += "---\n\n"
    output += body
    output += get_ymyl_disclaimer()

    dest_file.write_text(output, encoding="utf-8")
    print(f"✅ {source_path.name} → {dest_file.relative_to(PROJECT_ROOT)}")


def convert_ingredient_radar(source_path: Path, dest_dir: Path):
    """轉換成分雷達報告"""
    content = source_path.read_text(encoding="utf-8")
    frontmatter, body = parse_frontmatter(content)
    config = load_seo_config()
    site_url = config.get("site", {}).get("url", "https://supplement.weiqi.kids")

    period = frontmatter.get("period", "")

    # 從檔名或 frontmatter 取得期間
    if not period:
        match = re.search(r"(\d{4}-\d{2})", source_path.name)
        if match:
            period = match.group(1)

    title = f"成分雷達 {period}"
    description = f"全球保健食品成分趨勢分析月報 {period}，追蹤熱門成分、品類分布與市場動態。"
    canonical_url = f"{site_url}/reports/ingredient-radar/{period}"
    date_str = frontmatter.get("generated_at", datetime.now().isoformat())[:10]

    # 計算字數
    word_count = count_words(body)

    # 產生 JSON-LD
    breadcrumb = [
        {"name": "首頁", "url": site_url},
        {"name": "成分雷達", "url": f"{site_url}/reports/ingredient-radar"},
        {"name": title, "url": canonical_url},
    ]
    json_ld = generate_json_ld(
        page_type="report",
        title=title,
        description=description,
        canonical_url=canonical_url,
        date_published=date_str,
        date_modified=date_str,
        breadcrumb_items=breadcrumb,
        word_count=word_count,
        keywords="成分雷達,保健食品成分,市場趨勢,成分分析",
        article_section="成分雷達",
    )

    # 建立新的 frontmatter
    new_frontmatter = {
        "layout": "default",
        "title": title,
        "description": description,
        "parent": "成分雷達",
        "grand_parent": "報告總覽",
        "nav_order": get_nav_order_from_period(period),
        "json_ld": json_ld,
    }

    # 保留原始的 metadata
    if "generated_at" in frontmatter:
        new_frontmatter["generated_at"] = frontmatter["generated_at"]
    if "source_layers" in frontmatter:
        new_frontmatter["source_layers"] = frontmatter["source_layers"]

    # 輸出檔案
    dest_file = dest_dir / f"{period}.md"
    dest_file.parent.mkdir(parents=True, exist_ok=True)

    output = "---\n"
    output += yaml.dump(new_frontmatter, allow_unicode=True, default_flow_style=False)
    output += "---\n\n"
    output += body
    output += get_ymyl_disclaimer()

    dest_file.write_text(output, encoding="utf-8")
    print(f"✅ {source_path.name} → {dest_file.relative_to(PROJECT_ROOT)}")


def get_topic_name(topic_id: str) -> str:
    """從 YAML 取得主題名稱"""
    topics_dir = PROJECT_ROOT / "core" / "Narrator" / "Modes" / "topic_tracking" / "topics"
    yaml_file = topics_dir / f"{topic_id}.yaml"
    if yaml_file.exists():
        with open(yaml_file, "r", encoding="utf-8") as f:
            topic = yaml.safe_load(f)
            return topic.get("name", {}).get("zh", topic_id)
    return topic_id


def convert_topic_report(source_path: Path, topic_id: str, dest_dir: Path):
    """轉換主題追蹤報告"""
    content = source_path.read_text(encoding="utf-8")
    frontmatter, body = parse_frontmatter(content)
    config = load_seo_config()
    site_url = config.get("site", {}).get("url", "https://supplement.weiqi.kids")

    period = frontmatter.get("period", "")

    # 從檔名取得期間
    if not period:
        match = re.search(r"(\d{4}-\d{2})", source_path.name)
        if match:
            period = match.group(1)

    topic_name = get_topic_name(topic_id)
    title = f"{topic_name}市場報告 {period}"
    description = f"{topic_name}保健食品市場追蹤報告 {period}，涵蓋產品數據、品牌分析與市場趨勢。"
    canonical_url = f"{site_url}/reports/{topic_id}/reports/{period}"
    date_str = frontmatter.get("generated_at", datetime.now().isoformat())[:10]

    # 計算字數
    word_count = count_words(body)

    # 產生 JSON-LD
    breadcrumb = [
        {"name": "首頁", "url": site_url},
        {"name": topic_name, "url": f"{site_url}/reports/{topic_id}"},
        {"name": "市場報告", "url": f"{site_url}/reports/{topic_id}/reports"},
        {"name": period, "url": canonical_url},
    ]
    json_ld = generate_json_ld(
        page_type="report",
        title=title,
        description=description,
        canonical_url=canonical_url,
        date_published=date_str,
        date_modified=date_str,
        breadcrumb_items=breadcrumb,
        word_count=word_count,
        keywords=f"{topic_name},市場報告,保健食品,產品分析",
        article_section="主題報告",
    )

    # 建立新的 frontmatter
    new_frontmatter = {
        "layout": "default",
        "title": f"{topic_name} {period}",
        "description": description,
        "parent": "市場報告",
        "grand_parent": topic_name,
        "nav_order": get_nav_order_from_period(period),
        "json_ld": json_ld,
    }

    # 保留原始的 metadata
    if "generated_at" in frontmatter:
        new_frontmatter["generated_at"] = frontmatter["generated_at"]
    if "topic" in frontmatter:
        new_frontmatter["topic"] = frontmatter["topic"]

    # 輸出檔案
    dest_file = dest_dir / f"{period}.md"
    dest_file.parent.mkdir(parents=True, exist_ok=True)

    output = "---\n"
    output += yaml.dump(new_frontmatter, allow_unicode=True, default_flow_style=False)
    output += "---\n\n"
    output += body
    output += get_ymyl_disclaimer()

    dest_file.write_text(output, encoding="utf-8")
    print(f"✅ {source_path.name} → {dest_file.relative_to(PROJECT_ROOT)}")


def convert_literature_review(source_path: Path, topic_id: str, dest_dir: Path):
    """轉換文獻薈萃報告"""
    content = source_path.read_text(encoding="utf-8")
    frontmatter, body = parse_frontmatter(content)
    config = load_seo_config()
    site_url = config.get("site", {}).get("url", "https://supplement.weiqi.kids")

    period = frontmatter.get("period", "")

    # 從檔名取得期間
    if not period:
        match = re.search(r"(\d{4}-\d{2})", source_path.name)
        if match:
            period = match.group(1)

    topic_name = get_topic_name(topic_id)
    title = f"{topic_name}文獻薈萃 {period}"
    description = f"{topic_name}相關學術文獻彙整 {period}，整理最新研究成果與證據等級分析。"
    canonical_url = f"{site_url}/reports/{topic_id}/literature/{period}"
    date_str = frontmatter.get("generated_at", datetime.now().isoformat())[:10]

    # 計算字數
    word_count = count_words(body)

    # 產生 JSON-LD
    breadcrumb = [
        {"name": "首頁", "url": site_url},
        {"name": topic_name, "url": f"{site_url}/reports/{topic_id}"},
        {"name": "文獻薈萃", "url": f"{site_url}/reports/{topic_id}/literature"},
        {"name": period, "url": canonical_url},
    ]
    json_ld = generate_json_ld(
        page_type="literature",
        title=title,
        description=description,
        canonical_url=canonical_url,
        date_published=date_str,
        date_modified=date_str,
        breadcrumb_items=breadcrumb,
        word_count=word_count,
        keywords=f"{topic_name},文獻回顧,學術研究,證據分析",
        article_section="文獻薈萃",
    )

    # 建立新的 frontmatter
    new_frontmatter = {
        "layout": "default",
        "title": title,
        "description": description,
        "parent": "文獻薈萃",
        "grand_parent": topic_name,
        "nav_order": get_nav_order_from_period(period),
        "json_ld": json_ld,
    }

    # 保留原始的 metadata
    if "generated_at" in frontmatter:
        new_frontmatter["generated_at"] = frontmatter["generated_at"]
    if "topic" in frontmatter:
        new_frontmatter["topic"] = frontmatter["topic"]
    if "total_articles" in frontmatter:
        new_frontmatter["total_articles"] = frontmatter["total_articles"]

    # 輸出檔案
    dest_file = dest_dir / f"{period}.md"
    dest_file.parent.mkdir(parents=True, exist_ok=True)

    output = "---\n"
    output += yaml.dump(new_frontmatter, allow_unicode=True, default_flow_style=False)
    output += "---\n\n"
    output += body
    output += get_ymyl_disclaimer()

    dest_file.write_text(output, encoding="utf-8")
    print(f"✅ {source_path.name} → {dest_file.relative_to(PROJECT_ROOT)}")


def main():
    print("=" * 50)
    print("Jekyll 報告轉換（含 SEO Schema 注入）")
    print("=" * 50)

    # 載入 SEO 設定
    config = load_seo_config()
    if config:
        print(f"✅ 載入 SEO 設定：{SEO_CONFIG_PATH.relative_to(PROJECT_ROOT)}")
    else:
        print("⚠️ SEO 設定檔不存在，使用預設值")

    # 確保目標目錄存在
    (REPORTS_DIR / "market-snapshot").mkdir(parents=True, exist_ok=True)
    (REPORTS_DIR / "ingredient-radar").mkdir(parents=True, exist_ok=True)

    converted = 0

    # 轉換市場快照
    market_dir = NARRATOR_DIR / "market_snapshot"
    if market_dir.exists():
        for f in market_dir.glob("*.md"):
            if f.name.startswith("."):
                continue
            convert_market_snapshot(f, REPORTS_DIR / "market-snapshot")
            converted += 1

    # 轉換成分雷達
    radar_dir = NARRATOR_DIR / "ingredient_radar"
    if radar_dir.exists():
        for f in radar_dir.glob("*.md"):
            if f.name.startswith("."):
                continue
            convert_ingredient_radar(f, REPORTS_DIR / "ingredient-radar")
            converted += 1

    # 轉換主題追蹤報告
    topic_tracking_dir = NARRATOR_DIR / "topic_tracking"
    if topic_tracking_dir.exists():
        for topic_dir in topic_tracking_dir.iterdir():
            if not topic_dir.is_dir():
                continue
            topic_id = topic_dir.name

            # 確保目標目錄存在
            dest_reports_dir = REPORTS_DIR / topic_id / "reports"
            dest_reports_dir.mkdir(parents=True, exist_ok=True)

            for f in topic_dir.glob("*.md"):
                if f.name.startswith("."):
                    continue
                convert_topic_report(f, topic_id, dest_reports_dir)
                converted += 1

    # 轉換文獻薈萃報告
    literature_review_dir = NARRATOR_DIR / "literature_review"
    if literature_review_dir.exists():
        for topic_dir in literature_review_dir.iterdir():
            if not topic_dir.is_dir():
                continue
            topic_id = topic_dir.name

            # 確保目標目錄存在
            dest_lit_dir = REPORTS_DIR / topic_id / "literature"
            dest_lit_dir.mkdir(parents=True, exist_ok=True)

            for f in topic_dir.glob("*.md"):
                if f.name.startswith("."):
                    continue
                convert_literature_review(f, topic_id, dest_lit_dir)
                converted += 1

    print("=" * 50)
    print(f"✅ 轉換完成：{converted} 份報告")
    print("=" * 50)


if __name__ == "__main__":
    main()
