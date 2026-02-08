---
mode: "market_snapshot"
period: "2026-W05"
generated_at: "2026-01-27T19:03:30Z"
source_layers:
  - us_dsld
  - ca_lnhpd
  - kr_hff
  - jp_foshu
  - jp_fnfc
---

# 市場快照週報 — 2026 年第 5 週

> 報告期間：2026-01-26 ~ 2026-02-01
> 產出時間：2026-01-27T19:03:30Z

## 摘要

本週四國五個資料庫共收錄 15,661 筆保健食品產品登記資訊，排除 545 筆 REVIEW_NEEDED 標記後，有效統計產品為 15,116 筆。美國 DSLD 貢獻最多（10,000 筆），其次為韓國 HFF（4,600 筆）、日本 FOSHU（1,032 筆）及加拿大 LNHPD（29 筆）。品類方面，botanicals（4,458 筆）與 specialty（4,028 筆）為全球前兩大品類，合計佔總量 54.2%，主要由美國市場驅動。韓國市場則以 other（1,330 筆）和 probiotics（1,274 筆）為主，反映韓國在複合配方與益生菌產品的強勢地位。日本 FNFC 因需手動下載 CSV，本週無資料。

## 各市場概況

### 🇺🇸 美國（us_dsld）
- 本週收錄：9,475 筆（排除 525 筆 REVIEW_NEEDED 後）
- 熱門品類：botanicals（3,855 筆）、specialty（3,109 筆）、other（1,237 筆）
- 亮點：美國市場以植物萃取類產品佔比最高（38.6%），代表產品如 Gaia Herbs "Olive Leaf"（botanicals, capsule）。specialty 類佔比 31.1%，顯示美國市場的複方保健食品登記量大。vitamins_minerals（1,053 筆）與 protein_amino（418 筆）亦有一定規模。值得注意的是，probiotics 與 sports_fitness 在本批 DSLD 資料中未有登記。品牌涵蓋範圍多元，橫跨 vitamins、botanicals、specialty 等品類。

### 🇨🇦 加拿大（ca_lnhpd）
- 本週收錄：29 筆（REVIEW_NEEDED: 0 筆）
- 熱門品類：vitamins_minerals（14 筆）、botanicals（7 筆）、other（6 筆）
- 亮點：加拿大市場以維生素與礦物質為主（48.3%），代表產品如 Jamieson "Vitamin D 400 IU"（vitamins_minerals, tablet）。本週因 fetch 過程超時，僅取得部分資料（29 筆），不代表加拿大市場的完整規模。omega_fatty_acids（1 筆）與 sports_fitness（1 筆）各有少量登記。

### 🇰🇷 韓國（kr_hff）
- 本週收錄：4,581 筆（排除 19 筆 REVIEW_NEEDED 後）
- 熱門品類：other（1,330 筆）、probiotics（1,274 筆）、specialty（915 筆）
- 亮點：韓國市場品類結構與其他市場差異顯著。other 類佔比最高（28.9%），反映韓國登記制度下大量產品難以歸入單一品類。probiotics 佔 27.7%，代表產品如 (주)비피도 "KERUIYA PROBIO BEBE PLUS"（probiotics, powder），顯示韓國消費者對益生菌產品的強勁需求。specialty（915 筆）佔 19.9%，代表複方保健食品。botanicals 僅 130 筆（2.8%），與美國形成鮮明對比。

### 🇯🇵 日本 — FOSHU（jp_foshu）
- 本週收錄：1,031 筆（排除 1 筆 REVIEW_NEEDED 後）
- 熱門品類：botanicals（466 筆）、other（359 筆）、protein_amino（85 筆）
- 亮點：日本 FOSHU 市場以 botanicals 佔比最高（45.2%），代表產品如株式会社東洋新薬 "ハッピー ファイバー"（botanicals, powder），反映日本特保制度下植物來源機能性食品的高佔比。other 類（359 筆，34.8%）同樣佔比顯著。probiotics（49 筆）在 FOSHU 制度下佔比不高（4.7%），但日本 FOSHU 的益生菌產品以發酵乳飲料型態為主，與其他市場膠囊粉末型態不同。

### 🇯🇵 日本 — FNFC（jp_fnfc）
- 本週收錄：0 筆
- 備註：FNFC 資料需手動下載 CSV 檔案，本週未取得資料

## 品類分布

| Category | 🇺🇸 US | 🇨🇦 CA | 🇰🇷 KR | 🇯🇵 FOSHU | 🇯🇵 FNFC | 合計 |
|----------|---------|---------|---------|-----------|-----------|------|
| vitamins_minerals | 1,053 | 14 | 701 | 54 | 0 | 1,822 |
| botanicals | 3,855 | 7 | 130 | 466 | 0 | 4,458 |
| protein_amino | 418 | 0 | 164 | 85 | 0 | 667 |
| probiotics | 0 | 0 | 1,274 | 49 | 0 | 1,323 |
| omega_fatty_acids | 328 | 1 | 63 | 15 | 0 | 407 |
| specialty | 3,109 | 0 | 915 | 4 | 0 | 4,028 |
| sports_fitness | 0 | 1 | 23 | 0 | 0 | 24 |
| other | 1,237 | 6 | 1,330 | 359 | 0 | 2,932 |
| **合計** | **10,000** | **29** | **4,600** | **1,032** | **0** | **15,661** |

> 注：品類分布表為各 Layer 全量統計（含 REVIEW_NEEDED 產品），因 REVIEW_NEEDED 無逐品類分布資料。排除 REVIEW_NEEDED 後的有效產品合計為 15,116 筆。

## 跨國比較觀察

**品類結構的顯著差異反映各國監管制度與消費偏好。** 美國市場以 botanicals（3,855 筆，38.6%）和 specialty（3,109 筆，31.1%）為主導，兩者合計佔美國登記量的 69.6%，顯示美國膳食補充劑市場偏好植物萃取類與複方產品。韓國市場則以 other（1,330 筆，28.9%）和 probiotics（1,274 筆，27.7%）為兩大支柱，益生菌佔比遠超其他市場。日本 FOSHU 以 botanicals（466 筆，45.2%）領先，但其 botanicals 內容多為寡糖、膳食纖維等機能性成分，與美國草本植物為主的 botanicals 定義有所不同。加拿大則以 vitamins_minerals（14 筆，48.3%）為主，但因本週僅取得 29 筆資料，分布可能不具代表性。

**益生菌品類集中於東亞市場。** 在全部 1,323 筆 probiotics 產品中，韓國佔 1,274 筆（96.3%），日本 FOSHU 佔 49 筆（3.7%），美國與加拿大在本批資料中均為 0 筆。韓國益生菌產品多以粉末劑型呈現，且傾向高菌數規格；日本 FOSHU 的益生菌則以發酵乳飲料為主要型態。此分布差異可能受各國登記制度、消費者腸道健康意識以及傳統飲食文化影響。美國 DSLD 本批未錄得 probiotics 登記，但這不代表美國市場無益生菌產品，可能與 DSLD 資料庫的收錄範圍或本批抽樣有關。

**specialty 品類的跨國分布揭示複方產品的市場需求。** specialty 品類全球合計 4,028 筆，美國佔 3,109 筆（77.2%）、韓國佔 915 筆（22.7%）、日本 FOSHU 僅 4 筆（0.1%）、加拿大為 0 筆。美國與韓國在複方保健食品的登記量較大，反映兩國消費者對「一站式」多機能配方的接受度較高。日本 FOSHU 制度傾向針對單一機能宣稱進行審核，因此 specialty 類登記稀少。sports_fitness 品類在所有市場均為極低佔比（合計僅 24 筆），可能因運動保健產品多以一般食品而非保健食品登記，或分類上多歸入 protein_amino 等其他品類。

## 資料品質備註

- 帶有 `[REVIEW_NEEDED]` 標記：545 筆（US 525 筆、KR 19 筆、JP FOSHU 1 筆），未納入各市場概況的收錄筆數統計，但品類分布表為全量數據
- 不可用的 Layer：th_fda（已停用 disabled）、jp_fnfc（本週無資料，需手動下載 CSV）
- 資料完整度：
  - us_dsld：10,000 筆（REVIEW_NEEDED 525 筆，佔 5.3%）
  - ca_lnhpd：29 筆（因 fetch 超時僅取得部分資料，不代表加拿大市場完整規模）
  - kr_hff：4,600 筆（REVIEW_NEEDED 19 筆，佔 0.4%）
  - jp_foshu：1,032 筆（REVIEW_NEEDED 1 筆，佔 0.1%）
  - jp_fnfc：0 筆（需手動下載 CSV，本週無資料）
- 品類分布表使用各 Layer 全量數據（含 REVIEW_NEEDED），因 REVIEW_NEEDED 無逐品類拆分資訊；排除 REVIEW_NEEDED 後的有效產品合計為 15,116 筆

## 免責聲明

本報告由 AI 自動生成，基於各國官方公開資料庫的產品登記資訊。報告內容僅供參考，不構成任何商業建議或投資建議。產品統計以資料庫登記為準，不代表實際市場銷售狀況。各國監管制度不同，跨國比較應考慮法規差異。
