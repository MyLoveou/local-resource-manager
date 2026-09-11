# Hooks 目录（组合式函数）

跨组件复用的逻辑。命名 `useXxx`，可组合 @vueuse/core、motion、naive-ui API。

规划 hooks：
- `useResourcePage.ts` — 资源分页（首屏 + 触底加载）
- `useVirtualList.ts` — 虚拟滚动封装
- `useSearch.ts` — 搜索/排序状态
- `useApi.ts` — axios 封装（基础 URL、token、错误处理）
- `useToast.ts` — 消息提示封装
- `usePolling.ts` — 轮询（下载进度、抓取进度）
