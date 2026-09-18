## Purpose

注册表描述类型「能怎样进、怎样列、怎样开、文件落在哪」，不负责复制文件。新增类型只改档案，不改浏览壳类型分支、不新增 views 克隆页。

## ADDED Requirements

### Requirement: 类型能力注册表

系统 SHALL 为每种启用的 `ResourceType` 提供 TypeProfile，至少含 ingestKind、consumeKind、defaultStorage/allowedStorage、默认来源、扩展名、侧栏路由与文案。调用方 MUST 查表，MUST NOT 用类型字面量 if/else 选择过滤表、播放器、是否目录导入或是否复制。

#### Scenario: 新增类型只改表

- **WHEN** 注册表增加一种已启用类型
- **THEN** 导入向导与侧栏出现该项；路由由档案生成到 TypeBrowse；ResourceBrowser 无新增类型分支
- **对应测试**：`tests.md` T1

#### Scenario: 未登记类型拒导入

- **WHEN** 请求导入未启用的 type
- **THEN** API 400，不创建资源
- **对应测试**：`tests.md` T2
