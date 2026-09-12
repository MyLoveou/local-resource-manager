# 提案 · image-consume

> 与 `docs/requirements/features/image-consume/需求.md` 同范围。

## Why

图片无法认真看原图，也不能从应用打开文件夹或系统默认看图程序。看图时改描述/待办会打断。M2 消费缺口，且与「单击只选中」可以并存。

## What Changes

- 已选中图片再点同一张（及双击、点信息栏封面）打开覆盖层：左元数据、右完整查看器。
- 查看器：缩放、平移、旋转、适应/1:1、全屏、已加载列表相邻张。
- 主进程 IPC：资源管理器定位；默认应用打开；选择其他应用。
- 批量删除模式不打开查看器。

**BREAKING：** 无。

明确不交付：视频播放、画廊模块、应用内软件目录、记忆上次 exe、像素编辑、导入源路径。

## Capabilities

### New Capabilities

- `desktop-image-viewer`：覆盖层查看器 + 与选中/批量模式的打开规则
- `desktop-shell-open`：showItemInFolder / openPath / openWith

### Modified Capabilities

- （无主 spec 增量。）

## Impact

- API：无新 REST；用已有文件流与详情 `files.path`
- 前端：覆盖层组件、ResourceBrowser 二次点击、InfoPanel 按钮
- Electron：preload + main `shell`
- 依赖：Viewer.js（假设，可换）
- 表：无
