# Mode: ingredient_radar — 成分雷達月報

## Mode 定義表

| 項目 | 說明 |
|------|------|
| **Mode name** | ingredient_radar（成分雷達） |
| **Purpose and audience** | 每月追蹤各國保健食品成分趨勢，識別熱門成分與新興成分。目標受眾：研發配方、產品策略、法規事務 |
| **Source layers** | `us_dsld`, `ca_lnhpd`, `kr_hff`, `jp_foshu`, `jp_fnfc` |
| **Automation ratio** | 85% — 成分排名自動化，趨勢解讀與新興成分判斷需人工確認 |
| **Content risk** | 成分名稱標準化不一致（各國使用不同命名）、趨勢推斷可能受樣本偏差影響 |
| **Reviewer persona** | 領域保守審核員、資料可信度審核員 |

## 資料來源定義

### 從 docs/Extractor/ 讀取

- `docs/Extractor/us_dsld/{category}/*.md` — 美國 DSLD 產品（成分段落）
- `docs/Extractor/ca_lnhpd/{category}/*.md` — 加拿大 LNHPD 產品（成分段落）
- `docs/Extractor/kr_hff/{category}/*.md` — 韓國健康機能食品（機能性成分）
- `docs/Extractor/jp_foshu/{category}/*.md` — 日本 FOSHU（機能性成分）
- `docs/Extractor/jp_fnfc/{category}/*.md` — 日本 FNFC（機能性関与成分）

### 篩選邏輯

- **排除**：帶有 `[REVIEW_NEEDED]` 標記的產品靜默排除，不納入統計，**報告中不顯示 REVIEW_NEEDED 數量**
- **disabled Layer**：自動跳過帶有 `.disabled` 的 Layer

### 成分擷取邏輯

從每個 .md 檔的以下段落擷取成分資訊：
- `## 成分` — us_dsld, ca_lnhpd
- `## 機能性成分` — jp_foshu, jp_fnfc, kr_hff

成分名稱標準化：
- 去除劑量資訊，僅保留成分名稱
- 合併同義詞（如 "Vitamin D3" = "Cholecalciferol"、"DHA" = "Docosahexaenoic acid"）
- 日文成分名盡量對照英文通用名（如 "ビタミンC" → "Vitamin C"）
- 無法標準化的成分保留原名

### 從 Qdrant 查詢（可選）

- 可透過 Qdrant 查詢歷史月份的成分分布，用於趨勢比較
- Qdrant 不可用時降級為僅基於當月本地資料

## 輸出框架

```markdown
---
mode: "ingredient_radar"
period: "{YYYY}-{MM}"
generated_at: "{ISO8601}"
source_layers:
  - us_dsld
  - ca_lnhpd
  - kr_hff
  - jp_foshu
  - jp_fnfc
---

# 成分雷達月報 — {YYYY} 年 {MM} 月

> 報告期間：{YYYY}-{MM}-01 ~ {YYYY}-{MM}-{DD}
> 產出時間：{generated_at}

## 摘要

{3-5 句話概述本月成分趨勢重點：最熱門成分、跨國共同趨勢、值得關注的新興成分}

## 全球熱門成分 Top 20

| 排名 | 成分名稱 | 出現產品數 | 涵蓋市場 | 主要品類 |
|------|----------|-----------|----------|----------|
| 1 | {ingredient} | {N} | {US, CA, JP, KR} | {category} |
| 2 | {ingredient} | {N} | {markets} | {category} |
| ... | ... | ... | ... | ... |
| 20 | {ingredient} | {N} | {markets} | {category} |

## 各市場成分偏好

### 🇺🇸 美國 Top 10 成分
| 排名 | 成分 | 產品數 |
|------|------|--------|
| 1 | {ingredient} | {N} |
| ... | ... | ... |

### 🇨🇦 加拿大 Top 10 成分
| 排名 | 成分 | 產品數 |
|------|------|--------|
| ... | ... | ... |

### 🇰🇷 韓國 Top 10 成分
| 排名 | 成分 | 產品數 |
|------|------|--------|
| ... | ... | ... |

### 🇯🇵 日本（FOSHU + FNFC）Top 10 成分
| 排名 | 成分 | 產品數 | 來源 |
|------|------|--------|------|
| ... | ... | ... | FOSHU/FNFC |

## 成分 × 市場交叉分析

| 成分 | 🇺🇸 US | 🇨🇦 CA | 🇰🇷 KR | 🇯🇵 JP | 說明 |
|------|---------|---------|---------|---------|------|
| {ingredient_1} | ✅ {N} | ✅ {N} | ❌ | ✅ {N} | {跨國差異說明} |
| {ingredient_2} | ✅ {N} | ❌ | ✅ {N} | ❌ | {說明} |
| ... | ... | ... | ... | ... | ... |

> 僅列出有顯著跨國差異的成分（某些市場有而其他市場無，或數量差異大於 5 倍）

## 品類 × 成分分析

### vitamins_minerals
- 核心成分：{list}
- 市場差異：{observation}

### botanicals
- 核心成分：{list}
- 市場差異：{observation}

### probiotics
- 核心菌株：{list}
- 市場差異：{observation}

### omega_fatty_acids
- 核心成分：{list}
- 市場差異：{observation}

### protein_amino
- 核心成分：{list}
- 市場差異：{observation}

## 趨勢觀察

### 跨國共同趨勢
{2-3 段落描述多個市場共同出現的成分趨勢}

### 市場獨特趨勢
{各市場獨有的成分偏好或特色}

### 值得關注的成分
{列出 3-5 個值得深入追蹤的成分，說明原因}

> **判定標準**（見下方「新興/值得關注成分判定規則」）

## 方法論說明

- 成分名稱標準化方法：{簡述}
- 日文成分名對照：{對照了哪些成分}
- 已知限制：{資料覆蓋範圍、成分命名不一致等}

## 資料品質備註

- 分析產品總數：{N} 筆
- 不可用的 Layer：{list}
- 成分無法標準化的比例：{N}%

## 免責聲明

本報告由 AI 自動生成，基於各國官方公開資料庫的產品登記資訊。成分排名基於資料庫登記產品數量，不代表實際市場銷售份額或消費趨勢。成分名稱標準化為自動處理，可能存在歸併誤差。各國監管制度對成分的定義和分類標準不同，跨國比較應考慮法規差異。本報告不構成任何配方建議或法規諮詢。
```

## 輸出位置

`docs/Narrator/ingredient_radar/{YYYY}-{MM}-ingredient-radar.md`

範例：`docs/Narrator/ingredient_radar/2026-01-ingredient-radar.md`

## 執行邏輯

1. 確定報告期間（本月起迄日期）
2. 遍歷每個 source layer 的 `docs/Extractor/{layer}/{category}/` 目錄
3. 從每個 .md 檔提取成分段落，解析成分清單
4. 執行成分名稱標準化（同義詞合併、日文對照）
5. 統計各成分出現的產品數、涵蓋市場、主要品類
6. 產出全球 Top 20 + 各市場 Top 10 排名
7. 分析跨國差異（成分 × 市場交叉表）
8. 撰寫趨勢觀察

### 成分名稱標準化對照表

| 原始名稱 | 標準名稱 |
|----------|----------|
| Vitamin D3, Cholecalciferol, コレカルシフェロール | Vitamin D3 |
| DHA, Docosahexaenoic acid | DHA |
| EPA, Eicosapentaenoic acid | EPA |
| ビタミンC, Vitamin C, Ascorbic acid | Vitamin C |
| ビフィズス菌, Bifidobacterium | Bifidobacterium |
| 乳酸菌, Lactobacillus | Lactobacillus |
| GABA, γ-アミノ酪酸 | GABA |
| ルテイン, Lutein | Lutein |
| 難消化性デキストリン, Indigestible dextrin | Indigestible Dextrin |
| 茶カテキン, Tea catechins | Tea Catechins |
| イソフラボン, Isoflavone | Isoflavone |
| 葉酸, Folic acid, Folate | Folate |
| コラーゲン, Collagen | Collagen |
| グルコサミン, Glucosamine | Glucosamine |

> 此對照表隨資料累積持續擴充。新增對照需與使用者確認。

## 新興/值得關注成分判定規則

### 值得關注的成分

從以下維度識別 3-5 個值得深入追蹤的成分：

| 類型 | 判定標準 | 說明 |
|------|----------|------|
| **跨國潛力成分** | 在 2+ 個市場同時出現 Top 20 | 多國監管機關認可，具跨國發展潛力 |
| **區域獨特成分** | 僅在單一市場 Top 10，其他市場罕見 | 可能具有區域文化特色或專利壁壘 |
| **高成長成分** | 相較上期報告排名上升 5+ 名 | 若有歷史資料可比對時使用 |
| **新登場成分** | 本期首次進入 Top 20 | 新興趨勢信號 |

### 判定優先順序

1. 若有上期報告可比對 → 優先識別「高成長」和「新登場」成分
2. 若為首期報告或無歷史資料 → 聚焦「跨國潛力」和「區域獨特」成分
3. 避免選擇已飽和的基礎成分（如 Vitamin C、Calcium 已普遍存在）

### 輸出格式

每個值得關注的成分需包含：
- **成分名稱**
- **關注原因**（符合上述哪項標準）
- **涵蓋市場**
- **所屬品類**
- **後續追蹤建議**（如：監測下月排名變化、調查區域法規差異）

## 自我審核 Checklist

### 資料正確性
- [ ] 報告期間正確
- [ ] 成分統計數字可追溯（每個成分可對應到具體產品 .md 檔）
- [ ] 成分名稱標準化一致（同一成分未重複計算）
- [ ] 日文成分名已對照英文（有對照表的項目）
- [ ] 排名表無重複項
- [ ] 跨國比較考慮了資料量差異（不以絕對數量做不公平比較）

### 趨勢分析
- [ ] 趨勢觀察有資料支撐，無無中生有的判斷
- [ ] 「值得關注的成分」符合判定規則（見上方判定標準）
- [ ] 方法論說明完整

### REVIEW_NEEDED 處理
- [ ] 帶有 `[REVIEW_NEEDED]` 的產品已靜默排除
- [ ] 報告中**無**以下表述：
  - ❌ "排除 N 筆 REVIEW_NEEDED"
  - ❌ "REVIEW_NEEDED 產品佔比 X%"
  - ❌ "資料品質問題 N 筆"
- [ ] 可使用的替代表述：
  - ✅ "成功萃取成分資訊的產品達 N 筆"
  - ✅ "本期分析涵蓋 N 筆產品"

### 合規性
- [ ] 免責聲明完整
- [ ] 未包含配方建議或法規諮詢性質的內容

---

## ⚠️ 子代理精簡回報規範

完成後**只輸出一行**：
```
DONE|ingredient_radar|{YYYY-MM}|{總產品數}|OK
```

範例：
```
DONE|ingredient_radar|2026-02|346446|OK
```

**禁止**：
- ❌ 輸出成分排名表
- ❌ 列舉 Top 20 成分
- ❌ 重複跨國比較表
