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
│  ├── [Layer] us_dsld        → fetch → extract → update         │
│  ├── [Layer] ca_lnhpd       → fetch → extract → update         │
│  ├── [Layer] kr_hff         → fetch → extract → update         │
│  ├── [Layer] jp_fnfc        → fetch → extract → update         │
│  ├── [Layer] jp_foshu       → fetch → extract → update         │
│  ├── [Layer] tw_hf          → fetch → extract → update         │
│  ├── [Layer] pubmed         → fetch → extract → update         │
│  ├── [Layer] dhi            → fetch → extract → update         │
│  ├── [Layer] dfi            → fetch → extract → update         │
│  ├── [Layer] ddi            → fetch → extract → update         │
│  ├── [Mode]  market_snapshot     → 報告產出                     │
│  ├── [Mode]  ingredient_radar    → 報告產出                     │
│  ├── [Mode]  topic_tracking      → 主題追蹤報告                 │
│  └── [Mode]  literature_review   → 文獻薈萃報告                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 快速指令

| 指令 | 行為 |
|------|------|
| `執行完整流程` | 背景平行執行所有 Layer + Mode + 主題追蹤 + 推薦 + Jekyll + **品質關卡檢查** |
| `更新資料` | 同上 |

> ⚠️ **注意**：`執行完整流程` 必須通過「階段七：任務完成品質關卡」的所有檢查項目才視為成功完成。
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
| `dhi` | PubMed 藥物-補充劑交互文獻 | 1-2 分鐘 | ✅ 啟用 |
| `dfi` | PubMed 藥物-食物交互文獻 | 1-2 分鐘 | ✅ 啟用 |
| `ddi` | PubMed 藥物-藥物交互文獻 | 1-2 分鐘 | ✅ 啟用 |
| `th_fda` | 泰國 FDA 健康食品資料庫 | — | ❌ 已禁用 |
| `ingredient_map` | RxNorm API 成分標準化 | — | ⏸️ 暫停 |

> 禁用的 Layer 帶有 `.disabled` 標記，執行流程會自動跳過。
> 暫停的 Layer 功能已開發完成，但目前未納入例行執行流程。

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
| `calcium` | 鈣 | calcium, calcium citrate |
| `collagen` | 膠原蛋白 | collagen, hydrolyzed collagen |
| `curcumin` | 薑黃素 | curcumin, turmeric |
| `exosomes` | 外泌體 | exosome, stem cell, 幹細胞 |
| `fish-oil` | 魚油 | omega-3, EPA, DHA, krill oil |
| `glucosamine` | 葡萄糖胺 | glucosamine, chondroitin |
| `lutein` | 葉黃素 | lutein, zeaxanthin |
| `magnesium` | 鎂 | magnesium, magnesium citrate |
| `nattokinase` | 納豆激酶 | nattokinase, natto |
| `nmn` | NMN | NMN, nicotinamide mononucleotide |
| `red-yeast-rice` | 紅麴 | red yeast rice, monacolin K |
| `vitamin-b6` | 維生素 B6 | vitamin B6, pyridoxine |
| `vitamin-c` | 維生素 C | vitamin C, ascorbic acid |
| `zinc` | 鋅 | zinc, zinc gluconate |

> 主題可透過 `python3 scripts/create_topic.py` 新增

### 階段三.5：選購指南交互作用更新（前景）

**在 Mode 報告完成後**，更新選購指南的藥物交互章節：

```bash
python3 scripts/update_guide_interactions.py
```

此腳本會自動：
- 讀取 `docs/Extractor/dhi`、`dfi`、`ddi` 下的交互文獻
- 根據 `TOPIC_INTERACTION_MAP` 匹配相關文獻
- 更新 `docs/reports/{topic}/guide.md` 的交互章節

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

### 階段五：Jekyll 轉換 + SEO 注入（前景）

所有報告完成後，轉換為 Jekyll 格式並注入 SEO Schema：

```bash
python3 scripts/convert_to_jekyll.py
```

此腳本會自動：
- 讀取 `seo/config.yaml` 全域設定
- 為每個頁面產生 JSON-LD Schema（WebPage、Article、BreadcrumbList 等）
- 加入 YMYL 免責聲明
- 輸出至 `docs/reports/`

### 階段五.5：SEO 驗證（前景）

部署前執行 SEO 檢查：

```bash
python3 scripts/validate_seo.py
```

檢查項目：
- JSON-LD Schema 完整性（必填 Schema 存在）
- Meta 標籤長度（title ≤60 字、description ≤155 字）
- YMYL 免責聲明存在
- URL 結構正確（英文小寫 + 連字號）

**通過標準**：
- ✅ 通過：無錯誤
- ⚠️ 警告：有警告但可部署（建議修正）
- ❌ 失敗：有錯誤，阻斷部署

```bash
# 詳細輸出（含警告）
python3 scripts/validate_seo.py --verbose

# 驗證單一檔案
python3 scripts/validate_seo.py --file docs/reports/exosomes/reports/2026-02.md
```

---

## 子代理 Prompt 範本（Context 優化版）

> ⚠️ **重要**：子代理回報必須使用**精簡單行格式**，避免 Context 超限。

### 精簡回報格式規範

**Layer 子代理回報格式**：
```
DONE|{layer}|F:{fetch筆數}|E:{extract筆數}|R:{review筆數}|{OK/ERR}
```

範例：
```
DONE|us_dsld|F:214780|E:214780|R:9042|OK
DONE|ca_lnhpd|F:160545|E:160545|R:5164|OK
DONE|jp_fnfc|F:0|E:0|R:0|ERR:fetch failed - network timeout
```

**Mode 子代理回報格式**：
```
DONE|{mode}|{period}|{筆數}|{OK/ERR}
```

範例：
```
DONE|market_snapshot|2026-W07|421076|OK
DONE|ingredient_radar|2026-02|346446|OK
DONE|topic_tracking|exosomes:45,fish-oil:1234|OK
DONE|literature_review|exosomes:50,fish-oil:500|OK
```

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

## ⚠️ 精簡回報（必須遵守）
完成後**只回報一行**：
DONE|{layer_name}|F:{fetch筆數}|E:{extract筆數}|R:{review筆數}|OK

錯誤時：
DONE|{layer_name}|F:{筆數}|E:{筆數}|R:{筆數}|ERR:{簡短錯誤描述}

❌ 禁止冗長描述、禁止輸出完整 log、禁止重複步驟說明
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

## ⚠️ 精簡回報（必須遵守）
完成後**只回報一行**：
DONE|{mode_name}|{period}|{涵蓋筆數}|OK

❌ 禁止輸出報告內容摘要、禁止列舉統計細節
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

## ⚠️ 精簡回報（必須遵守）
完成後**只回報一行**：
DONE|topic_tracking|{topic1}:{數量},{topic2}:{數量}|OK

❌ 禁止列舉匹配產品清單
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

## ⚠️ 精簡回報（必須遵守）
完成後**只回報一行**：
DONE|literature_review|{topic1}:{數量},{topic2}:{數量}|OK

❌ 禁止輸出證據等級分布表、禁止列舉文獻清單
```

---

## 主執行緒職責（Context 優化版）

### 啟動階段
1. 發現所有有效 Layer 和 Mode
2. 平行啟動所有 Layer 子代理（`run_in_background: true`）
3. 告知使用者「已啟動 N 個背景任務」（一句話即可）

### 監控階段（低 Context 消耗）

**高效監控原則**：
- ✅ 使用 `tail -1` 只讀取 output_file 最後一行（子代理的精簡回報）
- ✅ 批次檢查多個任務狀態
- ❌ 禁止使用 `Read` 讀取完整 output_file
- ❌ 禁止重複輸出相同的進度資訊

**監控指令範例**：
```bash
# 檢查單一任務最後一行
tail -1 /path/to/output_file

# 批次檢查所有任務（一行指令）
for f in /tmp/agent_*.txt; do echo "==$f=="; tail -1 "$f" 2>/dev/null || echo "RUNNING"; done
```

**回應使用者「查看進度」**：
只輸出精簡狀態表，不要重複子代理的完整輸出：
```
Layer: ✅us_dsld ✅ca_lnhpd ⏳kr_hff ⏳jp_fnfc ⏳jp_foshu ⏳tw_hf
Mode:  ⏸️waiting
```

### 彙整階段
1. 等待所有 Layer 完成（解析精簡回報格式）
2. 平行啟動所有 Mode 子代理
3. 等待所有 Mode 完成
4. 執行 HTML 建置
5. 產出最終報告（使用下方精簡格式）

---

## 進度追蹤格式（精簡版）

> ⚠️ **重要**：進度追蹤使用單行格式，避免 Context 膨脹。

### 標準格式（3 行以內）

```
Layer(5/10): ✅us ✅ca ✅kr ⏳jp_fnfc ⏳jp_foshu ⏳tw ⏳pub ⏳dhi ⏳dfi ⏳ddi
Mode(0/4): ⏸️snap ⏸️radar ⏸️topic ⏸️lit
Post: ⏸️recommend ⏸️jekyll ⏸️seo
```

### 圖例

| 符號 | 意義 |
|------|------|
| ✅ | 完成 |
| ⏳ | 執行中 |
| ⏸️ | 等待中 |
| ❌ | 失敗 |

### 縮寫對照

| 縮寫 | 完整名稱 |
|------|----------|
| us | us_dsld |
| ca | ca_lnhpd |
| kr | kr_hff |
| jp_fnfc | jp_fnfc |
| jp_foshu | jp_foshu |
| tw | tw_hf |
| pub | pubmed |
| snap | market_snapshot |
| radar | ingredient_radar |
| topic | topic_tracking |
| lit | literature_review |

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
| dhi/dfi/ddi | `raw/{type}-*.jsonl` | `python3 scripts/extract_interactions.py --type {type}` |

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

## 完成後回報（精簡版）

> ⚠️ **重要**：完成報告必須精簡，避免 Context 超限。

### 標準格式（約 20 行以內）

```markdown
## ✅ 執行完成

**Layer** (10/10)
us_dsld:214K ca_lnhpd:160K kr_hff:44K jp_fnfc:1.5K jp_foshu:1K tw_hf:555 pubmed:1K dhi:50 dfi:30 ddi:40

**Mode** (4/4)
market_snapshot:2026-W07 ingredient_radar:2026-02 topic_tracking:exo+fish literature_review:exo+fish

**Jekyll** ✅ | **SEO** ✅ | **Git** pushed

**異常** 無（若有則列出）
```

### 有錯誤時的格式

```markdown
## ⚠️ 執行完成（有警告）

**Layer** (9/10) ❌kr_hff:API timeout
us_dsld:214K ca_lnhpd:160K jp_fnfc:1.5K ...

**需要處理**
- kr_hff: API timeout，需手動重跑 `./fetch.sh`
```

### 禁止事項

- ❌ 不要輸出完整表格（太佔 Context）
- ❌ 不要重複列舉每個 Layer 的詳細數字
- ❌ 不要輸出 Jekyll 轉換的檔案清單
- ❌ 不要在每個階段結束時輸出中間報告

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
    ├── jp_fnfc ──────┤
    ├── jp_foshu ─────┼──▶ 等待全部完成
    ├── tw_hf ────────┤
    ├── pubmed ───────┤
    ├── dhi ──────────┤
    ├── dfi ──────────┤
    └── ddi ──────────┘
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
階段三.5（前景）：選購指南交互作用更新
    └── update_guide_interactions.py
                            │
                            ▼
階段四（前景）：主題推薦
    └── recommend_topics.py
                            │
                            ▼
階段五（前景）：Jekyll 轉換 + SEO 注入
    └── convert_to_jekyll.py
                            │
                            ▼
階段五.5（前景）：SEO 驗證
    └── validate_seo.py
        ├── 通過 → 繼續部署
        └── 失敗 → 阻斷部署
                            │
                            ▼
階段六（前景）：部署與驗證
    ├── git push origin main
    ├── gh run watch（等待 Actions 完成）
    └── WebFetch 驗證網站內容
                            │
                            ▼
階段七（前景）：任務完成品質關卡
    ├── 連結檢查
    ├── SEO/AEO 標籤檢查
    ├── 內容更新確認
    ├── Git 狀態檢查
    └── SOP 完成度檢查
        ├── 全部通過 → 回報完成
        └── 未通過 → 修正後重新檢查
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

## 階段七：任務完成品質關卡（必做！）

⚠️ **重要**：每當要回報「完成」時，必須先執行以下檢查，**全部通過才能回報完成**。

### 7.1 連結檢查

- [ ] 所有新增/修改的內部連結正常，無 404
- [ ] 所有新增/修改的外部連結正常
- [ ] 無死連結或斷裂連結

### 7.2 SEO + AEO 標籤檢查

#### Meta 標籤

- [ ] `<title>` 存在且 ≤ 60 字，含核心關鍵字
- [ ] `<meta name="description">` 存在且 ≤ 155 字
- [ ] `og:title`, `og:description`, `og:image`, `og:url` 存在
- [ ] `og:type` = "article"
- [ ] `article:published_time`, `article:modified_time` 存在（ISO 8601 格式）
- [ ] `twitter:card` = "summary_large_image"

#### JSON-LD Schema（7 種必填）

| Schema | 必填欄位 |
|--------|----------|
| WebPage | speakable（至少 7 個 cssSelector） |
| Article | isAccessibleForFree, isPartOf（含 SearchAction）, significantLink |
| Person | knowsAbout（≥2）, hasCredential（≥1）, sameAs（≥1） |
| Organization | contactPoint, logo（含 width/height） |
| BreadcrumbList | position 從 1 開始連續編號 |
| FAQPage | 3-5 個 Question + Answer |
| ImageObject | license, creditText |

#### 條件式 Schema（依內容判斷）

| Schema | 觸發條件 | 必填欄位 |
|--------|----------|----------|
| HowTo | 有步驟教學 | step, totalTime |
| Recipe | 有食譜 | recipeIngredient, recipeInstructions |
| VideoObject | 有嵌入影片 | duration, thumbnailUrl |
| ItemList | 有排序清單（「N 大」「TOP」） | itemListElement |
| Review | 有評測內容 | itemReviewed, reviewRating |
| AggregateRating | 有多則評論 | ratingValue, ratingCount |
| Product | 有商品頁 | offers, brand |
| Event | 有活動資訊 | startDate, location |
| Course | 有課程內容 | provider, offers |
| LocalBusiness | 有店家資訊 | address, openingHoursSpecification |

#### SGE/AEO 標記（AI 引擎優化）

| 標記 | 要求 |
|------|------|
| `.key-answer` | 每個 H2 必須有，含 `data-question` 屬性 |
| `.key-takeaway` | 文章重點摘要（2-3 個） |
| `.expert-quote` | 專家引言（至少 1 個） |
| `.actionable-steps` | 行動步驟清單 |
| `.comparison-table` | 比較表格（若有） |

#### E-E-A-T 信號

- [ ] Person Schema 有專業認證（hasCredential）
- [ ] 至少 2 個高權威外部連結（.gov、學術期刊、專業協會）

#### YMYL 檢查（健康/財務/法律內容適用）

- [ ] `lastReviewed` 欄位（最後審核日期）
- [ ] `reviewedBy` 欄位（審核者資訊）
- [ ] 免責聲明（醫療/財務/法律）

### 7.3 內容更新確認

- [ ] 列出本次預計修改的所有檔案
- [ ] 逐一確認每個檔案都已正確更新
- [ ] 修改內容與任務要求一致
- [ ] 無遺漏項目

### 7.4 Git 狀態檢查

- [ ] 所有變更已 commit
- [ ] commit message 清楚描述本次變更
- [ ] 已 push 到 Github（除非另有指示）
- [ ] 遠端分支已更新

### 7.5 SOP 完成度檢查

- [ ] 回顧原始任務需求
- [ ] 原訂 SOP 每個步驟都已執行
- [ ] 無遺漏的待辦項目
- [ ] 無「之後再處理」的項目

### 7.6 完成檢查報告格式

完成檢查後，輸出以下格式：

```
## 完成檢查報告

| 類別 | 狀態 | 問題（如有） |
|------|------|-------------|
| 連結檢查 | ✅/❌ | |
| Meta 標籤 | ✅/❌ | |
| Schema（必填） | ✅/❌ | |
| Schema（條件式） | ✅/❌/N/A | |
| SGE/AEO 標記 | ✅/❌ | |
| E-E-A-T 信號 | ✅/❌ | |
| YMYL | ✅/❌/N/A | |
| 內容更新 | ✅/❌ | |
| Git 狀態 | ✅/❌ | |
| SOP 完成度 | ✅/❌ | |

**總結**：X/Y 項通過，狀態：通過/未通過
```

### 7.7 檢查未通過時

1. **不回報完成**
2. 列出所有未通過項目
3. 立即修正問題
4. 重新執行檢查
5. 全部通過才能說「完成」

### 7.8 任務開始時

接到新任務時，先建立本次檢查清單：

```
## 本次任務檢查清單

- 任務目標：[描述]
- 預計修改檔案：
  - [ ] 檔案1
  - [ ] 檔案2
- 預計新增內容：
  - [ ] 內容1
  - [ ] 內容2
- 適用的條件式 Schema：[列出]
- 是否為 YMYL 內容：是/否
```

### 7.9 SEO/AEO 參考文件

完整 SEO/AEO 規則請參照：
- `/Users/lightman/weiqi.kids/agent.idea/seo/CLAUDE.md` - SEO + AEO 規則庫
- `/Users/lightman/weiqi.kids/agent.idea/seo/writer/CLAUDE.md` - Writer 執行流程
- `/Users/lightman/weiqi.kids/agent.idea/seo/review/CLAUDE.md` - Reviewer 檢查清單

---

## Context 優化進階策略

### 1. 背景任務輸出清理

每次執行前清理舊的 output 檔案：
```bash
rm -f /tmp/agent_*.txt 2>/dev/null
```

### 2. 分批執行（Context 緊張時）

若 Context 接近上限，改用分批模式：

**批次 1**：產品 Layer（大資料量）
```
us_dsld, ca_lnhpd, kr_hff
```

**批次 2**：日本 + 台灣 Layer
```
jp_fnfc, jp_foshu, tw_hf
```

**批次 3**：文獻 Layer
```
pubmed, dhi, dfi, ddi
```

**批次 4**：Mode 報告
```
market_snapshot, ingredient_radar, topic_tracking, literature_review
```

每批完成後執行 `/compact` 釋放 Context。

### 3. 增量更新優先

優先使用增量模式減少處理量：
```bash
./fetch.sh          # 預設增量
./fetch.sh --full   # 僅在需要時全量
```

### 4. 統計替代讀取

| 需求 | 錯誤做法 | 正確做法 |
|------|----------|----------|
| 計算產品數 | Read 所有 .md | `find \| wc -l` |
| 抽樣分析 | Read 100+ 檔案 | `ls \| head -3` 只讀 3 個 |
| 比對差異 | Read 兩份報告 | 使用 `diff` 指令 |

### 5. 子代理數量控制

若同時啟動過多子代理導致 Context 緊張：
- 最多同時 5 個背景子代理
- 優先完成大型 Layer（us_dsld, ca_lnhpd）
- 小型 Layer 可合併處理（tw_hf + jp_foshu）

---

## 維護操作

Layer/Mode 的新增、修改、刪除，參見 `core/CLAUDE.md`。
