#!/bin/bash
# =============================================================================
# TenGod Framework 部署脚本
# =============================================================================
# 中华文明数字永生体 · 一键部署
# =============================================================================

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# 日志函数
log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; exit 1; }

# 显示横幅
echo ""
echo "╔══════════════════════════════════════════════════════════╗"
echo "║     中华文明数字永生体 · TenGod Framework 部署脚本      ║"
echo "║                    版本 v2.0                            ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""

# 检查 Docker
if ! command -v docker &> /dev/null; then
    log_error "Docker 未安装，请先安装 Docker"
fi

if ! command -v docker-compose &> /dev/null; then
    log_error "Docker Compose 未安装，请先安装 Docker Compose"
fi

# 检查 .env 文件
if [ ! -f .env ]; then
    log_warn ".env 文件不存在，创建示例配置..."
    cp .env.example .env
    log_warn "请编辑 .env 文件配置 DEEPSEEK_API_KEY"
fi

# 拉取最新代码
log_info "拉取最新代码..."
git pull origin main 2>/dev/null || log_warn "Git 拉取失败，跳过"

# 构建并启动服务
log_info "构建 Docker 镜像..."
docker-compose build --no-cache

log_info "启动服务..."
docker-compose up -d

# 等待服务启动
log_info "等待服务启动..."
sleep 10

# 健康检查
log_info "执行健康检查..."
if curl -sf http://localhost:8000/api/health > /dev/null; then
    log_success "服务运行正常！"
else
    log_error "健康检查失败，请检查日志: docker-compose logs tengod"
fi

# 显示状态
echo ""
echo "╔══════════════════════════════════════════════════════════╗"
echo "║                      服务状态                          ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""
docker-compose ps
echo ""

# 显示访问地址
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  API 地址:     http://localhost:8000"
echo "  API 文档:     http://localhost:8000/docs"
echo "  Prometheus:   http://localhost:9090"
echo "  Grafana:     http://localhost:3000"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

log_success "部署完成！"
