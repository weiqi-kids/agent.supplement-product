# Layer: ingredient_map — 成分標準化對照表

## Layer 定義表

| 項目 | 說明 |
|------|------|
| **Layer name** | ingredient_map（成分標準化） |
| **Engineering function** | 萃取所有產品成分並透過 RxNorm API 標準化名稱 |
| **Collectable data** | 成分名稱、RxNorm ID、別名、分類、複合成分 |
| **Automation level** | 80% — RxNorm API 自動化 + 人工策展高頻成分 |
| **Output value** | 統一成分識別碼，支援跨 Layer 成分匹配與交互作用分析 |
| **Risk type** | API 匹配失敗、成分名稱歧義、複合成分拆解錯誤 |
| **Reviewer persona** | 藥學專家、成分標準化審核員 |
| **WebFetch 策略** | **不使用** — 使用 RxNorm API |

## 資料源資訊

- **主要來源**: 既有產品 Layer（us_dsld, ca_lnhpd, kr_hff, jp_fnfc, jp_foshu, tw_hf）
- **標準化 API**: RxNorm (NLM)
- **API 文件**: https://lhncbc.nlm.nih.gov/RxNav/APIs/index.html
- **認證**: 免費，無需 API Key
- **速率限制**: 20 requests/second

## 設計原則

1. **先萃取再標準化**：從所有產品 .md 萃取成分，再批次查詢 RxNorm
2. **模糊匹配**：使用 `/approximateTerm` API 處理拼寫差異
3. **別名累積**：每次發現新別名即更新對應成分檔案
4. **多語言對應**：日文（ビタミン）、韓文（비타민）、中文（維生素）皆可對應

## 萃取策略

### Step 1: 從產品萃取成分清單

```bash
# 從所有產品 .md 萃取成分區塊
grep -h "^- " docs/Extractor/*/[!raw]*/*.md | \
  grep -v "^\- 品牌\|^\- 製造商\|^\- 劑型\|^\- 市場" | \
  sort | uniq -c | sort -rn > raw/ingredient_frequency.txt
```

### Step 2: RxNorm API 標準化

```bash
# 使用 approximateTerm 查詢
GET https://rxnav.nlm.nih.gov/REST/approximateTerm.json
  ?term={ingredient_name}
  &maxEntries=3

# 使用 findRxcuiByString 精確查詢
GET https://rxnav.nlm.nih.gov/REST/rxcui.json
  ?name={ingredient_name}
```

### Step 3: 建立標準化檔案

每個標準化成分產出一個 .md 檔案。

## 輸出格式

```markdown
---
source_id: "{ingredient_slug}"
source_layer: "ingredient_map"
source_url: "https://rxnav.nlm.nih.gov/REST/rxcui/{rxnorm_id}"
standard_name: "{標準英文名稱}"
standard_name_zh: "{標準中文名稱}"
rxnorm_id: "{RxNorm RXCUI}"
aliases:
  - "{別名1}"
  - "{別名2}"
  - "{日文名}"
  - "{韓文名}"
category: "{ingredient_category}"
contains: ["{子成分1}", "{子成分2}"]  # 僅複合成分
confidence: "{high|medium|low}"
fetched_at: "{ISO8601}"
---

# {standard_name}

## 基本資訊
- 標準名稱：{standard_name}
- 中文名稱：{standard_name_zh}
- RxNorm ID：{rxnorm_id}
- 分類：{category}
- 匹配信心度：{confidence}

## 別名
{aliases list — 各語言版本}

## 複合成分
{contains list — 如 Fish Oil 包含 EPA, DHA}

## 出現市場
{markets list — 在哪些市場產品中出現}

## 備註
{notes — 標準化過程說明}
```

## Ingredient Category Enum

| Category Key | 中文 | 範例 |
|-------------|------|------|
| `vitamin` | 維生素 | Vitamin C, Vitamin D3 |
| `mineral` | 礦物質 | Calcium, Zinc, Magnesium |
| `fatty_acid` | 脂肪酸 | Omega-3, EPA, DHA |
| `amino_acid` | 胺基酸 | L-Glutamine, BCAA |
| `protein` | 蛋白質 | Whey Protein, Collagen |
| `botanical` | 植物萃取 | Curcumin, Green Tea Extract |
| `probiotic` | 益生菌 | Lactobacillus, Bifidobacterium |
| `enzyme` | 酵素 | Nattokinase, Bromelain |
| `hormone` | 荷爾蒙前驅物 | DHEA, Melatonin |
| `other` | 其他 | 無法歸類 |

## `[REVIEW_NEEDED]` 觸發規則

以下情況**必須**標記 `[REVIEW_NEEDED]`：

1. RxNorm API 無匹配結果且無法手動對應
2. 多個 RxNorm ID 候選且無法判斷
3. 成分名稱含歧義（如 "Vitamin E" 可指 d-alpha 或 dl-alpha）

以下情況**不觸發** `[REVIEW_NEEDED]`：

- ❌ 手動策展成功對應
- ❌ 複合成分已正確拆解

## 輸出位置

`docs/Extractor/ingredient_map/{category}/{ingredient_slug}.md`

範例：
- `docs/Extractor/ingredient_map/fatty_acid/omega-3.md`
- `docs/Extractor/ingredient_map/vitamin/vitamin-c.md`

## 執行方式

```bash
# 萃取所有產品成分
./fetch.sh --extract-all

# 標準化高頻成分（前 500 名）
./fetch.sh --normalize --top 500

# 完整執行
./fetch.sh --full
```

## 環境設定

```bash
# .env（可選）
# RxNorm API 免費，無需 Key
```

## 自我審核 Checklist

- [ ] `standard_name` 使用英文官方名稱
- [ ] `rxnorm_id` 正確對應 NLM RxNorm
- [ ] 別名列表包含多語言版本
- [ ] 複合成分已正確拆解
- [ ] `confidence` 反映標準化品質
- [ ] `[REVIEW_NEEDED]` 僅在觸發條件成立時標記

## 高頻成分手動策展表

以下成分因名稱多樣性高，需手動維護對照：

| 標準名稱 | RxNorm ID | 常見別名 |
|---------|-----------|---------|
| Omega-3 Fatty Acids | 1372702 | omega 3, オメガ3, 오메가3, n-3 脂肪酸 |
| Vitamin C | 1151 | ascorbic acid, ビタミンC, 비타민C, 維生素C |
| Vitamin D3 | 10631 | cholecalciferol, ビタミンD3, 비타민D3 |
| Calcium | 1427 | Ca, カルシウム, 칼슘, 鈣 |
| Fish Oil | 1308207 | fish oil, 魚油, フィッシュオイル, 피쉬오일 |
| Collagen | 37026 | コラーゲン, 콜라겐, 膠原蛋白 |
| Curcumin | 37230 | turmeric extract, ウコン, 강황, 薑黃素 |

> 此表應持續更新，隨使用頻率增加而擴充。
