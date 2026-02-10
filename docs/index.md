---
layout: default
title: 首頁
nav_order: 1
---

# 保健食品產品情報系統

跨國保健食品市場監測與成分趨勢分析平台。

## 快速導覽

### 主題追蹤

深入追蹤特定成分/產品類型的市場動態：

| 主題 | 說明 | 產品數 |
|------|------|--------|
| [外泌體]({{ site.baseurl }}/reports/exosomes/) | 細胞修復、抗老化相關產品 | 9,675 |
| [魚油]({{ site.baseurl }}/reports/fish-oil/) | Omega-3、EPA/DHA 相關產品 | 15,444 |

### 定期報告

| 報告類型 | 說明 | 更新頻率 |
|----------|------|----------|
| [市場快照]({{ site.baseurl }}/reports/market-snapshot/) | 各國市場產品統計與品類分佈 | 每週 |
| [成分雷達]({{ site.baseurl }}/reports/ingredient-radar/) | 跨國成分趨勢與新興成分追蹤 | 每月 |

## 資料涵蓋範圍

本系統整合五大市場的官方保健食品資料庫，共計超過 **41 萬筆**產品資料：

| 國家 | 資料來源 | 產品數量 |
|------|----------|----------|
| 🇺🇸 美國 | DSLD (Dietary Supplement Label Database) | 214,780 |
| 🇨🇦 加拿大 | LNHPD (Licensed Natural Health Products Database) | 149,243 |
| 🇰🇷 韓國 | HFF (Health Functional Food) | 44,246 |
| 🇯🇵 日本 | FNFC (Foods with Function Claims) | 1,110 |
| 🇯🇵 日本 | FOSHU (Foods for Specified Health Uses) | 1,031 |

## 最新更新

{% assign market_reports = site.pages | where_exp: "page", "page.path contains 'market-snapshot'" | sort: "nav_order" | reverse %}
{% assign ingredient_reports = site.pages | where_exp: "page", "page.path contains 'ingredient-radar'" | sort: "nav_order" | reverse %}

### 市場快照
{% for report in market_reports limit: 3 %}
{% unless report.title == "市場快照" %}
- [{{ report.title }}]({{ report.url | relative_url }})
{% endunless %}
{% endfor %}

### 成分雷達
{% for report in ingredient_reports limit: 3 %}
{% unless report.title == "成分雷達" %}
- [{{ report.title }}]({{ report.url | relative_url }})
{% endunless %}
{% endfor %}

### 主題追蹤
- [外泌體 2026-02]({{ site.baseurl }}/reports/exosomes/reports/2026-02.html) — 9,675 筆產品分析
- [魚油 2026-02]({{ site.baseurl }}/reports/fish-oil/reports/2026-02.html) — 15,444 筆產品分析

## 系統特色

- **自動化更新**：每日自動同步各國官方資料庫
- **跨國比較**：統一格式呈現不同國家的產品資訊
- **成分標準化**：自動對照英文、日文、韓文成分名稱
- **趨勢分析**：追蹤成分排名變化與市場動態

---

*最後更新：2026 年 2 月*
