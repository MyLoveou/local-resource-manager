# 跨会话续作 · library-covers

## 状态

- change：`library-covers`
- 阶段：`实现中 / 待 Electron 手工验`
- 最后更新：2026-09-19 · 后端单测绿、desktop typecheck 绿

## 已完成

- TypeProfile / covers 包 / 导入自动封面 / 手指定锁定 / InfoPanel

## 下一步

1. 重启 Electron，按 tests.md T1–T10、R1 点验。
2. 本机需 PATH 上有 ffmpeg 才能看到视频抽帧。

## 阻塞

- 待手工验。旧库不回填。

## 关键路径

- `app/library/application/covers/`
- `InfoPanel` `allowsUserCover`
