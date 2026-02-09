#!/usr/bin/env python3
"""
建立新追蹤主題腳本

功能：
1. 建立 topics/{topic_id}.yaml
2. 建立 docs/reports/{topic_id}/ 目錄結構
3. 產生初始 index.md 和 guide.md（佔位內容）
4. 可選：立即執行首次報告產出

用法：
  python3 scripts/create_topic.py --name "NMN" --id nmn
  python3 scripts/create_topic.py --interactive
  python3 scripts/create_topic.py --from-recommendation nmn
"""

import argparse
import subprocess
import yaml
from pathlib import Path
from datetime import datetime


# 路徑配置
PROJECT_ROOT = Path(__file__).parent.parent
TOPICS_DIR = PROJECT_ROOT / "core" / "Narrator" / "Modes" / "topic_tracking" / "topics"
REPORTS_DIR = PROJECT_ROOT / "docs" / "reports"


def slugify(name: str) -> str:
    """將名稱轉換為 URL-friendly 格式"""
    return name.lower().replace(" ", "-").replace("_", "-")


def create_topic_yaml(topic_id: str, name: str, keywords: list[str]) -> Path:
    """建立主題 YAML 定義檔"""
    yaml_content = {
        "topic_id": topic_id,
        "name": {
            "zh": name,
            "en": name,
            "ja": name,
            "ko": name,
        },
        "keywords": {
            "exact": keywords,
            "fuzzy": [],
        },
        "category_filter": [],  # 空 = 搜尋全部分類
        "output": {
            "index": f"docs/reports/{topic_id}/index.md",
            "guide": f"docs/reports/{topic_id}/guide.md",
            "reports": f"docs/reports/{topic_id}/reports/",
        },
    }

    yaml_path = TOPICS_DIR / f"{topic_id}.yaml"

    # 加入註解
    header = f"""# {name} 主題追蹤定義
# 建立時間: {datetime.now().isoformat()}
# 可手動編輯 keywords 和 category_filter 以調整篩選範圍

"""

    with open(yaml_path, "w", encoding="utf-8") as f:
        f.write(header)
        yaml.dump(yaml_content, f, allow_unicode=True, default_flow_style=False, sort_keys=False)

    return yaml_path


def create_index_md(topic_id: str, name: str) -> Path:
    """建立主題首頁"""
    topic_dir = REPORTS_DIR / topic_id
    topic_dir.mkdir(parents=True, exist_ok=True)

    index_path = topic_dir / "index.md"

    content = f"""---
layout: default
title: {name}
nav_order: 10
parent: 報告總覽
has_children: true
---

# {name}

{{: .note }}
本主題追蹤頁面由系統自動建立，內容將在首次報告產出後更新。

## 要解決什麼問題？

（待產出報告後自動分析填入）

## 造成問題的原因

（待產出報告後自動分析填入）

## 市面解決方案分析

（待產出報告後自動分析填入）

## 作用機轉

（待產出報告後自動分析填入）

## 發展歷史與現況

（待產出報告後自動分析填入）

## 參考文獻

（待補充）
"""

    index_path.write_text(content, encoding="utf-8")
    return index_path


def create_guide_md(topic_id: str, name: str) -> Path:
    """建立選購指南"""
    topic_dir = REPORTS_DIR / topic_id

    guide_path = topic_dir / "guide.md"

    content = f"""---
layout: default
title: 選購指南
nav_order: 2
parent: {name}
grand_parent: 報告總覽
---

# {name}選購指南

{{: .note }}
本頁面將在首次報告產出後自動更新。

## 決策樹

（待產出報告後自動分析填入）

## 選購要點

（待產出報告後自動分析填入）

## 常見問題 FAQ

（待補充）
"""

    guide_path.write_text(content, encoding="utf-8")
    return guide_path


def create_reports_dir(topic_id: str) -> Path:
    """建立報告目錄"""
    reports_path = REPORTS_DIR / topic_id / "reports"
    reports_path.mkdir(parents=True, exist_ok=True)

    # 建立 index.md 作為報告列表頁
    index_content = f"""---
layout: default
title: 市場報告
nav_order: 3
parent: {topic_id}
grand_parent: 報告總覽
has_children: true
---

# 市場報告

歷史市場報告列表。

{{% assign reports = site.pages | where_exp: "page", "page.path contains 'reports/{topic_id}/reports/2'" | sort: "nav_order" | reverse %}}
{{% for report in reports %}}
- [{{{{ report.title }}}}]({{{{ report.url | relative_url }}}})
{{% endfor %}}
"""

    (reports_path / "index.md").write_text(index_content, encoding="utf-8")

    return reports_path


def interactive_mode():
    """互動模式建立主題"""
    print("=" * 50)
    print("📝 建立新追蹤主題（互動模式）")
    print("=" * 50)

    name = input("主題名稱 (如: NMN, 葉黃素): ").strip()
    if not name:
        print("❌ 名稱不可為空")
        return

    topic_id = input(f"主題 ID [{slugify(name)}]: ").strip()
    if not topic_id:
        topic_id = slugify(name)

    keywords_input = input("關鍵詞 (逗號分隔): ").strip()
    keywords = [k.strip() for k in keywords_input.split(",") if k.strip()]
    if not keywords:
        keywords = [name]

    print()
    print(f"主題名稱: {name}")
    print(f"主題 ID: {topic_id}")
    print(f"關鍵詞: {keywords}")
    print()

    confirm = input("確認建立？ [Y/n]: ").strip().lower()
    if confirm and confirm != "y":
        print("❌ 已取消")
        return

    return create_topic(topic_id, name, keywords)


def create_topic(topic_id: str, name: str, keywords: list[str], run_report: bool = True):
    """建立主題的完整流程"""
    print(f"\n📂 建立主題: {name} ({topic_id})")

    # 檢查是否已存在
    yaml_path = TOPICS_DIR / f"{topic_id}.yaml"
    if yaml_path.exists():
        print(f"❌ 主題已存在: {yaml_path}")
        return False

    # 建立 YAML
    yaml_path = create_topic_yaml(topic_id, name, keywords)
    print(f"  ✅ YAML: {yaml_path.relative_to(PROJECT_ROOT)}")

    # 建立目錄結構
    index_path = create_index_md(topic_id, name)
    print(f"  ✅ index.md: {index_path.relative_to(PROJECT_ROOT)}")

    guide_path = create_guide_md(topic_id, name)
    print(f"  ✅ guide.md: {guide_path.relative_to(PROJECT_ROOT)}")

    reports_path = create_reports_dir(topic_id)
    print(f"  ✅ reports/: {reports_path.relative_to(PROJECT_ROOT)}")

    # 執行首次報告
    if run_report:
        print(f"\n🔄 執行首次報告產出...")
        result = subprocess.run(
            ["python3", "scripts/generate_topic_report.py", "--topic", topic_id],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            print(f"  ✅ 報告產出完成")
        else:
            print(f"  ⚠️  報告產出有錯誤:")
            print(result.stderr)

    print(f"\n✅ 主題 '{name}' 建立完成！")
    return True


def main():
    parser = argparse.ArgumentParser(description="建立新追蹤主題")
    parser.add_argument("--name", help="主題名稱")
    parser.add_argument("--id", help="主題 ID（用於目錄名稱）")
    parser.add_argument("--keywords", help="關鍵詞（逗號分隔）")
    parser.add_argument("--interactive", "-i", action="store_true", help="互動模式")
    parser.add_argument("--no-report", action="store_true", help="不執行首次報告")
    args = parser.parse_args()

    if args.interactive:
        interactive_mode()
    elif args.name:
        topic_id = args.id or slugify(args.name)
        keywords = [k.strip() for k in args.keywords.split(",")] if args.keywords else [args.name]
        create_topic(topic_id, args.name, keywords, run_report=not args.no_report)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
