# Layer: dhi — Drug-Herb/Supplement Interactions

## Layer 定義表

| 項目 | 說明 |
|------|------|
| **Layer name** | dhi（藥物-草藥/補充劑交互） |
| **Engineering function** | 從 PubMed 擷取藥物與草藥/補充劑間交互作用文獻 |
| **Collectable data** | PMID、標題、摘要、藥物、補充劑、交互類型、嚴重程度、機轉 |
| **Automation level** | 90% — PubMed API + Claude 分析 |
| **Output value** | 藥物-補充劑交互作用知識庫，支援產品安全性評估與消費者警示 |
| **Risk type** | 文獻解讀錯誤、補充劑成分複雜性 |
| **Reviewer persona** | 藥學專家、中醫師、營養師、臨床安全審核員 |
| **WebFetch 策略** | **不使用** — PubMed API 已包含摘要 |

## 資料源資訊

### 主要來源：PubMed

- **API**: E-utilities (esearch.fcgi + efetch.fcgi)
- **文件**: https://www.ncbi.nlm.nih.gov/books/NBK25499/
- **認證**: 免費，建議設定 API Key
- **速率限制**: 無 Key: 3 req/s；有 Key: 10 req/s

### 未來擴充：NatMed (TRC)（MVP 後評估）

- **網址**: https://trchealthcare.com/product/natmed-pro/
- **資料量**: 300,000+ 產品交互資料
- **取用方式**: 商業訂閱
- **狀態**: MVP 後評估投資效益

## 查詢策略

### PubMed 查詢模板

```
(herb drug interaction[Title] OR supplement drug interaction[Title] OR natural product drug interaction[Title])
  AND (adverse[Title/Abstract] OR safety[Title/Abstract] OR risk[Title/Abstract])
  AND humans[MH]
  AND English[Language]
```

### 細分查詢（按補充劑類別）

```yaml
# 魚油交互
query_fish_oil: |
  (fish oil[Title] OR omega-3[Title] OR EPA[Title] OR DHA[Title])
  AND (drug interaction[Title] OR warfarin[Title] OR anticoagulant[Title])

# 薑黃/薑黃素交互
query_curcumin: |
  (curcumin[Title] OR turmeric[Title])
  AND (drug interaction[Title] OR CYP450[Title/Abstract])

# 銀杏交互
query_ginkgo: |
  (ginkgo[Title] OR ginkgo biloba[Title])
  AND (drug interaction[Title] OR bleeding[Title/Abstract])

# 聖約翰草交互（已知強效 CYP 誘導劑）
query_st_johns_wort: |
  (st john's wort[Title] OR hypericum[Title])
  AND (drug interaction[Title])
```

## 高風險交互組合

以下組合已有明確文獻支持，屬高關注項目：

| 補充劑 | 藥物類別 | 風險 | 機轉 |
|--------|---------|------|------|
| 魚油 | 抗凝血劑 | 出血風險增加 | 抗血小板作用疊加 |
| 銀杏 | 抗凝血劑 | 出血風險增加 | 抑制血小板聚集 |
| 聖約翰草 | 多數藥物 | 藥效降低 | CYP3A4 誘導 |
| 鈣 | 甲狀腺藥物 | 吸收降低 | 螯合作用 |
| 維生素 K | Warfarin | 抗凝效果降低 | 拮抗作用 |
| 薑黃素 | 抗凝血劑 | 出血風險 | 抗血小板作用 |

## 萃取邏輯

### XML → Markdown 欄位映射

| Markdown 欄位 | XML 路徑 | 說明 |
|---------------|----------|------|
| `source_id` | PMID | PubMed ID |
| `source_layer` | 固定 `"dhi"` | — |
| `interaction_type` | 固定 `"DHI"` | Drug-Herb/Supplement |
| `drug` | Claude 萃取 | 涉及藥物 |
| `supplement` | Claude 萃取 | 涉及補充劑 |
| `supplement_ingredient` | Claude 萃取 | 補充劑主成分（如有） |
| `severity` | Claude 判定 | major/moderate/minor/unknown |
| `mechanism` | Claude 萃取 | 作用機轉 |

## 輸出格式

```markdown
---
source_id: "{PMID}"
source_layer: "dhi"
source_url: "https://pubmed.ncbi.nlm.nih.gov/{PMID}/"
interaction_type: "DHI"
drug: "{藥物名稱}"
drug_rxnorm: "{RxNorm ID}"
drug_class: "{藥物類別}"
supplement: "{補充劑名稱}"
supplement_ingredient: "{主成分}"
supplement_rxnorm: "{RxNorm ID}"
severity: "{major|moderate|minor|unknown}"
mechanism: "{作用機轉概述}"
evidence_level: {1-5}
pub_date: "{YYYY-MM-DD}"
fetched_at: "{ISO8601}"
---

# {supplement} × {drug} 交互作用

## 基本資訊
- 交互類型：Drug-Herb/Supplement Interaction (DHI)
- 嚴重程度：{severity}
- 證據等級：Level {evidence_level}
- 藥物類別：{drug_class}
- PMID：{PMID}

## 作用機轉
{mechanism 詳細說明}

## 臨床建議
{recommendations — Claude 萃取自摘要}

## 相關產品
{related_products — 連結到含此補充劑的產品}

## 原始摘要
{abstract}
```

## Supplement Category Enum

| Category Key | 中文 | 範例 |
|-------------|------|------|
| `omega_fatty_acid` | Omega 脂肪酸 | 魚油、磷蝦油、亞麻籽油 |
| `botanical` | 植物萃取 | 銀杏、薑黃、人參 |
| `vitamin` | 維生素 | 維生素 E、維生素 K |
| `mineral` | 礦物質 | 鈣、鎂、鋅 |
| `amino_acid` | 胺基酸 | 精胺酸、色胺酸 |
| `enzyme` | 酵素 | 納豆激酶、輔酶 Q10 |
| `probiotic` | 益生菌 | 乳酸桿菌、雙歧桿菌 |
| `other` | 其他 | 無法歸類 |

## Drug Class Enum

| Class Key | 中文 | 範例藥物 |
|----------|------|---------|
| `anticoagulant` | 抗凝血劑 | Warfarin, Heparin |
| `antiplatelet` | 抗血小板劑 | Aspirin, Clopidogrel |
| `antihypertensive` | 降血壓藥 | ACE inhibitors, Beta blockers |
| `antidiabetic` | 降血糖藥 | Metformin, Insulin |
| `statin` | 他汀類 | Atorvastatin, Simvastatin |
| `antidepressant` | 抗憂鬱藥 | SSRIs, MAOIs |
| `immunosuppressant` | 免疫抑制劑 | Cyclosporine, Tacrolimus |
| `thyroid` | 甲狀腺藥物 | Levothyroxine |
| `other` | 其他 | 無法歸類 |

## `[REVIEW_NEEDED]` 觸發規則

以下情況**必須**標記 `[REVIEW_NEEDED]`：

1. 無法從摘要識別藥物或補充劑
2. severity 為 unknown
3. 摘要為空或不完整
4. 補充劑為複方且無法確定交互成分

## 輸出位置

`docs/Extractor/dhi/{supplement_category}/{supplement-drug_slug}.md`

範例：
- `docs/Extractor/dhi/omega_fatty_acid/fish-oil-warfarin.md`
- `docs/Extractor/dhi/botanical/ginkgo-aspirin.md`
- `docs/Extractor/dhi/botanical/curcumin-anticoagulant.md`

## 與現有產品關聯

DHI Layer 可與現有產品 Layer 交叉比對：

```
docs/Extractor/dhi/omega_fatty_acid/fish-oil-warfarin.md
    ↓ 關聯
docs/Extractor/us_dsld/omega_fatty_acids/*.md（含魚油產品）
```

報告產出時可自動標註：「此產品含魚油，服用 Warfarin 者應注意」

## 執行方式

```bash
# 擷取所有 DHI 文獻
./fetch.sh --all

# 擷取特定補充劑類別
./fetch.sh --category omega_fatty_acid

# 擷取與特定藥物類別相關
./fetch.sh --drug-class anticoagulant

# 指定最大結果數
./fetch.sh --limit 500
```

## 自我審核 Checklist

- [ ] `drug` 和 `supplement` 正確識別
- [ ] `supplement_ingredient` 準確萃取（複方產品）
- [ ] `drug_class` 正確分類
- [ ] `severity` 與文獻內容一致
- [ ] `mechanism` 萃取正確
- [ ] `[REVIEW_NEEDED]` 僅在觸發條件成立時標記

## 免責聲明

所有 DHI 檔案必須包含：

```
⚠️ 本資訊僅供教育和研究目的，不構成醫療建議。
服用處方藥物者，在使用任何補充劑前應諮詢專業醫療人員。
```
