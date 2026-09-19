# L1 需求文档

需求沉淀维护的定稿需求。新能力用子目录 `features/<id>/需求.md`；文首含状态（草案 / 评审中 / 已定稿）。

## image-viewer-cross-page（**已落地** · D-20260919-08）

> 图片查看器上一张/下一张越过当前已加载页。不环绕、不拉全库。待 Electron 手验。

| 文档 | 内容 |
|------|------|
| [`image-viewer-cross-page/需求.md`](image-viewer-cross-page/需求.md) | IN/OUT |
| [`image-viewer-cross-page/设计.md`](image-viewer-cross-page/设计.md) | playlist 与 loadMore 同源 |
| [`image-viewer-cross-page/实现方案.md`](image-viewer-cross-page/实现方案.md) | bindPager、预拉、文件清单 |

## library-covers-complete（**已落地** · D-20260919-07）

> 九种库类型封面策略收口。PDF/EPUB/cbz/同名贴图本刀；cbr 不抽页；不刮削、不回填。禁止编码。

| 文档 | 内容 |
|------|------|
| [`library-covers-complete/需求.md`](library-covers-complete/需求.md) | IN/OUT、已关开放问题 |
| [`library-covers-complete/设计.md`](library-covers-complete/设计.md) | 选源顺序、origin、模块 |
| [`library-covers-complete/实现方案.md`](library-covers-complete/实现方案.md) | sidecar/EPUB/PDF/cbz、文件清单 |

## series-import-explain（**已落地** · D-20260919-06）

> 番剧/AV 导入只读说明：为何失败、成功分成几集。不改映射。禁止编码。

| 文档 | 内容 |
|------|------|
| [`series-import-explain/需求.md`](series-import-explain/需求.md) | IN/OUT |
| [`series-import-explain/设计.md`](series-import-explain/设计.md) | explain code、job.message |
| [`series-import-explain/实现方案.md`](series-import-explain/实现方案.md) | 文件清单 |
| OpenSpec | 尚未建 |

## audio-embedded-cover（**已落地**）

> 音频新导入抽内嵌专辑图。EPUB 仍 OUT。

| 文档 | 内容 |
|------|------|
| [`audio-embedded-cover/需求.md`](audio-embedded-cover/需求.md) | IN/OUT |
| [`audio-embedded-cover/设计.md`](audio-embedded-cover/设计.md) | ffmpeg 附加图、origin=embedded |
| [`audio-embedded-cover/实现方案.md`](audio-embedded-cover/实现方案.md) | 文件清单 |

## library-covers（**已落地 / 视频抽帧已手验**）

> 封面治理。D-20260919-03。音频内嵌图见 `audio-embedded-cover`。

| 文档 | 内容 |
|------|------|
| [`library-covers/需求.md`](library-covers/需求.md) | IN/OUT |
| [`library-covers/设计.md`](library-covers/设计.md) | L2 |
| [`library-covers/实现方案.md`](library-covers/实现方案.md) | 抽帧/pefile/lnk、文件清单 |
| OpenSpec | `openspec/changes/library-covers/` |

## image-exif-taken（**已落地**）

> 图片深化第一刀（D1）：新导入写入 EXIF 拍摄时间并在信息栏展示。不做旧库回填。禁止编码。

| 文档 | 内容 |
|------|------|
| [`image-exif-taken/需求.md`](image-exif-taken/需求.md) | IN/OUT、故事 |
| [`image-exif-taken/设计.md`](image-exif-taken/设计.md) | 探测优先级、存储格式、模块 |
| OpenSpec | 尚未建（等 L3） |

## image-library-depth（**草案 / 探索**）

> 图片在最低消费之后还能加深什么、还能加什么。第一刀已拆 `image-exif-taken`。禁止把剩余表整包实现。

| 文档 | 内容 |
|------|------|
| [`image-library-depth/需求.md`](image-library-depth/需求.md) | 现状缺口、债（D1–D6）、候选（N1–N22）、开放问题 |
| [`image-library-depth/handoff.md`](image-library-depth/handoff.md) | D1 已拆出 |

## library-search-sort（**实现中 / 待 Electron 手工验**）

> 库内共用与分类型搜索、排序。未授权实现。

| 文档 | 内容 |
|------|------|
| [`library-search-sort/需求.md`](library-search-sort/需求.md) | IN/OUT、故事、开放问题 |
| [`library-search-sort/实现方案.md`](library-search-sort/实现方案.md) | LIKE、API、keyset、文件清单 |
| OpenSpec | `openspec/changes/library-search-sort/` |

## ui-theme-shell（**实现中 / 已合入 master**）

> 壳层模块化、CSS 主题加载、批量条位置、信息栏分区。已合入 master。

| 文档 | 内容 |
|------|------|
| [`ui-theme-shell/需求.md`](ui-theme-shell/需求.md) | IN/OUT、故事、开放问题 |
| OpenSpec | `openspec/changes/ui-theme-shell/` |

## library-type-platform（**已合入 master**）

> 所有库类型最低导入与展示；领域 TypeProfile；游戏默认扫描登记；漫画/小说本刀无阅读器；类型页 TypeBrowse。

| 文档 | 内容 |
|------|------|
| [`library-type-platform/需求.md`](library-type-platform/需求.md) | 模型分层、IN/OUT、开放问题 |
| [`library-type-platform/实现方案.md`](library-type-platform/实现方案.md) | TypeProfile、文件清单 |
| OpenSpec | `openspec/changes/library-type-platform/` |

## anime-av-types（**第一刀已合入 master；第二刀未做**）

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
