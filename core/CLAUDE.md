# 系統維護指令

本文件在 `core/` 目錄下操作時自動載入。

## 維護操作

### Layer 管理

#### 新增 Layer

使用者說：「新增一個 {名稱} Layer，資料來源是 {URL}，類型是 {RSS/API/...}」

執行流程：
1. 與使用者確認 Layer 定義表
2. 確認 category enum 清單（嚴格限定）
3. 確認 WebFetch 策略
4. 確認 `[REVIEW_NEEDED]` 觸發規則
5. 建立目錄 `core/Extractor/Layers/{layer_name}/`
6. 產生 `fetch.sh`、`update.sh`、`CLAUDE.md`
7. 建立 `docs/Extractor/{layer_name}/` 及 category 子目錄
8. 更新 `docs/explored.md`「已採用」表格
9. 告知使用者需要在 `.env` 補充的設定（若有）

#### 修改 Layer

1. 讀取 `core/Extractor/Layers/{layer_name}/CLAUDE.md` 確認現況
2. 與使用者確認修改內容
3. 修改對應檔案
4. 若 category enum 有變動，確認不會影響既有 docs 分類
5. 列出影響範圍（哪些 Mode 會受影響）

#### 刪除 / 暫停 Layer

- 刪除前列出依賴此 Layer 的所有 Mode
- 暫停：建立 `.disabled` 標記檔
- 執行流程自動跳過帶有 `.disabled` 的 Layer

### Mode 管理

與 Layer 管理邏輯類似，在 `core/Narrator/Modes/` 下操作。

### 資料源管理

使用者說：「我找到一個新的資料源 {URL}」

1. 測試連線（curl 確認可達）
2. 若為 RSS，驗證格式；若為 API，測試端點
3. 更新 `docs/explored.md`「評估中」表格
4. 詢問使用者要建立新 Layer 還是加入現有 Layer

## 統一 Category Enum

所有 Layer 共用同一組 category：

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

> category 不可自行新增，需與使用者確認後寫入 CLAUDE.md。

## Qdrant Payload Schema

```json
{
  "source_id": "string — API 原始產品 ID",
  "source_layer": "string — layer name",
  "source_url": "string — 產品頁面連結",
  "market": "string — us/kr/ca/jp/th",
  "product_name": "string",
  "brand": "string",
  "manufacturer": "string",
  "category": "string — category enum",
  "product_form": "string — 劑型",
  "ingredients": ["string array — 主要成分名稱清單"],
  "claims": ["string array — 宣稱語句清單"],
  "date_entered": "string — YYYY-MM-DD",
  "fetched_at": "string — ISO8601"
}
```

去重 key：`{source_layer}-{source_id}` → 透過 `_qdrant_id_to_uuid` 轉為 UUID

## Layer 清單

### 產品資料 Layer

| Layer | 資料來源 | 市場 | 狀態 |
|-------|----------|------|------|
| `us_dsld` | 美國膳食補充劑標示資料庫 | 🇺🇸 US | ✅ 啟用 |
| `ca_lnhpd` | 加拿大天然健康產品資料庫 | 🇨🇦 CA | ✅ 啟用 |
| `kr_hff` | 韓國健康機能食品資料庫 | 🇰🇷 KR | ✅ 啟用 |
| `jp_fnfc` | 日本機能性表示食品資料庫 | 🇯🇵 JP | ✅ 啟用 |
| `jp_foshu` | 日本特定保健用食品資料庫 | 🇯🇵 JP | ✅ 啟用 |
| `tw_hf` | 台灣衛福部健康食品資料庫 | 🇹🇼 TW | ✅ 啟用 |
| `th_fda` | 泰國 FDA 健康食品資料庫 | 🇹🇭 TH | ❌ 已禁用 |

### 學術文獻 Layer

| Layer | 資料來源 | 說明 | 狀態 |
|-------|----------|------|------|
| `pubmed` | PubMed 學術文獻資料庫 | 主題相關研究文獻 | ✅ 啟用 |

### 交互作用 Layer

| Layer | 資料來源 | 說明 | 狀態 |
|-------|----------|------|------|
| `dhi` | PubMed | Drug-Herb/Supplement Interactions | ✅ 啟用 |
| `dfi` | PubMed | Drug-Food Interactions | ✅ 啟用 |
| `ddi` | PubMed | Drug-Drug Interactions | ✅ 啟用 |
| `ingredient_map` | RxNorm API | 成分標準化對照表 | ⏸️ 暫停 |

## Mode 清單

| Mode | 輸出位置 | 報告週期 | 狀態 |
|------|----------|----------|------|
| `market_snapshot` | `docs/Narrator/market_snapshot/` | 週報 | ✅ 啟用 |
| `ingredient_radar` | `docs/Narrator/ingredient_radar/` | 月報 | ✅ 啟用 |
| `topic_tracking` | `docs/Narrator/topic_tracking/{topic}/` | 月報 | ✅ 啟用 |
| `literature_review` | `docs/Narrator/literature_review/{topic}/` | 月報 | ✅ 啟用 |

> 交互作用資料已整合至選購指南，由 `scripts/update_guide_interactions.py` 自動更新。
