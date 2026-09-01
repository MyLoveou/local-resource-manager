# 16 · 踩坑：Vue 模板引用了未导入的组件

## 现象

- `pnpm build` / `pnpm typecheck` **都通过**
- 运行时浏览器/DevTools 报警告：`Failed to resolve component: MenuBar`（组件不渲染/报错）

## 根因

Vue SFC 模板里写了 `<MenuBar />`，但 `<script setup>` 里**没 import**。Vue 编译器把模板中的标签当作运行时组件名解析，**构建不报错，只在运行时报**——typecheck 抓不到（除非启用严格模板检查）。

## 修复

```vue
<script setup lang="ts">
import MenuBar from '@/ui/layouts/MenuBar/index.vue'   // 必须显式导入
import ToolBar from '@/ui/layouts/ToolBar/index.vue'
</script>
<template>
  <MenuBar />
  <ToolBar />
</template>
```

## 教训

1. **构建/类型检查通过 ≠ 运行正常**——模板组件解析是运行时行为。
2. 排查：打开 DevTools Console，`Failed to resolve component` 直接点名。
3. 此项目踩过两次：占位组件目录是空的 + 组件未 import。
4. 通用组件建议注册为全局组件或统一 barrel 导出，减少遗漏。
