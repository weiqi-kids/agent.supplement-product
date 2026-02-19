# Layer: jp_fnfc — 日本 CAA 機能性表示食品 (Foods with Function Claims)

## Layer 定義表

| 項目 | 說明 |
|------|------|
| **Layer name** | jp_fnfc（日本機能性表示食品） |
| **Engineering function** | 從消費者庁 (CAA) 機能性表示食品資料庫匯出 CSV，轉換為結構化資料 |
| **Collectable data** | 屆出番號、商品名、屆出者、食品區分、機能性成分、機能性表示、評價方法 |
| **Automation level** | 95% — fetch.sh 可自動下載 CSV，完全自動化 |
| **Output value** | 日本機能性表示食品完整資料庫（~10K+ 筆），支援跨國比較 |
| **Risk type** | Document ID 可能變更、日文欄位處理、CSV 格式變動 |
| **Reviewer persona** | 資料可信度審核員、領域保守審核員 |
| **WebFetch 策略** | **不使用** — CSV 已包含完整結構化資料 |

## 資料源資訊

- **來源**: 消費者庁 (CAA) 機能性表示食品制度屆出資料庫
- **搜尋頁面**: https://www.fld.caa.go.jp/caaks/cssc01/
- **CSV 匯出**: 透過搜尋頁面的「全届出の全項目出力(CSV 出力)」按鈕手動下載
- **產品數**: ~10,000+ 筆（截至 2025 年 11 月約 10,161 筆）
- **認證**: 免 key，公開存取
- **更新頻率**: 每日更新

## 自動下載

fetch.sh 現已支援自動下載 CSV：

```bash
./fetch.sh              # 自動下載並轉換
./fetch.sh --no-download true  # 使用現有 CSV（不下載）
./fetch.sh --csv /path/to/file.csv  # 指定 CSV 檔案
```

### 下載 URL

```
https://www.fld.caa.go.jp/caaks/sfc/servlet.shepherd/document/download/069RA00000n6SLZYA2?operationContext=S1
```

> ⚠️ **注意**：此 Salesforce Document ID (`069RA00000n6SLZYA2`) 可能會變更。
> 如果自動下載失敗，請手動更新 fetch.sh 中的 `DOWNLOAD_URL`。

### 手動下載備案

如果自動下載失敗：
1. 前往 https://www.fld.caa.go.jp/caaks/cssc01/
2. 點選「全届出の全項目出力(CSV 出力)」
3. 將 CSV 放入 `docs/Extractor/jp_fnfc/raw/`
4. 執行 `./fetch.sh --no-download true`

## CSV 欄位結構

| 欄位 | 日文名稱 | 說明 |
|------|----------|------|
| 届出番号 | 届出番号 | 屆出番號（如 A1, B234, J1126） |
| 届出日 | 届出日 | 屆出日期 |
| 届出者名 | 届出者名 | 屆出公司名稱 |
| 商品名 | 商品名 | 產品名稱 |
| 食品の区分 | 食品の区分 | 食品區分（加工食品/生鮮食品/サプリメント） |
| 機能性関与成分名 | 機能性関与成分名 | 機能性成分名 |
| 表示しようとする機能性 | 表示しようとする機能性 | 機能性表示（保健宣稱） |
| 摂取する上での注意事項 | 摂取する上での注意事項 | 攝取注意事項 |
| 名称 | 名称 | 食品名稱/種類 |
| 機能性関与成分を含む原材料名 | 機能性関与成分を含む原材料名 | 含機能性成分的原料名 |
| 機能性の評価方法 | 機能性の評価方法 | 機能性評價方法 |

> 完整欄位清單請參閱消費者庁搜尋手冊 P.34-46

## CSV → JSONL 轉換

fetch.sh 執行以下處理：
1. 下載 CSV 檔案（Shift_JIS 編碼）
2. 轉換為 UTF-8 編碼
3. 使用 `csvjson` 轉為 JSONL 格式
4. **保留日文欄位名稱**（如 `商品名`、`届出番号`）

輸出檔案：`docs/Extractor/jp_fnfc/raw/fnfc-YYYY-MM-DD.jsonl`

> 萃取腳本直接使用日文欄位名稱讀取 JSONL。

## 萃取邏輯

### JSONL → Markdown 欄位映射

| Markdown 欄位 | JSONL 欄位（日文） | 說明 |
|---------------|----------|------|
| `source_id` | 届出番号 | 屆出番號（唯一識別） |
| `source_layer` | 固定 `"jp_fnfc"` | — |
| `source_url` | 組合產生 | `https://www.fld.caa.go.jp/caaks/cssc02/?recordSeq={届出番号}` |
| `market` | 固定 `"jp"` | — |
| `product_name` | 商品名 | 日文原名 |
| `brand` | 届出者名 | 屆出公司名 |
| `manufacturer` | 届出者名 | 同上 |
| `category` | 由 機能性関与成分名 推斷 | 見下方規則 |
| `product_form` | 由 食品の区分 + 名称 推斷 | 見下方規則 |
| `date_entered` | 届出日 | YYYY-MM-DD |
| `fetched_at` | 萃取時自動產生 | ISO8601 |

## Category 推斷規則

從 `機能性関与成分名`（機能性成分）關鍵字推斷：

| 日文關鍵字 | 統一 Category |
|-----------|---------------|
| ビタミン, 葉酸, カルシウム, 鉄, 亜鉛, マグネシウム | `vitamins_minerals` |
| ルテイン, イチョウ, ブルーベリー, クルクミン, 茶カテキン, イソフラボン, GABA, 難消化性デキストリン | `botanicals` |
| コラーゲン, ペプチド, アミノ酸, HMB | `protein_amino` |
| 乳酸菌, ビフィズス菌, プロバイオティクス | `probiotics` |
| DHA, EPA, オメガ, n-3系脂肪酸 | `omega_fatty_acids` |
| 多成分複合 | `specialty` |
| 以上皆不符 | `other` |

## Product Form 推斷規則

從 `食品の区分` 和 `名称` 推斷：

| 條件 | product_form |
|------|-------------|
| 食品の区分 = "サプリメント形状の加工食品" | 依名称細分：錠剤→tablet, カプセル→capsule, 粉末→powder |
| 食品の区分 = "その他加工食品" | 依名称：飲料→liquid, ゼリー→gummy, 其他→other |
| 食品の区分 = "生鮮食品" | `other` |

## `[REVIEW_NEEDED]` 觸發規則

以下情況**必須**標記 `[REVIEW_NEEDED]`：
1. 商品名為空
2. 届出番号為空
3. 機能性関与成分名為空

以下情況**不觸發** `[REVIEW_NEEDED]`：
- ❌ 日文內容未翻譯 — 系統保留原文
- ❌ category 推斷為 `other` — 成分名稱可能不含標準關鍵字
- ❌ 已撤回的屆出 — 撤回是正常狀態

## 撤回產品處理

已撤回的屆出（`撤回日` 欄位非空）：

| 處理方式 | 說明 |
|----------|------|
| ✅ 保留 .md 檔案 | 在「備註」欄標記「已撤回（{撤回日}）」 |
| ✅ 可納入報告分析 | 撤回趨勢、撤回原因、是否有先例等 |
| ❌ 不標記 `[REVIEW_NEEDED]` | 撤回是市場資訊，不是資料品質問題 |

> 撤回產品是有價值的市場情報，可用於分析產品失敗原因、監管趨勢等。

## 輸出格式

```markdown
---
source_id: "{届出番号}"
source_layer: "jp_fnfc"
source_url: "https://www.fld.caa.go.jp/caaks/cssc02/?recordSeq={届出番号}"
market: "jp"
product_name: "{商品名}"
brand: "{届出者名}"
manufacturer: "{届出者名}"
category: "{inferred category}"
product_form: "{inferred product_form}"
date_entered: "{届出日 YYYY-MM-DD}"
fetched_at: "{ISO8601 timestamp}"
---

# {商品名}

## 基本資訊
- 屆出者：{届出者名}
- 食品區分：{食品の区分}
- 劑型：{inferred product_form}
- 市場：日本
- 屆出番號：{届出番号}

## 機能性成分
{機能性関与成分名}

## 機能性表示
{表示しようとする機能性}

## 攝取注意事項
{摂取する上での注意事項}

## 原料
{機能性関与成分を含む原材料名}

## 備註
{撤回狀態或其他特殊情況}
```

## 輸出位置

`docs/Extractor/jp_fnfc/{category}/{届出番号}.md`

## 自我審核 Checklist

- [ ] `source_id` 正確對應届出番号
- [ ] 日文內容完整保留
- [ ] `category` 依機能性関与成分名關鍵字規則推斷
- [ ] `product_form` 依食品の区分 + 名称推斷
- [ ] frontmatter 格式正確
- [ ] `[REVIEW_NEEDED]` 僅在觸發條件成立時標記

---

## ⚠️ 子代理精簡回報規範

完成後**只輸出一行**：
```
DONE|jp_fnfc|F:{fetch筆數}|E:{extract筆數}|R:{review筆數}|OK
```

**禁止**：冗長描述、完整 log、日文內容輸出
