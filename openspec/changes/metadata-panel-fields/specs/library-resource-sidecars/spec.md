## Purpose

本能力补齐资源详情的描述、待办、作者、文件技术字段，并在导入时探测媒体；视频字幕按导入原始文件名改名入库（多语言）。不包含抓取与播放器内渲染字幕。

## ADDED Requirements

### Requirement: 详情含描述格式作者待办与媒体列

系统 SHALL 在资源详情中提供 description、author、主文件 format，以及待办列表。视频主文件 SHALL 可包含 duration、width、height、fps、bitrate、codec。缺失 MUST 可空。待办增删改勾选 SHALL 立即持久化。

#### Scenario: 详情带新字段

- **WHEN** 客户端 GET 已存在资源
- **THEN** 响应含 description、author、files 的 format/fps/bitrate/codec、todos
- **对应测试**：`tests.md` T1

#### Scenario: 待办立刻写入

- **WHEN** 客户端 POST 一条待办后再次 GET
- **THEN** 列表含该待办，无需先 PATCH 资源
- **对应测试**：`tests.md` T8

### Requirement: 导入时探测媒体

系统 SHALL 在复制入库后探测主文件：图片用 Pillow 写入 width/height；视频调用 ffprobe 写入 width/height/duration/fps/bitrate/codec。探测失败或找不到 ffprobe MUST NOT 使整次导入失败。系统 MUST NOT 在 GET 详情时探测。本切片 MUST NOT 回填导入前已存在的资源。

#### Scenario: 导入图片有分辨率

- **WHEN** 导入一张可被 Pillow 打开的图
- **THEN** 该资源 primary 的 width 与 height 非空
- **对应测试**：`tests.md` T11

#### Scenario: 无 ffprobe 仍导入视频

- **WHEN** ffprobe 不可用时导入视频
- **THEN** 资源仍创建成功，媒体列可空
- **对应测试**：`tests.md` T12

### Requirement: 字幕复制并按原始视频名加语言后缀

系统 SHALL 仅对视频接受本机字幕路径，复制到 `subtitles/`。目标名 MUST 为导入源视频 stem（路径安全清洗）加可选语言白名单后缀与原扩展名。源文件 MUST 保留。非法类型或扩展名 SHALL 400。同目标名替换；不同语言并存。

#### Scenario: 添加带语言的 srt

- **WHEN** importSourcePath 为 `.../电影.mkv` 且 POST `foo.zh.srt`
- **THEN** 存在 `subtitles/电影.zh.srt`
- **对应测试**：`tests.md` T2

#### Scenario: 第二条不同语言并存

- **WHEN** 同一资源再 POST `bar.en.srt`
- **THEN** 两个字幕文件均存在
- **对应测试**：`tests.md` T9

#### Scenario: 图片拒绝字幕

- **WHEN** 对图片 POST subtitles
- **THEN** 400
- **对应测试**：`tests.md` T3
