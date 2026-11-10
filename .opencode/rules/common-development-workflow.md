# Development Workflow

> This rule extends the git workflow rule with the full feature development process that happens before git operations.

The Feature Implementation Workflow describes the development pipeline: planning, tests, code review, and then committing to git.

## Feature Implementation Workflow

1. **Plan First**
   - New capability: `project-spec` propose, then wait for user confirm
   - Or use **planner** / `plan-workflow` when the repo has no OpenSpec root

2. **Tests**
   - Prefer tests that lock the behavior you change
   - Bug fixes: reproduce with a failing test when practical

3. **Code Review**
   - Use **code-reviewer** agent immediately after writing code
   - Address CRITICAL and HIGH issues
   - Fix MEDIUM issues when possible

4. **Commit & Push**
   - Detailed commit messages
   - Follow conventional commits format
   - See the git workflow rule for commit message format and PR process

