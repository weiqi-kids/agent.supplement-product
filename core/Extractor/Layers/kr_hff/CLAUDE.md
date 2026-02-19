# Layer: kr_hff — 韓國 MFDS 건강기능식품（健康機能食品）

## Layer 定義表

| 項目 | 說明 |
|------|------|
| **Layer name** | kr_hff（韓國健康機能食品） |
| **Engineering function** | 從 MFDS data.go.kr API 擷取韓國健康機能食品產品資料 |
| **Collectable data** | 產品名稱、製造商、品目番號、外觀、用法用量、主要功能、注意事項 |
| **Automation level** | 80% — API 回傳完整資料但韓文欄位需正確處理 |
| **Output value** | 韓國市場健康機能食品資料庫，支援跨國比較 |
| **Risk type** | 韓文翻譯準確度、分類映射（韓國分類體系 → 統一 category） |
| **Reviewer persona** | 資料可信度審核員、領域保守審核員 |
| **WebFetch 策略** | **不使用** — API 已回傳完整結構化資料 |

## API 資訊

- **Base URL**: `https://apis.data.go.kr/1471000/HtfsInfoService03`
- **端點**:
  - `/getHtfsList01` — 產品列表
  - `/getHtfsItem01` — 產品詳情
- **認證**: 需要 data.go.kr 服務金鑰 (`MFDS_API_KEY`)
- **分頁**: `pageNo` (頁碼, 從 1 開始) + `numOfRows` (每頁筆數, 預設 10)
- **回應格式**: XML 預設, 可指定 `type=json`

## .env 設定

```bash
MFDS_API_KEY=...  # data.go.kr 服務金鑰（URL encoded）
```

## 萃取邏輯

### MFDS JSON → Markdown 欄位映射

| Markdown 欄位 | MFDS JSON 路徑 | 說明 |
|---------------|---------------|------|
| `source_id` | `STTEMNT_NO` | 品目製造管理番號 |
| `source_layer` | 固定 `"kr_hff"` | — |
| `source_url` | 組合產生 | data.go.kr 查詢頁面 |
| `market` | 固定 `"kr"` | — |
| `product_name` | `PRDUCT` | 產品名稱（韓文） |
| `brand` | `ENTRPS` | 製造商/業者名稱 |
| `manufacturer` | `ENTRPS` | 同上 |
| `category` | 由 `MAIN_FNCTN` 關鍵字推斷 | 見下方規則 |
| `product_form` | `SUNGSANG` 關鍵字推斷 | 見下方規則 |
| `date_entered` | `REGIST_DT` | 登記日期 |
| `fetched_at` | 萃取時自動產生 | ISO8601 |

### 額外欄位
- `SUNGSANG`: 性狀（外觀描述）
- `SRV_USE`: 用法用量
- `DISTB_PD`: 流通期限
- `MAIN_FNCTN`: 主要功能
- `INTAKE_HINT1`: 攝取注意事項
- `BASE_STANDARD`: 規格基準

## Category 推斷規則

從 `MAIN_FNCTN`（主要功能）關鍵字推斷：

| 韓文關鍵字 | 統一 Category |
|-----------|---------------|
| 비타민, 미네랄, 칼슘, 철, 아연, 마그네슘 | `vitamins_minerals` |
| 인삼, 홍삼, 녹차, 쏘팔메토, 식물 | `botanicals` |
| 단백질, 아미노산, 콜라겐 | `protein_amino` |
| 유산균, 프로바이오틱스, 비피더스 | `probiotics` |
| 오메가, EPA, DHA, 지방산 | `omega_fatty_acids` |
| 운동, 체력, 근력, 스포츠 | `sports_fitness` |
| 多功能複合 | `specialty` |
| 以上皆不符 | `other` |

## Product Form 推斷規則

從 `SUNGSANG`（性狀）關鍵字推斷：

| 韓文關鍵字 | product_form |
|-----------|-------------|
| 정제 (tablet) | `tablet` |
| 캡슐 (capsule) | `capsule` |
| 연질캡슐 (softgel) | `softgel` |
| 분말 (powder) | `powder` |
| 액상, 액제 (liquid) | `liquid` |
| 젤리 (gummy/jelly) | `gummy` |
| 其他 | `other` |

## `[REVIEW_NEEDED]` 觸發規則

### 關鍵欄位定義

| 欄位 | 用途 | 必要性 |
|------|------|--------|
| `STTEMNT_NO` | 唯一識別碼 | 必要 — 缺失則無法產生 `.md` 檔 |
| `PRDUCT` | 產品名稱 | 必要 — 缺失觸發 REVIEW_NEEDED |
| `MAIN_FNCTN` | 主要功能 | 必要 — 缺失觸發 REVIEW_NEEDED |
| `ENTRPS` | 製造商 | 選填 — 缺失不影響萃取 |
| `SUNGSANG` | 性狀/外觀 | 選填 — 缺失不影響萃取 |

### 觸發條件

以下情況**必須**標記 `[REVIEW_NEEDED]`：
1. `PRDUCT` 為空（無產品名稱）
2. `MAIN_FNCTN` 為空（無法推斷 category）

> 若 `STTEMNT_NO` 為空，該記錄無法識別，直接跳過不產生 `.md` 檔。

以下情況**不觸發** `[REVIEW_NEEDED]`：
- ❌ 韓文內容未翻譯 — 系統保留原文
- ❌ category 推斷為 `other` — 可能是功能描述不含標準關鍵字
- ❌ 單一來源資料 — MFDS 為韓國官方監管機關
- ❌ 選填欄位（`ENTRPS`, `SUNGSANG`, `SRV_USE` 等）為空

## 輸出格式

```markdown
---
source_id: "{STTEMNT_NO}"
source_layer: "kr_hff"
source_url: "https://www.data.go.kr/data/15056760/openapi.do"
market: "kr"
product_name: "{PRDUCT}"
brand: "{ENTRPS}"
manufacturer: "{ENTRPS}"
category: "{inferred category}"
product_form: "{inferred product_form}"
date_entered: "{REGIST_DT}"
fetched_at: "{ISO8601 timestamp}"
---

# {PRDUCT}

## 基本資訊
- 製造商：{ENTRPS}
- 劑型：{inferred product_form}
- 市場：韓國
- 品目番號：{STTEMNT_NO}
- 性狀：{SUNGSANG}

## 主要功能
{MAIN_FNCTN}

## 用法用量
{SRV_USE}

## 注意事項
{INTAKE_HINT1}

## 規格基準
{BASE_STANDARD}

## 備註
{映射問題或特殊情況}
```

## 輸出位置

`docs/Extractor/kr_hff/{category}/{STTEMNT_NO}.md`

## 自我審核 Checklist

- [ ] `source_id` 正確對應 STTEMNT_NO
- [ ] 韓文內容完整保留
- [ ] `category` 依關鍵字規則推斷
- [ ] `product_form` 依關鍵字規則推斷
- [ ] frontmatter 格式正確
- [ ] `[REVIEW_NEEDED]` 僅在觸發條件成立時標記

---

## ⚠️ 子代理精簡回報規範

完成後**只輸出一行**：
```
DONE|kr_hff|F:{fetch筆數}|E:{extract筆數}|R:{review筆數}|OK
```

**禁止**：冗長描述、完整 log、韓文內容輸出
