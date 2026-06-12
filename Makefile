# -*- coding: utf-8 -*-
# Claw 项目 Makefile
# 支持 Windows (PowerShell) 和 Linux/macOS
# ============================================

# 检测操作系统，用于跨平台命令分支
ifeq ($(OS),Windows_NT)
    IS_WINDOWS := true
else
    IS_WINDOWS := false
endif

# Python 解释器
PYTHON := python
PIP := pip

# .PHONY: 声明所有目标不依赖实际文件，避免与同名文件冲突
.PHONY: all install install-dev test test-cov lint format format-check typecheck clean run-api run-console run-wechat

# ----------------------------------------
# 默认目标：安装开发依赖 + 测试 + 代码检查
# ----------------------------------------
all: install-dev test lint

# ----------------------------------------
# 安装生产环境依赖
# ----------------------------------------
install:
	$(PIP) install -r requirements.txt

# ----------------------------------------
# 安装开发环境依赖并以可编辑模式安装本项目
# ----------------------------------------
install-dev:
	$(PIP) install -r requirements-dev.txt && $(PIP) install -e .

# ----------------------------------------
# 运行单元测试（Windows 使用 PowerShell 调用）
# ----------------------------------------
test:
ifeq ($(IS_WINDOWS),true)
	powershell pytest tests/ -v --tb=short
else
	pytest tests/ -v --tb=short
endif

# ----------------------------------------
# 运行测试并生成覆盖率报告（终端 + HTML）
# ----------------------------------------
test-cov:
	pytest tests/ --cov=. --cov-report=term --cov-report=html

# ----------------------------------------
# 代码风格检查（flake8）
# ----------------------------------------
lint:
	flake8 src/ tests/

# ----------------------------------------
# 自动格式化代码（black 格式化 + isort 排序导入）
# ----------------------------------------
format:
	black . && isort .

# ----------------------------------------
# 检查代码格式是否符合 black 和 isort 规范
# ----------------------------------------
format-check:
	black --check . && isort --check .

# ----------------------------------------
# 静态类型检查（mypy，跳过缺失导入的警告）
# ----------------------------------------
typecheck:
	mypy src/ --ignore-missing-imports

# ----------------------------------------
# 清理临时文件和构建产物
# ----------------------------------------
clean:
ifeq ($(IS_WINDOWS),true)
	powershell Remove-Item -Recurse -Force -Path __pycache__, .pytest_cache, htmlcov, build, dist -ErrorAction SilentlyContinue
	powershell Get-ChildItem -Recurse -Filter '*.pyc' | Remove-Item -Force
	powershell Get-ChildItem -Recurse -Directory -Filter '*.egg-info' | Remove-Item -Recurse -Force
else
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name '*.pyc' -delete
	rm -rf .pytest_cache htmlcov build dist
	find . -type d -name '*.egg-info' -exec rm -rf {} +
endif

# ----------------------------------------
# 启动 API 服务
# ----------------------------------------
run-api:
	$(PYTHON) api_server.py

# ----------------------------------------
# 启动控制台交互界面
# ----------------------------------------
run-console:
	$(PYTHON) siming_console.py

# ----------------------------------------
# 启动微信集成机器人
# ----------------------------------------
run-wechat:
	$(PYTHON) src/integration/wechat/main.py
