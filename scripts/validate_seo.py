#!/usr/bin/env python3
"""
SEO 驗證腳本

在部署前檢查所有頁面的 SEO 完整性：
- JSON-LD Schema 存在且有效
- YMYL 免責聲明存在
- Meta 標籤長度符合規範
- URL 結構正確

使用方式：
    python3 scripts/validate_seo.py
    python3 scripts/validate_seo.py --verbose
    python3 scripts/validate_seo.py --fix  # 嘗試自動修復（未來功能）
"""

import os
import re
import sys
import json
import yaml
import argparse
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional


# 路徑配置
PROJECT_ROOT = Path(__file__).parent.parent
REPORTS_DIR = PROJECT_ROOT / "docs" / "reports"
SEO_CONFIG_PATH = PROJECT_ROOT / "seo" / "config.yaml"


@dataclass
class ValidationResult:
    """驗證結果"""

    file_path: Path
    passed: bool = True
    errors: list = field(default_factory=list)
    warnings: list = field(default_factory=list)


@dataclass
class ValidationSummary:
    """驗證摘要"""

    total: int = 0
    passed: int = 0
    warnings: int = 0
    failed: int = 0
    results: list = field(default_factory=list)


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


def validate_json_ld(frontmatter: dict, result: ValidationResult):
    """驗證 JSON-LD Schema"""
    json_ld = frontmatter.get("json_ld")

    if not json_ld:
        result.errors.append("缺少 json_ld Schema")
        result.passed = False
        return

    # 檢查 @context
    if json_ld.get("@context") != "https://schema.org":
        result.errors.append("json_ld @context 應為 https://schema.org")
        result.passed = False

    # 檢查 @graph
    graph = json_ld.get("@graph", [])
    if not graph:
        result.errors.append("json_ld 缺少 @graph")
        result.passed = False
        return

    # 檢查必要的 Schema 類型
    types_found = set()
    for item in graph:
        item_type = item.get("@type")
        if item_type:
            types_found.add(item_type)

    required_types = {"WebPage", "Organization", "WebSite"}
    missing_types = required_types - types_found

    if missing_types:
        result.warnings.append(f"缺少基礎 Schema: {', '.join(missing_types)}")

    # 報告頁面應有 Article
    if "Article" not in types_found:
        result.warnings.append("報告頁面建議加入 Article Schema")

    # 檢查 BreadcrumbList
    if "BreadcrumbList" not in types_found:
        result.warnings.append("建議加入 BreadcrumbList Schema")


def validate_meta_tags(frontmatter: dict, result: ValidationResult):
    """驗證 Meta 標籤"""
    title = frontmatter.get("title", "")
    description = frontmatter.get("description", "")

    # 標題長度
    if len(title) > 60:
        result.warnings.append(f"標題過長 ({len(title)} 字，建議 ≤60)")

    if not title:
        result.errors.append("缺少 title")
        result.passed = False

    # 描述長度
    if len(description) > 155:
        result.warnings.append(f"描述過長 ({len(description)} 字，建議 ≤155)")

    if not description:
        result.warnings.append("缺少 description")


def validate_ymyl_disclaimer(body: str, result: ValidationResult):
    """驗證 YMYL 免責聲明"""
    if "免責聲明" not in body and "disclaimer" not in body.lower():
        result.warnings.append("建議加入 YMYL 免責聲明")


def validate_url_structure(file_path: Path, result: ValidationResult):
    """驗證 URL 結構"""
    filename = file_path.stem

    # 檢查是否包含中文
    if re.search(r"[\u4e00-\u9fff]", filename):
        result.warnings.append(f"檔名包含中文: {filename}")

    # 檢查是否使用連字號
    if "_" in filename:
        result.warnings.append(f"建議使用連字號(-)而非底線(_): {filename}")


def validate_file(file_path: Path, verbose: bool = False) -> ValidationResult:
    """驗證單一檔案"""
    result = ValidationResult(file_path=file_path)

    try:
        content = file_path.read_text(encoding="utf-8")
        frontmatter, body = parse_frontmatter(content)

        if not frontmatter:
            result.errors.append("無法解析 frontmatter")
            result.passed = False
            return result

        # 執行各項驗證
        validate_json_ld(frontmatter, result)
        validate_meta_tags(frontmatter, result)
        validate_ymyl_disclaimer(body, result)
        validate_url_structure(file_path, result)

    except Exception as e:
        result.errors.append(f"讀取檔案失敗: {str(e)}")
        result.passed = False

    return result


def validate_all(verbose: bool = False) -> ValidationSummary:
    """驗證所有報告檔案"""
    summary = ValidationSummary()

    # 收集所有 .md 檔案
    md_files = list(REPORTS_DIR.rglob("*.md"))

    # 排除 index.md 和 guide.md（這些可能有不同的結構）
    report_files = [
        f
        for f in md_files
        if f.name not in ("index.md", "guide.md") and not f.name.startswith(".")
    ]

    summary.total = len(report_files)

    for file_path in sorted(report_files):
        result = validate_file(file_path, verbose)
        summary.results.append(result)

        if not result.passed:
            summary.failed += 1
        elif result.warnings:
            summary.warnings += 1
        else:
            summary.passed += 1

    return summary


def print_summary(summary: ValidationSummary, verbose: bool = False):
    """輸出驗證摘要"""
    print("\n" + "=" * 60)
    print("SEO 驗證報告")
    print("=" * 60)
    print(f"總計：{summary.total} 頁")
    print(f"✅ 通過：{summary.passed} 頁")
    print(f"⚠️ 警告：{summary.warnings} 頁（非致命問題）")
    print(f"❌ 失敗：{summary.failed} 頁")
    print("=" * 60)

    # 輸出詳細問題
    if summary.failed > 0 or (verbose and summary.warnings > 0):
        print("\n詳細問題清單：")
        print("-" * 60)

        for result in summary.results:
            if not result.passed or (verbose and result.warnings):
                rel_path = result.file_path.relative_to(PROJECT_ROOT)
                print(f"\n📄 {rel_path}")

                for error in result.errors:
                    print(f"   ❌ {error}")

                if verbose:
                    for warning in result.warnings:
                        print(f"   ⚠️ {warning}")

    # 輸出總結建議
    print("\n" + "-" * 60)
    if summary.failed > 0:
        print("❌ 驗證失敗：請修正上述錯誤後再部署")
        return False
    elif summary.warnings > 0:
        print("⚠️ 驗證通過（有警告）：建議修正警告項目以優化 SEO")
        return True
    else:
        print("✅ 驗證通過：所有頁面符合 SEO 規範")
        return True


def main():
    parser = argparse.ArgumentParser(description="SEO 驗證腳本")
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="顯示詳細資訊（包含警告）"
    )
    parser.add_argument(
        "--fix", action="store_true", help="嘗試自動修復問題（未來功能）"
    )
    parser.add_argument("--file", type=str, help="驗證特定檔案")

    args = parser.parse_args()

    if args.fix:
        print("⚠️ --fix 功能尚未實作")
        return

    if args.file:
        # 驗證單一檔案
        file_path = Path(args.file)
        if not file_path.exists():
            print(f"❌ 檔案不存在: {args.file}")
            sys.exit(1)

        result = validate_file(file_path, args.verbose)
        print(f"\n📄 {file_path}")

        if result.errors:
            for error in result.errors:
                print(f"   ❌ {error}")

        if result.warnings:
            for warning in result.warnings:
                print(f"   ⚠️ {warning}")

        if result.passed and not result.warnings:
            print("   ✅ 驗證通過")

        sys.exit(0 if result.passed else 1)

    # 驗證所有檔案
    summary = validate_all(args.verbose)
    success = print_summary(summary, args.verbose)

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
