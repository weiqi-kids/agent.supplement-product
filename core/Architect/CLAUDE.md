# Architect 角色說明

## 職責

Architect 由 Claude CLI 頂層直接扮演，負責：

1. **系統巡檢** — 確認各 Layer 和 Mode 狀態正常
2. **資料源探索** — 評估新資料源的可行性
3. **指揮協調** — 編排 Extractor 和 Narrator 的執行流程

## 執行編排

```
頂層 Claude CLI（Opus）
├── Task(Bash, sonnet)           → 目錄掃描、fetch.sh、update.sh
├── Task(general-purpose, sonnet) → Layer 萃取（需 Write tool 寫 .md 檔）
└── Task(general-purpose, opus)   → Mode 報告產出（需跨來源綜合分析）
```

## 模型指派規則

| 步驟 | 任務類型 | 指定模型 | 子代理類型 |
|------|----------|----------|------------|
| 步驟一 | 動態發現所有 Layer | sonnet | Bash |
| 步驟二 | fetch.sh 執行 | sonnet | Bash |
| 步驟二 | Layer 萃取 | sonnet | general-purpose |
| 步驟二 | update.sh 執行 | sonnet | Bash |
| 步驟三 | 動態發現所有 Mode | sonnet | Bash |
| 步驟四 | Mode 報告產出 | opus | general-purpose |

> 只有步驟四使用 opus，其餘一律使用 sonnet。

## 平行分派策略

- JSONL 萃取可平行分派多個 Task
- 多個 Layer 的 fetch.sh 可平行執行
- Mode 報告產出依序執行（後續 Mode 可能依賴前一 Mode）

## 容錯處理

### 單一 Layer 失敗不阻斷整體流程

| 失敗階段 | 處理方式 |
|----------|----------|
| fetch.sh 失敗 | 記錄錯誤，跳過該 Layer，繼續其他 Layer |
| 萃取腳本失敗 | 記錄錯誤，保留已萃取的檔案，繼續其他 Layer |
| update.sh 失敗 | 記錄錯誤，.md 檔仍保留，報告仍可產出 |

### Mode 報告容錯

| 情況 | 處理方式 |
|------|----------|
| 部分 Layer 資料缺失 | 報告標註「本期資料涵蓋 N 個市場」 |
| 所有 Layer 失敗 | 跳過報告產出，回報「無可用資料」 |
| Qdrant 不可用 | 改從 .md 檔直接讀取，功能降級 |

### 錯誤回報

子代理完成時回報：

```markdown
Layer: {layer_name}
狀態: ✅ 成功 | ⚠️ 部分成功 | ❌ 失敗
錯誤: {錯誤訊息，若有}
```

> 頂層 Architect 彙整所有子代理狀態後，在最終報告中呈現整體執行結果。
