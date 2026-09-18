# 测试 · library-type-platform

## 映射

| Spec 场景 | ID | 类型 | 步骤 | 期望 |
|-----------|----|------|------|------|
| 注册表 + TypeBrowse | T1 | 构建+对照 | 档案生成路由；views 无类型克隆页 | 侧栏/向导一致 |
| 未登记 type | T2 | 接口 | POST type=unknown | 422 |
| 音频导入 | T3 | 单测 | 导入音频夹具 | 1 条 audio owned |
| 游戏默认登记 | T4 | 单测 | 目录含 exe，默认导入 | 1 条 game indexed；store 无整树 |
| 游戏删记录不删源 | T4b | 单测 | indexed 彻底删除 | 源 exe 仍在 |
| 音频去重 | T5 | 单测 | 同哈希两次 | skippedDuplicate |
| 空列表 | T6 | 单测 | GET 五新 type | 空 items |
| 网格可见 | T7 | 手工 | 导入后开页 | 有卡 |
| 音频 overlay | T8 | 手工 | 二次点击 | Howler 在播 |
| 小说/漫画系统打开 | T9 | 手工 | 打开 | 系统应用，非阅读器 |
| 离页 | T10 | 手工 | 音频→图片 | 无 TypeError |
| 漫画目录一作 | T11 | 单测 | 多 png 一夹 | 1 条 comic，多 files |
| 模型内置预览 | T12 | 手工 | 打开 glb | overlay 能看见 |
| 回归图视频番剧 | R1 | 单测+手工 | 现有测 | PASS |

## 命令

```powershell
apps/backend/.venv/Scripts/python -m unittest discover -s apps/backend/tests -p "test_*.py"
pnpm --filter desktop typecheck
```

## 记录

| ID | 结果 | 证据 | 日期 |
|----|------|------|------|
| T2–T6 T11 T4b | PASS | `test_library_types` | 2026-09-17 |
| R1 自动 | PASS | 全量 71 tests | 2026-09-17 |
| typecheck | PASS | `pnpm --filter desktop typecheck` | 2026-09-17 |
| T1 T7–T10 T12 | 待手工 | 需重启 Electron 跑 0009 |  |

## 未覆盖

- 内置小说/漫画阅读器：另立项。
- 游戏 owned 大目录二次确认：手工即可。
