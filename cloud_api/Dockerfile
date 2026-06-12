FROM python:3.11-slim

WORKDIR /app

# 安装基础系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ libffi-dev && \
    rm -rf /var/lib/apt/lists/*

# 安装 Python 依赖（使用官方 PyPI，镜像源对部分包有访问限制）
RUN pip install --no-cache-dir --default-timeout=300 \
    torch \
    sentence-transformers \
    fastapi==0.115.6 \
    uvicorn==0.34.0 \
    pydantic \
    jieba \
    numpy

# 复制代码
COPY spirit_api.py /app/
COPY advanced_spirit_evaluator.py /app/
COPY enhanced_spirit_evaluator.py /app/
COPY spirit_p444_micro.pt /app/
COPY P446_branches/ /app/P446_branches/

# 设置环境变量
ENV PORT=8000
ENV API_KEY=spirit-p444-prod-key
ENV HF_ENDPOINT=https://hf-mirror.com
ENV TRANSFORMERS_CACHE=/app/.cache
ENV TRANSFORMERS_VERBOSITY=error

EXPOSE 8000

# 启动命令
CMD ["python", "spirit_api.py"]
