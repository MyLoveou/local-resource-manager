# 设计 · image-consume

> 与 `docs/requirements/features/image-consume/实现方案.md` 同一套分层与文件清单。

## Context

见 proposal。现状：单击选中（D-16）；InfoPanel 已有描述/待办；`GET files/content` 原图；`files.path` 已是库内绝对路径；preload 仅有选文件对话框；无查看器、无 shell 打开。

基线：渲染只 HTTP；入库 IO 只在后端；打开 OS 资源用主进程。

## Goals / Non-Goals

**Goals：** 覆盖层看图+改元数据；IPC 定位、默认打开、选择其他应用。

**Non-Goals：** 视频播放、新表、新 REST、渲染读盘。

## Decisions

| 决策 | 选择 | 不选 |
|------|------|------|
| UI | 同窗覆盖层左面板右查看器 | 新 BrowserWindow（状态难共用） |
| 看图 | Viewer.js（§7.1：嵌右栏+旋转/适应/1:1） | PhotoSwipe（灯箱）；OpenSeadragon（巨图瓦片） |
| 打开 | `showItemInFolder` / `openPath` / `openWith` | 渲染 `file://`；自建软件目录 |
| 入口 | 已选中再点 + 双击 + 封面 | 单击即打开（与 D-16 冲突） |
| 切图范围 | 当前页已加载图片 id | 全库乱序拉下一页 |

## Risks / Trade-offs

- 大图内存 → 本轮仍原图流，可后置预览档
- Viewer.js 与 Vue 生命周期 → destroy
- 无库根设置时 IPC 只验文件存在 → 开放问题，暂接受（仅本机）

## Migration Plan

先 IPC + 按钮（可无查看器验证打开），再覆盖层与 Viewer.js。回滚卸依赖即可。

## Open Questions

已关闭：Viewer.js + 封装；覆盖层左元数据右看图；选择其他应用走系统打开方式。
