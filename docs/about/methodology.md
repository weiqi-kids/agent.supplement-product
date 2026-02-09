---
layout: default
title: 方法論
nav_order: 2
parent: 關於系統
---

# 方法論說明

## 資料處理流程

### 1. 擷取（Fetch）

從各國官方資料庫下載原始資料：
- 使用官方 API 或公開資料集
- 定期檢查資料更新
- 保留原始資料備份

### 2. 萃取（Extract）

解析原始資料，標準化產品資訊：
- 統一欄位格式
- 標準化成分名稱
- 分類對應

### 3. 分析（Analyze）

跨國比較與趨勢分析：
- 成分熱度計算
- 品類統計
- 跨國比較

### 4. 報告（Report）

產出定期報告：
- 市場快照（週報）
- 成分雷達（月報）

## 產品分類

本系統採用統一的產品分類標準：

| 分類 | 說明 |
|------|------|
| vitamins_minerals | 維生素與礦物質 |
| botanicals | 植物萃取 |
| probiotics | 益生菌 |
| omega_fatty_acids | Omega 脂肪酸 |
| protein_amino | 蛋白質與胺基酸 |
| sports_fitness | 運動營養 |
| specialty | 特殊配方 |
| other | 其他 |

## 資料品質

- 資料來源：各國官方資料庫
- 更新頻率：每日擷取
- 資料驗證：自動化檢查機制
