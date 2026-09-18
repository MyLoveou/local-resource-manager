# 视图目录（页面 / 路由组件）

```
views/
├── Home/index.vue       # 首页概览
├── TypeBrowse/index.vue # 所有库类型网格（路由 meta.resourceType）
└── Trash/index.vue      # 回收站
```

类型页禁止再为每个 ResourceType 复制一份仅 type 字符串不同的 vue 文件。
