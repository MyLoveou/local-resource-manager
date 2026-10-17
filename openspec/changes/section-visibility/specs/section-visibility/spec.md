## Purpose

为本地媒体库桌面端提供代码级的分区可见性配置，让尚未实现或未完整实现的分区（如 AV、小说、漫画、游戏、模型）不再出现在菜单、导入向导和首页概览中，并拦截直达 URL；配置只影响入口展示，不改变资源数据与 API。

## ADDED Requirements

### Requirement: 分区可见性配置

系统 SHALL 通过单一代码配置 `HIDDEN_SECTIONS`（路由 path 列表）控制分区入口的隐藏，所有入口（菜单、路由、导入向导、首页概览）读取同一判定，配置为空时行为与现状一致；`/` 首页不可被隐藏。

#### Scenario: 主路径成功（默认清单全链路隐藏）

- **WHEN** 配置为默认 `['/av','/novel','/comic','/game','/model']` 并启动应用
- **THEN** 左侧菜单不出现 AV/小说/漫画/游戏/模型；地址栏访问 `#/av` 重定向回首页；导入向导类型选项不含这 5 类；首页概览不出现这 5 类统计卡
- **对应测试**：`tests.md` T1/T2/T3

#### Scenario: 空配置不改变现状

- **WHEN** `HIDDEN_SECTIONS` 为空数组
- **THEN** 菜单、路由、导入向导、首页概览与未引入该配置时一致
- **对应测试**：`tests.md` T4

#### Scenario: 边界（未知 key / 子路径 / 首页）

- **WHEN** 配置含不存在的 path；或配置 `'/collections'` 后访问 `#/collections/1`；或配置 `'/'`
- **THEN** 未知 path 被忽略且无报错；`/collections/1` 与 `/collections` 一并重定向首页；`'/'` 被忽略，首页始终可访问
- **对应测试**：`tests.md` T3/T5

## MODIFIED Requirements

（无）

## REMOVED Requirements

（无）
