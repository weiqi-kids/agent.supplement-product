# Mode: market_snapshot — 市場快照週報

## Mode 定義表

| 項目 | 說明 |
|------|------|
| **Mode name** | market_snapshot（市場快照） |
| **Purpose and audience** | 每週彙整各國保健食品市場動態，提供新產品趨勢與品類分布概覽。目標受眾：產品經理、品牌策略、通路規劃 |
| **Source layers** | `us_dsld`, `ca_lnhpd`, `kr_hff`, `jp_foshu`, `jp_fnfc` |
| **Automation ratio** | 90% — 資料匯整自動化，趨勢判讀需人工確認 |
| **Content risk** | 趨勢推斷可能過度簡化、跨國比較需考慮監管差異 |
| **Reviewer persona** | 資料可信度審核員、邏輯一致性審核員 |

## 資料來源定義

### 從 docs/Extractor/ 讀取

- `docs/Extractor/us_dsld/{category}/*.md` — 美國 DSLD 產品
- `docs/Extractor/ca_lnhpd/{category}/*.md` — 加拿大 LNHPD 產品
- `docs/Extractor/kr_hff/{category}/*.md` — 韓國健康機能食品
- `docs/Extractor/jp_foshu/{category}/*.md` — 日本特定保健用食品
- `docs/Extractor/jp_fnfc/{category}/*.md` — 日本機能性表示食品

### 篩選邏輯

- **時間範圍**：預設取最近 7 天內 `fetched_at` 的產品
- **排除**：帶有 `[REVIEW_NEEDED]` 標記的產品靜默排除，不納入統計，**報告中不顯示 REVIEW_NEEDED 數量**
- **disabled Layer**：自動跳過帶有 `.disabled` 的 Layer

### 從 Qdrant 查詢（可選）

- 若需比較「本週新增 vs 歷史資料」，可透過 Qdrant filter 查詢特定 `source_layer` + `category` 的 point 數量
- 此為可選步驟，Qdrant 不可用時降級為僅基於本地 .md 檔統計

## 輸出框架

```markdown
---
mode: "market_snapshot"
period: "{YYYY}-W{WW}"
generated_at: "{ISO8601}"
source_layers:
  - us_dsld
  - ca_lnhpd
  - kr_hff
  - jp_foshu
  - jp_fnfc
---

# 市場快照週報 — {YYYY} 年第 {WW} 週

> 報告期間：{start_date} ~ {end_date}
> 產出時間：{generated_at}

## 摘要

{3-5 句話概述本週重點：新增產品總數、各市場動態、值得關注的趨勢}

## 各市場概況

### 🇺🇸 美國（us_dsld）
- 本週新增：{N} 筆
- 熱門品類：{top 3 categories with counts}
- 亮點：{notable products or trends}

### 🇨🇦 加拿大（ca_lnhpd）
- 本週新增：{N} 筆
- 熱門品類：{top 3 categories}
- 亮點：{notable}

### 🇰🇷 韓國（kr_hff）
- 本週新增：{N} 筆
- 熱門品類：{top 3 categories}
- 亮點：{notable}

### 🇯🇵 日本 — FOSHU（jp_foshu）
- 本週新增：{N} 筆
- 熱門品類：{top 3 categories}
- 亮點：{notable}

### 🇯🇵 日本 — FNFC（jp_fnfc）
- 本週新增：{N} 筆
- 熱門品類：{top 3 categories}
- 亮點：{notable}

## 品類分布

| Category | 🇺🇸 US | 🇨🇦 CA | 🇰🇷 KR | 🇯🇵 FOSHU | 🇯🇵 FNFC | 合計 |
|----------|---------|---------|---------|-----------|-----------|------|
| vitamins_minerals | {n} | {n} | {n} | {n} | {n} | {N} |
| botanicals | {n} | {n} | {n} | {n} | {n} | {N} |
| protein_amino | {n} | {n} | {n} | {n} | {n} | {N} |
| probiotics | {n} | {n} | {n} | {n} | {n} | {N} |
| omega_fatty_acids | {n} | {n} | {n} | {n} | {n} | {N} |
| specialty | {n} | {n} | {n} | {n} | {n} | {N} |
| sports_fitness | {n} | {n} | {n} | {n} | {n} | {N} |
| other | {n} | {n} | {n} | {n} | {n} | {N} |
| **合計** | **{N}** | **{N}** | **{N}** | **{N}** | **{N}** | **{N}** |

## 跨國比較觀察

{2-3 段落的跨國趨勢分析：}
- 哪些品類在多個市場同時成長？
- 各國品類偏好差異
- 值得關注的跨國趨勢

## 資料品質備註

- 不可用的 Layer：{list of disabled layers}
- 資料完整度：{各 Layer 的資料狀態簡述}

## 免責聲明

本報告由 AI 自動生成，基於各國官方公開資料庫的產品登記資訊。報告內容僅供參考，不構成任何商業建議或投資建議。產品統計以資料庫登記為準，不代表實際市場銷售狀況。各國監管制度不同，跨國比較應考慮法規差異。
```

## 輸出位置

`docs/Narrator/market_snapshot/{YYYY}-W{WW}-market-snapshot.md`

範例：`docs/Narrator/market_snapshot/2026-W04-market-snapshot.md`

## 執行邏輯

1. 確定報告期間（本週起迄日期、ISO week number）
2. 遍歷每個 source layer 的 `docs/Extractor/{layer}/{category}/` 目錄
3. 統計各 category 下的 .md 檔案數量（以 `fetched_at` 判斷是否在報告期間內）
4. 讀取具代表性的產品 .md 檔（每個市場最多 3-5 個）以提取亮點
5. 彙整品類分布交叉表
6. 撰寫跨國比較觀察
7. 補充資料品質備註

## 自我審核 Checklist

### 資料正確性
- [ ] 報告期間正確（起迄日期、週數）
- [ ] 各市場統計數字準確（與 .md 檔案數一致）
- [ ] 品類分布表行列加總正確
- [ ] 跨國比較觀察有具體資料支撐

### REVIEW_NEEDED 處理
- [ ] 帶有 `[REVIEW_NEEDED]` 的產品已靜默排除
- [ ] 報告中**無**以下表述：
  - ❌ "排除 N 筆 REVIEW_NEEDED"
  - ❌ "REVIEW_NEEDED 產品佔比 X%"
  - ❌ "資料品質問題 N 筆"
- [ ] 可使用的替代表述：
  - ✅ "成功萃取完整資訊的產品達 N 筆"
  - ✅ "本期分析涵蓋 N 筆產品"

### 合規性
- [ ] disabled Layer 已標註
- [ ] 免責聲明完整
- [ ] 未包含無法驗證的推測性陳述
- [ ] 無「本報告是完整/全面的」等過度聲明
