## MODIFIED Requirements

### Requirement: 详情返回通用元数据

系统 SHALL 在资源详情中提供封面引用、标题、评分、分类对象数组（`categories`，可为空）、标签列表、创建时间，以及至少 primary 文件的大小。分类 MUST 来自该资源类型的独立分类树，不得用资源 type 充当分类；同一资源可关联多个分类。缺失字段 MUST 可空渲染。

#### Scenario: 选中后可见通用字段

- **WHEN** 客户端请求已存在的 active 资源详情
- **THEN** 响应包含 title、createdAt、rating、categories（数组，可为空）、tags、files（含 primary 的 size 或显式空）

#### Scenario: 多分类资源

- **WHEN** 资源同时关联两个同类型分类
- **THEN** 详情返回两个分类对象，不合并为单个 category

#### Scenario: 资源不存在

- **WHEN** 客户端请求不存在的 id
- **THEN** HTTP 404，不返回半截对象

### Requirement: 部分更新标题评分分类与标签

系统 SHALL 接受 PATCH：可选 title、description、rating（0–10）、`categoryIds`（数组替换全部分类；空数组清空）、tagNames。`categoryIds` 中的分类 MUST 存在且属于资源类型，否则返回 422；分类类型不匹配或不存在时 MUST NOT 部分写入。tagNames 若出现则替换该资源全部标签；未知名字 SHALL 创建标签再关联。未出现的字段 MUST 保持原值。系统 SHALL 提供分类树与标签词表的只读列表接口；分类树管理属于 `library-category-tree` 能力。

#### Scenario: 只改评分

- **WHEN** PATCH 仅含 rating
- **THEN** 其它字段不变，响应中 rating 为新值

#### Scenario: 用 tagNames 替换标签

- **WHEN** PATCH `tagNames` 为两个新名字
- **THEN** 该资源恰好关联这两标签且 tags 表出现这两名；再 PATCH 空数组则无标签

#### Scenario: 多分类替换

- **WHEN** PATCH `categoryIds` 为两个同类型分类 ID
- **THEN** 资源恰好关联这两个分类；再 PATCH 空数组则清空分类

#### Scenario: 分类类型不符

- **WHEN** PATCH `categoryIds` 包含视频分类 ID，而资源是图片
- **THEN** 返回 422，资源原分类与其它字段不变

#### Scenario: 新分类名创建词条

- **WHEN** 用户在分类树中新建节点，并通过 PATCH `categoryIds` 将资源关联到该节点
- **THEN** 资源关联到新分类；资源 PATCH 不再按 `categoryName` 隐式创建分类
