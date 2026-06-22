# 阶段二十二：数据库升级 — 技术实现方案

> 目标：从 SQLite 升级为 PostgreSQL + Redis，支持生产级数据规模与向量检索
> 依赖：现有 `data_store.py`（已有 SQLAlchemy ORM 抽象层 + PostgreSQL URL 支持）
> 预计工作量：2-3 人/周

---

## 22.0 现状评估

### 当前状态

| 组件 | 现状 | 升级目标 |
|------|------|---------|
| 数据库 | SQLite（`data/tengod.db`），单文件，锁竞争明显 | PostgreSQL 15，MVCC，支持高并发 |
| 缓存 | 无独立缓存层，SQLite 无结果集缓存 | Redis 7，缓存热点查询 + 限流计数 |
| 向量检索 | FAISS 内存索引，进程内，重启需重建 | pgvector PostgreSQL 扩展，持久化存储 |
| 全文检索 | 无，基于 LIKE 扫描全表 | PostgreSQL tsvector + GIN 索引 |
| 连接池 | SQLAlchemy 默认（pool_size=5） | PgBouncer 独立连接池，pool_size=20 |
| 部署 | 单进程，无读/写分离 | 主库 + 读副本（第2期） |

### 现有代码利用

好消息：[data_store.py](file:///workspace/demo_project/tengod/data_store.py#L43-L46) 已内置 PostgreSQL 支持：
```python
DATABASE_URL = os.environ.get("TENGOD_DATABASE_URL", "")
# 已有: psycopg2-binary>=2.9.9 (requirements.txt)
```

[docker-compose.yml](file:///workspace/demo_project/docker-compose.yml#L16-L37) 已有 PostgreSQL + Redis 服务定义。

**实际需完成：** 数据迁移脚本、索引优化、pgvector 向量表、Redis 缓存层、全文检索 API。

---

## 22.1 PostgreSQL 迁移工具（2天）

### 新建文件：`tengod/db_migration.py`

```
├── MigrationManager
│   ├── _connect_sqlite()          # 读取旧 SQLite
│   ├── _connect_postgres()         # 连接目标 PostgreSQL
│   ├── _verify_schema()             # 验证 ORM 模型已建表
│   ├── migrate_users()               # 迁移 users 表
│   ├── migrate_records()              # 迁移 bazi_records 表
│   ├── migrate_case_library()           # 迁移 cases / case_relations
│   ├── migrate_report_cache()           # 迁移 report_cache
│   ├── verify_migration()               # 校验记录数一致
│   └── rollback()                        # 清理目标库（迁移失败时）
└── 命令行入口：python -m tengod.db_migration
                 --sqlite data/tengod.db
                 --postgres postgresql://user:pass@host/db
```

### 迁移流程

```
步骤 1: 验证两端连接 → 步骤 2: 在目标库执行 Base.metadata.create_all()
    → 步骤 3: 分表分批迁移（每批 1000 条）
    → 步骤 4: 同步序列（setval 让 PostgreSQL serial 从最大 id+1 开始）
    → 步骤 5: 校验（两端 COUNT(*) 比较）→ 步骤 6: 生成迁移报告 JSON
```

### 数据完整性保障

- **字段映射：** `TEXT` → `TEXT`，`INTEGER` → `INTEGER`，`DateTime` → `TIMESTAMPTZ`
- **JSON 字段：** SQLite `Text` 存储 JSON 字符串 → PostgreSQL `JSONB`（查询性能提升）
- **外键约束：** SQLite 外键需显式 `PRAGMA foreign_keys=ON` → PostgreSQL 默认启用
- **时区转换：** SQLite 无时区感知 → PostgreSQL `TIMESTAMP WITH TIME ZONE`

---

## 22.2 索引与查询优化（1.5天）

### 索引策略

**BaziRecord 表新增索引：**
```sql
-- 已有索引（SQLite 时代保留）
CREATE INDEX idx_bazi_user_created ON bazi_records(user_id, created_at);
CREATE INDEX idx_bazi_date ON bazi_records(year, month, day);
CREATE INDEX idx_bazi_day_master ON bazi_records(day_master);

-- PostgreSQL 新增
CREATE INDEX idx_bazi_gender ON bazi_records(gender);
CREATE INDEX idx_bazi_created_at ON bazi_records(created_at DESC);
-- 全文索引（GIN）
ALTER TABLE bazi_records ADD COLUMN fts_vector tsvector
    GENERATED ALWAYS AS (
        to_tsvector('simple', COALESCE(label, '') || ' ' || COALESCE(notes, ''))
    ) STORED;
CREATE INDEX idx_bazi_fts ON bazi_records USING GIN(fts_vector);

-- Case 表新增
CREATE INDEX idx_case_category ON cases(category);
CREATE INDEX idx_case_featured ON cases(is_featured) WHERE is_featured = true;
CREATE INDEX idx_case_public ON cases(is_public) WHERE is_public = true;
ALTER TABLE cases ADD COLUMN fts_vector tsvector
    GENERATED ALWAYS AS (
        to_tsvector('simple', COALESCE(title, '') || ' ' ||
                    COALESCE(summary, '') || ' ' || COALESCE(analysis_text, ''))
    ) STORED;
CREATE INDEX idx_case_fts ON cases USING GIN(fts_vector);
```

### 连接池优化 — 修改 `data_store.py`

```python
# data_store.py 中 create_engine 调用修改为：
if self.db_url and "postgres" in self.db_url:
    self.engine = create_engine(
        self.db_url,
        pool_size=20,          # 常驻连接
        max_overflow=30,       # 突发额外连接
        pool_timeout=30,        # 获取连接等待超时
        pool_recycle=1800,       # 30 分钟回收旧连接
        pool_pre_ping=True,       # 连接前检查有效性
        future=True,
    )
else:
    # SQLite 保持原有逻辑
    self.engine = create_engine(f"sqlite:///{self.db_path}", future=True)
```

### EXPLAIN ANALYZE 验证脚本（可选）

新建 `tests/test_query_perf.py`，对关键查询做性能基线：

```python
@pytest.mark.parametrize("query,expected_ms", [
    ("SELECT * FROM bazi_records WHERE user_id = 1 ORDER BY created_at DESC LIMIT 20", 10),
    ("SELECT * FROM cases WHERE category = '事业' AND is_public = true ORDER BY created_at DESC LIMIT 20", 5),
    ("SELECT * FROM cases WHERE fts_vector @@ plainto_tsquery('simple', '伤官') LIMIT 20", 10),
])
def test_query_performance(query, expected_ms):
    """确保关键查询在预期时间内返回"""
    pass
```

---

## 22.3 向量检索升级（pgvector 替代 FAISS）（2天）

### 新建文件：`tengod/vector_store_pg.py`

```python
"""
vector_store_pg.py — PostgreSQL + pgvector 向量存储与语义检索

用 pgvector 扩展替代内存 FAISS 索引，优势：
  1. 持久化（重启不丢失）
  2. 多进程共享（FAISS 为进程内）
  3. SQL 查询 + 向量相似度混合检索
  4. 与 bazi_records / cases 表天然关联

依赖：pip install pgvector
"""

from pgvector.sqlalchemy import Vector
from sqlalchemy import Column, Integer, String, ForeignKey, Index, text

# ── ORM 模型（新增两张向量表） ──

class BaziEmbedding(Base):
    """八字排盘向量嵌入"""
    __tablename__ = "bazi_embeddings"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    record_id: Mapped[int] = mapped_column(Integer, ForeignKey("bazi_records.id", ondelete="CASCADE"), index=True)
    embedding_type: Mapped[str] = mapped_column(String(16))  # "full" / "pillars" / "geju"
    vector = mapped_column(Vector(256))  # 256 维向量
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("idx_bazi_embedding_cosine", text("vector vector_cosine_ops"), postgresql_using="hnsw"),
    )

class CaseEmbedding(Base):
    """案例库向量嵌入"""
    __tablename__ = "case_embeddings"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    case_id: Mapped[int] = mapped_column(Integer, ForeignKey("cases.id", ondelete="CASCADE"), index=True)
    embedding_type: Mapped[str] = mapped_column(String(16))  # "full" / "summary" / "analysis"
    vector = mapped_column(Vector(256))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("idx_case_embedding_cosine", text("vector vector_cosine_ops"), postgresql_using="hnsw"),
    )

# ── 管理类 ──

class VectorStorePG:
    """PostgreSQL 向量存储"""

    def __init__(self, session_factory):
        self.Session = session_factory

    def store_embedding(self, record_id: int, embedding_type: str, vector: List[float]):
        """存入一条向量"""
        with self.Session() as s:
            emb = BaziEmbedding(record_id=record_id, embedding_type=embedding_type, vector=vector)
            s.add(emb)
            s.commit()

    def search_similar(self, query_vector: List[float], top_k: int = 10) -> List[Dict]:
        """余弦相似度搜索"""
        with self.Session() as s:
            results = s.execute(
                text("""
                    SELECT br.id, br.label, br.day_master, 1 - (be.vector <=> :qv) AS similarity
                    FROM bazi_embeddings be
                    JOIN bazi_records br ON br.id = be.record_id
                    WHERE be.embedding_type = 'full'
                    ORDER BY be.vector <=> :qv
                    LIMIT :k
                """),
                {"qv": f"[{','.join(map(str, query_vector))}]", "k": top_k}
            ).fetchall()
            return [{"id": r[0], "label": r[1], "day_master": r[2], "similarity": float(r[3])} for r in results]

    def search_similar_cases(self, query_vector: List[float], top_k: int = 10) -> List[Dict]:
        """案例相似度搜索"""
        # 类似 search_similar，从 case_embeddings 查
        pass

    def rebuild_index(self):
        """重建 HNSW 索引（数据批量导入后调用）"""
        with self.Session() as s:
            s.execute(text("REINDEX INDEX idx_bazi_embedding_cosine"))
            s.execute(text("REINDEX INDEX idx_case_embedding_cosine"))
            s.commit()
```

### 向量生成策略

沿用 `vector_store.py` 的字符级 n-gram hash 方法，保持向后兼容：
```
256维 = sum(hash("年柱庚")) + sum(hash("月柱癸")) + ... + 五行分布计数
```

### 初始化脚本

新建 `tengod/scripts/init_pgvector.py`：
1. 在 PostgreSQL 中 `CREATE EXTENSION IF NOT EXISTS vector;`
2. 创建 `bazi_embeddings` / `case_embeddings` 表
3. 对已有 records/cases 批量生成向量并写入（每批 500 条，避免 OOM）

### requirements.txt 新增

```
pgvector>=0.3.0
```

---

## 22.4 Redis 缓存层（1.5天）

### 新建文件：`tengod/cache_manager.py`

```python
"""
cache_manager.py — Redis 缓存管理

缓存策略：
  - 热点统计：/api/cases/stats, /api/stats/summary  TTL=5min
  - 八字排盘结果：相同输入的 pillars/analysis/shensha  TTL=24h
  - 用户 Session（替代内存 QuotaManager） TTL=24h
  - API 限流滑动窗口 TTL=60s
  - Webhook 订阅状态缓存 TTL=10min

缓存键命名约定：tengod:{component}:{key}
"""

import json
import hashlib
from typing import Any, Dict, Optional, List, Callable
from datetime import timedelta

import redis

# 默认 Redis 连接
DEFAULT_REDIS_URL = os.environ.get("TENGOD_REDIS_URL", "redis://localhost:6379/0")


class CacheManager:
    """Redis 缓存管理器"""

    def __init__(self, redis_url: str = DEFAULT_REDIS_URL):
        self._client = redis.Redis.from_url(redis_url, decode_responses=True)
        self._prefix = "tengod"

    # ── 基础操作 ──

    def get(self, key: str) -> Optional[Any]:
        v = self._client.get(f"{self._prefix}:{key}")
        return json.loads(v) if v else None

    def set(self, key: str, value: Any, ttl: int = 300) -> None:
        self._client.setex(f"{self._prefix}:{key}", ttl, json.dumps(value, ensure_ascii=False))

    def delete(self, key: str) -> None:
        self._client.delete(f"{self._prefix}:{key}")

    def delete_pattern(self, pattern: str) -> int:
        """模糊删除（例如清理某组件全部缓存）"""
        keys = self._client.keys(f"{self._prefix}:{pattern}")
        if keys:
            return self._client.delete(*keys)
        return 0

    # ── 命中逻辑 ──

    def cached(self, key: str, ttl: int) -> Callable:
        """装饰器：函数结果缓存"""
        def decorator(func):
            def wrapper(*args, **kwargs):
                cache_key = f"{key}:{hashlib.md5(str(args)+str(kwargs)).hexdigest()}"
                cached = self.get(cache_key)
                if cached is not None:
                    return cached
                result = func(*args, **kwargs)
                self.set(cache_key, result, ttl)
                return result
            return wrapper
        return decorator

    # ── 专用方法 ──

    def cache_case_stats(self, stats: Dict) -> None:
        self.set("cases:stats", stats, ttl=300)

    def get_case_stats(self) -> Optional[Dict]:
        return self.get("cases:stats")

    def cache_bazi_result(self, input_hash: str, result: Dict) -> None:
        self.set(f"bazi:result:{input_hash}", result, ttl=86400)

    def get_bazi_result(self, input_hash: str) -> Optional[Dict]:
        return self.get(f"bazi:result:{input_hash}")

    def rate_limit(self, user_id: str, endpoint: str, limit: int, window: int = 60) -> bool:
        """滑动窗口限流：True=允许, False=超限"""
        key = f"ratelimit:{user_id}:{endpoint}"
        pipe = self._client.pipeline()
        now = int(time.time())
        pipe.zremrangebyscore(key, 0, now - window)
        pipe.zcard(key)
        pipe.zadd(key, {f"{now}-{secrets.token_hex(4)}": now})
        pipe.expire(key, window)
        _, count, _, _ = pipe.execute()
        return count <= limit

    def get_cache_stats(self) -> Dict:
        """API: /api/cache/stats 使用的统计信息"""
        info = self._client.info()
        return {
            "total_keys": self._client.dbsize(),
            "memory_used_mb": round(info.get("used_memory", 0) / 1048576, 2),
            "hits_approx": info.get("keyspace_hits", 0),
            "misses_approx": info.get("keyspace_misses", 0),
            "connected_clients": info.get("connected_clients", 0),
        }

    def invalidate_component(self, component: str) -> int:
        """清理某组件全部缓存（admin 手动触发）"""
        return self.delete_pattern(f"{component}:*")
```

### API 端点新增

在 `api_server.py` 新增：

```python
@app.get("/api/cache/stats", tags=["缓存管理"], dependencies=[Depends(admin_only)])
async def cache_stats():
    """缓存统计（仅 admin）"""
    from tengod.cache_manager import CacheManager
    return CacheManager().get_cache_stats()

@app.post("/api/cache/invalidate", tags=["缓存管理"], dependencies=[Depends(admin_only)])
async def cache_invalidate(component: str = Query(..., description="要清理的组件名，如 cases/bazi/all")):
    """手动清理缓存（仅 admin）"""
    from tengod.cache_manager import CacheManager
    cm = CacheManager()
    if component == "all":
        count = cm.delete_pattern("*")
    else:
        count = cm.invalidate_component(component)
    return {"invalidated_keys": count, "component": component}
```

### 鉴权辅助：admin_only

在 `auth.py` 新增：
```python
def admin_only(request: Request):
    """Depends 函数：验证当前用户必须是 admin 角色"""
    claims = verify_jwt_from_request(request)
    if claims.get("role") != "admin":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "需要管理员权限")
    return claims
```

---

## 22.5 Docker Compose 升级（0.5天）

### [docker-compose.yml](file:///workspace/demo_project/docker-compose.yml) 修改要点

1. **PostgreSQL 容器启用 pgvector 扩展：** 改用 `pgvector/pgvector:pg15` 镜像（或自建 image）
2. **环境变量传入 TENGOD_DATABASE_URL：** 已存在 ✓
3. **健康检查验证 pgvector：** `test: ["CMD-SHELL", "psql -U user -d db -c 'SELECT * FROM pg_extension WHERE extname = \\\"vector\\\"'"]`
4. **连接池（可选）：** 新增 `pgbouncer` 服务

### 修改后的 docker-compose 关键片段

```yaml
services:
  db:
    # 改用 pgvector 官方镜像（基于 PostgreSQL 15）
    image: pgvector/pgvector:pg15
    container_name: tengod-db
    restart: unless-stopped
    environment:
      POSTGRES_USER: ${POSTGRES_USER:-tengod}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-tengod_secret_2026}
      POSTGRES_DB: ${POSTGRES_DB:-tengod}
      TZ: Asia/Shanghai
    volumes:
      - pg_data:/var/lib/postgresql/data
      - ./docker/init-db.sql:/docker-entrypoint-initdb.d/init-db.sql:ro
      # ── 新增：pgvector 扩展初始化 ──
      - ./docker/init-pgvector.sql:/docker-entrypoint-initdb.d/01-pgvector.sql:ro
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER:-tengod} && psql -U ${POSTGRES_USER:-tengod} -d ${POSTGRES_DB:-tengod} -c 'SELECT 1 FROM pg_extension WHERE extname = \\\"vector\\\"'"]
      interval: 15s
      timeout: 5s
      retries: 5
    networks:
      - tengod_net
```

### 新建：`docker/init-pgvector.sql`

```sql
-- pgvector 扩展初始化
CREATE EXTENSION IF NOT EXISTS vector;

-- 验证
SELECT extname, extversion FROM pg_extension WHERE extname = 'vector';
```

---

## 22.6 全文检索 API（1天）

### 在 `api_server.py` 新增

```python
class FulltextSearchRequest(BaseModel):
    query: str
    scope: Literal["cases", "records", "all"] = "all"
    category: Optional[str] = None
    is_public: Optional[bool] = True
    limit: int = 20
    offset: int = 0

class FulltextSearchHit(BaseModel):
    id: int
    type: str          # "case" | "record"
    title: str
    snippet: str       # 高亮片段
    category: Optional[str]
    day_master: Optional[str]
    score: float

class FulltextSearchResponse(BaseModel):
    total: int
    hits: List[FulltextSearchHit]

@app.post("/api/search/fulltext", tags=["全文检索"])
async def fulltext_search(req: FulltextSearchRequest, request: Request):
    """PostgreSQL tsvector 全文搜索"""
    from tengod.data_store import get_default_store
    store = get_default_store()
    return store.fulltext_search(
        query=req.query, scope=req.scope, category=req.category,
        is_public=req.is_public, limit=req.limit, offset=req.offset
    )
```

### 在 `data_store.py` 实现

```python
def fulltext_search(self, query: str, scope: str = "all", category: Optional[str] = None,
                    is_public: Optional[bool] = True, limit: int = 20, offset: int = 0) -> Dict:
    """PostgreSQL tsvector 全文搜索"""
    with self.Session() as s:
        hits = []
        if scope in ("cases", "all"):
            sql = text("""
                SELECT id, 'case' as type, title, COALESCE(summary, analysis_text),
                       category, NULL, ts_rank(fts_vector, plainto_tsquery('simple', :q)) as score
                FROM cases
                WHERE fts_vector @@ plainto_tsquery('simple', :q)
                  AND (:cat IS NULL OR category = :cat)
                  AND (:pub IS NULL OR is_public = :pub)
                ORDER BY score DESC
                LIMIT :lim OFFSET :off
            """)
            rows = s.execute(sql, {"q": query, "cat": category, "pub": is_public, "lim": limit, "off": offset}).fetchall()
            for r in rows:
                hits.append({"id": r[0], "type": r[1], "title": r[2][:80], "snippet": (r[3] or "")[:200], "category": r[4], "day_master": None, "score": float(r[6])})
        if scope in ("records", "all"):
            sql = text("""
                SELECT id, 'record' as type, COALESCE(label, ''), notes,
                       NULL, day_master, ts_rank(fts_vector, plainto_tsquery('simple', :q)) as score
                FROM bazi_records
                WHERE fts_vector @@ plainto_tsquery('simple', :q)
                ORDER BY score DESC
                LIMIT :lim OFFSET :off
            """)
            rows = s.execute(sql, {"q": query, "lim": limit, "off": offset}).fetchall()
            for r in rows:
                hits.append({"id": r[0], "type": r[1], "title": r[2][:80], "snippet": (r[3] or "")[:200], "category": None, "day_master": r[5], "score": float(r[6])})
        hits.sort(key=lambda x: x["score"], reverse=True)
        return {"total": len(hits), "hits": hits[:limit]}
```

---

## 22.7 测试与验证（1天）

### 新建：`tests/test_postgres_migration.py`

```python
"""PostgreSQL 迁移验证"""

import pytest
import tempfile
from tengod.data_store import DataStore
from tengod.db_migration import MigrationManager


@pytest.fixture(scope="module")
def source_sqlite():
    """源 SQLite 数据库（预先填充测试数据）"""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    store = DataStore(db_path=db_path)
    # 填充测试数据：5 users, 50 records, 10 cases, 20 report_cache entries
    yield store
    store.close()


@pytest.fixture(scope="module")
def target_postgres():
    """目标 PostgreSQL（测试环境临时库）"""
    # 开发环境可跳过：标记 pytest.mark.skipif 当无 PG 连接
    pg_url = os.environ.get("TEST_POSTGRES_URL", "")
    if not pg_url:
        pytest.skip("TEST_POSTGRES_URL 未设置，跳过 PostgreSQL 迁移测试")
    store = DataStore(db_url=pg_url)
    yield store
    store.close()


def test_migration_users(source_sqlite, target_postgres):
    """users 表迁移后记录数一致"""
    mm = MigrationManager(source_sqlite, target_postgres)
    mm.migrate_users()
    src_count = source_sqlite.count_users()
    dst_count = target_postgres.count_users()
    assert src_count == dst_count


def test_migration_records(source_sqlite, target_postgres):
    """bazi_records 表迁移后记录数一致"""
    mm = MigrationManager(source_sqlite, target_postgres)
    mm.migrate_records()
    src = source_sqlite.count_records()
    dst = target_postgres.count_records()
    assert src == dst


def test_migration_cases(source_sqlite, target_postgres):
    """cases / case_relations 表迁移"""
    mm = MigrationManager(source_sqlite, target_postgres)
    mm.migrate_case_library()
    assert source_sqlite.count_cases() == target_postgres.count_cases()


def test_migration_verify(source_sqlite, target_postgres):
    """完整迁移 + 校验"""
    mm = MigrationManager(source_sqlite, target_postgres)
    report = mm.migrate_all()
    assert report["status"] == "success"
    assert report["tables"]["users"]["source_count"] == report["tables"]["users"]["target_count"]
```

### 新建：`tests/test_redis_cache.py`

```python
@pytest.fixture
def redis_client():
    """测试 Redis 连接"""
    url = os.environ.get("TEST_REDIS_URL", "redis://localhost:6379/1")
    from tengod.cache_manager import CacheManager
    return CacheManager(url)


def test_cache_set_get(redis_client):
    redis_client.set("test:foo", {"a": 1, "b": "测试"}, ttl=60)
    v = redis_client.get("test:foo")
    assert v == {"a": 1, "b": "测试"}


def test_cache_expiry(redis_client):
    redis_client.set("test:expire", "value", ttl=1)
    import time; time.sleep(1.1)
    assert redis_client.get("test:expire") is None


def test_rate_limit(redis_client):
    user = "test_user_123"
    endpoint = "bazi:calc"
    for _ in range(10):  # 在 window 内允许
        assert redis_client.rate_limit(user, endpoint, limit=10, window=60)
    assert not redis_client.rate_limit(user, endpoint, limit=10, window=60)  # 第11次拒绝
```

### 新建：`tests/test_pgvector.py`

```python
@pytest.fixture
def pg_store():
    pg_url = os.environ.get("TEST_POSTGRES_URL", "")
    if not pg_url:
        pytest.skip("TEST_POSTGRES_URL 未设置")
    from tengod.data_store import DataStore
    return DataStore(db_url=pg_url)


def test_vector_store_embedding(pg_store):
    """向量存入与检索"""
    from tengod.vector_store_pg import VectorStorePG
    vs = VectorStorePG(pg_store.Session)
    vs.store_embedding(record_id=1, embedding_type="full", vector=[0.1] * 256)
    results = vs.search_similar(query_vector=[0.1] * 256, top_k=5)
    assert len(results) >= 1


def test_vector_store_similarity(pg_store):
    """余弦相似度验证"""
    from tengod.vector_store_pg import VectorStorePG
    vs = VectorStorePG(pg_store.Session)
    vs.store_embedding(record_id=100, embedding_type="full", vector=[1.0] + [0.0] * 255)
    vs.store_embedding(record_id=101, embedding_type="full", vector=[0.99] + [0.0] * 255)
    results = vs.search_similar(query_vector=[1.0] + [0.0] * 255, top_k=2)
    assert results[0]["similarity"] > 0.95  # 几乎完全一致
```

---

## 22.8 性能监控面板（0.5天）

### 在 `api_server.py` 新增

```python
@app.get("/api/db/stats", tags=["数据库监控"], dependencies=[Depends(admin_only)])
async def db_stats():
    """PostgreSQL 性能指标（仅 admin）"""
    from tengod.data_store import get_default_store
    store = get_default_store()
    return store.get_db_performance_stats()
```

### 在 `data_store.py` 实现

```python
def get_db_performance_stats(self) -> Dict:
    """PostgreSQL 性能指标"""
    if not self.db_url or "postgres" not in self.db_url:
        return {"error": "当前非 PostgreSQL 模式"}
    with self.Session() as s:
        stats = {}
        # 表行数
        for table in ["users", "bazi_records", "cases", "case_relations", "report_cache"]:
            c = s.execute(text(f"SELECT count(*) FROM {table}")).scalar()
            stats[f"rows_{table}"] = c
        # 缓存命中率
        cache_hit = s.execute(text("SELECT sum(heap_blks_hit) / (sum(heap_blks_hit) + sum(heap_blks_read) + 1e-9) FROM pg_stat_user_tables")).scalar()
        stats["cache_hit_ratio"] = round(float(cache_hit), 4) if cache_hit else 0
        # 索引使用率
        idx_usage = s.execute(text("SELECT sum(idx_scan) / (sum(idx_scan) + sum(seq_scan) + 1e-9) FROM pg_stat_user_tables")).scalar()
        stats["index_hit_ratio"] = round(float(idx_usage), 4) if idx_usage else 0
        return stats
```

---

## 22.9 文件结构汇总

```
新增文件:
  tengod/db_migration.py              # 迁移管理器
  tengod/vector_store_pg.py           # pgvector 向量层（替代 FAISS）
  tengod/cache_manager.py             # Redis 缓存 + 限流
  tengod/scripts/init_pgvector.py     # 向量表初始化脚本
  docker/init-pgvector.sql            # 扩展启用脚本

修改文件:
  docker-compose.yml                  # db 容器改用 pgvector 镜像
  requirements.txt                    # 添加 pgvector>=0.3.0
  data_store.py                       # 连接池优化 + 全文检索 + 性能统计
  auth.py                             # 新增 admin_only 依赖函数
  api_server.py                       # 新增 /api/search/fulltext, /api/cache/*, /api/db/stats

测试文件:
  tests/test_postgres_migration.py    # 迁移验证
  tests/test_redis_cache.py           # 缓存 + 限流测试
  tests/test_pgvector.py              # pgvector 向量测试
```

---

## 22.10 风险与缓解

| 风险 | 概率 | 影响 | 缓解方案 |
|------|------|------|---------|
| 生产数据迁移期间服务中断 | 中 | 高 | 停机窗口迁移（夜间），或逻辑复制双写 |
| pgvector 扩展不可用（官方镜像） | 低 | 中 | 备选：Dockerfile 手动安装扩展 |
| Redis 未启动导致关键功能故障 | 低 | 中 | 降级：无 Redis 时回退为内存缓存 |
| 全文检索大表扫描性能差 | 中 | 低 | 预先生成 GIN 索引 + limit 分页 |
| SQL 注入风险（text() 动态查询） | 低 | 高 | 严格使用参数绑定，不拼接用户输入 |

---

## 22.11 实施顺序

```
第1天:
  □ db_migration.py 迁移工具实现
  □ docker-compose.yml 修改 + init-pgvector.sql
  □ 本地测试：SQLite → PostgreSQL 迁移

第2天:
  □ vector_store_pg.py pgvector 向量层
  □ init_pgvector.py 批量向量生成脚本
  □ data_store.py 索引优化 + 全文检索

第3天:
  □ cache_manager.py Redis 缓存 + 限流
  □ /api/cache/* 与 /api/db/stats 端点
  □ 测试与性能验证（tests/test_postgres_migration.py + test_pgvector.py + test_redis_cache.py）

第4-5天:
  □ 生产环境部署演练
  □ 文档编写（迁移指南、运维手册）
```
