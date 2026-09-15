# 提案 · anime-av-types

> 与 `docs/requirements/features/anime-av-types/需求.md` 同范围。

## Why

番剧/AV 的使用单位是「一部作品」，播放单位是「一集/一条特典」。沿用单文件 Resource 做网格会让信息栏无法展示集树，也会把特典和正片混成同一张卡。菜单已有占位但契约仍是图/视频。

## What Changes

- 作品级 `resources.type`：`anime`、`av`（菜单「番剧」）。旧 `video` 行不迁移。
- 专属 `anime_profiles` / `av_profiles` + `seasons` / `episodes` / `extras`。
- 网格一张作品封面；信息栏季/集/特典；选集或特典播放（复用视频 overlay）。
- 导入以 **一目录一部作品** 解析 Season / SxxExx / extras|特典|Specials。
- **BREAKING：** 前端占位 `/anime-series` 改为 `/anime`；列表 type 不再用 `anime-series`。

不交付：刮削、旧视频改类型、合集模块、新播放器、Proactor 10054。

## Capabilities

### New Capabilities

- `library-series-tree`：作品 Resource + 季/集/特典/profile 持久化与详情
- `desktop-series-browse`：番剧/AV 页、作品卡、信息栏选集播放与特典分组

### Modified Capabilities

- `library-ingest`：`anime`/`av` 目录导入走系列收纳，不是一文件一资源
- `desktop-import-entry`：向导类型「番剧」「AV」；成功后作品网格刷新

## Impact

- API：详情 DTO 扩展；content 按 file id 播集
- 表：新子表 + CHECK
- 前端：路由、InfoPanel 系列态、安全 close
- 磁盘：`{store}/anime/{id}/seasons/…`

## 开放问题

见需求 §9（profile 字段清单、散文件导入、OVA 归季还是 extras）。
