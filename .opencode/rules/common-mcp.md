# MCP 使用

配置：本平台目录的 MCP 配置（`mcp.json`；OpenCode 为 `opencode.json` 的 `mcp` 段）。说明见 `mcp/README.md`。

## 已接入服务

| 服务 | 先用它何时 | 回退 |
|------|------------|------|
| `codegraph` | 摸调用链、影响面、现有模块 | Grep；并写明未用图谱 |
| `git` | 看仓库状态/历史 | Shell `git` |
| `ssh` | 用户点名已登记主机上的远程操作 | 用户本机终端；禁止连未登记地址 |
| `mcp-knowledge-graph` | 仅企业认证、且已按 `mcp/knowledge-graph.md` 合并时，用来回忆线索 | 读 facts、decisions、台账 |

## 硬约束

- `mcp.json` 与 git 中**不得**出现密码、PAT、私钥正文
- SSH 仅 `SSH_MCP_ALLOWED_HOSTS` / `mcp/hosts.json` 中的主机；占位符 `REPLACE_*` 未改则禁用 ssh
- Git 写操作（commit / push / checkout）遵守 G9 与 Git Safety Protocol
- 远程破坏性命令、生产环境 → 先问用户
- CodeGraph 结论要落到 `实现方案.md` 或 `facts.md`，不替代人核实
- 知识图谱里的内容不是已确认事实。拍板写入 `decisions.md` 或企业认证台账
- 未绿灯的 MCP 不得假装已执行

