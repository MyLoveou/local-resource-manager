## Purpose

侧栏与类型页由注册表生成。网格只展示该 type 的作品卡。类型浏览 MUST 使用单一页面组件，MUST NOT 为每种 ResourceType 复制一份仅 type 字符串不同的 vue 文件。

## ADDED Requirements

### Requirement: 类型页展示

系统 SHALL 为 audio/novel/game/model/comic 以及现有 image/video/anime/av 提供相同网格、信息栏、回收站行为，路由由 TypeProfile 生成并挂到同一 TypeBrowse。列表 MUST 只含该 type。

#### Scenario: 空列表

- **WHEN** GET `type=audio|novel|game|model|comic` 且无数据
- **THEN** 200 空 items
- **对应测试**：`tests.md` T6

#### Scenario: 导入后网格可见

- **WHEN** 导入成功并打开对应路由
- **THEN** 可见作品卡；单击只选中
- **对应测试**：`tests.md` T7

#### Scenario: 无克隆类型页

- **WHEN** 检视 `apps/desktop/src/renderer/src/views`
- **THEN** 不存在仅 ResourceBrowser+type 不同的 Image/Video/Anime/AV 分目录实现；类型网格只有 TypeBrowse
- **对应测试**：`tests.md` T1
