# 05 · CORS 跨域配置

## 现象

渲染进程（`http://localhost:5173`）请求后端（`http://127.0.0.1:8000`），浏览器报跨域拦截。

## 背景

渲染进程与后端端口不同源（`localhost` vs `127.0.0.1` 在 CORS 里就是不同 origin），浏览器必须放行。桌面应用有两条路：

| 方案 | 机制 | 打包后 | 结论 |
|------|------|--------|------|
| vite dev proxy | renderer 用 `/api` 相对路径，vite 代理到后端 | ❌ 打包后无 vite dev server | 不选，双路径 |
| **直连 + 后端 CORS** | renderer 直连 `http://127.0.0.1:8000`，后端放行 | ✅ 同样工作 | **选这个，dev/prod 统一** |

## 修复（main.py 根应用）

```python
from fastapi.middleware.cors import CORSMiddleware
from app.shared.config import settings

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,   # ["*"]，配置收口于 settings
    allow_credentials=False,               # 用 token 头，不用 cookie → 可安全用 "*"
    allow_methods=["*"],
    allow_headers=["*"],
)
```

`config.py`：

```python
cors_origins: list[str] = ["*"]   # 本地服务绑定 127.0.0.1 + token 鉴权（非 cookie），"*" 安全
```

## 安全说明

- 后端只绑定 `127.0.0.1`（不暴露外网）+ token 鉴权（非 cookie），`allow_origins=["*"]` 安全
- 若日后收紧，改为具体源列表（如 `["http://localhost:5173"]`）

## 验证

```powershell
# 带 Origin 的请求应返回头
Invoke-RestMethod http://127.0.0.1:8000/library/overview -Headers @{Origin='http://localhost:5173'}
# 响应应含 access-control-allow-origin: *
```

## 与 CSP 的区别（易混）

| | CSP | CORS |
|--|-----|------|
| 谁发起的 | 浏览器自己，发请求**前**拦截 | 浏览器对跨源响应，**收到后**校验 |
| 请求到没到后端 | **没到** | **到了**（预检 OPTIONS 会到） |
| 症状 | 后端日志无请求 | 后端日志有 OPTIONS/GET 但浏览器报错 |

## 踩坑：鉴权中间件排在了 CORS 外面（2026-09-27）

加了 Bearer 鉴权之后，应用一启动就全黑：后端日志出现

```text
WARNING - 拒绝未授权请求 OPTIONS /library/overview
[renderer] - WARN - [http] GET /library/overview -> network
[renderer] - DEBUG - [notify] Network Error
```

### 根因（两层）

1. **CORS 预检请求按规范不携带凭证** —— 浏览器发 `OPTIONS` 时不会带上 `Authorization`。鉴权中间件把这个预检 401 掉，浏览器随后**拒绝发出真正的 GET**，前端只能看到 `Network Error`。
2. **中间件顺序错了**。Starlette 里 `add_middleware` 是**插到最前面**，而 `build_middleware_stack` 从后往前包，所以 **最后注册的中间件在最外层**。原代码先注册 CORS、后注册鉴权 → 鉴权在外 → 预检先撞鉴权。附带后果：401 响应不带 CORS 头，浏览器连错误原因都读不到。

### 修复（两条都要做）

```python
# 1) 鉴权中间件主动放行预检（不依赖注册顺序，防御性）
if request.method == "OPTIONS":
    return await call_next(request)

# 2) CORS 挪到**最后**注册 = 最外层：先应答预检，并给所有响应（含 401）加 CORS 头
app.middleware("http")(log_requests)
app.middleware("http")(require_token)
app.middleware("http")(wrap_json_envelope)
app.add_middleware(CORSMiddleware, ...)   # ← 最后
```

### 验证（真实进程，不是 TestClient）

```text
预检 OPTIONS        -> 200  ACAO=*  ACAH=authorization
真实 GET(带 token)   -> 200  ACAO=*
真实 GET(无 token)   -> 401  ACAO=*     ← 401 也必须带 CORS 头
```

### 教训

1. 任何「给所有请求加一道关卡」的中间件（鉴权、限流、审计），都要先问一句：**预检请求能不能过**。
2. **CORS 必须是最外层**。放在里面的后果不只是预检失败，还有「错误响应没有 CORS 头 → 前端只看到 Network Error」，把真实原因藏起来。
3. 顺序问题在 TestClient 上也复现（`TestClient.options(...)` 带 `Origin` + `Access-Control-Request-Headers` 即可），所以能写成单测，别只靠手点。

## 扩展阅读

### 站内（本仓）

- [04-CSP拦截渲染进程请求](04-CSP拦截渲染进程请求.md)
- [42-图解-一次请求的完整旅程](42-图解-一次请求的完整旅程.md)

### 站外知识

- [MDN · CORS](https://developer.mozilla.org/zh-CN/docs/Web/HTTP/CORS)
- [MDN · HTTP 概述](https://developer.mozilla.org/zh-CN/docs/Web/HTTP)
