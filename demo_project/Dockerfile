# =============================================================================
# TenGod Framework Docker 镜像构建
# =============================================================================
# 中华文明数字永生体 · 生产环境部署
# 版本: v2.0
# =============================================================================

# ── 第一阶段：构建 ────────────────────────────────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /build

# 安装构建依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件并安装
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# ── 第二阶段：运行 ────────────────────────────────────────────────────────
FROM python:3.11-slim

# 安装运行时依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    libpq5 \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --shell /bin/bash app

WORKDIR /app

# 复制依赖
COPY --from=builder /root/.local /home/app/.local

# 复制应用代码
COPY --chown=app:app . .

# 设置环境变量
ENV PATH=/home/app/.local/bin:$PATH
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# 切换用户
USER app

# 暴露端口
EXPOSE 8000

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/api/health || exit 1

# 启动命令
CMD ["python", "run_tengod_demo.py"]
