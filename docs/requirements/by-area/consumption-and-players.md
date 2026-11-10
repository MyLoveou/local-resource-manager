# 消费与播放器 · 跨类型需求

> “打开资源”是命令，不是数据失效广播。页面只提供资源 + 播放上下文，统一入口负责分发。

## 1. 已实现

- `openResource(item, { playlist, fileId, pager })`：
  - 解析 consume channel（embedded / system / command / workbench）；
  - 图片查看器、视频/音频播放器、模型预览、系列选集、系统打开；
  - playlist、视频分集 `fileId`、图片/音频 pager；
  - 错误提示与回退。
- 图片查看器支持跨页、上一张/下一张、翻页加载。
- 视频/音频播放器、模型 gltf/glb 预览。
- 番剧/AV 系列按季/集播放。
- 资源库、合集详情、首页、时间线、信息面板均调用同一入口。
- 合集详情：首次点击选中，再次点击打开；播放列表使用合集当前筛选结果。

## 2. 部分实现 / 缺口

| 能力 | 状态 | 说明 |
|------|------|------|
| 播放进度记忆 | 未实现 | 视频/音频在重启后从头开始 |
| 自动下一集/连续播放 | 未实现 | 有系列选集，但没有自动续播策略 |
| 自定义播放器参数 | 部分 | 命令模板可用；类型专属参数 UI 未做 |
| 字幕自动匹配 | 未实现 | 手动添加外挂字幕 |
| 幻灯片/画廊连看 | 未实现 | 候选 N1/N15 |
| 快捷键全局化 | 部分 | 查看器内有导航；跨页面统一快捷键未收口 |

## 3. 明确边界

- 打开动作不能复用 `library.invalidate`；否则会因任何数据变更误开播放器。
- 单机游戏默认只启动，不复制/安装。
- 系统打开失败要有提示，不能静默。

## 4. 入口

- `apps/desktop/src/renderer/src/infrastructure/consume/consumeResource.ts`
- `apps/desktop/src/renderer/src/infrastructure/consume/players.ts`
- `apps/desktop/src/renderer/src/components/ImageViewerOverlay`
- `apps/desktop/src/renderer/src/components/VideoPlayerOverlay`
- `apps/desktop/src/renderer/src/components/AudioPlayerOverlay`
- `features/image-viewer-ux/`、`features/image-consume/`、`features/work-consumption-hub/`
