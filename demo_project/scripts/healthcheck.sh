#!/bin/bash
# TenGod Framework v2.12 — 容器健康检查
# Docker 在 docker-compose.yml 中通过 healthcheck 指令调用

HOST="${API_HOST:-localhost}"
PORT="${API_PORT:-8000}"
TIMEOUT=5

# 检查 /health/live 端点
response=$(curl -s -o /dev/null -w "%{http_code}" --max-time "$TIMEOUT" "http://${HOST}:${PORT}/health/live" 2>/dev/null)

if [ "$response" = "200" ]; then
    exit 0
else
    echo "Health check failed: HTTP $response"
    exit 1
fi