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
- 來源：所有 Layer（us_dsld, ca_lnhpd, kr_hff, jp_foshu, jp_fnfc）
- 週期：週報
- 內容：新產品數、熱門成分、品類分布變化、跨國比較
- 定義：`core/Narrator/Modes/market_snapshot/CLAUDE.md`
- 輸出：`docs/Narrator/market_snapshot/{YYYY}-W{WW}-market-snapshot.md`

### Mode 2: `ingredient_radar`（成分雷達）
- 來源：所有 Layer（us_dsld, ca_lnhpd, kr_hff, jp_foshu, jp_fnfc）
- 週期：月報
- 內容：成分趨勢排名、新興成分、各國成分偏好差異
- 定義：`core/Narrator/Modes/ingredient_radar/CLAUDE.md`
- 輸出：`docs/Narrator/ingredient_radar/{YYYY}-{MM}-ingredient-radar.md`
