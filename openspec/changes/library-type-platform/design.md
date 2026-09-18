# 设计 · library-type-platform

> **详细施工图**以 `docs/requirements/features/library-type-platform/实现方案.md` 为准。本文只留架构摘要。

## 上下文

不新开 FastAPI、不重写 series_plan、不自写解码。领域：Work 聚合 + TypeProfile 目录 + Ingest 策略 + 桌面单一 TypeBrowse。

## 锁定

- 音频：howler.js
- 模型：@google/model-viewer（gltf/glb）
- 漫画：本刀 **shell-open**，无阅读器
- 游戏：默认 **indexed**；可选 owned 复制
- Player：consumeKind
- 类型页：只保留 `views/TypeBrowse`

## 模块与文件

见实现方案 §8。

## 数据流

入库 §5（含 StorageKind）；消费 §6。

## 决策

D-20260917-01/02/**03**；D-20260912-06 对媒体 owned 仍有效，游戏为例外。
