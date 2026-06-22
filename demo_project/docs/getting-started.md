# 起步指南 (Getting Started)

## 1. 克隆项目
```bash
git clone https://github.com/tengod/tengod.git
cd tengod
```

## 2. 安装依赖
```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## 3. 运行快速测试
```bash
python -m tengod.bazi_calculator
python -m pytest tests/ -q
```

## 4. 启动 API 服务器
```bash
python -m tengod.api_server --host 0.0.0.0 --port 8000
# 访问 http://localhost:8000/docs 查看 Swagger UI
```

## 5. 常见命令
- `python -m pytest tests/ -q`  运行测试
- `python -m tengod.api_server` 启动 API
- `python -m tengod.admin_api` 仅测试后台管理模块
