## Purpose

系列入库把异构来源收成规范包，并允许在作品内增删集、按季集号批量规范命名。导入预览可改映射，避免静默乱入。

## ADDED Requirements

### Requirement: 异构目录须预览再入库

系统 SHALL 对 `anime`/`av` 导入先返回布局探测与文件映射预览。用户确认后 MUST 将媒体 copy 为规范路径 `seasons/NN/SxxExx`（特典进 extras）。无法识别的布局 MUST NOT 自动建集。字幕组从文件名解析时 SHALL 写入作品默认或集覆盖字段。

#### Scenario: 字幕组扁平包预览

- **WHEN** 目录仅含 `[Fansub] Show - 01.mkv` 与 `02.mkv` 且用户请求 anime 预览
- **THEN** 映射为 S01E01/E02，fansub 为 Fansub，尚未创建 resource
- **对应测试**：`tests.md` T10

### Requirement: 系列内增删

系统 SHALL 允许向已有作品追加视频（指定季集或 extras）以及删除单集/特典。删除 MUST 去掉对应 files 与包内文件（含配套字幕与集封面），MUST NOT 删除整部作品 Resource。

#### Scenario: 删掉误导入的一集

- **WHEN** 用户 DELETE 某 episode
- **THEN** 该集不再出现在详情中，作品仍可 GET
- **对应测试**：`tests.md` T11

### Requirement: 规范命名

系统 SHALL 提供按当前季集号把包内正片、集封面、外挂字幕重命名为 `SxxExx` 同名族的操作。重命名 MUST 同时更新 files 路径。

#### Scenario: 批量规范名

- **WHEN** 包内仍为原始下载文件名且季集号已在表中
- **THEN** 调用规范命名后磁盘与 files.path 为 SxxExx
- **对应测试**：`tests.md` T10
