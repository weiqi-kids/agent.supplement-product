# Layer: jp_foshu — 日本 CAA 特定保健用食品 (FOSHU)

## Layer 定義表

| 項目 | 說明 |
|------|------|
| **Layer name** | jp_foshu（日本特定保健用食品） |
| **Engineering function** | 從消費者庁 (CAA) 下載 FOSHU 許可品目一覧 Excel，轉換為結構化資料 |
| **Collectable data** | 商品名、申請者、食品種類、機能成分、許可表示內容、攝取注意事項、每日攝取量、許可日 |
| **Automation level** | 90% — Excel 結構穩定，欄位明確 |
| **Output value** | 日本特定保健用食品完整資料庫，支援跨國比較 |
| **Risk type** | Excel 格式變動、日文欄位處理 |
| **Reviewer persona** | 資料可信度審核員、領域保守審核員 |
| **WebFetch 策略** | **不使用** — Excel 已包含完整結構化資料 |

## 資料源資訊

- **來源**: 消費者庁 (CAA) 特定保健用食品許可品目一覧
- **頁面**: https://www.caa.go.jp/policies/policy/food_labeling/foods_for_specified_health_uses/
- **下載 URL**: https://www.caa.go.jp/policies/policy/food_labeling/health_promotion/assets/food_labeling_cms206_260127_01.xlsx
  > 注意：URL 中的日期部分 (`260127`) 會隨更新而改變，fetch.sh 會自動從頁面解析最新連結
- **格式**: Excel (.xlsx)，2 個工作表
- **產品數**: ~1034 筆（許可一覧表）
- **認證**: 免 key，公開下載
- **更新頻率**: 不定期（依新許可核發）

## Excel 結構

### Sheet 1: 許可一覧表（主要資料）

| 欄位 | 日文名稱 | 說明 |
|------|----------|------|
| Column 1 | 通し番号 | 流水號（Excel 公式 `=ROW()-1`） |
| Column 2 | 商品名 | 產品名稱 |
| Column 3 | 申請者 | 申請公司 |
| Column 4 | 法人番号 | 法人編號 |
| Column 5 | 食品の種類 | 食品種類（はっ酵乳、清涼飲料水 等） |
| Column 6 | 関与する成分 | 機能性成分（以 ◆ 分隔多個成分） |
| Column 7 | 許可を受けた表示内容 | 許可的保健宣稱 |
| Column 8 | 摂取をする上での注意事項 | 攝取注意事項 |
| Column 9 | 1日摂取目安量 | 每日建議攝取量 |
| Column 10 | 区分 | 分類（特保 / 特保(規格基準型) / 特保(疾病リスク低減表示) / 条件付き特保） |
| Column 11 | 許可日 | 許可日期 |
| Column 12 | 許可番号 | 許可番號 |
| Column 13 | 令和5年度の販売実績 | 銷售實績（○ 或空白） |

### Sheet 2: 承認一覧表

特別用途食品承認品目，結構類似。fetch.sh 僅處理 Sheet 1。

## JSONL 欄位對照

fetch.sh 將 Excel 轉換為 JSONL 時，使用以下英文欄位名：

| Excel 日文欄位 | JSONL 英文欄位 | 說明 |
|---------------|---------------|------|
| 通し番号 | `serial_no` | 流水號 |
| 商品名 | `product_name` | 產品名稱 |
| 申請者 | `applicant` | 申請公司 |
| 法人番号 | `corporate_no` | 法人編號 |
| 食品の種類 | `food_type` | 食品種類 |
| 関与する成分 | `functional_ingredient` | 機能性成分 |
| 許可を受けた表示内容 | `health_claim` | 保健宣稱 |
| 摂取をする上での注意事項 | `precautions` | 攝取注意事項 |
| 1日摂取目安量 | `daily_intake` | 每日建議攝取量 |
| 区分 | `foshu_category` | FOSHU 分類 |
| 許可日 | `approval_date` | 許可日期 |
| 許可番号 | `approval_no` | 許可番號 |
| 令和5年度の販売実績 | `sales_record` | 銷售實績 |

## 萃取邏輯

### JSONL → Markdown 欄位映射

| Markdown 欄位 | JSONL 欄位 | 說明 |
|---------------|-----------|------|
| `source_id` | `approval_no` 或 `serial_no` | 許可番號作為唯一識別 |
| `source_layer` | 固定 `"jp_foshu"` | — |
| `source_url` | 固定頁面 URL | 無個別產品頁面 |
| `market` | 固定 `"jp"` | — |
| `product_name` | `product_name` | 日文原名 |
| `brand` | `applicant` | 申請公司名 |
| `manufacturer` | `applicant` | 同上 |
| `category` | 由 `functional_ingredient` 推斷 | 見下方規則 |
| `product_form` | 由 `food_type` 推斷 | 見下方規則 |
| `date_entered` | `approval_date` | YYYY-MM-DD |
| `fetched_at` | 萃取時自動產生 | ISO8601 |

### 額外欄位（寫入 Markdown 正文）
- `関与する成分`: 機能性成分清單
- `許可を受けた表示内容`: 保健宣稱
- `摂取をする上での注意事項`: 攝取注意
- `1日摂取目安量`: 每日攝取量
- `区分`: FOSHU 子分類
- `法人番号`: 法人編號
- `令和5年度の販売実績`: 銷售實績

## Category 推斷規則

從 `関与する成分`（機能性成分）關鍵字推斷：

| 日文關鍵字 | 統一 Category |
|-----------|---------------|
| ビタミン, カルシウム, 鉄, マグネシウム, 亜鉛 | `vitamins_minerals` |
| 茶カテキン, イソフラボン, 植物ステロール, ポリフェノール, 難消化性デキストリン, 食物繊維 | `botanicals` |
| ペプチド, アミノ酸, たんぱく質, コラーゲン, カゼイン | `protein_amino` |
| Lactobacillus, ビフィズス菌, 乳酸菌, Bifidobacterium, L.カゼイ, L.アシドフィルス, B.ブレーベ, B.ロンガム, ラクトバチルス, Streptococcus | `probiotics` |
| DHA, EPA, 脂肪酸, フィッシュオイル | `omega_fatty_acids` |
| 多成分複合（2 種以上不同類別成分） | `specialty` |
| 以上皆不符 | `other` |

> FOSHU 產品多為食品形態，「運動保健 (sports_fitness)」極少見。

## Product Form 推斷規則

從 `食品の種類`（食品種類）推斷：

| 日文關鍵字 | product_form |
|-----------|-------------|
| 錠剤 | `tablet` |
| カプセル | `capsule` |
| 粉末, 顆粒 | `powder` |
| 飲料, 清涼飲料水, はっ酵乳, 乳酸菌飲料, 豆乳 | `liquid` |
| ゼリー | `gummy` |
| その他 / 無法判定 | `other` |

> FOSHU 以飲料和發酵乳為主，大部分會映射為 `liquid`。

## `[REVIEW_NEEDED]` 觸發規則

以下情況**必須**標記 `[REVIEW_NEEDED]`：
1. 商品名為空
2. 関与する成分為空
3. 許可番号為空或重複

以下情況**不觸發** `[REVIEW_NEEDED]`：
- ❌ 日文內容未翻譯 — 系統保留原文
- ❌ category 推斷為 `other` — 成分描述可能不含標準關鍵字
- ❌ 區分為「条件付き特保」— 這是正常的 FOSHU 子分類

## 輸出格式

```markdown
---
source_id: "{許可番号}"
source_layer: "jp_foshu"
source_url: "https://www.caa.go.jp/policies/policy/food_labeling/foods_for_specified_health_uses/"
market: "jp"
product_name: "{商品名}"
brand: "{申請者}"
manufacturer: "{申請者}"
category: "{inferred category}"
product_form: "{inferred product_form}"
date_entered: "{許可日 YYYY-MM-DD}"
fetched_at: "{ISO8601 timestamp}"
---

# {商品名}

## 基本資訊
- 申請者：{申請者}
- 食品種類：{食品の種類}
- 劑型：{inferred product_form}
- 市場：日本
- 許可番號：{許可番号}
- 區分：{区分}
- 法人番號：{法人番号}

## 機能性成分
{関与する成分}

## 保健宣稱
{許可を受けた表示内容}

## 攝取注意事項
{摂取をする上での注意事項}

## 每日建議攝取量
{1日摂取目安量}

## 備註
{銷售實績或其他特殊情況}
```

## 輸出位置

`docs/Extractor/jp_foshu/{category}/{許可番号}.md`

## 自我審核 Checklist

- [ ] `source_id` 正確對應許可番号
- [ ] 日文內容完整保留
- [ ] `category` 依関与する成分關鍵字規則推斷
- [ ] `product_form` 依食品の種類關鍵字規則推斷
- [ ] frontmatter 格式正確
- [ ] `[REVIEW_NEEDED]` 僅在觸發條件成立時標記
