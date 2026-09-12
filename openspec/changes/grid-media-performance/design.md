# 设计 · grid-media-performance

> 与 `docs/requirements/features/grid-media-performance/实现方案.md` 同一套分层与文件清单。

## 上下文

- 包布局：`apps/backend/app/library/application/packages/resource_package.py`
- 导入：`import_service.py` copy → probe
- 网格：`ResourceBrowser` + `VirtualGrid` + `useElementSize`
- 基线：渲染只 HTTP；路径只在 ResourcePackage 内拼接

## 与现有架构对齐

- 沿用：library application → repository；renderer ui → domain → http
- 落点：`library` 域 + 现有 VirtualGrid
- **不**新开 thumbnail 微服务、不建 `library/_cache`
- 摸底：已读 ResourcePackage / import_service / ResourceBrowser / media_types

## 目标 / 非目标

**目标：** 导入写 `thumbs/grid.webp`；列表 `thumbnailPath`；网格用它；宽度节流。

**非目标：** 抽帧、回填、改 cover_path、重构分页。

## 方案

### 模块与文件

见实现方案「文件路径清单」。清单外默认不改。

### 数据流

1. 导入：copy → probe → 选源图 → Pillow → `put_thumbnail` → `add_file(thumbnail)`
2. 列表：仓储拼 `thumbnailPath`；网格 `thumbnailPath ?? coverPath`
3. 换封面：覆盖 `thumbs/grid.webp`
4. resize：节流 width → lanes

### 决策

| 决策 | 选择 | 为何不选 |
|------|------|----------|
| 何时生成 | 导入时 | 浏览现算首屏仍卡；与用户口令不符 |
| 路径 | `{id}/thumbs/grid.webp` | 全局 hash 缓存会孤儿；根目录 `thumb.webp` 与 cover/primary 抢名 |
| 列表字段 | 新 `thumbnailPath` | 改 cover_path 会糊信息栏 |
| 视频无封面 | 不生成 | 抽帧后置（D-20260912-07） |
| 缩放 | 节流 100–200ms | 松手才排会感觉「拖不动」 |

## 风险

| 风险 | 表现 | 缓解 |
|------|------|------|
| HEIC 解码失败 | 无小图 | 失败跳过 |
| 导入变慢 | 向导停更久 | 单档 480 边；不优化吞吐 |

## 迁移与回滚

- 无新表；先后端生成与字段，再前端改 URL 与节流
- 回滚代码即可；已生成文件可留在包内无害

## 注释与可维护性

- `put_thumbnail`、角色名、目录常量用中文注释标「仅网格、勿改 cover_path」
