# 保健食品產品情報系統

全球保健食品（膳食補充品）產品資料擷取、萃取與分析系統。透過 Claude CLI 編排多角色協作，自動從各國官方資料庫收集產品情報。

## 涵蓋市場

| 市場 | Layer | 資料源 | 狀態 |
|------|-------|--------|------|
| 🇺🇸 美國 | `us_dsld` | NIH DSLD Bulk Download | ✅ 已建置 |
| 🇨🇦 加拿大 | `ca_lnhpd` | Health Canada LNHPD API | ✅ 已建置 |
| 🇰🇷 韓國 | `kr_hff` | MFDS API | ✅ 已建置 |
| 🇯🇵 日本 | `jp_foshu` | CAA FOSHU Excel | ✅ 已建置 |
| 🇯🇵 日本 | `jp_fnfc` | CAA FNFC CSV | ✅ 已建置（半自動） |
| 🇹🇼 台灣 | `tw_hf` | 衛福部健康食品資料庫 | ✅ 已建置 |
| 🇹🇭 泰國 | `th_fda` | Thai FDA API | ❌ 暫緩（無公開資料源） |

## 系統健康度

### Extractor Layers

| Layer | 最後更新 | 萃取筆數 | REVIEW_NEEDED | Qdrant 寫入 | 狀態 |
|-------|----------|----------|---------------|-------------|------|
| us_dsld | 2026-06-17 | 214,780 | 9,042 | ✅ 完成 | ✅ 正常（本期無新增） |
| ca_lnhpd | 2026-06-17 | 150,250 | 4,805 | ✅ 完成 | ✅ 正常（增量 +1,024） |
| kr_hff | 2026-06-17 | 46,715 | 40 | ✅ 完成 | ✅ 正常（增量 +1,585） |
| jp_foshu | 2026-06-17 | 1,036 | 1 | ✅ 完成 | ✅ 正常 |
| jp_fnfc | 2026-06-18 | 11,094 | 0 | ✅ 完成 | ✅ 正常（瀏覽器自動下載全届出 CSV） |
| tw_hf | 2026-06-17 | 561 | 8 | ✅ 完成 | ✅ 正常 |
| pubmed | 2026-06-17 | 88,802 | 5,034 | ✅ 完成 | ✅ 正常（增量 +18,875） |
| dhi | 2026-06-17 | 897 | 739 | ✅ 完成 | ✅ 正常（藥物-補充劑交互） |
| dfi | 2026-06-17 | 361 | 250 | ✅ 完成 | ✅ 正常（藥物-食物交互） |
| ddi | 2026-06-17 | 286 | 191 | ✅ 完成 | ✅ 正常（藥物-藥物交互） |
| th_fda | — | 0 | — | — | ❌ 暫緩（.disabled） |

### Narrator Modes

| Mode | 最後產出 | 輸出檔案 | 狀態 |
|------|----------|----------|------|
| market_snapshot | 2026-06-17 | `2026-W25-market-snapshot.md` | ✅ 正常（週報） |
| ingredient_radar | 2026-06-17 | `2026-06-ingredient-radar.md` | ✅ 正常（月報） |
| topic_tracking | 2026-06-17 | `{topic}/2026-06.md` ×26 主題 | ✅ 正常（月報） |
| literature_review | 2026-06-17 | `{topic}/2026-06.md` ×26 主題 | ✅ 正常（月報） |

## 快速開始

### 環境需求

- Claude CLI
- bash, curl, jq
- `.env` 設定檔（見下方）

### .env 設定

```bash
QDRANT_URL=...
QDRANT_API_KEY=...
QDRANT_COLLECTION=supplement-product
EMBEDDING_MODEL=text-embedding-3-small
EMBEDDING_DIMENSION=1536
OPENAI_API_KEY=sk-...

# 第二階段
MFDS_API_KEY=...           # 韓國 data.go.kr 服務金鑰
```

### 執行

```bash
# 在 Claude CLI 中執行完整流程
claude "執行完整流程"

# 只執行特定 Layer
claude "執行 us_dsld"

# 只跑 fetch
claude "只跑 fetch"
```

## 架構

```
core/
├── Architect/     # 系統編排（Claude CLI 直接扮演）
├── Extractor/     # 資料擷取 + 萃取
│   └── Layers/    # 各市場 Layer
└── Narrator/      # 綜合分析報告
    └── Modes/     # 各類報告模式

docs/
├── Extractor/     # 萃取結果（.md 檔）
└── Narrator/      # 報告輸出

lib/               # 共用 shell 工具
```
