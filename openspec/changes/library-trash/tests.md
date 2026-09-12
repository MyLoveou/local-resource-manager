# 测试 · library-trash

> 每个 spec 场景一行可执行检查。声称完成前实跑。

## 映射

| Spec 场景 | 测试 ID | 类型 | 命令或步骤 | 期望 |
|-----------|---------|------|------------|------|
| 软删 active | T1 | 单测 | `python -m unittest tests.test_library_trash -v` | 200，trashed，有 deletedAt，包仍在 |
| 软删幂等 | T2 | 单测 | 同上 | 再 DELETE 仍 200，包仍在 |
| 恢复 | T3 | 单测 | 同上 | active，deletedAt 空 |
| 恢复缺失 | T4 | 单测 | 同上 | 404 |
| purge 删行+包 | T5 | 单测 | 同上 | GET 404，目录不存在 |
| purge 不动源文件 | T6 | 单测 | 导入副本后 purge | 源路径仍存在 |
| 回收站混排 | T7 | 单测 | GET status=trashed 无 type | 图+视频 id 都在 |
| 批量部分失败 | T8 | 单测 | batch trash 合法+未知 | ok + failed |
| 批量超限 | T9 | 单测 | 201 个 id | 422，库不变 |
| 打开回收站 | T10 | 手工 | Electron 点左侧回收站 | `/trash`，网格为 trashed |
| 批量删除模式 | T11 | 手工 | 类型页点批量删除，点两张卡，再点移入回收站 | 须先进入模式才出现移入按钮；两卡进回收站 |
| 未进模式无批量删除按钮 | T11b | 手工 | 类型页只单击卡片 | 信息栏打开；列表上方没有「移入回收站」 |
| 取消确认 | T12 | 手工 | 取消移入 | 卡片仍在类型页 |
| 移入后网格 | T13 | 手工 | 确认移入 | 类型页无卡、回收站有 |
| 恢复后网格 | T14 | 手工 | 回收站恢复 | 站内无、类型页有 |
| 面板按钮 | T15 | 手工 | 切选 active / trashed | 按钮集合切换 |
| 清空回收站 | T16 | 手工 | 确认清空 | 站空、包目录没了 |
| typecheck | R1 | 构建 | `pnpm --filter desktop typecheck` | 通过 |

## 命令

```powershell
pnpm --filter desktop typecheck
apps/backend/.venv/Scripts/python -m unittest tests.test_library_trash -v
```

## 记录

| ID | 结果 | 证据 | 日期 |
|----|------|------|------|
| T1–T9 | PASS | `python -m unittest tests.test_library_trash -v`（11 tests OK，含删盘失败不 DROP） | 2026-09-12 |
| T10–T16 | 未跑 | 须重启 Electron 手工验 | |
| R1 | PASS | `pnpm --filter desktop typecheck`；`pnpm --filter desktop build` | 2026-09-12 |

## 未覆盖

- 跨未加载分页的范围选择（本轮批量模式为单击切换）
- lost 资源
- 定时过期
