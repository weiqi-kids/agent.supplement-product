# Narrator 角色說明

## 職責

Narrator 負責跨來源綜合分析，將 Extractor 萃取的結構化資料轉化為可讀報告。

## 資料來源

Narrator Mode 讀取：
1. `docs/Extractor/{layer_name}/` 下的 `.md` 檔案
2. Qdrant 向量搜尋結果（用於相似產品比較）
3. 前一個 Mode 的報告輸出（若有依賴關係）

## 執行流程

對每個 Mode 依序執行：
1. 讀取該 Mode 的 `CLAUDE.md` 和本文件
2. 讀取 CLAUDE.md 中宣告的來源 Layer 資料
3. 依照輸出框架產出報告到 `docs/Narrator/{mode_name}/`

## Mode CLAUDE.md 必備內容

1. **Mode 定義表** — 名稱、目的、受眾、來源 Layer
2. **資料來源定義** — 讀取哪些 Layer 和 Qdrant 資料
3. **輸出框架** — 報告結構
4. **免責聲明** — 法律與使用限制
5. **輸出位置** — 檔案路徑
6. **自我審核 Checklist** — 發布前逐項確認

## 已建立的 Modes

### Mode 1: `market_snapshot`（市場快照）
- 來源：所有產品 Layer（us_dsld, ca_lnhpd, kr_hff, jp_foshu, jp_fnfc, tw_hf）
- 週期：週報
- 內容：新產品數、熱門成分、品類分布變化、跨國比較
- 定義：`core/Narrator/Modes/market_snapshot/CLAUDE.md`
- 輸出：`docs/Narrator/market_snapshot/{YYYY}-W{WW}-market-snapshot.md`

### Mode 2: `ingredient_radar`（成分雷達）
- 來源：所有產品 Layer（us_dsld, ca_lnhpd, kr_hff, jp_foshu, jp_fnfc, tw_hf）
- 週期：月報
- 內容：成分趨勢排名、新興成分、各國成分偏好差異
- 定義：`core/Narrator/Modes/ingredient_radar/CLAUDE.md`
- 輸出：`docs/Narrator/ingredient_radar/{YYYY}-{MM}-ingredient-radar.md`

### Mode 3: `topic_tracking`（主題追蹤）
- 來源：所有產品 Layer（依主題關鍵詞篩選）
- 週期：月報
- 內容：特定主題產品統計、品牌分析、趨勢觀察
- 定義：`core/Narrator/Modes/topic_tracking/CLAUDE.md`
- 輸出：`docs/Narrator/topic_tracking/{topic}/{YYYY}-{MM}.md`

### Mode 4: `literature_review`（文獻薈萃）
- 來源：pubmed Layer
- 週期：月報
- 內容：學術文獻統計、證據等級分布、功效分類分析
- 定義：`core/Narrator/Modes/literature_review/CLAUDE.md`
- 輸出：`docs/Narrator/literature_review/{topic}/{YYYY}-{MM}.md`

---

## 選購指南交互作用整合

交互作用章節由 `scripts/update_guide_interactions.py` 自動更新至選購指南（guide.md）。

### 執行方式

```bash
# 更新所有主題
python3 scripts/update_guide_interactions.py

# 更新特定主題
python3 scripts/update_guide_interactions.py --topic fish-oil

# 僅顯示，不寫入
python3 scripts/update_guide_interactions.py --dry-run
```

### 主題與交互類別對照

定義於腳本內 `TOPIC_INTERACTION_MAP`：

| 主題 | DHI 類別 | DFI 類別 | DDI 類別 |
|------|----------|----------|----------|
| fish-oil | omega_fatty_acid, general | — | anticoagulant |
| curcumin | botanical, general | — | — |
| nattokinase | general | vitamin_k | anticoagulant |
| red-yeast-rice | general | grapefruit, citrus | statin |

### 輸出位置

- `docs/reports/{topic}/guide.md` — 選購指南（含交互作用章節）

### 重要規則

**所有主題的選購指南都必須包含藥物交互章節**。若新增主題：
1. 在 `fetch_interactions.py` 新增對應的 PubMed 查詢
2. 執行 `python3 scripts/fetch_interactions.py --type dhi --category {new_category}`
3. 執行 `python3 scripts/extract_interactions.py --type dhi`
4. 在 `update_guide_interactions.py` 的 `TOPIC_INTERACTION_MAP` 新增映射
5. 執行 `python3 scripts/update_guide_interactions.py --topic {topic_id}`

---

## ⚠️ Context 優化規範

### 子代理精簡回報

**所有 Mode 子代理完成後只輸出一行**：
```
DONE|{mode}|{period}|{筆數}|OK
```

### 禁止行為

- ❌ 輸出報告內容摘要
- ❌ 列舉統計表格
- ❌ 描述執行過程步驟
- ❌ 在回報中包含產品名稱清單

### 資料讀取策略

- 統計產品數：使用 `find docs/Extractor/{layer} -name "*.md" | wc -l`
- 抽樣分析：只讀取每個 category 前 3 個 .md 檔
- 歷史比較：使用 Qdrant 查詢，不逐一讀取舊報告
