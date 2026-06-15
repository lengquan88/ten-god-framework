# ═══════════════════════════════════════════════════════════
# 十神架构 · Dockerfile v1.5.0
# 中华文明数字永生体 — 一键部署十神服务 + PostgreSQL
# ═══════════════════════════════════════════════════════════

FROM python:3.11-slim

LABEL maintainer="tengod"
LABEL version="1.5.0"
LABEL description="十神架构 — 中华文明数字永生体"

# 系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Python 环境
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app/demo_project/tengod

WORKDIR /app

# 复制项目
COPY demo_project/ ./demo_project/
COPY .env.example ./.env.example

# 安装依赖
RUN pip install --no-cache-dir -r demo_project/requirements.txt 2>/dev/null || true

# 可选生产级依赖
RUN pip install --no-cache-dir fastapi uvicorn sqlalchemy psycopg2-binary 2>/dev/null || true

# 数据目录
RUN mkdir -p /app/data /app/logs

# 暴露端口
EXPOSE 8000

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# 启动十神 API 服务
CMD ["python", "-c", "import sys; sys.path.insert(0, 'demo_project/tengod'); from core import get_core; c = get_core(); c.run(serve=True, host='0.0.0.0', port=8000, init_seed=True)"]