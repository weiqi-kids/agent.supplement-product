---
layout: default
title: 首頁
nav_order: 1
---

# 保健食品產品情報系統

跨國保健食品市場監測與成分趨勢分析平台。

## 快速導覽

| 報告類型 | 說明 | 更新頻率 |
|----------|------|----------|
| [市場快照](/reports/market-snapshot/) | 各國市場產品統計與品類分佈 | 每週 |
| [成分雷達](/reports/ingredient-radar/) | 跨國成分趨勢與新興成分追蹤 | 每月 |

## 資料涵蓋範圍

本系統整合五大市場的官方保健食品資料庫：

| 國家 | 資料來源 | 產品數量 |
|------|----------|----------|
| 美國 | DSLD (Dietary Supplement Label Database) | 214,000+ |
| 加拿大 | LNHPD (Licensed Natural Health Products Database) | 149,000+ |
| 韓國 | HFF (Health Functional Food) | 44,000+ |
| 日本 | FOSHU (Foods for Specified Health Uses) | 1,000+ |
| 日本 | FNFC (Foods with Function Claims) | 1,500+ |

## 最新更新

{% assign market_reports = site.pages | where_exp: "page", "page.path contains 'market-snapshot'" | sort: "nav_order" | reverse %}
{% assign ingredient_reports = site.pages | where_exp: "page", "page.path contains 'ingredient-radar'" | sort: "nav_order" | reverse %}

### 市場快照
{% for report in market_reports limit: 3 %}
- [{{ report.title }}]({{ report.url | relative_url }})
{% endfor %}

### 成分雷達
{% for report in ingredient_reports limit: 3 %}
- [{{ report.title }}]({{ report.url | relative_url }})
{% endfor %}
