## Purpose

按档案 ingestKind / storageKind 把音频、小说、游戏、模型、漫画写入作品级 Resource。媒体默认复制进库；游戏默认扫描登记源路径。不把源目录登记为可再扫的库根。

## ADDED Requirements

### Requirement: 新类型入库

系统 SHALL 支持 `audio`、`novel`、`game`、`model`、`comic` 入库。file：一文件一资源（owned）。package：一目录一条资源。游戏缺省 storageKind=indexed（files.path 为源盘路径，不 copytree）；显式 owned 时复制到 `{library}/game/{id}/`。漫画 owned 复制页文件。去重与软删与现网一致；indexed 彻底删除 MUST NOT 删除源盘文件。

#### Scenario: 音频文件导入

- **WHEN** 以 audio 导入一个受支持音频文件
- **THEN** 1 条 `type=audio` `storageKind=owned`，不出现在 video 列表
- **对应测试**：`tests.md` T3

#### Scenario: 游戏目录默认登记

- **WHEN** 以 game 导入含启动文件的目录且未指定复制
- **THEN** 仅 1 条 `type=game` `storageKind=indexed`；库目录下无该游戏整树副本；launch path 指向源盘
- **对应测试**：`tests.md` T4

#### Scenario: 游戏彻底删除不删源

- **WHEN** 删除一条 indexed 游戏并彻底删除
- **THEN** 库记录消失，源目录与 exe 仍在
- **对应测试**：`tests.md` T4b

#### Scenario: 漫画目录一作

- **WHEN** 以 comic 导入仅含多张图片的目录
- **THEN** 仅 1 条 `type=comic`，多 files；consume 为系统打开而非内置翻页
- **对应测试**：`tests.md` T11

#### Scenario: 重复哈希跳过

- **WHEN** 同一音频再导入
- **THEN** imported 不增加
- **对应测试**：`tests.md` T5
