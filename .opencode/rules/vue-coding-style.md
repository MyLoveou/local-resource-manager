# Vue Coding Style

> Extends `typescript-coding-style` and `common-coding-style`.

## SFC structure

Prefer `<script setup lang="ts">` with ordered blocks: script → template → style.

```vue
<script setup lang="ts">
// imports, props, composables, logic
</script>

<template>...</template>

<style scoped>...</style>
```

## Naming

- Components: `PascalCase` file and symbol (`UserCard.vue`)
- Composables: `useCamelCase` (`useUserList.ts`)
- Props / emits: `camelCase` in script; kebab-case in template attributes when needed

## File layout

```
src/
├── components/
├── views/ or pages/
├── composables/
├── stores/        # Pinia
├── api/
└── router/
```

## 组合

- 模板只展示。校验、权限、计算放在 composable 调用的功能或算法模块
- 样式用 `scoped` 或 CSS modules
- 用 composable，不用 mixin
- 单文件过大就拆。页面是组合根

