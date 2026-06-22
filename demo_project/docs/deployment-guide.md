# 生产部署指南

## 1. Docker 部署
```bash
docker build -t tengod:latest .
docker run -d --name tengod -p 8000:8000 \
  -e TENGOD_DB_URL=/data/tengod.db \
  -v $(pwd)/data:/data tengod:latest
```

## 2. Docker Compose (推荐)
```yaml
version: '3.8'
services:
  redis:
    image: redis:7-alpine
    ports: ['6379:6379']
  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: tengod
      POSTGRES_USER: tengod
      POSTGRES_PASSWORD: secret
    ports: ['5432:5432']
  tengod:
    image: tengod:latest
    ports: ['8000:8000']
    environment:
      TENGOD_REDIS_URL: redis://redis:6379/0
      TENGOD_DB_URL: postgresql://tengod:secret@postgres:5432/tengod
```

## 3. 生产环境关键变量
- `TENGOD_DB_URL`             主数据库地址（SQLite/Postgres）
- `TENGOD_REDIS_URL`          缓存/限流 Redis
- `TENGOD_API_KEY`            对外 API 鉴权密钥
- `TENGOD_WORKERS`            Gunicorn worker 数量

## 4. 健康检查
```bash
curl http://localhost:8000/api/health
curl http://localhost:8000/api/health/full
```

## 5. 性能与可靠性
使用 `tengod.reliability` 模块：
- `RateLimiter`  限流保护
- `CircuitBreaker` 熔断器
- `EnhancedHealthChecker` 综合健康检查
