# 图片（image） · 需求

> 类型配置：`file` 导入、`owned` 存储、内置图片查看器；扩展名 `jpg/jpeg/png/webp/gif/bmp/heic/avif`。
> 共用能力见 [library-and-organization.md](../by-area/library-and-organization.md)、[consumption-and-players.md](../by-area/consumption-and-players.md)。

## 1. 已实现

- 文件/文件夹导入，复制入库、sha256 去重、生成 `thumbs/grid.webp`。
- 网格/Justified 时间线浏览；跨页图片查看器（上一张/下一张、翻页）。
- EXIF 拍摄时间、GPS、手动改拍摄时间；旧图回填拍摄时间/GPS。
- 时间线：按拍摄日分组、年/月/分类/标签筛选、未知时间组、计入时间线三态。
- 顶级 **GPS 地图** `/maps`：Leaflet + MarkerCluster + 内置 LayersControl，OSM/Esri 浅色/深色底图切换；地图规则独立保存/编辑/删除；聚合点使用簇内首张缩略图 + 数量角标，单点使用缩略图标记；点击聚合点查看该位置的图片缩略图，点击缩略图打开资源；右侧「城市 / 地点」面板按本地城市库分组；导入/信息栏可控制是否加入地图。
- 日期备注/地点名；保存时间线备注（见 [timeline-annotations](../features/timeline-annotations/需求.md)）。
- 分类树、标签、合集、批量打标/分类、合集导出、回收站、搜索/排序。
- 封面：图片使用主文件/缩略图；不支持用户自定义封面。

## 2. 部分实现 / 未实现

| 能力 | 状态 | 说明 |
|------|------|------|
| 旧库缩略图回填 | 部分 | 新导入有 `grid.webp`；旧资源仍可能读原图，见 `grid-media-performance` |
| EXIF 详情（机身/镜头/ISO/光圈/快门） | 已实现 | 导入探测写入 `files.exif_*`；信息栏只读；不写回文件；Pillow JPEG/能打开的 HEIC |
| 图片站点刮削 | 未实现 | 视频/番剧有抓取链路，图片刮削仍未做（N9） |
| 地图反向地理编码 | OUT（v1） | 只显示 GPS 点；地点名为手动输入 |
| 日期多备注/无照片日期备注 | OUT（v1） | 一天一条，且先给已有照片的日期 |
| 动图（GIF/动 WebP） | 已实现 | 查看器用原生 img 播放，避免 Viewer.js 停在首帧 |
| 回收站内看图 | 已实现 | 二次点击/封面仍打开查看器；叠加层标明回收站预览 |
| HEIC 失败兜底 | 已实现 | 解码失败时查看器内按钮「用外部应用打开」 |

## 2.1 优先级（2026-10-21 调整）

| 优先级 | 项目 | 说明 |
|--------|------|------|
| P1 | EXIF 只读详情（机身/镜头/ISO/光圈/快门） | **已落地**（2026-10-21）：导入写入、信息栏只读、旧图走现有回填 |
| P2 | 角色/作品/扮演者、R4 人脸 | R3/R4，需要独立数据模型 |
| P2 | 时间线详情网格视图 | **已落地**（2026-10-21）：详情页「时间线 / 网格」切换，网格用同一套保存规则铺成连续 Justified |
| P2 | 动图、HEIC 失败兜底、回收站预览 | **已落地**（2026-10-21）：GIF/WebP 原生播放；HEIC 失败可外部打开；回收站可预览 |
| P3 | 图片站点刮削 | 优先度下调，不再作为近期图片主路径 |
| P3 | 旧库缩略图回填 | 先确认老库实际表现，不阻塞新功能 |
| 候选 | CLIP/视觉近重复/OCR、双图对比、RAW/Live Photo 等 | 未拍板 |

> EXIF 详情可参考 digiKam 的**信息架构**（相机/曝光/日期/GPS 分组、只读优先），不建议复制其 C++/Qt/Exiv2 实现；本项目先用 Pillow 解析常见标签，动态范围/RAW/厂商 MakerNote 再评估 ExifTool。

## 3. 候选（未拍板）

- 画廊沉浸连看、幻灯片（N1/N15）
- 连拍/组图堆叠（N4）
- 以图搜图/CLIP、视觉近重复、OCR（N11/N12/N13）
- 双图对比、复制到剪贴板/设为壁纸（N16/N17）
- RAW、Live Photo、目录当相册（N20/N21/N22）
- 右键菜单（N5）
- 相册/漫画边界、EXIF 是否写回文件，仍需产品拍板。

## 4. 明确不做

- 像素编辑、图层、滤镜、裁切写回。
- 把漫画合并进 image 类型。
- 在线图床/社交分享/移动端。

## 5. 验收入口

- 网格/时间线：`apps/desktop/src/renderer/src/components/ResourceBrowser`
- 图片查看器：`components/ImageViewerOverlay`、`application/stores/imageViewer`
- 时间线：`components/PhotoTimeline`、`views/TimelineDetail`
- 地图：`components/PhotoMap`
- 后端：`app/library/application/photos.py`、`repositories.timeline_photos`
- 详细需求：`features/image-library-depth/`、`features/photo-timeline-map/`、`features/image-viewer-ux/`、`features/image-consume/`
