# 提案 · library-type-platform

> 与 `docs/requirements/features/library-type-platform/需求.md` 同范围。  
> 开放问题已拍板：D-20260917-02、**D-20260917-03**。

## 为什么

番剧/AV A-min 已合入；其余库类型与类型分支仍散落。需要领域级类型目录 + 补齐导入展示与最低打开，并去掉类型页克隆。

## 做什么

- TypeProfile（领域目录）查表，禁止类型 if 链。
- 新类型：`audio` `novel` `game` `model` `comic`。
- 最低消费：音频 Howler；游戏系统打开 launch；模型内置预览；漫画/小说系统打开（阅读器另立项）。
- 游戏默认扫描登记（indexed），可选复制。
- 桌面类型网格收口为单一 TypeBrowse。
- **BREAKING：** CHECK 扩 type；resources 增 `storage_kind`。

不交付：刮削/下载/合集/画廊；番剧 plus；**内置小说/漫画阅读器**；游戏成就；自研解码器；持久 library_roots。

## 范围

| | 内容 |
|--|------|
| IN | 领域档案；五类型导入展示；上述打开；游戏 indexed；TypeBrowse |
| OUT | A-plus；阅读器；游戏整盘默认复制 |
| 假设 | 漫画图片目录=一作；模型预览以 3D 为主；媒体仍 owned |

## 能力

- `library-type-registry`
- `library-type-ingest`
- `desktop-type-browse`
- `desktop-min-consume`

## 开放问题

无。扩展名清单 apply 时核对。
