# 测试 · image-consume

> 每个 spec 场景一行可执行检查。声称完成前实跑。

## 映射

| Spec 场景 | 测试 ID | 类型 | 命令或步骤 | 期望 |
|-----------|---------|------|------------|------|
| 选中再点打开 | T1 | 手工 | 图片页点 A，再点 A | 覆盖层打开，右为原图 |
| 批量模式不打开 | T2 | 手工 | 批量删除后点卡片 | 只勾选，无覆盖层 |
| 看图时改描述 | T3 | 手工 | 覆盖层左侧改描述保存 | 关闭后再打开信息栏仍是新文案 |
| 缩放与下一张 | T4 | 手工 | 滚轮缩放，点下一张 | 下一张是列表相邻图片 |
| 打开所在位置 | T5 | 手工 | 点打开所在位置 | 资源管理器定位到库内 primary |
| 外部默认应用 | T6 | 手工 | 用外部应用打开 | 默认看图程序打开该文件 |
| 选择其他应用 | T6b | 手工 | 选择其他应用并换程序 | 所选程序打开同一库内文件 |
| 缺失路径 IPC | T7 | 单测或主进程测 | 调 IPC 假路径 | 不崩溃，返回错误 |
| typecheck | R1 | 构建 | `pnpm --filter desktop typecheck` | 通过 |

## 命令

```powershell
pnpm --filter desktop typecheck
node --test --experimental-strip-types apps/desktop/src/main/infrastructure/existingFile.test.ts
```

## 记录

| ID | 结果 | 证据 | 日期 |
|----|------|------|------|
| R1 | 通过 | `pnpm --filter desktop typecheck` | 2026-09-12 |
| T7 | 通过 | existingFile.test.ts 4 passed | 2026-09-12 |
| T1–T6 / T6b | 未跑 | 需重启 Electron 后手工 | 2026-09-12 |

## 未覆盖

- HEIC 全解码
- 万级切图性能
- 视频
