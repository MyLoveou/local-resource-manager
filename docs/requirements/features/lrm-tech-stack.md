# 技术栈决策 · local-resource-manager

> 状态：**已定稿**（2026-08-30 调研后定稿）
> 主需求见 [local-resource-manager.md](local-resource-manager.md)
> 调研：2026-08-30 双路检索（下载引擎 / 抓取生态）

## 1. 架构总览（三进程）

```
┌─ Electron 渲染进程 (Vue/TS) ─────────────────────┐
│        │ HTTP + SSE/WebSocket（自有 REST，token）  │
│  Electron 主进程 (TS)：窗口 / IPC / 进程编排 / 本地文件
│        ├── 抓取服务 ── Python FastAPI，127.0.0.1 随机端口 + token
│        └── 下载服务 ── Python FastAPI 编排层 + 下载引擎
│             ├── aria2c 子进程    HTTP 分段 + BT/磁力/DHT
│             └── rqbit 子进程     现代 BT / 磁力 / 流式
└───────────────────────────────────────────────┘
```

- 服务间通信：localhost HTTP + SSE/WebSocket + token 鉴权，绑定 127.0.0.1
- 存储：SQLite 共享库（单写者优先，其余短事务/只读），不引入 Redis/gRPC

## 2. 抓取服务（FastAPI）

| 层 | 选型 | 说明 |
|------|------|------|
| Web 框架 | FastAPI + uvicorn | 单进程，异步原生；勿多 worker（SQLite 锁） |
| HTTP 客户端 | httpx | HTTP/2 + brotli/zstd，全局 AsyncClient + Limits |
| HTML 解析 | selectolax (Lexbor) | 性能一个数量级优势，适合哈希批量匹配 |
| 渲染兜底 | Playwright 懒启动 | 仅强反爬/JS 站点启用，用完即关，空闲回收 |
| 反爬增强 | curl_cffi | TLS 指纹伪装（JA3/JA4），可插拔请求层 |
| 任务模型 | asyncio 进程内队列 | Semaphore(按域名) + gather；SQLite job 表持久化；SSE 进度 |
| 存储 | aiosqlite | 与既有库一致 |
| 缓存 | 封面磁盘缓存 + SQLite URL→本地映射 + HTTP 条件缓存 | 避免重复抓取 |

## 3. 下载服务（编排层 + 双引擎）

| 层 | 选型 | 说明 |
|------|------|------|
| 编排层 | Python FastAPI | SQLite 任务表为**权威状态**，aria2/rqbit 仅执行 |
| 引擎 1 | aria2c（JSON-RPC/WebSocket） | HTTP/HTTPS/FTP 多源分段、BT/磁力/DHT、限速、断点续传 |
| 引擎 2 | rqbit（HTTP API） | 现代 BT、磁力 resolve、流式播放、fastresume |
| 站点兜底 | yt-dlp | 数千 extractor；`--downloader aria2c` 对接 |
| 协议路由 | 编排层按 URL 判定 | http/https/ftp → aria2；magnet/torrent → rqbit（aria2 兜底） |

**关键原则**
- 任务状态主权在编排层 SQLite，aria2 `--save-session` 仅辅助
- 双引擎并存：BT 走 rqbit（能力新），aria2 作 BT 兜底 + 全 HTTP
- 参考实现：Motrix（Electron+Vue+aria2，MIT），其架构可作抄作业样板

## 4. 许可合规

- aria2：GPL-2.0，独立子进程 + RPC 驱动不链接代码，**不传染**（Motrix 同款）
- rqbit：Apache-2.0，宽松
- yt-dlp：源码 Unlicense，二进制分发为 GPLv3+（注意打包产物许可声明）
- 打包注意事项：aria2 官方 exe 未签名，构建期校验哈希

## 5. 风险与关注点

- aria2 发版慢（单维护者），rqbit 高活跃可对冲
- 磁力解析慢：冷门种子加超时/多 tracker，rqbit `resolve_magnet` 兜底
- Playwright Chromium 内存高：仅按需懒启动，不做常驻
- SQLite 多进程共享：单写者优先，写库串行化

## 6. 元数据发现层（RAG 式检索 · 新增）

借鉴 RAG 检索层，元数据「发现」与「抓取」分离为两类 Provider：

```
Metadata Adapter
├── SearchProvider（发现 · RAG 式）
│   ├── SearXNG（自托管元搜索，聚合 Google/Bing/DDG，免费）   ← 主方案
│   └── 预留商业 API 接口（Exa / Tavily / Brave），配置可切换
└── SiteProvider（详情抓取 · 原方案不变）
    └── httpx + selectolax + 本地缓存
```

**决策（2026-08-30 用户确认）**
- 发现层：**SearXNG 自托管**为主；适配器接口化，商业搜索 API（Exa/Tavily）仅预留可插拔接口，按需切换
- 图片哈希匹配：**双路匹配** —— 反查图（TinEye / Google Lens）优先，哈希→搜索词兜底
- 文本匹配（视频/番剧）：标题→SearXNG 查询→候选列表→SiteProvider 抓详情

**设计要点**
- SearchProvider 返回统一候选结构（title / url / thumbnail / source / relevance）
- 反查图结果同样归一化为该结构，供批量抓取流程复用
- SearXNG 作为子进程由抓取服务编排，localhost 访问；失败时降级为直连站点搜索

## 7. 站点适配器清单（MVP 定稿）

| 适配器 | 类型 | 用途 |
|--------|------|------|
| 通用 OG 抓取器 | 抓取 | 任意命中页面提取 `og:title/og:image/og:description`，覆盖 80% 站点 |
| TMDB | API | 视频/剧集结构化元数据（免费、规范） |
| Bangumi | API | 番剧结构化元数据 |
| 图片专项（Pixiv 等） | 抓取 | 图片来源站详情/标签/作者 |
| 豆瓣 | 抓取 | 中文详情兜底，**默认关**（反爬/ToS 风险） |

- 图片匹配路径：反查图命中 → OG 抓取器 / 图片专项适配器
- 未匹配兜底：手动填写（已定）

## 8. SQLite 定稿

| 决策 | 结论 |
|------|------|
| 存储位置 | Electron `userData` 目录下单文件 `library.db`，用户可备份 |
| 并发模式 | WAL + busy_timeout，多进程安全 |
| 多进程写 | 单写者优先：资源/元数据表归抓取服务写；job 表各进程自写；写库串行化 |
| 迁移 | 内置 schema_version + 迁移脚本，启动自动升级 |
| 表结构 | resources / files / metadata / tags / tag_links / jobs / settings / adapters → **L3 数据模型**落 `docs/design/02-数据模型.md` |

## 9. 下载协议范围（MVP 定稿）

| 协议 | 引擎 | 支持 |
|------|------|------|
| HTTP / HTTPS | aria2 | ✅ 断点续传/多源分段/限速 |
| FTP / SFTP | aria2 | ✅ 零成本 |
| BT / 磁力 | rqbit + aria2 兜底 | ✅ 双引擎已定 |
| Web Seed / Metalink | aria2 | ✅ 原生顺带 |
| 站点/流媒体（HLS/DASH/m3u8） | yt-dlp | ✅ 站点兜底 |
| ED2K / WebDAV | — | ❌ MVP 排除 |
