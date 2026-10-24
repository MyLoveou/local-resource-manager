<p align="center">
  <img src="apps/desktop/build/icon.png" width="96" alt="Source Manager">
</p>

<h1 align="center">Source Manager · 本地资源管理器</h1>

<p align="center">
  把散落在硬盘里的图片、视频、番剧、音频、小说、漫画、游戏和 3D 模型，<br>
  整理成一个可搜索、可浏览、可继续消费的本地资源库。
</p>

<p align="center">
  <a href="https://github.com/MyLoveou/local-resource-manager/releases/latest">下载最新版本</a>
  ·
  <a href="docs/requirements/features/">功能文档</a>
  ·
  <a href="docs/product/facts.md">产品设计</a>
</p>

---

## 这是什么

Source Manager 是一个 **Windows 本地优先的桌面资源管理器**。

它不把文件上传到云端，也不依赖在线图库。你选择文件和目录后，应用会把资源复制进受管理的本地库，建立索引、缩略图和元数据，然后提供搜索、筛选、时间线、地图、合集、角色、播放和 AI 检索。

它适合：

- 图片和照片很多，想按时间、地点、人物、角色、标签整理的人
- 同时管理视频、番剧、音频、小说、漫画、游戏和模型的人
- 希望数据留在本机，不想把私人图库交给在线服务的人
- 需要批量打标、分类、合集和回收站工作流的人

它不试图替代：

- 在线视频平台
- 多用户媒体服务器
- 自带下载器
- 云端同步服务

## 提供哪些功能

### 多类型资源库

- 图片、视频、番剧/AV、音频、小说、漫画、游戏、3D 模型等类型
- 每种类型独立分类树、标签和筛选
- 统一资源库、首页概览和回收站
- 批量选择、批量打标、批量分类、批量加入合集
- 软删除、恢复和彻底删除

### 导入与整理

- 文件或目录导入，复制进受管理资源库
- SHA-256 去重与文件完整性校验
- 自动生成网格缩略图
- 图片 EXIF 拍摄时间、GPS、相机/镜头/ISO/光圈/快门
- 视频 ffprobe 宽高、时长、编码、拍摄时间与 GPS
- 封面选择：内嵌封面、视频抽帧、图片、EPUB/PDF/cbz、可执行文件
- 监视源目录，新增文件自动导入
- 导入向导：类型、分类、时间线、地图可见性

### 浏览与消费

- 虚拟网格与触底分页
- 图片 Justified 照片流
- 照片时间线：按年/月/日分组，支持未知时间
- 地图：Leaflet + MarkerCluster，按 GPS 聚类
- 图片查看器：缩放、切换、跨页看图、找相似
- 视频/番剧选集播放
- 音频播放
- 小说/漫画/PDF/EPUB 系统打开
- 3D 模型 glTF/GLB 预览
- 打开所在位置、用其他程序打开

### 组织维度

- 标签、分类、评分、简介、待办
- 角色与作品
- 扮演者/人物
- 合集：跨类型、手动排序、导出
- 保存的时间线/筛选器
- 日期备注与时间线备注
- 按角色、扮演者、分类、标签、日期筛选

### 元数据与刮削

- 视频：TMDB
- 番剧：Bangumi + 蜜柑发现
- 视频补充：B 站公开稿件
- 图片页面：Open Graph 信息
- 抓取候选确认后写入，不静默覆盖已有元数据
- 可配置抓取凭证和监视目录

### 本地 AI 检索

AI 能力全部在本机运行，模型可选安装，不捆绑在安装包里。

- **文搜图**：中文 CLIP 本地向量检索
- **图搜图**：库内图片相似、近似重复
- **外部图片**：文件选择、拖放、剪贴板粘贴
- **图文融合**：以图为基础，叠加文字条件
- **检索解释**：显示查询解析、硬条件、CLIP 分数、dHash 和匹配原因
- **VLM 文案**：可选 Ollama，生成 caption、短标题、标签、场景、动作、颜色、服饰和 OCR
- **动漫兜底**：可选 WD14，通用 VLM 对动漫图重复失败时生成标签
- **模型管理**：检测 Ollama、选择程序、启动、下载/切换视觉模型、显示视觉能力
- **排序反馈**：最低相似度、相关/不相关反馈、探索展示
- **索引维护**：增量索引、自动补索引、全量重建、待索引提示
- **任务与日志**：任务历史、失败归档、按日日志、失败原因
- **AI 建议**：未落地标签，以及匹配现有角色/扮演者/合集

AI 模型不随安装包分发。首次使用可在 AI 中心下载中文 CLIP；VLM 和 WD14 需要单独安装或下载。

### 设置、更新与发布

- 本地路径、日志目录、备份目录配置
- 主题与界面密度
- 检查更新、下载更新、重启安装
- Windows x64 NSIS 安装包与 zip
- 自动更新：electron-updater + GitHub Releases
- 发布前类型检查、lint、测试、打包、夹具校验

## 界面结构

```text
浏览：首页 / 资源库
视图：时间线 / 地图
组织：角色 / 扮演者 / 合集
工具：AI 中心 / 回收站
```

顶部提供导入、整理、AI、设置和 AI 状态；右侧 Inspector 显示资源详情、关联和 AI 信息；底部批量条处理选中资源。

## 本地优先与隐私

- 资源库、缩略图、索引和 AI 向量默认保存在本机
- 图片、文案和查询不会上传到云端
- 不需要账号
- 不含遥测
- 地图底图可选在线 OSM/Esri，会暴露当前地图瓦片请求，但不上传照片或数据库
- 刮削只把用户选择的公开信息请求发给对应服务

默认数据位置：

- 开发：`apps/backend/data`
- 安装版：`%APPDATA%\local-resource-manager`
- 日志：`%APPDATA%\local-resource-manager\logs`

## 快速开始

环境要求：

- Windows x64
- Node.js 24+
- pnpm 11+
- Python 3.14（仅源码运行或重新打包后端时需要）

```bash
# 安装前端依赖
pnpm install

# 首次安装后端依赖
pnpm backend:install

# 启动桌面端，自动拉起后端
pnpm dev

# 只启动后端（本机排障）
pnpm backend:start
```

检查：

```bash
pnpm --filter desktop typecheck
pnpm --filter desktop lint
pnpm --filter desktop build

apps/backend/.venv/Scripts/python -m pytest -q apps/backend/tests
```

构建 Windows 安装包：

```bash
pnpm release:win
```

正式发布前需要更新版本号和 `docs/releases/vX.Y.Z.md`，然后：

```bash
pnpm release:publish
```

`release:publish` 会校验版本、说明、工作区和 tag，再推送并触发 GitHub Actions 构建 Release。

## 技术栈

| 模块 | 技术 | 位置 |
|------|------|------|
| 桌面端 | Electron 44 + Vue 3 + Vite 8 + TypeScript | `apps/desktop` |
| 后端 | Python FastAPI + SQLAlchemy async | `apps/backend` |
| 数据库 | SQLite（WAL + 迁移） | `apps/backend/app/shared/db` |
| 文件监视 | watchdog + 事件桥 | `apps/backend/app/shared/utils/watch_*` |
| AI | ONNX Runtime + Chinese-CLIP + YOLOv8n + 可选 Ollama/WD14 | `apps/backend/app/ai` |
| 地图 | Leaflet + MarkerCluster | `apps/desktop/src/renderer/src` |

更详细的技术说明：

- 产品事实：`docs/product/facts.md`
- 决策记忆：`docs/product/decisions.md`
- 功能需求：`docs/requirements/features/`
- 架构与经验：`docs/经验总结/`
- 发布流程：`docs/requirements/by-area/release-and-quality.md`

## 当前状态与限制

- 目前主要面向 Windows x64；macOS/Linux 未提供正式包
- 安装包未做代码签名，Windows SmartScreen 可能提示
- 下载功能不自建，统一交给第三方下载器；应用只负责监视下载目录并导入
- AI 模型不随安装包提供，首次使用需要下载模型
- 通用 VLM 对部分动漫图片可能触发重复输出中止；当前可用 WD14 兜底
- 训练型 LTR、OpenAI-compatible 的完整 UI 配置仍在后续计划
- 小说/漫画内置阅读器、游戏启动增强、部分类型深度能力仍在逐步补齐
- 1 万/5 万资源的性能基准放在后续优化，不在当前首版范围

## 参与开发

- 新需求先写需求与设计，再进入编码
- 功能文档放在 `docs/requirements/features/<feature>/`
- 架构取舍写入 `docs/design/adr/`
- 提交信息使用 `feat` / `fix` / `docs` / `chore` 前缀
- 发布前必须通过 typecheck、lint、pytest、打包与 release verify

## 相关链接

- [最新 Release](https://github.com/MyLoveou/local-resource-manager/releases/latest)
- [功能需求目录](docs/requirements/features/)
- [产品事实基线](docs/product/facts.md)
- [发布与质量](docs/requirements/by-area/release-and-quality.md)
