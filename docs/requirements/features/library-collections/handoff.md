# handoff · library-collections

- 状态：**已实现 + E2E 验证**；待 Electron 手验
- 本轮（2026-10-07 增量设计 §8 已确认：A 混排 / 目录名优先 / 类型页不放合集卡）：
  - 迁移 `0016_collections.sql`：collections / collection_items（成员多对多、手动 position）
  - 后端：CollectionRepository（CRUD/成员增删/上移下移/软删过滤）、CollectionService 用例、`/library/collections` 全套路由、`/library/resources/{id}/collections`
  - **全库混排**：`GET /library/resources`（type 空、无过滤、默认排序）资源与合集卡按时间混排（offset 分页）；合集卡含首成员缩略图
  - **自动归集合集**：watch 导入后按目录名定位/新建合集并加入（开关 `autoCollection`）
  - **EP 前缀**：bilidown 导入标题 `{ep:02d}. {title}`（开关 `titleWithEp`）
  - 前端：合集列表页 / 成员页（移出/上移下移）/ 全库网格混排渲染（点击合集卡进成员页）/ 信息栏「加入合集」弹窗 / 设置「命名解析」页签两开关
  - E2E：合集 CRUD → 混排卡 → 开关 → bilidown 视频监视导入（标题 `07. 测试标题`）→ 自动归集到目录名合集
- 排障记录：测试清理脚本必须 `PRAGMA foreign_keys=ON`，否则级联失效产生孤儿 files 行导致哈希查重误判（已清）
- 已知边界：合集卡不参与搜索/标签/分类过滤（仅全库无过滤浏览）；合集改名/删除 UI 未做（后端已有）；混排为 offset 分页（量大时可优化）
- 下一步：Electron 手验（建合集→加入→全库网格见合集卡→监视自动归集）；facts.md 同步
