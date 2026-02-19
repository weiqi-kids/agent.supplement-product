# Layer: ca_lnhpd — 加拿大 Health Canada LNHPD 天然保健品資料庫

## Layer 定義表

| 項目 | 說明 |
|------|------|
| **Layer name** | ca_lnhpd（加拿大 LNHPD） |
| **Engineering function** | 從 Health Canada LNHPD API 擷取已授權天然保健品資料 |
| **Collectable data** | 產品名稱、公司名稱、劑型、授權編號 (NPN)、授權日期、成分清單（含劑量） |
| **Automation level** | 95% — 產品基本資訊完整，成分資料可透過 `--with-ingredients` 同步下載 |
| **Output value** | 加拿大市場產品資料庫（含成分），支援跨國比較與成分分析 |
| **Risk type** | 分類準確度（無原生 productType 欄位，依關鍵字推斷） |
| **Reviewer persona** | 資料可信度審核員、幻覺風險審核員 |
| **WebFetch 策略** | **不使用** — API 已回傳結構化資料 |

## API 資訊

| 端點 | URL | 說明 |
|------|-----|------|
| **產品 (Bulk)** | `https://health-products.canada.ca/api/natural-licences/ProductLicence/?lang=en&type=json` | 完整 JSON 陣列（~139MB, ~120K 產品），無分頁 |
| **成分** | `https://health-products.canada.ca/api/natural-licences/medicinalingredient/?lang=en&type=json&page={N}&limit=1000` | 分頁 API（~810K 筆） |

- **認證**: 免 API Key
- **產品總數**: ~120,000+
- **成分總數**: ~810,000+

## 擷取策略

### 產品資料（必要）
- 呼叫 ProductLicence bulk 端點
- 回應為 JSON 陣列，需較長 timeout（600s）
- 以 `jq -c '.[]'` 轉為 JSONL

### 成分資料（選擇性）
- 透過 `--with-ingredients` 旗標啟用
- 使用 `scripts/fetch_lnhpd_ingredients.py` 分頁下載
- 自動重試（3 次，指數退避）+ 斷點續傳
- 存為獨立 JSONL 檔案（`ingredients-YYYY-MM-DD.jsonl`）
- 萃取時以 `--ingredients` 參數指定，由 `lnhpd_id` 關聯

## 增量更新機制

LNHPD 資料量龐大（~290K 筆），支援增量更新以減少處理時間。

### 差異偵測

使用 `revised_date` 欄位比對新舊資料：
- **新增**：新檔案有、舊檔案無的 `lnhpd_id`
- **更新**：`revised_date` 變更的記錄
- **未變**：`revised_date` 相同的記錄
- **移除**：舊檔案有、新檔案無的 `lnhpd_id`

### 使用流程

```bash
# === 增量更新（預設，建議日常使用）===
./core/Extractor/Layers/ca_lnhpd/fetch.sh

# 若有差異，會產生 delta 檔案：
python3 scripts/extract_ca_lnhpd.py --delta \
  --ingredients docs/Extractor/ca_lnhpd/raw/latest-ingredients.jsonl \
  docs/Extractor/ca_lnhpd/raw/delta-$(date +%Y-%m-%d)/delta.jsonl

# === 全量更新（重建資料庫時使用）===
./core/Extractor/Layers/ca_lnhpd/fetch.sh --full
python3 scripts/extract_ca_lnhpd.py \
  --ingredients docs/Extractor/ca_lnhpd/raw/latest-ingredients.jsonl \
  docs/Extractor/ca_lnhpd/raw/products-$(date +%Y-%m-%d).jsonl

# === 首次/含成分全量更新 ===
./core/Extractor/Layers/ca_lnhpd/fetch.sh --full --with-ingredients
python3 scripts/extract_ca_lnhpd.py \
  --ingredients docs/Extractor/ca_lnhpd/raw/ingredients-$(date +%Y-%m-%d).jsonl \
  docs/Extractor/ca_lnhpd/raw/products-$(date +%Y-%m-%d).jsonl
```

### 建議更新頻率

| 資料類型 | 建議頻率 | 說明 |
|----------|----------|------|
| **產品** | 每週增量更新 | 新產品核准較頻繁 |
| **成分** | 每月全量更新 | 成分資料變動較少 |

### fetch.sh 參數

| 參數 | 說明 |
|------|------|
| （無） | 增量模式：與 `latest.jsonl` 比對，只輸出差異 |
| `--full` | 全量模式：處理所有產品，不做差異比對 |
| `--with-ingredients` | 同時下載成分資料（約 810K 筆，耗時約 7-10 分鐘） |
| `--limit N` | 限制筆數（測試用） |
| `--timeout N` | 下載超時秒數（預設 600） |

### extract 參數

| 參數 | 說明 |
|------|------|
| （無） | 一般模式：跳過已存在的 .md 檔 |
| `--force`, `-f` | 強制覆蓋已存在的檔案 |
| `--delta`, `-d` | Delta 模式：自動啟用 `--force` |
| `--ingredients`, `-i` | 成分 JSONL 檔案路徑，整合成分資料 |

### 輸出檔案結構

```
docs/Extractor/ca_lnhpd/raw/
├── latest.jsonl                   # symlink → 最新完整產品 JSONL
├── latest-ingredients.jsonl       # symlink → 最新完整成分 JSONL
├── products-2026-02-02.jsonl      # 完整產品資料
├── ingredients-2026-02-02.jsonl   # 完整成分資料（~810K 筆）
├── delta-2026-02-03/              # 差異目錄
│   ├── delta.jsonl                # 需處理的記錄（新增+更新）
│   ├── new_ids.txt                # 新增的 lnhpd_id
│   ├── updated_ids.txt            # 更新的 lnhpd_id
│   ├── removed_ids.txt            # 移除的 lnhpd_id
│   └── summary.json               # 差異統計摘要
└── .last_fetch                    # 最後擷取日期
```

## 萃取邏輯

### LNHPD JSON → Markdown 欄位映射

| Markdown 欄位 | LNHPD JSON 路徑 | 說明 |
|---------------|-----------------|------|
| `source_id` | `lnhpd_id` | LNHPD 內部 ID |
| `source_layer` | 固定 `"ca_lnhpd"` | — |
| `source_url` | `https://health-products.canada.ca/lnhpd-bdpsnh/info.do?licence={licence_number}&lang=en` | 組合產生 |
| `market` | 固定 `"ca"` | — |
| `product_name` | `product_name` | 產品名稱 |
| `brand` | `company_name` | LNHPD 無獨立品牌欄位 |
| `manufacturer` | `company_name` | 公司名稱 |
| `category` | 由產品名稱關鍵字推斷 | 見下方規則 |
| `product_form` | `dosage_form` 映射 | 見下方映射表 |
| `date_entered` | `licence_date` | 授權日期 YYYY-MM-DD |
| `fetched_at` | 萃取時自動產生 | ISO8601 |

### 額外欄位（LNHPD 特有）
- `licence_number`: NPN 編號
- `flag_product_status`: 1=有效, 0=無效
- `sub_submission_type_desc`: 申請類型

## Category 推斷規則

LNHPD 無 productType 欄位，依產品名稱關鍵字推斷：

| 關鍵字 | 統一 Category |
|--------|---------------|
| vitamin, vit, multi-vitamin, multivitamin | `vitamins_minerals` |
| mineral, calcium, iron, zinc, magnesium, selenium | `vitamins_minerals` |
| herbal, herb, botanical, ginseng, echinacea, turmeric, St. John's | `botanicals` |
| protein, amino, collagen, BCAA, whey | `protein_amino` |
| probiotic, lactobacillus, bifidobacterium | `probiotics` |
| omega, fish oil, DHA, EPA, flax | `omega_fatty_acids` |
| sport, creatine, electrolyte, pre-workout | `sports_fitness` |
| 含多個上述分類的關鍵字 | `specialty` |
| 以上皆不符 | `other` |

> 以 contains 方式匹配（不區分大小寫），優先匹配順序：probiotics > omega > botanicals > vitamins_minerals > protein_amino > sports_fitness > specialty > other。
> 若名稱匹配多個分類，歸入 `specialty`。

## Product Form 映射規則

| LNHPD dosage_form | product_form |
|-------------------|-------------|
| Tablet | `tablet` |
| Capsule | `capsule` |
| Softgel | `softgel` |
| Powder | `powder` |
| Liquid | `liquid` |
| Gummy | `gummy` |
| Cream, Ointment, Lotion | `other` |
| 其他 | `other` |

## 資料過濾規則

### 非主要名稱產品

LNHPD API 回傳的記錄中，`flag_primary_name` 欄位標示該記錄是否為產品的主要名稱：
- `flag_primary_name = 1`：主要名稱，產生 `.md` 檔
- `flag_primary_name = 0`：別名/副品牌，**自動跳過不處理**

> 同一產品可能有多個名稱記錄，僅保留主要名稱以避免重複。

## `[REVIEW_NEEDED]` 觸發規則

以下情況**必須**標記 `[REVIEW_NEEDED]`：
1. `product_name` 為空
2. `dosage_form` 為空
3. category 推斷為 `other` 但名稱含保健食品相關詞彙
4. `flag_product_status` 欄位遺失

以下情況**不觸發** `[REVIEW_NEEDED]`：
- ❌ 缺少成分資料 — 成分需額外 API 呼叫，不影響產品基本資訊
- ❌ category 為 `other` 且名稱無保健食品關鍵字 — 可能是藥用軟膏等非口服品
- ❌ `flag_product_status` 為 0 — 授權失效是正常狀態
- ❌ `flag_primary_name` 為 0 — 非主要名稱記錄直接跳過，不產生 `.md` 檔

## 輸出格式

```markdown
---
source_id: "{lnhpd_id}"
source_layer: "ca_lnhpd"
source_url: "https://health-products.canada.ca/lnhpd-bdpsnh/info.do?licence={licence_number}&lang=en"
market: "ca"
product_name: "{product_name}"
brand: "{company_name}"
manufacturer: "{company_name}"
category: "{inferred category}"
product_form: "{mapped product_form}"
date_entered: "{licence_date}"
fetched_at: "{ISO8601 timestamp}"
---

# {product_name}

## 基本資訊
- 公司：{company_name}
- 劑型：{mapped product_form}
- 市場：加拿大
- NPN：{licence_number}
- 授權狀態：{有效/無效}
- 授權日期：{licence_date}

## 成分
- Vitamin D: 400.0 IU（Cholecalciferol）
- Vitamin C: 500.0 mg（Ascorbic acid）
{若無成分資料：「成分資料需額外擷取（參見 MedicinalIngredient API）」}

## 宣稱
{LNHPD 產品基本資訊不含宣稱，標註「參見 Health Canada 產品頁面」}

## 備註
{映射問題或特殊情況}
```

## 輸出位置

`docs/Extractor/ca_lnhpd/{category}/{lnhpd_id}.md`

## 自我審核 Checklist

- [ ] `source_id` 正確對應 lnhpd_id
- [ ] `licence_number` 正確（NPN 格式）
- [ ] `category` 依關鍵字規則推斷
- [ ] `product_form` 依映射表正確轉換
- [ ] frontmatter 格式正確（YAML 語法）
- [ ] `[REVIEW_NEEDED]` 僅在觸發條件成立時標記
- [ ] 檔案寫入正確的 category 子目錄

---

## ⚠️ 子代理精簡回報規範

完成後**只輸出一行**：

```
DONE|ca_lnhpd|F:{fetch筆數}|E:{extract筆數}|R:{review筆數}|OK
```

**禁止**：冗長描述、完整 log、category 細項統計
