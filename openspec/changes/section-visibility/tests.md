# 测试 · section-visibility

> 声称完成前实跑，禁止臆造 PASS。

## 映射

| Spec 场景 | 切片 | 测试 ID | 类型 | 命令或步骤 | 期望 |
|-----------|------|---------|------|------------|------|
| 主路径：菜单隐藏 | UI | T1 | 冒烟/手工 | 启动应用看左侧菜单 | 无 AV/小说/漫画/游戏/模型 |
| 主路径：路由拦截 | 功能 | T2 | 手工 | 地址栏 `#/av`、`#/novel` 等 | 重定向首页 |
| 主路径：导入与首页 | UI | T3 | 手工 | 打开导入向导；看首页概览 | 无这 5 类选项/统计卡 |
| 空配置回归 | 组合根 | T4 | 手工 | `HIDDEN_SECTIONS = []` 重启 | 菜单/导入/首页与现状一致 |
| 边界：子路径/未知/首页 | 算法+功能 | T5 | 手工 | 配 `'/collections'` 访问 `#/collections/1`；配未知 key；配 `'/'` | 子路径重定向；未知忽略；首页可访问 |
| 回归：构建与静态检查 | — | R1 | 构建 | typecheck/lint/build | 全绿 |
| 回归：后端未受影响 | — | R2 | 接口 | 全量 pytest | 177 passed |

## 命令

```powershell
pnpm --filter desktop typecheck
pnpm --filter desktop lint
pnpm --filter desktop build
apps/backend/.venv/Scripts/python -m pytest -q apps/backend/tests

# 算法谓词（Node 24 直接跑 TS）
node --experimental-strip-types --input-type=module -e "import { isSectionHidden } from './apps/desktop/src/renderer/src/domain/visibility.ts'; ..."
```

## 记录

| ID | 结果 | 证据（日志摘要/截图路径） | 日期 |
|----|------|---------------------------|------|
| T1 | 未跑 | 需 Electron 手验 | |
| T2 | 未跑 | 需 Electron 手验 | |
| T3 | 未跑 | 需 Electron 手验 | |
| T4 | 未跑 | 需 Electron 手验 | |
| T5 | 部分 PASS | 算法谓词 11 例 PASS（`/av/1` 前缀命中、`/` false、`/avx` false、未知 path false）；`'/collections'` 子路径重定向待手验 | 2026-10-07 |
| R1 | PASS | vue-tsc web/node exit 0；eslint 0 errors；electron-vite build 成功 | 2026-10-07 |
| R2 | PASS | `pytest -q apps/backend/tests` → 177 passed, 2 subtests passed | 2026-10-07 |

## 未覆盖（必须说明）

- T1–T5：无前端自动化测试框架（`apps/desktop/package.json` 无 test script），只能 typecheck/lint/build + Electron 手验；手工步骤已在映射表写明。
- 最近消费点击隐藏类型：由 T2 的守卫覆盖（重定向首页），不单独列条。
