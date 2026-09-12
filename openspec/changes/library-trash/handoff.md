# 跨会话续作 · library-trash

## 状态

- change：`library-trash`
- 阶段：`实现中 / 待手工验收`
- 最后更新：2026-09-12

## 已完成

- 后端 restore / purge / batch + `tests.test_library_trash` 11 项绿
- 前端 `/trash`、批量删除模式、面板恢复/彻底删除、`bump(null)` 刷新列表
- typecheck + desktop build 通过

## 下一步

1. 重启 Electron，手工 T10–T16
2. 用户确认后可 archive

## 阻塞

- 手工 UI 未跑
