# 小说（novel） · 需求

> 类型配置：`file` 导入、`owned` 存储、系统打开；扩展名 `epub/pdf/txt/html/htm/mobi/azw3`。
> 当前定位是“资源登记 + 外部阅读器”，不是内置阅读器。

## 1. 已实现

- EPUB/PDF/TXT 等文件导入，复制入库、sha256 去重。
- 系统默认程序打开；合集/详情统一消费入口。
- 封面：EPUB/PDF/cbz 等封面提取（通用 `library-covers`）。
- 分类、标签、合集、批量、回收站、搜索。
- 文件可带多角色（封面、字幕等通用 File 模型）。

## 2. 未实现 / 待确认

| 能力 | 状态 | 说明 |
|------|------|------|
| 内置阅读器 | OUT（当前） | 明确后置；先用系统阅读器 |
| 阅读进度/书签 | 未实现 | 无阅读器状态 |
| EPUB 目录/章节解析 | 未实现 | 只取封面，不建章节模型 |
| 小说元数据刮削 | 未实现 | 无站点适配器 |
| 书源/在线阅读 | OUT | 不做在线书源 |

## 3. 候选

- EPUB 内置阅读器、目录/进度/书签。
- 作者/系列/出版社结构化字段。
- 小说封面/简介手动编辑的批量流程。
- 与工作目录的“待读/在读”状态结合。

## 4. 明确不做

- 在线小说站/书源。
- 排版编辑器/格式转换。
- 把漫画/小说合并成同一类型。

## 5. 入口

- `features/library-covers-complete/`
- `apps/desktop/src/renderer/src/infrastructure/shell/openLibraryFile.ts`
- `apps/backend/app/library/application/covers/`
