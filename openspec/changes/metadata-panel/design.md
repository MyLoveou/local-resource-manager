# 设计 · metadata-panel

> 与 `实现方案.md` 同一清单。

## 上下文

InfoPanel + PATCH 三字段 + 0001 tags 未映射 + 无分类表。基线：渲染只 HTTP；新表走 migrations。

## 与现有架构对齐

- UI → hooks → http → library api → use_cases → repositories
- 落在 InfoPanel 与 `app/library/`
- 不新开 metadata 子应用

## 目标 / 非目标

**目标：** 展示、草稿+保存、独立词表随保存创建、弹窗含换封面、确认删除。  
**非目标：** 词表管理页、抓取、导入重构。

## 方案

模块与文件、数据流见实现方案。

### 决策

| 决策 | 选择 | 不选 |
|------|------|------|
| 分类 | categories + FK | 自由文本 |
| 写入 | 显式保存 | 即时/失焦 |
| 封面 | 面板按钮立即 POST；弹窗进草稿随保存 | 弹窗选图立刻写盘 |

## 风险

见实现方案。

## 迁移

0003 → API → UI。回滚停用按钮；表可留。

## 注释

- categoryName / tagNames 查找或创建
- 分类 ≠ type
