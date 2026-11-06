# 模型（model） · 需求

> 类型配置：`file` 导入、`owned` 存储、3D 预览；扩展名 `gltf/glb/obj/fbx/stl`。
> 当前预览只保证 `gltf/glb`，其它格式走外部打开。

## 1. 已实现

- 文件导入、复制入库、sha256 去重。
- `gltf/glb` 内置 3D 预览（model-viewer）；其它格式外部打开。
- 合集/主页/详情统一消费入口；封面与标签/分类。
- 批量、回收站、搜索；格式搜索。

## 2. 未实现 / 待确认

| 能力 | 状态 | 说明 |
|------|------|------|
| OBJ/FBX/STL 内置预览 | 未实现 | 当前依赖外部程序 |
| 动画/材质/灯光控制 | 未实现 | 只做基础预览 |
| 缩略图/预览图生成 | 部分 | 依赖通用封面；3D 缩略图未单独做 |
| 模型元数据 | 未实现 | 三角面数、骨骼、材质列表未解析 |
| 3D 资产库/版本 | OUT（当前） | 远期方向 |

## 3. 候选

- 多格式预览、相机/光照预设。
- 模型缩略图、面数/骨骼信息。
- 与设计系统/AI 资产库的连接。

## 4. 明确不做

- 3D 编辑器、建模、材质编辑。
- 自动转换/导出格式。
- 把模型文件当普通图片塞进时间线。

## 5. 入口

- `apps/desktop/src/renderer/src/components/ModelPreviewOverlay`
- `apps/backend/app/library/domain/type_profile.py`（`MODEL_PREVIEW_EXTENSIONS`）
