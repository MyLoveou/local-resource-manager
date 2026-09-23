# 测试 · app-performance

| ID | 类型 | 步骤 | 期望 |
|----|------|------|------|
| G0 | 记录 | 测列表/详情/导入/滚动 | 本轮无用户万级语料；基线为代码审查 + pytest |
| G-ARCH | 审查 | 渲染进程无 fs 写库/hash | 入库仍走 API |
| G1 | 单测 | `test_app_performance.py` keyset | 复合索引迁移 + 翻页不重复 |
| G2 | 单测 | 导入工人池 3 文件 | imported=3 |
| G3c | 代码 | resolveCardImageUrl | 无 thumbnail 则空串 |
| G5 | 构建 | backend pytest；desktop typecheck | 通过 |
| G6 | 手工 | `scripts/reset_library.py --yes` | 空库（须先关应用） |

## 记录

| ID | 结果 | 日期 |
|----|------|------|
| G0 | 无万级语料；定性：串行导入、offset、coverPath 回退、DevTools 常开、axios info | 2026-09-12 |
