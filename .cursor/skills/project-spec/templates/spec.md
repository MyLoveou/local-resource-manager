## Purpose

用两句说明该能力对用户或下游系统做什么（不少于 50 字，避免 TBD）。仅**新能力**写本节；改已有能力不要重复 Purpose。

## ADDED Requirements

### Requirement: <短名，中文可>

系统 SHALL …（可观察行为，不写类名/框架）。

#### Scenario: 主路径成功

- **WHEN** …
- **THEN** …
- **对应测试**：`tests.md` §<编号>

#### Scenario: 校验失败 / 无权限

- **WHEN** …
- **THEN** …
- **对应测试**：`tests.md` §<编号>

#### Scenario: 边界（空列表 / 重复提交 / 幂等）

- **WHEN** …
- **THEN** …
- **对应测试**：`tests.md` §<编号>

## MODIFIED Requirements

<!-- 从 openspec/specs/<path>/spec.md 整段复制再改。禁止只写 diff 碎片。 -->

## REMOVED Requirements

### Requirement: <旧名>

**Reason**：  
**Migration**：调用方怎么改
