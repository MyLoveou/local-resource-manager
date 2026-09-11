# 浓缩基线

> 上限约 80 行。只写**已确认**约束。  
> 实现现状与方向：[`docs/product/facts.md`](../docs/product/facts.md)  
> 历次拍板：[`docs/product/decisions.md`](../docs/product/decisions.md)  
> 副本：[`docs/product/baseline.md`](../docs/product/baseline.md)

## 栈

| 层 | 技术 | 目录 |
|----|------|------|
| 桌面 | Electron 44 + Vue 3 + Vite + TS | `apps/desktop` |
| 后端 | Python FastAPI + uvicorn | `apps/backend` |
| 数据 | SQLite（WAL） | `apps/backend` data / userData |
| 规范 | Cursor Skill `project-spec` + OpenSpec CLI | `docs/product` · `openspec/` |

## 不变量（已确认）

1. 渲染进程只通过 HTTP 调本机后端；地址由主进程注入，不写死 8000。
2. 后端只绑 `127.0.0.1`；单一进程，library / scrape / download 为 router 前缀。
3. API JSON camelCase，Python/SQLite snake_case，经 `ApiModel`。
4. 资源删除默认软删（`status=trashed`），不是 DROP 行。
5. 分层：UI → application → domain ← infrastructure；domain 不依赖上层。
6. 先交付媒体库闭环，再上不完整工作台；远期类型与资产域可插拔。
7. 新表必须走 `shared/db/migrations/NNNN_*.sql`。

## 禁止（已确认）

- 提交密钥、`.env`、`.venv`、`*.db`、日志、`node_modules`、`out/`
- 新能力未确认规划（L1+L3 或 OpenSpec change）就改业务主路径
- 用户未要求时 `git commit` / `push`
- 把推测写成 `facts.md` 已确认句
- 为本地 sidecar 先上 `/v1`（未另拍板前）
- WCH / 词表治理需求仍为草案时当已定稿开工
- 常驻文件监视、多用户账号
- 渲染进程对库目录做复制/移动/哈希（入库 IO 只在后端）
- 把用户源目录登记为可重复扫描的库根（导入是一次性复制）

## 验收命令

```powershell
pnpm --filter desktop typecheck
pnpm --filter desktop lint
# 后端冒烟（venv 已建）
apps/backend/.venv/Scripts/python -c "from app.main import app"
# 开发启动
pnpm dev
```

改 `apps/backend/**` 后：停旧 Electron → 再 `pnpm dev` → `GET /health` 与 `GET /library/health` 为 200。

## 个人偏好（已确认、反复强调）

- 回复用简体中文
- 先契约/列表状态对齐，再拆目录；不要平行另起架构
- OpenSpec change 与中文 `需求.md`/`实现方案.md` 不得各写一套范围

## 未确认

- 见 `facts.md`「未确认」
