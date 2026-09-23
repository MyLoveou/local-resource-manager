# 跨会话续作 · bilibili-scrape

## 状态

- 阶段：**已编码**（待 Electron 手验）
- 拍板：D-20260922-03
- 最后更新：2026-09-22

## 已完成

- L1/L2/L3
- Provider + job.query + 手填 BV + 信息栏/确认队列
- `unittest tests.test_bilibili_scrape tests.test_scrape_jobs` 19 passed

## 手测

视频信息栏填 BV → 获取元数据 → 确认后标题为投稿名。文件名含 BV 可不填。番剧不应出现 BV 框。非法串应提示无法识别。

## 不做

登录、下载、批量填 BV、番剧渠道。
