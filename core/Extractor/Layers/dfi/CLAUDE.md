# Layer: dfi — Drug-Food Interactions

## Layer 定義表

| 項目 | 說明 |
|------|------|
| **Layer name** | dfi（藥物-食物交互） |
| **Engineering function** | 從 PubMed 擷取藥物與食物間交互作用文獻 |
| **Collectable data** | PMID、標題、摘要、藥物、食物、交互類型、影響機轉 |
| **Automation level** | 90% — PubMed API + Claude 分析 |
| **Output value** | 藥物-食物交互作用知識庫，支援飲食注意事項建議 |
| **Risk type** | 文獻解讀錯誤、食物分類不一致 |
| **Reviewer persona** | 藥學專家、營養師、臨床安全審核員 |
| **WebFetch 策略** | **不使用** — PubMed API 已包含摘要 |

## 資料源資訊

### 主要來源：PubMed

- **API**: E-utilities (esearch.fcgi + efetch.fcgi)
- **文件**: https://www.ncbi.nlm.nih.gov/books/NBK25499/
- **認證**: 免費，建議設定 API Key
- **速率限制**: 無 Key: 3 req/s；有 Key: 10 req/s

### 補充來源：DDInter 2.0（評估中）

- **網址**: https://ddinter2.scbdd.com/
- **資料量**: 857 筆 DFI
- **取用方式**: 需評估 Terms of Service
- **狀態**: MVP 階段暫不使用

## 查詢策略

### PubMed 查詢模板

```
(drug food interaction[Title])
  AND (bioavailability[Title/Abstract] OR absorption[Title/Abstract] OR metabolism[Title/Abstract])
  AND humans[MH]
  AND English[Language]
```

### 細分查詢（按食物類別）

```yaml
# 柑橘類水果交互
query_citrus: |
  (grapefruit[Title] OR citrus[Title])
  AND (drug interaction[Title])
  AND (CYP3A4 OR bioavailability)

# 高維生素K食物交互
query_vitamin_k: |
  (vitamin K[Title] OR leafy greens[Title])
  AND (warfarin[Title] OR anticoagulant[Title])
  AND interaction

# 乳製品交互
query_dairy: |
  (dairy[Title] OR milk[Title] OR calcium[Title])
  AND (antibiotic[Title] OR tetracycline[Title] OR fluoroquinolone[Title])
  AND absorption
```

## 常見 Drug-Food 交互類型

| 交互類型 | 說明 | 範例 |
|---------|------|------|
| `absorption_decrease` | 食物降低藥物吸收 | 乳製品 + 四環黴素 |
| `absorption_increase` | 食物增加藥物吸收 | 高脂餐 + 親脂性藥物 |
| `metabolism_inhibition` | 食物抑制藥物代謝 | 葡萄柚 + CYP3A4 受質 |
| `metabolism_induction` | 食物誘導藥物代謝 | 高蛋白飲食 + 某些藥物 |
| `pharmacodynamic` | 藥效學交互 | 高維生素K食物 + Warfarin |

## 萃取邏輯

### XML → Markdown 欄位映射

| Markdown 欄位 | XML 路徑 | 說明 |
|---------------|----------|------|
| `source_id` | PMID | PubMed ID |
| `source_layer` | 固定 `"dfi"` | — |
| `interaction_type` | 固定 `"DFI"` | Drug-Food |
| `drug` | Claude 萃取 | 涉及藥物 |
| `food` | Claude 萃取 | 涉及食物 |
| `effect_type` | Claude 判定 | 交互類型（見上表） |
| `severity` | Claude 判定 | major/moderate/minor/unknown |
| `mechanism` | Claude 萃取 | 作用機轉 |

## 輸出格式

```markdown
---
source_id: "{PMID}"
source_layer: "dfi"
source_url: "https://pubmed.ncbi.nlm.nih.gov/{PMID}/"
interaction_type: "DFI"
drug: "{藥物名稱}"
drug_rxnorm: "{RxNorm ID}"
food: "{食物名稱}"
food_category: "{food_category enum}"
effect_type: "{absorption_decrease|metabolism_inhibition|...}"
severity: "{major|moderate|minor|unknown}"
mechanism: "{作用機轉概述}"
evidence_level: {1-5}
pub_date: "{YYYY-MM-DD}"
fetched_at: "{ISO8601}"
---

# {drug} × {food} 交互作用

## 基本資訊
- 交互類型：Drug-Food Interaction (DFI)
- 影響類型：{effect_type}
- 嚴重程度：{severity}
- 證據等級：Level {evidence_level}
- PMID：{PMID}

## 作用機轉
{mechanism 詳細說明}

## 飲食建議
{dietary_recommendations — Claude 萃取自摘要}

## 原始摘要
{abstract}
```

## Food Category Enum

| Category Key | 中文 | 範例 |
|-------------|------|------|
| `citrus` | 柑橘類 | 葡萄柚、柳橙 |
| `dairy` | 乳製品 | 牛奶、起司、優格 |
| `leafy_greens` | 深綠葉蔬菜 | 菠菜、羽衣甘藍 |
| `high_fat` | 高脂肪食物 | 油炸食物、肥肉 |
| `caffeine` | 咖啡因 | 咖啡、茶、能量飲料 |
| `alcohol` | 酒精 | 啤酒、葡萄酒、烈酒 |
| `fermented` | 發酵食品 | 納豆、味噌、泡菜 |
| `fiber` | 高纖維食物 | 全穀、豆類 |
| `other` | 其他 | 無法歸類 |

## `[REVIEW_NEEDED]` 觸發規則

以下情況**必須**標記 `[REVIEW_NEEDED]`：

1. 無法從摘要識別藥物或食物
2. severity 為 unknown
3. 摘要為空或不完整

## 輸出位置

`docs/Extractor/dfi/{food_category}/{drug-food_slug}.md`

範例：
- `docs/Extractor/dfi/citrus/simvastatin-grapefruit.md`
- `docs/Extractor/dfi/dairy/tetracycline-milk.md`

## 執行方式

```bash
# 擷取所有 DFI 文獻
./fetch.sh --all

# 擷取特定食物類別
./fetch.sh --category citrus

# 指定最大結果數
./fetch.sh --limit 500
```

## 自我審核 Checklist

- [ ] `drug` 和 `food` 正確識別
- [ ] `effect_type` 準確分類
- [ ] `severity` 與文獻內容一致
- [ ] `mechanism` 萃取正確
- [ ] `[REVIEW_NEEDED]` 僅在觸發條件成立時標記

## 免責聲明

所有 DFI 檔案必須包含：

```
⚠️ 本資訊僅供教育和研究目的，不構成醫療或飲食建議。
任何用藥或飲食變更應諮詢專業醫療人員或營養師。
```
