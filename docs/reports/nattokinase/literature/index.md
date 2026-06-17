---
grand_parent: 報告總覽
has_children: true
layout: default
nav_order: 4
parent: 納豆激酶 2026-06-01
title: 文獻薈萃
---

# 納豆激酶文獻薈萃

歷史文獻薈萃報告列表。

{% assign reports = site.pages | where_exp: "page", "page.path contains 'reports/nattokinase/literature/2'" | sort: "nav_order" | reverse %}
{% for report in reports %}
- [{{ report.title }}]({{ report.url | relative_url }})
{% endfor %}
