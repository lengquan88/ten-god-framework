#!/bin/bash
# =============================================================================
# TenGod Framework 部署脚本 v2.1
# =============================================================================
# 中华文明数字永生体 · 一键部署
# 支持：开发/测试/生产环境部署
# =============================================================================

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# 日志函数
log_info()    { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warn()    { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error()   { echo -e "${RED}[ERROR]${NC} $1"; exit 1; }
log_step()    { echo -e "${CYAN}[STEP]${NC} $1"; }

# 显示横幅
echo ""
echo "╔══════════════════════════════════════════════════════════╗"
echo "║     中华文明数字永生体 · TenGod Framework 部署脚本      ║"
echo "║                    版本 v2.1                            ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""

# 参数解析
ENVIRONMENT="${1:-production}"
COMPOSE_FILE="docker-compose.yml"

case "$ENVIRONMENT" in
    dev|development)
        ENVIRONMENT="development"
        COMPOSE_FILE="docker-compose.yml"
        ;;
    prod|production)
        ENVIRONMENT="production"
        COMPOSE_FILE="docker-compose.yml"
        ;;
    *)
        log_warn "未知环境: $ENVIRONMENT，使用默认 production"
        ENVIRONMENT="production"
        ;;
esac

log_info "部署环境: $ENVIRONMENT"
log_info "Compose 文件: $COMPOSE_FILE"
echo ""

# ── 步骤 1：环境检查 ─────────────────────────────────────────────────────
log_step "步骤 1/6：环境检查"

if ! command -v docker &> /dev/null; then
    log_error "Docker 未安装，请先安装 Docker"
fi

if ! docker compose version &> /dev/null && ! command -v docker-compose &> /dev/null; then
    log_error "Docker Compose 未安装，请先安装 Docker Compose"
fi

# 确定 compose 命令
if docker compose version &> /dev/null; then
    COMPOSE_CMD="docker compose"
else
    COMPOSE_CMD="docker-compose"
fi
log_success "Docker 和 Docker Compose 已安装"

# ── 步骤 2：配置检查 ─────────────────────────────────────────────────────
log_step "步骤 2/6：配置检查"

if [ ! -f .env ]; then
    log_warn ".env 文件不存在，创建示例配置..."
    cp .env.example .env
    log_warn "请编辑 .env 文件配置 DEEPSEEK_API_KEY、IMA_OPENAPI_APIKEY 等敏感信息"
    echo ""
    echo "  vim .env"
    echo ""
    read -p "已配置完成后按 Enter 继续，或 Ctrl+C 退出..." _
fi

# 检查必要的 API Key
if grep -q "your_api_key_here" .env 2>/dev/null; then
    log_warn ".env 中 API Key 仍为占位符，AI 分析功能将不可用"
fi

log_success "配置检查完成"

# ── 步骤 3：拉取最新代码 ────────────────────────────────────────────────
log_step "步骤 3/6：拉取最新代码"

if [ -d .git ]; then
    git pull origin main 2>/dev/null && log_success "代码已更新" || log_warn "Git 拉取失败，使用本地代码"
else
    log_info "非 Git 仓库，跳过拉取"
fi

# ── 步骤 4：构建 Docker 镜像 ────────────────────────────────────────────
log_step "步骤 4/6：构建 Docker 镜像"

log_info "构建镜像（可能需要几分钟）..."
$COMPOSE_CMD -f $COMPOSE_FILE build --no-cache 2>&1 | tail -5
log_success "镜像构建完成"

# ── 步骤 5：启动服务 ────────────────────────────────────────────────────
log_step "步骤 5/6：启动服务"

log_info "启动 Docker 服务..."
$COMPOSE_CMD -f $COMPOSE_FILE up -d
log_success "服务已启动"

# 等待服务就绪
log_info "等待服务就绪..."
MAX_RETRIES=30
RETRY=0
while [ $RETRY -lt $MAX_RETRIES ]; do
    if curl -sf http://localhost:8000/api/health > /dev/null 2>&1; then
        log_success "服务已就绪"
        break
    fi
    RETRY=$((RETRY + 1))
    sleep 2
    if [ $RETRY -eq $MAX_RETRIES ]; then
        log_error "服务启动超时，请检查日志: $COMPOSE_CMD logs tengod"
    fi
done

# ── 步骤 6：健康检查与状态展示 ──────────────────────────────────────────
log_step "步骤 6/6：健康检查"

log_info "执行 API 健康检查..."
if curl -sf http://localhost:8000/api/health | python3 -m json.tool 2>/dev/null; then
    log_success "API 健康检查通过"
else
    log_warn "API 健康检查失败，请检查服务状态"
fi

# 显示服务状态
echo ""
echo "╔══════════════════════════════════════════════════════════╗"
echo "║                      服务状态                          ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""
$COMPOSE_CMD -f $COMPOSE_FILE ps
echo ""

# 显示访问地址
echo "╔══════════════════════════════════════════════════════════╗"
echo "║                      访问地址                          ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""
echo "  🌐 API 地址:       http://localhost:8000"
echo "  📚 API 文档:       http://localhost:8000/docs"
echo "  ❤️  健康检查:       http://localhost:8000/api/health"
echo "  📊 Prometheus:     http://localhost:9090"
echo "  📈 Grafana:        http://localhost:3000 (admin/admin)"
echo "  🔴 Redis:          localhost:6379"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  常用命令:"
echo "    查看日志:   $COMPOSE_CMD logs -f tengod"
echo "    重启服务:   $COMPOSE_CMD restart tengod"
echo "    停止服务:   $COMPOSE_CMD down"
echo "    查看状态:   $COMPOSE_CMD ps"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

log_success "🚀 部署完成！TenGod v2.1 已成功运行"
