# 测试 · production-packaging

> 声称完成前实跑，禁止臆造 PASS。

## 映射

| Spec 场景 | 切片 | 测试 ID | 类型 | 命令或步骤 | 期望 |
|-----------|------|---------|------|------------|------|
| 主路径：一键发布 | 组合根 | T1 | 构建 | `pnpm release:win` | 退出码 0；产物齐全 |
| 冻结后端独立启动 | 功能 | T2 | 冒烟 | verify 脚本内含；也可手动 spawn | `/health` 200；DB 生成 |
| 产物/版本/命名 | 功能 | T3 | 脚本 | `pnpm release:verify` | 版本一致；SHA256 生成 |
| 失败即阻断 | 组合根 | T4 | 脚本 | 故意移除冻结后端后跑 verify | 非零退出，无 SHA256SUMS |
| 生产态数据落 userData | 功能 | T5 | 手工 | 安装包启动 → 检查 `%APPDATA%/local-resource-manager` | `library.db` + `logs/` |
| 开发态回归 | 组合根 | T6 | 手工 | `pnpm dev` | 后端 venv 启动；数据在 `apps/backend/data` |
| 门禁回归 | — | R1 | 构建 | typecheck / lint / pytest | 全绿 |
| CI 语法 | — | R2 | 静态 | workflow YAML 解析 | 合法 |

## 命令

```powershell
pnpm --filter desktop typecheck
pnpm --filter desktop lint
apps/backend/.venv/Scripts/python -m pytest -q apps/backend/tests   # cwd=apps/backend
pnpm release:win
pnpm release:verify
```

## 记录

| ID | 结果 | 证据（日志摘要/截图路径） | 日期 |
|----|------|---------------------------|------|
| T1 | PASS | `pnpm release:win` 退出 0；setup 135.7MB、zip 181.4MB；图标已嵌入（无默认图标警告） | 2026-10-07 |
| T2 | PASS | verify 启动冻结后端 → `/health` 200；临时 DB 192KB | 2026-10-07 |
| T3 | PASS | `pnpm release:verify` PASS；`SHA256SUMS.txt` 两条哈希 | 2026-10-07 |
| T4 | PASS | 移走冻结后端 exe → verify exit 1、无 SHA256SUMS；恢复后 PASS | 2026-10-07 |
| T5 | PASS | 静默安装到 `%LOCALAPPDATA%\Programs\资源管理器`；启动后 `%APPDATA%/local-resource-manager/{library.db,logs}` 更新；卸载后程序目录移除、数据保留（导入/打开未点） | 2026-10-07 |
| T6 | 未跑 | 需手工 `pnpm dev` 回归 | |
| R1 | PASS | typecheck 0；eslint 0 errors；pytest 177 passed（随 release:win） | 2026-10-07 |
| R2 | PASS | `release-windows.yml` 经 js-yaml 解析成功 | 2026-10-07 |

## 未覆盖（必须说明）

- T5/T6：依赖安装与人工点击，无法在无 GUI 环境自动断言；步骤已写明。
- 签名/杀软：未签名，SmartScreen 提示属预期。
