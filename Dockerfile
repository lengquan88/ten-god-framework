# syntax=docker/dockerfile:1
FROM python:3.11-slim AS base

WORKDIR /app

# 依赖层
FROM base AS deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    git curl build-essential \
    && rm -rf /var/lib/apt/lists/*
COPY requirements.txt* /tmp/
RUN pip install --no-cache-dir -r /tmp/requirements.txt || true
COPY . /app

# 运行层
FROM base AS runtime
WORKDIR /app
COPY --from=deps /usr/local/lib/python*/site-packages /usr/local/lib/python*/site-packages
COPY . /app

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# 默认启动：仅健康检查（API 服务需手动启动）
CMD ["python", "-c", "print('十神架构容器已启动，API 服务请用 docker-compose up 或 python -m tengod.core')"]
