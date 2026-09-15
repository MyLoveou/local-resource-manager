# 测试 · anime-av-types

## 映射

| Spec 场景 | ID | 类型 | 步骤 | 期望 |
|-----------|----|------|------|------|
| 空作品列表 | T1 | 接口 | GET type=anime 与 av | 200 空 items |
| 旧视频不变 | T2 | 单测 | 迁移后读 video 行 | type=video |
| 详情含树 | T3 | 单测 | 两集+一特典 GET | episodes=2 extras=1 正片集数=2 |
| 一文件夹一张卡 | T4 | 接口 | 目录导入 anime | 1 条 anime resource；video 列表无这两集 |
| 选中不自动播 | T5 | 手工 | 单击作品卡 | 栏有数据 overlay 关 |
| 选集播放 | T6 | 手工 | 点一集 | overlay 播该 file |
| 特典分组 | T7 | 手工 | 有 extras 的作品 | 特典区有；集数不含 extra |
| 离页导航 | T8 | 手工 | /anime → /video | 视频页出现无 TypeError |
| 向导番剧 | T9 | 手工 | 导入类型步 | 可见番剧、AV |
| 单文件视频回归 | R1 | 单测 | 现有 video 导入测 | PASS |

## 命令

```powershell
apps/backend/.venv/Scripts/python -m unittest discover -s apps/backend/tests -p "test_*.py"
pnpm --filter desktop typecheck
```

## 记录

| ID | 结果 | 证据 | 日期 |
|----|------|------|------|
| T1–T9, R1 | 未跑 | | |

## 未覆盖

- 刮削、旧库改类型、10054：OUT。
