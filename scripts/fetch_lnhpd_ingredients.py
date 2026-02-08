#!/usr/bin/env python3
"""
fetch_lnhpd_ingredients.py — 下載 Health Canada LNHPD 成分資料

從 MedicinalIngredient API 分頁下載所有成分記錄（約 810,000 筆）。

用法：
    python3 scripts/fetch_lnhpd_ingredients.py [--resume] [--limit N]

選項：
    --resume    從上次中斷處繼續下載（讀取 .progress 檔案）
    --limit N   限制下載筆數（測試用）
    --output    指定輸出路徑（預設為 docs/Extractor/ca_lnhpd/raw/ingredients-YYYY-MM-DD.jsonl）

API 端點：
    https://health-products.canada.ca/api/natural-licences/medicinalingredient/?lang=en&type=json&page={N}&limit=100

注意：
    - API 分頁從 1 開始
    - 每頁最多 100 筆（API 硬性限制，即使請求更多也只回傳 100）
    - 約需 5-6 小時下載完整資料集（810K 筆 / 100 筆每頁 / ~40 筆每秒）
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_DIR = os.path.join(BASE_DIR, "docs/Extractor/ca_lnhpd/raw")

API_BASE = "https://health-products.canada.ca/api/natural-licences/medicinalingredient/"
PAGE_SIZE = 100  # API 硬性限制，即使請求 1000 也只會回傳 100
MAX_RETRIES = 3
RETRY_DELAY_BASE = 5  # seconds, exponential backoff


def fetch_page(page_num: int, retries: int = MAX_RETRIES) -> dict | None:
    """
    下載指定頁面的成分資料。

    Args:
        page_num: 頁碼（從 1 開始）
        retries: 剩餘重試次數

    Returns:
        API 回應的 JSON 物件，失敗時回傳 None
    """
    url = f"{API_BASE}?lang=en&type=json&page={page_num}&limit={PAGE_SIZE}"

    req = Request(url)
    req.add_header("User-Agent", "SupplementProductIntelligence/1.0")
    req.add_header("Accept", "application/json")

    for attempt in range(retries):
        try:
            with urlopen(req, timeout=60) as response:
                data = json.loads(response.read().decode("utf-8"))
                return data
        except (URLError, HTTPError, json.JSONDecodeError) as e:
            delay = RETRY_DELAY_BASE * (2 ** attempt)
            print(f"  ⚠️  第 {page_num} 頁下載失敗（嘗試 {attempt + 1}/{retries}）：{e}", file=sys.stderr)
            if attempt < retries - 1:
                print(f"     等待 {delay} 秒後重試...", file=sys.stderr)
                time.sleep(delay)
            else:
                print(f"  ❌ 第 {page_num} 頁下載失敗，已達重試上限", file=sys.stderr)
                return None

    return None


def save_progress(progress_file: str, page_num: int, total_fetched: int):
    """儲存下載進度"""
    with open(progress_file, "w") as f:
        json.dump({
            "last_page": page_num,
            "total_fetched": total_fetched,
            "timestamp": datetime.now().isoformat()
        }, f)


def load_progress(progress_file: str) -> tuple[int, int]:
    """載入下載進度，回傳 (last_page, total_fetched)"""
    if os.path.exists(progress_file):
        try:
            with open(progress_file, "r") as f:
                data = json.load(f)
                return data.get("last_page", 0), data.get("total_fetched", 0)
        except (json.JSONDecodeError, KeyError):
            pass
    return 0, 0


def main():
    parser = argparse.ArgumentParser(
        description="下載 Health Canada LNHPD 成分資料"
    )
    parser.add_argument(
        "--resume", "-r",
        action="store_true",
        help="從上次中斷處繼續下載"
    )
    parser.add_argument(
        "--limit", "-l",
        type=int,
        default=0,
        help="限制下載筆數（測試用）"
    )
    parser.add_argument(
        "--output", "-o",
        type=str,
        default="",
        help="指定輸出路徑"
    )
    args = parser.parse_args()

    # 確保輸出目錄存在
    os.makedirs(RAW_DIR, exist_ok=True)

    # 設定輸出檔案
    today = datetime.now().strftime("%Y-%m-%d")
    if args.output:
        output_file = args.output
    else:
        output_file = os.path.join(RAW_DIR, f"ingredients-{today}.jsonl")

    progress_file = output_file + ".progress"
    latest_link = os.path.join(RAW_DIR, "latest-ingredients.jsonl")

    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("📡 LNHPD 成分資料下載")
    print(f"   API: {API_BASE}")
    print(f"   輸出: {output_file}")
    if args.limit > 0:
        print(f"   限制: {args.limit} 筆")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print()

    # 處理斷點續傳
    start_page = 1
    total_fetched = 0
    write_mode = "w"

    if args.resume:
        last_page, prev_fetched = load_progress(progress_file)
        if last_page > 0:
            start_page = last_page + 1
            total_fetched = prev_fetched
            write_mode = "a"
            print(f"📥 從第 {start_page} 頁繼續下載（已有 {total_fetched} 筆）")
        else:
            print("ℹ️  無進度檔案，從頭開始下載")

    # 開始下載
    page_num = start_page
    empty_pages = 0
    start_time = time.time()

    with open(output_file, write_mode, encoding="utf-8") as f:
        while True:
            # 限制筆數檢查
            if args.limit > 0 and total_fetched >= args.limit:
                print(f"\n✅ 已達限制筆數 {args.limit}，停止下載")
                break

            # 下載頁面
            data = fetch_page(page_num)

            if data is None:
                print(f"\n❌ 第 {page_num} 頁下載失敗，中斷下載")
                print(f"   已下載 {total_fetched} 筆，進度已儲存")
                save_progress(progress_file, page_num - 1, total_fetched)
                sys.exit(1)

            # 檢查是否為空頁
            records = data if isinstance(data, list) else data.get("data", [])

            if not records:
                empty_pages += 1
                if empty_pages >= 3:
                    # 連續三個空頁，視為已到達結尾
                    print(f"\n✅ 連續 {empty_pages} 個空頁，下載完成")
                    break
                page_num += 1
                continue

            empty_pages = 0  # 重置空頁計數

            # 寫入 JSONL
            page_count = 0
            for record in records:
                if args.limit > 0 and total_fetched >= args.limit:
                    break
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
                total_fetched += 1
                page_count += 1

            # 進度回報
            elapsed = time.time() - start_time
            rate = total_fetched / elapsed if elapsed > 0 else 0
            print(f"✅ 第 {page_num:4d} 頁：{page_count:4d} 筆 | 累計 {total_fetched:,} 筆 | {rate:.0f} 筆/秒")

            # 儲存進度（每 10 頁）
            if page_num % 10 == 0:
                save_progress(progress_file, page_num, total_fetched)

            page_num += 1

            # 短暫延遲，避免對 API 造成壓力
            time.sleep(0.1)

    # 清理進度檔案
    if os.path.exists(progress_file):
        os.remove(progress_file)

    # 更新符號連結
    if os.path.islink(latest_link):
        os.unlink(latest_link)
    elif os.path.exists(latest_link):
        os.remove(latest_link)
    os.symlink(os.path.basename(output_file), latest_link)

    # 最終統計
    elapsed = time.time() - start_time
    print()
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("📊 下載完成統計")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print(f"   總筆數：{total_fetched:,}")
    print(f"   總頁數：{page_num - start_page + 1}")
    print(f"   耗時：{elapsed:.1f} 秒（{elapsed/60:.1f} 分鐘）")
    print(f"   輸出：{output_file}")
    print(f"   連結：latest-ingredients.jsonl → {os.path.basename(output_file)}")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")


if __name__ == "__main__":
    main()
