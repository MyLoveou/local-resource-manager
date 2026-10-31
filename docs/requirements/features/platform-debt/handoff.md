# 跨会话续作 · platform-debt

## 状态

- 阶段：**已落地**（2026-09-27，`D-20260927-06`；余 Electron 手验）
- change：`openspec/changes/platform-debt/`
- 最后更新：2026-09-27

## 已完成

- D1 Notify 迁移（视图内已无 `useMessage`）
- D3 导入进度分相（校验/复制/探测/封面/缩略图/入队刮削）
- L1 + L2 + L3 三份文档；OpenSpec change 已建

## 下一步

- [x] 落地 D2（token 校验）与 D4（5 处同步 IO）
- [x] 跑 `tests.md` T1–T11（14 项新增单测全绿；全量 170 passed）
- [x] 同步 API 设计 / baseline / README / facts
- [ ] Electron 手验：应用内导入 → 网格 → 看图 → 播放 → 回收站（确认媒体豁免生效）
- [ ] 手验 T10b：导入大目录时 `/library/health` 持续 200

## 不做

用户登录与权限模型、token 轮换 UI、HTTPS、签名 URL / 前端 blob、导入搬进程。
