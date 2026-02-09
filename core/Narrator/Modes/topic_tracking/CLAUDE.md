# topic_tracking Mode

## 目的

針對特定主題（外泌體、魚油等）追蹤跨國市場產品、分析趨勢、產出定期報告。

## 資料來源

- 讀取 `topics/*.yaml` 取得追蹤主題清單
- 從 `docs/Extractor/{layer}/{category}/*.md` 篩選符合關鍵詞的產品

---

## 主題定義格式

每個追蹤主題以 YAML 檔案定義，存放於 `topics/` 目錄：

```yaml
topic_id: exosomes          # 唯一識別碼（用於目錄名稱）
name:
  zh: 外泌體                 # 中文名稱
  en: Exosomes              # 英文名稱
  ja: エクソソーム           # 日文名稱
  ko: 외소좀                 # 韓文名稱

keywords:
  exact:                    # 精確匹配（成分欄位）
    - exosome
    - exosomes
  fuzzy:                    # 模糊匹配（產品名稱、描述）
    - stem cell
    - placenta

category_filter:            # 限定搜尋的分類（可選，空=全部）
  - specialty
  - other

output:
  index: docs/reports/{topic_id}/index.md
  guide: docs/reports/{topic_id}/guide.md
  reports: docs/reports/{topic_id}/reports/
```

---

## 篩選邏輯

1. **分類篩選**：依 `category_filter` 先篩選目標分類目錄
2. **精確匹配**：依 `keywords.exact` 匹配 `## 成分` 或 `## 機能性成分` 段落
3. **模糊匹配**：依 `keywords.fuzzy` 匹配產品名稱、描述
4. **排除標記**：排除 `[REVIEW_NEEDED]` 標記的產品
5. **去重**：同一產品跨多關鍵詞匹配只計一次

### 匹配範例

```
產品 A:
  - 名稱: "Premium Exosome Serum"
  - 成分: Exosome Extract, Hyaluronic Acid
  - 結果: ✅ 匹配 (exact: exosome, fuzzy: exosome in name)

產品 B:
  - 名稱: "Anti-Aging Cream"
  - 成分: Stem Cell Extract, Vitamin E
  - 結果: ✅ 匹配 (fuzzy: stem cell)

產品 C:
  - 名稱: "Vitamin C Tablet"
  - 成分: Vitamin C, Zinc
  - 結果: ❌ 不匹配
```

---

## 輸出類型

### 1. 主題首頁 (index.md)

**更新頻率**：季度/年度（或內容有重大變化時）

**AI 自動產生內容**：

```markdown
# {主題名稱}

## 要解決什麼問題？
← 根據產品健康聲明 (health_claim) 分析歸納

## 造成問題的原因
← 根據產品描述和成分機轉分析

## 市面解決方案分析
← 自動統計各類產品（劑型、劑量、品牌）

## 作用機轉
← 根據成分資料和產品聲明歸納

## 發展歷史與現況
← 根據產品上市日期統計趨勢

## 參考文獻
← 從產品資料中提取（若有引用）
```

### 2. 選購指南 (guide.md)

**更新頻率**：月度

**AI 自動產生內容**：

```markdown
# {主題名稱}選購指南

## 決策樹
← 根據產品分類自動產生選擇流程

## 選購要點
← 統計常見劑量、劑型、認證標準

## 常見問題 FAQ
← 根據產品描述中的常見問題歸納
```

### 3. 市場報告 (reports/YYYY-MM.md)

**更新頻率**：月度

**報告框架**：

```markdown
---
topic: {topic_id}
period: "YYYY-MM"
generated_at: "ISO8601"
---

# {主題名稱}市場報告 — YYYY 年 M 月

## 摘要
← 3-5 句話概述本月市場動態

## 各國產品統計

| 市場 | 產品數 | 較上月 | 主要品牌 |
|------|--------|--------|----------|
| 🇺🇸 美國 | N | +/-N | Brand A, B |
| 🇨🇦 加拿大 | N | +/-N | Brand C |
| ...

## 熱門品牌/製造商

| 排名 | 品牌/製造商 | 產品數 | 市場 |
|------|-------------|--------|------|
| 1 | Brand A | N | 🇺🇸🇨🇦 |
| ...

## 劑型分布

| 劑型 | 產品數 | 佔比 |
|------|--------|------|
| Softgel | N | X% |
| Capsule | N | X% |
| ...

## 新品上市
← 列出本月新增產品

## 撤回/下市
← 列出本月撤回或下市產品（若有）

## 趨勢觀察
← 分析市場趨勢與值得關注的變化
```

---

## 執行腳本

### 主題報告產出

```bash
# 產出所有主題的月報
python3 scripts/generate_topic_report.py

# 產出特定主題
python3 scripts/generate_topic_report.py --topic exosomes

# Dry run（僅顯示匹配結果，不產出報告）
python3 scripts/generate_topic_report.py --topic fish-oil --dry-run
```

### AI 內容產生

```bash
# 更新主題首頁和選購指南
python3 scripts/generate_topic_content.py --topic exosomes
```

---

## 輸出位置

```
docs/
├── Narrator/
│   └── topic_tracking/
│       ├── exosomes/
│       │   └── 2026-02.md      # 市場報告（CI 產出）
│       └── fish-oil/
│           └── 2026-02.md
└── reports/                    # Jekyll 網站
    ├── exosomes/
    │   ├── index.md            # 主題首頁
    │   ├── guide.md            # 選購指南
    │   └── reports/
    │       └── 2026-02.md      # 市場報告（Jekyll 格式）
    └── fish-oil/
        └── ...
```

---

## 與其他 Mode 的關係

| Mode | 產出 | 關係 |
|------|------|------|
| `market_snapshot` | 週報（全市場） | 互補：topic_tracking 聚焦特定主題 |
| `ingredient_radar` | 月報（成分趨勢） | 上游：提供主題推薦依據 |
| `topic_tracking` | 月報（特定主題） | 下游：深入追蹤特定成分/產品類型 |

---

## 禁止事項

- ❌ 自行新增 topic YAML（需透過 create_topic.py 或推薦流程）
- ❌ 在報告中推薦特定品牌（保持中立）
- ❌ 產出無法驗證的健康聲明
- ❌ 混淆推測與事實
