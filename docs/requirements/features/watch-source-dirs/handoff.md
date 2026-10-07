# handoff · watch-source-dirs

- 状态：**已实现 + E2E 验证**；待 Electron 手验
- 剧集自动导入轮（2026-10-07）：
  - **P0 解析增强**：`series_plan` 抽不出集号时降级为「按文件名顺序自动编号」；混合场景顺延编号；新增 `classify_single_video` 单文件分类（抽不出集号归特典）
  - **P1 监视剧集增量**：`watch_bridge._import_series` 替换占位——事件按父目录分组；目录已有资源（`extra.importSourcePath`）→ 增量挂季/集/特典；没有 → 整目录系列导入建树
  - 仓储新增：`find_by_import_source` / `get_season` / `get_episode` / `max_episode_number` / `list_extras`
  - E2E：真视频目录 → 补扫建系列（2 集）→ 放 03.mkv → 增量追加（3 集）→ 修订号 +2
  - 回归：163 全过（4 个旧行为断言按新方向更新）
- 已知边界：DELETE 事件不处理；game 不可监视；增量挂集不重新生成封面/不探测（元数据可后续补）；监视导入不自动刮削
- 下一步：Electron 手验（图片/视频/番剧监视自动入库、列表软刷新）；facts.md 同步（anime/av 已接入）
