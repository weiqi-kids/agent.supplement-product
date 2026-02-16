#!/usr/bin/env python3
"""
更新選購指南的藥物交互章節

用法：
  python3 scripts/update_guide_interactions.py              # 更新所有主題
  python3 scripts/update_guide_interactions.py --topic fish-oil  # 更新特定主題
  python3 scripts/update_guide_interactions.py --dry-run    # 僅顯示，不寫入
"""

import argparse
import re
import yaml
from pathlib import Path
from collections import defaultdict

PROJECT_ROOT = Path(__file__).parent.parent
DHI_DIR = PROJECT_ROOT / "docs" / "Extractor" / "dhi"
DFI_DIR = PROJECT_ROOT / "docs" / "Extractor" / "dfi"
DDI_DIR = PROJECT_ROOT / "docs" / "Extractor" / "ddi"
GUIDES_DIR = PROJECT_ROOT / "docs" / "reports"

# 主題與交互類別對照
TOPIC_INTERACTION_MAP = {
    "fish-oil": {
        "name": "魚油",
        "dhi": ["omega_fatty_acid", "general"],
        "dfi": [],
        "ddi": ["anticoagulant"],
    },
    "curcumin": {
        "name": "薑黃素",
        "dhi": ["botanical", "general"],
        "dfi": [],
        "ddi": [],
    },
    "nattokinase": {
        "name": "納豆激酶",
        "dhi": ["general"],
        "dfi": ["vitamin_k"],
        "ddi": ["anticoagulant"],
    },
    "glucosamine": {
        "name": "葡萄糖胺",
        "dhi": ["general"],
        "dfi": [],
        "ddi": [],
    },
    "collagen": {
        "name": "膠原蛋白",
        "dhi": ["general"],
        "dfi": [],
        "ddi": [],
    },
    "lutein": {
        "name": "葉黃素",
        "dhi": ["general"],
        "dfi": [],
        "ddi": [],
    },
    "nmn": {
        "name": "NMN",
        "dhi": ["general"],
        "dfi": [],
        "ddi": [],
    },
    "red-yeast-rice": {
        "name": "紅麴",
        "dhi": ["general"],
        "dfi": ["grapefruit", "citrus"],
        "ddi": ["statin"],
    },
    "exosomes": {
        "name": "外泌體",
        "dhi": ["general"],
        "dfi": [],
        "ddi": [],
    },
}


def load_interaction_files(base_dir: Path, categories: list) -> list:
    """載入指定類別的交互作用檔案"""
    interactions = []

    for category in categories:
        category_dir = base_dir / category
        if not category_dir.exists():
            continue

        for md_file in category_dir.glob("*.md"):
            content = md_file.read_text(encoding="utf-8")

            # 跳過 REVIEW_NEEDED
            if "[REVIEW_NEEDED]" in content:
                continue

            # 解析 frontmatter
            interaction = {"file": str(md_file), "pmid": md_file.stem}

            clean_content = content.replace("[REVIEW_NEEDED]\n\n", "")
            if clean_content.startswith("---"):
                parts = clean_content.split("---", 2)
                if len(parts) >= 3:
                    try:
                        fm = yaml.safe_load(parts[1])
                        if fm:
                            interaction["title"] = fm.get("title", "")
                            interaction["severity"] = fm.get("severity", "unknown")
                            interaction["evidence_level"] = fm.get("evidence_level", 5)
                            interaction["source_url"] = fm.get("source_url", "")
                            interaction["category"] = fm.get("category", category)
                    except yaml.YAMLError:
                        pass

            # 提取摘要
            abstract_match = re.search(r"## 摘要\s*\n([\s\S]*?)(?=\n---|\n##|\Z)", content)
            if abstract_match:
                interaction["abstract"] = abstract_match.group(1).strip()[:500]
            else:
                interaction["abstract"] = ""

            if interaction.get("title"):
                interactions.append(interaction)

    return interactions


def infer_risk(interaction: dict) -> str:
    """推斷風險描述"""
    text = f"{interaction.get('title', '')} {interaction.get('abstract', '')}".lower()

    if any(kw in text for kw in ["bleeding", "hemorrhag", "coagulopathy", "anticoagulant"]):
        return "出血風險"
    if any(kw in text for kw in ["cyp", "metabolism", "pharmacokinetic"]):
        return "代謝影響"
    if any(kw in text for kw in ["hypoglycemia", "blood glucose", "diabetes"]):
        return "血糖影響"
    if any(kw in text for kw in ["hypotension", "blood pressure"]):
        return "血壓影響"
    if any(kw in text for kw in ["hepato", "liver"]):
        return "肝臟影響"
    if any(kw in text for kw in ["no effect", "no significant", "safe"]):
        return "無顯著交互"
    return "交互待評估"


def generate_interaction_section(topic_id: str, topic_config: dict) -> str:
    """產生交互作用章節"""
    topic_name = topic_config["name"]

    # 載入各類交互資料
    dhi_data = load_interaction_files(DHI_DIR, topic_config.get("dhi", []))
    dfi_data = load_interaction_files(DFI_DIR, topic_config.get("dfi", []))
    ddi_data = load_interaction_files(DDI_DIR, topic_config.get("ddi", []))

    all_interactions = dhi_data + dfi_data + ddi_data

    if not all_interactions:
        return ""

    # 去重（by PMID）
    seen_pmids = set()
    unique_interactions = []
    for item in all_interactions:
        if item["pmid"] not in seen_pmids:
            seen_pmids.add(item["pmid"])
            unique_interactions.append(item)

    # 限制數量（最多 10 筆最相關的）
    unique_interactions = unique_interactions[:10]

    section = f"""
## ⚠️ 藥物交互提醒

本章節整理{topic_name}相關的藥物交互文獻，供參考。

### 相關交互文獻

| 文獻標題 | 風險類型 | 證據等級 | 來源 |
|----------|----------|----------|------|
"""

    for item in unique_interactions:
        title = item.get("title", "")[:45]
        if len(item.get("title", "")) > 45:
            title += "..."
        risk = infer_risk(item)
        level = item.get("evidence_level", 5)
        pmid = item.get("pmid", "")
        url = item.get("source_url", f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/")
        section += f"| {title} | {risk} | Level {level} | [PMID:{pmid}]({url}) |\n"

    section += """
### 安全建議

1. **諮詢醫師**：服用處方藥物者，補充保健食品前應諮詢醫師
2. **注意劑量**：遵循建議劑量，避免過量補充
3. **觀察反應**：開始補充時注意身體反應，如有不適應停用並就醫
4. **術前告知**：手術前應告知醫師所有正在服用的保健食品

> ⚠️ **免責聲明**：本資訊僅供教育和研究目的，不構成醫療建議。任何用藥或補充劑變更應諮詢專業醫療人員。
"""

    return section


def update_guide(topic_id: str, dry_run: bool = False) -> bool:
    """更新指定主題的選購指南"""
    if topic_id not in TOPIC_INTERACTION_MAP:
        print(f"  ⚠️ 未知主題: {topic_id}")
        return False

    guide_path = GUIDES_DIR / topic_id / "guide.md"
    if not guide_path.exists():
        print(f"  ⚠️ 找不到指南: {guide_path}")
        return False

    topic_config = TOPIC_INTERACTION_MAP[topic_id]
    interaction_section = generate_interaction_section(topic_id, topic_config)

    if not interaction_section:
        print(f"  ℹ️ 無交互資料: {topic_id}")
        return False

    content = guide_path.read_text(encoding="utf-8")

    # 檢查是否已有交互章節
    if "## ⚠️ 藥物交互提醒" in content:
        # 替換現有章節
        pattern = r"## ⚠️ 藥物交互提醒[\s\S]*?(?=\n---\n|\n## [^⚠️]|\Z)"
        new_content = re.sub(pattern, interaction_section.strip(), content)
    else:
        # 在檔案末尾的免責聲明前插入
        if "*本指南基於" in content:
            new_content = content.replace(
                "*本指南基於",
                f"{interaction_section}\n---\n\n*本指南基於"
            )
        else:
            # 直接加在最後
            new_content = content.rstrip() + "\n" + interaction_section

    if dry_run:
        print(f"  📝 [DRY RUN] 將更新: {guide_path.name}")
        print(f"     交互文獻數: {interaction_section.count('PMID:')}")
    else:
        guide_path.write_text(new_content, encoding="utf-8")
        print(f"  ✅ 已更新: {guide_path.name}")

    return True


def main():
    parser = argparse.ArgumentParser(description="更新選購指南的藥物交互章節")
    parser.add_argument("--topic", help="指定主題 ID")
    parser.add_argument("--dry-run", action="store_true", help="僅顯示，不寫入")
    args = parser.parse_args()

    print("=" * 50)
    print("更新選購指南藥物交互章節")
    print("=" * 50)

    if args.topic:
        topics = [args.topic]
    else:
        topics = list(TOPIC_INTERACTION_MAP.keys())

    updated = 0
    for topic_id in topics:
        print(f"\n處理: {topic_id}")
        if update_guide(topic_id, args.dry_run):
            updated += 1

    print("\n" + "=" * 50)
    print(f"✅ 完成：更新 {updated}/{len(topics)} 個指南")
    print("=" * 50)


if __name__ == "__main__":
    main()
