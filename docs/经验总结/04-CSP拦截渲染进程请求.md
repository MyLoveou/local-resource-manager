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

当前 `apps/desktop/src/renderer/index.html`：

```html
<meta http-equiv="Content-Security-Policy"
  content="default-src 'self';
    connect-src 'self' http://127.0.0.1:* http://localhost:* https://tile.openstreetmap.org https://server.arcgisonline.com;
    script-src 'self' 'unsafe-eval' 'wasm-unsafe-eval';
    worker-src 'self' blob:;
    style-src 'self' 'unsafe-inline';
    img-src 'self' data: blob: http://127.0.0.1:* http://localhost:* https://tile.openstreetmap.org https://server.arcgisonline.com https://picsum.photos https://fastly.picsum.photos;
    media-src 'self' blob: http://127.0.0.1:* http://localhost:*" />
```

- 端口动态 → 用 `http://127.0.0.1:*` 通配；
- 地图瓦片（Leaflet）需要放行 `tile.openstreetmap.org` 和 Esri 域名；否则地图区域空白但没有后端请求。
- `script-src` 允许 wasm/eval，模型预览/部分库需要；
- `img-src`/`media-src` 放行本机缩略图/视频，以及演示封面域名；
- 生产环境若不再使用 picsum，可移除对应域名，收紧 CSP。

> 注意：`default-src 'self'` 会兜底限制 `connect-src`。只改 `connect-src` 不要忘了 `img-src`/`media-src` 也有各自来源。

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

## 扩展阅读

### 站内（本仓）

- [03-主进程传参additionalArguments](03-主进程传参additionalArguments.md)
- [05-CORS跨域配置](05-CORS跨域配置.md)
- [42-图解-一次请求的完整旅程](42-图解-一次请求的完整旅程.md)

### 站外知识

- [MDN · CSP](https://developer.mozilla.org/zh-CN/docs/Web/HTTP/CSP)
- [MDN · HTTP 概述](https://developer.mozilla.org/zh-CN/docs/Web/HTTP)



# 什么是CSP

内容安全策略，用于防范或降低特定类型安全威胁风险的特性。

主要是用来控制文档是否允许加载某些资源，特别是JavaScript资源
