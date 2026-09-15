## Purpose

库把番剧与 AV 存成作品级资源，其下有季、正片集和特典文件。列表与回收站只出现作品。详情返回可点选播放的集与特典，且正片集数不含花絮。这样信息栏可以展示专用档案字段和集树，而不把每一集当成独立库条目。

## ADDED Requirements

### Requirement: 作品是列表单位

系统 SHALL 将 `anime` 与 `av` 作为作品级 `ResourceType`。按这两种 type 列出资源时 MUST 只返回作品行。单集与特典 MUST NOT 成为 `resources` 列表项。已有 `image`/`video` 行 MUST 保持原 type。

#### Scenario: 空作品列表

- **WHEN** `GET /library/resources?type=anime` 且无番剧作品
- **THEN** HTTP 200 且 items 为空
- **对应测试**：`tests.md` T1

#### Scenario: 旧视频不变

- **WHEN** 迁移在含 video 行的库上执行
- **THEN** 这些行 type 仍为 video
- **对应测试**：`tests.md` T2

### Requirement: 季集特典树

系统 SHALL 为每个作品持久化 seasons、episodes、extras，并在作品详情中返回。正片集数 SHALL 等于 episodes 数量，MUST NOT 计入 extras。Episode 与 extra MUST 关联库内 files 行以便 content 播放。

#### Scenario: 详情含树

- **WHEN** 一部含两集与一条特典的作品被 GET
- **THEN** 详情含两 episode、一 extra，正片集数字段为 2
- **对应测试**：`tests.md` T3

### Requirement: 目录导入成一部作品

系统 SHALL 把 `type=anime` 或 `av` 且 `sourceKind=directory` 的导入收成 **一个** 作品包。匹配 Season 目录与 SxxExx 的视频进入 episodes；名为 extras/特典/Specials/Season 00 的附属视频进入 extras 或 season 0（按需求约定）。未知未启用 type 仍 HTTP 400。

#### Scenario: 一文件夹一张卡

- **WHEN** 导入含 Season 01 下两集 mkv 的目录为 anime
- **THEN** 仅新增 1 条 type=anime 的 resource，且 video 列表不含这两集为独立项
- **对应测试**：`tests.md` T4
