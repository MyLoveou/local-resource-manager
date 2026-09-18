## Purpose

最低消费按 consumeKind：音频用 Howler 内置播；模型内置 3D 预览；游戏/小说/漫画系统打开。内置小说阅读器与漫画阅读器不在本切片。渲染进程不复制库文件。

## ADDED Requirements

### Requirement: 最低消费

系统 SHALL 用档案 consumeKind 打开。audio → overlay-audio（howler.js）。model → overlay-model（model-viewer）。novel/game/comic → shell-open（launch 优先否则 primary）。indexed 资源 MUST 打开 `files.path` 源路径。离页关闭对应 overlay。

#### Scenario: 音频二次点击播放

- **WHEN** 音频页对已选中卡再点
- **THEN** Howler 驱动的音频 overlay 打开，不是视频播放器
- **对应测试**：`tests.md` T8

#### Scenario: 小说或漫画系统打开

- **WHEN** 触发小说或漫画打开
- **THEN** 主进程 openPath（库内 primary），不是内置阅读器
- **对应测试**：`tests.md` T9

#### Scenario: 模型内置预览

- **WHEN** 对已导入 gltf/glb 模型二次点击
- **THEN** 内置预览 overlay 显示模型
- **对应测试**：`tests.md` T12

#### Scenario: 离页关闭

- **WHEN** 音频页转到图片页
- **THEN** overlay 关闭且无 TypeError
- **对应测试**：`tests.md` T10
