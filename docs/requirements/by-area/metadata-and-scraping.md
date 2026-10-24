# 元数据与抓取 · 跨类型需求

> 抓取是“候选 → 用户确认 → 回填”，不是自动静默覆盖。

## 1. 已实现

- `ScrapeJob` / `Candidate` 任务模型；`/scrape/jobs`、候选列表、预览、确认。
- 视频/番剧：TMDB、B站（按现有适配器）。
- 番剧：Bangumi。
- 通用：Open Graph 页面抓取、封面/简介/作者等字段候选。
- 抓取结果可在确认时选择应用哪些字段；封面可单独选择。
- 失败/无候选有状态与错误信息，不阻塞其他资源。

## 2. 部分实现 / 缺口

| 能力 | 状态 | 说明 |
|------|------|------|
| 图片站点刮削 | 未实现 | 图片还没有专用适配器（N9） |
| AV 专属站点 | 未实现 | 无 AV 适配器；不自动抓未确认内容 |
| 多站点字段合并 | 未实现 | 各适配器独立；冲突未自动合并 |
| 角色/演员结构化 | 未实现 | R3；抓取目前主要落标题/简介/封面/标签 |
| 自动重试/批量抓取策略 | 部分 | 有任务队列；复杂退避/批量策略未收口 |
| XMP/sidecar | 未实现 | 远期；与库内副本真源冲突 |

## 3. 明确边界

- 不自动应用候选；用户确认后才写 Resource。
- 不把站点 HTML 直接存为富文本/脚本。
- 抓取失败不能把资源标成“已刮削成功”。
- 下载不在此模块；下载统一委托第三方（D-20261007-01）。

## 4. 入口

- `apps/backend/app/scrape/`
- `apps/desktop/src/renderer/src/components/ScrapeConfirmQueue`
- `features/metadata-scrape/`、`features/bilibili-scrape/`、`features/scrape-confirm-ux/`
- `features/image-library-depth/`（N9 图片刮削）
