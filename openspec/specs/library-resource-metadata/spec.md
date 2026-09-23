# library-resource-metadata Specification

## Purpose
本能力让本机库在选出一条资源后，能在右侧看到通用文件与整理字段，并能改评分、分类、标签、标题和封面，删除仍走软删。它补齐导入之后「能看见、能改」的详情闭环，不包含网上抓取或按标签检索。

## Requirements

### Requirement: 详情返回通用元数据

系统 SHALL 在资源详情中提供封面引用、标题、评分、分类对象（id+name 或 null）、标签列表、创建时间，以及至少 primary 文件的大小。分类 MUST 来自独立词表，不得用资源 type 充当分类。缺失字段 MUST 可空渲染。

#### Scenario: 选中后可见通用字段

- **WHEN** 客户端请求已存在的 active 资源详情
- **THEN** 响应包含 title、createdAt、rating、category（对象或 null）、tags、files（含 primary 的 size 或显式空）
- **对应测试**：`tests.md` T1

#### Scenario: 资源不存在

- **WHEN** 客户端请求不存在的 id
- **THEN** HTTP 404，不返回半截对象
- **对应测试**：`tests.md` T2

### Requirement: 部分更新标题评分分类与标签

系统 SHALL 接受 PATCH：可选 title、description、rating（0–10）、categoryName（null 清空；非空则查找或创建 categories 行并设置外键）、tagNames。tagNames 若出现则替换该资源全部标签；未知名字 SHALL 创建标签再关联。未出现的字段 MUST 保持原值。系统 SHALL 提供分类与标签词表的只读列表接口。本切片 MUST NOT 提供删除或合并词条的管理 API。

#### Scenario: 只改评分

- **WHEN** PATCH 仅含 rating
- **THEN** 其它字段不变，响应中 rating 为新值
- **对应测试**：`tests.md` T3

#### Scenario: 用 tagNames 替换标签

- **WHEN** PATCH `tagNames` 为两个新名字
- **THEN** 该资源恰好关联这两标签且 tags 表出现这两名；再 PATCH 空数组则无标签
- **对应测试**：`tests.md` T4

#### Scenario: 新分类名创建词条

- **WHEN** PATCH `categoryName` 为库中不存在的名字
- **THEN** 新建 categories 行，资源 category 指向它
- **对应测试**：`tests.md` T4b

### Requirement: 更换封面不替换主文件

系统 SHALL 接受本机图片路径，将字节复制为资源包 `cover` 角色并更新封面引用。primary 文件路径与哈希 MUST 保持不变。非法路径或非图片 SHALL 400。

#### Scenario: 换封面成功

- **WHEN** 对已有资源 POST cover 且 path 指向存在的图片
- **THEN** 存在 role=cover 的 files 行，coverPath 可用于读取封面，primary 行未改
- **对应测试**：`tests.md` T5

#### Scenario: 路径无效

- **WHEN** path 不存在或不是允许的图片扩展名
- **THEN** 400，库内文件树与封面引用不变
- **对应测试**：`tests.md` T6
