#!/usr/bin/env python3
"""
連結修復腳本

解析 lychee 報告，嘗試自動修復常見的連結問題。
無法修復的問題會輸出到 stdout 供後續建立 Issue。
"""

import re
import sys
import json
from pathlib import Path


def parse_lychee_report(report_path: str) -> list[dict]:
    """解析 lychee 報告檔案"""
    issues = []

    try:
        content = Path(report_path).read_text(encoding="utf-8")
    except FileNotFoundError:
        print(f"報告檔案不存在: {report_path}", file=sys.stderr)
        return issues

    # lychee markdown 格式：
    # ## Errors
    # | Status | URL | Source |
    # |--------|-----|--------|
    # | 404 | https://example.com/broken | file.html |

    current_section = None
    in_table = False

    for line in content.split("\n"):
        line = line.strip()

        if line.startswith("## "):
            current_section = line[3:].lower()
            in_table = False
            continue

        if line.startswith("|") and "Status" in line:
            in_table = True
            continue

        if line.startswith("|---"):
            continue

        if in_table and line.startswith("|"):
            parts = [p.strip() for p in line.split("|")]
            if len(parts) >= 4:
                status = parts[1]
                url = parts[2]
                source = parts[3]

                if status and url:
                    issues.append({
                        "type": current_section or "unknown",
                        "status": status,
                        "url": url,
                        "source": source,
                    })

    return issues


def attempt_fix(issue: dict) -> dict | None:
    """嘗試修復連結問題，返回修復建議或 None"""
    url = issue.get("url", "")
    status = issue.get("status", "")

    # 常見修復模式
    fixes = []

    # HTTP -> HTTPS 升級
    if url.startswith("http://"):
        fixes.append({
            "action": "replace",
            "old": url,
            "new": url.replace("http://", "https://"),
            "reason": "升級為 HTTPS",
        })

    # 尾部斜線問題
    if status == "404" and not url.endswith("/") and "." not in url.split("/")[-1]:
        fixes.append({
            "action": "replace",
            "old": url,
            "new": url + "/",
            "reason": "添加尾部斜線",
        })

    # 常見網站 URL 變更
    url_mappings = {
        "github.com/anthropics/claude-code/issues": "github.com/anthropics/claude-code/issues",
        # 可以添加更多已知的 URL 映射
    }

    for old_pattern, new_pattern in url_mappings.items():
        if old_pattern in url:
            fixes.append({
                "action": "replace",
                "old": url,
                "new": url.replace(old_pattern, new_pattern),
                "reason": "已知 URL 遷移",
            })

    return fixes[0] if fixes else None


def main():
    if len(sys.argv) < 2:
        print("用法: fix_broken_links.py <lychee-report.md>", file=sys.stderr)
        sys.exit(1)

    report_path = sys.argv[1]
    issues = parse_lychee_report(report_path)

    if not issues:
        print("✅ 沒有發現連結問題")
        sys.exit(0)

    print(f"🔍 發現 {len(issues)} 個連結問題")
    print("=" * 50)

    fixed = []
    unfixed = []

    for issue in issues:
        fix = attempt_fix(issue)
        if fix:
            fixed.append({**issue, "fix": fix})
            print(f"✅ 可修復: {issue['url']}")
            print(f"   → {fix['new']} ({fix['reason']})")
        else:
            unfixed.append(issue)
            print(f"❌ 無法自動修復: {issue['url']}")
            print(f"   狀態: {issue['status']}, 來源: {issue['source']}")

    print("=" * 50)
    print(f"可自動修復: {len(fixed)}")
    print(f"需人工處理: {len(unfixed)}")

    # 輸出需要建立 Issue 的問題
    if unfixed:
        print("\n## 需要人工處理的連結問題\n")
        for issue in unfixed:
            print(f"- [{issue['status']}] {issue['url']}")
            print(f"  - 來源: {issue['source']}")

    # 輸出 JSON 格式供後續處理
    output = {
        "fixed": fixed,
        "unfixed": unfixed,
        "summary": {
            "total": len(issues),
            "fixed": len(fixed),
            "unfixed": len(unfixed),
        }
    }

    # 寫入 JSON 結果
    result_path = Path(report_path).with_suffix(".json")
    result_path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n📄 詳細結果已寫入: {result_path}")

    # 如果有無法修復的問題，返回非零退出碼
    sys.exit(1 if unfixed else 0)


if __name__ == "__main__":
    main()
