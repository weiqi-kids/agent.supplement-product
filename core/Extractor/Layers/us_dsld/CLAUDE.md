# Layer: us_dsld — 美國 NIH DSLD 膳食補充品標籤資料庫

## Layer 定義表

| 項目 | 說明 |
|------|------|
| **Layer name** | us_dsld（美國 DSLD） |
| **Engineering function** | 從 NIH DSLD API 擷取美國膳食補充品標籤資料 |
| **Collectable data** | 產品名稱、品牌、成分、劑型、宣稱、上市狀態 |
| **Automation level** | 95% — API 回傳結構化資料，僅少數邊界情況需人工確認 |
| **Output value** | 美國市場完整產品資料庫，支援成分分析、品牌追蹤、跨國比較 |
| **Risk type** | 分類錯誤（productType → category 映射）、資料延遲 |
| **Reviewer persona** | 資料可信度審核員、領域保守審核員 |
| **WebFetch 策略** | **不使用** — API 已回傳完整結構化資料 |

## 資料來源

### Bulk Download（推薦）

- **URL**: `https://api.ods.od.nih.gov/dsld/s3/data/DSLD-full-database-JSON.zip`
- **格式**: ZIP 壓縮檔，內含個別產品 JSON 檔案（每個產品一個檔案）
- **總筆數**: 214,780+（完整資料庫）
- **檔案大小**: ~557 MB (ZIP) / ~2.4 GB (解壓後)
- **認證**: 免認證

這是取得完整 DSLD 資料庫的推薦方式，可繞過 API 的分頁限制。

### API（備用）

- **Base URL**: `https://api.ods.od.nih.gov/dsld/v9/search-filter`
- **認證**: 免 API Key
- **分頁**: `from` (offset, 從 0 開始) + `size` (每頁筆數, 預設 1000)
- **回應格式**: `{hits: [{_id, _source: {...}}], stats: {count}}`

**⚠️ API 限制**:
- Elasticsearch 深度分頁限制：`max_result_window=10000`，超過此 offset 返回空結果
- 過濾參數（`startYear`、`endYear`、`productType`）實測無效
- 建議僅用於測試或查詢單一產品，不建議用於全量擷取

## 萃取邏輯

### DSLD JSON → Markdown 欄位映射

| Markdown 欄位 | DSLD JSON 路徑 | 說明 |
|---------------|---------------|------|
| `source_id` | `dsld_id` | DSLD 產品 ID |
| `source_layer` | 固定 `"us_dsld"` | — |
| `source_url` | `https://dsld.od.nih.gov/label/{dsld_id}` | 組合產生 |
| `market` | 固定 `"us"` | — |
| `product_name` | `fullName` | 產品完整名稱 |
| `brand` | `brandName` | 品牌名稱 |
| `manufacturer` | `brandName` | DSLD 不區分品牌與製造商，使用品牌名 |
| `category` | 由 `productType.langualCode` 映射 | 見下方映射表 |
| `product_form` | `physicalState.langualCodeDescription` 映射 | 見下方映射表 |
| `date_entered` | `entryDate` | 格式 YYYY-MM-DD |
| `fetched_at` | 萃取時自動產生 | ISO8601 |

### 成分欄位

從 `allIngredients` 陣列提取：
- 每個成分輸出：`- {name}（{ingredientGroup}）`
- 若成分有 `notes`，附加在後方

### 宣稱欄位

從 `claims` 陣列提取：
- 每個宣稱輸出：`- {langualCodeDescription}`

## Category 映射規則

DSLD `productType.langualCode` → 統一 category：

| DSLD langualCode | DSLD Description | 統一 Category |
|-----------------|------------------|---------------|
| `A1299` | Mineral | `vitamins_minerals` |
| `A1302` | Vitamin | `vitamins_minerals` |
| `A1305` | Amino acid/Protein | `protein_amino` |
| `A1306` | Botanical | `botanicals` |
| `A1309` | Non-Nutrient/Non-Botanical | `other` |
| `A1310` | Fat/Fatty Acid | `omega_fatty_acids` |
| `A1315` | Multi-Vitamin and Mineral (MVM) | `vitamins_minerals` |
| `A1317` | Botanical with Nutrients | `botanicals` |
| `A1325` | Other Combinations | `specialty` |
| `A1326` | Fiber and Other Nutrients | `other` |
| 其他 / 未知 | — | `other` |

> 若遇到未列出的 langualCode，歸類為 `other` 並在 notes 標註。
> 映射表基於 2026-01-27 API 實測驗證（200 筆樣本）。

## Product Form 映射規則

DSLD `physicalState.langualCodeDescription` → 統一 product_form：

| DSLD Description | product_form |
|-----------------|-------------|
| Tablet or Pill | `tablet` |
| Capsule | `capsule` |
| Softgel | `softgel` |
| Powder | `powder` |
| Liquid | `liquid` |
| Gummy | `gummy` |
| 其他 | `other` |

> 以 contains 方式匹配（不區分大小寫）。

## `[REVIEW_NEEDED]` 觸發規則

以下情況**必須**標記 `[REVIEW_NEEDED]`：
1. `productType` 為 null 或空值（無法判定 category）
2. `fullName` 為空（缺少產品名稱）
3. `allIngredients` 為空陣列（無成分資料）
4. category 映射落入 `other` 但成分列表顯示應歸入其他分類

以下情況**不觸發** `[REVIEW_NEEDED]`：
- ❌ 品牌名不熟悉 — 這不影響資料準確性
- ❌ 僅單一資料來源 — DSLD 是美國政府官方資料庫
- ❌ `offMarket` 為 1 — 產品已下市是正常資料狀態
- ❌ 成分缺少劑量資訊 — DSLD 標籤資料不一定包含劑量

## 輸出格式

```markdown
---
source_id: "{dsld_id}"
source_layer: "us_dsld"
source_url: "https://dsld.od.nih.gov/label/{dsld_id}"
market: "us"
product_name: "{fullName}"
brand: "{brandName}"
manufacturer: "{brandName}"
category: "{mapped category}"
product_form: "{mapped product_form}"
date_entered: "{entryDate}"
fetched_at: "{ISO8601 timestamp}"
---

# {fullName}

## 基本資訊
- 品牌：{brandName}
- 劑型：{mapped product_form}
- 市場：美國
- 上市狀態：{on/off market}
- 淨含量：{netContents display}

## 成分
- {ingredient name}（{ingredientGroup}）
...

## 宣稱
- {claim description}
...

## 備註
{若有映射問題或特殊情況，在此標註}
```

## 輸出位置

`docs/Extractor/us_dsld/{category}/{dsld_id}.md`

## 執行流程

### 完整流程（fetch → 萃取 → update）

```bash
# 1. Fetch: 下載完整資料庫
./core/Extractor/Layers/us_dsld/fetch.sh

# 2. 萃取: 轉換為 .md 檔
python3 scripts/extract_us_dsld.py

# 3. Update: 寫入 Qdrant（自動跳過已存在）
./core/Extractor/Layers/us_dsld/update.sh
```

### Fetch 詳細流程

`fetch.sh` 預設使用 Bulk Download 模式：

```
1. 下載 DSLD-full-database-JSON.zip (~557 MB)
2. 解壓縮 214,780 個 JSON 檔案 (~2.4 GB)
3. 執行 convert_dsld_bulk_to_jsonl.py 轉換為 JSONL
4. 若有前次資料，執行 diff_dsld.py 比對差異
5. 更新 latest.jsonl 符號連結
6. 清理暫存檔案（ZIP、解壓目錄）
```

### 增量更新機制

系統在兩個層級實現增量更新：

#### 層級 1: Fetch 差異比對

```
diff_dsld.py 比對新舊 JSONL：
├── 使用 dsld_id 作為唯一識別碼
├── 使用 entryDate 判斷資料是否更新
├── 輸出 delta.jsonl（只含新增/更新的產品）
└── 輸出 summary.json（統計摘要）
```

#### 層級 2: Qdrant 去重

```
update.sh 批次處理時：
├── 查詢 Qdrant 已存在的 UUID（基於 us_dsld-{source_id}）
├── 跳過已存在的產品 → SKIPPED
└── 只處理新產品 → embedding → upsert
```

### 參數說明

| 參數 | 說明 |
|------|------|
| `./fetch.sh` | 預設使用 Bulk Download |
| `./fetch.sh --full` | 全量更新（跳過差異比對） |
| `./fetch.sh --api` | 使用舊版 API（⚠️ 限制 10,000 筆） |
| `python3 extract_us_dsld.py` | 使用 latest.jsonl，跳過已存在 |
| `python3 extract_us_dsld.py --force` | 強制覆蓋所有 .md 檔 |
| `python3 extract_us_dsld.py --delta <file>` | 只處理差異檔案 |

### 相關腳本

| 腳本 | 用途 |
|------|------|
| `scripts/convert_dsld_bulk_to_jsonl.py` | Bulk JSON → JSONL 轉換 |
| `scripts/extract_us_dsld.py` | JSONL → Markdown 萃取 |
| `scripts/diff_dsld.py` | 新舊 JSONL 差異比對 |

## 自我審核 Checklist

萃取完成後，逐項確認：

- [ ] `source_id` 正確對應 DSLD _id
- [ ] `category` 依映射表正確分類
- [ ] `product_form` 依映射表正確轉換
- [ ] 成分列表完整（與原始 JSON 的 allIngredients 一致）
- [ ] 宣稱列表完整（與原始 JSON 的 claims 一致）
- [ ] frontmatter 格式正確（YAML 語法）
- [ ] `[REVIEW_NEEDED]` 僅在觸發條件成立時標記
- [ ] 檔案寫入正確的 category 子目錄
