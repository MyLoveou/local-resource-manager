# L1 需求文档

需求沉淀维护的定稿需求。文件名：`<feature-id>.md`，文首含状态（草案 / 评审中 / 已定稿）。

## local-resource-manager（**已定稿**）

| 文档 | 内容 |
|------|------|
| `local-resource-manager.md` | 主需求：背景/范围/决策/开放问题 |
| `lrm-modules.md` | 模块拆解（M0–M6）与边界异常 |
| `lrm-ui.md` | 页面结构（三栏布局） |
| `lrm-tech-stack.md` | 技术栈决策（三进程架构、双服务、双引擎） |

## tag-category-hygiene（**草案**）

> LRM **P1 增量**：标签/分类词表统计与删除。依赖 M4 打标能力；实现排在 MS4.1，不挡当前浏览闭环。

| 文档 | 内容 |
|------|------|
| `tag-category-hygiene.md` | 词表膨胀治理：统计、删除、与 M4 边界、开放问题 |

## work-consumption-hub（**草案**）

> LRM 增量 Feature：工作上下文 + 消费渠道。依赖 LRM M0–M6。

| 文档 | 内容 |
|------|------|
| `work-consumption-hub.md` | 主需求：定位变更、核心概念、范围、开放问题 |
| `wch-modules.md` | 增量模块拆解（M7–M10）与 API 草案 |
| `wch-ui.md` | UI 增量：工作区面板、首页概览、消费渠道设置 |
