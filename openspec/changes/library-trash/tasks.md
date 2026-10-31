# 任务 · library-trash

> 收尾状态（2026-10-27）：剩余项均为需人工在 Electron 内验收，清单见 `docs/requirements/收尾清单.md`。

> 用户授权 apply 后再实现。验证对照 `tests.md`。

## 1. 对齐

- [x] 1.1 已读 facts、baseline、`需求.md`、`实现方案.md` 与本 change 的 proposal/specs/design/tests
- [x] 1.2 实现不超出实现方案文件清单

## 2. 后端

- [x] 2.1 仓储：restore、按 ids 取、hard delete 行；单测可调用
- [x] 2.2 用例：restore、purge（先删包再 DROP）、batch 部分失败；验证 T1–T9
- [x] 2.3 API：`/restore` `/purge` `/batch`（batch 注册在 `/{id}` 前）；信封与 404/409/422
- [x] 2.4 `tests/test_library_trash.py` 绿：`python -m unittest tests.test_library_trash -v`

## 3. 前端

- [x] 3.1 `http/resources.ts`：restore、purge、batch
- [x] 3.2 批量删除模式：点按钮进入，单击切换选中，模式内才显示移入回收站；验证 T11
- [x] 3.3 `library.bump` 可刷新全部页；`useResourcePage` type 可空；删除后网格同步 T13
- [x] 3.4 路由 `/trash` + `views/Trash`；InfoPanel 按 status 换按钮；批量条 + 清空；确认框 T12 T15 T16
- [x] 3.5 `pnpm --filter desktop typecheck` 通过（R1）

## 4. 文档

- [x] 4.1 同步 `docs/design/02-数据模型.md` restore/purge/batch
- [x] 4.2 两处 `handoff.md` 改为实现中

## 5. 验收

- [x] 5.1 跑 `tests.md` 后端项，禁止臆造 PASS
- [ ] 5.2 手工 T10–T16：回收站页、多选、确认取消、列表同步、清空
