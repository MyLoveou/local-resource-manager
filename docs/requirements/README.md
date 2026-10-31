# 需求总览（按资源类型 + 跨类型）

> 目标：把“某个资源类型到底要什么”和“所有类型共用的能力”分开，避免需求全堆在 `features/` 里。
>
> 三层关系：
>
> 1. **本目录**：按资源类型/能力域的**需求视图**，说明现状、缺口、边界。
> 2. `features/<id>/`：单个能力的 L1/L2/L3 详细文档，仍是验收与实现依据。
> 3. `docs/product/facts.md` / `decisions.md`：跨会话事实与拍板，不在这里复制。

## 1. 按资源类型

| 类型 | 文档 | 当前定位 |
|------|------|----------|
| 图片 | [image.md](by-type/image.md) | 导入、看图、时间线、GPS 地图、备注、分类/合集 |
| 视频 | [video.md](by-type/video.md) | 单文件视频导入、播放、TMDB/B站抓取 |
| 番剧 | [anime.md](by-type/anime.md) | 目录/系列、季集、播放、TMDB/Bangumi/B站 |
| AV | [av.md](by-type/av.md) | 目录/系列、播放、封面；元数据与角色维度待定 |
| 音频 | [audio.md](by-type/audio.md) | 文件导入、内置播放、内嵌封面 |
| 小说 | [novel.md](by-type/novel.md) | EPUB/PDF/TXT 等导入、系统打开、封面 |
| 漫画 | [comic.md](by-type/comic.md) | cbz/cbr/图片包、封面、系统打开 |
| 游戏 | [game.md](by-type/game.md) | 目录登记、启动器、默认只登记路径 |
| 模型 | [model.md](by-type/model.md) | gltf/glb 预览，其它格式外部打开 |
| 工作目录 | [work-directory.md](by-type/work-directory.md) | 路径登记、工作台、备注/待办 |

## 2. 跨类型能力

| 能力域 | 文档 | 覆盖 |
|--------|------|------|
| 资源库与组织 | [library-and-organization.md](by-area/library-and-organization.md) | Resource/File、分类树、标签、合集、时间线、搜索/排序、回收站、批量、导入/导出 |
| 消费与播放器 | [consumption-and-players.md](by-area/consumption-and-players.md) | `openResource`、消费渠道、图片查看器、视频/音频/模型、系列选集 |
| 元数据与抓取 | [metadata-and-scraping.md](by-area/metadata-and-scraping.md) | TMDB、Bangumi、B站、Open Graph、候选确认、封面；图片刮削未做 |
| 设置与监视 | [settings-and-watch.md](by-area/settings-and-watch.md) | 凭证、系统路径、备份、监视目录、解析规则、消费渠道 |
| 发布与质量 | [release-and-quality.md](by-area/release-and-quality.md) | Windows 打包、更新、CI、测试门禁、已知限制 |
| 非目标与边界 | [non-goals.md](by-area/non-goals.md) | 明确不做/暂不做，防止需求膨胀 |

## 3. 状态标记

- **已实现**：有代码、有测试或已有手工验收记录。
- **部分实现**：主路径可用，但文档中的验收项未全部覆盖。
- **待设计**：L1 已明确，尚未进入 L2/L3。
- **候选**：方向，不等于已排期。
- **OUT**：明确不做或当前版本不做。

## 4. 维护规则

- 新需求先判断：属于某个资源类型，还是跨类型能力。
- 类型文档只写该类型的差异；共用能力写 `by-area/`，不要复制十份。
- 详细验收仍写 `features/<id>/需求.md`；类型文档链接过去。
- 实现/方向变化同步 `docs/product/facts.md`；拍板同步 `decisions.md`。
- 某个类型新增能力时，同时更新：
  1. `by-type/<type>.md`
  2. 对应 `features/<id>/`
  3. 如涉及共用能力，更新 `by-area/`
