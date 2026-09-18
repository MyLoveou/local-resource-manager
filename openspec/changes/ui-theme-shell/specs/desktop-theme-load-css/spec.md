## Purpose

用户可选择本机 css 文件作为当前主题；失败时保持上一可用主题。

## ADDED Requirements

### Requirement: 加载本机主题文件

系统 SHALL 允许用户选择本地一份 `.css` 并应用到渲染进程（主进程读文本，渲染注入 style）。无效文件 MUST NOT 导致白屏。所选主题在重启后 MUST 仍能恢复（Pinia persist / localStorage；不写后端）。

#### Scenario: 选择合法 css

- **WHEN** 用户选中符合令牌约定的 css 文件
- **THEN** 壳层使用该文件中的变量

#### Scenario: 文件不可读

- **WHEN** 路径不存在或内容无法应用
- **THEN** 提示失败并保持当前已成功主题
