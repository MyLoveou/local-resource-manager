## Purpose

类型页提供搜索与排序控件；选项随 TypeProfile 变化，不复制页面。

## ADDED Requirements

### Requirement: 控件随类型变化

系统 SHALL 在类型浏览壳上提供搜索与排序入口。类型相关选项 MUST 随当前 type 变化；共用选项 MUST 在所有启用类型上可用。

#### Scenario: 从视频切到小说

- **WHEN** 用户从视频页转到小说页
- **THEN** 视频专用排序项不再出现，共用排序项仍在
