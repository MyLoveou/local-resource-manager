# Agent Orchestration

Agents live in the platform's `agents/` directory.

| Agent | Purpose | When to Use |
|-------|---------|-------------|
| planner | Implementation planning | Complex features without an OpenSpec change yet |
| architect | System design | Architectural decisions |
| product-manager | Requirements | New capability wording, acceptance criteria |
| backend-dev | Spring / Java | `backend/**`, migrations, APIs |
| frontend-dev | React | React pages and components |
| frontend-vue-dev | Vue 3 | Vue SFCs and composables |
| code-reviewer | Code review | After writing or modifying code |
| doc-sync | Docs / contracts | After API or entity changes |
| qa-engineer | Quality | Smoke, DoD, verification |

Independent read-only investigations may run in parallel. Do not let two agents write the same files.

