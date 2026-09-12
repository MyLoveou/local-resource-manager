# 测试 · grid-media-performance

> 每个 spec 场景一行可执行检查。声称完成前实跑。

## 映射

| Spec 场景 | 测试 ID | 类型 | 命令或步骤 | 期望 |
|-----------|---------|------|------------|------|
| 导入图片成功落盘 | T1 | 单测 | `python -m unittest tests.test_grid_thumbnails` | 包内 `thumbs/grid.webp` + role=thumbnail |
| 无封面视频不造空文件 | T2 | 单测 | 同上 | 无 thumbs、无 thumbnail 行，导入成功 |
| 生成失败不挡导入 | T3 | 单测 | mock 生成失败 | 资源仍在，无坏 grid.webp |
| 字段分离 | T4 | 单测 | GET/仓储映射 | thumbnailPath 含 files/content；coverPath 不含 thumbs/grid |
| 换封面覆盖 | T5 | 单测 | replace_cover | 仍是 thumbs/grid.webp，mtime/内容变 |
| 网格优先缩略图 | T6 | 手工 | Electron 导入后看网络/img src | 卡片 URL 为 thumbnail 文件流 |
| 旧数据回退 | T7 | 手工 | 打开导入前的旧图 | 卡片仍显示 coverPath |
| 宽度节流 | T8 | 手工 | 拖窗口 | 列数跳动明显少于像素变化；不假死 |
| 回归 typecheck | R1 | 构建 | `pnpm --filter desktop typecheck` | 通过 |

## 命令

```powershell
pnpm --filter desktop typecheck
apps/backend/.venv/Scripts/python -m unittest tests.test_grid_thumbnails -v
```

## 记录

| ID | 结果 | 证据 | 日期 |
|----|------|------|------|
| T1–T5 | PASS | `python -m unittest tests.test_grid_thumbnails -v` | 2026-09-12 |
| T6–T8 | 未跑 | 须重启 Electron 手工验 | |
| R1 | PASS | `pnpm --filter desktop typecheck` | 2026-09-12 |

## 未覆盖

- 万级滚动：本切片不作硬门槛，不单测。
