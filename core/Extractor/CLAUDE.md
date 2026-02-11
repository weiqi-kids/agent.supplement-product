# Extractor 角色說明 — 保健食品產品情報

## 職責

Extractor 負責從外部資料源擷取（fetch）原始資料，並萃取（extract）為結構化 Markdown 檔案。

## 資料流

```
外部資料源（API / RSS / 檔案下載）
  → fetch.sh 下載原始資料 → docs/Extractor/{layer}/raw/*.jsonl
  → scripts/extract_{layer}.py 萃取 → docs/Extractor/{layer}/{category}/*.md
  → update.sh 寫入 Qdrant + 檢查 REVIEW_NEEDED
```

## 萃取腳本

每個 Layer 都有對應的 Python 萃取腳本：

| Layer | 腳本 | 特殊參數 |
|-------|------|---------|
| ca_lnhpd | `scripts/extract_ca_lnhpd.py` | `--delta` 增量模式 |
| jp_fnfc | `scripts/extract_jp_fnfc.py` | — |
| jp_foshu | `scripts/extract_jp_foshu.py` | — |
| kr_hff | `scripts/extract_kr_hff.py` | — |
| us_dsld | `scripts/extract_us_dsld.py` | — |
| tw_hf | `scripts/extract_tw_hf.py` | — |
| pubmed | `scripts/extract_pubmed.py` | `--topic` 指定主題 |

### 去重機制

萃取腳本內建去重邏輯：
- 預設跳過已存在的 `.md` 檔（依 `source_id` 判斷）
- 使用 `--force` 或 `--delta` 強制覆蓋

### 備用方案（無腳本時）

若 `scripts/extract_{layer}.py` 不存在，改用 Claude 逐行處理：

```
⛔ 禁止使用 Read 工具直接讀取 .jsonl 檔案（可能數百 KB 至數 MB）

✅ wc -l < {jsonl_file}           → 取得總行數
✅ sed -n '{N}p' {jsonl_file}     → 逐行讀取
✅ 每行獨立交由一個 Task 子代理    → 透過 Write tool 寫出 .md 檔
```

## 統一 Markdown 輸出格式

所有 Layer 萃取後的 .md 檔使用統一結構：

```markdown
---
source_id: "{API 原始 ID}"
source_layer: "{layer_name}"
source_url: "{連結}"
market: "{us|kr|ca|jp|th}"
product_name: "{產品名稱}"
brand: "{品牌}"
manufacturer: "{製造商}"
category: "{category enum value}"
product_form: "{劑型：tablet/capsule/powder/liquid/softgel/gummy/other}"
date_entered: "{產品進入資料庫的日期 YYYY-MM-DD}"
fetched_at: "{擷取時間 ISO8601}"
---

# {product_name}

## 基本資訊
- 品牌：{brand}
- 製造商：{manufacturer}
- 劑型：{product_form}
- 市場：{market}

## 成分
{ingredients list — 名稱、劑量、DV%（如有）}

## 宣稱
{claims/statements list}

## 備註
{notes — 包含降級說明、特殊標記等}
```

> frontmatter 用於 Qdrant payload 結構化欄位。正文用於 embedding 和人工閱讀。

## 統一 Category Enum

| Category Key | 中文 | 判定條件 |
|-------------|------|---------|
| `vitamins_minerals` | 維生素與礦物質 | 主成分為維生素或礦物質 |
| `botanicals` | 植物萃取 | 主成分為草本/植物來源 |
| `protein_amino` | 蛋白質與胺基酸 | 乳清蛋白、BCAA、膠原蛋白等 |
| `probiotics` | 益生菌 | 含活菌株 |
| `omega_fatty_acids` | Omega 脂肪酸 | 魚油、亞麻籽油、DHA/EPA |
| `specialty` | 特殊配方 | 複方、針對特定機能 |
| `sports_fitness` | 運動保健 | 肌酸、電解質、運動前後補充 |
| `other` | 其他 | 無法歸類的品項 |

> **嚴格限制：category 只能使用上述英文值，不可自行新增。**

## WebFetch 補充機制

API 類 Layer 通常不需要 WebFetch（API 回傳完整資料）。
RSS 類 Layer 可能需要 WebFetch 補充不完整的 description。

各 Layer 的 CLAUDE.md 定義 WebFetch 策略：
- **必用**：一律使用 WebFetch 抓取原始頁面
- **按需**：description 不足時才使用
- **不使用**：資料源已包含完整結構化資料

WebFetch 失敗不阻斷萃取流程，應降級並在 notes 標註。

## `[REVIEW_NEEDED]` 通用原則

| 概念 | 含義 | 標記方式 |
|------|------|----------|
| `[REVIEW_NEEDED]` | 萃取結果**可能有誤** | 在 .md 檔開頭加上 |
| `confidence: 低` | 資料來源有**結構性限制** | 在 confidence 欄位反映 |

> 兩者不等價。子任務不可自行擴大判定範圍。
> 子任務必須嚴格遵循各 Layer CLAUDE.md 定義的觸發規則。
