# 测试 · import-directory-scan

> 每个 spec 场景一条可执行检查。声称完成前实跑。

## 映射

| Spec 场景 | 测试 ID | 类型 | 命令或步骤 | 期望 |
|-----------|---------|------|------------|------|
| library-ingest / Single image file is copied | T1 | 单测 | `apps/backend/.venv/Scripts/python -m unittest apps.backend.tests.test_import_ingest`（或项目约定等价命令） | 库内有副本，源文件仍在 |
| Directory is not remembered as a root | T2 | 单测 | 同上：导入目录后无 roots 存储 | settings 无 library_roots，也无 roots API 200 列表含该路径 |
| Duplicate hash is skipped | T3 | 单测 | 两次导入同一字节 | 资源数=1，skippedDuplicate≥1 |
| Image folder ignores non-images | T4 | 单测 | 目录含 png+txt，type=image | 只入图片 |
| Image cover falls back to primary | T5 | 单测 | 导入一张图后 resolve_cover | 指向 primary，未再复制封面文件 |
| Video ingest is primary only | T5b | 单测 | mp4 旁有 srt | 只入 primary，包内无字幕文件 |
| Unsupported type is rejected | T6 | 接口 | POST 未启用 type | 400，库目录无新文件 |
| Concurrent import is rejected | T7 | 单测 | 任务 running 时再 POST | 409 |
| Unreadable file is counted | T8 | 单测 | 夹一个不可读候选 | skippedError≥1，其它仍入库 |
| Job is created and reaches done | T9 | 接口 | POST 202 后轮询 GET | status=done，done≤total |
| Content is served from the library copy | T10 | 接口 | GET `/library/resources/{id}/content` | 字节与库内副本一致 |
| Unknown content id is 404 | T11 | 接口 | GET 不存在 id | 404 |
| desktop / Image file import happy path | T12 | 冒烟 | 向导选图片文件导入 | 网络面板仅 POST imports，无 renderer 写库路径 |
| User cancels the dialog | T13 | 手工 | 打开对话框点取消 | 无 POST |
| Disabled type cannot be submitted | T14 | 手工 | 向导看未启用类型 | 无法进入对话框 |
| Folder import does not add a root list | T15 | 冒烟 | 导入一文件夹后看顶栏 | 无「立即扫描 / 根目录」 |
| Progress updates during import | T16 | 冒烟 | 导入多张图 | 进度 done 增加 |
| Views refresh after success | T17 | 冒烟 | 导入后打开图片页与首页 | 有新卡、计数增加 |
| Multiple files in one file-mode import | T18 | 冒烟 | 文件模式一次选多张图 | 一次 POST，paths 长度>1，均入库 |
| typecheck | R1 | 构建 | `pnpm --filter desktop typecheck` | 通过 |

## 命令

```powershell
pnpm --filter desktop typecheck
# 后端测试路径以落地后的 unittest 模块名为准
```

## 记录

| ID | 结果 | 证据 | 日期 |
|----|------|------|------|
| T1–T5b, T7–T8, T5 | PASS | `python -m unittest tests.test_import_ingest -v` 10 tests OK | 2026-09-12 |
| T6 | 部分 | 未启用类型仅 image/video 枚举，非法 type 由 Pydantic 422；缺文件 400 已测 | 2026-09-12 |
| T9–T11 | 部分 | job 状态机与 content 路径已实现；未起完整 TestClient 打 HTTP | 2026-09-12 |
| T12–T18 | 未跑 | 需 Electron 手工/冒烟 | 2026-09-12 |
| R1 | PASS | `pnpm --filter desktop typecheck` | 2026-09-12 |

## 未覆盖

- 视频字幕/抽帧/探测：OUT，后续专项。  
- 库路径设置与 userData：OUT，设置模块。  
- 清空旧演示数据：OUT。
