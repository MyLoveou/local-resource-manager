## Purpose

桌面资源网格用列表提供的缩略图地址显示卡片图，避免把原图解码进每张卡片。窗口宽度变化时节流后再重算列数，避免拖动过程中每像素全量重排。

## ADDED Requirements

### Requirement: 网格优先使用缩略图地址

系统 SHALL 在虚拟网格卡片上优先使用资源的 `thumbnailPath` 作为图片 URL；仅当该字段为空时回退 `coverPath`。信息栏封面 SHALL 仍使用 `coverPath`。

#### Scenario: 有缩略图的卡片

- **WHEN** 列表项同时有 `thumbnailPath` 与 `coverPath`
- **THEN** 网格卡片 img 的地址来自 `thumbnailPath`
- **对应测试**：`tests.md` T6

#### Scenario: 旧数据回退

- **WHEN** 列表项没有 `thumbnailPath` 但有 `coverPath`
- **THEN** 网格卡片仍能显示封面，不出现空白闪烁导致整页无法渲染
- **对应测试**：`tests.md` T7

### Requirement: 窗口宽度节流后重算网格列

系统 SHALL 不在窗口宽度的每一个像素变化上同步重算虚拟列；SHALL 在约 100–200ms 的节流或防抖之后再更新列宽与卡片尺寸。

#### Scenario: 连续缩放不每帧改 lanes

- **WHEN** 网格容器宽度在短时间连续变化
- **THEN** 列数/卡片宽度的更新次数明显少于宽度采样次数（节流生效）
- **对应测试**：`tests.md` T8
