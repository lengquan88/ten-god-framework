@echo off
chcp 65001 > nul
REM 司命假面 · Windows 一键部署脚本 v1.4.0

echo.
echo  ╔══════════════════════════════════════════════════════════════╗
echo  ║                                                              ║
echo  ║     ☯ 司命假面 · 统一控制台 v1.4.0                           ║
echo  ║                                                              ║
echo  ║     九模协议 · 279智能体 · 记忆永生 · 旋转防御              ║
echo  ║                                                              ║
echo  ╚══════════════════════════════════════════════════════════════╝
echo.

REM 检查Docker
where docker > nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Docker 未安装
    exit /b 1
)
echo [OK] Docker: 
docker --version

REM 检查docker-compose
where docker-compose > nul 2>&1
if %ERRORLEVEL% neq 0 (
    where docker > nul 2>&1
    docker compose version > nul 2>&1
    if %ERRORLEVEL% neq 0 (
        echo [ERROR] Docker Compose 未安装
        exit /b 1
    )
)

REM 创建目录
if not exist "data\capsules" mkdir data\capsules
if not exist "data\graph" mkdir data\graph
if not exist "logs" mkdir logs
if not exist "ssl" mkdir ssl
echo [OK] 目录创建完成

REM 处理命令
if "%1"=="" goto help
if "%1"=="start" goto start
if "%1"=="stop" goto stop
if "%1"=="restart" goto restart
if "%1"=="logs" goto logs
if "%1"=="status" goto status
if "%1"=="build" goto build
if "%1"=="clean" goto clean

:help
echo 用法: deploy.bat [命令]
echo.
echo 命令:
echo   start   启动所有服务
echo   stop    停止所有服务
echo   restart 重启所有服务
echo   logs    查看日志
echo   status  查看状态
echo   build   构建Docker镜像
echo   clean   清理Docker资源
echo   help    显示帮助
goto end

:start
echo [INFO] 构建Docker镜像...
docker build -t siming/siming-core:latest -f deploy/Dockerfile .
docker build -t siming/jiumo-engine:latest -f deploy/Dockerfile.jiumo .
docker build -t siming/memory-immortal:latest -f deploy/Dockerfile.memory .
docker build -t siming/luoshu-agents:latest -f deploy/Dockerfile.luoshu .

echo [INFO] 启动服务...
docker compose -f deploy/docker-compose.yml up -d

echo [SUCCESS] 服务启动完成！
echo.
echo 访问地址:
echo   • 控制台: http://localhost
echo   • API: http://localhost:8080
echo   • 九模引擎: http://localhost:8082
echo   • 记忆存储: http://localhost:8083
echo   • 洛书智能体: http://localhost:8084
goto end

:stop
echo [INFO] 停止服务...
docker compose -f deploy/docker-compose.yml down
echo [SUCCESS] 服务已停止
goto end

:restart
call :stop
timeout /t 2 > nul
call :start
goto end

:logs
docker compose -f deploy/docker-compose.yml logs -f
goto end

:status
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
goto end

:build
echo [INFO] 构建Docker镜像...
docker build -t siming/siming-core:latest -f deploy/Dockerfile .
docker build -t siming/jiumo-engine:latest -f deploy/Dockerfile.jiumo .
docker build -t siming/memory-immortal:latest -f deploy/Dockerfile.memory .
docker build -t siming/luoshu-agents:latest -f deploy/Dockerfile.luoshu .
echo [SUCCESS] 镜像构建完成
goto end

:clean
echo [WARN] 清理Docker资源...
docker compose -f deploy/docker-compose.yml down -v --rmi local
docker system prune -f
echo [SUCCESS] 清理完成
goto end

:end
