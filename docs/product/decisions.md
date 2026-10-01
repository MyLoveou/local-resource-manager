# 项目决策记忆（压缩）

> 跨会话先读**本文最近条目** + [facts.md](facts.md)。  
> 每条 ≤8 行。新条目插在「有效决策」最上面。未拍板不进本文。

---

## 有效决策

### D-20260927-06 · 平台债 D2/D4 口径：媒体豁免 + 空 token 放行

- 日期：2026-09-27
- 场景：批次 3 的 Q1–Q5 —— token 校验与导入事件循环的实现口径
- **决定**：**Q1** token 为空 = 未启用鉴权（启动打 `WARN`；Electron 路径始终注入 token，故发布态始终校验）。**Q2** 媒体端点走**豁免**：`*/content` 与 `/scrape/proxy-image` 免请求头。**Q3** 既有 159 项测试不改造，另建 `test_auth.py`。**Q4** 只补齐 `to_thread` + 核对表，导入搬进程另立项。**Q5** 不写进 baseline 常规验收，改为「线程探针」确定性单测 + 手验顺带看。
- **为何**：`img`/`video`/`model-viewer` 无法带请求头，豁免是唯一不改前端媒体主路径的方案；空 token 放行保住 `pnpm backend:start` 手测与既有测试；线程探针（断言调用线程 ≠ 事件循环线程）比计时更快更可证。
- **不选**：fail-closed（裸跑后端与既有测试会全 401）；前端取 blob；签名 URL；本刀把导入搬进独立进程。
- **落点**：`openspec/changes/platform-debt/`；`shared/middleware/auth.py`、`shared/constants.py`、`shared/config.py`；`tests/test_auth.py`、`tests/test_import_concurrency.py`
- 状态：有效（D2/D4 已落地；文件流豁免与空 token 语义可随时单点改回 fail-closed）

> 补充（同日）：CORS 预检 `OPTIONS` 必须放行，且 **CORS 中间件注册在最外层**，否则预检被 401、401 响应又缺 CORS 头，渲染进程只会看到 `Network Error`。踩坑记录见 `docs/经验总结/05-CORS跨域配置.md`。

### D-20260927-05 · WCH 定稿：模型以 3D 为主

- 日期：2026-09-27
- 场景：`work-consumption-hub` 的 4 个开放问题阻碍定稿；其主体已编码待手验
- **决定**：`model` 类型以 **3D（gltf/glb，已内嵌预览）** 为准；AI 权重（safetensors/ckpt）不并入，留给 P5「模型管理」。待办/备注**仅应用内**存储，不导出、不同步外部笔记。**不改仓库名**。M7/M8 顺序问题**失效**（已同批完成）。
- **为何**：`facts.md` 已把模型 A-min 定义为内置 gltf 预览；权重涉及版本/来源/校验，属另一能力；导出属 P6。
- **不选**：权重并入 `model`；待办备注同步 Obsidian/Notion；改产品名；为顺序问题返工。
- **落点**：`work-consumption-hub.md` / `wch-modules.md` / `wch-ui.md`；`todo.md` P5
- 状态：有效（需求已定稿；MS5/MS6 只剩手验）

### D-20260927-04 · quality-and-deploy 拆分定稿：只留主题一条

- 日期：2026-09-27
- 场景：七条意图捆在一份草案里，多数缺可观察的失败与可测验收
- **决定**：**S3 主题**单独立项 `theme-tokens`（补齐令牌覆盖）；**S4 Docker/远程后端冻结为不做**；**S1 设置页、S2 下载/刮削弹层退回观察**（真有问题时按 fix/style 单独立项）；**S5 实现、S6 架构、S7 算法保持 OUT**。
- **为何**：无复现/无指标的「更好」不是验收标准；S4 与「只绑本机、媒体复制在库内、磁力依赖本机 aria2c」三条已拍板冲突，且依赖 token 校验先落地。
- **不选**：七条捆成一次编码；未拍板就加 Dockerfile 或远程后端地址；为「更好」平行另起一套分层。
- **落点**：`docs/requirements/features/quality-and-deploy/需求.md` §7；新需求 `docs/requirements/features/theme-tokens/`
- 状态：有效

### D-20260927-03 · 合集定稿：分组，不是作品

- 日期：2026-09-27
- 场景：`library-collections` 的设计与 4 个开放问题待确认
- **决定**：按 L2 默认全部通过 —— 一条资源可进多个合集、**允许跨类型**、成员**手动 `position` 排序**、封面取第一张仍 active 成员的 `thumbnailPath`（**不落封面文件**）、**软删保留成员行**（恢复后回原位）、`/collections` 进侧栏而 `/collections/:id` 不进。新表 `collections` + `collection_items`，落在现有 `library`，不新建顶层包。
- **为何**：标签不能表达顺序、也不能单独打开成一页；合集是"用户起的一组资源"，必须与系列的季/集结构严格分开。
- **不选**：智能合集/规则引擎；合集嵌套；把合集做成 `ResourceType`；合集自己的刮削、下载、连播；单独上传合集封面。
- **落点**：`docs/requirements/features/library-collections/`
- 状态：有效（需求 + L2 设计已定稿，待 L3）

### D-20260927-02 · 词表治理定稿：统计 + 删除

- 日期：2026-09-27
- 场景：`tag-category-hygiene` 轮次 1 的 6 个开放问题
- **决定**：分类 = **独立受控词表**（Q1，已拍板）；删除仍被引用的词条 = **二次确认后级联摘标**并显示引用数；管理入口 = **设置弹窗新页签**；引用统计**只算 `active`**，删除时提示「回收站中另有 N 条」；提供**「一键清理 0 引用」**（二次确认 + 单事务）；**重命名/合并 OUT，另立项**。
- **为何**：schema 已是 `ON DELETE CASCADE`，删词条天然摘标；0 引用清理是词表治理存在的理由；把回收站算进统计会给用户错误阻力；合并需定大小写/近义/冲突顺序，属另一量级。
- **不选**：禁止删除有引用的词条；管理入口放左侧类型菜单（那是库类型语义）；回收站计入统计；本刀做重命名/合并。
- **落点**：`docs/requirements/features/tag-category-hygiene.md`；路线图 MS4.1
- 状态：有效（需求已定稿，待 L2/L3）

### D-20260927-01 · 放开「常驻文件监视」禁令

- 日期：2026-09-27
- 场景：`apps/backend/app/shared/utils/fileWatcher.py` 草稿做源目录常驻监视，与基线禁止项冲突；用户明确要求保留该能力
- **决定**：放开常驻文件监视禁令。允许对**用户显式添加**的源目录用 watchdog 常驻监视，事件驱动地发现新文件并按类型入库。
- **边界（未放开）**：入库仍是**复制进 owned 包** + sha256 去重；**不把源目录登记为可反复全量重扫的库根**——本次只放开「监视」，没有放开「持久扫描根」。
- **不选**：周期性全库重扫；把源目录当库根持久化；用监视取代导入向导。
- **落点**：需求与 L2 待立项（`docs/requirements/features/<id>/`）；草稿 `shared/utils/fileWatcher.py` 尚未实现（`watchdog` 不在 `requirements.txt`）
- 状态：有效（**方向已放开，实现未立项**）

### D-20260923-06 · 磁力走本机 aria2，HTTP 仍用 httpx

- 日期：2026-09-23
- 场景：MS7 原文要贴 HTTP 和磁力都能进库；第一刀只做了直链
- **决定**：磁力用本机 `aria2c`（PATH 或 `ARIA2C_PATH`），RPC 只听 127.0.0.1。拒绝带直链参数和内网 tracker 的磁力。下完仍复制进视频库。HTTP 直链继续 httpx。
- **为何**：补上原文缺口，又不把已通的直链换成另一套引擎。
- **不选**：内嵌 rqbit；应用自己下载 aria2；HTTP 改走 aria2；磁力搜索。
- **落点**：`docs/requirements/features/download-magnet-aria2/`
- 状态：有效（已编码，待手验）

### D-20260923-05 · 抓取里程碑：图片走页面 Open Graph

- 日期：2026-09-23
- 场景：视频与番剧已能确认回填；完成定义还要求一张图
- **决定**：图片在信息栏填写公网 http(s) 页面链接，读 Open Graph 标题与封面，走同一确认队列。封面下载须过公网校验。导入图片不自动搜索。
- **为何**：没有页面地址就无法猜作品；不靠 SearXNG 也能让一张图跑通获取 → 选候选 → 标题和封面进库。
- **不选**：SearXNG、以图搜图、Pixiv 登录、AV 刮削、远程索引、适配器配置表。
- **落点**：`app/scrape/application/providers/og.py`；信息栏图片输入
- 状态：有效（已编码，待手验）

### D-20260923-04 · 设置第一刀：刮削凭证与备份

- 日期：2026-09-23
- 场景：TMDB Key 只能靠环境变量；库路径与备份无处看
- **决定**：顶栏设置两页签（刮削/系统）。凭证写入 `settings` KV，env 优先且锁定。GET 只给掩码。备份用 SQLite backup API 到 `data/backups/`。不改库根、不上扫描根。
- **为何**：先让刮削能在应用内配 Key，并有可打开的路径与可恢复副本。
- **不选**：四空页签；改 `db_path`；adapters 管理页；主题进设置。
- **落点**：`docs/requirements/features/app-settings-first/`
- 状态：有效（已编码，待手验）

### D-20260923-03 · 再归档四项已确认收口的 change

- 日期：2026-09-23
- 场景：用户确认手验门禁可收口
- **决定**：归档 `app-performance`、`image-viewer-ux`、`fix-image-consume-ui`、`metadata-panel`。查看器占位以「只盖主网格」写入主 spec。`image-consume` 去掉已被取代的左右分栏布局描述。
- **为何**：任务与代码已落地；继续留在进行中列表会挡住下一刀。
- **不选**：把仍差 Electron 手验、用户未点名的 change 一起归档。
- **落点**：`openspec/changes/archive/2026-09-23-*`；主 spec `platform-performance`、`desktop-image-viewer`、`library-resource-metadata`、`desktop-metadata-panel`
- 状态：有效

### D-20260923-02 · 下载第一刀仅 HTTP(S) 直链并复制入库

- 日期：2026-09-23
- 场景：M5 原文要双引擎+磁力，一刀做不完；入库禁止再扫根
- **决定**：`/download` 用 httpx 流式拉 HTTP(S) 视频直链，暂存后走 `ImportService` 进视频库。顶栏抽屉。拒绝磁力/私网。完成后自动入库；sha256 重复挂已有资源。
- **为何**：先闭环「贴链接 → 能播」，引擎与蜜柑后置。
- **不选**：aria2/rqbit/yt-dlp；扫描下载目录；独立下载页；完成后二次确认。
- **落点**：`docs/requirements/features/download-http-ingest/`
- 状态：有效（已编码，待手验）

### D-20260923-01 · 三个早期 change 归档进主 spec

- 日期：2026-09-23
- 场景：用户要求分析需求并对已完成项归档
- **决定**：归档 `align-resource-api`、`assemble-api-routers`、`shell-layout-selection`。任务已全部勾完，不变量已在基线。其余 change 仍有未勾手验或下一刀，不归档。
- **为何**：门禁写明这三个等用户要求后再 archive；继续留在进行中列表会和未完成需求混在一起。
- **不选**：把「代码已写、手验未做」的 change 一并归档。
- **落点**：`openspec/changes/archive/2026-09-23-*`；主 spec `library-resource-api`、`desktop-shell-selection`
- 状态：有效

### D-20260922-03 · 视频增加 B 站渠道；可手填 BV 获取元数据

- 日期：2026-09-22
- 场景：B 站下载件对不上 TMDB；标题里也常常没有 BV
- **决定**：`video` 刮削 = TMDB + B 站公开稿件（不登录）。能解析 BV/av 则直取并排在候选前。信息栏/确认队列可填 BV、av 或视频链接，非空必须能解析否则 400 且 force 新 job。无手填时仍吃标题+文件名。`anime` 不挂 B 站。无 TMDB Key 但 B 站有候选则任务成功。空 `author` 才写 UP。
- **为何**：片源经常是投稿而不是电影；用户知道 BV 时应能直接取，而不是只靠文件名碰运气。
- **不选**：应用内登录；下载原片；批量逐条填 BV；用 B 站替换 TMDB；番剧本刀出 B 站候选。
- **落点**：`docs/requirements/features/bilibili-scrape/`
- 状态：有效（已编码，待手验）

### D-20260922-02 · 简介与评价分列；确认页选封面；站点档案进 catalog

- 日期：2026-09-22
- 场景：Bangumi 确认页不能选封面；`description` 被当作品简介覆盖；已有导入封面刮削后看不见换封面
- **决定**：全类型 Resource 增加 `synopsis`（作品简介）。`description` 只表示用户评价，刮削不改。站点字段写入 `extra.catalog`（`WorkCatalog`：原名/中文名/放送日/平台/集数/站点评分/infobox）。确认弹层预览封面并勾选写入；导入/抽帧封面默认可覆盖；仅 `coverOrigin=user` 需再勾「覆盖我手动指定的封面」。封面 URL 走 `/scrape/proxy-image`，http 升 https。
- **为何**：评价与站点文案混在一起会丢笔记；lain.bgm.tv 直链在 img 里常裂且旧逻辑拒 http。
- **不选**：把 Bangumi 全部 infobox 摊成独立 SQL 列；刮削改用户评价。
- **落点**：`0011_resource_synopsis.sql`；`ScrapeConfirmQueue`；`apply_scrape_detail`
- 状态：有效（已编码）

### D-20260922-01 · 刮削渠道不唯一；番剧 Bangumi 为主、蜜柑为附加

- 日期：2026-09-22
- 场景：用户要求渠道不能唯一；蜜柑计划可作为番剧来源
- **决定**：SearchProvider 按类型返回**列表**。番剧先 Bangumi 再蜜柑（`MIKAN_BASE_URL`，默认 `https://mikanani.kas.pub`）。候选带 `source`；select 按键前缀走对应 provider。蜜柑详情优先解析 bgm.tv 再拉 Bangumi。蜜柑不写种子、不做登录、不进下载模块。
- **为何**：文件名/字幕组标题 TMDB/Bangumi 可能空，蜜柑能补发现；作品简介仍以 Bangumi 为准。
- **不选**：用蜜柑替换 Bangumi；HTML 日历当主库；应用内下磁力。
- **落点**：`providers_for` / `MikanProvider`
- 状态：有效（已编码发现层）

### D-20260919-10 · 元数据第一刀：视频+番剧直连；确认覆盖文案；导入只搜不写

- 日期：2026-09-19
- 场景：`metadata-scrape` 开放问题
- **决定**：本刀只刮 **视频（TMDB）与番剧（Bangumi）**，直连官方 API，不上 SearXNG。人选候选后**覆盖标题和简介**；标签只加不删；`coverOrigin=user` 不换封面。支持批量逐条确认/跳过。导入成功后自动 search，**不回填**，有候选再让人确认。
- **为何**：先打通确认闭环；自动写库会盖掉文件名且打爆 API。
- **不选**：本刀 AV/图片；应用内登录；导入完成即改标题。
- **落点**：`docs/requirements/features/metadata-scrape/`
- 状态：有效（已落地）

### D-20260919-09 · 抓取可演进为远程索引 + 本地落盘；爬虫不进桌面、不自动写库

- 日期：2026-09-19
- 场景：MS3 抓取定位；对照绿管「刮削库」是本地可交换包，网上刮站仍是他们的规划
- **决定**：第一刀仍是本机 FastAPI `/scrape`、用户触发、候选确认后写 Resource。适配器接口必须能换成「远程索引」（自建爬取服务或他人数据包）。远程侧只产出**可落本地的快照**（候选/封面字节），客户端再确认或只填空。爬取进程**单独部署、可定时**，不进 Electron、不与 library 同进程。禁止默认定时把结果写入用户库。
- **为何**：AV 等公开检索差，需要以后能养索引；桌面单机不能当爬虫农场；和封面 `user` 锁定、未选不写库一致。
- **不选**：第一刀就上云爬虫；客户端定时全库刮；绿管式群友 db 交换当第一刀（可作更后的数据包形态）。
- **落点**：`docs/design/00-路线图与里程碑.md` MS3；实现时 SearchProvider 本地/远程可切换
- 状态：有效（方向；未编码）

### D-20260919-08 · 查看器切图与当前列表分页同源

- 日期：2026-09-19
- 场景：`image-viewer-cross-page`
- **决定**：playlist = `useResourcePage.items` 里的图片 id。末张下一张走同一 `loadMore`（keyset 80）。不环绕、不另拉全库 id。封面入口用已绑定列表。bump 关闭查看器。
- **为何**：原先只切已加载 80 张，列表背后已能翻页。
- **不选**：beforeKey、画廊沉浸、查看器自己打 REST。
- **落点**：`docs/requirements/features/image-viewer-cross-page/`
- 状态：有效（已落地）

### D-20260919-07 · 全类型封面自动源收口；不回填

- 日期：2026-09-19
- 场景：`library-covers-complete`
- **决定**：新导入按 手选 > 旁海报/同名图 > 类型专用。EPUB 走 OPF/cover 文件名；PDF 渲首页（pypdfium2）；cbz 抽第一张图；cbr 不抽。旧库不回填。
- **为何**：九种类型卡面策略补齐，列表仍只吃 thumbnailPath。
- **不选**：刮削、3D 截图、unrar、回填。
- **落点**：`docs/requirements/features/library-covers-complete/`
- 状态：有效（已落地）

### D-20260919-05 · 音频新导入抽内嵌封面；EPUB 仍后置

- 日期：2026-09-19
- 场景：`audio-embedded-cover`
- **决定**：PATH 上 ffmpeg 抽第一条附加图流写入包内 cover，`coverOrigin=embedded`。无图/无 ffmpeg 不挡导入。不回填、不写回文件、不加 mutagen。EPUB 仍 OUT。
- **为何**：与已验过的视频抽帧同一工具；很多 mp3/flac/m4a 自带专辑图。
- **不选**：mutagen；目录当一张专辑卡；本刀做 EPUB。
- **落点**：`docs/requirements/features/audio-embedded-cover/`
- 状态：有效（已落地）

### D-20260919-04 · 图片拍摄时间：新导入探测并可手改；不回填

- 日期：2026-09-19
- 场景：`image-exif-taken`（图片深化 D1）
- **决定**：导入用 Pillow 读 EXIF 写入 `files.exif_taken_at`。信息栏可手改，PATCH 只动图片 primary。开发库不回填。不写回文件。
- **为何**：排序键 `takenAt` 已有但列空；手改覆盖错误 EXIF。
- **不选**：旧库扫描；完整 EXIF 档案；视频 creation_time。
- **落点**：`docs/requirements/features/image-exif-taken/`
- 状态：有效（已落地）

### D-20260919-03 · 封面治理：非图片可换；游戏海报优于 exe；抽帧本刀；手指定锁定

- 日期：2026-09-19
- 场景：`library-covers` 开放问题
- **决定**：除图片外均可手选封面。游戏优先级：手指定 > 目录海报 > exe 图标 > 无。视频/番剧/AV 无海报则导入时抽一帧。`.lnk` 解析到目标 exe 再抽。手指定后自动源不可覆盖。旧库不回填。音频内嵌图与 EPUB 封面不进本刀。
- **为何**：网格大量无封面；游戏安装版没有 poster 文件；用户海报不能被图标顶掉。
- **不选**：仅视频能换封面；展示时现抽图标；旧库批量补；本刀做音频/EPUB 内嵌图。
- **落点**：`docs/requirements/features/library-covers/实现方案.md`
- 状态：有效（已落地；Electron 手测待重启应用）

### D-20260919-02 · 打开所在位置是所有资源共用能力

- 日期：2026-09-19
- 场景：信息栏「打开所在位置」原先只挂在图片 / shell-open / 模型
- **决定**：定位磁盘文件与 consumeKind 无关。所有当前类型（含视频、番剧/AV、音频、回收站）信息栏常驻「打开所在位置」。路径：launch → primary → episode → extra → page，再回退其它非封面/字幕/缩略图文件。系统打开/选应用仍按类型最低消费。
- **为何**：用户要在资源管理器里找到任意作品的文件，不依赖内置播放器。
- **不选**：仅部分类型提供；把 reveal 绑死 primary。
- **落点**：`InfoPanel`；`revealPath.ts`
- 状态：有效

### D-20260919-01 · 库内搜排：LIKE；顶栏跨类型；标签多选且关键词可命中

- 日期：2026-09-19
- 场景：`library-search-sort` 开放问题
- **决定**：共用搜索=标题/作者/描述/分类/标签/文件名。顶栏跨类型搜索与类型页同一套字段。共用排序=创建/更新时间、标题、评分、体积（默认创建降序）。需求表内分类型键全部进本刀，其余后补；女优/字幕组 OUT。本刀 SQLite **LIKE**，不上 FTS5。排序与标签多选等按类型（scope）localStorage 记住。标签：**独立多选（AND）** 且关键词仍可命中标签名。回收站同一套控件只搜已删除；顶栏不搜回收站。
- **为何**：先能搜到；FTS 要同步表与分词。跨类型与本类都要。标签既要点选也要打字。
- **不选**：本刀 FTS5；只做类型页不做顶栏；只靠关键词或只靠多选之一；女优/字幕组检索。
- **落点**：`docs/requirements/features/library-search-sort/实现方案.md`
- 状态：有效（规划已记；实现待「可以按此实现」）

### D-20260918-01 · 壳层换肤：本机一份 css；顶栏主题与批量；信息栏分区

- 日期：2026-09-18
- 场景：`ui-theme-shell` 需求开放问题按默认假设收口并写 L3
- **决定**：外置主题=任意本机路径、同时仅一份 `.css`。内置 default+dark。入口=顶栏主题菜单（不做设置页）。批量删除/恢复/清空在 **ToolBar 右侧**。InfoPanel 身份/技术/编辑分区，底栏固定操作，封面仍在顶。主题选择 persist 在渲染进程 localStorage（Pinia），不写后端 settings。主进程读 css 文本注入，上限 256KiB；失败回滚上一套。
- **为何**：设置页与主题市场未做；CSP 不便 `file://` 链样式；批量条与网格抢高。
- **不选**：扫描主题目录/多文件叠加/远程皮肤；批量底悬浮或信息栏顶；主题进 API 表。
- **落点**：`docs/requirements/features/ui-theme-shell/实现方案.md`
- 状态：有效（实现中；待 Electron 手工验）

### D-20260917-03 · 游戏默认扫描登记；漫画本刀无阅读器；类型页抽离

- 日期：2026-09-17
- 场景：`library-type-platform` 详细设计评审
- **决定**：游戏默认 `storageKind=indexed`（只登记源路径与 launch，不 copytree）；向导可选 owned 复制（便携小游戏）。彻底删除 indexed **不得**删源盘。漫画本刀与小说一样系统打开，**不做**内置翻页/阅读器。类型网格只保留 `TypeBrowse`，删除按类型复制的 views。D-20260912-06 对图/视频/番剧/音频/小说/模型/漫画仍为 owned 复制；**不**恢复持久 library_roots。
- **为何**：安装版/Steam 库无法整盘复制（GRM/Bakabase/Vnite 均记路径启动）；views 克隆违反开闭；阅读器范围大。
- **不选**：游戏一律复制进库；本刀漫画 ImageViewer 翻页；为每个 type 新建 `views/*/index.vue`。
- **落点**：`docs/requirements/features/library-type-platform/实现方案.md`
- 状态：有效（规划已记；实现待 apply）

### D-20260917-02 · 库类型平台：漫画进本刀；打开方式拍板

- 日期：2026-09-17
- 场景：`library-type-platform` 开放问题
- **决定**：本切片新增 `comic`。游戏最低消费=系统打开启动文件。模型最低消费=**内置预览**。小说只做导入与列表，**内置阅读器另立项**（本刀可用系统打开作最低打开）。音频=内置 overlay，必须接成熟第三方库，不自写解码播放器。
- **为何**：漫画是独立库不能并进图片；模型预览才算能用；阅读器范围大；音频库成熟避免自研坑。
- **不选**：漫画 OUT；游戏只入库不启动；模型仅系统打开；本刀做完整阅读器；自写 audio 元素当播放器产品。
- **落点**：`docs/requirements/features/library-type-platform/`
- 状态：有效（规划已记；实现待 apply）

### D-20260917-01 · A 阶段先做「所有库最低消费」，高级后置

- 日期：2026-09-17
- 场景：对照参考产品后划路线；用户要求先导入+基本打开/读取/播放
- **决定**：媒体库 A 的第一刀是**每种库类型**都能导入（复制进库）和**最低消费**（打开、阅读、播放或启动）。抓取、下载、合集、画廊沉浸、词表治理、系列整理/规范名/字幕组/女优等 **高级能力后做**。不挡类型：图片、视频、番剧、AV、音频、小说、游戏、模型都先具备最低消费，而不是做完图视频再长期空置其它库。
- **为何**：先让所有库「能进能用」，避免一个类型做深、其它类型菜单空转。
- **不选**：A0 只做图+视频、其它类型整体推迟到 A5；先做刮削/下载再补播放。
- **落点**：`docs/product/facts.md` · `module-map.md` · `reference-landscape.md`
- 状态：有效

### D-20260915-01 · 番剧/AV 是作品级系列，不是每集一资源

- 日期：2026-09-15
- 场景：`anime-av-types` 规划；用户否定无季/集树
- **决定**：网格一部作品一张封面；信息栏展示专用档案、季/集、特典；选集或特典才播放。作品用 Resource 外壳 + `anime_profiles`/`av_profiles` + seasons/episodes/extras。菜单「番剧」，API 建议 `anime`。已有 video 不迁移。特典不计入正片集数。
- **为何**：单文件 Resource 无法同时当列表单位和播放单位；特典会污染正片集。
- **不选**：每集一条 Resource；只扩 extra JSON；本切片刮削；改旧视频类型。
- **落点**：`docs/requirements/features/anime-av-types/`
- 状态：有效（规划中）

### D-20260916-01 · 系列：规范包、整理、字幕组、女优多值、集封面双展示

- 日期：2026-09-16
- 场景：`anime-av-types` 第二轮拍板
- **决定**：来源目录只做解析；确认后写入 `SxxExx` 规范包。支持预览改映射、系列内增删集、批量规范命名。番剧字幕组（作品默认+集覆盖）+ 外挂字幕 files。AV 女优 `performers` M2M。每集可有封面；信息栏封面/序号两种列表。每集按视频探测。
- **为何**：下载源结构不一；导入会错；同一系列集封面不齐。
- **不选**：原样镜像网盘目录；女优逗号字段；只能整部删除来纠错。
- **落点**：`docs/requirements/features/anime-av-types/`
- 状态：有效（规划中）

### D-20260912-18 · 查看器只盖中间栏；信息栏动收进「更多」

- 日期：2026-09-12
- 场景：`image-viewer-ux`；用户确认可以按此实现
- **决定**：查看器只覆盖 `main`；壳右侧 InfoPanel 不卸。关闭在图右上，切张在图左右中部。底部主按钮保存/编辑/回收站，打开位置与外部应用等进「更多」。仍用 Viewer.js，封装内关过渡、少重建。
- **为何**：全窗罩难看且卡；按钮墙挤。
- **不选**：中央小弹窗；本轮换库；罩内再复制左栏。
- **落点**：`docs/requirements/features/image-viewer-ux/`
- 状态：有效（实现中）

### D-20260912-17 · 图片消费：Viewer.js 封装 + 默认/其他应用打开

- 日期：2026-09-12
- 场景：`image-consume`；用户确认可以按此实现，并要求第三方封装
- **决定**：覆盖层左元数据右看图；看图只用 Viewer.js 且**仅** `createInlineImageViewer` 可 import。默认 `openPath`，选择其他走系统打开方式。二次点击已选中图片打开。
- **为何**：S1 嵌栏 + S2 旋转/适应现成；渲染不读盘。
- **不选**：PhotoSwipe 灯箱；OpenSeadragon；业务组件直接 new Viewer。
- **落点**：`docs/requirements/features/image-consume/`
- 状态：有效（实现中）

### D-20260912-16 · 批量删除须先进入模式

- 日期：2026-09-12
- 场景：用户否定 Ctrl/Shift 随时多选
- **决定**：类型页上方「批量删除」进入选择模式；该模式下单击切换选中，再点「移入回收站」（确认）才软删。取消退出模式。平时单击只看信息栏。回收站用「批量选择」同样进模式后再恢复/彻底删除。
- **为何**：避免浏览时误选、误删。
- **不选**：默认 Ctrl/Shift 多选、有选中就出删除条。
- **落点**：`library-trash` 需求 US-T.4；`ResourceBrowser`
- 状态：有效

### D-20260912-15 · 回收站彻底删除删库内包；混排；无右键本轮

- 日期：2026-09-12
- 场景：`library-trash`；用户确认可以按此实现
- **决定**：`DELETE` 仍软删。彻底删除先删 `{library}/{type}/{id}/` 再 DROP 行，不碰导入源文件。回收站一页混排。本轮多选+批量条，不做右键菜单。清空回收站本轮做。
- **为何**：库内是副本；DELETE 语义已拍板；独立 trash 表无必要。
- **不选**：只删库留盘；按类型拆回收站页；本轮完整右键菜单。
- **落点**：`docs/requirements/features/library-trash/`
- 状态：有效（实现中）

### D-20260912-14 · 导入时在资源包内生成网格缩略图

- 日期：2026-09-12
- 场景：`grid-media-performance`；网格拉原图、窗口缩放卡
- **决定**：导入 copy/probe 后生成一档网格 WebP，路径 `{store}/{type}/{id}/thumbs/grid.webp`，`files.role=thumbnail`。列表用 `thumbnailPath`；`coverPath` 仍是原封面。无封面视频不抽帧、不造空文件。不回填旧库。失败不挡导入。
- **为何**：小图必须跟资源走，删除/回滚才干净；改 cover_path 会糊掉信息栏。
- **不选**：浏览时现算；库根 `_cache/{hash}`；根目录 `thumb.webp` 与 primary/cover 混放。
- **落点**：`grid-media-performance` 需求 §7 / 实现方案
- 状态：有效（规范已记；实现待 apply）


### D-20260912-13 · JSON 接口统一信封

- 日期：2026-09-12
- 场景：接口直接返回资源体，缺少 code/status/message
- **决定**：所有 JSON 响应包 `{ code, status, message, data }`。成功 code=0、status=success；错误 status=error 且 code=HTTP 状态。文件内容与 OpenAPI 文档不包。渲染进程 axios 解开 data。
- **为何**：调用方需要稳定判断成败和展示文案，不能每个接口形状不同。
- **不选**：HTTP 一律 200 只靠业务码；在每个路由手写信封。
- **落点**：`shared/api_envelope.py`、`infrastructure/http/client.ts`
- 状态：有效

### D-20260912-12 · 类型过滤与不变量配置化

- 日期：2026-09-12
- 场景：导入对话框 `image ? IMAGE_FILTER : VIDEO_FILTER` 硬编码
- **决定**：资源类型→扩展名/对话框过滤/中文名用映射表；字幕/封面过滤、文件角色、探测超时、清晰度/画质阈值等同理进常量模块。调用只查表或引用常量。新增类型只改映射，不改 if 链。
- **为何**：硬编码分支无法扩展模型/游戏等类型，扩展名会在前后端各写一份还容易分叉。
- **不选**：在 hook/组件里维护平行的 IMAGE_FILTER / VIDEO_FILTER。
- **落点**：`mediaTypes.ts`、`shared/media_types.py`；编码约定
- 状态：有效（已落地 `change/metadata-panel-fields`）

### D-20260912-11 · 导入探测用 Pillow/ffprobe；视频增加帧率码率画质

- 日期：2026-09-12
- 场景：`metadata-panel-fields` 轮次 3
- **决定**：新导入时图片用 Pillow 写宽高，视频用 ffprobe 写宽高/时长/帧率/码率/编码。面板只读已有列。视频面板增加帧率、码率、画质；画质用 bpp 分档（HEVC/AV1/VP9 加权），与清晰度分开。无 ffprobe 不挡导入。本切片不内嵌 FFmpeg、不回填旧库。
- **为何**：宽高时长本应入库时有；画质描述压缩程度，不能和 1080p 混成一个词。
- **不选**：打开详情再探测；用手填画质；图片显示帧率/码率。
- **落点**：`metadata-panel-fields` 需求轮次 3
- 状态：有效（已落地代码，`change/metadata-panel-fields`；桌面手工待验）

### D-20260912-10 · 元数据扩展：立刻待办、多语言字幕、原始视频名、面板不补探测

- 日期：2026-09-12
- 场景：关闭 `metadata-panel-fields` 首轮开放问题
- **决定**：资源待办增删改勾立刻请求。视频字幕允许多语言；库内名对齐**导入时原始视频文件名** + 可选语言后缀。面板只展示 `files` 已有宽高/时长，打开详情不补探测。清晰度不手填，用标准分辨率对 + 短边档位（竖屏按短边，避免只看 height 错档）。
- **为何**：待办与面板「保存」混会丢勾选；播放器按片源名匹配字幕；宽高本应在导入 probe 写入（上一轮后置，见 D-20260912-07）。
- **不选**：待办跟保存一起提交；只用 `primary.srt`；字幕沿用源文件全名；GET 时探测；手填清晰度。
- **落点**：`metadata-panel-fields` 需求轮次 2
- 状态：有效（规范已记；实现待 apply）
- 未决：导入 probe 是否并入本切片

### D-20260912-09 · 元数据面板：独立词表、点保存、5 星、弹窗换封面

- 日期：2026-09-12
- 场景：关闭 metadata-panel 开放问题
- **决定**：分类做独立词表（资源单选）。评分/分类/标签都是草稿，点保存才写库。评分 5 星（半星，×2 为 0–10）。编辑弹窗也有更换封面。删除要确认框。标签/分类保存时允许新建词条。词条治理不在本切片，沿用 `tag-category-hygiene`。
- **为何**：整理要用受控词表，但本轮只要能挂到资源上；管理页后做。即时 PATCH 与「保存」按钮冲突。
- **不选**：分类自由文本；改星/Enter 即写库；无确认删除；本切片做词表管理页。
- **落点**：`metadata-panel` 需求 §7
- 状态：有效（已落地，2026-09-12 合入 master）

### D-20260912-08 · 标签：Enter 切词，改完再一次性提交

- 日期：2026-09-12
- 场景：元数据面板标签交互
- **决定**：输入框监听 Enter 把当前文本切成一枚标签（本地草稿）。增删标签都不在每次 Enter 时请求后端；修改完成后**一次** `PATCH tagNames` 整表替换。
- **为何**：连打多个标签不应打出多次写库。
- **不选**：每按一次 Enter 就保存；每个芯片单独 POST。
- **落点**：`metadata-panel` 需求 §2/§4/§5
- 状态：有效（已落地，2026-09-12 合入 master）

### D-20260912-07 · 导入第三轮收口：多选、视频专项后置、布局封装

- 日期：2026-09-12
- 场景：用户关闭导入开放问题并要求封装目录结构
- **决定**：文件模式允许单选与多选。视频字幕/封面抽帧等专项后做，本轮视频只复制 primary。库根路径本轮不进设置。旧演示数据不管。包布局用通用 ResourcePackage（含 cover 等跨类型角色方法）+ 按类型 Layout。
- **为何**：封面等多类型都会有，不能每个导入器各写一套路径；视频复杂度单独切，避免挡住图片闭环。
- **不选**：本轮抄字幕/抽帧；本轮做 userData 库路径；导入器手写 `{type}/{id}`。
- **落点**：`import-directory-scan` 需求 §9、实现方案 packages/
- 状态：有效（已落地，2026-09-12 合入 master）

### D-20260912-06 · 导入是复制入库，前端只选路径

- 日期：2026-09-12
- 场景：导入需求第二轮（9 条口令）
- **决定**：导入向导先选类型再选文件或目录；目录只用于这一次收集来源，不登记为库根、不再扫。前端/主进程只选路径。后端负责复制进 `{library_store}/{type}/{id}/`、算元数据、写库。图片包内单文件即封面；作者/分类不建物理目录。文件复制/移动/重命名集中在共享 `FileOps`。类型用可插拔导入策略。
- **为何**：后续视频附件、其它类型不能靠「记账源路径 + 持久根」；组织信息会变，不应写死在文件夹树上。
- **不选**：持久 library_roots；只记源路径不复制；渲染进程做文件 IO；按作者/分类建库内文件夹。
- **落点**：`docs/requirements/features/import-directory-scan/`；OpenSpec 同名 change（评审中）
- 状态：有效（已落地，2026-09-12 合入 master）

### D-20260912-05 · 功能模块目录作为规划骨架

- 日期：2026-09-12
- 场景：用户口头划分功能模块
- **决定**：长期模块按 [module-map.md](module-map.md) 管理：导入、回收站、消费、画廊、分类标签、合集、系列、下载器、元数据、主题、加密资源/空间，外加已拍板的设计系统/提示词/Skill/导出。逐项验收仍要单独立项。
- **为何**：产品可扩展面大，先有一张模块地图，避免把所有能力挤进媒体库 MVP。
- **不选**：把该列表当成 v0.1 开工范围。
- **落点**：`docs/product/module-map.md`、`facts.md` §二
- 状态：有效

### D-20260912-04 · 产品分阶段：先 A 后不完整 B，远期可扩展

- 日期：2026-09-12
- 场景：口头拍板产品目标
- **决定**：先媒体库（A），再做不完整工作台（B）；B 不等于 WCH 全量。后续类型含模型（预览）、游戏（单机/Gal/黄油等）。另规划设计系统管理、AI 提示词、Skill、以及必要的导出；架构要可扩展。
- **为何**：当前要用起来的是本地图/视频库；工作台与 AI/设计资产是同一产品的后段，不能挡第一闭环。
- **不选**：一上来按完整 WCH 开工；把模型/游戏/设计系统塞进媒体库 MVP。
- **落点**：`facts.md` §二
- 状态：有效

### D-20260830-01 · L1 产品与栈定稿

- 日期：2026-08-30
- 场景：`local-resource-manager` 需求定稿
- **决定**：Electron+Vue 桌面；单一 FastAPI 进程内分 library/scrape/download；SQLite；MVP 图片+视频；扫描手动触发；下载 aria2c+rqbit；抓取自建+SearXNG。
- **为何**：单机场景不需要多后端进程抢 SQLite；引擎子进程才是隔离边界。
- **不选**：多用户、移动端、常驻文件监视、ED2K/WebDAV。
- **落点**：`docs/requirements/features/local-resource-manager.md`、`facts.md` §二
- 状态：有效（其中「不做常驻文件监视」一条已被 D-20260927-01 取代）

### D-20260912-01 · 资源 HTTP 用复数路径 + PATCH + 软删

- 日期：2026-09-12
- 场景：change `align-resource-api`（已落地代码）
- **决定**：集合 `/library/resources`；写操作为 PATCH（title/description/rating）与 DELETE=trashed；去掉公开 `/dev/seed`。
- **为何**：原先单复数路径分裂，删除绕过状态机。
- **不选**：URL `/v1`；PUT 整份 Resource；HTTP 灌演示数据。
- **落点**：`openspec/changes/archive/2026-09-23-align-resource-api/`、`facts.md` §一
- 状态：有效

### D-20260912-02 · 根应用 APIRouter 装配

- 日期：2026-09-12
- 场景：change `assemble-api-routers`（已落地代码）
- **决定**：根 FastAPI `include_router(prefix=...)`，不再 `mount` 三个子 FastAPI；library 按 health/overview/resources 拆文件。
- **为何**：同进程同库，嵌套应用只增加 OpenAPI 碎片。
- **不选**：继续 mount；本轮上 `/api/v1`。
- **落点**：`apps/backend/app/main.py`、`facts.md` §一
- 状态：有效

### D-20260912-03 · 壳层三栏 + 选中 id 进 Pinia

- 日期：2026-09-12
- 场景：change `shell-layout-selection`（已落地代码）
- **决定**：InfoPanel 挂在 App 壳；选中只存 id；详情 GET；删除成功 `clear()`。
- **为何**：浏览组件内嵌右栏导致首页/其它路由无法共享当前项。
- **不选**：嵌套 vue-router 命名视图（本轮）。
- **落点**：`App.vue`、`stores/selection.ts`、`facts.md` 已知债（列表未刷新）
- 状态：有效

---

## 已撤销 / 被取代

### D-20260830-mount · 子应用用 FastAPI.mount

- 状态：已撤销 → 被 `D-20260912-02` 取代
- 原决定（一句）：单进程用 `app.mount` 挂 scrape/download 子应用（L1/技术栈原文；实现已改为 include_router，并增加 /library）。

---

## 压缩规则

- 同一主题已有有效条：改旧条或撤销后写新条。
- 改变实现或方向：同一轮更新 `facts.md`。
- 未拍板：写 change 开放问题，不要进本文。
