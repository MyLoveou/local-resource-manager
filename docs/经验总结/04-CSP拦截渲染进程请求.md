# 04 · CSP 拦截渲染进程请求（最隐蔽的网络黑盒）

## 现象

- axios 报 `AxiosError: Network Error`
- **后端日志收不到任何请求**（连 OPTIONS 都没有）
- baseURL 确认正确、后端确认在运行

## 根因

渲染页面 `index.html` 的 CSP meta 只有：

```html
<meta http-equiv="Content-Security-Policy"
  content="default-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:" />
```

`default-src 'self'` 会把 `connect-src` 一并限为 `'self'`（即页面源 localhost:5173）。**XHR 到 `http://127.0.0.1:<动态端口>` 在发请求前就被浏览器拦截** → 后端永远收不到 → axios 报 Network Error。

## 修复

```html
<meta http-equiv="Content-Security-Policy"
  content="default-src 'self'; connect-src 'self' http://127.0.0.1:* http://localhost:*; style-src 'self' 'unsafe-inline'; img-src 'self' data: http://127.0.0.1:*" />
```

- 端口动态 → 用 `http://127.0.0.1:*` 通配
- `img-src` 也放行本机，供后续封面/缩略图本地服务

## 排查方法论（最重要）

**请求不通时，先看后端日志有没有收到请求：**

```
后端收到 → 问题在 CORS / 业务层（见 05）
后端没收到 → 问题在 CSP / 网络层（本文件）
```

本次就是靠这条铁律定位的：后端日志只有 `GET /health`（健康检查），渲染进程的请求根本没到。

## 延伸

- CSP 是浏览器安全机制，Electron 同样生效。
- 修改 CSP 后需重启应用（meta 在 HTML 里，构建/热更不一定刷到）。
- 排查工具：DevTools → Network 面板，被 CSP 拦截的请求会直接红字 "net::ERR_BLOCKED_BY_CSP"。
