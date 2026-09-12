# 跨会话续作 · app-performance

实现已落在分支 `feat/app-performance`。清库须先退出 `pnpm dev`，再：

```powershell
cd apps/backend
.\.venv\Scripts\python scripts\reset_library.py --yes
```

然后重新 `pnpm dev` 并导入。可选先预览残缺项：`python scripts/repair_thumbnails.py`（加 `--yes` 才删/补）。
