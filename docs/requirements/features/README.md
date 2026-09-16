# L1 需求文档

需求沉淀维护的定稿需求。新能力用子目录 `features/<id>/需求.md`；文首含状态（草案 / 评审中 / 已定稿）。

## anime-av-types（**评审中 / 规划待确认**）

> 动画番剧与 AV **作品级系列**（季/集树、特典、字幕组、女优多值、异构导入整理、集封面双展示）。菜单「番剧」。

| 文档 | 内容 |
|------|------|
| [`anime-av-types/需求.md`](anime-av-types/需求.md) | 范围、验收；§11 参考产品模型与能力对照 |
| [`anime-av-types/实现方案.md`](anime-av-types/实现方案.md) | 枚举/CHECK/映射/消费 |
| OpenSpec | `openspec/changes/anime-av-types/` |

## app-performance（**已定稿 / 实现中**）

> 全项目性能：DB / 导入 / HTTP / 万级显示 / 查看器 / 清脏库；API 保持可远程。

| 文档 | 内容 |
|------|------|
| [`app-performance/需求.md`](app-performance/需求.md) | 现状分析、验收、阶段 |
| [`app-performance/实现方案.md`](app-performance/实现方案.md) | S0–S5 文件清单 |
| OpenSpec | `openspec/changes/app-performance/` |

## image-consume-perf（**已并入 app-performance**）

> 看图跟手与缓存不再单独落地，见全项目方案 S5。

| 文档 | 内容 |
|------|------|
| [`image-consume-perf/需求.md`](image-consume-perf/需求.md) | 验收与开放问题（换库） |
| [`image-consume-perf/实现方案.md`](image-consume-perf/实现方案.md) | 封装 + 缓存文件清单 |
| OpenSpec | `openspec/changes/image-consume-perf/` |

## image-viewer-ux（**已定稿 / 实现中**）

> 查看器只盖中间网格；信息栏底部收纳；导航按钮上图。待确认。

| 文档 | 内容 |
|------|------|
| [`image-viewer-ux/需求.md`](image-viewer-ux/需求.md) | 占位与动作区 |
| [`image-viewer-ux/实现方案.md`](image-viewer-ux/实现方案.md) | Overlay 进 main + 封装性能 |
| OpenSpec | `openspec/changes/image-viewer-ux/` |

## image-consume（**已定稿 / 实现中**）

> 图片消费：二次点击打开左元数据+右完整查看器；打开所在位置；系统默认应用打开。待「可以按此实现」。

| 文档 | 内容 |
|------|------|
| [`image-consume/需求.md`](image-consume/需求.md) | 范围、故事、IPC 草案 |
| [`image-consume/实现方案.md`](image-consume/实现方案.md) | 覆盖层 + Viewer.js + shell IPC |
| OpenSpec | `openspec/changes/image-consume/` |

## library-trash（**已定稿 / 实现中**）

> 回收站页、多选批量移入/恢复/彻底删除（删库内包）。规划待「可以按此实现」。

| 文档 | 内容 |
|------|------|
| [`library-trash/需求.md`](library-trash/需求.md) | 范围、故事、验收、契约草案 |
| [`library-trash/实现方案.md`](library-trash/实现方案.md) | 沿用 library；文件清单 |
| OpenSpec | `openspec/changes/library-trash/` |

## grid-media-performance（**已定稿 / 实现中**）

> 导入时在包内生成网格缩略图；列表 `thumbnailPath`；窗口宽度节流。待 Electron 手工验 T6–T8。

| 文档 | 内容 |
|------|------|
| [`grid-media-performance/需求.md`](grid-media-performance/需求.md) | 范围、路径约定、验收 |
| [`grid-media-performance/实现方案.md`](grid-media-performance/实现方案.md) | ResourcePackage / 文件清单 |
| OpenSpec | `openspec/changes/grid-media-performance/` |

## metadata-panel-fields（**已定稿 / 实现中**）

> 描述、立刻待办、图/视频技术字段（含帧率码率画质）、导入 Pillow/ffprobe、多语言字幕。评审中，待「可以按此实现」。

| 文档 | 内容 |
|------|------|
| [`metadata-panel-fields/需求.md`](metadata-panel-fields/需求.md) | 范围与开放问题 |
| [`metadata-panel-fields/实现方案.md`](metadata-panel-fields/实现方案.md) | 包内 `subtitles/` 命名与文件清单 |
| OpenSpec | `openspec/changes/metadata-panel-fields/` |

## metadata-panel（**已定稿 / 已合入 master**）

> 右侧元数据面板：通用字段；独立词表；草稿点保存；编辑弹窗含换封面；删除确认。

| 文档 | 内容 |
|------|------|
| [`metadata-panel/需求.md`](metadata-panel/需求.md) | 范围、故事、验收、契约草案、开放问题 |
| [`metadata-panel/实现方案.md`](metadata-panel/实现方案.md) | 沿用 InfoPanel + library；文件清单 |
| OpenSpec | `openspec/changes/metadata-panel/` |

## import-directory-scan（**已定稿 / 已归档**）

> 导入：分步向导、一次选择文件或目录、**复制**进库。**已落地 master**。

| 文档 | 内容 |
|------|------|
| [`import-directory-scan/需求.md`](import-directory-scan/需求.md) | 本轮范围、故事、验收、契约草案 |
| [`import-directory-scan/实现方案.md`](import-directory-scan/实现方案.md) | 路径清单与数据流 |
| OpenSpec | 已归档 `openspec/changes/archive/2026-09-12-import-directory-scan/` |

## local-resource-manager（**已定稿**）

| 文档 | 内容 |
|------|------|
| `local-resource-manager.md` | 主需求：背景/范围/决策/开放问题 |
| `lrm-modules.md` | 模块拆解（M0–M6）与边界异常 |
| `lrm-ui.md` | 页面结构（三栏布局） |
| `lrm-tech-stack.md` | 技术栈决策（三进程架构、双服务、双引擎） |

## tag-category-hygiene（**草案**）

> LRM **P1 增量**：标签/分类词表统计与删除。依赖 M4 打标能力；实现排在 MS4.1，不挡当前浏览闭环。

| 文档 | 内容 |
|------|------|
| `tag-category-hygiene.md` | 词表膨胀治理：统计、删除、与 M4 边界、开放问题 |

## work-consumption-hub（**草案**）

> LRM 增量 Feature：工作上下文 + 消费渠道。依赖 LRM M0–M6。

| 文档 | 内容 |
|------|------|
| `work-consumption-hub.md` | 主需求：定位变更、核心概念、范围、开放问题 |
| `wch-modules.md` | 增量模块拆解（M7–M10）与 API 草案 |
| `wch-ui.md` | UI 增量：工作区面板、首页概览、消费渠道设置 |
