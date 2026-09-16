# 测试 · anime-av-types

## 映射

| Spec 场景 | ID | 刀 | 类型 | 步骤 | 期望 |
|-----------|----|----|------|------|------|
| 空作品列表 | T1 | min | 接口 | GET type=anime 与 av | 200 空 items |
| 旧视频不变 | T2 | min | 单测 | 迁移后读 video 行 | type=video |
| 详情含树 | T3 | min | 单测 | 两集 GET | episodes=2 |
| 一文件夹一张卡 | T4 | min | 接口 | 目录导入 anime | 1 条 anime；video 列表无这两集 |
| 选中不自动播 | T5 | min | 手工 | 单击作品卡 | 栏有数据 overlay 关 |
| 选集播放 | T6 | min | 手工 | 点一集 | overlay 播该 file |
| 特典分组 | T7 | plus 或 min 顺手 | 手工 | 有 extras | 特典区有；集数不含 extra |
| 离页导航 | T8 | min | 手工 | /anime → /video | 无 TypeError |
| 向导番剧 | T9 | min | 手工 | 导入类型步 | 可见番剧、AV |
| 扁平字幕组预览 | T10 | plus | 单测 | `[Fansub] Title - 02.mkv` | 预览 S01E02 + fansub |
| 删错集 | T11 | plus | 接口 | DELETE 一集 | 作品仍在 |
| 集探测与封面 | T12 | plus | 单测 | mkv+jpg | duration；cover_file_id |
| 女优多值 | T13 | plus | 接口 | 两名 performers | 长度 2 |
| 单文件视频回归 | R1 | min | 单测 | video 导入 | PASS |

## 命令

```powershell
apps/backend/.venv/Scripts/python -m unittest discover -s apps/backend/tests -p "test_*.py"
pnpm --filter desktop typecheck
```

## 记录

| ID | 结果 | 证据 | 日期 |
|----|------|------|------|
| T1–T4, R1 | PASS | `unittest` 62 tests OK，含 `test_series_ingest.py` | 2026-09-17 |
| T5 选中不自动播 | 代码：系列不在 Player 映射 | ResourceBrowser `type in Player` | 2026-09-17 |
| T6 选集播放 | 代码：InfoPanel `open(..., fileId)` | 待 Electron 手工 | 2026-09-17 |
| T7 特典 | 文件名命中则 extras，不计入正片 | 待手工夹 | 2026-09-17 |
| T8 离页 | unmount 仅 image/video close | 待手工 | 2026-09-17 |
| T9 向导 | ENABLED_IMPORT_TYPES 含番剧/AV | 待手工 | 2026-09-17 |

## 未覆盖

- 刮削、旧库改类型、10054、overlay 内切字幕：OUT。
