# 测试 · metadata-panel

> 每个 spec 场景一行可执行检查。声称完成前实跑。

## 映射

| Spec 场景 | 测试 ID | 类型 | 命令或步骤 | 期望 |
|-----------|---------|------|------------|------|
| 详情通用字段 | T1 | 单测 | 导入或插入资源后 GET id | 含 files.size、tags、category、createdAt |
| 详情 404 | T2 | 单测 | GET 不存在 id | 404 |
| PATCH 仅评分 | T3 | 单测 | PATCH `{ rating: 8 }` | 标题不变，rating=8 |
| PATCH tagNames | T4 | 单测 | 两次 PATCH 名字数组 / 空数组 | 关联条数 2 然后 0；tags 表有名 |
| PATCH 新分类名 | T4b | 单测 | categoryName 新词 | categories 多一行，详情 category.name 为该词 |
| POST cover 成功 | T5 | 单测 | 复制临时 png 为封面 | files 有 cover；primary sha256 不变 |
| POST cover 非法 | T6 | 单测 | path 不存在 | 400，封面未改 |
| 面板字段可见 | T7 | 手工 | 图片页点选一条 | 封面/标题/大小/评分/标签/分类/时间 |
| 未选中空态 | T8 | 手工 | 删除后或清空选中 | 「未选择资源」 |
| 改星未保存 | T9 | 手工 | 改星不保存再点选 | 仍为旧分 |
| Enter 切词不保存 | T9b | 手工 | 连打两个标签回车 | 无 PATCH |
| 面板保存草稿 | T9c | 手工 | 改星/分类/标签后点保存 | 一次 PATCH，重载一致 |
| 弹窗保存/取消含封面 | T10 | 手工 | 弹窗改标题并选封面后取消 | 标题封面均不变 |
| 面板换封面 | T11 | 手工 | 视频页更换封面；图片页确认无该按钮 | 视频封面变；图片无入口 |
| 删除确认 | T12 | 手工 | 删除点取消再确认 | 取消仍在；确认后消失 |
| 回归导入 bump | R1 | 手工 | 图片页导入视频 | 图片网格不 reset |

## 命令

```powershell
pnpm --filter desktop typecheck
apps/backend/.venv/Scripts/python -m unittest tests.test_metadata_panel tests.test_import_ingest -v
pnpm dev
```

## 记录

| ID | 结果 | 证据 | 日期 |
|----|------|------|------|
| T1–T6 / T4b | PASS | `python -m unittest tests.test_metadata_panel` 7 ok（T2 为仓储 get None，与 API 404 同语义） | 2026-09-12 |
| T7–T12 / R1 | 未跑 | 需本机 Electron | |

## 未覆盖

- Electron 对话框本身无单测；T11 依赖手工选文件。
