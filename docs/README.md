# 司命假面 v1.4 - 使用手册

> 九模协议系统 · 洛书279智能体 · 数字永生体

---

## 目录

1. [概述](#概述)
2. [快速开始](#快速开始)
3. [核心模块](#核心模块)
4. [API参考](#api参考)
5. [部署指南](#部署指南)
6. [云端同步](#云端同步)
7. [测试验证](#测试验证)
8. [故障排除](#故障排除)

---

## 概述

### 系统架构

```
┌─────────────────────────────────────────────────────────────────┐
│                     司命假面 v1.4                                │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐           │
│  │  界面层  │  │  知识层  │  │  调度层  │  │  协议层  │           │
│  │  监控    │  │  图谱    │  │  洛书    │  │  九模    │           │
│  │  面板    │  │  RAG    │  │  279    │  │  引擎    │           │
│  └────┬────┘  └────┬────┘  └────┬────┘  └────┬────┘           │
│       │            │            │            │                  │
│  ┌────▼────────────▼────────────▼────────────▼────┐            │
│  │                   Claw 七层架构                 │            │
│  │  L1感知 → L2认知 → L3决策 → L4执行 → L5反馈   │            │
│  │  → L6记忆 → L7进化                              │            │
│  └────────────────────────────────────────────────┘            │
└─────────────────────────────────────────────────────────────────┘
```

### 九模协议

| 协议 | 触发条件 | 功能 |
|:---|:---|:---|
| **消化** | new_external_input | 吸收外部信息 |
| **留白** | high_confidence | 保持不确定性 |
| **归墟** | memory_overflow | 遗忘与归档 |
| **扮演** | role_required | 角色人格面具 |
| **观照** | periodic_reflection | 自我觉察监控 |
| **断裂** | critical_failure | 危机突然转变 |
| **返还** | debt_detected | 回报因果循环 |
| **投影** | value_expression | 价值观输出 |
| **呼吸** | time_cycle | 节奏周期调节 |

---

## 快速开始

### 安装依赖

```bash
cd C:\Users\41876\WorkBuddy\Claw

# 安装核心依赖
pip install fastapi uvicorn pydantic websockets

# 安装可选依赖
pip install qcloud-cos-python-sdk-v5  # 腾讯云COS
pip install requests                   # GitHub API

# 安装测试依赖
pip install pytest pytest-asyncio
```

### 启动服务

```bash
# 方式1: API服务 (REST + WebSocket)
python api_server.py

# 方式2: 直接运行核心
python claw_deployment.py

# 方式3: 快速测试
python e2e_integration_test.py --quick
```

### 访问界面

| 服务 | 地址 |
|:---|:---|
| API文档 | http://localhost:8080/docs |
| ReDoc | http://localhost:8080/redoc |
| 健康检查 | http://localhost:8080/health |
| 系统状态 | http://localhost:8080/status |

---

## 核心模块

### 1. 司命假面人格系统

```python
from 司命假面_深度集成 import 司命假面人格系统

# 创建系统
系统 = 司命假面人格系统()

# 处理输入
结果 = 系统.处理("测试输入", 角色="诗人")

# 执行协议
结果 = 系统.执行九模协议(系统.九模.消化, "内容", {})
```

### 2. 洛书279智能体

```python
from luoshu_jiumo_fusion import LuoShuJiuMoFusion

# 创建融合系统
fusion = LuoShuJiuMoFusion(
    agent_count=279,
    palace_count=9,
    enable_protocols=True
)

# 执行任务
result = fusion.execute_jiumo_protocol("任务描述", "呼吸")

# 获取智能体状态
agents = fusion.agent_manager.get_agents_by_palace(1)
```

### 3. 九模协议引擎

```python
from src.memory.immortal.persona_self_perfection import JiuMoProtocolIntegration

# 创建协议集成
integration = JiuMoProtocolIntegration(
    base_system=base,
    integration_config={
        "enabled_protocols": ["digest", "blank", "void", ...],
        "trigger_check_interval": 10,
        "max_concurrent_protocols": 3,
    }
)

# 执行协议
result = integration.execute_protocol("消化", "内容")
```

### 4. 知识图谱RAG

```python
from knowledge_graph import JiuMoKnowledgeGraph, JiuMoRAGRetriever

# 创建知识图谱
kg = JiuMoKnowledgeGraph()

# RAG检索
retriever = JiuMoRAGRetriever(kg)
results = retriever.retrieve(
    query="测试查询",
    top_k=5,
    mode="hybrid"
)
```

### 5. 模板系统

```python
from templates import TemplateExecutor

# 创建执行器
executor = TemplateExecutor()

# 匹配模板
template_id = executor.match_template("写一首诗")

# 执行模板
result = executor.execute(template_id, {"topic": "春天"})
```

### 6. 健康监控

```python
from health_monitor import HealthMonitor, HealthChecker

# 健康检查
checker = HealthChecker()
results = checker.run_all_checks()

# 定时监控
monitor = HealthMonitor(interval_seconds=30)
monitor.start()
```

---

## API参考

### REST API

#### 基础接口

| 方法 | 路径 | 描述 |
|:---|:---|:---|
| GET | `/` | API根页面 |
| GET | `/health` | 健康检查 |
| GET | `/status` | 系统状态 |
| POST | `/process` | 处理输入 |
| POST | `/config` | 更新配置 |
| GET | `/config` | 获取配置 |

#### 九模协议

| 方法 | 路径 | 描述 |
|:---|:---|:---|
| GET | `/protocols` | 列出所有协议 |
| POST | `/protocols/execute` | 执行协议 |

#### 洛书智能体

| 方法 | 路径 | 描述 |
|:---|:---|:---|
| GET | `/agents` | 列出智能体 |
| GET | `/palaces` | 列出九宫 |
| POST | `/agents/execute` | 执行任务 |

#### RAG知识检索

| 方法 | 路径 | 描述 |
|:---|:---|:---|
| GET | `/rag/knowledge` | 获取知识图谱 |
| POST | `/rag/query` | RAG检索 |

#### 模板

| 方法 | 路径 | 描述 |
|:---|:---|:---|
| GET | `/templates` | 列出模板 |
| GET | `/templates/{id}` | 获取模板详情 |
| POST | `/templates/{id}/execute` | 执行模板 |

### WebSocket API

```javascript
// 连接
const ws = new WebSocket("ws://localhost:8080/ws");

// 订阅频道
ws.send(JSON.stringify({type: "subscribe", channel: "status"}));

// 处理输入
ws.send(JSON.stringify({
    type: "process",
    input: "测试输入",
    role: "诗人"
}));

// 心跳
ws.send(JSON.stringify({type: "ping"}));
```

---

## 部署指南

### Docker Compose

```bash
cd deploy
docker-compose up -d
```

### Kubernetes

```bash
# 部署到K8s
kubectl apply -f deploy/k8s-deployment.yaml

# 检查状态
kubectl get pods -n siming

# 查看日志
kubectl logs -n siming -l app=siming-core
```

### 环境变量

```bash
# API配置
API_PORT=8080
WS_PORT=8081
LOG_LEVEL=info

# LLM配置
DEEPSEEK_API_KEY=your_key
ZHIPU_API_KEY=your_key

# 云同步配置
GITHUB_TOKEN=your_token
COS_SECRET_ID=your_id
COS_SECRET_KEY=your_key
```

---

## 云端同步

### 配置GitHub Gist

```python
from cloud_sync import CloudSyncManager, CloudConfig

config = CloudConfig(
    github_token="your_github_token",
    gist_id=None  # 首次自动创建
)

manager = CloudSyncManager(config)
record = manager.sync_all()
```

### 配置腾讯云COS

```python
config = CloudConfig(
    cos_secret_id="your_secret_id",
    cos_secret_key="your_secret_key",
    cos_region="ap-guangzhou",
    cos_bucket="your-bucket",
)

manager = CloudSyncManager(config)
manager.sync_all()
```

### CLI工具

```bash
# 配置
python cloud_sync.py config --github-token xxx

# 推送
python cloud_sync.py sync --push

# 拉取
python cloud_sync.py sync --pull

# 状态
python cloud_sync.py status

# 创建胶囊
python cloud_sync.py create --title "测试" --content "内容"
```

---

## 测试验证

### 快速测试

```bash
python e2e_integration_test.py --quick
```

### 完整测试

```bash
python e2e_integration_test.py
```

### 分类测试

```bash
# 只测试部署
python e2e_integration_test.py --category deploy

# 只测试协议
python e2e_integration_test.py --category protocol
```

### 生成报告

```bash
python e2e_integration_test.py --report
```

---

## 故障排除

### 常见问题

| 问题 | 解决方案 |
|:---|:---|
| 端口占用 | 修改`api_server.py`中的端口或杀死占用进程 |
| 模块导入失败 | 检查`sys.path`或重新安装依赖 |
| WebSocket连接失败 | 检查防火墙和端口配置 |
| Docker启动失败 | 检查Docker守护进程和镜像构建 |
| K8s Pod启动失败 | 检查资源限制和镜像地址 |

### 日志位置

| 组件 | 日志路径 |
|:---|:---|
| API服务 | `logs/api_server.log` |
| 部署 | `logs/deployment_{date}.log` |
| 云同步 | `logs/cloud_sync.log` |

### 健康检查

```bash
# API健康
curl http://localhost:8080/health

# 详细检查
curl http://localhost:8080/health/detailed

# 系统状态
curl http://localhost:8080/status
```

---

## 版本历史

| 版本 | 日期 | 变化 |
|:---|:---|:---|
| v1.4.0 | 2026-04-14 | O/P/Q/R/S深化模块完成 |
| v1.3.0 | 2026-04-14 | 自我完善系统v1.4 |
| v1.2.0 | 2026-04-14 | 遗忘曲线/逆反导图 |
| v1.1.0 | 2026-04-14 | 七层架构集成 |
| v1.0.0 | 2026-04-14 | 初始版本 |

---

**☯ 以洛书为体，以九模为用，以279智能体为网络。**

*文档版本: v1.4.0 · 更新日期: 2026-04-14*
