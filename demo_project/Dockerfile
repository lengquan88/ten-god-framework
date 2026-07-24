# =============================================================================
# TenGod Framework Docker 镜像构建 v4.0.0
# =============================================================================
# 中华文明数字永生体 · v4.1.0「集成贯通」
# 升级：门禁认知引擎 + 向量存储 + 语料库 + 评估框架 + 知识图谱桥接
# =============================================================================

# ── 第一阶段：构建依赖 ────────────────────────────────────────────────────
FROM python:3.14-slim AS builder

WORKDIR /build

# 安装构建依赖（合并为单层减少镜像大小）
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件（利用 Docker 层缓存）
COPY requirements.txt .

# 安装依赖到用户目录
RUN pip install --no-cache-dir --user -r requirements.txt

# 预下载 SentenceTransformer 模型（可选，加速首次启动）
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')" 2>/dev/null || true

# ── 第二阶段：运行时 ──────────────────────────────────────────────────────
FROM python:3.14-slim

# 镜像元数据
LABEL org.opencontainers.image.title="TenGod Framework" \
      org.opencontainers.image.description="中华文明数字永生体 · 门禁认知系统 v4.1.0" \
      org.opencontainers.image.version="4.1.0" \
      org.opencontainers.image.authors="TenGod Team" \
      org.opencontainers.image.licenses="MIT"

# 安装运行时依赖（合并为单层）
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    libpq5 \
    libgomp1 \
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
    ENV=production \
    HF_HOME=/home/app/.cache/huggingface \
    INNER_CHILD_ALERTNESS=32.0 \
    INNER_CHILD_PHI_LIMIT=0.8 \
    INNER_CHILD_BETA_LIMIT=0.7

# 切换非 root 用户
USER app

# 暴露端口
EXPOSE 8000

# 健康检查（含内在小孩状态）
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/api/health || exit 1

# 启动命令（使用 exec 形式 + SIGTERM 信号传递）
# uvicorn 默认处理 SIGTERM 实现优雅关闭
CMD ["python", "-m", "uvicorn", "tengod.api_server:app", "--host", "0.0.0.0", "--port", "8000", "--graceful-timeout", "15"]