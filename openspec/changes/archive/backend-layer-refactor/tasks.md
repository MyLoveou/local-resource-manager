# 任务 · backend-layer-refactor

## 0. 基线

- [x] 0.1 修复基线：resources.md5 → sha256 + 补 0015 迁移

## 1. 内核收敛

- [x] 1.1 抽出 `shared/utils/time.py`（db_now/db_ts），替换三处 `_now/_ts`
- [x] 1.2 清 `shared/utils`：死代码移出至 scripts/scratch

## 2. 领域与枚举归位

- [x] 2.1 shared/models.py 只留 ApiModel；library 实体 → library/domain；settings 实体 → settings/domain
- [x] 2.2 shared/constants.py 只留横切；Protocol/DownloadEngine → download；SourceKind → library；AdapterKey → settings
- [x] 2.3 media_types/media_labels → library/domain

## 3. ORM 拆分

- [x] 3.1 shared/db/orm.py → 四模块 infrastructure/orm.py；Base → shared/db/base.py

## 4. settings 补全

- [x] 4.1 新增 settings/domain + settings/infrastructure；删除 shared/infrastructure

## 5. 文档

- [x] 5.1 更新 apps/backend/README.md
- [x] 5.2 记录 handoff
