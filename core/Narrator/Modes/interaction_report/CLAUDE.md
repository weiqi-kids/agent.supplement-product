# Mode: interaction_report — 交互作用報告

## Mode 定義表

| 項目 | 說明 |
|------|------|
| **Mode name** | interaction_report（交互作用報告） |
| **Function** | 整合 ddi/dfi/dhi Layer 資料，產出交互作用分析報告 |
| **Source Layers** | `ddi`, `dfi`, `dhi`, `ingredient_map` |
| **Output frequency** | 月報 + 主題報告整合 |
| **Target audience** | 消費者（選購指南）、專業人士（產品情報） |

## 報告類型

### 1. 主題交互報告（整合至 topic_tracking）

為每個追蹤主題產出交互作用章節：

```
docs/reports/{topic}/interactions/
├── index.md          # 主題交互總覽
├── ddi.md            # 藥物-藥物交互
├── dfi.md            # 藥物-食物交互
└── dhi.md            # 藥物-補充劑交互
```

### 2. 獨立交互報告（月報）

```
docs/Narrator/interaction_report/{YYYY-MM}.md
```

## 來源 Layer

| Layer | 資料類型 | 用途 |
|-------|---------|------|
| `ddi` | Drug-Drug Interactions | 藥物間交互 |
| `dfi` | Drug-Food Interactions | 藥物-食物交互 |
| `dhi` | Drug-Herb/Supplement Interactions | 藥物-補充劑交互 |
| `ingredient_map` | 成分標準化 | 成分名稱對應 |

## 輸出格式

### 主題交互報告範本

```markdown
---
mode: "interaction_report"
topic: "{topic_id}"
period: "{YYYY-MM}"
generated_at: "{ISO8601}"
source_layers:
  - ddi
  - dfi
  - dhi
---

# {topic_name} 交互作用指南

> ⚠️ **重要提醒**：本資訊僅供教育和研究目的，不構成醫療建議。
> 服用處方藥物者，在使用任何補充劑前應諮詢專業醫療人員。

## 摘要

{topic_name} 相關產品（如 {example_products}）已有 **{dhi_count}** 筆藥物-補充劑交互文獻記錄。
其中 **{major_count}** 筆屬重大（Major）交互，需特別注意。

## 高風險藥物類別

以下藥物與 {topic_name} 類產品併用時需格外謹慎：

| 藥物類別 | 風險等級 | 交互機轉 | 建議 |
|---------|---------|---------|------|
{high_risk_table}

## 藥物-藥物交互 (DDI)

{ddi_section — 若此主題成分為藥物前驅物}

## 藥物-食物交互 (DFI)

{dfi_section — 相關飲食注意事項}

## 藥物-補充劑交互 (DHI)

### Major（重大）

{major_interactions_list}

### Moderate（中等）

{moderate_interactions_list}

### Minor（輕微）

{minor_interactions_list}

## 安全使用建議

1. **服用抗凝血藥物者**：{anticoagulant_advice}
2. **服用降血壓藥物者**：{antihypertensive_advice}
3. **術前準備**：{surgery_advice}

## 文獻來源

{literature_references — 連結到原始 PubMed 文獻}

---

*報告產出日期：{generated_at}*
*資料來源：PubMed 文獻資料庫*
```

## 報告產出邏輯

### Step 1: 識別主題相關成分

從 `ingredient_map` Layer 取得主題相關標準化成分：

```python
# 範例：fish-oil 主題
related_ingredients = [
    "omega-3",
    "EPA",
    "DHA",
    "fish oil",
    "krill oil"
]
```

### Step 2: 篩選相關交互文獻

從 ddi/dfi/dhi Layer 篩選：

```python
# 篩選 DHI 中含相關成分的文獻
dhi_matches = filter(
    lambda x: x.supplement_ingredient in related_ingredients,
    dhi_documents
)
```

### Step 3: 分級統計

按 severity 分組統計：

```python
severity_counts = {
    "major": len([x for x in matches if x.severity == "major"]),
    "moderate": len([x for x in matches if x.severity == "moderate"]),
    "minor": len([x for x in matches if x.severity == "minor"])
}
```

### Step 4: 產出報告

使用模板填充資料。

## 整合至現有報告

### topic_tracking 整合

在現有主題報告中加入交互作用章節：

```markdown
# 魚油 2026 年 2 月市場報告

## 市場概覽
{existing_content}

## 交互作用提醒 🆕

⚠️ **服用以下藥物者請注意：**

| 藥物類別 | 風險 | 建議 |
|---------|------|------|
| 抗凝血劑（Warfarin 等） | 出血風險增加 | 諮詢醫師，監測 INR |
| 降血壓藥 | 可能增強降壓效果 | 監測血壓 |

👉 [查看完整交互作用報告](/reports/fish-oil/interactions/)

{rest_of_existing_content}
```

### 選購指南整合

在 `guide.md` 加入安全須知：

```markdown
## 選購前須知

### 安全性考量

{safety_section — 基於 DHI 資料}

### 不建議族群

- 服用 Warfarin 或其他抗凝血藥物者（除非醫師許可）
- 手術前兩週內
- {other_contraindications}
```

## 自我審核 Checklist

- [ ] 所有 severity=major 交互均已列出
- [ ] 藥物類別分類正確
- [ ] 臨床建議與原始文獻一致
- [ ] 免責聲明已包含
- [ ] 文獻連結有效
- [ ] 無誇大或縮小交互風險

## 禁止行為

- ❌ 提供具體用藥劑量建議
- ❌ 建議停用處方藥物
- ❌ 淡化已知重大交互風險
- ❌ 引用未經同行審查的資料
- ❌ 混淆個案報告與 RCT 證據

## 執行方式

```bash
# 產出所有主題的交互報告
python3 scripts/generate_interaction_report.py --all

# 產出特定主題
python3 scripts/generate_interaction_report.py --topic fish-oil

# 產出月報總覽
python3 scripts/generate_interaction_report.py --monthly 2026-02
```

## 輸出位置

| 類型 | 位置 |
|------|------|
| 主題交互報告 | `docs/reports/{topic}/interactions/` |
| 月報總覽 | `docs/Narrator/interaction_report/{YYYY-MM}.md` |
| Jekyll 轉換後 | `docs/reports/interactions/` |
