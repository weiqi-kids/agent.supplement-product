#!/usr/bin/env python3
"""
將 DSLD 完整資料庫的個別 JSON 檔案轉換為萃取腳本所需的 JSONL 格式

用法：
  python3 convert_dsld_bulk_to_jsonl.py <json_dir> <output.jsonl>
  python3 convert_dsld_bulk_to_jsonl.py DSLD-full-database-JSON dsld-full-2026-02-04.jsonl
"""
import json
import os
import sys
from pathlib import Path


def convert_ingredient_rows_to_all_ingredients(ingredient_rows):
    """將詳細的 ingredientRows 轉換為簡化的 allIngredients 格式"""
    if not ingredient_rows:
        return []

    result = []
    for row in ingredient_rows:
        if not isinstance(row, dict):
            continue

        simplified = {
            "name": row.get("name", ""),
            "ingredientGroup": row.get("ingredientGroup", ""),
            "category": row.get("category", ""),
            "notes": row.get("notes", "") or ""
        }
        result.append(simplified)

        # 處理巢狀成分
        nested = row.get("nestedRows", [])
        if nested:
            for nested_row in nested:
                if isinstance(nested_row, dict):
                    nested_simplified = {
                        "name": nested_row.get("name", ""),
                        "ingredientGroup": nested_row.get("ingredientGroup", ""),
                        "category": nested_row.get("category", ""),
                        "notes": nested_row.get("notes", "") or ""
                    }
                    result.append(nested_simplified)

    return result


def convert_single_json(json_data):
    """將單個 bulk JSON 轉換為萃取腳本期望的格式"""
    # 確保 dsld_id 為字串格式（與 API 一致）
    raw_id = json_data.get("id")
    dsld_id = str(raw_id) if raw_id is not None else ""

    converted = {
        "dsld_id": dsld_id,
        "fullName": json_data.get("fullName", ""),
        "brandName": json_data.get("brandName", ""),
        "productType": json_data.get("productType"),
        "physicalState": json_data.get("physicalState"),
        "entryDate": json_data.get("entryDate", ""),
        "offMarket": json_data.get("offMarket", 0),
        "netContents": json_data.get("netContents", []),
        "claims": json_data.get("claims", []),
        "allIngredients": convert_ingredient_rows_to_all_ingredients(
            json_data.get("ingredientRows", [])
        ),
        # 保留其他可能有用的欄位
        "userGroups": json_data.get("userGroups", []),
        "targetGroups": json_data.get("targetGroups", []),
        "statements": json_data.get("statements", []),
    }
    return converted


def main():
    if len(sys.argv) < 3:
        print("用法: python3 convert_dsld_bulk_to_jsonl.py <json_dir> <output.jsonl>")
        print("範例: python3 convert_dsld_bulk_to_jsonl.py DSLD-full-database-JSON dsld-full.jsonl")
        sys.exit(1)

    json_dir = Path(sys.argv[1])
    output_file = Path(sys.argv[2])

    if not json_dir.is_dir():
        print(f"❌ 目錄不存在: {json_dir}", file=sys.stderr)
        sys.exit(1)

    json_files = list(json_dir.glob("*.json"))
    total = len(json_files)

    print(f"📂 來源目錄：{json_dir}")
    print(f"📄 JSON 檔案數：{total}")
    print(f"📝 輸出檔案：{output_file}")
    print()

    converted = 0
    errors = 0

    with open(output_file, "w", encoding="utf-8") as out:
        for i, json_file in enumerate(sorted(json_files), 1):
            try:
                with open(json_file, "r", encoding="utf-8") as f:
                    data = json.load(f)

                converted_data = convert_single_json(data)
                out.write(json.dumps(converted_data, ensure_ascii=False) + "\n")
                converted += 1

                if converted % 10000 == 0:
                    print(f"  進度：{converted:,}/{total:,} ({converted*100/total:.1f}%)")

            except Exception as e:
                print(f"  ⚠️ 錯誤處理 {json_file.name}: {e}", file=sys.stderr)
                errors += 1

    print()
    print(f"━━━ 轉換完成 ━━━")
    print(f"  成功轉換：{converted:,} 筆")
    print(f"  錯誤：{errors} 筆")
    print(f"  輸出檔案：{output_file}")
    print(f"  檔案大小：{output_file.stat().st_size / 1024 / 1024:.1f} MB")


if __name__ == "__main__":
    main()
