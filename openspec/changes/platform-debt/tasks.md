# 任务 · platform-debt

> 收尾状态（2026-10-27）：剩余项均为需人工在 Electron 内验收，清单见 `docs/requirements/收尾清单.md`。

> 用户已授权 apply（2026-09-27，Q1–Q5 按建议通过）。**已全部完成**，余 Electron 手验。

## 1. D2 · token 校验

- [x] 1.1 `shared/config.py`：`Settings` 加 `env_prefix="BACKEND_"`，确认 `BACKEND_TOKEN` 可读
- [x] 1.2 `shared/constants.py`：新增 `AUTH_EXEMPT_PREFIXES` / `AUTH_EXEMPT_SUFFIXES` / `AUTH_EXEMPT_PATHS` + `is_auth_exempt()`（`/health` 用**后缀**匹配，前缀会漏 `/library/health`）
- [x] 1.3 新建 `shared/middleware/auth.py`：`require_token`（`secrets.compare_digest`，401 信封，日志不含 token）
- [x] 1.4 `app/main.py`：装配中间件；lifespan 里 token 为空时打 WARN
- [x] 1.5 新增 `tests/test_auth.py`（T1–T9，11 条）

## 2. D4 · 事件循环

- [x] 2.1 `import_service.py`：`comic_pages` / `find_launch` 改 `to_thread`
- [x] 2.2 `covers/ingest.py`：`find_folder_cover` / `find_sidecar_cover` / `resolve_lnk_target` 改 `to_thread`
- [x] 2.3 `docs/standards/coding-conventions.md`：补「async 里不得直接阻塞 IO」一条
- [x] 2.4 新增 `tests/test_import_concurrency.py`：线程探针断言（已反向验证：退回修复即失败）

## 3. 文档与验证

- [x] 3.1 `docs/design/03-API设计.md` §1 鉴权行改为实况
- [x] 3.2 `openspec/baseline.md` 不变量 1/2 补 token 校验口径；`README.md` 补开发态说明
- [x] 3.3 `docs/product/facts.md` 移除「`BACKEND_TOKEN` 校验」未实现项
- [x] 3.4 跑 `tests.md`：T1–T11（14 项新增全绿，全量 170 passed / 2 skipped）
- [ ] 3.5 Electron 手验（媒体豁免生效 + T10b）
