# 07 · SQLite 迁移与仓储（2026-10-19 现状）

> 项目已从早期同步 sqlite3 仓储迁到 **SQLAlchemy 2.0 async + aiosqlite**。
> 旧文里“每请求一个短连接 / get_connection”的写法已过时，本文以当前代码为准。

## 1. 分层位置

```text
apps/backend/app/shared/db/
├─ db.py            # async engine、session、PRAGMA、ensure_db
├─ migrations.py    # 同步迁移执行器
├─ base.py          # declarative base
├─ orm.py           # SQLAlchemy ORM 基类/公共列
└─ migrations/
   ├─ 0001_init.sql
   ├─ ...
   ├─ 0018_category_tree.sql
   └─ 0019_saved_views.sql
```

当前迁移到 `0019`，不是早期文档里的 `0001`。

## 2. 连接管理

`db.py`：

```python
def _apply_sqlite_pragmas(dbapi_conn: sqlite3.Connection) -> None:
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.execute("PRAGMA busy_timeout=5000")
    cursor.execute("PRAGMA synchronous=NORMAL")
    cursor.execute("PRAGMA cache_size=-8000")
    cursor.close()

def get_engine():
    global _engine, _async_session_factory
    if _engine is None:
        settings.db_path.parent.mkdir(parents=True, exist_ok=True)
        _engine = create_async_engine(_database_url(), echo=False)

        @event.listens_for(_engine.sync_engine, "connect")
        def _on_connect(dbapi_conn, _record) -> None:
            _apply_sqlite_pragmas(dbapi_conn)

        _async_session_factory = async_sessionmaker(
            _engine, expire_on_commit=False
        )
    return _engine
```

请求级 session：

```python
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    factory = get_session_factory()
    async with factory() as session:
        yield session
```

要点：

- engine 是进程级单例；
- session 是请求级，`expire_on_commit=False`，提交后还能读对象；
- SQLite PRAGMA 必须每条新连接都设，不能只在第一次设；
- 测试要自己创建 engine/session，并 `dispose()`。

## 3. 迁移执行器

`migrations.py` 使用同步 `sqlite3`，因为迁移是启动时一次性操作：

```python
def migrate(conn: sqlite3.Connection) -> int:
    conn.execute(
        "CREATE TABLE IF NOT EXISTS schema_version (version INTEGER NOT NULL PRIMARY KEY)"
    )
    row = conn.execute("SELECT MAX(version) AS v FROM schema_version").fetchone()
    current = int(row["v"]) if row and row["v"] is not None else 0

    applied = 0
    for path in sorted(MIGRATIONS_DIR.glob("*.sql")):
        version = int(path.name.split("_", 1)[0])
        if version <= current:
            continue
        conn.executescript(path.read_text(encoding="utf-8"))
        conn.execute("INSERT INTO schema_version (version) VALUES (?)", (version,))
        conn.commit()
        applied += 1
    return applied
```

启动时：

```python
def ensure_db() -> bool:
    is_new = not database_file_ready()
    if is_new:
        init_db()
        return True
    _apply_pending_migrations()
    return False
```

规则：

- 迁移文件只增不改；已发布文件不能回头编辑。
- 新字段/表新增 `0020_xxx.sql`。
- 冻结后从 PyInstaller 的 `sys._MEIPASS` 找迁移目录：

```python
if getattr(sys, "frozen", False):
    MIGRATIONS_DIR = Path(sys._MEIPASS) / "app" / "shared" / "db" / "migrations"
```

## 4. 仓储模式

`library/infrastructure/repositories.py`：

```python
def _orm_to_resource(row: ResourceRow) -> Resource:
    extra = _parse_extra(row.extra)
    catalog = _catalog_from_extra(extra)
    rest = {k: v for k, v in extra.items() if k != "catalog"}
    return Resource(
        id=row.id,
        type=ResourceType(row.type),
        storage_kind=StorageKind(row.storage_kind or StorageKind.OWNED.value),
        title=row.title,
        cover_path=row.cover_path,
        status=ResourceStatus(row.status),
        extra=rest,
        timeline_visible=(
            None if row.timeline_visible is None else bool(row.timeline_visible)
        ),
        created_at=row.created_at,
        updated_at=row.updated_at,
        ...
    )
```

仓储职责：

- 把 ORM Row 转成 domain 对象；
- 批量附加分类/标签/缩略图，避免 N+1；
- 提供排序键、keyset 分页、计数；
- 不决定“是否排除合集成员”这类业务规则。

列表查询：

```python
items, keys = await self._resources.list_with_sort_keys(
    type_, status, fetch, offset, order,
    sort=sort, q=query, tag_ids=tags,
    category_ids=expanded_category_ids,
    after_key=cursor_key, after_id=after_id,
    exclude_collected=exclude_collected,
)
```

`list_page` 先判断是否能走全库混排 `list_mixed`，否则走 keyset/offset 组合。

## 5. 当前表结构重点

| 迁移 | 内容 |
|------|------|
| `0001` | resources/files/tags/分类/任务等初始表 |
| `0008` | seasons/episodes/extras，系列结构 |
| `0009` | `storage_kind` owned/indexed，资源类型扩展 |
| `0014` | workbench |
| `0015` | resources.sha256 |
| `0016` | collections / collection_items |
| `0017` | timeline_visible、EXIF GPS |
| `0018` | 每类型分类树、`resource_categories`、旧分类迁移 |
| `0019` | saved_views（保存的时间线筛选） |

新增表/字段时，先看目标表当前定义，再写迁移；不要假设 `0001` 是最新结构。

## 6. 分类迁移的三个关键点

`0018_category_tree.sql`：

1. 建 `categories_new`，增加 `type` / `parent_id` / `is_system`；
2. 把旧分类按资源类型拆成新行；
3. 建 `resource_categories`，把 `resources.category_id` 迁进去。

迁移后：

- 新代码读写 `resource_categories`；
- `resources.category_id` 保留一个版本用于回滚；
- 有孤儿分类时挂到系统“待整理分类”。

## 7. 时间线为什么不建成员表

`0019_saved_views.sql`：

```sql
CREATE TABLE saved_views (
  id, kind, type, name, filters_json, sort, created_at, updated_at
);
```

时间线保存的是规则，不是成员：

- 新资源满足规则会自动出现；
- 不需要导入时批量维护关系；
- 删除时间线不影响资源。

## 8. 测试隔离

正确模式：

```python
self.db_path = self.root / "t.db"
conn = sqlite3.connect(self.db_path)
migrate(conn)
conn.close()
self.engine = create_async_engine(...)
self.factory = async_sessionmaker(self.engine, expire_on_commit=False)
```

不要：

```python
with patch.object(settings, "db_path", self.db_path):
    with TestClient(app) as client: ...
```

`TestClient` 会触发 app lifespan，而 lifespan 使用全局 engine/session，容易读到另一个库，出现“本地过、CI 挂”。

优先测服务层：

```python
async with self.factory() as session:
    service = LibraryQueryService(ResourceRepository(session), ...)
    await service.list_page(...)
```

## 9. 关键点回顾

1. **DB 列 snake_case、Python 字段 snake_case、API camelCase**。
2. JSON 列（`extra`/`filters_json`）显式序列化/反序列化。
3. 每个请求一个 `AsyncSession`，engine 进程级单例。
4. 迁移只增不改，冻结时从 `sys._MEIPASS` 读。
5. 时间线是规则，不是成员表。
6. 测试用临时库 + 自己 migrate，不碰开发库。
7. `resources.category_id` 是回滚兼容字段，不是新代码主路径。

## 10. 延伸阅读

- [01-架构全景.md](01-架构全景.md)
- [06-领域模型-状态机值对象常量.md](06-领域模型-状态机值对象常量.md)
- [25-后端分层与数据访问.md](25-后端分层与数据访问.md)
- [27-媒体库领域与时间线.md](27-媒体库领域与时间线.md)
- `apps/backend/app/shared/db/db.py`
- `apps/backend/app/shared/db/migrations.py`

## 扩展阅读

- [49-图解-导出备份与恢复](49-图解-导出备份与恢复.md)
- [46-图解-分层数据模型与状态机](46-图解-分层数据模型与状态机.md)
