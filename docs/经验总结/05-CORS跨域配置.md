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
