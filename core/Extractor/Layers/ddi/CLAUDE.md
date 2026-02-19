# Layer: ddi — Drug-Drug Interactions

## Layer 定義表

| 項目 | 說明 |
|------|------|
| **Layer name** | ddi（藥物-藥物交互） |
| **Engineering function** | 從 PubMed 擷取藥物與藥物間交互作用文獻 |
| **Collectable data** | PMID、標題、摘要、藥物對、交互類型、嚴重程度、機轉 |
| **Automation level** | 90% — PubMed API + Claude 分析 |
| **Output value** | 藥物交互作用知識庫，支援產品安全性評估 |
| **Risk type** | 文獻解讀錯誤、嚴重程度判定不一致 |
| **Reviewer persona** | 藥學專家、臨床安全審核員 |
| **WebFetch 策略** | **不使用** — PubMed API 已包含摘要 |

## 資料源資訊

### 主要來源：PubMed

- **API**: E-utilities (esearch.fcgi + efetch.fcgi)
- **文件**: https://www.ncbi.nlm.nih.gov/books/NBK25499/
- **認證**: 免費，建議設定 API Key
- **速率限制**: 無 Key: 3 req/s；有 Key: 10 req/s

### 補充來源：DDInter 2.0（評估中）

- **網址**: https://ddinter2.scbdd.com/
- **資料量**: 302,516 筆 DDI
- **取用方式**: 需評估 Terms of Service
- **狀態**: MVP 階段暫不使用

## 查詢策略

### PubMed 查詢模板

```
(drug drug interaction[Title])
  AND (adverse[Title/Abstract] OR safety[Title/Abstract] OR risk[Title/Abstract])
  AND humans[MH]
  AND English[Language]
```

### 細分查詢（按藥物類別）

```yaml
# 抗凝血藥物交互
query_anticoagulant: |
  (warfarin[Title] OR anticoagulant[Title])
  AND (interaction[Title])
  AND (supplement OR herb OR nutraceutical)

# 降血壓藥物交互
query_antihypertensive: |
  (antihypertensive[Title] OR blood pressure medication[Title])
  AND (interaction[Title])
  AND (supplement OR natural product)
```

## 萃取邏輯

### XML → Markdown 欄位映射

| Markdown 欄位 | XML 路徑 | 說明 |
|---------------|----------|------|
| `source_id` | PMID | PubMed ID |
| `source_layer` | 固定 `"ddi"` | — |
| `source_url` | 組合產生 | `https://pubmed.ncbi.nlm.nih.gov/{PMID}/` |
| `interaction_type` | 固定 `"DDI"` | Drug-Drug |
| `drug_a` | Claude 萃取 | 第一個藥物 |
| `drug_b` | Claude 萃取 | 第二個藥物 |
| `severity` | Claude 判定 | major/moderate/minor/unknown |
| `mechanism` | Claude 萃取 | 作用機轉 |
| `evidence_level` | 由 study_type 決定 | 1-5 級 |

### Severity 判定規則

| severity | 條件 | 說明 |
|----------|------|------|
| `major` | 可能危及生命、需避免併用 | 出血、QT 延長、腎毒性 |
| `moderate` | 需監測、可能需調整劑量 | 血壓變化、代謝影響 |
| `minor` | 臨床意義低、通常無需處理 | 輕微吸收影響 |
| `unknown` | 無法從摘要判定 | 標記 REVIEW_NEEDED |

## 輸出格式

```markdown
---
source_id: "{PMID}"
source_layer: "ddi"
source_url: "https://pubmed.ncbi.nlm.nih.gov/{PMID}/"
interaction_type: "DDI"
drug_a: "{藥物A}"
drug_a_rxnorm: "{RxNorm ID}"
drug_b: "{藥物B}"
drug_b_rxnorm: "{RxNorm ID}"
severity: "{major|moderate|minor|unknown}"
mechanism: "{作用機轉概述}"
evidence_level: {1-5}
study_type: "{meta_analysis|rct|clinical_trial|...}"
pub_date: "{YYYY-MM-DD}"
fetched_at: "{ISO8601}"
---

# {drug_a} × {drug_b} 交互作用

## 基本資訊
- 交互類型：Drug-Drug Interaction (DDI)
- 嚴重程度：{severity}
- 證據等級：Level {evidence_level}
- 研究類型：{study_type}
- PMID：{PMID}

## 作用機轉
{mechanism 詳細說明}

## 臨床建議
{recommendations — Claude 萃取自摘要}

## 原始摘要
{abstract}
```

## `[REVIEW_NEEDED]` 觸發規則

以下情況**必須**標記 `[REVIEW_NEEDED]`：

1. 無法從摘要識別藥物對
2. severity 為 unknown
3. 摘要為空或不完整

以下情況**不觸發** `[REVIEW_NEEDED]`：

- ❌ mechanism 無法判定 — 標註 "mechanism unclear"
- ❌ RxNorm ID 無法取得 — 可後續補充

## 輸出位置

`docs/Extractor/ddi/{drug_category}/{drug_pair_slug}.md`

範例：
- `docs/Extractor/ddi/anticoagulant/warfarin-fish-oil.md`
- `docs/Extractor/ddi/cardiovascular/statin-grapefruit.md`

## 執行方式

```bash
# 擷取所有 DDI 文獻
./fetch.sh --all

# 擷取特定藥物類別
./fetch.sh --category anticoagulant

# 指定最大結果數
./fetch.sh --limit 500
```

## 環境設定

```bash
# .env
NCBI_API_KEY=your-api-key      # 可選，提高速率
NCBI_EMAIL=your@email.com      # 可選
```

## 自我審核 Checklist

- [ ] `drug_a` 和 `drug_b` 正確識別
- [ ] `severity` 與文獻內容一致
- [ ] `mechanism` 萃取正確
- [ ] `evidence_level` 與 study_type 對應
- [ ] `[REVIEW_NEEDED]` 僅在觸發條件成立時標記

---

## ⚠️ 子代理精簡回報規範

完成後**只輸出一行**：
```
DONE|ddi|F:{fetch筆數}|E:{extract筆數}|R:{review筆數}|OK
```

**禁止**：冗長描述、完整 log、摘要內容輸出

## 免責聲明

所有 DDI 檔案必須包含：

```
⚠️ 本資訊僅供教育和研究目的，不構成醫療建議。
任何用藥變更應諮詢專業醫療人員。
```
