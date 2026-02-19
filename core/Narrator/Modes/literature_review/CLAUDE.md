# Mode: literature_review — 文獻薈萃報告

## Mode 定義表

| 項目 | 說明 |
|------|------|
| **Mode name** | literature_review（文獻薈萃） |
| **Purpose** | 針對追蹤主題產出學術文獻統計與分析報告 |
| **Audience** | 研究人員、產品開發人員、專業消費者 |
| **來源 Layer** | pubmed |
| **週期** | 月報 |

## 資料來源

- 讀取 `docs/Extractor/pubmed/{topic_id}/*.md` 文獻資料
- 依據 `core/Narrator/Modes/topic_tracking/topics/*.yaml` 取得主題清單

## 報告框架

```markdown
---
topic: "{topic_id}"
period: "YYYY-MM"
generated_at: "{ISO8601}"
total_articles: {N}
---

# {主題名稱}文獻薈萃報告 — YYYY 年 M 月

## 摘要
本月共收錄 {topic} 相關文獻 N 篇，其中 Level 1 證據（Meta-Analysis/Systematic Review）
N 篇，RCT N 篇。主要研究方向集中於...

## 證據等級分布

| 證據等級 | 文獻數 | 佔比 |
|----------|--------|------|
| Level 1 (Meta-Analysis/Systematic Review) | N | X% |
| Level 2 (RCT) | N | X% |
| Level 3 (Clinical Trial) | N | X% |
| Level 4 (Observational) | N | X% |
| Level 5 (Review/Case Report) | N | X% |

## 功效分類統計

| 功效分類 | 中文 | 文獻數 | 佔比 | 主要結論 |
|----------|------|--------|------|----------|
| cardiovascular | 心血管 | N | X% | ... |
| cognitive | 認知功能 | N | X% | ... |
| immune | 免疫調節 | N | X% | ... |
| metabolic | 代謝 | N | X% | ... |
| ... | | | | |

## 成分搭配統計

| 搭配成分 | 文獻數 | 常見研究設計 |
|----------|--------|-------------|
| + Vitamin D | N | RCT 居多 |
| + Vitamin E | N | 觀察性研究 |
| ... | | |

## 研究類型分布

| 研究類型 | 文獻數 | 佔比 |
|----------|--------|------|
| meta_analysis | N | X% |
| systematic_review | N | X% |
| rct | N | X% |
| clinical_trial | N | X% |
| observational | N | X% |
| review | N | X% |
| case_report | N | X% |
| other | N | X% |

## 近期重要文獻

### Level 1 證據（Meta-Analysis / Systematic Review）

1. **[標題](PubMed連結)** — 期刊, 日期
   - 功效分類：{categories}
   - 摘要：...

2. ...

### Level 2 證據（RCT）

1. **[標題](PubMed連結)** — 期刊, 日期
   - 功效分類：{categories}
   - 摘要：...

2. ...

## 研究趨勢觀察

- 近期研究熱點：...
- 新興研究方向：...
- 值得關注的發現：...
```

## 執行腳本

```bash
# 產出所有主題的文獻薈萃報告
python3 scripts/generate_literature_report.py

# 產出特定主題
python3 scripts/generate_literature_report.py --topic fish-oil

# 指定報告期間
python3 scripts/generate_literature_report.py --topic exosomes --period 2026-02
```

## 輸出位置

```
docs/Narrator/literature_review/
├── fish-oil/
│   └── 2026-02.md
├── exosomes/
│   └── 2026-02.md
└── ...
```

## 功效分類對照表

| claim_category | 中文名稱 | 統計說明 |
|---------------|----------|----------|
| anti_aging | 抗衰老 | 涵蓋老化、壽命、端粒相關研究 |
| cardiovascular | 心血管 | 血脂、血壓、心臟疾病風險 |
| cognitive | 認知功能 | 記憶、大腦健康、神經保護 |
| immune | 免疫調節 | 發炎、免疫反應、自體免疫 |
| metabolic | 代謝 | 血糖、體重、代謝症候群 |
| musculoskeletal | 肌肉骨骼 | 肌肉、骨骼、關節健康 |
| sexual | 性功能 | 性功能、生殖健康 |
| skin | 皮膚 | 皮膚健康、抗皺、光老化 |
| digestive | 消化 | 腸道健康、微生物組 |
| energy | 活力 | 疲勞、體力、運動表現 |
| other | 其他 | 無法歸類的研究 |

## 與其他 Mode 的關係

| Mode | 關係 |
|------|------|
| topic_tracking | 互補：topic_tracking 追蹤產品，literature_review 追蹤證據 |
| ingredient_radar | 上游：成分趨勢可用於驗證文獻研究方向 |

## 自我審核 Checklist

- [ ] 報告期間正確
- [ ] 文獻數量與來源檔案一致
- [ ] 證據等級分類正確
- [ ] 功效分類統計完整
- [ ] 重要文獻連結有效
- [ ] 摘要簡潔且具資訊量
- [ ] frontmatter 格式正確

---

## ⚠️ 子代理精簡回報規範

完成後**只輸出一行**：
```
DONE|literature_review|{topic1}:{數量},{topic2}:{數量}|OK
```

範例：
```
DONE|literature_review|exosomes:50,fish-oil:500|OK
```

**禁止**：
- ❌ 輸出證據等級分布表
- ❌ 列舉文獻清單
- ❌ 重複功效分類統計
