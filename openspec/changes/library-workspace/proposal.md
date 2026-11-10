# Proposal

## Why

图片、合集、时间线、分类持续增加后，当前“类型页 + 扁平单值分类 + 多入口时间线”的结构开始把资源拆成互不相干的入口：主库混有二次元、真人 coser、风景，分类无法表达层级；时间线/地图与资源库各自成页；工具栏、批量条和信息栏的动作持续膨胀。

现在需要把**资源放回唯一底层**：分类变成每类型独立树，时间线/地图变成资源视图，合集保留为手动关系；同时收敛资源库导航、首页和操作区。

## What Changes

- 引入**每类型独立分类树**：资源与分类多对多；最多 4 层；单节点筛选包含后代；分类 CRUD/移动/删除保护；老分类迁移。
- 引入**保存的时间线筛选器**：按类型保存分类（可多选、并集）、标签、日期范围；无成员表；默认不含未知时间。
- 资源库改为「类型 tabs + 分类树 + 网格/时间线/地图视图切换」；时间线、地图不再作为独立数据入口。
- 首页改为资源工作台：最近添加缩略图（点击只开当前一张）、合集叠图卡、保存时间线、继续整理、最近消费。
- 合集卡采用 D 卡（封面 + hover/focus 扇形）；合集详情按类型 tabs 筛选。
- 批量选择支持 `Ctrl + 左键` 切换、`Shift + 左键` 范围替换、`Esc` 退出。
- **BREAKING**：资源分类从单值 `category`/`categoryName` 改为多值 `categories`/`categoryIds`；旧分类单值列迁移后移除。
- 地图首版只做入口/空态，完整地图交互后置。

## Capabilities

### New Capabilities

- `library-category-tree`: 每类型分类树、资源多分类、子树筛选、分类管理与迁移。
- `library-saved-views`: 按类型保存时间线筛选器（多分类并集、标签、日期），无成员表。
- `desktop-library-workspace`: 资源库导航、类型 tabs、分类树、视图切换、首页工作台、合集 D 卡、批量快捷键与操作区层级。

### Modified Capabilities

- `library-resource-metadata`: 资源详情与部分更新改为多分类；分类对象数组与 `categoryIds` 取代单值 `category`/`categoryName`。

## Impact

- **DB**：新增分类树字段与资源-分类连接表、保存视图表；迁移旧分类与 `resources.category_id`；不移动库内文件。
- **Backend**：分类 CRUD/树查询/计数、资源列表子树筛选、保存视图 CRUD、首页聚合、合集预览缩略图；现有 `library-resource-api` 与 metadata DTO 调整。
- **Desktop**：资源库 Shell、类型 tabs、分类树、视图切换、首页、合集卡、批量快捷键、信息栏分区；旧 `/photos` 与类型页路由重定向/兼容。
- **Compatibility**：现有分类/资源/合集数据保留；旧 API 单分类字段移除，前端同步升级。
- **Out**：角色/人脸、多节点分类筛选、时间线成员表、物理目录、完整 MapLibre 交互。
