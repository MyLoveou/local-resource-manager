# 设计 · section-visibility

> 写 HOW（L3 施工）。L2 模型/交互/模块见 `docs/requirements/features/section-visibility/设计.md`。
> 与 `docs/requirements/features/section-visibility/实现方案.md` 同一套文件清单。

## 上下文

- 现状：菜单由 `domain/menu.ts` 的 `menuFromRoutes(routes)` 生成，`App.vue` 消费；类型路由由 `domain/libraryTypes.ts` 的 `TYPE_PROFILES` 生成；导入类型列表在 `domain/mediaTypes.ts`；首页概览卡在 `views/Home/index.vue`；路由守卫在 `router/index.ts`（仅日志）
- 基线 / 约定：前端四层 `ui/views/components → application → domain → infrastructure`；HTTP 只在 `infrastructure/http`；常量集中在 `domain/*`
- 无后端/DB/API 变更

## 与现有架构对齐

- 沿用分层：domain（配置 + 纯谓词）→ ui/views 与 infrastructure/router 消费
- 落在现有模块：`domain/visibility.ts`（新）、`domain/menu.ts`、`domain/mediaTypes.ts`、`App.vue`、`router/index.ts`、`views/Home/index.vue`
- **不**新开的分层/目录：不建 feature-flag 引擎、不建 settings 存储、不新增 store
- 摸底证据：已读 `App.vue`、`domain/menu.ts`、`router/route.ts`、`router/index.ts`、`domain/mediaTypes.ts`、`views/Home/index.vue`、`components/ImportWizard/index.vue`

## 目标 / 非目标

**目标：**

- 单点配置 + 纯谓词；菜单/路由/导入/首页四入口一致
- 空配置零行为变化；未知 key 静默忽略；首页不可隐藏

**非目标：**

- 不改搜索、合集混排、最近消费列表
- 不改资源类型定义、后端、数据库
- 不做运行时切换/设置 UI
- 不重构无关模块

## 方案

### 模块与文件

| 路径 | 职责 | 新建/改 |
|------|------|---------|
| `apps/desktop/src/renderer/src/domain/visibility.ts` | `HIDDEN_SECTIONS` + `isSectionHidden(path)` | 新建 |
| `apps/desktop/src/renderer/src/domain/menu.ts` | `menuFromRoutes(routes, isHidden?)` | 改 |
| `apps/desktop/src/renderer/src/App.vue` | 注入谓词（组合根） | 改 |
| `apps/desktop/src/renderer/src/domain/mediaTypes.ts` | `ENABLED_IMPORT_TYPES` 排除隐藏类型 | 改 |
| `apps/desktop/src/renderer/src/router/index.ts` | 守卫重定向 | 改 |
| `apps/desktop/src/renderer/src/views/Home/index.vue` | 概览卡过滤 + 空态判定 | 改 |

清单外的文件默认不改。

### 组合根

- 组合于：`App.vue`（菜单）、`router/index.ts`（导航）、`Home`/`ImportWizard`（各自消费 domain 谓词）
- 切片路径：算法 `domain/visibility.ts`；功能 `router/index.ts`；UI `menu.ts` 注入 + `Home` + `mediaTypes.ts`
- 最后一步：四入口接到页面并跑主路径，禁止只合算法

### 数据流

1. 入口：应用启动 / 地址栏导航 / 导入向导打开 / 首页加载
2. 校验：`isSectionHidden(path)`（纯函数；`/` → false）
3. 持久化：无
4. 返回与前端状态：菜单不渲染；守卫 `return { path: '/' }`；导入列表过滤；首页卡过滤（可见卡为空的类型不计入空态判定）

### 决策

| 决策 | 选择 | 为何不选备选 |
|------|------|----------------|
| 配置形态 | TS 常量 + 纯谓词 | 不选设置页/环境变量：需求明确代码配置，避免新增持久化与 API |
| key 粒度 | 路由 path（含子路径前缀） | 不选类型枚举：合集/回收站等非类型分区也要覆盖；不选通配符：过度设计 |
| 菜单过滤 | 谓词注入 `menuFromRoutes` | 不选在 menu.ts 直接读配置：保持 domain 函数可测、App.vue 为组合根 |
| 首页 | 只过滤统计卡，最近消费不过滤 | 点击隐藏类型的消费记录由守卫自然回首页，避免额外过滤逻辑 |
| 搜索/合集 | 不过滤 | 前端过滤会破坏分页总数；后端过滤需新契约，超出 v1 |

## 风险

| 风险 | 表现 | 缓解 |
|------|------|------|
| 首页不可隐藏规则被绕过 | 配 `'/'` 导致重定向循环 | 谓词显式忽略 `/`；守卫仅重定向非 `/` |
| 隐藏子路径遗漏 | `#/collections/1` 仍可打开 | 前缀规则（`key + '/'`）覆盖 |
| 导入类型与菜单不一致 | 菜单隐藏但导入仍出现 | 两处共用 `isSectionHidden(profile.routePath)` |

## 迁移与回滚

- 发布顺序：前端一次提交（无库表/API）
- 回滚：清空 `HIDDEN_SECTIONS` 即可恢复全部入口

## 注释与可维护性

- `visibility.ts` 顶部中文注释说明：改清单即隐藏、`/` 不可隐藏、前缀规则
- `menu.ts` 注明谓词可选，默认不过滤（保持旧调用兼容）
