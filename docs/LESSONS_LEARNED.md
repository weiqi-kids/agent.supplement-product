# 錯誤與教訓記錄

本文件記錄專案開發過程中遇到的問題與解決方案，避免未來重蹈覆轍。

---

## 2026-02-04：us_dsld 與 kr_hff 資料完整性修復

### 問題 1：未充分調查資料源的完整存取方式

**現象**：
- 使用 DSLD API 分頁擷取，遇到 Elasticsearch `max_result_window=10,000` 限制
- 嘗試 product_type 分區、日期過濾等方式繞過，均失敗
- 僅擷取 10,000/214,780 筆（4.7%）

**根本原因**：
- 未事先調查是否有 Bulk Download 選項
- NIH 官網有提供完整資料庫下載，但未被發現

**正確做法**：
```
Bulk Download URL:
https://api.ods.od.nih.gov/dsld/s3/data/DSLD-full-database-JSON.zip
```

**教訓**：
> 遇到 API 分頁限制時，優先搜尋「bulk download」、「full database export」、「complete dataset」等關鍵字。
> 檢查資料源官網的「Download」、「Data Access」、「API Guide」頁面。

**預防措施**：
- 在 Layer CLAUDE.md 中記錄資料源的所有存取方式
- fetch.sh 註解中標明選用的存取方式及其限制

---

### 問題 2：資料格式不一致未事先驗證

**現象**：
- Bulk Download JSON 的 `id` 欄位是整數（如 `10000`）
- API 回傳的 `dsld_id` 欄位是字串（如 `"270355"`）
- diff_dsld.py 比對時將所有產品視為「新增」，無法正確識別重複

**根本原因**：
- 切換資料源時未比對新舊格式的欄位型別
- 假設兩種來源格式一致

**修正方式**：
```python
# convert_dsld_bulk_to_jsonl.py
dsld_id = str(raw_id) if raw_id is not None else ""
```

**教訓**：
> 切換資料源時，必須比對新舊格式的：
> 1. 欄位名稱（id vs dsld_id）
> 2. 欄位型別（int vs string）
> 3. 欄位值格式（日期格式、編碼等）

**預防措施**：
- 新增資料源時，先取樣比對 3-5 筆資料的完整結構
- 在轉換腳本中明確處理型別轉換

---

### 問題 3：報告未自動與資料更新連動

**現象**：
- 資料從 10,000 筆增加到 214,780 筆
- 報告仍顯示舊數據（10,000 筆）
- 使用者需手動要求重新產出報告

**根本原因**：
- Extractor 和 Narrator 流程分離
- 無機制檢測資料變化並觸發報告更新

**教訓**：
> 完整流程（執行完整流程）應包含 Narrator 報告更新。
> 資料萃取完成後，若數量變化超過 10%，應主動提醒或自動重新產出報告。

**預防措施**：
- 在 CLAUDE.md 執行流程中加入報告更新步驟
- 萃取完成後比對新舊筆數，變化顯著時提醒更新報告

---

### 問題 4：缺乏資料完整性檢查機制

**現象**：
- kr_hff 只擷取了 4,600/44,091 筆（10.4%）
- 系統未發出警告，直到手動檢查才發現
- fetch.sh 執行中斷但未記錄預期總數

**根本原因**：
- fetch.sh 只記錄實際擷取筆數，未與預期筆數比對
- 無完整性檢查機制

**教訓**：
> fetch.sh 應在開始時記錄 API 回報的總筆數，結束時比對實際擷取筆數。
> 若差異過大，應發出警告。

**預防措施**：
```bash
# fetch.sh 結束時加入檢查
EXPECTED=$(curl -s "$API?size=0" | jq '.stats.count')
if [[ $TOTAL -lt $((EXPECTED * 90 / 100)) ]]; then
  echo "⚠️ 警告：擷取筆數 ($TOTAL) 低於預期 ($EXPECTED) 的 90%"
fi
```

---

## 通用教訓清單

| 類別 | 教訓 | 檢查點 |
|------|------|--------|
| 資料源 | 優先調查 Bulk Download 選項 | 新增 Layer 時 |
| 資料源 | 記錄 API 的已知限制 | Layer CLAUDE.md |
| 格式 | 比對新舊資料源的欄位型別 | 切換資料源時 |
| 格式 | ID 欄位統一使用字串格式 | 轉換腳本 |
| 流程 | 資料更新後檢查報告是否需更新 | 萃取完成後 |
| 完整性 | 比對預期筆數與實際筆數 | fetch.sh 結束時 |
| 完整性 | 設定合理的完整性閾值（如 90%） | fetch.sh |

---

## 2026-02-04：ca_lnhpd 成分資料整合

### 問題：報告顯示「成分資料尚未完整擷取」

**現象**：
- 成分雷達報告顯示「加拿大 - 成分資料尚未完整擷取」
- 所有 ca_lnhpd 產品的成分欄位顯示 placeholder
- 產品資料有 ~120K 筆，但無成分

**根本原因**：
- Health Canada LNHPD 的產品 API (`ProductLicence`) 不包含成分資料
- 成分資料需另外呼叫 `MedicinalIngredient` API（約 810K 筆）
- 原有 fetch.sh 只下載產品資料，未考慮成分

**解決方案**：
```
架構：分離式 Fetch + 合併式萃取

1. fetch_lnhpd_ingredients.py  →  ingredients-YYYY-MM-DD.jsonl (810K 筆)
2. extract_ca_lnhpd.py --ingredients <path>  ←  載入成分索引，關聯輸出
```

**教訓**：
> 當資料源有多個相關 API 端點時（產品、成分、宣稱等），應在 Layer 設計階段就規劃完整的資料獲取策略。
> 不要假設單一 API 端點包含所有需要的資料。

**預防措施**：
- 新增 Layer 時，完整調查所有可用 API 端點
- 在 Layer CLAUDE.md 中明確記錄各端點的資料範圍
- 設計可擴展的 fetch.sh（如 `--with-ingredients` 選項）

---

### 設計決策：分離式下載 vs 一次性下載

**考量因素**：
| 因素 | 分離式（採用） | 一次性 |
|------|----------------|--------|
| 更新頻率 | 產品：每週；成分：每月 | 都要全量 |
| 下載時間 | 可平行，成分可斷點續傳 | 需等待 |
| 記憶體 | 成分索引約需 ~500MB | 需全部載入 |
| 靈活性 | 可選擇是否整合成分 | 強制綁定 |

**結論**：
> 當兩類資料的更新頻率不同時，優先採用分離式架構。
> 成分資料變動少，每月更新一次即可；產品資料更頻繁，應支援獨立增量更新。

---

### API 限制發現：每頁最多 100 筆

**現象**：
- 腳本設定 `limit=1000`，預期 7-10 分鐘完成
- 實際 API 只回傳 100 筆/頁，需 5-6 小時

**根本原因**：
- Health Canada MedicinalIngredient API 有硬性分頁限制（100 筆）
- 即使請求 `limit=1000`，回應的 `pagination.limit` 仍為 100

**教訓**：
> API 文件可能未完整記載所有限制。
> 實際測試時應檢查回應的 pagination metadata 是否符合請求參數。

**預防措施**：
- 在 fetch 腳本開頭測試一頁，確認實際回傳筆數
- 在 Layer CLAUDE.md 記錄 API 的實際限制（非文件宣稱）

---

### 技術細節：成分索引的記憶體最佳化

**做法**：
```python
# 使用 lnhpd_id 作為 key，只載入必要欄位
index = defaultdict(list)
for record in ingredients:
    index[record["lnhpd_id"]].append({
        "ingredient_name": ...,
        "potency_amount": ...,
        "potency_unit": ...,
        "source_material": ...
    })
```

**注意事項**：
- 810K 筆成分對應約 120K 產品，平均每產品約 6-7 種成分
- 載入完整索引約需 30-60 秒，約 500MB 記憶體
- 若記憶體不足，可考慮改用 SQLite 或 LMDB 作為本地索引

---

## 通用教訓清單

| 類別 | 教訓 | 檢查點 |
|------|------|--------|
| 資料源 | 優先調查 Bulk Download 選項 | 新增 Layer 時 |
| 資料源 | 記錄 API 的已知限制 | Layer CLAUDE.md |
| 資料源 | 調查所有相關 API 端點（產品、成分、宣稱） | 新增 Layer 時 |
| 格式 | 比對新舊資料源的欄位型別 | 切換資料源時 |
| 格式 | ID 欄位統一使用字串格式 | 轉換腳本 |
| 架構 | 不同更新頻率的資料應分離下載 | Layer 設計時 |
| API | 測試實際回傳筆數，勿信文件宣稱 | fetch 腳本開發時 |
| 流程 | 資料更新後檢查報告是否需更新 | 萃取完成後 |
| 完整性 | 比對預期筆數與實際筆數 | fetch.sh 結束時 |
| 完整性 | 設定合理的完整性閾值（如 90%） | fetch.sh |

---

## 2026-02-04：ca_lnhpd 產品名稱重複問題

### 問題：同一產品出現在多個分類目錄

**現象**：
- 萃取完成後驗證失敗：萃取完成率 55.4%（160,566 / 289,682）
- 實際 MD 檔案數（160,566）多於不重複產品 ID 數（149,161）
- 同一個產品 ID 出現在多個分類目錄（如 vitamins_minerals, botanicals, omega 等）

**根本原因**：
- Health Canada API 回傳同一產品的多個名稱變體
- 每個變體有不同的 `product_name`，但相同的 `lnhpd_id`
- `flag_primary_name = 1` 表示主要名稱，`= 0` 表示替代名稱
- 萃取腳本未過濾替代名稱，導致：
  1. 同一產品被多次處理
  2. 不同名稱可能分類到不同 category
  3. 同一 ID 的檔案出現在多個分類目錄

**範例**：
```
lnhpd_id: 25611924
├── vitamins_minerals/25611924.md  (SKIN REEJOV)
├── botanicals/25611924.md         (VIT-DERMA)
├── omega_fatty_acids/25611924.md  (DERMA-VIT)
├── specialty/25611924.md          (SKIN PLEX)
└── other/25611924.md              (META-SKIN)
```

**解決方案**：
```python
# extract_ca_lnhpd.py
# 只處理主要名稱（flag_primary_name == 1）
if data.get("flag_primary_name") != 1:
    return {"skip": True, "reason": "non_primary_name"}
```

**教訓**：
> API 回傳的「每筆記錄」不一定對應「一個產品」。
> 需要理解資料模型中的主從關係（如主要名稱 vs 替代名稱）。
> 使用 ID 作為檔名時，需確保 ID 的唯一性。

**預防措施**：
- 在 Layer CLAUDE.md 中記錄 API 的資料模型（一對多關係）
- 萃取腳本中明確處理主從關係
- 驗證時檢查 MD 檔案數是否等於不重複 ID 數

---

### 驗證數據對比（修正前後）

| 指標 | 修正前 | 修正後 |
|------|--------|--------|
| 總行數 | 289,682 | 289,682 |
| 跳過（替代名稱） | 0 | 140,518 |
| MD 檔案數 | 160,566 | 149,153 |
| 不重複 ID 數 | 149,161 | 149,161 |
| 萃取完成率 | 55.4% | 99.9% |
| 有成分 | 82.0% | 81.7% |
| REVIEW_NEEDED | 3.2% | 3.2% |

---

## 文件更新記錄

| 日期 | 更新內容 |
|------|----------|
| 2026-02-04 | 新增：ca_lnhpd 產品名稱重複問題（flag_primary_name）|
| 2026-02-04 | 新增：ca_lnhpd 成分資料整合的設計決策與教訓 |
| 2026-02-04 | 初版：記錄 us_dsld/kr_hff 資料完整性修復過程的教訓 |
