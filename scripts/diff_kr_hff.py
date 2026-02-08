#!/usr/bin/env python3
"""
kr_hff 差異比對工具

比較新舊 JSONL 檔案，輸出：
1. 新增的產品（new_ids.txt）
2. 修改的產品（updated_ids.txt）
3. 差異 JSONL（delta.jsonl）- 只包含需要處理的產品

用法：
  python3 diff_kr_hff.py <old_jsonl> <new_jsonl> <output_dir>

差異偵測邏輯：
- 使用 STTEMNT_NO（品目番號）作為唯一識別碼
- 使用 REGIST_DT（登記日期）判斷更新
"""
import json
import sys
import os
from datetime import datetime

def load_jsonl_index(filepath):
    """
    載入 JSONL 並建立索引
    返回: {STTEMNT_NO: {REGIST_DT, data}}
    """
    index = {}
    if not os.path.exists(filepath):
        return index

    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
                # kr_hff 可能有 item wrapper
                item = record.get('item', record)
                sttemnt_no = item.get('STTEMNT_NO')
                if sttemnt_no:
                    index[str(sttemnt_no)] = {
                        'REGIST_DT': item.get('REGIST_DT'),
                        'data': record
                    }
            except json.JSONDecodeError:
                continue
    return index

def compare_indexes(old_index, new_index):
    """
    比較新舊索引，找出差異
    返回: (added_ids, updated_ids, unchanged_ids, removed_ids)
    """
    old_ids = set(old_index.keys())
    new_ids_set = set(new_index.keys())

    # 新增的 ID
    added_ids = new_ids_set - old_ids

    # 刪除的 ID
    removed_ids = old_ids - new_ids_set

    # 檢查更新的 ID（REGIST_DT 變化）
    updated_ids = set()
    unchanged_ids = set()

    common_ids = old_ids & new_ids_set
    for sid in common_ids:
        old_dt = old_index[sid]['REGIST_DT']
        new_dt = new_index[sid]['REGIST_DT']

        # 如果 REGIST_DT 變更，視為更新
        if old_dt != new_dt:
            updated_ids.add(sid)
        else:
            unchanged_ids.add(sid)

    return added_ids, updated_ids, unchanged_ids, removed_ids

def main():
    if len(sys.argv) < 4:
        print("用法: python3 diff_kr_hff.py <old_jsonl> <new_jsonl> <output_dir>")
        sys.exit(1)

    old_file = sys.argv[1]
    new_file = sys.argv[2]
    output_dir = sys.argv[3]

    os.makedirs(output_dir, exist_ok=True)

    print(f"載入舊檔案: {old_file}")
    old_index = load_jsonl_index(old_file)
    print(f"  → {len(old_index)} 筆產品")

    print(f"載入新檔案: {new_file}")
    new_index = load_jsonl_index(new_file)
    print(f"  → {len(new_index)} 筆產品")

    print("比對差異...")
    added_ids, updated_ids, unchanged_ids, removed_ids = compare_indexes(old_index, new_index)

    print(f"\n━━━ 比對結果 ━━━")
    print(f"  新增: {len(added_ids)}")
    print(f"  更新: {len(updated_ids)}")
    print(f"  未變: {len(unchanged_ids)}")
    print(f"  移除: {len(removed_ids)}")

    # 輸出新增 ID 清單
    with open(os.path.join(output_dir, 'new_ids.txt'), 'w') as f:
        for sid in sorted(added_ids):
            f.write(f"{sid}\n")

    # 輸出更新 ID 清單
    with open(os.path.join(output_dir, 'updated_ids.txt'), 'w') as f:
        for sid in sorted(updated_ids):
            f.write(f"{sid}\n")

    # 輸出移除 ID 清單
    with open(os.path.join(output_dir, 'removed_ids.txt'), 'w') as f:
        for sid in sorted(removed_ids):
            f.write(f"{sid}\n")

    # 輸出差異 JSONL（新增 + 更新）
    delta_ids = added_ids | updated_ids
    delta_file = os.path.join(output_dir, 'delta.jsonl')
    with open(delta_file, 'w', encoding='utf-8') as f:
        for sid in delta_ids:
            record = new_index[sid]['data']
            f.write(json.dumps(record, ensure_ascii=False) + '\n')

    print(f"\n輸出檔案:")
    print(f"  {output_dir}/new_ids.txt ({len(added_ids)} 筆)")
    print(f"  {output_dir}/updated_ids.txt ({len(updated_ids)} 筆)")
    print(f"  {output_dir}/removed_ids.txt ({len(removed_ids)} 筆)")
    print(f"  {output_dir}/delta.jsonl ({len(delta_ids)} 筆)")

    # 輸出摘要 JSON
    summary = {
        'timestamp': datetime.now().isoformat(),
        'old_file': old_file,
        'new_file': new_file,
        'old_count': len(old_index),
        'new_count': len(new_index),
        'added': len(added_ids),
        'updated': len(updated_ids),
        'unchanged': len(unchanged_ids),
        'removed': len(removed_ids),
        'delta_total': len(delta_ids)
    }
    with open(os.path.join(output_dir, 'summary.json'), 'w') as f:
        json.dump(summary, f, indent=2)

    # 返回需處理的數量
    print(f"\n需處理: {len(delta_ids)} 筆")
    return len(delta_ids)

if __name__ == '__main__':
    sys.exit(0 if main() >= 0 else 1)
