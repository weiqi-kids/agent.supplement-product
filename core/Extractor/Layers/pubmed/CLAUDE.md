# Layer: pubmed — PubMed 學術文獻資料庫

## Layer 定義表

| 項目 | 說明 |
|------|------|
| **Layer name** | pubmed（學術文獻） |
| **Engineering function** | 從 NCBI E-utilities API 查詢與追蹤主題相關的學術文獻 |
| **Collectable data** | PMID、標題、摘要、期刊、發表日期、作者、研究類型 |
| **Automation level** | 100% — 公開 API，可選用 API Key 提高速率 |
| **Output value** | 主題相關文獻資料庫，支援實證分析與文獻薈萃 |
| **Risk type** | API 速率限制、摘要內容可能不完整 |
| **Reviewer persona** | 資料可信度審核員、科學文獻審核員 |
| **WebFetch 策略** | **不使用** — API 已包含摘要資料 |

## 資料源資訊

- **來源**: NCBI PubMed
- **API**: E-utilities (esearch.fcgi + efetch.fcgi)
- **文件**: https://www.ncbi.nlm.nih.gov/books/NBK25499/
- **認證**: 免費，建議設定 API Key 提高速率
- **速率限制**:
  - 無 API Key: 3 requests/second
  - 有 API Key: 10 requests/second

## 設計原則

1. **主題驅動**：只查詢已追蹤主題（exosomes, fish-oil 等）的文獻
2. **複用主題定義**：從 `topics/*.yaml` 讀取關鍵詞組合 PubMed 查詢
3. **Claude 萃取分析**：讀取摘要，標記功效分類與成分提及

## 查詢策略

### 從主題定義產生 PubMed 查詢

```yaml
# topics/fish-oil.yaml
pubmed:
  query: "(omega-3[Title/Abstract] OR fish oil[Title/Abstract] OR EPA[Title/Abstract] OR DHA[Title/Abstract]) AND (supplement*[Title/Abstract] OR nutraceutical[Title/Abstract])"
  filters:
    - humans[MH]
    - English[Language]
  date_range: 5  # 最近 5 年
  max_results: 500
```

### 查詢欄位對應

| 主題關鍵詞 | PubMed 查詢構建 |
|-----------|----------------|
| `keywords.exact` | 組合為 OR 條件 |
| `keywords.fuzzy` | 作為擴展詞 |
| 預設過濾 | humans, English, 最近 5 年 |

## API 流程

### Step 1: ESearch — 取得 PMID 列表

```bash
GET https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi
  ?db=pubmed
  &term={query}
  &retmax={max_results}
  &retmode=json
  &mindate={5年前}
  &maxdate={今日}
  &datetype=pdat
```

### Step 2: EFetch — 取得文獻詳細資料

```bash
GET https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi
  ?db=pubmed
  &id={pmid1,pmid2,...}
  &rettype=xml
```

## 萃取邏輯

### XML → Markdown 欄位映射

| Markdown 欄位 | XML 路徑 | 說明 |
|---------------|----------|------|
| `source_id` | PMID | PubMed ID |
| `source_layer` | 固定 `"pubmed"` | — |
| `source_url` | 組合產生 | `https://pubmed.ncbi.nlm.nih.gov/{PMID}/` |
| `market` | 固定 `"global"` | 學術文獻無地區限制 |
| `title` | ArticleTitle | 文獻標題 |
| `journal` | Journal/Title | 期刊名稱 |
| `pub_date` | PubDate | YYYY-MM-DD |
| `authors` | AuthorList | 作者列表 |
| `study_type` | PublicationType + 推斷 | 見下方規則 |
| `evidence_level` | 由 study_type 決定 | 1-5 級 |
| `topic` | 查詢時指定 | 對應主題 ID |
| `abstract` | Abstract/AbstractText | 摘要全文 |

## Study Type 分類規則

從 PublicationType 和標題/摘要推斷：

| study_type | 識別條件 | evidence_level |
|-----------|----------|----------------|
| `meta_analysis` | "Meta-Analysis" in PublicationType | 1 |
| `systematic_review` | "Systematic Review" in PublicationType 或標題含 "systematic review" | 1 |
| `rct` | "Randomized Controlled Trial" in PublicationType | 2 |
| `clinical_trial` | "Clinical Trial" in PublicationType | 3 |
| `observational` | "Observational Study" or "Cohort Study" in PublicationType | 4 |
| `review` | "Review" in PublicationType（非 systematic） | 5 |
| `case_report` | "Case Reports" in PublicationType | 5 |

## Claim Category 分類規則（Claude 分析）

從摘要內容分析歸類：

| claim_category | 中文 | 識別關鍵詞 |
|---------------|------|-----------|
| `anti_aging` | 抗衰老 | aging, longevity, senescence, telomere |
| `cardiovascular` | 心血管 | cardiovascular, lipid, cholesterol, blood pressure |
| `cognitive` | 認知功能 | cognitive, memory, brain, neurological |
| `immune` | 免疫調節 | immune, inflammation, autoimmune |
| `metabolic` | 代謝 | glucose, diabetes, metabolism, obesity |
| `musculoskeletal` | 肌肉骨骼 | muscle, bone, joint, osteoporosis |
| `sexual` | 性功能 | sexual, erectile, libido |
| `skin` | 皮膚 | skin, dermatological, collagen |
| `digestive` | 消化 | gut, intestinal, microbiome, digestive |
| `energy` | 活力 | fatigue, energy, vitality |
| `other` | 其他 | 無法歸類 |

## `[REVIEW_NEEDED]` 觸發規則

以下情況**必須**標記 `[REVIEW_NEEDED]`：
1. 無法取得摘要（AbstractText 為空）
2. PMID 為空
3. 標題為空

以下情況**不觸發** `[REVIEW_NEEDED]`：
- ❌ study_type 無法判定 — 預設為 "other"
- ❌ claim_category 為空 — 可能為基礎研究

## 輸出格式

```markdown
---
source_id: "{PMID}"
source_layer: "pubmed"
source_url: "https://pubmed.ncbi.nlm.nih.gov/{PMID}/"
market: "global"
title: "{ArticleTitle}"
journal: "{Journal}"
pub_date: "{YYYY-MM-DD}"
study_type: "{inferred study_type}"
evidence_level: {1-5}
topic: "{topic_id}"
claim_categories: ["{cat1}", "{cat2}"]
ingredients_mentioned: ["{ingredient1}", "{ingredient2}"]
fetched_at: "{ISO8601}"
---

# {ArticleTitle}

## 基本資訊
- 期刊：{Journal}
- 發表日期：{pub_date}
- 研究類型：{study_type}
- 證據等級：Level {evidence_level}
- 主題：{topic}
- PMID：{PMID}

## 作者
{authors}

## 摘要
{AbstractText}

## 功效分類
{claim_categories 列表}

## 提及成分
{ingredients_mentioned 列表}
```

## 輸出位置

`docs/Extractor/pubmed/{topic_id}/{PMID}.md`

## 執行方式

```bash
# 擷取特定主題文獻
./fetch.sh --topic fish-oil

# 擷取所有主題
./fetch.sh --all

# 指定最大結果數
./fetch.sh --topic exosomes --limit 100
```

## 環境設定

```bash
# .env（可選，提高 API 速率）
NCBI_API_KEY=your-api-key
NCBI_EMAIL=your-email@example.com
```

## 自我審核 Checklist

- [ ] `source_id` 正確對應 PMID
- [ ] 摘要完整保留
- [ ] `study_type` 依 PublicationType 正確推斷
- [ ] `evidence_level` 與 study_type 對應
- [ ] `claim_categories` 由 Claude 分析產生
- [ ] frontmatter 格式正確
- [ ] `[REVIEW_NEEDED]` 僅在觸發條件成立時標記
