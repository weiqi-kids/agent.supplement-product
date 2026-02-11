#!/usr/bin/env python3
"""
轉換 Narrator 報告為 Jekyll 格式

將 docs/Narrator/ 下的報告轉換為 Jekyll 格式，
加入適當的 frontmatter 並輸出到 docs/reports/ 目錄。
"""

import os
import re
import yaml
import shutil
from pathlib import Path
from datetime import datetime


# 路徑配置
PROJECT_ROOT = Path(__file__).parent.parent
NARRATOR_DIR = PROJECT_ROOT / "docs" / "Narrator"
REPORTS_DIR = PROJECT_ROOT / "docs" / "reports"


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

    period = frontmatter.get("period", "")

    # 從檔名或 frontmatter 取得期間
    if not period:
        match = re.search(r"(\d{4}-W\d{2})", source_path.name)
        if match:
            period = match.group(1)

    # 建立新的 frontmatter
    new_frontmatter = {
        "layout": "default",
        "title": f"市場快照 {period}",
        "parent": "市場快照",
        "grand_parent": "報告總覽",
        "nav_order": get_nav_order_from_period(period),
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

    dest_file.write_text(output, encoding="utf-8")
    print(f"✅ {source_path.name} → {dest_file.relative_to(PROJECT_ROOT)}")


def convert_ingredient_radar(source_path: Path, dest_dir: Path):
    """轉換成分雷達報告"""
    content = source_path.read_text(encoding="utf-8")
    frontmatter, body = parse_frontmatter(content)

    period = frontmatter.get("period", "")

    # 從檔名或 frontmatter 取得期間
    if not period:
        match = re.search(r"(\d{4}-\d{2})", source_path.name)
        if match:
            period = match.group(1)

    # 建立新的 frontmatter
    new_frontmatter = {
        "layout": "default",
        "title": f"成分雷達 {period}",
        "parent": "成分雷達",
        "grand_parent": "報告總覽",
        "nav_order": get_nav_order_from_period(period),
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

    period = frontmatter.get("period", "")

    # 從檔名取得期間
    if not period:
        match = re.search(r"(\d{4}-\d{2})", source_path.name)
        if match:
            period = match.group(1)

    topic_name = get_topic_name(topic_id)

    # 建立新的 frontmatter
    new_frontmatter = {
        "layout": "default",
        "title": f"{topic_name} {period}",
        "parent": "市場報告",
        "grand_parent": topic_name,
        "nav_order": get_nav_order_from_period(period),
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

    dest_file.write_text(output, encoding="utf-8")
    print(f"✅ {source_path.name} → {dest_file.relative_to(PROJECT_ROOT)}")


def convert_literature_review(source_path: Path, topic_id: str, dest_dir: Path):
    """轉換文獻薈萃報告"""
    content = source_path.read_text(encoding="utf-8")
    frontmatter, body = parse_frontmatter(content)

    period = frontmatter.get("period", "")

    # 從檔名取得期間
    if not period:
        match = re.search(r"(\d{4}-\d{2})", source_path.name)
        if match:
            period = match.group(1)

    topic_name = get_topic_name(topic_id)

    # 建立新的 frontmatter
    new_frontmatter = {
        "layout": "default",
        "title": f"{topic_name}文獻薈萃 {period}",
        "parent": "文獻薈萃",
        "grand_parent": topic_name,
        "nav_order": get_nav_order_from_period(period),
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

    dest_file.write_text(output, encoding="utf-8")
    print(f"✅ {source_path.name} → {dest_file.relative_to(PROJECT_ROOT)}")


def main():
    print("=" * 50)
    print("Jekyll 報告轉換")
    print("=" * 50)

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
