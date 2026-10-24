# handoff · library-workspace

> 状态：**已 apply（2026-10-19）· 待发版手验**
> 业务代码、迁移与 0.1.1 本地包已完成；未提交/未推送。

## 已完成

- L1/L2/L3：`docs/requirements/features/library-workspace/`
- OpenSpec：`proposal.md`、`design.md`、`specs/`、`tasks.md`、`tests.md`
- 分类树 `0018`、保存视图 `0019`；真实库副本迁移对账通过
- 资源库 `/library/:type`、类型 tabs、分类树、网格/时间线/地图入口
- 多分类赋值、子树筛选、`待整理分类`、分类管理
- 保存时间线（多分类并集、无成员表、默认排除未知时间）
- 首页 `/library/home`、D 叠图卡、Ctrl/Shift/Esc
- 后端 195 passed；前端 typecheck/lint/build 通过；`release:win` verify PASS

## 下一步

1. 安装 `release/local-resource-manager-0.1.1-win-x64-setup.exe` 手验真实库。
2. 手验通过后，把当前 R1/时间线/工作区改动拆分提交；**未获用户要求不要提交**。
3. 需要发布更新时 bump 0.1.2 + tag；归档需用户单独要求。
4. 剩余未做：完整地图交互、日期范围保存 UI、角色/人脸、分类多节点筛选、时间线成员表。

## 风险

- 旧 `resources.category_id` 本版保留只读回滚，下一版删除。
- 迁移会重建 categories；继续用真实库副本/备份。
- 真实库当前未执行迁移，安装新包后首次启动执行。
