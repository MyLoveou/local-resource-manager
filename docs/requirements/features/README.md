# L1 需求文档

> 按资源类型/跨类型能力的需求视图见 [`../README.md`](../README.md)；本目录保留每个能力的详细 L1/L2/L3。

需求沉淀维护的定稿需求。新能力用子目录 `features/<id>/需求.md`；文首含状态（草案 / 评审中 / 已定稿）。

## video-management（**L1 评审中** · 2026-10-25 · D-20261025-01）

> 图片库阶段手验通过后的下一阶段。播放进度与续播（S1）→ 播放器体验与字幕（S2）→ 视频专属维度与刮削（S3）。

| 文档 | 内容 |
|------|------|
| [`video-management/需求.md`](video-management/需求.md) | 现状与缺口、5 块 IN/OUT、切片顺序、V1–V14 验收、Q1–Q5 开放问题 |

## photo-management-next（**R1 已落地 · R2–R4 需求收集** · 2026-10-18）

> R1 批量加入合集已实现；多时间线（旅游/漫展）、角色维度（角色/作品/扮演者）、本地人脸识别与模型管理待设计。

| 文档 | 内容 |
|------|------|
| [`photo-management-next/需求.md`](photo-management-next/需求.md) | R1–R4、候选方案、验收与开放问题；R1 实现记录 |

## timeline-annotations（**v1 已实现 · 2026-10-20**）

> 时间线某天/某条时间线的备注与手动地点名；日期备注全局一条、保存时间线备注一条；不改 EXIF。地图由 `photo-timeline-map` 的地图视图承接。

| 文档 | 内容 |
|------|------|
| [`timeline-annotations/需求.md`](timeline-annotations/需求.md) | 日期备注/时间线备注/地点 IN-OUT、US-A.1–A.7、v1 实现记录 |

## library-workspace（**已落地 · 待发版手验** · 2026-10-19）

> 资源底层 + 每类型分类树 + 资源库/视图导航 + 首页工作台；含合集 D 卡与批量快捷键。

| 文档 | 内容 |
|------|------|
| [`library-workspace/需求.md`](library-workspace/需求.md) | 已确认决策、W1–W7 验收、IN/OUT |
| [`library-workspace/设计.md`](library-workspace/设计.md) | L2：模型/交互/模块/切片/开放问题 |
| [`library-workspace/实现方案.md`](library-workspace/实现方案.md) | L3：路径/契约/数据流/纵向步骤 |
| [`library-workspace/handoff.md`](library-workspace/handoff.md) | 已落地；发版手验/提交待办 |

## platform-debt（**已定稿 · 已落地** · D-20260927-06）

> D1 Notify 迁移、D2 token 校验、D3 导入进度分相、D4 事件循环**四项均已落地**（2026-09-27）。余 Electron 手验（媒体豁免生效 + 导入大目录时 `/health` 可用）。

| 文档 | 内容 |
|------|------|
| [`platform-debt/需求.md`](platform-debt/需求.md) | 四项债的 IN/OUT、可测验收 A1–A6 / B1–B3 |
| [`platform-debt/设计.md`](platform-debt/设计.md) | token 中间件与豁免取舍、事件循环判定规则、切片契约 |
| [`platform-debt/实现方案.md`](platform-debt/实现方案.md) | L3：文件清单、纵向步骤、阻塞点核对表 |

## theme-tokens（**已定稿** · 来自 D-20260927-04）

> 主题令牌补齐：状态色/交互态/背景层次/圆角，并清零组件内硬编码颜色。第一刀不做字号/阴影。

| 文档 | 内容 |
|------|------|
| [`theme-tokens/需求.md`](theme-tokens/需求.md) | IN/OUT、T1–T6 验收、Q1–Q4 已确认 |

## quality-and-deploy（**已定稿 · 边界结论** · D-20260927-04）

> 只保留拆分与边界：S3 已拆为 `theme-tokens`；S4 Docker/远程后端**冻结**；S1/S2 退回观察；S5–S7 保持 OUT。本文件不再作为可实施需求。

| 文档 | 内容 |
|------|------|
| [`quality-and-deploy/需求.md`](quality-and-deploy/需求.md) | 七条拆分（S1–S7）与逐条定论 §7 |
| [`quality-and-deploy/handoff.md`](quality-and-deploy/handoff.md) | 轮次 2 结论 |

## library-collections（**已定稿** · 需求 + L2 设计 · D-20260927-03）

> 用户自建一组资源。不是系列。需求与 L2 设计均已定稿，待 L3 后才可编码。分支 `feat/library-collections`。

| 文档 | 内容 |
|------|------|
| [`library-collections/需求.md`](library-collections/需求.md) | IN/OUT、C1–C8、轮次 2 决策清单 |
| [`library-collections/设计.md`](library-collections/设计.md) | 两张表、与系列的边界（L2 已定稿） |
| [`library-collections/handoff.md`](library-collections/handoff.md) | 下一步 L3 |

## app-settings-first（**已落地** · D-20260923-04）

> 设置第一刀：刮削凭证 + 系统路径/备份。无扫描根。

| 文档 | 内容 |
|------|------|
| [`app-settings-first/需求.md`](app-settings-first/需求.md) | IN/OUT、US-Z.1–5 |
| [`app-settings-first/设计.md`](app-settings-first/设计.md) | KV、掩码、两页签 |
| [`app-settings-first/实现方案.md`](app-settings-first/实现方案.md) | REST、文件清单 |
| [`app-settings-first/handoff.md`](app-settings-first/handoff.md) | 待 apply |

> 自建下载功能（download-http-ingest / download-magnet-aria2）已随方向调整移除（D-20261007-01：下载委托第三方成熟下载器，产物经监视目录入库）。

## scrape-confirm-ux（**已落地** · 待手验）

> 确认元数据分栏；按字段勾选覆盖。

| 文档 | 内容 |
|------|------|
| [`scrape-confirm-ux/界面方向.md`](scrape-confirm-ux/界面方向.md) | 视觉 |
| [`scrape-confirm-ux/需求.md`](scrape-confirm-ux/需求.md) | IN/OUT |
| [`scrape-confirm-ux/设计.md`](scrape-confirm-ux/设计.md) | 字段开关 |

## bilibili-scrape（**已落地** · D-20260922-03）

> 视频附加 B 站公开稿件；信息栏可手填 BV。不登录、不下载。待 Electron 手验。

| 文档 | 内容 |
|------|------|
| [`bilibili-scrape/需求.md`](bilibili-scrape/需求.md) | IN/OUT、US-B.6 手填 BV |
| [`bilibili-scrape/设计.md`](bilibili-scrape/设计.md) | query 列、force 新 job |
| [`bilibili-scrape/实现方案.md`](bilibili-scrape/实现方案.md) | 路径清单、契约 |
| [`bilibili-scrape/handoff.md`](bilibili-scrape/handoff.md) | 已编码，待手验 |

## metadata-scrape（**已落地** · D-20260919-10）

> 视频/番剧直连 TMDB+Bangumi；确认后覆盖标题简介；批量确认；导入预搜不写库。

| 文档 | 内容 |
|------|------|
| [`metadata-scrape/需求.md`](metadata-scrape/需求.md) | IN/OUT、已关开放问题 |
| [`metadata-scrape/设计.md`](metadata-scrape/设计.md) | Provider、job、导入入队、批量 |
| [`metadata-scrape/实现方案.md`](metadata-scrape/实现方案.md) | REST、worker、文件清单 |

## image-viewer-cross-page（**已落地** · D-20260919-08）

> 图片查看器上一张/下一张越过当前已加载页。不环绕、不拉全库。待 Electron 手验。

| 文档 | 内容 |
|------|------|
| [`image-viewer-cross-page/需求.md`](image-viewer-cross-page/需求.md) | IN/OUT |
| [`image-viewer-cross-page/设计.md`](image-viewer-cross-page/设计.md) | playlist 与 loadMore 同源 |
| [`image-viewer-cross-page/实现方案.md`](image-viewer-cross-page/实现方案.md) | bindPager、预拉、文件清单 |

## library-covers-complete（**已落地** · D-20260919-07）

> 九种库类型封面策略收口。PDF/EPUB/cbz/同名贴图本刀；cbr 不抽页；不刮削、不回填。

| 文档 | 内容 |
|------|------|
| [`library-covers-complete/需求.md`](library-covers-complete/需求.md) | IN/OUT、已关开放问题 |
| [`library-covers-complete/设计.md`](library-covers-complete/设计.md) | 选源顺序、origin、模块 |
| [`library-covers-complete/实现方案.md`](library-covers-complete/实现方案.md) | sidecar/EPUB/PDF/cbz、文件清单 |

## series-import-explain（**已落地** · D-20260919-06）

> 番剧/AV 导入只读说明：为何失败、成功分成几集。不改映射。

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

> 图片深化第一刀（D1）：新导入写入 EXIF 拍摄时间并在信息栏展示。不做旧库回填。

| 文档 | 内容 |
|------|------|
| [`image-exif-taken/需求.md`](image-exif-taken/需求.md) | IN/OUT、故事 |
| [`image-exif-taken/设计.md`](image-exif-taken/设计.md) | 探测优先级、存储格式、模块 |
| OpenSpec | 未建独立 change（能力已落地） |

## image-library-depth（**草案 / 探索**）

> 图片在最低消费之后还能加深什么、还能加什么。第一刀已拆 `image-exif-taken`。禁止把剩余表整包实现。

| 文档 | 内容 |
|------|------|
| [`image-library-depth/需求.md`](image-library-depth/需求.md) | 现状缺口、债（D1–D6）、候选（N1–N22）、开放问题 |
| [`image-library-depth/handoff.md`](image-library-depth/handoff.md) | D1 已拆出 |

## library-search-sort（**已落地 / 待 Electron 手工验**）

> 库内共用与分类型搜索、排序。代码与后端测试已在。

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

## app-performance（**已定稿 / 已归档**）

> 全项目性能：DB / 导入 / HTTP / 万级显示 / 查看器 / 清脏库；API 保持可远程。

| 文档 | 内容 |
|------|------|
| [`app-performance/需求.md`](app-performance/需求.md) | 现状分析、验收、阶段 |
| [`app-performance/实现方案.md`](app-performance/实现方案.md) | S0–S5 文件清单 |
| OpenSpec | 已归档 `openspec/changes/archive/2026-09-23-app-performance/` |

## image-consume-perf（**已并入 app-performance**）

> 看图跟手与缓存不再单独落地，见全项目方案 S5。

| 文档 | 内容 |
|------|------|
| [`image-consume-perf/需求.md`](image-consume-perf/需求.md) | 验收与开放问题（换库） |
| [`image-consume-perf/实现方案.md`](image-consume-perf/实现方案.md) | 封装 + 缓存文件清单 |
| OpenSpec | `openspec/changes/image-consume-perf/` |

## image-viewer-ux（**已定稿 / 已归档**）

> 查看器只盖中间网格；信息栏底部收纳；导航按钮上图。

| 文档 | 内容 |
|------|------|
| [`image-viewer-ux/需求.md`](image-viewer-ux/需求.md) | 占位与动作区 |
| [`image-viewer-ux/实现方案.md`](image-viewer-ux/实现方案.md) | Overlay 进 main + 封装性能 |
| OpenSpec | 已归档 `openspec/changes/archive/2026-09-23-image-viewer-ux/` |
| `fix-image-consume-ui` | 已归档 `openspec/changes/archive/2026-09-23-fix-image-consume-ui/`（无独立需求目录） |

## image-consume（**已定稿 / 实现中**）

> 图片消费：二次点击打开查看器（只盖主网格，信息栏留在壳右侧）；打开所在位置；系统默认应用打开。待手验 T1–T6。

| 文档 | 内容 |
|------|------|
| [`image-consume/需求.md`](image-consume/需求.md) | 范围、故事、IPC 草案 |
| [`image-consume/实现方案.md`](image-consume/实现方案.md) | 覆盖层 + Viewer.js + shell IPC |
| OpenSpec | `openspec/changes/image-consume/` |

## library-trash（**已落地 / 待 Electron 手工验**）

> 回收站页、多选批量移入/恢复/彻底删除（删库内包）。代码已写，T10–T16 待手验。

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

## metadata-panel-fields（**已落地 / 待手验**）

> 描述、立刻待办、图/视频技术字段（含帧率码率画质）、导入 Pillow/ffprobe、多语言字幕。代码已写。

| 文档 | 内容 |
|------|------|
| [`metadata-panel-fields/需求.md`](metadata-panel-fields/需求.md) | 范围与开放问题 |
| [`metadata-panel-fields/实现方案.md`](metadata-panel-fields/实现方案.md) | 包内 `subtitles/` 命名与文件清单 |
| OpenSpec | `openspec/changes/metadata-panel-fields/` |

## metadata-panel（**已定稿 / 已归档**）

> 右侧元数据面板：通用字段；独立词表；草稿点保存；编辑弹窗含换封面；删除确认。

| 文档 | 内容 |
|------|------|
| [`metadata-panel/需求.md`](metadata-panel/需求.md) | 范围、故事、验收、契约草案、开放问题 |
| [`metadata-panel/实现方案.md`](metadata-panel/实现方案.md) | 沿用 InfoPanel + library；文件清单 |
| OpenSpec | 已归档 `openspec/changes/archive/2026-09-23-metadata-panel/` |

## 早期 change（**已归档** · D-20260923-01）

> 无独立 `需求.md`。任务当时已全部勾完，不变量已进基线。

| change | 归档 |
|--------|------|
| `align-resource-api` | `openspec/changes/archive/2026-09-23-align-resource-api/` · 主 spec `library-resource-api` |
| `assemble-api-routers` | `openspec/changes/archive/2026-09-23-assemble-api-routers/` · 无行为 spec |
| `shell-layout-selection` | `openspec/changes/archive/2026-09-23-shell-layout-selection/` · 主 spec `desktop-shell-selection` |

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

## tag-category-hygiene（**已定稿** · D-20260927-02）

> LRM **P1 增量**：标签/分类词表统计与删除。依赖 M4 打标能力；实现排在 MS4.1，不挡当前浏览闭环。需求已定稿，待 L2/L3。

| 文档 | 内容 |
|------|------|
| `tag-category-hygiene.md` | 词表膨胀治理：统计、删除、与 M4 边界、轮次 2 决策清单 |

## work-consumption-hub（**已定稿** · D-20260927-05）

> LRM 增量 Feature：工作上下文 + 消费渠道。三份文档已定稿；主体已编码待手验，MS5/MS6 不再返工。

| 文档 | 内容 |
|------|------|
| `work-consumption-hub.md` | 主需求：定位变更、核心概念、范围、开放问题 |
| `wch-modules.md` | 增量模块拆解（M7–M10）与 API 草案 |
| `wch-ui.md` | UI 增量：工作区面板、首页概览、消费渠道设置 |
