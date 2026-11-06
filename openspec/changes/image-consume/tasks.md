# 任务 · image-consume

> 收尾状态（2026-10-27）：剩余项均为需人工在 Electron 内验收，清单见 `docs/requirements/收尾清单.md`。

> 用户已确认可以按此实现。

## 1. 对齐

- [x] 1.1 已读 facts、baseline、`需求.md`、`实现方案.md` 与本 change 规划产物
- [x] 1.2 开放问题已关闭或按假设执行
- [x] 1.3 不超出实现方案文件清单

## 2. Electron 打开

- [x] 2.1 主进程 IPC showItemInFolder / openPath / openWith + 存在性校验；preload 暴露
- [x] 2.2 InfoPanel：默认打开 + 选择其他应用；验证 T5 T6 T6b T7（T5–T6b 待手工）

## 3. 查看器

- [x] 3.1 加入 Viewer.js 并封装右侧容器；覆盖层左右分栏复用 InfoPanel
- [x] 3.2 ResourceBrowser：二次点击/双击打开，批量模式不打开；验证 T1 T2（待手工）
- [x] 3.3 查看器内保存描述/待办；Esc 关闭；相邻张；验证 T3 T4（待手工）
- [x] 3.4 `pnpm --filter desktop typecheck`

## 4. 文档与验收

- [x] 4.1 更新两处 handoff
- [ ] 4.2 跑 tests.md；手工 T1–T6
