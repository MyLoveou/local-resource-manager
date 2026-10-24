# 设计 · platform-debt（L3 HOW）

> 与 `docs/requirements/features/platform-debt/设计.md`（L2）同一范围；本文件只落 HOW。

## D2 · token 校验

### 挂载顺序

```text
app = FastAPI(lifespan=...)
app.add_middleware(CORSMiddleware)          # 既有
app.middleware("http")(log_requests)        # 既有：先记 Request
app.middleware("http")(require_token)       # 新增：鉴权
app.middleware("http")(wrap_json_envelope)  # 既有：最外层包信封
```

`require_token` 直接返回**已完成信封**的 `JSONResponse`，因此不依赖它相对 `wrap_json_envelope` 的位置：`is_envelope()` 会原样放行。

**顺序有硬要求**：Starlette 里最后注册的中间件在最外层。CORS 必须最后注册（最外层），否则
① 预检 `OPTIONS` 会先被鉴权 401（浏览器不发真正请求）；
② 401 响应不带 CORS 头，渲染进程只能看到 `Network Error`。
同时 `require_token` 主动放行 `OPTIONS`，作为不依赖顺序的防御。

### 关键决策

| 项 | 决定 | 理由 |
|----|------|------|
| 凭证 | 单一共享 token，来自 `BACKEND_TOKEN` | 主进程已按此生成并注入 |
| 环境映射 | `Settings` 增加 `env_prefix="BACKEND_"` | 现状字段名 `token` 读的是 `TOKEN`，`BACKEND_TOKEN` 实际被忽略 |
| 比较 | `secrets.compare_digest` | 避免时序侧信道 |
| 空 token | **视为未启用鉴权** + 启动 WARN | 保住 `pnpm backend:start`、`/docs` 手测与既有 159 项测试；Electron 路径永远有 token，故发布态始终开启校验 |
| 401 文案 | `未授权` | 不区分「没带」「带错」，不泄露 token 是否存在 |
| 日志 | 只记 `method + path` | 与 `mapHttpError` 的敏感信息规则一致 |

### 豁免清单（`shared/constants.py`）

```python
AUTH_EXEMPT_PREFIXES = ("/docs", "/redoc", "/openapi.json")
AUTH_EXEMPT_SUFFIXES = ("/health", "/content")  # 健康检查 + 媒体字节流
AUTH_EXEMPT_PATHS = ("/scrape/proxy-image",)    # 刮削封面代理（<img> 直链）

def is_auth_exempt(path: str) -> bool: ...
```

`/health` 用**后缀**而非前缀：`/library/health`、`/scrape/health`、`/download/health` 都不以 `/health` 开头，前缀规则会漏（实现时踩过一次，已改为后缀）。

### 数据流

```text
渲染进程 axios ──Bearer──► require_token ──ok──► 路由
<img>/<video> ──无头────► require_token ──后缀命中──► 路由（豁免）
裸跑/手测     ──无头────► token 为空 ──► 直接放行（启动已 WARN）
```

## D4 · 事件循环

### 判定规则（进 `coding-conventions.md`）

`async def` 里不得直接调用同步阻塞 IO（`os.walk` / `iterdir` / `shutil.*` / `subprocess.run` / `PIL.Image.open`）；必须 `await asyncio.to_thread(...)`。

### 本次补的 5 处

| 位置 | 现状 | 处理 |
|------|------|------|
| `import_service.py::_ingest_comic` | `comic_pages(root)` | `await asyncio.to_thread(comic_pages, root)` |
| `import_service.py::_ingest_game` | `find_launch(root)` | `await asyncio.to_thread(find_launch, root)` |
| `covers/ingest.py::_apply_ingest_cover_inner` | `find_folder_cover(source_root)` | `await asyncio.to_thread(...)` |
| 同上 | `find_sidecar_cover(source_file)` | `await asyncio.to_thread(...)` |
| `covers/ingest.py::_attach_game_icon` | `resolve_lnk_target(launch_path)` | `await asyncio.to_thread(...)` |

### 已合规（不动）

`hash_file`、`importer.collect`、`layout.place_primary`、`package.put_relative` / `put_cover` / `put_thumbnail`、`copy_tree_filtered`、`probe_media`、`write_grid_thumbnail`、封面提取器（抽帧 / EPUB / PDF / cbz / exe 图标）、`FileOps.remove_tree` —— 均已 `to_thread`。

## 测试策略

- 新增 `tests/test_auth.py`：T1–T9（见 `tests.md`）。
- 既有 159 项：token 为空时行为不变，**不改造**。
- D4：既有 `test_import_ingest` / `test_series_ingest` / `test_grid_thumbnails` 覆盖正确性；并发不阻塞为手工验证项（T10）。
