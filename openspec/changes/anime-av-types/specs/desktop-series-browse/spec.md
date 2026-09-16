## Purpose

桌面番剧页与 AV 页以作品封面为网格单位。选中作品后信息栏展示专用档案、季/集与特典；用户点某一集或特典才打开现有视频覆盖层。离开这些页不得因播放器映射抛错而卡住路由。菜单显示「番剧」。

## ADDED Requirements

### Requirement: 作品卡与信息栏选集

单击作品卡 SHALL 只选中并加载作品详情，MUST NOT 立即按第一集开播。信息栏 SHALL 列出季、集、特典，并提供集列表 **封面模式** 与 **仅序号模式**。选择一集或特典 SHALL 打开视频覆盖层播放对应文件。字幕组与女优 SHALL 出现在档案区。二次点击作品卡 MUST NOT 再走「无结构视频」的 Player[type] 打开逻辑。

#### Scenario: 选中不自动播

- **WHEN** 用户单击番剧网格中的作品
- **THEN** 信息栏出现该作品数据且覆盖层仍关闭
- **对应测试**：`tests.md` T5

#### Scenario: 选集播放

- **WHEN** 用户在信息栏点击某一集
- **THEN** 视频覆盖层可见并请求该集 file 的 content
- **对应测试**：`tests.md` T6

#### Scenario: 两种集列表

- **WHEN** 用户在有集封面的作品上切换封面/序号模式
- **THEN** 封面模式可见缩略图，序号模式展示第几集且不要求缩略图
- **对应测试**：`tests.md` T12

### Requirement: 特典分组与导航安全

信息栏 SHALL 将特典与正片集分开。从 `/anime` 或 `/av` 导航到其它路由时系统 SHALL 关闭覆盖层且 MUST NOT 抛出未定义 Player close。

#### Scenario: 特典分开展示

- **WHEN** 作品含 extras
- **THEN** 信息栏特典区可见且正片集数不含 extra 条数
- **对应测试**：`tests.md` T7

#### Scenario: 离页可导航

- **WHEN** 用户从番剧页点击侧栏视频
- **THEN** 主区变为视频页且无 close TypeError
- **对应测试**：`tests.md` T8

### Requirement: 向导类型文案

导入向导 SHALL 提供启用的番剧与 AV 类型；番剧对应 API `anime`。

#### Scenario: 向导可见番剧

- **WHEN** 用户打开导入类型步
- **THEN** 可见「番剧」与「AV」
- **对应测试**：`tests.md` T9
