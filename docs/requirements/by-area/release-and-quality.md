# 发布与质量 · 跨类型需求

## 1. Windows 发布

已实现：

- `pnpm release:win`：typecheck → lint → pytest → 前端构建 → PyInstaller 后端 → ffprobe → electron-builder（NSIS + zip）→ verify。
- 后端冻结为 onedir，随包分发，不要求用户安装 Python。
- `verify-release` 检查安装包/后端/ffprobe/latest.yml/app-update.yml，并启动冻结后端 `/health`、检查 DB。
- GitHub Actions tag `v*` 发布 Release；仓库 public；资产含 setup/blockmap/zip/latest.yml/SHA256SUMS。
- 应用更新：electron-updater + GitHub Releases；更新说明纯文本、进度/速度/剩余时间、手动下载兜底。

未实现/限制：

| 能力 | 状态 | 说明 |
|------|------|------|
| 代码签名 | 未实现 | 未签名，Windows SmartScreen 可能提示 |
| 差分更新 | 未验证 | 有 blockmap；首次更新通常仍是全量 |
| macOS/Linux 包 | OUT | 当前仅 Windows x64 |
| 下载加速 | OUT | 默认 GitHub；无第三方镜像 |
| 自动回滚 | OUT | 只能发更高版本修复 |

## 2. 测试门禁

- 后端：`pytest`，当前 **201 passed**；临时 DB + migrate；服务层优先。
- 前端：`vue-tsc` + `tsc`、ESLint、electron-vite build；lint 仍有历史 warning，0 error。
- 发布前必须全绿；发布后做冻结后端 health 冒烟。
- 已知测试缺口：前端没有完整的组件/E2E 测试脚本，主要靠 typecheck/build + 手工/ CDP 验收。

## 3. 安全与数据

- 后端默认绑定 `127.0.0.1`；token 由主进程随机生成。
- 动态 token 走 `additionalArguments`，不进 URL/localStorage。
- 不记录 token；HTTP 日志不打印敏感请求体。
- 数据库迁移只增不改；安装版数据在 `%APPDATA%/local-resource-manager`。
- 地图使用 OSM 在线瓦片会暴露视口；不上传照片/精确坐标字段。

## 4. 入口

- `scripts/release.mjs`、`scripts/verify-release.mjs`
- `.github/workflows/release-windows.yml`
- `apps/desktop/src/main/infrastructure/services/update.ts`
- `features/production-packaging/`、`features/app-update/`
- `docs/经验总结/23-GitHub-Releases与自动更新.md`、`26-发布构建与测试门禁.md`
