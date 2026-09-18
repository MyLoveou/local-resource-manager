## Purpose

壳层颜色与间距由 CSS 自定义属性表达，编译期 less 硬编码不得作为换肤唯一手段。

## ADDED Requirements

### Requirement: 设计令牌

系统 SHALL 用文档化的 `--sm-*` CSS 变量驱动壳层主色、背景、文字、边框。naive-ui MUST 经 `NConfigProvider` 映射同一套变量。组件 MUST NOT 以无法被主题 css 覆盖的硬编码作为本切片覆盖面（三栏壳、顶栏、InfoPanel）的唯一着色手段。

#### Scenario: 改令牌即改壳层

- **WHEN** 当前主题 css 改变 `--` 主色与背景变量并生效
- **THEN** 顶栏、侧栏、页面背景可见变化，无需重编应用
