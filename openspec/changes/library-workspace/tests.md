# Tests

## 映射

| Spec 能力 | 切片 | 测试 ID | 方式 | 输入/场景 | 断言 |
|-----------|------|---------|------|-----------|------|
| library-category-tree | 迁移/算法 | T1 | pytest | 旧库含多类型分类 | 资源/关系/合集对账；文件路径不变 |
| library-category-tree | 迁移 | T2 | pytest | 无资源旧分类 | 进入图片树「待整理分类」；非空显示 |
| library-category-tree | 算法 | T3 | pytest | 父/子节点、多分类 | 父节点含后代；计数去重 |
| library-category-tree | 算法 | T4 | pytest | 第 5 层、循环移动 | 4xx，树不变 |
| library-category-tree | 功能 | T5 | pytest | 删除空/非空分类 | 空分类删除并清时间线；非空阻止 |
| library-resource-metadata | 功能 | T6 | pytest | 多分类/清空/类型不符 | categories 数组；422 不部分写入 |
| library-resource-api | 功能 | T7 | pytest | categoryIds 单/多/未分类 | 子树/并集/去重/未分类 |
| library-saved-views | 功能 | T8 | pytest | 保存/重名/删除/未知时间 | 无成员表；默认排除未知时间；重名 409 |
| library-saved-views | 功能 | T9 | pytest | 删除引用分类 | filters 清 ID；剩余条件生效 |
| library-saved-views | 功能 | T10 | pytest | 时间线多分类并集 | 资源命中任一分类 |
| desktop-library-workspace | UI | T11 | CDP | 分类树/多分类/父节点筛选 | 结果与计数正确 |
| desktop-library-workspace | UI | T12 | CDP | 类型切换/视图切换/URL | 重置全部筛选；视图/URL 保留正确 |
| desktop-library-workspace | UI | T13 | CDP | 保存时间线/新增资源 | 自动进入；删除分类后条件更新 |
| desktop-library-workspace | UI | T14 | CDP | 首页缩略图点击 | 路由不变；只开当前一张 |
| desktop-library-workspace | UI | T15 | CDP | 合集 D 卡/键盘/0-3 成员 | 叠层/展开/Enter 打开 |
| desktop-library-workspace | UI | T16 | CDP | 批量 Ctrl/Shift/Esc | 范围替换；输入框不响应 |
| desktop-library-workspace | UI | T17 | CDP | 旧 `/photos`、旧类型路由 | 重定向正确，不 404 |
| library-saved-views / home | 功能 | T18 | pytest | `/library/home` 限量/空库 | recent=12、预览≤3、空态 |
| 回归 | — | R1 | 命令 | typecheck/lint/build/pytest | 全绿 |
| 交付 | — | R2 | 命令 | `pnpm release:win` | verify PASS |

## 命令

```powershell
pnpm --filter desktop typecheck
pnpm --filter desktop lint
pnpm --filter desktop build
apps/backend/.venv/Scripts/python -m pytest -q apps/backend/tests
pnpm release:win
```

## 记录

| ID | 结果 | 证据 | 日期 |
|----|------|------|------|
| T1 | PASS | pytest: legacy migration copies categories by type; FK check empty | 2026-10-19 |
| T2 | PASS | pytest: pending root parent for unused category | 2026-10-19 |
| T3 | PASS | pytest: parent subtree includes descendants; distinct count | 2026-10-19 |
| T4 | PASS | pytest: depth 4 and cycle rejected | 2026-10-19 |
| T5 | PASS | pytest: delete protection and saved-view cleanup | 2026-10-19 |
| T6 | PASS | pytest: multi-category PATCH and type mismatch 422 | 2026-10-19 |
| T7 | PASS | pytest: categoryIds single/multi/uncategorized | 2026-10-19 |
| T8 | PASS | pytest: saved view create/duplicate/unknown-time default | 2026-10-19 |
| T9 | PASS | pytest: category delete clears saved-view ID | 2026-10-19 |
| T10 | PASS | pytest: multi-category saved timeline union | 2026-10-19 |
| T11 | PASS | CDP: tree filter 8 tiles; counts 8/8/4 | 2026-10-19 |
| T12 | PASS | CDP: video tab reset filters; view switch preserves category | 2026-10-19 |
| T13 | PASS | CDP: save timeline; option appears; hash updated | 2026-10-19 |
| T14 | PASS | CDP: home recent click keeps hash; viewer opens | 2026-10-19 |
| T15 | PASS | CDP: collection D card click; previews visible | 2026-10-19 |
| T16 | PASS | CDP: batch Shift range 5 selected; Esc exits | 2026-10-19 |
| T17 | PASS | CDP: /image -> /library/image; /photos -> timeline | 2026-10-19 |
| T18 | PASS | pytest: home recent=2, collection previews=2; CDP home counts | 2026-10-19 |
| R1 | PASS | 195 passed; typecheck/lint/build exit 0 | 2026-10-19 |
| R2 | PASS | release:win verify PASS; 0.1.1 package rebuilt | 2026-10-19 |
