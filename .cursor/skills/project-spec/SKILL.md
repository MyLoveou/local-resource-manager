---
name: project-spec
description: >-
  本仓库自定义的规范驱动工作流。复杂需求先过设计阶段；实现可按 UI/功能/算法
  拆分、在页面（组合根）组装。触发：project-spec、先出方案、先设计、怎么拆、组合实现。
origin: 项目规范
---

# 项目规范工作流（project-spec）

这是**本仓库自己的 Skill**，不要和官方 `openspec` 插件 Skill 混名。业务仓变更仍用 CLI `@fission-ai/openspec`（`openspec --help`）。规则见 `rules/common/openspec.md`。

**本 Skill 按阶段走，复杂需求禁止从需求直接跳到编码或只写文件清单：**

1. **项目规范（L1）**：范围、验收、开放问题 → `需求.md`
2. **能力设计（L2）**：原则、模型、交互、模块、拆分（含 UI/功能/算法组合）、抽象 → `设计.md`
3. **实现方案（L3）**：路径清单、数据流、纵向步骤 → `实现方案.md`
4. **项目架构**：落在现有分层上，禁止平行另起一套

跨会话另有两份**项目级**真源（不是某个 change 的手记）：

- **事实基线** `docs/product/facts.md`：项目**实现**（现状）+ 项目**方向**（往哪走）
- **决策记忆** `docs/product/decisions.md`：每次拍板的压缩条目，换会话先读最近条

中文需求多轮仍用 `requirements-refinement`；**文档落点与本 Skill 是同一套目录**。OpenSpec change 是 CLI 执行/归档载体，不得与中文目录各写一套范围或架构。

## 何时用

| 意图 | 动作 |
|------|------|
| 新能力 / 大改 / 先出方案 | **propose**：先 L1，复杂则 **L2 设计 STOP**，确认后再 L3 |
| 复杂需求：模型/交互/模块/怎么拆 | **设计阶段**（只写 `设计.md`，不写业务代码） |
| 可以按方案实现 | **apply** |
| 归档进主 spec | **archive**（须确认） |
| 换会话继续上次 | 读 change 的 `handoff.md` 与能力目录 `handoff.md` 再 apply |
| 还没有 `openspec/` | 在**业务仓** `openspec init`，再拷本目录 `templates/` 的加厚模板作对照 |

小 bug、改样式、先做视觉方向：**不要走本 Skill 全量 propose**，改走特化 Skill（见下表）。

## 场景分流

| 场景 | Skill | 典型口令 |
|------|--------|----------|
| 新能力 / 改契约 / 大改流程 | 本 Skill：L1 → **L2 设计** → L3 → apply | 先出方案、新功能、先设计、怎么拆模块 |
| 现有行为错了 | `project-spec-fix` | 修 bug、复现、报错 |
| 只改观感布局 | `project-spec-style` | 改样式、间距、对齐 |
| 只定视觉方向（不是能力设计） | `project-spec-design` | UI 更好看、改这一页观感 |

吃不准时：会改 API/表/主流程/模块边界 → 本 Skill（复杂先 L2）；只是坏了 → fix；只是难看 → style；只要像素方向 → `project-spec-design`。

界面工艺不另开全量 propose。定方向仍是 `project-spec-design`，新界面的方向方法用 `oil-ui`，只改样式仍是 `project-spec-style`。约束见 `baseline-ui`、`better-layout`、`better-typography`、`better-ui`、`fixing-accessibility`、`fixing-motion-performance`。按本产品证据审计且先不改代码用 `improve-ui`。组件变体画布和自由比较画布用 `component-canvas`、`create-canvas`，默认不进产品导航。

## 目录（业务仓，与 requirements-refinement 共用）

```
docs/
  product/facts.md                    # 项目事实基线：实现 + 方向（G0 必读）
  product/decisions.md                # 压缩决策记忆（跨会话）
  product/baseline.md                 # 浓缩约束副本（可与 openspec/baseline.md 互链）
  standards/                          # 项目规范：动工门禁、编码约定、审查
  requirements/features/<id>/
    需求.md                           # L1
    设计.md                           # L2 能力设计（复杂需求必做）
    实现方案.md                       # L3 施工
    handoff.md                        # 跨会话（可选，与 change 内 handoff 对齐）
  requirements/features/<id>-track.md # Track 参考（可选）
  design/03-API设计.md                # 契约（定稿后同步）
  design/02-数据模型.md
  design/adr/                         # 架构决策
  UI/                                 # 跨功能界面规格

openspec/
  baseline.md                         # 浓缩基线（G0）
  specs/                              # 主 spec（归档后）
  changes/<name>/
    proposal.md                       # 与 需求.md 对齐
    design.md                         # L3 HOW，与 实现方案.md 对齐；L2 以中文 设计.md 为准
    tasks.md
    tests.md
    handoff.md
    specs/<capability>/spec.md
```

`<id>` 与 change 名尽量同一 kebab-case。  
加厚模板：同目录 [templates/](templates/)；L1/L2/L3 对照 `templates/docs-requirements-feature.md`、`docs-feature-design.md`、`docs-implementation-plan.md`。

无 `openspec/` 的仓：只维护 `docs/requirements/features/<id>/`，技术方案走 `plan-workflow`，**架构章节不可省略**。

## 项目事实基线与决策记忆

| 文件 | 写什么 | 不写什么 |
|------|--------|----------|
| `docs/product/facts.md` | 已确认的**实现现状**与**产品/技术方向** | 单功能验收、任务进度、聊天记录 |
| `docs/product/decisions.md` | 每次拍板：决定 / 为何 / 不选（≤8 行） | 长篇 ADR、未决开放问题 |
| 浓缩 `baseline.md` | 不变量、禁止、验收命令 | 实现细节（指向 facts） |
| change `handoff.md` | 本 change 做到哪、下一步 | 全项目方向 |

没有 `facts.md`：按模板起草实现+方向 → 标「待你确认」→ **STOP**（与缺浓缩基线同等）。  
会话中用户拍板（「就用 A」「方向改成…」）：追加 `decisions.md` 一条；若改实现或方向，**同一轮**改 `facts.md`。未拍板不进决策文件。

## 项目规范（propose 必做）

动手前读齐，缺则起草并 STOP：

- `docs/product/facts.md`（实现 + 方向）
- `docs/product/decisions.md` 最近有效条目
- `openspec/baseline.md` 或 `docs/product/baseline.md`
- `docs/standards/版本与动工门禁.md`（L1–L3）
- 已有 `docs/standards/coding-conventions.md` / 审查约定（若有）
- 本能力 `需求.md`：IN/OUT、验收、开放问题；与 **facts 方向** / 能力文档冲突先问

禁止：把网上通用清单或未确认推测写成已确认规范或已确认实现。

## 何时必须进入设计阶段（L2）

命中任一，**禁止**从 `需求.md` 直接写 `实现方案.md` 或 apply：

- 新实体 / 表 / 状态机 / 对外契约
- 跨 2+ 模块或前后端
- 多角色或新主交互
- 要新抽象、改分层、拆多个子能力、或 **UI/功能/算法分开提供再在页面组合**
- 预估 >1 PR 或跨层 >3 文件
- 用户说「复杂」「先设计」「模型怎么定」「模块怎么分」「怎么拆」

未命中可跳过 L2，须在 `实现方案.md` 文首写一句理由。

## 设计阶段（L2，复杂需求必做）

本轮只产出 `docs/requirements/features/<id>/设计.md`（模板：[feature-design.md](templates/feature-design.md) / `templates/docs-feature-design.md`）。**禁止**写业务代码，**禁止**用文件清单冒充设计。

必须写清：

| 块 | 要落到纸上的 |
|----|----------------|
| 设计原则 | 本能力遵守什么、明确不做什么（对齐 facts，禁止空话） |
| 模型 | 对象、关系、状态机、不变量；沿用还是新建（有路径） |
| 交互 | 用户主路径 + 空态/失败/权限；前端↔API↔模块↔数据 |
| 模块划分 | 边界、不进入、依赖方向；落在现有包 |
| 功能拆分 | 产品切片 **和** 实现切片（UI / 功能 / 算法）；页面作组合根 |
| 抽象 | 抽什么、为何、**不抽**什么 |

委派 `@architect`（模块/抽象）、`@product-manager`（交互是否超出需求）。有 CodeGraph 先摸现有模块再划边界。

写完 **STOP**，展示 `设计.md`，等用户说「按此设计写实现方案」。未确认不得进入 L3，不得 apply。

## 组合式拆实现（UI · 功能 · 算法）

这不是微服务，也不是把一个用户能力拆成多个发版。名字：**关注点分离 + 能力组合**；页面（或它调用的应用门面）是 **组合根（Composition Root）**。

| 实现切片 | 提供什么 | 禁止塞进去 |
|----------|----------|------------|
| **UI** | 展示、输入、状态呈现、空态/错误态控件 | 业务规则、算法公式、直接打库 |
| **功能** | 用例编排：权限、流程、调算法、读写模型 | 像素布局、可复用的纯计算细节 |
| **算法** | 纯计算/策略/排序/规则引擎；输入输出明确 | Vue/React、HTTP、会话 |

不同模块/目录各自提供能力，**最后在页面（或 BFF/应用服务）组装**成用户可感知的一条能力。依赖方向：`UI → 功能 → 算法`（或 `UI → 功能`，算法被功能调用）；**禁止**算法依赖 UI。

### 何时拆

- 算法会复用、要单测、或会独立演进
- UI 与规则会由不同人改、或同一页组装多块能力
- 复杂需求 L2 已判定要新抽象

### 何时不拆

- 只有一处用、十几行、拆开会空转三层
- 修 bug / 改样式：不要借机抽「架构」

### 与「一版本一能力」

用户可验收的仍是 **一项能力、一个版本**。UI / 功能 / 算法是 **同一版本内的实现切片**，可以分 PR、甚至分短期分支并行，但必须有一条 **组合切片** 把它们接到页面上一起验收。禁止：算法上线了、页面没有入口就算「能力交付」。

Git 分支（可选）：`ui-*` / `app-*` / `algo-*` 只服务本能力本版本，合入前组合切片必须绿。不要为每个切片开长期产品分支。

L3 `tasks.md` / `实现方案.md` 按切片列步骤，最后一项必须是 **页面组合 + 主路径验收**。

采用组合式时，L2 **必须**写切片契约（谁调用谁、名称、入参、出参/错误、状态在哪）。没有契约视为未完成设计（G1a）。

## 项目架构（L3 / propose 施工稿）

- **先摸现状**：现有分层、模块、命名、数据入口。已接 CodeGraph MCP 时先走图谱（见 `mcp/codegraph.md`），无命中再只读检索
- **再写方案**：落在 `实现方案.md` 与 change 的 `design.md`，必须含：
  - 沿用哪一层、哪个模块（禁止无理由新分层）
  - **文件路径清单**（新建/修改 + 职责）
  - 主路径 + 错误路径数据流
  - 契约落点（API / 表 / 前端边界）
  - 若采用组合式：标出 UI / 功能 / 算法路径与 **组合根**（哪个页面/门面组装）
- 跨模块或分层有争议 → 委派 `@architect`，结论写入 ADR 或实现方案「决策」表
- 未摸清现状就定架构 → STOP

## 会话开始（续作）

1. 读 `docs/product/facts.md` + `docs/product/decisions.md` 最近条目
2. `openspec list --json`（或 `openspec list`）
3. 有进行中的 change → 读其 `handoff.md`，以及 `docs/requirements/features/<id>/handoff.md`（若有），声明 `续作 change: <name>`
4. 读浓缩基线 + 该能力 `需求.md` / `设计.md` / `实现方案.md`（缺 L2 且命中复杂度 → 先补设计并 STOP）

## Propose（禁止写业务代码）

即使用户说「帮我做 X」，复杂需求也先设计再施工稿。做完当前阶段 **STOP**，等用户确认。

1. **G0**：读事实基线、决策记忆、浓缩基线；摸清现有架构（CodeGraph 优先）。
2. kebab-case 名；范围会影响外部行为则先问清。
3. 需要多轮中文讨论 → 先 `requirements-refinement` 把 `需求.md` 推到可评审。
4. 判定复杂度（见上表）。**复杂**：只写/更新 `设计.md`（可用 `openspec new change` 但本轮不要填满 tasks 施工项）→ **STOP 等设计确认**。
5. 设计已确认或判定为简单：`openspec new change "<name>"`（若尚未建）。
6. `openspec status --change "<name>" --json`，再 `openspec instructions <artifact-id> --change "<name>" --json`
7. 用本库模板写满 proposal / specs / L3 design / tasks；**同时**写或更新：
   - `docs/requirements/features/<id>/需求.md`
   - `docs/requirements/features/<id>/设计.md`（复杂必有且已定稿）
   - `docs/requirements/features/<id>/实现方案.md`
8. **立刻写** `tests.md` 和两处 `handoff.md`（复杂未过 L2 时状态=`设计待确认`，过 L2 后=`规划待确认`）
9. 跑 `knowledge-extract`；向用户展示路径，列出门禁，等待 **设计确认** 或 **apply** 授权

`需求.md` / `设计.md` / `实现方案.md` / change 产物冲突 → 先改文档再请确认，禁止各写一套。未过 L2 不得把 tasks 当已授权施工。

## Apply

1. 确认用户已授权；声明 `Using change: <name>`
2. 读 `facts.md`、最近决策、baseline、`需求.md`、**已定稿 `设计.md`（复杂需求）**、`实现方案.md`、proposal、specs、design、tasks、tests、handoff
3. 复杂需求无已定稿 `设计.md` → **STOP**，回到设计阶段
4. `openspec instructions apply --change "<name>" --json`
5. **按已确认架构的文件清单实现**；组合式则先切片后接组合根，不扩到清单外；遵守 `comments`；勾选完成项
6. 每完成一组任务：跑 `tests.md` 对应项，更新 handoff
7. 构建失败 → `build-fix`。改范围或改分层 → 先改 `需求.md` / `设计.md` / `实现方案.md` / change 规划产物，再继续
8. 任务勾完 → `code-review-gate` → `verification-gate`（含 tests.md）

## Archive

仅当用户要求，且 G5 满足：

```bash
openspec archive "<name>"
```

归档后把仍有效的新不变量**浓缩进 baseline**；实现/方向变化写入 `facts.md`（用户确认后）。更新两处 handoff 为已归档。`需求.md` / `实现方案.md` 保持已定稿。本轮拍板写入 `decisions.md`。

## 与其它 Skill

| 阶段 | 配合 |
|------|------|
| 中文需求多轮 | `requirements-refinement`（同一 `需求.md`） |
| 复杂需求结构 | 本 Skill **设计阶段**（`设计.md`）；不要误走 `project-spec-design`（那是视觉） |
| 无 OpenSpec 时的 L3 | `plan-workflow`（须 L2 已过或已声明跳过） |
| 测试证据 | `tests.md` + `eval-harness` |
| 续作/harness | `handoff.md`（任务进度）；`decisions.md`（项目拍板）；复杂循环可叠加 `dynamic-workflow-mode` |
| 反复强调的偏好 | `knowledge-extract` → 规则 / 浓缩基线 / facts / 新 Skill |
| 修缺陷 | `project-spec-fix` |
| 改样式 | `project-spec-style` |
| 界面设计方向 | `project-spec-design` |
| 改 backend | `backend-verify` |

## 约束

- 规划轮次不改 `backend/`、`frontend/` 业务代码
- spec 写可观察行为（WHEN/THEN），测试写如何证明
- 架构写路径与边界，不写空泛「微服务/最佳实践」
- 复杂需求禁止用 L3 文件清单代替 L2（模型/交互/模块/拆分/抽象/原则）
- 组合式拆分不得把算法/规则写进控件；不得把无组合根的切片当交付
- 本规范库的 `rules/` 不是业务仓 OpenSpec root
- `--store` 仅当用户指定或 `openspec context --json` 指向 store
