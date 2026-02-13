---
layout: default
title: 市場報告
nav_order: 2
parent: 納豆激酶 (2026-02-13)
grand_parent: 報告總覽
has_children: true
---

# 納豆激酶市場報告

每月更新的納豆激酶市場追蹤報告，包含產品統計、品牌分析、趨勢觀察。

## 最新報告

{% assign reports = site.pages | where_exp: "page", "page.path contains 'reports/nattokinase/reports/2'" | sort: "nav_order" | reverse %}
{% for report in reports %}
- [{{ report.title }}]({{ report.url | relative_url }})
{% endfor %}

## 報告內容

- 各國產品數量統計
- 熱門品牌排行
- 劑型分布分析
- 新品上市追蹤
- 市場趨勢觀察
