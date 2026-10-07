# handoff · watch-source-dirs

- 状态：**已实现 + E2E 验证**；待 Electron 手验
- 补扫轮（2026-10-07）：
  - `WatchBridge.catch_up(dirs)`：启动/设置保存后遍历监视目录（按类型扩展名过滤），合成事件入队复用导入管道；已入库文件由 sha256 查库去重跳过
  - 触发点：main.py lifespan（启动）+ `patch_watch`（设置保存后）
  - E2E：启动前预放 2 GIF + readme.txt → 启动后补扫入队 2（txt 被过滤）→ 全部导入、修订号 +1
  - 过程中修复：catch_up 入队形状与消费端不一致（裸 FileEvent vs (event, type_) 元组）→ TypeError
- 已知边界：anime/av 自动导入未接入；DELETE 不处理；game 不可监视；补扫为全量哈希模式（manifest 增量是后续优化）
- 下一步：Electron 手验；anime/av 剧集目录自动导入立项；facts.md 同步
