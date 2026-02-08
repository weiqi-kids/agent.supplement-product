# 資料源探索紀錄

## 已採用

| 資料源 | 類型 | 對應 Layer | 採用日期 | 備註 |
|--------|------|-----------|----------|------|
| NIH DSLD (Dietary Supplement Label Database) | REST API | `us_dsld` | 2026-01-27 | 免 API Key，~214K 產品 |
| Health Canada LNHPD | REST API (Bulk) | `ca_lnhpd` | 2026-01-27 | 免 API Key，~120K 產品，Bulk 端點 139MB |
| MFDS 건강기능식품 | REST API | `kr_hff` | 2026-01-27 | 需 data.go.kr API Key |
| CAA 特定保健用食品 (FOSHU) | Excel 下載 | `jp_foshu` | 2026-01-27 | 免 Key，~1034 產品，openpyxl 解析 |
| CAA 機能性表示食品 (FNFC) | CSV 手動下載 | `jp_fnfc` | 2026-01-27 | 免 Key，~10K+ 產品，需手動下載 CSV |

## 評估中

| 資料源 | 類型 | URL | 語言 | 發現日期 | 狀態 | 下次評估 |
|--------|------|-----|------|----------|------|----------|
| （目前無評估中項目）| — | — | — | — | — | — |

## 已排除

| 資料源 | 類型 | 排除原因 | 排除日期 | 重新評估時間 |
|--------|------|----------|----------|-------------|
| Thai FDA | REST API | 無公開 API 或批量下載管道；data.go.th 僅有有限食品資料，無保健食品專用端點 | 2026-01-27 | 2026-Q3（待泰國 Open Data 平台更新） |
