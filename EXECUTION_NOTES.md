# 執行經驗記錄

> 記錄「執行完整流程」的經驗與優化建議

---

## 2026-02-21 執行記錄

### 執行成果

| 階段 | 結果 |
|------|------|
| Layer 資料處理 | 10/10 完成，總計 590K fetch、411K extract |
| Mode 報告產出 | 4/4 完成 |
| 選購指南交互更新 | 9/9 指南 |
| 主題推薦 | 5 個新建議（Vitamin B12, E, D, A, B2） |
| Jekyll + SEO | 36 份報告，100% 通過 |
| 部署驗證 | GitHub Actions 成功，網站內容正確 |
| 品質關卡 | PASS |

### 經驗教訓

#### 1. 子代理回報格式不一致

**問題**：部分子代理回報時夾帶範本文字，如：
```
DONE|us_dsld|F:{fetch筆數}|E:{extract筆數}...
```

**解法**：子代理 prompt 需更明確強調「只輸出結果，不輸出範本」

#### 2. 背景任務監控效率

**問題**：初期使用 `grep "DONE|"` 會誤匹配 JSON log 中的內容

**解法**：使用 `grep -o 'DONE|[^"]*'` 精確提取回報格式

#### 3. Layer 執行順序

**觀察**：大型 Layer（us_dsld, ca_lnhpd）耗時較長，小型 Layer（tw_hf, jp_foshu）很快完成

**建議**：可以先等小型 Layer 完成後就開始部分 Mode 報告，減少整體等待時間

#### 4. 去重檢查有效

**觀察**：Session 恢復時去重檢查正確跳過了今日已產出的報告，避免重複執行

---

## 已授權項目清單

> 這些項目已在本次執行中授權，後續執行無需再次授權

### Bash 指令類

已在 `.claude/settings.local.json` 設定 `"Bash"` 允許，涵蓋：

- `python3 scripts/*.py` - 所有 Python 腳本執行
- `./core/Extractor/Layers/*/fetch.sh` - Layer fetch 腳本
- `./core/Extractor/Layers/*/update.sh` - Layer update 腳本
- `git add/commit/push` - Git 操作
- `gh run list/watch` - GitHub CLI 操作
- `ls/find/grep/wc` - 檔案操作
- `sleep` - 等待指令

### 檔案操作類

- `Read(*)` - 讀取任意檔案
- `Write(*)` - 寫入任意檔案
- `Edit(*)` - 編輯任意檔案

### 網路存取類

- `WebFetch(domain:supplement.weiqi.kids)` - 網站驗證
- `WebFetch(domain:*)` - 通用網頁存取
- `WebSearch` - 網路搜尋

---

## 優化建議

### 短期

1. **子代理 prompt 強化**：在 CLAUDE.md 的子代理範本中加入「禁止輸出範本文字」

2. **監控指令標準化**：記錄正確的監控指令格式供日後使用

### 中期

1. **平行化優化**：小型 Layer 完成後可先啟動不依賴大型資料的 Mode

2. **增量報告**：對於未變更的主題，可跳過報告重新產出

### 長期

1. **自動化排程**：設定 cron 或 GitHub Actions 定期執行完整流程

---

## 常用指令速查

```bash
# 檢查 Layer 資料數量
for layer in us_dsld ca_lnhpd kr_hff jp_fnfc jp_foshu tw_hf pubmed dhi dfi ddi; do
  count=$(find docs/Extractor/$layer -name "*.md" 2>/dev/null | wc -l | tr -d ' ')
  echo "$layer: $count"
done

# 檢查報告產出狀態
ls docs/Narrator/market_snapshot/2026-W*
ls docs/Narrator/topic_tracking/*/2026-02.md | wc -l
ls docs/Narrator/literature_review/*/2026-02.md | wc -l

# 驗證 SEO
python3 scripts/validate_seo.py

# 監控背景任務（精簡版）
for f in /private/tmp/claude/-Users-lightman-weiqi-kids-agent-supplement-product/tasks/*.output; do
  name=$(basename "$f" .output)
  result=$(grep -o 'DONE|[^"]*' "$f" 2>/dev/null | tail -1)
  [ -n "$result" ] && echo "✅ $result" || echo "⏳ $name"
done
```

---

*最後更新：2026-02-21*
