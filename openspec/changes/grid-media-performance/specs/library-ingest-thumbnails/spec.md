## Purpose

导入时在资源包内生成网格用缩略图并登记为文件角色，使列表能提供独立于原封面的小图地址。换封面时覆盖同一文件，生成失败不得导致导入失败。

## ADDED Requirements

### Requirement: 导入时写入包内网格缩略图

系统 SHALL 在成功复制主文件并完成探测之后，为可得到源图的资源生成一档网格缩略图，写入该资源包目录下的 `thumbs/grid.webp`，并登记 `files.role` 为 `thumbnail`。源图优先已有封面角色，否则仅当资源类型为图片时使用主文件。无可用源图时 SHALL 不创建空缩略图文件。生成失败时 SHALL 仍提交已复制的资源。缩略图路径 SHALL 仅由资源包拼接，不得写到库根下的全局缓存目录。

#### Scenario: 导入图片成功落盘

- **WHEN** 用户导入一张可被解码的图片
- **THEN** 磁盘存在 `{library}/{type}/{id}/thumbs/grid.webp`，且该资源有一条 `role=thumbnail` 的文件记录
- **对应测试**：`tests.md` T1

#### Scenario: 无封面视频不造空文件

- **WHEN** 用户导入一条没有封面角色的视频
- **THEN** 导入成功，包内没有 `thumbs/grid.webp`，也没有 thumbnail 文件行
- **对应测试**：`tests.md` T2

#### Scenario: 生成失败不挡导入

- **WHEN** 缩略图生成抛错（无法解码等）
- **THEN** 资源记录与主文件仍提交成功，且不留下损坏的 `grid.webp`
- **对应测试**：`tests.md` T3

### Requirement: 列表提供缩略图地址且不改原封面语义

系统 SHALL 在资源列表与详情 JSON 中提供可选 `thumbnailPath`，指向 thumbnail 文件的已有 content URL。`coverPath` SHALL 继续指向原封面或主文件内容，不得改为 `thumbs/grid.webp`。

#### Scenario: 字段分离

- **WHEN** 客户端 GET 一条刚导入且已有缩略图的图片资源
- **THEN** `thumbnailPath` 含 `/files/{thumbId}/content`，`coverPath` 不含 `thumbs/grid`
- **对应测试**：`tests.md` T4

### Requirement: 换封面覆盖同一缩略图

系统 SHALL 在用户更换封面成功后，用新封面覆盖写入 `thumbs/grid.webp`（同一相对路径），而不是新增另一档网格文件名。

#### Scenario: 换封面后路径不变内容更新

- **WHEN** 对已有缩略图的资源 POST 新封面
- **THEN** thumbnail 文件仍落在 `thumbs/grid.webp`，内容与新封面相关
- **对应测试**：`tests.md` T5
