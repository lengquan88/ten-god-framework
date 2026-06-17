#!/bin/bash
# ============================================================================
# 中华文明数字永生体 · 部署脚本
# 阶段十二：生产化部署运维
# ============================================================================
# 用法：
#   ./deploy.sh build    - 构建镜像
#   ./deploy.sh up       - 启动所有服务
#   ./deploy.sh down     - 停止所有服务
#   ./deploy.sh restart  - 重启所有服务
#   ./deploy.sh logs     - 查看日志
#   ./deploy.sh status   - 查看服务状态
#   ./deploy.sh health   - 健康检查
#   ./deploy.sh backup   - 数据库备份
#   ./deploy.sh clean    - 清理（慎用，会删除数据）
# ============================================================================

set -e

COMPOSE_FILE="docker-compose.yml"
PROJECT_NAME="tengod"

# 颜色
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info()  { echo -e "${GREEN}[INFO]${NC}  $1"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC}  $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# 检查 .env
check_env() {
    if [ ! -f .env ]; then
        log_warn ".env 文件不存在，从模板创建..."
        cp .env.example .env
        log_warn "请编辑 .env 文件修改敏感配置"
    fi
}

# 构建镜像
build() {
    log_info "构建 Docker 镜像..."
    docker-compose -f $COMPOSE_FILE build --no-cache
    log_info "构建完成"
}

# 启动服务
up() {
    check_env
    log_info "启动服务..."
    docker-compose -f $COMPOSE_FILE up -d
    log_info "等待服务就绪..."
    sleep 10
    health
}

# 停止服务
down() {
    log_info "停止服务..."
    docker-compose -f $COMPOSE_FILE down
    log_info "服务已停止"
}

# 重启服务
restart() {
    log_info "重启服务..."
    docker-compose -f $COMPOSE_FILE restart
    sleep 5
    health
}

# 查看日志
logs() {
    local service=${1:-}
    if [ -n "$service" ]; then
        docker-compose -f $COMPOSE_FILE logs -f --tail=100 $service
    else
        docker-compose -f $COMPOSE_FILE logs -f --tail=100
    fi
}

# 查看状态
status() {
    log_info "服务状态："
    docker-compose -f $COMPOSE_FILE ps
    echo ""
    log_info "资源使用："
    docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}" $(docker-compose -f $COMPOSE_FILE ps -q) 2>/dev/null || true
}

# 健康检查
health() {
    log_info "执行健康检查..."
    local ok=true

    # API 健康检查
    if curl -sf http://localhost:8000/api/health > /dev/null 2>&1; then
        log_info "API: ✅ 健康"
    else
        log_error "API: ❌ 不可达"
        ok=false
    fi

    # 全面健康检查
    if curl -sf http://localhost:8000/api/health/full > /dev/null 2>&1; then
        log_info "全面检查: ✅ 通过"
        curl -s http://localhost:8000/api/health/full | python3 -m json.tool 2>/dev/null || true
    else
        log_warn "全面检查: ⚠️ 部分组件异常"
    fi

    # Prometheus 指标
    if curl -sf http://localhost:8000/metrics > /dev/null 2>&1; then
        log_info "指标端点: ✅ 可用"
    else
        log_warn "指标端点: ⚠️ 不可达"
    fi

    if $ok; then
        log_info "✅ 健康检查通过"
    else
        log_error "❌ 健康检查失败"
        exit 1
    fi
}

# 数据库备份
backup() {
    log_info "执行数据库备份..."
    local ts=$(date +%Y%m%d_%H%M%S)
    local backup_file="backups/tengod_backup_${ts}.sql"

    mkdir -p backups

    # PostgreSQL 备份
    docker-compose -f $COMPOSE_FILE exec -T db pg_dump -U tengod tengod > $backup_file 2>/dev/null || {
        log_warn "PostgreSQL 备份失败，尝试 JSON 导出..."
        curl -s -X POST http://localhost:8000/api/records > "backups/tengod_records_${ts}.json" || true
    }

    if [ -f "$backup_file" ] && [ -s "$backup_file" ]; then
        log_info "备份完成: $backup_file ($(du -h $backup_file | cut -f1))"
    fi
}

# 清理
clean() {
    log_warn "此操作将删除所有数据，确认请输入 YES："
    read -r confirm
    if [ "$confirm" = "YES" ]; then
        log_error "清理所有数据和容器..."
        docker-compose -f $COMPOSE_FILE down -v
        docker system prune -f
        log_info "清理完成"
    else
        log_info "已取消"
    fi
}

# 主入口
case "${1:-help}" in
    build)   build ;;
    up)      up ;;
    down)    down ;;
    restart) restart ;;
    logs)    shift; logs "$@" ;;
    status)  status ;;
    health)  health ;;
    backup)  backup ;;
    clean)   clean ;;
    *)
        echo "用法: $0 {build|up|down|restart|logs|status|health|backup|clean}"
        echo ""
        echo "命令说明："
        echo "  build    - 构建 Docker 镜像"
        echo "  up       - 启动所有服务"
        echo "  down     - 停止所有服务"
        echo "  restart  - 重启所有服务"
        echo "  logs     - 查看日志（可指定服务名）"
        echo "  status   - 查看服务状态"
        echo "  health   - 健康检查"
        echo "  backup   - 数据库备份"
        echo "  clean    - 清理所有数据（慎用）"
        ;;
esac
