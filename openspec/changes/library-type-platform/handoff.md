# 跨会话续作 · library-type-platform

## 状态

- change：`library-type-platform`
- 阶段：`feat 已落地 / 待手工 T7–T12 / 未合 master`
- 分支：`feat/library-type-platform`
- 最后更新：2026-09-17

## 已完成

- TypeProfile、0009 storage_kind、三路入库、游戏默认 indexed、漫画无阅读器
- TypeBrowse 取代类型页克隆
- Howler / model-viewer / shell-open / CSP
- 后端 71 tests + desktop typecheck 绿

## 下一步

1. 重启 `pnpm run dev`（跑迁移 0009）
2. 手工：导入各类型、音频 overlay、模型预览、游戏启动不复制、离页
3. 用户要求后再合 master
