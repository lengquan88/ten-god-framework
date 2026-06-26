#!/bin/bash
# TenGod Framework v2.0 — 容器健康检查
# Docker 在 docker-compose.yml 中通过 healthcheck 指令调用
# v2.0 升级：新增内在小孩健康检查

HOST="${API_HOST:-localhost}"
PORT="${API_PORT:-8000}"
TIMEOUT=5

# 1. 检查 /health/live 端点
response=$(curl -s -o /dev/null -w "%{http_code}" --max-time "$TIMEOUT" "http://${HOST}:${PORT}/health/live" 2>/dev/null)

if [ "$response" != "200" ]; then
    echo "Health check failed: HTTP $response"
    exit 1
fi

# 2. v2.16.1 内在小孩健康检查（可选，不阻塞）
inner_child=$(curl -s --max-time "$TIMEOUT" "http://${HOST}:${PORT}/api/v2/gate/inner-child-stats" 2>/dev/null || echo '{}')
if echo "$inner_child" | grep -q "memory_pool"; then
    echo "✅ 内在小孩状态正常"
else
    echo "⚠️  内在小孩状态不可用（非阻塞）"
fi

exit 0