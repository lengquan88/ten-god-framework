FROM pytorch/pytorch:2.5.1-cuda12.4-cudnn9-runtime

LABEL maintainer="Mingguang AI"
LABEL description="神似评估器 API — P444 地支藏干 + P446 增量学习架构"

# 系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3-pip \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Python 依赖
RUN pip install --no-cache-dir \
    sentence-transformers==3.4.1 \
    fastapi==0.115.6 \
    uvicorn[standard]==0.34.0 \
    pydantic==2.10.4 \
    jieba==0.42.1

# 镜像站 (中国区部署)
ENV HF_ENDPOINT=https://hf-mirror.com
ENV TRANSFORMERS_VERBOSITY=error

WORKDIR /app

# 复制核心文件
COPY spirit_api.py .
COPY advanced_spirit_evaluator.py .
COPY spirit_p444_micro.pt .
COPY spirit_p444_final.pt .
COPY P446_branches/ ./P446_branches/

# 默认端口
ENV PORT=8000
ENV API_KEY=spirit-p444-prod-key
ENV RATE_LIMIT=60
ENV RATE_WINDOW=60
ENV LOG_DIR=/var/log/spirit_api/

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["python3", "spirit_api.py"]
