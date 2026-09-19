## Purpose

作品级封面：导入自动源与用户指定，网格只显示包内缩略图。

## ADDED Requirements

### Requirement: 非图片可更换封面

系统 SHALL 允许除图片外的资源将本机图片复制为包内 cover 并刷新网格缩略图。图片 MUST 拒绝更换封面。

#### Scenario: 视频更换封面

- **WHEN** 用户为视频选择一张本机图片并提交封面
- **THEN** 该资源出现新的 cover 与 thumbnail，且 `coverOrigin` 为 user

#### Scenario: 图片拒绝

- **WHEN** 客户端对图片资源请求更换封面
- **THEN** 系统返回 422

### Requirement: 手指定锁定

系统 SHALL 在用户指定封面后拒绝自动封面覆盖该资源。

#### Scenario: 锁定

- **WHEN** 资源 `coverOrigin` 已为 user 且再次执行导入自动封面逻辑
- **THEN** 包内封面文件内容不变

### Requirement: 新导入自动封面

系统 SHALL 在新导入时按类型尝试自动封面：目录海报；视频或系列第一集抽一帧；游戏 exe 或 lnk 目标 exe 图标。失败 MUST 不阻止导入。系统 MUST NOT 批量回填旧资源。

#### Scenario: 无 ffmpeg

- **WHEN** 导入无海报视频且本机没有 ffmpeg
- **THEN** 导入成功且可以没有缩略图

#### Scenario: 游戏海报优先

- **WHEN** 游戏目录同时存在 poster 图片与 exe
- **THEN** 封面来自海报而非 exe 图标
