# 07 · SQLite 迁移执行器 + 仓储层

## 分层位置

```
app/shared/db/
├── db.py            # 连接（WAL/foreign_keys/busy_timeout）、init_db、get_connection 依赖
├── migrations.py    # 迁移执行器
└── migrations/0001_init.sql   # 初始 DDL（9 表）
```

## 连接管理（db.py）

```python
def connect(db_path=None) -> sqlite3.Connection:
    path = db_path or settings.db_path        # 默认 apps/backend/data/library.db
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")   # 多进程/并发
    conn.execute("PRAGMA foreign_keys=ON")    # 外键级联
    conn.execute("PRAGMA busy_timeout=5000")
    return conn

def get_connection():
    """FastAPI 依赖：每请求一个短连接，yield 后自动关闭。"""
    conn = connect()
    try:
        yield conn
    finally:
        conn.close()
```

## 迁移执行器（migrations.py）

```python
def migrate(conn):
    conn.execute("CREATE TABLE IF NOT EXISTS schema_version (version INTEGER PRIMARY KEY)")
    current = conn.execute("SELECT MAX(version) FROM schema_version").fetchone()[0] or 0
    for path in sorted(MIGRATIONS_DIR.glob("*.sql")):     # 按文件名 NNNN_*.sql 排序
        version = int(path.name.split("_", 1)[0])
        if version > current:
            conn.executescript(path.read_text(encoding="utf-8"))
            conn.execute("INSERT INTO schema_version (version) VALUES (?)", (version,))
            conn.commit()
```

- 启动时 `main.py` 的 lifespan 调 `init_db()` → 自动建库 + 升级
- 新表/改表 = 新增一个 `0002_xxx.sql`，不手改旧文件

## 仓储模式（library/infrastructure/repositories.py）

```python
_RESOURCE_COLUMNS = "id, type, title, ..., extra, created_at, updated_at"

def _row_to_resource(row) -> Resource:
    data = dict(row)
    data["extra"] = json.loads(data["extra"] or "{}")   # JSON 列反序列化
    data["type"] = ResourceType(data["type"])           # 字符串 → 枚举
    return Resource(**data)                             # snake_case 字段直接构造

class ResourceRepository:
    def __init__(self, conn): self._conn = conn

    def create(self, resource: Resource) -> Resource:   # 写入 + 回读带 id
        cur = self._conn.execute("INSERT INTO resources (...) VALUES (?,...,?)",
            (resource.type.value, resource.title, ..., json.dumps(resource.extra, ensure_ascii=False)))
        self._conn.commit()
        return self.get(cur.lastrowid)

    def stats(self) -> dict:                            # 概览聚合 SQL
        row = self._conn.execute("SELECT COALESCE(SUM(CASE ...),0) AS image_count, ...").fetchone()
        return dict(row)
```

## 关键点

1. **DB 列 snake_case ↔ 领域模型 snake_case ↔ API camelCase**：仓储层用 snake_case 字段构造模型，序列化交给 `ApiModel` 别名。
2. **JSON 列**（`extra`/`config`/`value`）必须显式 `json.dumps`/`json.loads`。
3. **依赖注入**：端点 `Depends(_service)` → `Depends(get_connection)`（见 01 的 DI 链），每请求一连接、自动关闭。
4. **WAL** 让读不阻塞写；单后端进程（单写者优先）避免跨进程锁竞争。

## 延伸（未做）

- `update`/`delete`、File/Tag/Settings/Adapter/ScrapeJob/DownloadTask 各仓储尚未实现。
- 扫描入库管道（M1）：扫描 → ffprobe/EXIF → 哈希 → resource + file 一并落库。
