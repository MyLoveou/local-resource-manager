# 提案 · ui-theme-shell

> 与 `docs/requirements/features/ui-theme-shell/需求.md` 同范围。  
> 状态：实现中。待 Electron 手工验 T1–T5、R1。

## 为什么

壳层能用但不可换肤：颜色编译进 less/组件。用户要模块化主题，并用本机 css 切换。同时批量删除和信息栏布局难用。

## 做什么

- CSS `--sm-*` 令牌 + 内置 default/dark + 加载本机一份 css（主进程读文本注入）
- `NConfigProvider` 映射令牌；Pinia persist 本地
- 批量操作改到 ToolBar 右侧；InfoPanel 分区 + 底栏操作

不交付：设计系统资产、远程皮肤市场、overlay 精修、布局编辑器、后端表、设置页。

## 范围

| | 内容 |
|--|------|
| IN | 令牌、外置 css、批量条位置、信息栏分区 |
| OUT | 主题工坊、设置页全集、改导入/播放契约 |

## 能力

- `desktop-theme-tokens`
- `desktop-theme-load-css`
- `desktop-shell-layout`
