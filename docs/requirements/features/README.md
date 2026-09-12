# L1 需求文档

需求沉淀维护的定稿需求。新能力用子目录 `features/<id>/需求.md`；文首含状态（草案 / 评审中 / 已定稿）。

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
