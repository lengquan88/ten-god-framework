# 阶段二十九：性能与可靠性 — 技术实现方案

> 目标：达到生产级 SLA 标准（99.9% 可用性，P95 < 200ms，故障恢复 < 30s）
> 依赖：现有 `docker-compose.yml`（PostgreSQL + Redis）、`api_server.py`
> 预计工作量：3-4 人/周

---

## 29.0 架构总览

```
              ┌─ 外部流量 ───┐
              │   (Nginx)     │
              └──────┬────────┘
                     ▼
         ┌─ Load Balancer / 灰度路由 ─┐
         │   (Nginx upstream + 权重)   │
         └┬──────────┬──────────┬──────┘
          ▼          ▼          ▼
     FastAPI v1   FastAPI v2  FastAPI (灰度)
     (90% 流量)  (10% 流量)  (新功能 1%)
          │          │          │
          └──────┬───┴──────────┘
                 ▼
         ┌──────────────────┐
         │  Redis Cache 层   │
         │  · 热点数据        │
         │  · API 限流        │
         │  · Session         │
         │  · Webhook 队列    │
         └──────┬───────────┘
                ▼
         ┌────────────────────┐
         │  PostgreSQL 主从   │
         │  · Master (写/最新读) │
         │  · Replica × 2 (读)   │
         │  · PgBouncer 连接池   │
         └──────┬──────────────┘
                ▼
         ┌─ 监控 & 告警 ───┐
         │  Prometheus / Grafana  │
         │  · API 错误率 (>1%)    │
         │  · P99 延迟 (>1s)      │
         │  · 连接池耗尽           │
         │  · 健康检查             │
         └─────────────────────────┘
```

---

## 29.1 Redis 缓存深度集成（1天）

### 缓存策略矩阵

| 数据类型 | 缓存 TTL | 缓存 Key 模式 | 失效策略 |
|---------|---------|--------------|---------|
| 案例详情（公开） | 5 min | `case:{id}` | 案例更新时主动删除 |
| 案例列表 | 2 min | `cases:list:{category}:{page}` | 批量删除 `cases:list:*` |
| 案例统计 | 5 min | `cases:stats` | 定时更新 |
| 八字排盘结果（静态） | 24 h | `bazi:result:{input_hash}` | 自动过期 |
| 知识图谱查询 | 10 min | `kg:query:{hash}` | LRU 淘汰 |
| AI 解读结果 | 1 h | `ai:interpret:{hash}` | 手动失效 |
| 用户 Session | 24 h | `session:{user_id}` | 登出主动删除 |
| Feature Flag | 5 min | `config:flags` | 管理员更新时主动 delete |

### 缓存实现代码模板

```python
# tengod/cache_manager.py
import json, hashlib, time, os
from typing import Any, Callable, Optional
import redis

class CacheManager:
    def __init__(self, redis_url=None):
        url = redis_url or os.environ.get("TENGOD_REDIS_URL", "redis://localhost:6379/0")
        self._client = redis.Redis.from_url(url, decode_responses=True)
        self._prefix = "tengod"

    # ── 基础操作 ──
    def get(self, key: str) -> Optional[Any]:
        val = self._client.get(f"{self._prefix}:{key}")
        return json.loads(val) if val else None

    def set(self, key: str, value: Any, ttl_seconds: int = 300) -> None:
        self._client.setex(f"{self._prefix}:{key}", ttl_seconds, json.dumps(value, ensure_ascii=False))

    def delete(self, key: str) -> None:
        self._client.delete(f"{self._prefix}:{key}")

    def delete_pattern(self, pattern: str) -> int:
        """模糊删除：按前缀批量失效"""
        keys = self._client.keys(f"{self._prefix}:{pattern}")
        if keys:
            return self._client.delete(*keys)
        return 0

    # ── 装饰器：函数结果缓存 ──
    def cached(self, ttl_seconds: int, key_prefix: str = ""):
        def decorator(func):
            def wrapper(*args, **kwargs):
                # 构造缓存 key: 使用位置参数 + 关键字参数 hash
                args_str = hashlib.md5(str(args).encode()).hexdigest()[:8]
                kwargs_str = hashlib.md5(str(sorted(kwargs.items())).encode()).hexdigest()[:8]
                cache_key = f"{key_prefix or func.__name__}:{args_str}:{kwargs_str}"
                cached = self.get(cache_key)
                if cached is not None:
                    return cached
                result = func(*args, **kwargs)
                self.set(cache_key, result, ttl_seconds)
                return result
            return wrapper
        return decorator

    # ── 限流：滑动窗口 ──
    def rate_limit(self, key: str, limit: int, window_seconds: int = 60) -> bool:
        """返回 True=允许, False=超限"""
        pipe = self._client.pipeline()
        now = time.time()
        full_key = f"{self._prefix}:ratelimit:{key}"
        pipe.zremrangebyscore(full_key, 0, now - window_seconds)
        pipe.zcard(full_key)
        pipe.zadd(full_key, {f"{now}-{os.urandom(4).hex()}": now})
        pipe.expire(full_key, window_seconds)
        _, count, _, _ = pipe.execute()
        return count <= limit

    # ── 缓存统计 ──
    def get_stats(self) -> dict:
        info = self._client.info()
        return {
            "keys": self._client.dbsize(),
            "memory_mb": round(info.get("used_memory", 0) / 1048576, 2),
            "hits_approx": info.get("keyspace_hits", 0),
            "misses_approx": info.get("keyspace_misses", 0),
            "connected_clients": info.get("connected_clients", 0),
            "uptime_seconds": info.get("uptime_in_seconds", 0),
        }

    def invalidate_component(self, component: str) -> int:
        """清理某组件全部缓存"""
        return self.delete_pattern(f"{component}:*")

    def ping(self) -> bool:
        try:
            return self._client.ping()
        except:
            return False

# 全局单例
_cache_instance = None
def get_cache() -> CacheManager:
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = CacheManager()
    return _cache_instance
```

### API 端点新增

```python
@app.get("/api/cache/stats", tags=["缓存"], dependencies=[Depends(admin_only)])
async def cache_stats():
    """Redis 缓存使用统计（仅 admin）"""
    from tengod.cache_manager import get_cache
    return get_cache().get_stats()

@app.post("/api/cache/invalidate", tags=["缓存"], dependencies=[Depends(admin_only)])
async def cache_invalidate(component: str = Query(..., description="组件名如 cases/bazi/all")):
    """手动失效缓存"""
    from tengod.cache_manager import get_cache
    cm = get_cache()
    if component == "all":
        count = cm.delete_pattern("*")
    else:
        count = cm.invalidate_component(component)
    return {"invalidated_keys": count, "component": component}

@app.get("/api/cache/health", tags=["缓存"])
async def cache_health():
    """Redis 健康检查（是否可用）"""
    from tengod.cache_manager import get_cache
    return {"redis_connected": get_cache().ping()}
```

---

## 29.2 数据库读写分离（1天）

### PgBouncer 连接池配置

```
# docker-compose.yml 中新增
services:
  pgbouncer:
    image: edoburu/pgbouncer:latest
    container_name: tengod-pgbouncer
    environment:
      DATABASE_URL: postgres://${POSTGRES_USER}:${POSTGRES_PASSWORD}@db:5432/${POSTGRES_DB}
      POOL_SIZE: 50
      MAX_DB_CONNECTIONS: 200
      DEFAULT_POOL_SIZE: 20
      ADMIN_USERS: ${POSTGRES_USER}
    ports:
      - "6432:6432"
    depends_on:
      - db
    networks:
      - tengod_net
```

### SQLAlchemy 双引擎配置

```python
# tengod/data_store.py — 修改 DataStore.__init__()
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

class DataStore:
    def __init__(self, db_url: str = None, read_replica_urls: list = None):
        # 主库（写 + 实时读）
        self._master_engine = create_engine(
            db_url or os.environ.get("TENGOD_DATABASE_URL"),
            pool_size=20, max_overflow=30, pool_timeout=30, pool_recycle=1800,
            pool_pre_ping=True, future=True
        )
        self.Session = sessionmaker(bind=self._master_engine)

        # 读副本（可选，round-robin）
        self._read_engines = []
        if read_replica_urls or os.environ.get("TENGOD_READ_REPLICA_URLS"):
            urls = read_replica_urls or os.environ.get("TENGOD_READ_REPLICA_URLS", "").split(",")
            for url in urls:
                if url:
                    self._read_engines.append(create_engine(
                        url, pool_size=15, max_overflow=20, pool_pre_ping=True, future=True
                    ))
        self._read_counter = 0

        # 创建表结构
        Base.metadata.create_all(self._master_engine)

    def _get_read_session(self):
        """获取只读 session（优先读副本，无则主库）"""
        if self._read_engines:
            engine = self._read_engines[self._read_counter % len(self._read_engines)]
            self._read_counter += 1
            return sessionmaker(bind=engine)()
        return self.Session()

    # ── 示例：将只读查询路由到副本 ──
    def list_cases_read_only(self, category=None, limit=20, offset=0):
        with self._get_read_session() as s:
            q = s.query(Case).filter(Case.is_public == True)
            if category: q = q.filter(Case.category == category)
            return [c.to_dict() for c in q.order_by(Case.created_at.desc()).offset(offset).limit(limit).all()]
```

---

## 29.3 灰度发布机制（1天）

### Feature Flag 增强

```python
# 基于用户 ID 的灰度发布
def is_feature_enabled_for_user(feature_key: str, user_id: int) -> bool:
    """
    根据用户 ID 判断是否启用某功能
    策略:
      1. 读 feature_flags 表获取配置（格式: {"enabled": true, "ratio": 0.1, "include_users": []}）
      2. 固定用户: user_id 在 include_users 列表中 → 启用
      3. 比例用户: hash(user_id) % 100 < (ratio * 100) → 启用
      4. 其他: 禁用
    """
    from tengod.cache_manager import get_cache
    cache_key = f"flags:{feature_key}"
    config = get_cache().get(cache_key)
    if config is None:
        # 缓存 miss，从数据库读
        with get_default_store().Session() as s:
            flag = s.query(FeatureFlag).filter(FeatureFlag.flag_key == feature_key).first()
            if not flag:
                return False  # 未配置，默认关闭
            config = json.loads(flag.flag_value) if flag.flag_value.startswith("{") else {"enabled": flag.flag_value == "true", "ratio": 1.0, "include_users": []}
            get_cache().set(cache_key, config, ttl_seconds=300)

    if not config.get("enabled", False):
        return False
    if user_id in config.get("include_users", []):
        return True
    # 基于 user_id 稳定 hash 的比例控制
    ratio = config.get("ratio", 0.0)
    if ratio >= 1.0:
        return True
    import hashlib
    h = int(hashlib.md5(str(user_id).encode()).hexdigest(), 16)
    return (h % 10000) / 10000.0 < ratio

# 灰度端点保护装饰器
def require_feature(feature_key: str):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, request: Request = None, **kwargs):
            claims = _extract_jwt_claims(request) if request else {}
            user_id = claims.get("user_id", 0)
            if not is_feature_enabled_for_user(feature_key, user_id):
                raise HTTPException(403, "此功能正在灰度测试，尚未开放给您")
            return await func(*args, request=request, **kwargs)
        return wrapper
    return decorator

# 使用：
@app.get("/api/some-new-feature")
@require_feature("new_feature_v2")
async def new_feature_endpoint(request: Request):
    return {"status": "ok"}
```

### 基于权重的 API 路由（Nginx 级）

```nginx
# nginx.conf — 灰度路由示例
upstream api_pool {
    server api_v1:8000 weight=90;    # 稳定版本 90%
    server api_v2:8000 weight=10;    # 新版本 10%
}

# 或基于 Cookie 的灰度（如 cookie=canary=true）
map $cookie_feature_flag $upstream {
    default api_v1;
    v2      api_v2;
    canary  api_v2;
}

server {
    location /api/ {
        proxy_pass http://$upstream;
    }
}
```

---

## 29.4 灾备与监控（1天）

### PostgreSQL 主从自动切换（简化方案）

```bash
# docker-compose healthcheck
services:
  db:
    image: postgres:15-alpine
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER} -d ${POSTGRES_DB}"]
      interval: 10s
      timeout: 5s
      retries: 3
      start_period: 30s

  api:
    healthcheck:
      test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/health')"]
      interval: 30s
      timeout: 10s
      retries: 3
```

### Prometheus 指标 + Grafana 大盘

```python
# 在 api_server.py 中增加 /metrics 端点（集成 prometheus_client）
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST

# 定义指标
REQUEST_COUNT = Counter("http_requests_total", "Total HTTP requests", ["method", "endpoint", "status"])
REQUEST_LATENCY = Histogram("http_request_duration_seconds", "HTTP request latency", ["endpoint"])
DB_ERRORS = Counter("db_errors_total", "Database errors", ["operation"])
CACHE_HITS = Counter("cache_hits_total", "Cache hits", ["component"])

# 中间件：记录请求
@app.middleware("http")
async def record_metrics(request: Request, call_next):
    start = time.time()
    response = await call_next(request)
    latency = time.time() - start
    REQUEST_COUNT.labels(request.method, request.url.path, response.status_code).inc()
    REQUEST_LATENCY.labels(request.url.path).observe(latency)
    return response

@app.get("/metrics")
async def metrics():
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
```

```yaml
# prometheus.yml 新增
scrape_configs:
  - job_name: "tengod-api"
    static_configs:
      - targets: ["api:8000"]
    metrics_path: "/metrics"
    scrape_interval: 15s

# 告警规则
groups:
  - name: tengod_alerts
    rules:
      - alert: HighErrorRate
        expr: sum(rate(http_requests_total{status=~"5.*"}[5m])) / sum(rate(http_requests_total[5m])) > 0.01
        for: 2m
        labels: { severity: critical }
        annotations: { summary: "API 错误率 > 1%" }

      - alert: HighP99Latency
        expr: histogram_quantile(0.99, rate(http_request_duration_seconds_sum[5m])) > 1
        for: 5m
        labels: { severity: warning }
        annotations: { summary: "P99 延迟 > 1s" }

      - alert: RedisDown
        expr: redis_up == 0
        for: 1m
        labels: { severity: critical }
```

### 结构化日志（JSON）

```python
# tengod/logging_config.py
import logging, json, time, traceback
from datetime import datetime, timezone

class JsonFormatter(logging.Formatter):
    def format(self, record):
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
            "module": record.module,
            "funcName": record.funcName,
            "line": record.lineno,
        }
        if hasattr(record, "user_id"): log_entry["user_id"] = record.user_id
        if hasattr(record, "request_id"): log_entry["request_id"] = record.request_id
        if record.exc_info:
            log_entry["exception"] = traceback.format_exception(*record.exc_info)
        return json.dumps(log_entry, ensure_ascii=False)

def setup_logging(level=logging.INFO):
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    logging.basicConfig(level=level, handlers=[handler])
```

---

## 29.5 API 健康检查增强（0.5天）

```python
@app.get("/api/health")
async def health_check():
    """增强版健康检查：数据库+缓存+核心服务"""
    from tengod.cache_manager import get_cache
    from tengod.data_store import get_default_store

    db_ok = get_default_store().ping_db()
    redis_ok = get_cache().ping()
    overall = "healthy" if (db_ok and redis_ok) else "degraded"

    return {
        "status": overall,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "services": {
            "database": "ok" if db_ok else "fail",
            "redis": "ok" if redis_ok else "fail",
            "api": "ok",
        },
        "version": "3.0.0"
    }

@app.get("/api/health/detailed", dependencies=[Depends(admin_only)])
async def health_check_detailed():
    """详细健康检查（admin 可见）"""
    from tengod.cache_manager import get_cache
    from tengod.data_store import get_default_store
    store = get_default_store()
    cm = get_cache()

    return {
        "status": "healthy",
        "database": {
            "connected": store.ping_db(),
            "pool_size": store._master_engine.pool.size() if hasattr(store._master_engine.pool, "size") else None,
            "pool_overflow": store._master_engine.pool.overflow() if hasattr(store._master_engine.pool, "overflow") else None,
        },
        "redis": cm.get_stats(),
        "pending_webhooks": store.count_pending_webhooks() if hasattr(store, "count_pending_webhooks") else None,
        "api_process_time_ms": 0,  # 由调用者测量
    }
```

---

## 29.6 文件结构汇总

```
新增:
  tengod/cache_manager.py     # Redis 缓存管理器（装饰器/限流/统计）
  tengod/logging_config.py    # JSON 结构化日志

修改:
  tengod/data_store.py        # 双引擎（主+读副本）+ ping_db()
  tengod/api_server.py        # /metrics + /cache/* + 增强 health + 灰度装饰器
  docker-compose.yml          # PgBouncer + Prometheus + Grafana + Nginx 灰度权重
  requirements.txt            # 添加 redis>=5.0.0, prometheus-client>=0.19.0

配置文件:
  config/prometheus.yml       # Prometheus 抓取配置
  config/alert_rules.yml      # 告警规则
  config/grafana-dashboard.json # Grafana 仪表盘模板
```

---

## 29.7 实施顺序

```
第1天:   Redis 缓存深度集成 + 缓存端点
第2天:   PgBouncer 连接池 + 数据库读写分离
第3天:   灰度发布（Feature Flag + 路由权重）
第4天:   监控(Prometheus/Grafana) + 结构化日志 + 健康检查
```

---

## 29.8 风险与缓解

| 风险 | 概率 | 影响 | 缓解方案 |
|------|------|------|---------|
| Redis 未启动导致所有请求失败 | 低 | 高 | 降级：无 Redis 时回退为内存 dict 缓存（开发模式） |
| 缓存雪崩（大量同时过期） | 中 | 中 | TTL 随机抖动（±10%），分批次预热 |
| 读副本延迟导致读到旧数据 | 低 | 中 | 关键业务（如登录）强制走主库 |
| 灰度发布错误路由 | 中 | 中 | Feature Flag 每端点独立控制，默认关闭，后台可开关 |
| Prometheus 指标爆炸 | 中 | 低 | 控制 Cardinality（指标维度不超 5），定期归档 |
