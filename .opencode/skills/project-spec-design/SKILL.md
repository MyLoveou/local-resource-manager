---
name: project-spec-design
description: >-
  样式/界面视觉方向。触发：UI 观感、视觉方向、设计稿、更好看、改这一页样子。
  能力设计（模型/模块/交互）请用 project-spec 设计阶段。
origin: 项目规范
---

# 项目规范 · 界面设计

这是**视觉方向** Skill。模型、交互、模块划分、功能拆分、抽象、设计原则走 `project-spec` **设计阶段**（`设计.md`），不要用本 Skill 代替。

先产出可执行的**视觉**方向，**默认本轮不写业务代码**。用户确认后再：

- 只改观感 → `project-spec-style`
- 新页面/新流程 → `project-spec` 全量 propose

## 步骤

1. **G0** 读基线与已有页面（同产品里已有的密度、色、字，不要换皮成另一款产品）。
2. 问清：哪一页、给谁用、要解决的观感问题、有无设计稿。缺关键信息就问，不要发明品牌。
3. 新界面或用户明确要求重做视觉时，方向方法用 `oil-ui`（产品事实、主角、灰度、方向卡）。再用 [templates/design-direction.md](../project-spec/templates/design-direction.md) 记下层级、色、字、间距、状态和组件拆分。默认 **1 个主方案**；用户明确要求比较时才按 `oil-ui` 做多个真正不同的方向。已有页面只是不好看时，沿用现有密度、色和字，不要换皮。方向确认后落地时，工艺约束用 `baseline-ui`、`better-ui`、`better-layout`、`better-typography`。本技能仍只出方向。
4. Vue / React 分开写落地要点（SFC vs 组件文件），不要混栈。
5. 有 `openspec/`：可建 `style-direction-<name>` change，`skip_specs: true`；`handoff.md` 状态=`视觉待确认`。
6. **STOP**，等用户说「按这个做」或指出修改。
7. 授权后：纯样式走 `project-spec-style`；含新交互/新 API 走 `project-spec` propose（本方向作为 design 输入）。

## 禁止

- 未确认方向就大改 CSS/组件树
- 套用网上完整 UI kit / 与本产品无关的风格包
- 把无障碍对比度、可点击区域改没
- 用设计探索当借口改后端
