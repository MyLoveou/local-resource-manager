# 提案 · app-performance

> 与 `docs/requirements/features/app-performance/需求.md` 同范围。  
> **取代** `image-consume-perf`（看图只是 S5）。

## Why

卡顿来自整条链，且当前脏库（无缩略图）会逼前端去拉原图。用户还要求：大批量导入不卡死、万级网格可滚、优化后能清空脏数据。同时必须想清楚「哪些能只放前端」——以后后端上服务器时，库不在本机，前端直写磁盘的捷径会作废。

## What Changes

S0 测量 → S1 索引与 slim/keyset 列表 → S2 导入工人池+单写者+后台 job → S3 缓存头 → S4 万级虚拟显示 → S5 查看器 → S6 显式清空/修补脚本。

**不把入库 IO 下放到渲染进程。** 显示与草稿可以前端化。JSON 已有字段不删；列表可加 cursor。

## Capabilities

### Modified Capabilities

- `library` 查询、导入 job、文件流、维护脚本  
- `desktop` 列表/信息栏/导入进度  
- `desktop-image-viewer`（S5）

## Impact

backend 迁移 + 仓储 + 导入模型；desktop 分页与虚拟网格；一次性清库脚本。不包含公网部署。
