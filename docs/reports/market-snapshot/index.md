---
layout: default
title: 📊 市場快照
nav_order: 100
parent: 報告總覽
has_children: true
---

# 市場快照

每週發布，涵蓋五大市場的保健食品產品統計與品類分佈。

## 報告內容

- 各市場產品數量統計
- 熱門品類排行
- 市場亮點與趨勢觀察
- 跨國比較分析

## 歷史報告

{% assign reports = site.pages | where_exp: "page", "page.path contains 'reports/market-snapshot/2'" | sort: "nav_order" | reverse %}
{% for report in reports %}
- [{{ report.title }}]({{ report.url | relative_url }})
{% endfor %}
