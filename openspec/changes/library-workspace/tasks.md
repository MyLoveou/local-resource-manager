# Tasks

> 收尾状态（2026-10-27）：剩余项均为需人工在 Electron 内验收，清单见 `docs/requirements/收尾清单.md`。

## 1. 动工与迁移

- [ ] 1.1 单独提交当前 R1/时间线改动，建 `feat/library-workspace`，备份 DB/release；验证：工作区无混入、备份可打开 ← 不再适用（分支已合并，见收尾清单）
- [x] 1.2 写 `0018_category_tree.sql`：分类树字段、`resource_categories`、多类型复制、待整理分类、索引与外键检查；验证：临时库迁移通过
- [x] 1.3 写 `0019_saved_views.sql`：保存视图表与唯一索引；验证：新库/旧库都能迁移
- [x] 1.4 更新 ORM/domain（Category 树、Resource.categories、ResourceCategory、SavedView）；验证：导入无错、旧列标记 deprecated
- [x] 1.5 迁移测试：资源/关系/合集对账、多类型复制、待整理分类、文件路径不变；验证：新测试通过
- [x] 1.6 更新 `facts.md` 迁移说明与 change handoff；验证：文档与迁移行为一致

## 2. 分类树后端

- [x] 2.1 实现 CategoryRepository：树读取、后代展开、计数、CRUD/移动/删除保护；验证：树/深度/循环/删除测试通过
- [x] 2.2 实现 CategoryService/API：`GET/POST/PATCH/DELETE /library/categories`；验证：API 成功与 4xx 场景通过
- [x] 2.3 资源多分类：Resource DTO `categories`、PATCH `categoryIds`、类型校验、旧 `categoryName` 移除；验证：多分类/清空/422 测试通过
- [x] 2.4 资源列表支持 `categoryIds[]`、单值兼容、`uncategorized`；验证：子树/多值/未分类/计数去重测试通过
- [x] 2.5 时间线查询支持类型/分类/日期/未知时间；验证：图片/视频分开、日期过滤测试通过
- [x] 2.6 更新 metadata/search/trash/type 相关后端测试；验证：后端相关测试全绿

## 3. 保存视图、首页与合集预览后端

- [x] 3.1 实现 SavedViewRepository/Service/API：CRUD、类型/重名/筛选校验；验证：保存时间线测试通过
- [x] 3.2 分类删除清理保存视图 filters；验证：删除引用分类后筛选继续正确
- [x] 3.3 时间线多分类并集与未知时间默认排除；验证：并集/默认排除/显式包含测试通过
- [x] 3.4 实现 `/library/home` 聚合（最近 12、时间线、统计、工作/消费）；验证：限量与空库测试通过
- [x] 3.5 合集 `previewThumbnails`（≤3）与批量计数/预览查询；验证：0/1/3 成员、无 N+1 测试通过
- [x] 3.6 更新 OpenSpec/API 文档与 handoff；验证：契约与实现一致

## 4. 前端分类树与赋值

- [x] 4.1 新增 domain/http（CategoryNode、SavedView、workspace；categories/savedViews/home）；验证：typecheck 通过
- [x] 4.2 扩展 browseQuery（categoryIds/view/savedViewId/reset）与 useResourcePage；验证：store 单测通过
- [x] 4.3 实现 CategoryTreePanel/管理弹窗（默认展开第一层、待整理分类非空显示）；验证：树交互 CDP 通过
- [x] 4.4 信息栏/编辑弹窗改多分类 chips + 树选择；验证：多分类保存/清空 CDP 通过
- [x] 4.5 分类树/赋值组件单测与 lint；验证：前端测试/typecheck/lint 通过

## 5. 工作区 Shell 与路由

- [x] 5.1 新增 `/library/:type` 规范路由与 `LibraryWorkspace` 组合根；验证：路由可达
- [x] 5.2 旧类型路由与 `/photos` 重定向；验证：旧链接 CDP 不 404
- [x] 5.3 TypeTabs/ViewSwitch/菜单 active 匹配；验证：类型切换与视图切换 CDP 通过
- [x] 5.4 类型切换重置全部筛选（视图保留/不支持回网格）；验证：CDP 断言重置
- [x] 5.5 隐藏类型不出现；验证：隐藏配置下 tabs CDP 通过
- [x] 5.6 路由/导航文档与 tests 记录；验证：文档与行为一致

## 6. 保存时间线 UI 与地图占位

- [x] 6.1 PhotoTimeline 接多分类/日期/保存视图；验证：保存/选择/删除 CDP 通过
- [x] 6.2 图片/视频时间线拆分，旧混合页迁移；验证：两个类型 tabs 结果正确
- [x] 6.3 未知时间默认排除、可显式开启；验证：过滤 CDP 通过
- [x] 6.4 地图视图入口/空态（不实现完整地图）；验证：切换不阻塞网格/时间线
- [x] 6.5 保存视图/时间线测试与 handoff；验证：tests.md 对应行通过

## 7. 首页、合集卡、快捷键与操作区

- [x] 7.1 首页接 `/library/home`，最近缩略图只打开当前；验证：CDP 路由不变/查看器打开
- [x] 7.2 CollectionCard D（0/1/3 成员、hover/focus、reduced motion）；验证：CDP + 键盘打开
- [x] 7.3 合集页与首页统一 D 卡；验证：两处卡片一致
- [x] 7.4 合集详情类型 tabs + 分类树；验证：跨类型合集筛选 CDP 通过
- [x] 7.5 批量 Ctrl/Shift/Esc 与范围替换；验证：选择/范围/Esc CDP 通过
- [x] 7.6 全局/上下文/批量/信息栏分区；验证：批量动作不污染全局栏
- [x] 7.7 更新 UI 文档与 tests；验证：文档与行为一致

## 8. 集成与交付

- [x] 8.1 全量后端测试（含迁移副本）通过；验证：pytest 190+ 全绿
- [x] 8.2 前端 typecheck/lint/build 全绿；验证：命令退出码 0
- [x] 8.3 CDP 主路径：分类树→视图→保存时间线→首页→合集→快捷键；验证：tests.md 记录
- [ ] 8.4 迁移/性能抽查（大库分类计数、首页/合集 N+1）；验证：无回退
- [x] 8.5 `pnpm release:win` 重打包并 verify；验证：安装包/健康检查/SHA 通过
- [x] 8.6 更新 facts/decisions/handoff/todo；验证：文档同步
- [ ] 8.7 `code-review-gate` → `verification-gate`（含 tests.md）；验证：门禁通过 ← 随下次评审执行
