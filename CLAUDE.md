# 保健食品產品情報系統 — 執行指令

本系統採用 **背景多工架構**：主執行緒負責監控與使用者互動，子代理在背景平行處理任務。

---

## 架構概覽

```
┌─────────────────────────────────────────────────────────────────┐
│  主執行緒 (Opus)                                                │
│  ├── 監控所有背景任務進度                                       │
│  ├── 與使用者互動（可同時處理其他請求）                         │
│  └── 彙整結果並回報                                             │
├─────────────────────────────────────────────────────────────────┤
│  背景子代理 (Sonnet × N，平行執行)                              │
│  ├── [Layer] us_dsld   → fetch → extract → update              │
│  ├── [Layer] ca_lnhpd  → fetch → extract → update              │
│  ├── [Layer] kr_hff    → fetch → extract → update              │
│  ├── [Layer] jp_fnfc   → fetch → extract → update              │
│  ├── [Layer] jp_foshu  → fetch → extract → update              │
│  ├── [Layer] tw_hf     → fetch → extract → update              │
│  ├── [Layer] pubmed    → fetch → extract → update              │
│  ├── [Mode]  market_snapshot    → 報告產出                      │
│  ├── [Mode]  ingredient_radar   → 報告產出                      │
│  ├── [Mode]  topic_tracking     → 主題追蹤報告                  │
│  └── [Mode]  literature_review  → 文獻薈萃報告                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 快速指令

| 指令 | 行為 |
|------|------|
| `執行完整流程` | 背景平行執行所有 Layer + Mode + 主題追蹤 + 推薦 + Jekyll |
| `更新資料` | 同上 |
| `執行 {layer}` | 背景執行單一 Layer（如 `執行 us_dsld`） |
| `執行 {mode}` | 背景執行單一 Mode（如 `執行 market_snapshot`） |
| `只跑 fetch` | 背景平行執行所有 Layer 的 fetch.sh |
| `只跑萃取` | 背景平行執行所有 Layer 的萃取腳本 |
| `建置 HTML` | 前景執行 `python3 scripts/build_html.py` |
| `查看進度` | 顯示所有背景任務狀態 |
| `推薦主題` | 執行 `python3 scripts/recommend_topics.py` |
| `新增主題` | 執行 `python3 scripts/create_topic.py --interactive` |

---

## 執行流程

### 階段一：發現（前景，快速）

```bash
# 發現所有有效 Layer
ls -d core/Extractor/Layers/*/ | grep -v '.disabled'

# 發現所有有效 Mode
ls -d core/Narrator/Modes/*/ | grep -v '.disabled'

# 發現所有追蹤主題
ls core/Narrator/Modes/topic_tracking/topics/*.yaml
```

### 階段二：資料處理（背景，平行）

**對每個 Layer 啟動一個背景子代理**（Sonnet, `run_in_background: true`）：

```
Task(
  subagent_type: "general-purpose",
  model: "sonnet",
  run_in_background: true,
  prompt: "執行 {layer_name} 的完整資料處理流程..."
)
```

每個子代理依序執行：
1. `fetch.sh` — 下載原始資料
2. `extract_{layer}.py` — 萃取為 `.md`
3. `update.sh` — 寫入 Qdrant（可選）

**Layer 清單**：

| Layer | 資料來源 | 預估時間 | 狀態 |
|-------|----------|----------|------|
| `us_dsld` | 美國膳食補充劑標示資料庫 | 2-5 分鐘 | ✅ 啟用 |
| `ca_lnhpd` | 加拿大天然健康產品資料庫 | 3-8 分鐘 | ✅ 啟用 |
| `kr_hff` | 韓國健康機能食品資料庫 | 2-5 分鐘 | ✅ 啟用 |
| `jp_fnfc` | 日本機能性表示食品資料庫 | 1-2 分鐘 | ✅ 啟用 |
| `jp_foshu` | 日本特定保健用食品資料庫 | 1-2 分鐘 | ✅ 啟用 |
| `tw_hf` | 台灣衛福部健康食品資料庫 | 1 分鐘 | ✅ 啟用 |
| `pubmed` | PubMed 學術文獻資料庫 | 2-5 分鐘 | ✅ 啟用 |
| `th_fda` | 泰國 FDA 健康食品資料庫 | — | ❌ 已禁用 |

> 禁用的 Layer 帶有 `.disabled` 標記，執行流程會自動跳過。

### 階段三：報告產出（背景，平行）

**等待階段二完成後**，對每個 Mode 啟動背景子代理（Sonnet）：

```
Task(
  subagent_type: "general-purpose",
  model: "sonnet",
  run_in_background: true,
  prompt: "依據 {mode_name}/CLAUDE.md 產出報告..."
)
```

**Mode 清單**：

| Mode | 輸出位置 | 報告週期 |
|------|----------|----------|
| `market_snapshot` | `docs/Narrator/market_snapshot/` | 週報 |
| `ingredient_radar` | `docs/Narrator/ingredient_radar/` | 月報 |
| `topic_tracking` | `docs/Narrator/topic_tracking/{topic}/` | 月報 |
| `literature_review` | `docs/Narrator/literature_review/{topic}/` | 月報 |

**追蹤主題清單**（定義於 `core/Narrator/Modes/topic_tracking/topics/`）：

| 主題 ID | 名稱 | 關鍵詞範例 |
|---------|------|-----------|
| `exosomes` | 外泌體 | exosome, stem cell, 幹細胞 |
| `fish-oil` | 魚油 | omega-3, EPA, DHA, krill oil |

> 主題可透過 `python3 scripts/create_topic.py` 新增

### 階段四：主題推薦（前景）

Mode 報告完成後，分析成分趨勢並推薦新追蹤主題：

```bash
python3 scripts/recommend_topics.py
```

推薦邏輯：
- 成長趨勢：排名上升 5+ 位的成分
- 跨國熱門：3+ 個市場同時 Top 20
- 新興成分：首次進入全球 Top 50
- 排除已追蹤主題

### 階段五：Jekyll 轉換 + 部署（前景）

所有報告完成後，轉換為 Jekyll 格式：

```bash
python3 scripts/convert_to_jekyll.py
```

輸出至 `docs/reports/`，供 GitHub Pages 發布。

---

## 子代理 Prompt 範本

### Layer 處理子代理

```markdown
你是 {layer_name} 資料處理子代理。

## 任務
1. 執行 fetch.sh 下載原始資料
2. 執行萃取腳本將 JSONL 轉為 MD
3. 執行 update.sh 寫入 Qdrant（若有設定）

## 路徑
- fetch: core/Extractor/Layers/{layer_name}/fetch.sh
- 萃取: scripts/extract_{layer_name}.py
- update: core/Extractor/Layers/{layer_name}/update.sh
- 輸出: docs/Extractor/{layer_name}/

## 規格
讀取 core/Extractor/Layers/{layer_name}/CLAUDE.md 了解詳細規格。

## 回報格式
完成後回報：
- 擷取筆數
- 萃取筆數
- REVIEW_NEEDED 筆數
- 是否有錯誤
```

### Mode 報告子代理

```markdown
你是 {mode_name} 報告產出子代理。

## 任務
依據 Mode 規格產出報告。

## 規格來源
1. core/Narrator/CLAUDE.md（通用規格）
2. core/Narrator/Modes/{mode_name}/CLAUDE.md（Mode 專屬規格）

## 資料來源
讀取 CLAUDE.md 中宣告的 Layer 資料（docs/Extractor/{layer}/）

## 輸出
寫入 docs/Narrator/{mode_name}/{period}-{mode_name}.md

## 回報格式
完成後回報：
- 報告檔名
- 涵蓋資料筆數
- 是否有 REVIEW_NEEDED
```

### 主題追蹤子代理

```markdown
你是 topic_tracking 報告產出子代理。

## 任務
執行主題追蹤報告產出。

## 執行指令
python3 scripts/generate_topic_report.py

## 規格來源
1. core/Narrator/Modes/topic_tracking/CLAUDE.md
2. core/Narrator/Modes/topic_tracking/topics/*.yaml（主題定義）

## 資料來源
從 docs/Extractor/{layer}/{category}/*.md 篩選符合主題關鍵詞的產品

## 輸出
- docs/Narrator/topic_tracking/{topic_id}/{period}.md

## 回報格式
完成後回報：
- 處理的主題數
- 各主題匹配產品數
- 是否有錯誤
```

### 文獻薈萃子代理

```markdown
你是 literature_review 報告產出子代理。

## 任務
執行文獻薈萃報告產出。

## 執行指令
python3 scripts/generate_literature_report.py --all

## 規格來源
1. core/Narrator/Modes/literature_review/CLAUDE.md
2. core/Narrator/Modes/topic_tracking/topics/*.yaml（主題定義）

## 資料來源
從 docs/Extractor/pubmed/{topic}/*.md 讀取文獻資料

## 輸出
- docs/Narrator/literature_review/{topic_id}/{period}.md

## 回報格式
完成後回報：
- 處理的主題數
- 各主題文獻數
- 證據等級分布
- 是否有錯誤
```

---

## 主執行緒職責

### 啟動階段
1. 發現所有有效 Layer 和 Mode
2. 平行啟動所有 Layer 子代理（`run_in_background: true`）
3. 告知使用者「已啟動 N 個背景任務，你可以繼續其他工作」

### 監控階段
- 定期檢查背景任務狀態（使用 `Read` 讀取 output_file）
- 回應使用者的其他請求
- 使用者說「查看進度」時顯示所有任務狀態

### 彙整階段
1. 等待所有 Layer 完成
2. 平行啟動所有 Mode 子代理
3. 等待所有 Mode 完成
4. 執行 HTML 建置
5. 產出最終報告

---

## 進度追蹤格式

```
📊 執行進度
═══════════════════════════════════════

Layer 處理（5/7 完成）
├── ✅ us_dsld    214,780 筆 | 0 REVIEW
├── ✅ ca_lnhpd   160,545 筆 | 5,164 REVIEW
├── ✅ kr_hff     44,095 筆 | 30 REVIEW
├── ⏳ jp_fnfc    執行中...
├── ⏳ jp_foshu   等待中
├── ⏳ tw_hf      等待中
└── ⏳ pubmed     等待中

Mode 報告（等待 Layer 完成）
├── ⏸️ market_snapshot
├── ⏸️ ingredient_radar
├── ⏸️ topic_tracking
│   ├── exosomes
│   └── fish-oil
└── ⏸️ literature_review
    ├── exosomes
    └── fish-oil

主題推薦（等待 Mode 完成）
└── ⏸️ recommend_topics.py

Jekyll 轉換（等待推薦完成）
└── ⏸️ convert_to_jekyll.py
```

---

## 萃取腳本對照表

| Layer | fetch 輸出 | 萃取指令 |
|-------|-----------|---------|
| ca_lnhpd | `raw/products-*.jsonl` | 見下方詳細說明 |
| jp_fnfc | `raw/fnfc-*.jsonl` | `python3 scripts/extract_jp_fnfc.py` |
| jp_foshu | `raw/foshu-*.jsonl` | `python3 scripts/extract_jp_foshu.py` |
| kr_hff | `raw/hff-*.jsonl` | `python3 scripts/extract_kr_hff.py` |
| us_dsld | `raw/dsld-*.jsonl` | `python3 scripts/extract_us_dsld.py` |
| tw_hf | `raw/tw_hf-*.jsonl` | `python3 scripts/extract_tw_hf.py` |
| pubmed | `raw/{topic}-*.jsonl` | `python3 scripts/extract_pubmed.py [--topic {topic}]` |

### ca_lnhpd 萃取指令詳細說明

```bash
# 基本用法（僅產品資料）
python3 scripts/extract_ca_lnhpd.py <products.jsonl>

# 含成分資料（需先下載 ingredients.jsonl）
python3 scripts/extract_ca_lnhpd.py --ingredients <ingredients.jsonl> <products.jsonl>

# 增量更新模式
python3 scripts/extract_ca_lnhpd.py --delta <delta.jsonl>

# 增量 + 成分
python3 scripts/extract_ca_lnhpd.py --delta --ingredients <ingredients.jsonl> <delta.jsonl>
```

### 萃取腳本不存在時

若 `scripts/extract_{layer}.py` 不存在，子代理改用逐行處理：

```
⛔ 禁止 Read 工具直接讀取 .jsonl（可能數 MB）

✅ wc -l < {jsonl}           → 取得總行數
✅ sed -n '{N}p' {jsonl}     → 逐行讀取
✅ 每行獨立處理              → Write tool 寫出 .md
```

### update.sh 參數說明

所有 Layer 的 `update.sh` 支援以下參數：

```bash
# 增量模式（預設）：只處理比 .last_qdrant_update 更新的檔案
./update.sh

# 全量模式：處理所有 .md 檔案
./update.sh --full

# 指定檔案清單：處理特定檔案
./update.sh /path/to/file1.md /path/to/file2.md
```

**增量更新機制**：
- 每次成功執行後，會更新 `.last_qdrant_update` 時間戳檔案
- 下次執行時，只處理比此時間戳更新的 `.md` 檔案
- 首次執行（無時間戳檔案）會處理所有檔案
- 批次大小：200 筆/批（原 50 筆，提升 4 倍效率）

---

## 環境設定

`.env` 檔案：

```bash
# Qdrant 向量資料庫（可選）
QDRANT_URL=...
QDRANT_API_KEY=...
QDRANT_COLLECTION=supplement-product

# OpenAI Embedding（可選）
EMBEDDING_MODEL=text-embedding-3-small
EMBEDDING_DIMENSION=1536
OPENAI_API_KEY=sk-...

# 韓國 MFDS API
MFDS_API_KEY=...

# 日本 jp_fnfc CSV 下載 URL（可選）
# Salesforce Document ID 可能變更，若自動下載失敗，請更新此 URL
# JP_FNFC_DOWNLOAD_URL=https://www.fld.caa.go.jp/caaks/sfc/servlet.shepherd/document/download/{新ID}?operationContext=S1

# PubMed API（可選，提高速率）
# 無 Key: 3 req/s；有 Key: 10 req/s
NCBI_API_KEY=...
NCBI_EMAIL=your-email@example.com
```

> 未設定 Qdrant/OpenAI 時，update.sh 會跳過，萃取流程仍正常。
> jp_fnfc 的 Salesforce Document ID 可能變更。若自動下載失敗，請至 https://www.fld.caa.go.jp/caaks/cssc01/ 手動下載 CSV。
> PubMed 查詢無需 API Key，但設定後可提高速率限制。

---

## 輸出規則

1. **格式遵循** — 各 Layer/Mode 的 CLAUDE.md 定義
2. **自我審核** — 通過 Checklist 才算完成
3. **REVIEW_NEEDED** — 未通過審核需標記（詳見下方規則）
4. **Category 限定** — 只能用 `core/CLAUDE.md` 定義的 enum

### REVIEW_NEEDED 處理規則

#### 定義與判定

`[REVIEW_NEEDED]` 標記用於 **資料不完整或無法正確萃取的產品**，觸發條件：

| 來源 | 觸發條件 |
|------|----------|
| us_dsld | 必填欄位缺失（品名、成分）、成分解析失敗 |
| ca_lnhpd | 必填欄位缺失、成分資料空白 |
| kr_hff | 必填欄位缺失、機能性成分空白 |
| jp_fnfc | 必填欄位缺失、**已撤回產品** |
| jp_foshu | 必填欄位缺失、機能性成分空白 |
| tw_hf | 必填欄位缺失（許可證字號、品名、保健功效） |
| pubmed | PMID 為空、標題為空、摘要為空 |

> 各 Layer 的詳細觸發規則定義於 `core/Extractor/Layers/{layer}/CLAUDE.md`

#### 產品檔案處理

**REVIEW_NEEDED 產品（資料不完整）**：
- ✅ 保留 `.md` 檔案於 `docs/Extractor/{layer}/{category}/`
- ✅ 檔案開頭標記 `[REVIEW_NEEDED]`
- ❌ **不納入 Mode 報告統計**（靜默排除，報告中不顯示 REVIEW_NEEDED 數量）

**已撤回產品（Withdrawn）**：
- ✅ 保留 `.md` 檔案，標記撤回狀態
- ✅ **可納入報告分析**：撤回趨勢、撤回原因、是否有先例等
- 這是市場情報的一部分，不是資料品質問題

#### Mode 報告輸出規則

**報告中不應出現**：
- ❌ REVIEW_NEEDED 數量統計
- ❌ 「排除 N 筆 REVIEW_NEEDED」字樣
- ❌ 資料品質備註中的 REVIEW_NEEDED 計數

**報告中可以出現**：
- ✅ 撤回產品分析（趨勢、原因、先例）
- ✅ 資料覆蓋範圍說明（如「成功萃取成分資訊的產品達 N 筆」）

**原則**：報告呈現的是「有效統計」，讀者無需知道有多少產品因資料不完整被排除。

#### 範例

```markdown
# 正確寫法 ✅
本月成分雷達報告分析五大市場共 410,640 筆保健食品產品資料，
成功萃取成分資訊的產品達 346,446 筆（84.4%）。

# 錯誤寫法 ❌
本月分析 410,640 筆產品，排除 460 筆 REVIEW_NEEDED 標記後，
有效統計產品為 410,180 筆。
```

### 禁止行為

- ❌ 自行新增 category enum
- ❌ 擴大 REVIEW_NEEDED 判定範圍
- ❌ 產出無法驗證的聲明
- ❌ 混淆推測與事實
- ❌ Read 工具讀取大型 .jsonl
- ❌ 報告中顯示 REVIEW_NEEDED 數量

---

## 完成後回報

```markdown
## 執行完成報告

### Layer 處理結果
| Layer | 擷取 | 萃取 | REVIEW | 狀態 |
|-------|------|------|--------|------|
| us_dsld | 214,780 | 214,780 | 9,042 | ✅ |
| ca_lnhpd | 160,545 | 160,545 | 5,164 | ✅ |
| kr_hff | 44,095 | 44,095 | 30 | ✅ |
| jp_fnfc | 1,569 | 1,569 | 459 | ✅ |
| jp_foshu | 1,032 | 1,032 | 1 | ✅ |
| tw_hf | 600 | 600 | 0 | ✅ |
| pubmed | 1,000 | 1,000 | 10 | ✅ |

### Mode 報告結果
| Mode | 檔案 | 狀態 |
|------|------|------|
| market_snapshot | 2026-W06-market-snapshot.md | ✅ |
| ingredient_radar | 2026-02-ingredient-radar.md | ✅ |

### 主題追蹤報告
| 主題 | 檔案 | 匹配產品 | 狀態 |
|------|------|----------|------|
| exosomes | 2026-02.md | 45 | ✅ |
| fish-oil | 2026-02.md | 1,234 | ✅ |

### 文獻薈萃報告
| 主題 | 檔案 | 文獻數 | 狀態 |
|------|------|--------|------|
| exosomes | 2026-02.md | 50 | ✅ |
| fish-oil | 2026-02.md | 500 | ✅ |

### 主題推薦
| 排名 | 成分 | 推薦原因 | 涵蓋市場 |
|------|------|----------|----------|
| 1 | NMN | 成長趨勢 (+12位) | 🇺🇸🇯🇵🇰🇷 |
| 2 | 葉黃素 | 跨國熱門 | 🇺🇸🇨🇦🇯🇵🇰🇷🇹🇼 |

### Jekyll 轉換
- 市場快照: docs/reports/market-snapshot/
- 成分雷達: docs/reports/ingredient-radar/
- 主題報告: docs/reports/{topic}/reports/
- 文獻報告: docs/reports/{topic}/literature/

### 需要關注
- （如有錯誤或異常列於此）
```

---

## 健康度儀表板

執行完成後更新 `README.md`：

| 狀態 | 條件 |
|------|------|
| ✅ 正常 | 最後更新在預期週期內 |
| ⚠️ 需關注 | 超過預期但未超過 2 倍 |
| ❌ 異常 | 超過 2 倍週期 |

---

## 進階：依賴關係

```
階段一（前景）：發現
    │
    ▼
階段二（背景平行）：資料處理
    ├── us_dsld ──────┐
    ├── ca_lnhpd ─────┤
    ├── kr_hff ───────┤
    ├── jp_fnfc ──────┼──▶ 等待全部完成
    ├── jp_foshu ─────┤
    ├── tw_hf ────────┤
    └── pubmed ───────┘
                      │
                      ▼
階段三（背景平行）：報告產出
    ├── market_snapshot ────┐
    ├── ingredient_radar ───┤
    ├── topic_tracking ─────┼──▶ 等待全部完成
    │   ├── exosomes        │
    │   └── fish-oil        │
    └── literature_review ──┘
        ├── exosomes
        └── fish-oil
                            │
                            ▼
階段四（前景）：主題推薦
    └── recommend_topics.py
                            │
                            ▼
階段五（前景）：Jekyll 轉換
    └── convert_to_jekyll.py
```

---

## 階段六：部署與驗證（必做！）

⚠️ **重要**：任何修改網站內容的任務，必須完成以下所有步驟才算「完成」：

### 完成定義（缺一不可）

1. ✅ `git push origin main` 成功
2. ✅ GitHub Actions 建置成功（`gh run watch` 全綠）
3. ✅ WebFetch 驗證網站內容已更新
4. ✅ 向用戶回報時明確列出以上三項完成狀態

**禁止**：只修改檔案就說「完成」，必須上傳並驗證網站更新後才能回報完成。

### 6.1 Git 提交與推送

```bash
# 1. 檢查所有變更
git status

# 2. 加入所有變更（包含報告和靜態頁面）
git add docs/

# 3. 提交
git commit -m "feat: update reports for YYYY-MM"

# 4. 推送
git push origin main
```

### 6.2 等待 GitHub Actions 完成

```bash
# 監看建置狀態
gh run list --repo weiqi-kids/agent.supplement-product --limit 1

# 等待完成
gh run watch <run-id> --repo weiqi-kids/agent.supplement-product --exit-status
```

### 6.3 網站內容驗證（WebFetch）

**必須使用 WebFetch 驗證以下頁面**（加 `?v=YYYYMMDD` 避免快取）：

| 頁面 | 檢查項目 |
|------|----------|
| 首頁 | 主題追蹤區塊、產品數量、最新報告連結 |
| 外泌體首頁 | 無「待補充」、市場分析數據正確 |
| 外泌體選購指南 | 決策樹、選購要點、FAQ 完整 |
| 外泌體市場報告 | 產品數、品牌排名、劑型分布 |
| 魚油首頁 | 無「待補充」、市場分析數據正確 |
| 魚油選購指南 | 決策樹、選購要點、FAQ 完整 |
| 魚油市場報告 | 產品數、品牌排名、劑型分布 |
| 市場快照 | 最新週報內容 |
| 成分雷達 | 最新月報內容 |

### 6.4 常見問題排查

| 問題 | 原因 | 解決方法 |
|------|------|----------|
| 頁面顯示舊內容 | CDN 快取 | URL 加 `?v=timestamp` 或強制重新整理 |
| 頁面 404 | 缺少父頁面 index.md | 檢查 `docs/reports/{topic}/reports/index.md` |
| 內容是「待補充」 | 靜態頁面未更新 | 更新 `docs/reports/{topic}/index.md` 和 `guide.md` |
| Jekyll 導航錯誤 | frontmatter parent/grand_parent 不符 | 檢查頁面層級關係 |

### 6.5 需要手動更新的靜態頁面

以下頁面**不會**被 `convert_to_jekyll.py` 自動更新，需手動維護：

```
docs/reports/{topic}/index.md      # 主題首頁（市場分析、作用機轉）
docs/reports/{topic}/guide.md      # 選購指南（決策樹、FAQ）
docs/reports/{topic}/reports/index.md  # 市場報告索引
docs/index.md                      # 網站首頁
```

當新增主題或資料有重大更新時，需同步更新這些頁面。

---

## 維護操作

Layer/Mode 的新增、修改、刪除，參見 `core/CLAUDE.md`。
