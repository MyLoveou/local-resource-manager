# L3 技术方案

`plan-workflow` 维护的技术方案文档落点。需求（L1）定稿后，在此生成 `<feature>-plan.md`，并与 `02-数据模型.md` 同步。

| 文档 | 说明 |
|------|------|
| [00-路线图与里程碑.md](00-路线图与里程碑.md) | 全项目任务拆分与里程碑（MS0–MS7 + MS4.1）；**§0 进度以 2026-09-19 为准** |

## local-resource-manager（L1 已定稿，待出 L3）

| 文档 | 说明 |
|------|------|
| `features/local-resource-manager-plan.md` | L3 技术方案（plan-workflow 生成，待办） |
| `02-数据模型.md` | 表结构：resources / files / metadata / tags / tag_links / jobs / settings / adapters |
| [03-日志系统.md](03-日志系统.md) | 前后端统一目录/格式、electron-log + Python logging（学习向见 [经验总结/20](../经验总结/20-日志系统.md)） |
| [04-全局提示系统.md](04-全局提示系统.md) | 渲染进程统一 Notify：Toast / Push / Confirm / Loading，与日志分工、错误映射 |
| [05-资源分页与无限滚动.md](05-资源分页与无限滚动.md) | 列表分页信封 + 触底加载（实现前契约草案） |
| [06-虚拟滚动与分页.md](06-虚拟滚动与分页.md) | **学习向**：两层模型、前后端分工、TanStack lanes、触底、踩坑与检查清单 |
