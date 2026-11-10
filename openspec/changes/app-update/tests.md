# 测试 · app-update

## 映射

| Spec 场景 | 切片 | 测试 ID | 类型 | 命令或步骤 | 期望 |
|-----------|------|---------|------|------------|------|
| 检查与公告 | 功能+UI | T1 | 冒烟 | 安装版启动/设置页检查 | 有无更新状态正确；错误可读 |
| 无 Release 404 | 功能 | T2 | 冒烟 | 0.1.1 检查（当前无 Release） | 显示「未找到更新发布（404）」，不崩溃 |
| 下载/安装 | 功能 | T3 | 手工 | 发布 0.1.2 后从 0.1.1 更新 | 下载→重启→0.1.2 |
| 发布 | CI | T4 | 手工 | push tag v0.1.2 | Release 含 setup/latest.yml/blockmap/SHA |
| 回归 | — | R1 | 构建 | 前后端门禁 | 全绿 |

## 记录

| ID | 结果 | 证据 | 日期 |
|----|------|------|------|
| T1 | PASS（部分） | 0.1.1 安装版 `getState` currentVersion=0.1.1；启动检查已触发 | 2026-10-18 |
| T2 | PASS | 无 Release：phase=error，message 映射为 404 提示（原始日志写入 main.log） | 2026-10-18 |
| T3 | 未跑 | 需先发布 0.1.2 Release | |
| T4 | 未跑 | 需 push tag 触发 CI | |
| R1 | PASS | 后端 186 passed；前端 typecheck/lint/build | 2026-10-18 |

## 未覆盖

- 完整下载/安装流程需 GitHub Release 与 CI 运行；本地未发布。
- 未签名更新可能触发 SmartScreen。
