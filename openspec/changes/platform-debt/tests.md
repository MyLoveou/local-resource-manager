# 测试 · platform-debt

> 每个 spec 场景一行可执行检查。声称完成前实跑。
> 命令统一在 `apps/backend` 下执行：`.venv/Scripts/python.exe -m pytest -q`。

## 映射

| Spec 场景 | 测试 ID | 类型 | 命令或步骤 | 期望 |
|-----------|---------|------|------------|------|
| 缺请求头 | T1 | 单测 | `pytest tests/test_auth.py -k missing` | 401，`code=401` `status=error` |
| 错 token | T2 | 单测 | `pytest tests/test_auth.py -k wrong` | 401 |
| 对 token | T3 | 单测 | `pytest tests/test_auth.py -k valid` | 200，业务体不变 |
| 健康检查免鉴权 | T4 | 单测 | `pytest tests/test_auth.py -k health` | `/health` 与 `/library/health` 均 200 |
| 文档免鉴权 | T5 | 单测 | `pytest tests/test_auth.py -k openapi` | 200，不含 `status` 键 |
| 媒体端点免鉴权 | T6 | 单测 | `pytest tests/test_auth.py -k media` | `*/content` 不是 401；列表端点仍是 401 |
| 日志不含 token | T7 | 单测 | `pytest tests/test_auth.py -k log` | WARN 记录里无 token 原文 |
| 空 token 放行 | T8 | 单测 | `pytest tests/test_auth.py -k disabled` | 无头请求 200 |
| 环境变量映射 | T9 | 单测 | `pytest tests/test_auth.py -k env` | `BACKEND_TOKEN` → `settings.token` |
| 导入不堵事件循环 | T10 | 单测 | `pytest tests/test_import_concurrency.py -q` | `comic_pages` / `find_launch` / `find_folder_cover` 的调用线程 ≠ 事件循环线程 |
| 导入期间服务可用 | T10b | 手工 | 导入大漫画/游戏目录，同时反复 `GET /library/health` | 期间 `/health` 持续 200 |
| CORS 预检不被鉴权拦 | T12 | 单测 | `pytest tests/test_auth.py -k preflight` | `OPTIONS` 200 + `access-control-allow-origin` |
| 401 带 CORS 头 | T13 | 单测 | `pytest tests/test_auth.py -k cors` | 401 响应含 `access-control-allow-origin` |
| 既有回归 | T11 | 单测 | `pytest -q` | 全绿（含 token 为空时既有用例不受影响） |

## 备注

- T10 用线程探针做**确定性**断言（不依赖目录规模与计时）；T10b 仍建议在 Electron 手验时顺带看一眼。
- 前端无需新测试：axios 拦截器已带 `Bearer`（`renderer/src/infrastructure/http/client.ts`），本次未改。
