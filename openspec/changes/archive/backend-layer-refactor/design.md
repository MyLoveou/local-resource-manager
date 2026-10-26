# 设计 · backend-layer-refactor

## 目标结构

```
app/
├── shared/                          # 共享内核
│   ├── config.py / log.py
│   ├── errors.py                    #   DomainError / InvalidStateError
│   ├── models.py                    #   仅 ApiModel 基类（snake↔camel）
│   ├── value_objects.py             #   Rating / Dimension / Progress
│   ├── constants.py                 #   仅 HTTP/鉴权豁免等横切常量
│   ├── api_envelope.py
│   ├── fs/file_ops.py               #   FileOps
│   ├── middleware/{auth,logging}.py
│   ├── db/{base,db,migrations}.py + migrations/
│   └── utils/time.py                #   db_now / db_ts
├── library/  (api/ application/ domain/ infrastructure/)
├── download/ (api/ application/ domain/ infrastructure/)
├── scrape/   (api/ application/ domain/ infrastructure/)
└── settings/ (api/ application/ domain/ infrastructure/)
```

## 决策

- 模型按模块归属（垂直切片），shared 只留跨模块内核。
- 依赖方向：`api → application → domain → core(shared)`；`infrastructure → domain + core`。
- ORM 拆表：跨模块外键用字符串表名引用；`Base` 上提 `shared/db/base.py`；建表走迁移 SQL，无需 metadata 注册点。
- 时间工具：抽出 `shared/utils/time.py` 的 `db_now()/db_ts()`，替换三处重复。
- shared/utils 死代码移出 app 包至 `apps/backend/scripts/scratch/` 保留。
- shared 目录名保留，不改名 core（降 churn）。

## 风险 / 回滚

- 分阶段提交，每阶段跑测试 + 启动冒烟；失败即停在当阶段修复。
- 不改 schema / API / 前端；纯 import 与文件移动。
