# 12 · 踩坑：TypeScript 7 与 vue-tsc 不兼容

## 现象

`vue-tsc` 直接报错：

```
Error [ERR_PACKAGE_PATH_NOT_EXPORTED]: Package subpath './lib/tsc' is not defined
by "exports" in .../typescript/package.json
```

## 根因

`pnpm add -D typescript` 装了 **TS 7.0.2**（Go 原生版 tsgo，2026 新版），它移除了 JS 版 `lib/tsc` 路径。而 `vue-tsc` 3.x 仍依赖旧 TS 的内部 API（`require('typescript/lib/tsc')`），二者不兼容。

## 修复

```bash
pnpm add -D typescript@^5.9   # 降到 5.x，vue-tsc 兼容
```

## 教训

1. **装工具链别直接 latest**：`vue-tsc` / `typescript` 这类绑定型工具要看 peer 约束。装完立刻 `pnpm typecheck` 验证。
2. `pnpm peers check` 能提前暴露 peer 不匹配。
3. 新版原生 TS（tsgo）已很可用，但生态适配滞后——等 vue-tsc 跟进再升。

## 扩展阅读

### 站内（本仓）

- [24-桌面端分层与模块封装](24-桌面端分层与模块封装.md)
- [30-经验-文件规模门禁下的落点选择](30-经验-文件规模门禁下的落点选择.md)

### 站外知识

- [Vue 3 文档](https://cn.vuejs.org/guide/)
- [electron-builder 配置](https://www.electron.build/configuration)
