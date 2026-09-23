# 跨会话续作 · metadata-scrape

## 状态

- 阶段：已落地（D-20260919-10）
- 最后更新：2026-09-19

## 已完成

- 需求 / 设计 / 实现方案
- `/scrape/jobs` search 不写 Resource；`select` 覆盖标题与 `synopsis`、写入 `catalog`、标签并集；不改 `description`
- 确认页预览封面（`/scrape/proxy-image`）；导入封面默认可覆盖，user 封面需显式勾选
- 导入 video/anime 入队 search
- 番剧多渠道：Bangumi 主源 + 蜜柑附加（D-20260922-01）；选蜜柑时尽量回落 Bangumi 详情
- 列表 `scrapePending`；信息栏 / 批量确认弹层
- 列表 `scrapePending`；信息栏 / 批量确认弹层
- `tests/test_scrape_jobs.py`

## 手测

设置 `TMDB_API_KEY` 后导入视频，网格出「候选」，确认后标题变。番剧走 Bangumi，可不填 token。

## 不做（本刀）

SearXNG、设置页填 key、AV/图、远程爬虫、确认前改标题。
