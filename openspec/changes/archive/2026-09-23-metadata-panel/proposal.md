# 提案 · metadata-panel

> 与 `docs/requirements/features/metadata-panel/需求.md` 同范围。

## 为什么

- 问题：选中后右侧栏几乎空白，无法整理评分/分类/标签/标题/封面。
- 为何现在做：导入已能进库；M2 详情是下一可感知块。
- 不做的后果：只能进不能改。

## 做什么

- 右侧展示通用字段；5 星评分。
- 面板可改评分/分类/标签草稿；Enter 切标签；**点保存**才 PATCH。
- 「编辑」弹窗含标题/简介/评分/分类/标签/**更换封面**；保存落地，取消不写。
- 分类、标签独立词表；保存时可新建词条。治理页不在本 change。
- 删除确认后软删并同步网格。
- **BREAKING：** 详情带 tags/files/category 对象；新增 categories 表。
- 不交付：抓取、过滤、词表管理、抽帧、彻底删。

## 范围

| | 内容 |
|--|------|
| IN | InfoPanel 展示与草稿保存；弹窗；cover API；categories+tags 创建；删除确认 |
| OUT | tag-category-hygiene 管理页；M3/M4 |
| 假设 | 无未关开放问题；待用户点 apply |

## 能力

### 新增

- `library-resource-metadata`：详情、PATCH 词条名、POST cover、GET 词表列表
- `desktop-metadata-panel`：面板/弹窗交互与确认删除

## 规范对齐

- 基线遵守（HTTP、后端 IO、软删、迁移）
- L1 评审中，开放问题已关；**未**口头 apply 前不准编码
- 与 hygiene：本切片创建词条，彼管理词条

## 现状要点

- InfoPanel 只读；PATCH 仅三字段；tags 表无 ORM；无 categories；put_cover 无入口

## 影响

- API：详情扩；GET /categories、/tags；PATCH categoryName/tagNames；POST cover
- 表：0003 categories + category_id
- 前端：InfoPanel + EditResourceModal

## 验收意图

见 tests.md。主路径：展示 → 草稿不自动存 → 保存 → 弹窗取消不写 → 换封面 → 确认删除。

## 开放问题

无。
