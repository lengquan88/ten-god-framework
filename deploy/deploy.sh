#!/bin/bash
###############################################################################
# 司命假面 · 一键部署脚本
# 版本: v1.4.0
###############################################################################

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日志函数
log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# 显示Banner
show_banner() {
    cat << 'EOF'
    ╔══════════════════════════════════════════════════════════════╗
    ║                                                              ║
    ║     ☯ 司命假面 · 统一控制台 v1.4.0                          ║
    ║                                                              ║
    ║     九模协议 · 279智能体 · 记忆永生 · 旋转防御              ║
    ║                                                              ║
    ╚══════════════════════════════════════════════════════════════╝
EOF
}

# 检查依赖
check_dependencies() {
    log_info "检查依赖..."
    
    # 检查Docker
    if ! command -v docker &> /dev/null; then
        log_error "Docker 未安装"
        exit 1
    fi
    log_success "Docker: $(docker --version)"
    
    # 检查docker-compose
    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        log_error "Docker Compose 未安装"
        exit 1
    fi
    log_success "Docker Compose: $(docker compose version 2>/dev/null || docker-compose --version)"
    
    # 检查Python
    if ! command -v python3 &> /dev/null; then
        log_error "Python3 未安装"
        exit 1
    fi
    log_success "Python: $(python3 --version)"
}

# 创建目录
create_directories() {
    log_info "创建目录..."
    mkdir -p data/capsules data/graph logs ssl
    chmod -R 755 data logs
    log_success "目录创建完成"
}

# 构建镜像
build_images() {
    log_info "构建Docker镜像..."
    
    cd "$(dirname "$0")"
    
    log_info "构建 siming-core..."
    docker build -t siming/siming-core:latest -f deploy/Dockerfile .
    
    log_info "构建 jiumo-engine..."
    docker build -t siming/jiumo-engine:latest -f deploy/Dockerfile.jiumo .
    
    log_info "构建 memory-immortal..."
    docker build -t siming/memory-immortal:latest -f deploy/Dockerfile.memory .
    
    log_info "构建 luoshu-agents..."
    docker build -t siming/luoshu-agents:latest -f deploy/Dockerfile.luoshu .
    
    log_success "所有镜像构建完成"
}

# 启动服务
start_services() {
    log_info "启动服务..."
    
    cd "$(dirname "$0")"
    
    docker compose -f deploy/docker-compose.yml up -d
    
    log_success "服务启动完成"
    log_info "等待服务就绪..."
    sleep 10
    
    # 检查服务状态
    check_services
}

# 检查服务状态
check_services() {
    log_info "检查服务状态..."
    
    services=("siming-core" "jiumo-engine" "memory-immortal" "luoshu-agents" "nginx")
    
    for service in "${services[@]}"; do
        if docker ps --format '{{.Names}}' | grep -q "^${service}$"; then
            log_success "${service}: 运行中"
        else
            log_warn "${service}: 未运行"
        fi
    done
}

# 停止服务
stop_services() {
    log_info "停止服务..."
    
    cd "$(dirname "$0")"
    docker compose -f deploy/docker-compose.yml down
    
    log_success "服务已停止"
}

# 查看日志
view_logs() {
    cd "$(dirname "$0")"
    docker compose -f deploy/docker-compose.yml logs -f
}

# 清理
cleanup() {
    log_warn "清理Docker资源..."
    cd "$(dirname "$0")"
    docker compose -f deploy/docker-compose.yml down -v --rmi local
    docker system prune -f
    log_success "清理完成"
}

# 显示帮助
show_help() {
    cat << 'EOF'
司命假面 · 部署脚本

用法: ./deploy.sh [命令]

命令:
    start       启动所有服务
    stop        停止所有服务
    restart     重启所有服务
    logs        查看日志
    status      查看状态
    build       构建Docker镜像
    clean       清理Docker资源
    help        显示帮助

示例:
    ./deploy.sh start      # 启动服务
    ./deploy.sh logs       # 查看日志
    ./deploy.sh stop       # 停止服务

EOF
}

# 主入口
main() {
    cd "$(dirname "$0")"
    SCRIPT_DIR="$(pwd)"
    
    show_banner
    
    case "${1:-}" in
        start)
            check_dependencies
            create_directories
            build_images
            start_services
            log_success "
            
服务已启动！

访问地址:
  • 控制台: http://localhost
  • API: http://localhost:8080
  • 九模引擎: http://localhost:8082
  • 记忆存储: http://localhost:8083
  • 洛书智能体: http://localhost:8084

查看日志: ./deploy.sh logs
停止服务: ./deploy.sh stop
"
            ;;
        stop)
            stop_services
            ;;
        restart)
            stop_services
            sleep 2
            start_services
            ;;
        logs)
            view_logs
            ;;
        status)
            check_services
            ;;
        build)
            check_dependencies
            build_images
            ;;
        clean)
            cleanup
            ;;
        help|--help|-h)
            show_help
            ;;
        *)
            show_help
            ;;
    esac
}

main "$@"
