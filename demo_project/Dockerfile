# =============================================================================
# TenGod Framework Docker 镜像构建 v2.1
# =============================================================================
# 中华文明数字永生体 · 生产环境部署
# 优化：多阶段构建、层缓存、最小镜像、非root用户
# =============================================================================

# ── 第一阶段：构建依赖 ────────────────────────────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /build

# 安装构建依赖（合并为单层减少镜像大小）
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件（利用 Docker 层缓存）
COPY requirements.txt .

# 安装依赖到用户目录
RUN pip install --no-cache-dir --user -r requirements.txt

# ── 第二阶段：运行时 ──────────────────────────────────────────────────────
FROM python:3.11-slim

# 镜像元数据
LABEL org.opencontainers.image.title="TenGod Framework" \
      org.opencontainers.image.description="中华文明数字永生体 · 命理智能分析系统" \
      org.opencontainers.image.version="2.8.0" \
      org.opencontainers.image.authors="TenGod Team" \
      org.opencontainers.image.licenses="MIT"

# 安装运行时依赖（合并为单层）
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    libpq5 \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --shell /bin/bash app

WORKDIR /app

# 复制依赖（从 builder 阶段）
COPY --from=builder /root/.local /home/app/.local

# 复制应用代码
COPY --chown=app:app . .

# 设置环境变量
ENV PATH=/home/app/.local/bin:$PATH \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    ENV=production

# 切换非 root 用户
USER app

# 暴露端口
EXPOSE 8000

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/api/health || exit 1

# 启动命令
CMD ["python", "run_tengod_demo.py"]
