# 跨会话续作 · image-exif-taken

## 状态

- change：无独立 OpenSpec（小切片已实现）
- 阶段：已落地
- 最后更新：2026-09-19

## 已完成

- 探测写入、PATCH 手改、信息栏、单测

## 下一步

- 重启 Electron；清库后导入带 EXIF 的 jpg 验收
- 手改拍摄时间并按拍摄排序

## 关键路径

- `docs/requirements/features/image-exif-taken/`
- 代码现状：`media_probe.probe_image` 无 EXIF；`add_file` 无该参数
