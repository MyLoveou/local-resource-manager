# 浓缩基线

> 上限约 80 行。只写**已确认**约束。未确认单独成节。  
> 业务仓路径：`openspec/baseline.md`（可另存 `docs/product/baseline.md` 并在此链接）。  
> **实现现状与项目方向**不写在本文展开，见 `docs/product/facts.md`。  
> **历次拍板**见 `docs/product/decisions.md`。

## 栈

| 层 | 技术 | 目录 |
|----|------|------|
| 后端 | （填写，如 Spring Boot / Java） | `backend/` |
| 前端 | Vue 和/或 React（以本仓实际为准） | `frontend/` |
| 规范 | 平台目录 + OpenSpec | `rules/` · `skills/` · `openspec/` |

实现细节与方向：`docs/product/facts.md`。

## 不变量（已确认）

1.
2.

## 禁止（已确认）

- 提交密钥、`.env`、本地库文件
- 新能力未确认规划就改业务代码
- 用户未要求时 commit / push
- 把推测当业务现状

## 验收命令（按项目改）

```powershell
# frontend
cd frontend; npm run build
# backend
.\mvnw.cmd test
```

改 `backend/**` 后：停旧进程 → 启动 → migration 无失败 → HTTP 冒烟。

## 个人偏好（已确认、反复强调）

- （例：回复用简体中文）
- （例：前端同时可能有 Vue 与 React，不要默认只留一个）

## 未确认

- …
