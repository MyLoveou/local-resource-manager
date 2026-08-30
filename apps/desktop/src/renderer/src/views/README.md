# 视图目录（页面 / 路由组件）

每个视图一个目录，组件文件用 `index.vue`。

```
views/
├── Home/index.vue          # 路由页
├── Image/
│   ├── index.vue           # 路由页
│   ├── components/         # 仅该页使用的子组件（第 2 级）
│   └── hooks/              # 仅该页使用的逻辑
└── Video/…（同 Image）
```

规则：
- **目录深度封顶 2~3 级**；超过 3 级说明该拆功能模块
- 页面私有的子组件/逻辑放页内 `components/`、`hooks/`，**不**污染全局目录
- 跨页面复用的组件 → 顶层 `components/`；通用逻辑 → 顶层 `hooks/`
- 目录内可加 `index.ts` barrel 导出，外部通过目录名引用
