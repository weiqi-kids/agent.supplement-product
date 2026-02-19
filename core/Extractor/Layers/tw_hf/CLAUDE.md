# Layer: tw_hf — 台灣衛福部健康食品資料庫

## Layer 定義表

| 項目 | 說明 |
|------|------|
| **Layer name** | tw_hf（台灣健康食品） |
| **Engineering function** | 從衛福部食藥署「健康食品資料集」API 下載 JSON，轉換為結構化資料 |
| **Collectable data** | 許可證字號、產品名稱、申請商、保健功效、保健功效宣稱 |
| **Automation level** | 100% — 公開 API，無需認證 |
| **Output value** | 台灣官方認證健康食品完整資料庫（555 筆），支援六國比較 |
| **Risk type** | API 結構變更、中文欄位處理 |
| **Reviewer persona** | 資料可信度審核員、領域保守審核員 |
| **WebFetch 策略** | **不使用** — API 已包含完整結構化資料 |

## 資料源資訊

- **來源**: 衛生福利部食品藥物管理署
- **資料集名稱**: 健康食品資料集
- **data.gov.tw ID**: 6951
- **API 端點**: `https://data.fda.gov.tw/opendata/exportDataList.do?method=ExportData&InfoId=19&logType=2`
- **產品數**: 555 筆（截至 2026-02-14）
- **認證**: 免 API Key，公開存取
- **更新頻率**: 每月更新

## API 回傳格式

```json
[
  {
    "許可證字號": "衛署健食字第A00022號",
    "類別": "衛署健食字",
    "中文品名": "波爾Green Time益牙口香糖-薄荷風味",
    "核可日期": "2002/03/25",
    "申請商": "金車股份有限公司",
    "證況": "核可",
    "保健功效相關成分": "木糖醇",
    "保健功效": "牙齒保健功能",
    "保健功效宣稱": "經人體食用研究結果...",
    "警語": null,
    "注意事項": "...",
    "網址": "https://consumer.fda.gov.tw//Food/InfoHealthFoodDetail..."
  }
]
```

## 萃取邏輯

### JSON → Markdown 欄位映射

| Markdown 欄位 | JSON 欄位 | 說明 |
|---------------|----------|------|
| `source_id` | 許可證字號 | 唯一識別（如 衛署健食字第A00022號） |
| `source_layer` | 固定 `"tw_hf"` | — |
| `source_url` | 網址 | API 提供的產品詳細頁連結 |
| `market` | 固定 `"tw"` | — |
| `product_name` | 中文品名 | 產品名稱 |
| `brand` | 申請商 | 申請商即品牌 |
| `manufacturer` | 申請商 | 同上 |
| `category` | 由 保健功效 推斷 | 見下方規則 |
| `product_form` | 由 中文品名 推斷 | 見下方規則 |
| `date_entered` | 核可日期 | YYYY-MM-DD 格式 |
| `fetched_at` | 萃取時自動產生 | ISO8601 |

## Category 推斷規則

從 `保健功效` 欄位關鍵字推斷：

| 中文關鍵字 | 統一 Category |
|-----------|---------------|
| 調節血脂、血脂、膽固醇 | `omega_fatty_acids` |
| 骨質、牙齒、鈣質 | `vitamins_minerals` |
| 胃腸、益生菌、腸道 | `probiotics` |
| 護肝、體脂肪、茶多酚、抗氧化 | `botanicals` |
| 免疫、血糖、抗疲勞 | `specialty` |
| 其他 | `other` |

> 若同時符合多個分類，歸入 `specialty`（複合功效）

## Product Form 推斷規則

從 `中文品名` 推斷：

| 關鍵字 | product_form |
|--------|-------------|
| 錠、片 | `tablet` |
| 膠囊 | `capsule` |
| 粉、顆粒 | `powder` |
| 飲、飲料、液、乳 | `liquid` |
| 軟糖 | `gummy` |
| 凝膠、果凍 | `gummy` |
| 以上皆無 | `other` |

## `[REVIEW_NEEDED]` 觸發規則

以下情況**必須**標記 `[REVIEW_NEEDED]`：
1. 許可證字號為空
2. 中文品名為空
3. 保健功效為空

以下情況**不觸發** `[REVIEW_NEEDED]`：
- ❌ 保健功效宣稱為空 — 部分早期產品未提供
- ❌ category 推斷為 `other` — 功效可能不含標準關鍵字

## 輸出格式

```markdown
---
source_id: "{許可證字號}"
source_layer: "tw_hf"
source_url: "https://consumer.fda.gov.tw/Food/InfoHealthFood.aspx?nodeID=162"
market: "tw"
product_name: "{中文品名}"
brand: "{申請商名稱}"
manufacturer: "{申請商名稱}"
category: "{inferred category}"
product_form: "{inferred product_form}"
date_entered: "{核可日期 YYYY-MM-DD}"
fetched_at: "{ISO8601 timestamp}"
---

# {中文品名}

## 基本資訊
- 申請商：{申請商名稱}
- 劑型：{inferred product_form}
- 市場：台灣
- 許可證字號：{許可證字號}

## 保健功效成分
{保健功效相關成分}

## 保健功效
{保健功效}

## 保健功效宣稱
{保健功效宣稱}

## 注意事項
{注意事項}
```

## 輸出位置

`docs/Extractor/tw_hf/{category}/{許可證字號}.md`

> 許可證字號中的特殊字元會被轉換為底線

## 自我審核 Checklist

- [ ] `source_id` 正確對應許可證字號
- [ ] 中文內容完整保留
- [ ] `category` 依保健功效關鍵字規則推斷
- [ ] `product_form` 依中文品名推斷
- [ ] frontmatter 格式正確
- [ ] `[REVIEW_NEEDED]` 僅在觸發條件成立時標記

---

## ⚠️ 子代理精簡回報規範

完成後**只輸出一行**：
```
DONE|tw_hf|F:{fetch筆數}|E:{extract筆數}|R:{review筆數}|OK
```

**禁止**：冗長描述、完整 log、中文內容輸出
