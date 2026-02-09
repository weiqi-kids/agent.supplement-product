---
layout: default
title: 成分雷達
nav_order: 4
parent: 報告總覽
has_children: true
---

# 成分雷達

每月發布，深入分析跨國成分趨勢與新興成分追蹤。

## 報告內容

- 成分熱度排行
- 新興成分追蹤
- 跨國成分比較
- 品類成分分析

## 歷史報告

{% assign reports = site.pages | where_exp: "page", "page.path contains 'reports/ingredient-radar/2'" | sort: "nav_order" | reverse %}
{% for report in reports %}
- [{{ report.title }}]({{ report.url | relative_url }})
{% endfor %}
