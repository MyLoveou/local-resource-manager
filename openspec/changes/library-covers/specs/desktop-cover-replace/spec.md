## Purpose

信息栏按 TypeProfile 提供更换封面，不按 consumeKind 写死视频。

## ADDED Requirements

### Requirement: 更换封面入口

系统 SHALL 对 `allowsUserCover` 为真的类型在信息栏或编辑弹窗提供更换封面。图片 MUST 不提供。

#### Scenario: 音频

- **WHEN** 用户选中音频
- **THEN** 可以使用更换封面

#### Scenario: 图片

- **WHEN** 用户选中图片
- **THEN** 界面不出现更换封面
