# syntax=docker/dockerfile:1
FROM python:3.11-slim AS base

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY demo_project/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY demo_project/ .

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the application
CMD ["python", "run_tengod_demo.py"]
