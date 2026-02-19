# 內容規格書

> **產出日期**：2026-02-19

---

## 規格書清單

| 頁面 | 優先級 | 階段 | 類型 |
|------|--------|------|------|
| sitemap.xml | P0 | Phase 1 | 新增 |
| robots.txt | P0 | Phase 1 | 新增 |
| 首頁價值主張 | P1 | Phase 2 | 修改 |

---

## 1. sitemap.xml 規格

### 基本資訊

| 項目 | 內容 |
|------|------|
| 檔案路徑 | docs/sitemap.xml |
| 類型 | 新增 |
| 優先級 | P0 |

### 內容規格

```xml
<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <!-- 首頁 -->
  <url>
    <loc>https://supplement.weiqi.kids/</loc>
    <lastmod>YYYY-MM-DD</lastmod>
    <changefreq>weekly</changefreq>
    <priority>1.0</priority>
  </url>

  <!-- 各成分主題頁 -->
  <url>
    <loc>https://supplement.weiqi.kids/reports/{topic}/</loc>
    <lastmod>YYYY-MM-DD</lastmod>
    <changefreq>monthly</changefreq>
    <priority>0.8</priority>
  </url>

  <!-- 選購指南 -->
  <url>
    <loc>https://supplement.weiqi.kids/reports/{topic}/guide</loc>
    <lastmod>YYYY-MM-DD</lastmod>
    <changefreq>monthly</changefreq>
    <priority>0.7</priority>
  </url>

  <!-- 市場報告 -->
  <url>
    <loc>https://supplement.weiqi.kids/reports/{topic}/reports/{period}</loc>
    <lastmod>YYYY-MM-DD</lastmod>
    <changefreq>monthly</changefreq>
    <priority>0.6</priority>
  </url>
</urlset>
```

### 自動化建議

使用 Jekyll 插件 `jekyll-sitemap` 自動生成，或建立 Python 腳本：

```bash
python3 scripts/generate_sitemap.py
```

---

## 2. robots.txt 規格

### 基本資訊

| 項目 | 內容 |
|------|------|
| 檔案路徑 | docs/robots.txt |
| 類型 | 新增 |
| 優先級 | P0 |

### 內容規格

```
User-agent: *
Allow: /

Sitemap: https://supplement.weiqi.kids/sitemap.xml
```

---

## 3. 首頁價值主張優化規格

### 基本資訊

| 項目 | 內容 |
|------|------|
| 檔案路徑 | docs/index.md |
| 類型 | 修改 |
| 優先級 | P1 |

### 修改內容

#### 新增區塊：數據亮點

```markdown
## 為什麼選擇我們？

| 優勢 | 數據 |
|------|------|
| 🌍 跨國市場 | 整合美、加、日、韓、台 5 國官方資料庫 |
| 📊 產品數量 | 超過 42 萬筆產品資料 |
| 🔄 即時更新 | 自動化系統持續追蹤最新資訊 |
| ⚖️ 中立客觀 | 無導購、無業配、純資訊服務 |
```

### SEO 規格

| 項目 | 規格 |
|------|------|
| Title | 保健食品產品情報系統｜跨國市場監測與成分分析 |
| Meta Description | 整合美、加、日、韓、台 5 國官方資料庫，提供 42 萬+ 保健食品資訊。中立客觀的選購指南與市場分析。 |

---

## 4. 相關成分連結修復規格

### 修改範圍

| 頁面 | 問題項目 | 處理方式 |
|------|----------|----------|
| 魚油主題頁 | CoQ10 | 移除連結或新增頁面 |
| 外泌體主題頁 | 幹細胞萃取 | 移除連結 |
| 外泌體主題頁 | 胎盤萃取 | 移除連結 |

### 建議處理

**短期**：移除無效連結，保留文字說明
**長期**：新增 CoQ10 等熱門成分追蹤

---

## 5. 藥物交互表清理規格

### 修改範圍

| 頁面 | 問題 | 處理方式 |
|------|------|----------|
| 魚油選購指南 | 混入 NMN、外泌體等不相關成分 | 移除不相關條目 |

### 清理標準

僅保留與該成分直接相關的藥物交互文獻：
- 魚油頁面：只保留 Omega-3、EPA、DHA 相關
- 其他成分比照辦理

---

## 檢查清單

### Phase 1 完成標準

- [ ] sitemap.xml 可正常訪問
- [ ] robots.txt 可正常訪問
- [ ] Google Search Console 已提交 sitemap

### Phase 2 完成標準

- [ ] 所有相關成分連結已修復
- [ ] 藥物交互表已清理
- [ ] 首頁價值主張區塊已新增
