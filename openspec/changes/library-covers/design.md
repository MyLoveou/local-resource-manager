# 设计 · library-covers（L3 HOW）

与 `docs/requirements/features/library-covers/实现方案.md` **同一套文件清单与锁定表**。L2 模型见同目录 `设计.md`。

## 上下文

- 换封面已有 `POST /cover` + `put_cover`，UI 写死视频。  
- 游戏 `find_folder_cover` 已有。  
- 系列把 `cover_path` 指到作品 `/content`（视频流），列表又禁用该回退，故无卡面。  
- 抽帧/图标必须在后端 ingest。

## 与现有架构对齐

沿用 library application + ResourcePackage。新建 `application/covers/`，不新进程。

## 目标 / 非目标

**目标：** 新导入可见封面；非图片可换且锁定。  
**非目标：** 回填、刮削、音频/EPUB、改播放器。

## 方案

见中文实现方案 §2–§7。

## 风险 / 迁移

无新 migration。回滚：去掉 covers 包与 pefile，封面行可留。
