# Claw 类脑AI智能体系统 · API 文档

> 版本：1.0.0  
> 最后更新：2026-05-04  
> 编码：UTF-8  
> 文档风格：DeepSeek API V4 规范

---

## 1. 概述

Claw 类脑AI智能体系统是一套基于 **九模协议（九种认知操作范式）** 构建的分布式智能体架构。系统由多个微服务组成，涵盖主控调度、记忆管理、LLM合成、形神评估、可视化监控和自进化回路等核心能力。

### 1.1 架构总览

| 服务 | 角色 | 端口 | 框架 |
|------|------|------|------|
| 司命假面主API | 核心调度与协议执行 | 8080 (HTTP) / 8081 (WS) | FastAPI |
| 记忆永生API | 跨对话知识胶囊网络 | 8080 | FastAPI |
| LLM合成API | LLM驱动的评估方法自动合成 | 动态 | FastAPI |
| 网关服务 | 统一入口、认证、限流、代理 | 8000 | FastAPI |
| 对话树服务 | 形神对话树管理 | 8001 | FastAPI |
| 评估引擎 | 形神得分、境界判定、递归校准 | 8002 | FastAPI |
| 可视化服务 | 森林数据聚合与实时推送 | 8003 | FastAPI |
| 自进化回路 | 评估结果→调度策略自动反馈闭环 | 集成于评估服务 | FastAPI APIRouter |
| 中华文明数字永生体 | 九模协议Flask轻量版 | 8765 | Flask |

### 1.2 通用约定

- **时间格式**：ISO 8601（`yyyy-MM-ddTHH:mm:ss`）
- **编码**：所有请求与响应使用 UTF-8 编码
- **Content-Type**：`application/json`（WebSocket 使用 JSON 文本帧）
- **通用响应结构**：

```json
{
    "success": true,
    "result": { ... },
    "error": null,
    "timestamp": "2026-05-04T12:00:00"
}
```

- **失败响应结构**：

```json
{
    "success": false,
    "error": "错误描述信息",
    "detail": "详细错误内容（可选）",
    "timestamp": "2026-05-04T12:00:00"
}
```

---

## 2. 认证方式

### 2.1 无认证服务

以下服务默认未内置认证机制，建议通过网关或反向代理添加：

- 司命假面主API（端口8080）
- 记忆永生API（端口8080）
- LLM合成API（端口动态）
- 中华文明数字永生体API（端口8765）

### 2.2 JWT Bearer Token 认证（网关服务）

网关服务（端口8000）使用 **JWT Bearer Token** 认证。

**获取令牌：**

```
POST /api/v1/auth/login
Content-Type: application/json

{
    "username": "admin",
    "password": "admin123"
}
```

**响应：**

```json
{
    "access_token": "eyJhbGciOiJIUzI1NiIs...",
    "token_type": "bearer",
    "expires_in": 1800,
    "user": {
        "username": "admin",
        "role": "admin",
        "email": "admin@example.com"
    }
}
```

**使用令牌：**

在请求头中添加 `Authorization: Bearer <access_token>`。令牌有效期30分钟，需在过期前重新获取。

### 2.3 模拟用户数据库

| 用户名 | 密码 | 角色 |
|--------|------|------|
| `admin` | `admin123` | admin |
| `user` | `user123` | user |

---

## 3. 通用错误码

### 3.1 HTTP 状态码

| 状态码 | 含义 | 说明 |
|--------|------|------|
| 200 | OK | 请求成功 |
| 400 | Bad Request | 请求参数错误（如缺少必填字段、枚举值非法） |
| 401 | Unauthorized | 认证失败（令牌无效或过期） |
| 404 | Not Found | 资源不存在 |
| 429 | Too Many Requests | 请求频率超过限流阈值 |
| 500 | Internal Server Error | 服务器内部错误 |
| 502 | Bad Gateway | 网关代理后端服务失败 |
| 503 | Service Unavailable | 服务未初始化或不可用 |
| 504 | Gateway Timeout | 网关代理超时 |

### 3.2 业务错误码（响应体中的 error 字段）

| 错误码 | 说明 | 常见原因 |
|--------|------|----------|
| `service_not_initialized` | 服务尚未完成初始化 | 启动过程中调用API |
| `invalid_parameter` | 请求参数不合法 | 枚举值超出范围、类型错误 |
| `resource_not_found` | 请求的资源不存在 | 胶囊ID/树ID/模板ID不存在 |
| `algorithm_unavailable` | 指定算法不可用 | 算法模块未加载 |
| `internal_error` | 内部处理异常 | 请查看服务端日志 |
| `rate_limit_exceeded` | 超出限流限制 | 稍后重试 |

---

## 4. 司命假面主API（api_server）

- **框架**：FastAPI
- **端口**：8080（HTTP）/ 8081（WebSocket）
- **基础URL**：`http://localhost:8080`
- **Swagger文档**：`http://localhost:8080/docs`
- **认证**：无内置认证

### 4.1 健康检查

```
GET /health
```

**响应参数：**

| 字段 | 类型 | 说明 |
|------|------|------|
| status | string | 健康状态：`healthy` / `initializing` |
| version | string | API版本号 |
| uptime | float | 服务运行时长（秒） |
| services | object | 各子系统的就绪状态 |

**成功示例：**

```json
{
    "status": "healthy",
    "version": "1.4.0",
    "uptime": 3600.5,
    "services": {
        "deployment": true,
        "luoshu": true,
        "knowledge_graph": true,
        "rag": true,
        "templates": true,
        "health_monitor": true
    }
}
```

### 4.2 系统状态

```
GET /status
```

**响应参数：**

| 字段 | 类型 | 说明 |
|------|------|------|
| system.version | string | 系统版本 |
| system.uptime_seconds | float | 运行时长 |
| system.initialized | bool | 是否初始化完成 |
| deployment | object | 部署报告 |
| websocket.active_connections | int | 当前WebSocket连接数 |
| websocket.channels | object | 各频道订阅数 |

**成功示例：**

```json
{
    "system": {
        "version": "1.4.0",
        "uptime_seconds": 3600.5,
        "initialized": true
    },
    "deployment": { "...": "..." },
    "websocket": {
        "active_connections": 3,
        "channels": {
            "status": 2,
            "protocols": 0,
            "agents": 1,
            "health": 0
        }
    }
}
```

### 4.3 处理输入（核心接口）

```
POST /process
```

**请求参数（JSON Body）：**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| input | string | 是 | 输入内容 |
| role | string | 否 | 角色类型 |
| protocols | string[] | 否 | 指定协议列表 |
| context | object | 否 | 上下文信息 |

**成功示例：**

```json
// Request
{
    "input": "分析这段对话的形神关系",
    "role": "evaluator",
    "context": { "mode": "deep" }
}

// Response
{
    "success": true,
    "result": { "...": "..." },
    "timestamp": "2026-05-04T12:00:00"
}
```

**失败示例：**

```json
{
    "detail": "服务初始化中"
}
```
状态码：503

### 4.4 执行九模协议

```
POST /protocols/execute
```

**请求参数（JSON Body）：**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| protocol | string | 是 | 协议名称：`消化` / `留白` / `归墟` / `扮演` / `观照` / `断裂` / `返还` / `投影` / `呼吸` |
| content | string | 否 | 输入内容 |
| context | object | 否 | 上下文 |

**响应参数：**

| 字段 | 类型 | 说明 |
|------|------|------|
| success | bool | 是否成功 |
| protocol | string | 执行的协议名称 |
| result | any | 协议执行结果 |
| timestamp | string | 时间戳 |

**成功示例：**

```json
// Request
{
    "protocol": "消化",
    "content": "新输入的对话数据"
}

// Response
{
    "success": true,
    "protocol": "消化",
    "result": { "digested": true, "summary": "..." },
    "timestamp": "2026-05-04T12:00:00"
}
```

**失败示例：**

```json
{
    "detail": "未知协议: unknown_protocol"
}
```
状态码：400

**错误码说明：**

| 状态码 | 条件 |
|--------|------|
| 400 | protocol 不在九模列表中 |
| 503 | 服务未初始化 |
| 500 | 协议执行内部错误 |

### 4.5 列出所有协议

```
GET /protocols
```

**响应参数：**

| 字段 | 类型 | 说明 |
|------|------|------|
| protocols | array | 协议列表，每项包含 name / trigger / description |

**成功示例：**

```json
{
    "protocols": [
        { "name": "消化", "trigger": "new_external_input", "description": "吸收外部信息" },
        { "name": "留白", "trigger": "high_confidence", "description": "保持不确定性" },
        { "name": "归墟", "trigger": "memory_overflow", "description": "遗忘与归档" },
        { "name": "扮演", "trigger": "role_required", "description": "角色人格面具" },
        { "name": "观照", "trigger": "periodic_reflection", "description": "自我觉察监控" },
        { "name": "断裂", "trigger": "critical_failure", "description": "危机突然转变" },
        { "name": "返还", "trigger": "debt_detected", "description": "回报因果循环" },
        { "name": "投影", "trigger": "value_expression", "description": "价值观输出" },
        { "name": "呼吸", "trigger": "time_cycle", "description": "节奏周期调节" }
    ]
}
```

### 4.6 执行智能体任务

```
POST /agents/execute
```

**请求参数（JSON Body）：**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| palace | int | 否 | 宫位(1-9) |
| agent_id | int | 否 | 智能体ID |
| task | string | 是 | 任务描述 |
| protocol | string | 否 | 关联协议 |

**成功示例：**

```json
// Request
{
    "task": "分析输入文本的语义结构",
    "protocol": "观照",
    "palace": 5
}

// Response
{
    "success": true,
    "task": "分析输入文本的语义结构",
    "result": { "...": "..." },
    "timestamp": "2026-05-04T12:00:00"
}
```

### 4.7 列出智能体

```
GET /agents?palace=<N>
```

**查询参数：**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| palace | int | 否 | 宫位过滤(1-9)，不传则返回全部 |

**响应参数：**

| 字段 | 类型 | 说明 |
|------|------|------|
| agents | array | 智能体列表，每项包含 id / palace / name / status |
| total | int | 总数 |

**成功示例：**

```json
{
    "agents": [
        { "id": 1, "palace": 1, "name": "坎一-01", "status": "active" },
        { "id": 2, "palace": 1, "name": "坎一-02", "status": "active" }
    ],
    "total": 2
}
```

### 4.8 列出九宫信息

```
GET /palaces
```

**响应参数：**

| 字段 | 类型 | 说明 |
|------|------|------|
| palaces | object | 九宫映射，key为1-9 |

**成功示例：**

```json
{
    "palaces": {
        "1": { "name": "坎一", "agent_count": 31, "protocol": "消化" },
        "2": { "name": "坤二", "agent_count": 28, "protocol": "留白" },
        "3": { "name": "震三", "agent_count": 30, "protocol": "断裂" },
        "4": { "name": "巽四", "agent_count": 33, "protocol": "投影" },
        "5": { "name": "中五", "agent_count": 28, "protocol": "呼吸" },
        "6": { "name": "乾六", "agent_count": 31, "protocol": "观照" },
        "7": { "name": "兑七", "agent_count": 29, "protocol": "返还" },
        "8": { "name": "艮八", "agent_count": 27, "protocol": "归墟" },
        "9": { "name": "离九", "agent_count": 34, "protocol": "扮演" }
    }
}
```

### 4.9 RAG知识检索

```
POST /rag/query
```

**请求参数（JSON Body）：**

| 字段 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| query | string | 是 | - | 查询内容 |
| top_k | int | 否 | 5 | 返回数量（1-20） |
| mode | string | 否 | `hybrid` | 检索模式：`exact` / `keyword` / `vector` / `hybrid` |
| protocols | string[] | 否 | null | 协议过滤 |

**成功示例：**

```json
// Request
{
    "query": "什么是形神合一？",
    "top_k": 3,
    "mode": "hybrid"
}

// Response
{
    "success": true,
    "query": "什么是形神合一？",
    "mode": "hybrid",
    "results": [
        { "content": "...", "score": 0.95, "source": "..." }
    ],
    "count": 3
}
```

### 4.10 获取知识图谱

```
GET /rag/knowledge
```

**成功示例：**

```json
{
    "nodes": ["node_1", "node_2"],
    "edges": [["node_1", "node_2"]],
    "stats": { "nodes": 100, "edges": 250 }
}
```

### 4.11 模板管理

#### 列出模板

```
GET /templates?category=<category>
```

**查询参数：**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| category | string | 否 | 分类过滤 |

**成功示例：**

```json
{
    "templates": [
        { "id": "tpl_1", "name": "形神评估模板", "category": "evaluation", "description": "..." }
    ],
    "categories": ["evaluation", "protocol", "analysis"]
}
```

#### 获取模板详情

```
GET /templates/{template_id}
```

**成功示例：**

```json
{
    "id": "tpl_1",
    "name": "形神评估模板",
    "category": "evaluation",
    "description": "...",
    "system_prompt": "你是一个形神评估专家...",
    "example_inputs": ["..."]
}
```

#### 执行模板

```
POST /templates/{template_id}/execute
```

**请求参数（JSON Body）：**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| template_id | string | 是 | 模板ID（路径参数） |
| context | object | 否 | 执行上下文 |

**成功示例：**

```json
{
    "success": true,
    "template_id": "tpl_1",
    "result": { "output": "..." }
}
```

### 4.12 详细健康检查

```
GET /health/detailed
```

**成功示例：**

```json
{
    "timestamp": "2026-05-04T12:00:00",
    "checks": {
        "database": { "passed": true },
        "api": { "passed": true }
    },
    "summary": { "total": 5, "passed": 5, "failed": 0 }
}
```

### 4.13 WebSocket 端点

```
WebSocket /ws
```

**支持的消息类型：**

| type | 说明 | 载荷字段 |
|------|------|----------|
| `subscribe` | 订阅频道 | channel: `status` / `protocols` / `agents` / `health` |
| `process` | 处理输入 | input, role |
| `protocol` | 执行协议 | protocol, content |
| `ping` | 心跳检测 | - |

**响应示例：**

```json
// 订阅成功
{ "type": "subscribed", "channel": "status" }

// 处理结果
{ "type": "result", "data": { ... } }

// 协议执行结果
{ "type": "protocol_result", "data": { ... } }

// 心跳响应
{ "type": "pong", "timestamp": "2026-05-04T12:00:00" }
```

### 4.14 系统配置管理

#### 更新配置

```
POST /config
```

**请求参数（JSON Body）：**

| 字段 | 类型 | 默认值 | 范围 | 说明 |
|------|------|--------|------|------|
| drift_threshold | float | 0.15 | 0.01-1.0 | 漂移阈值 |
| convergence_threshold | float | 0.05 | 0.01-1.0 | 收敛阈值 |
| max_concurrent_protocols | int | 3 | 1-10 | 最大并发协议数 |
| breath_cycle_ms | int | 5000 | 1000-60000 | 呼吸周期（毫秒） |

**成功示例：**

```json
{
    "success": true,
    "config": {
        "drift_threshold": 0.15,
        "convergence_threshold": 0.05,
        "max_concurrent_protocols": 3,
        "breath_cycle_ms": 5000
    },
    "message": "配置已更新（部分配置需要重启服务生效）"
}
```

#### 获取配置

```
GET /config
```

**成功示例：**

```json
{
    "drift_threshold": 0.15,
    "convergence_threshold": 0.05,
    "max_concurrent_protocols": 3,
    "breath_cycle_ms": 5000
}
```

---

## 5. 记忆永生API（memory-immortal）

- **框架**：FastAPI
- **端口**：8080（与司命假面共用）
- **基础URL**：`http://localhost:8080`
- **认证**：无内置认证
- **核心概念**：**胶囊（Capsule）**——跨对话的知识单元，支持标签、关键词、关联关系和智能重组

### 5.1 健康检查

```
GET /health
```

**成功示例：**

```json
{
    "status": "ok",
    "timestamp": "2026-05-04T12:00:00"
}
```

### 5.2 创建胶囊

```
POST /capsules
```

**请求参数（Query/Form 参数）：**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| title | string | 是 | 胶囊标题 |
| content | string | 是 | 胶囊内容 |
| summary | string | 否 | 内容摘要 |
| tags | string[] | 否 | 标签列表 |
| keywords | string[] | 否 | 关键词列表 |
| related_ids | string[] | 否 | 关联胶囊ID列表 |

**成功示例：**

```json
// Response
{
    "capsule_id": "capsule_uuid",
    "title": "形神合一的核心概念",
    "content": "...",
    "summary": "...",
    "tags": ["形神", "哲学"],
    "keywords": ["形", "神"],
    "related_ids": [],
    "created_at": "2026-05-04T12:00:00",
    "updated_at": "2026-05-04T12:00:00",
    "access_count": 0
}
```

### 5.3 获取胶囊

```
GET /capsules/{capsule_id}
```

**路径参数：**

| 字段 | 类型 | 说明 |
|------|------|------|
| capsule_id | string | 胶囊唯一标识 |

**成功示例：**

```json
{
    "capsule_id": "capsule_uuid",
    "title": "形神合一的核心概念",
    "content": "...",
    "summary": "...",
    "tags": ["形神", "哲学"],
    "access_count": 5
}
```

**失败示例：**

```json
{
    "detail": "胶囊不存在"
}
```
状态码：404

### 5.4 更新胶囊

```
PUT /capsules/{capsule_id}
```

**请求参数（Query/Form 参数，均为可选）：**

| 字段 | 类型 | 说明 |
|------|------|------|
| title | string | 新标题 |
| content | string | 新内容 |
| summary | string | 新摘要 |
| tags | string[] | 新标签列表 |
| keywords | string[] | 新关键词列表 |
| related_ids | string[] | 新关联ID列表 |

**成功示例：**

```json
{
    "capsule_id": "capsule_uuid",
    "title": "更新后的标题",
    "updated_at": "2026-05-04T13:00:00"
}
```

### 5.5 删除胶囊

```
DELETE /capsules/{capsule_id}
```

**成功示例：**

```json
{
    "status": "ok",
    "message": "胶囊已删除"
}
```

### 5.6 列出胶囊

```
GET /capsules?tags=<tags>&keyword=<keyword>&limit=<N>
```

**查询参数：**

| 字段 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| tags | string | 否 | - | 逗号分隔的标签过滤 |
| keyword | string | 否 | - | 关键词搜索 |
| limit | int | 否 | 100 | 返回数量上限 |

**成功示例：**

```json
[
    { "capsule_id": "...", "title": "...", "tags": ["形神"] },
    { "capsule_id": "...", "title": "...", "tags": ["九模"] }
]
```

### 5.7 寻找相似胶囊

```
POST /find-relatives/{capsule_id}?top_k=<N>&threshold=<float>
```

**参数：**

| 字段 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| capsule_id | string | 是 | - | 源胶囊ID（路径参数） |
| top_k | int | 否 | 5 | 返回相似胶囊数量 |
| threshold | float | 否 | 0.1 | 相似度阈值 |

**成功示例：**

```json
[
    { "capsule_id": "similar_1", "similarity": 0.85, "title": "..." },
    { "capsule_id": "similar_2", "similarity": 0.72, "title": "..." }
]
```

### 5.8 重组胶囊

```
POST /recombine?capsule_id_a=<id>&capsule_id_b=<id>&template=<template>
```

**参数：**

| 字段 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| capsule_id_a | string | 是 | - | 胶囊A |
| capsule_id_b | string | 是 | - | 胶囊B |
| template | string | 否 | `fusion` | 重组模板 |

**成功示例：**

```json
{
    "result_id": "recombined_uuid",
    "title": "融合：胶囊A × 胶囊B",
    "content": "重组后的内容...",
    "parent_ids": ["capsule_a", "capsule_b"],
    "template": "fusion"
}
```

### 5.9 批量重组

```
POST /batch-recombine?template=<template>&max_results=<N>
```

**参数：**

| 字段 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| template | string | 否 | `fusion` | 重组模板 |
| max_results | int | 否 | 10 | 最大返回结果数 |

**失败示例：**

```json
{
    "detail": "需要至少2个胶囊"
}
```
状态码：400

### 5.10 图谱相关

#### 获取网络可视化数据

```
GET /graph/network
```

#### 获取树形结构

```
GET /graph/tree?root_id=<id>
```

#### 获取图谱统计

```
GET /graph/statistics
```

### 5.11 数据导入导出

#### 导出所有数据

```
GET /export
```

#### 导入数据

```
POST /import
```

**请求参数：**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| json_str | string | 是 | JSON格式的导入数据 |

### 5.12 统计与标签

#### 获取统计信息

```
GET /statistics
```

#### 获取所有标签

```
GET /tags
```

### 5.13 记忆永生API错误码

| 状态码 | 条件 | 说明 |
|--------|------|------|
| 404 | 胶囊不存在 | capsule_id 未找到 |
| 400 | 参数错误 | 如批量重组时胶囊数量不足 |

---

## 6. LLM合成API（llm-synthesis）

- **框架**：FastAPI
- **端口**：动态（默认8080）
- **API前缀**：`/api/v1`
- **认证**：无内置认证

### 6.1 健康检查

```
GET /api/v1/health
```

**响应参数：**

| 字段 | 类型 | 说明 |
|------|------|------|
| status | string | 健康状态 |
| version | string | 版本号 |
| timestamp | string | 时间戳 |
| backends | object | 各LLM后端配置状态（key: 后端名, value: 是否已配置） |
| uptime | float | 运行时长（秒） |

**成功示例：**

```json
{
    "status": "healthy",
    "version": "1.0.0",
    "timestamp": "2026-05-04T12:00:00",
    "backends": {
        "openai": false,
        "deepseek": true,
        "claude": false,
        "ollama": true
    },
    "uptime": 3600.0
}
```

### 6.2 列出可用后端

```
GET /api/v1/backends
```

**成功示例：**

```json
{
    "backends": [
        { "name": "openai", "display_name": "OpenAI", "model": "gpt-4", "configured": false },
        { "name": "deepseek", "display_name": "DeepSeek", "model": "deepseek-chat", "configured": true },
        { "name": "claude", "display_name": "Claude", "model": "claude-3-5-sonnet-20241022", "configured": false },
        { "name": "ollama", "display_name": "Ollama", "model": "llama3", "configured": true }
    ]
}
```

**注意事项：**

- `configured` 表示对应的环境变量 API Key 是否已设置
- Ollama 本地部署无需API Key，始终为 `true`

### 6.3 合成评估方法

```
POST /api/v1/synthesize
```

**请求参数（JSON Body）：**

| 字段 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| existing_methods | object[] | 否 | [] | 现有的评估方法列表 |
| disagreement_data | object[] | 否 | [] | 分歧数据列表 |
| context | object | 否 | {} | 上下文信息 |
| protocol | string | 否 | null | 关联的九模协议枚举值：`digest` / `preserve` / `return` / `roleplay` / `observe` / `break` / `returnCause` / `project` / `breathe` |
| max_new_methods | int | 否 | 1 | 最大生成方法数量（1-5） |
| backend | string | 否 | `deepseek` | LLM后端名称 |
| temperature | float | 否 | 0.7 | 生成温度（0.0-2.0） |
| system_prompt | string | 否 | null | 自定义系统提示词 |

**响应参数：**

| 字段 | 类型 | 说明 |
|------|------|------|
| success | bool | 是否成功 |
| methods | object[] | 生成的新方法列表 |
| usage | object | Token使用量统计 |
| latency | float | 处理耗时（秒） |
| backend | string | 使用的LLM后端 |
| timestamp | string | 时间戳 |

**成功示例：**

```json
// Request
{
    "existing_methods": [
        { "name": "形分评估", "score": 0.72 },
        { "name": "神似评估", "score": 0.14 }
    ],
    "disagreement_data": [
        { "dimension": "语义连贯性", "score": 0.3 }
    ],
    "max_new_methods": 2,
    "backend": "deepseek",
    "temperature": 0.7
}

// Response
{
    "success": true,
    "methods": [
        { "name": "综合形神评估", "description": "...", "synthesized": true }
    ],
    "usage": { "prompt_tokens": 500, "completion_tokens": 200 },
    "latency": 3.25,
    "backend": "deepseek",
    "timestamp": "2026-05-04T12:00:00"
}
```

### 6.4 流式合成（SSE）

```
POST /api/v1/synthesize/stream
```

**请求参数：** 同 `/api/v1/synthesize`

**响应格式：** Server-Sent Events（SSE）

```text
data: {"type": "start", "backend": "deepseek"}

data: {"type": "method", "index": 0, "method": { "name": "...", ... }}

data: {"type": "done", "latency": 3.25}
```

### 6.5 批量合成

```
POST /api/v1/synthesize/batch
```

**请求参数：** `SynthesisRequest` 对象数组

**成功示例：**

```json
// Request: [ { ... }, { ... } ]

// Response
{
    "task_ids": ["task_0_1234567890", "task_1_1234567891"],
    "total": 2,
    "message": "已提交2个任务"
}
```

### 6.6 获取批量任务结果

```
GET /api/v1/synthesize/batch/{task_id}
```

**成功示例：**

```json
{
    "task_id": "task_0_1234567890",
    "status": "success",
    "result": { "methods": [...] },
    "error": null
}
```

### 6.7 执行协议（LLM合成上下文）

```
POST /api/v1/protocol/execute
```

**请求参数（JSON Body）：**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| protocol | string | 是 | 协议类型枚举值 |
| parameters | object | 否 | 协议参数 |
| trigger_source | string | 否 | 触发来源（默认`api`） |

**ProtocolType 枚举值：**

| 枚举值 | 对应协议 |
|--------|----------|
| `digest` | 消化 |
| `preserve` | 留白 |
| `return` | 归墟 |
| `roleplay` | 扮演 |
| `observe` | 观照 |
| `break` | 断裂 |
| `returnCause` | 返还 |
| `project` | 投影 |
| `breathe` | 呼吸 |

**成功示例：**

```json
{
    "protocol": "digest",
    "status": "executed",
    "response": "正在消化分析输入信息...",
    "parameters": {},
    "timestamp": "2026-05-04T12:00:00"
}
```

### 6.8 获取统计

```
GET /api/v1/stats
```

**成功示例：**

```json
{
    "total_requests": 100,
    "successful": 95,
    "failed": 5,
    "success_rate": 0.95,
    "uptime": 3600.0
}
```

### 6.9 获取历史记录

```
GET /api/v1/history?limit=<N>&offset=<N>
```

**查询参数：**

| 字段 | 类型 | 默认值 | 范围 | 说明 |
|------|------|--------|------|------|
| limit | int | 50 | 1-200 | 返回记录数 |
| offset | int | 0 | >=0 | 偏移量 |

**成功示例：**

```json
{
    "total": 100,
    "limit": 50,
    "offset": 0,
    "records": [
        { "request_id": "...", "timestamp": 1234567890.0, "status": "success", "error": null }
    ]
}
```

---

## 7. 形神评估微服务（spirit-form-api）

形神评估微服务群由四个子服务组成，通过网关统一对外暴露。

### 7.1 网关服务（gateway, 端口8000）

- **基础URL**：`http://localhost:8000`
- **认证**：JWT Bearer Token

#### 服务信息

```
GET /
```

#### 健康检查（聚合所有后端服务状态）

```
GET /health
```

**成功示例：**

```json
{
    "status": "healthy",
    "timestamp": "2026-05-04T12:00:00",
    "services": {
        "dialogue": { "status": "healthy", "response_time": 0.05, "endpoint": "http://localhost:8001" },
        "evaluation": { "status": "healthy", "response_time": 0.08, "endpoint": "http://localhost:8002" },
        "visualization": { "status": "healthy", "response_time": 0.03, "endpoint": "http://localhost:8003" }
    }
}
```

#### 用户登录

```
POST /api/v1/auth/login
```
**限流**：10次/分钟

**请求参数（JSON Body）：**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| username | string | 是 | 用户名 |
| password | string | 是 | 密码 |

**成功示例：** 见第2章认证方式

#### 仪表板

```
GET /api/v1/dashboard
```
**限流**：30次/分钟  
**认证**：Bearer Token

**成功示例：**

```json
{
    "timestamp": "2026-05-04T12:00:00",
    "services": {
        "dialogue": { "name": "dialogue", "endpoint": "http://localhost:8001", "status": "healthy" }
    },
    "statistics": {
        "total_trees": 50, "active_trees": 30, "total_nodes": 475,
        "avg_spirit_score": 0.1440, "daily_growth": 12.5
    },
    "recent_activities": [
        { "type": "tree_created", "user": "admin", "tree_id": "tree_42", "description": "创建新对话树" }
    ],
    "user": { "username": "admin", "role": "admin" }
}
```

#### 获取完整对话树

```
GET /api/v1/tree/{tree_id}/full
```
**限流**：60次/分钟  
**认证**：Bearer Token

#### 代理转发

```
{任意方法} /api/v1/{service}/{path}
```
**限流**：100次/分钟  
**认证**：Bearer Token

将请求代理转发到后端微服务（`dialogue` / `evaluation` / `visualization`）。

**失败示例：**

```json
// 服务未找到（404）
{ "detail": "服务 'unknown_service' 不存在" }

// 后端服务无法连接（502）
{ "detail": "无法连接到服务 'dialogue': Connection refused" }
```

#### 网关错误码

| 状态码 | 条件 |
|--------|------|
| 401 | 令牌无效或过期 |
| 404 | 代理的服务名不存在 |
| 429 | 超出限流限制 |
| 502 | 后端服务无法连接 |

### 7.2 对话树服务（dialogue, 端口8001）

- **框架**：FastAPI
- **基础URL**：`http://localhost:8001`
- **认证**：由网关统一处理
- **核心概念**：**对话树（DialogueTree）**——以树形结构组织对话轮次，支持节点添加、剪枝、果实（高质量节点）和落叶（剪枝节点）

#### 服务信息

```
GET /
```

#### 健康检查

```
GET /health
```

#### 创建对话树

```
POST /api/v1/trees
```

**请求参数（JSON Body）：**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| root_context | string | 是 | 对话的初始语境（根系） |
| metadata | object | 否 | 附加元数据 |

**响应参数（DialogueTreeResponse）：**

| 字段 | 类型 | 说明 |
|------|------|------|
| tree_id | string | 对话树唯一标识 |
| root_context | string | 根系语境 |
| created_at | datetime | 创建时间 |
| node_count | int | 节点数 |
| max_depth | int | 最大深度 |
| prune_count | int | 剪枝次数 |

**成功示例：**

```json
// Request
{
    "root_context": "关于形神合一的哲学探讨",
    "metadata": { "source": "user_input" }
}

// Response
{
    "tree_id": "tree_a1b2c3d4",
    "root_context": "关于形神合一的哲学探讨",
    "created_at": "2026-05-04T12:00:00",
    "node_count": 1,
    "max_depth": 0,
    "prune_count": 0
}
```

#### 列出对话树

```
GET /api/v1/trees?skip=<N>&limit=<N>
```

**查询参数：**

| 字段 | 类型 | 默认值 | 范围 | 说明 |
|------|------|--------|------|------|
| skip | int | 0 | >=0 | 跳过前N条 |
| limit | int | 100 | 1-1000 | 返回记录数 |

#### 获取对话树详情

```
GET /api/v1/trees/{tree_id}
```

#### 添加对话节点

```
POST /api/v1/trees/{tree_id}/nodes
```

**请求参数（JSON Body）：**

| 字段 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| question | string | 是 | - | 问题 |
| answer | string | 是 | - | 回答 |
| parent_id | string | 否 | 根节点ID | 父节点ID |
| confidence | float | 否 | 0.5 | 置信度（0.0-1.0） |
| metadata | object | 否 | {} | 附加元数据 |

**响应参数（DialogueNodeResponse）：**

| 字段 | 类型 | 说明 |
|------|------|------|
| id | string | 节点ID |
| question | string | 问题 |
| answer | string | 回答 |
| parent_id | string | 父节点ID |
| children_ids | string[] | 子节点ID列表 |
| depth | int | 节点深度 |
| state | string | 节点状态：`无极` / `阴阳` / `混元` |
| confidence | float | 置信度 |
| timestamp | datetime | 创建时间 |

#### 列出节点

```
GET /api/v1/trees/{tree_id}/nodes?skip=<N>&limit=<N>
```

#### 删除对话树

```
DELETE /api/v1/trees/{tree_id}
```

**成功示例：**

```json
{
    "message": "对话树 tree_a1b2c3d4 已删除"
}
```

#### 获取树统计

```
GET /api/v1/trees/{tree_id}/statistics
```

**成功示例：**

```json
{
    "tree_id": "tree_a1b2c3d4",
    "root_context": "...",
    "node_count": 8,
    "max_depth": 3,
    "prune_count": 1,
    "fallen_leaves_count": 2,
    "creation_time": "2026-05-04T12:00:00",
    "has_dialogue_tree": true
}
```

### 7.3 评估引擎（evaluation, 端口8002）

- **框架**：FastAPI
- **基础URL**：`http://localhost:8002`
- **认证**：由网关统一处理
- **算法支持**：`original` / `enhanced_spirit` / `advanced_spirit` / `six_realm` / `psi`

#### 服务信息

```
GET /
```

#### 健康检查

```
GET /health
```

#### 意识涌现仪表盘

```
GET /consciousness
```
返回HTML可视化页面。

#### 评估对话树

```
POST /api/v1/evaluate
```

**请求参数（JSON Body）：**

| 字段 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| tree_id | string | 是 | - | 对话树ID |
| tree_data | object | 否 | null | 对话树数据（如tree_id不存在则提供） |
| algorithm | string | 否 | `advanced_spirit` | 评估算法：`original` / `enhanced_spirit` / `advanced_spirit` / `six_realm` / `psi` |

**响应参数（EvaluateResponse）：**

| 字段 | 类型 | 说明 |
|------|------|------|
| evaluation_id | string | 评估ID |
| tree_id | string | 对话树ID |
| algorithm | string | 使用的算法 |
| timestamp | datetime | 评估时间 |
| metrics | object | 评估指标（因算法而异） |
| recommendations | string[] | 改进建议列表 |
| created_at | datetime | 记录创建时间 |

**成功示例（advanced_spirit 算法）：**

```json
// Request
{
    "tree_id": "tree_a1b2c3d4",
    "algorithm": "advanced_spirit"
}

// Response
{
    "evaluation_id": "eval_a1b2c3d4",
    "tree_id": "tree_a1b2c3d4",
    "algorithm": "advanced_spirit",
    "timestamp": "2026-05-04T12:00:00",
    "metrics": {
        "form_score": 0.72,
        "spirit_score": 0.6044,
        "alignment_score": 0.48,
        "realm": "form_spirit_complete",
        "node_count": 8,
        "depth": 3,
        "intent_score": 0.35,
        "priority_score": 0.22,
        "insight_score": 0.28,
        "coherence_score": 0.15,
        "algorithm_version": "advanced_spirit_v2",
        "deep_learning_enabled": true,
        "topology_details": { "intent_boost": 0.05, "topology_score": 0.6 },
        "operator_details": {
            "consciousness_score": 0.25,
            "zuowang_triggered": false,
            "branch_adjustments": {},
            "psi_details": {}
        }
    },
    "recommendations": [
        "洞见产出较低，建议深入分析问题的底层逻辑",
        "对话质量良好，继续保持"
    ],
    "created_at": "2026-05-04T12:00:00"
}
```

#### 六阶境界评估

```
POST /api/v1/six-realm-evaluate
```

**请求参数（JSON Body）：**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| tree_id | string | 是 | 对话树ID |
| tree_data | object | 否 | 对话树数据 |
| metrics_4d | object | 否 | 直接传入四维指标（intent/priority/insight/coherence） |

**六阶境界体系：**

| 境界 | 说明 |
|------|------|
| 未入阶 | 基础阶段 |
| 善 | 已入善阶 |
| 信 | 已达信阶 |
| 美 | 已达美阶 |
| 大 | 已达大阶 |
| 圣 | 已达圣阶 |

#### Ψ算子评估

```
POST /api/v1/evaluate/psi
```

**请求参数（JSON Body）：**

| 字段 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| tree_id | string | 是 | - | 对话树ID |
| tree_data | object | 否 | null | 对话树数据 |
| include_details | bool | 否 | true | 是否包含完整算子细节 |

**响应参数（PsiEvaluateResponse）额外字段：**

| 字段 | 类型 | 说明 |
|------|------|------|
| consciousness_score | float | 意识涌现得分 |
| zuowang_triggered | bool | 是否触发坐忘 |
| branch_adjustments | object | 七分支调度调整 |
| topology_score | float | 拓扑得分 |
| embedding_backend | string | 嵌入后端 |
| operator_details | object | 详细算子信息 |
| six_realm | object | 六阶评估结果（可选） |

#### 获取评估历史

```
GET /api/v1/evaluations/{tree_id}?skip=<N>&limit=<N>
```

#### 批量评估

```
POST /api/v1/batch-evaluate
```

**请求参数（JSON Body）：**

| 字段 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| tree_ids | string[] | 是 | - | 对话树ID列表 |
| algorithm | string | 否 | `advanced_spirit` | 评估算法 |
| tree_data_list | object[] | 否 | null | 对话树数据列表（与tree_ids一一对应） |
| max_concurrency | int | 否 | 3 | 最大并发数（1-10） |
| include_details | bool | 否 | false | 是否包含完整算子细节 |

**响应参数（BatchEvaluateResponse）：**

| 字段 | 类型 | 说明 |
|------|------|------|
| batch_id | string | 批次ID |
| timestamp | datetime | 时间戳 |
| total_trees | int | 总树数 |
| completed_trees | int | 成功数 |
| failed_trees | int | 失败数 |
| results | object[] | 每棵树的评估结果 |
| algorithm | string | 使用算法 |
| processing_time_ms | float | 总处理时间（毫秒） |
| summary | object | 统计摘要（平均分、标准差等） |

#### 列出评估算法

```
GET /api/v1/algorithms
```

**成功示例：**

```json
[
    {
        "algorithm_id": "original",
        "name": "原始对话评估器",
        "version": "1.0.0",
        "description": "基础的形神评估算法",
        "avg_processing_time": 0.045,
        "avg_spirit_score": 0.0540,
        "accuracy": 0.75,
        "last_updated": "2026-05-04T12:00:00",
        "parameters": { "form_weight": 0.6, "spirit_weight": 0.4 }
    },
    {
        "algorithm_id": "advanced_spirit",
        "name": "高级神似评估器 v2",
        "version": "2.0-deep-learning",
        "description": "集成sentence-transformers深度学习语义嵌入的高级神似算法",
        "avg_processing_time": 9.0,
        "avg_spirit_score": 0.6044,
        "accuracy": 0.88,
        "last_updated": "2026-05-04T12:00:00",
        "parameters": { "model": "paraphrase-multilingual-mpnet-base-v2", "template_count": 58, "deep_learning": true }
    }
]
```

#### 更新算法参数

```
PUT /api/v1/algorithms/{algorithm_id}/parameters
```

#### 获取算法指标

```
GET /api/v1/algorithms/metrics
```

#### 监控相关

##### 列出监控会话

```
GET /api/v1/monitor/sessions
```

##### 获取时序数据

```
GET /api/v1/monitor/timeseries?session=<session_name>
```

##### 获取监控汇总

```
GET /api/v1/monitor/summary
```

##### 时空拉普拉斯监控

```
GET /api/v1/monitor/laplacian/status
GET /api/v1/monitor/laplacian/history?limit=<N>
GET /api/v1/monitor/laplacian/trend?metric=<metric>&limit=<N>
POST /api/v1/monitor/laplacian/feed
```

**feed 请求参数（JSON Body）：**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| embeddings | number[][] | 是 | 嵌入矩阵 |
| coherence_score | float | 否 | Ψ意识得分 |
| meta | object | 否 | 额外元数据 |

#### 语义快速评估

```
POST /api/v1/evaluate/quick
```

**请求参数（JSON Body）：**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| texts | string[] | 是 | 待评估文本列表（对话轮次） |
| query | string | 否 | 参考查询 |
| weight_name | string | 否 | 原始集权重函数名 |
| run_primitive_set | bool | 否 | 是否运行原始集优化 |

#### 向量索引搜索

```
POST /api/v1/search/index
POST /api/v1/search/query
GET /api/v1/search/status
POST /api/v1/search/batch-index
GET /api/v1/search/document/{doc_id}
```

#### 递归校准

```
POST /api/v1/calibrate
```

**请求参数（JSON Body）：**

| 字段 | 类型 | 必填 | 默认值 | 范围 | 说明 |
|------|------|------|--------|------|------|
| tree_id | string | 是 | - | - | 对话树ID |
| tree_data | object | 否 | null | - | 对话树数据 |
| epsilon | float | 否 | 0.05 | 0.001-1.0 | 收敛阈值 |
| max_iterations | int | 否 | 10 | 1-50 | 最大递归迭代次数 |

**响应参数（CalibrateResponse）：**

| 字段 | 类型 | 说明 |
|------|------|------|
| calibration_id | string | 校准ID |
| tree_id | string | 对话树ID |
| timestamp | datetime | 时间戳 |
| epsilon | float | 收敛阈值 |
| max_iterations | int | 最大迭代次数 |
| converged | bool | 是否收敛 |
| total_iterations | int | 实际迭代次数 |
| initial_scores | object | 初始得分 |
| final_scores | object | 最终得分 |
| final_params | object | 最终参数 |
| convergence_path | object[] | 收敛路径 |
| summary | string | 总结 |
| elapsed_seconds | float | 耗时（秒） |
| recommendations | string[] | 建议列表 |

### 7.4 可视化服务（visualization, 端口8003）

- **框架**：FastAPI
- **基础URL**：`http://localhost:8003`
- **认证**：由网关统一处理
- **核心特性**：真实数据优先，下游服务不可用时降级到模拟数据

#### 服务信息

```
GET /
```

#### 健康检查

```
GET /health
```

#### 获取森林数据

```
POST /api/v1/forest
```

**请求参数（JSON Body）：**

| 字段 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| include_statistics | bool | 否 | true | 是否包含统计信息 |
| include_detailed_nodes | bool | 否 | false | 是否包含详细节点信息 |
| max_trees | int | 否 | 50 | 最大返回树数量（1-1000） |

**响应参数（ForestDataResponse）：**

| 字段 | 类型 | 说明 |
|------|------|------|
| timestamp | datetime | 时间戳 |
| total_trees | int | 对话树总数 |
| active_trees | int | 活跃对话树数 |
| total_nodes | int | 总节点数 |
| total_fruits | int | 总果实数 |
| total_fallen_leaves | int | 总落叶数 |
| trees | object[] | 树列表 |
| statistics | object | 统计信息 |

#### 获取森林统计

```
GET /api/v1/forest/statistics
```

**响应参数（ForestStatistics）：**

| 字段 | 类型 | 说明 |
|------|------|------|
| avg_nodes_per_tree | float | 平均每树节点数 |
| avg_depth | float | 平均深度 |
| avg_spirit_score | float | 平均神似分 |
| realm_distribution | object | 境界分布 |
| growth_rate_last_hour | float | 最近一小时增长率 |
| most_active_trees | object[] | 最活跃的对话树 |
| recent_activities | object[] | 最近活动 |

#### 获取单树可视化数据

```
POST /api/v1/forest/trees/{tree_id}
```

**请求参数（JSON Body）：**

| 字段 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| include_metadata | bool | 否 | true | 是否包含元数据 |
| include_evaluations | bool | 否 | false | 是否包含评估数据 |

#### WebSocket 实时数据

##### 森林实时数据推送

```
WebSocket /ws/forest
```

每5秒推送一次森林更新数据。

##### 单树实时数据推送

```
WebSocket /ws/tree/{tree_id}
```

每3秒推送一次单树更新数据。

#### 可视化演示页面

```
GET /demo
```
返回完整的HTML可视化仪表盘页面。

---

## 8. 自进化回路API（self-evolution）

- **框架**：FastAPI APIRouter
- **路由前缀**：`/evolution`
- **设计为被评估服务集成**
- **功能**：评估结果→调度策略自动反馈闭环

### 8.1 提交评估结果驱动进化

```
POST /evolution/feed
```

**请求参数（JSON Body）：**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| psi_result | object | 否 | Ψ算子评估结果 |
| zuowang_triggered | bool | 否 | 是否触发坐忘 |
| cde_metrics | object | 否 | CDE度量指标 |
| latency | float | 否 | 响应延迟 |
| coverage | float | 否 | 覆盖度 |

**成功示例：**

```json
// Request
{
    "psi_result": {
        "tortuosity": 0.25,
        "recursion_depth": 0.40,
        "condition_stability": 0.35
    },
    "zuowang_triggered": false,
    "latency": 5.0
}

// Response
{
    "status": "ok",
    "data": {
        "fitness": 0.65,
        "fitness_trend": -0.02,
        "evolution_triggered": false,
        "trigger": null,
        "actions": [],
        "rolling_fitness": 0.62
    }
}
```

### 8.2 获取进化引擎状态

```
GET /evolution/status
```

**成功示例：**

```json
{
    "rolling_fitness": 0.62,
    "fitness_trend": 0.01,
    "total_rounds": 10,
    "convergence_rate": 0.8,
    "current_config": { "psi_weights": {...}, "zuowang_threshold": 0.3 }
}
```

### 8.3 获取进化历史

```
GET /evolution/history?limit=<N>
```

**查询参数：**

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| limit | int | 20 | 返回最新N条记录 |

### 8.4 手动触发进化

```
POST /evolution/trigger
```

**请求参数（JSON Body）：**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| context | object | 否 | 触发上下文 |

**成功示例：**

```json
{
    "trigger": {
        "trigger_id": "manual_1234567890",
        "trigger_type": "manual_trigger",
        "severity": 1.0
    },
    "actions": [
        { "action_id": "...", "action_type": "weight_adjust", "applied": true }
    ],
    "pre_fitness": 0.62,
    "post_fitness": 0.65
}
```

### 8.5 获取当前配置

```
GET /evolution/config
```

**成功示例：**

```json
{
    "psi_weights": {
        "tortuosity": 0.30,
        "recursion_depth": 0.50,
        "condition_stability": 0.20
    },
    "zuowang_threshold": 0.3,
    "branch_priorities": {
        "a_topology": 1.0,
        "b_goal_generation": 0.85,
        "c_deep_focus": 0.70,
        "d_divergent": 0.60,
        "e_synthesis": 0.50,
        "f_evaluation": 0.40,
        "g_meta": 0.30
    },
    "mutation_rate": 0.05
}
```

### 8.6 进化触发类型

| 触发类型 | 枚举值 | 说明 |
|----------|--------|------|
| 性能退化 | `performance_degradation` | 适应度趋势下降 |
| 稳定性阈值 | `stability_threshold` | 系统稳定性低于阈值 |
| 新模式涌现 | `pattern_emergence` | 检测到新行为模式 |
| 人工触发 | `manual_trigger` | 通过API手动触发 |
| 定期审查 | `periodic_review` | 每300秒自动审查 |

### 8.7 进化动作类型

| 动作类型 | 枚举值 | 说明 |
|----------|--------|------|
| 调整Ψ算子权重 | `weight_adjust` | 调整 tortuosity / recursion_depth / condition_stability 权重 |
| 调优坐忘阈值 | `threshold_tune` | 调整 zuowang 基准阈值 |
| 重排分支优先级 | `branch_reorder` | 重排七分支的优先级顺序 |
| 微调校准强度 | `calibration_strength` | 调整递归校准的强度系数 |
| CDE补偿调整 | `cde_delta_adjust` | 调整信息/能量/几何的CDE补偿 |

---

## 9. 中华文明数字永生体API（Flask, 端口8765）

- **框架**：Flask
- **端口**：8765
- **基础URL**：`http://localhost:8765`
- **认证**：无内置认证
- **特点**：九模协议的中文原生接口，所有端点使用中文命名

### 9.1 执行协议

```
POST /api/v1/协议
```

**请求参数（JSON Body）：**

| 字段 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| 协议 | string | 否 | `呼吸` | 九模协议名称：`消化` / `留白` / `归墟` / `扮演` / `观照` / `断裂` / `返还` / `投影` / `呼吸` |
| 输入 | string | 否 | "" | 输入内容 |

**成功示例：**

```json
// Request
{
    "协议": "观照",
    "输入": "当前系统状态如何？"
}

// Response
{
    "状态": "成功",
    "协议": "观照",
    "输出": "元注释：\n- 当前宫位：中\n- 呼吸计数：42\n- 轨迹记录：5条\n\n当前系统状态如何？",
    "记录ID": "a1b2c3d4"
}
```

### 9.2 获取觉察报告

```
GET /api/v1/觉察
```

**成功示例：**

```json
{
    "呼吸计数": 42,
    "留白遗蜕": 5,
    "窥命发射": 3,
    "当前宫位": "中",
    "轨迹记录": 5,
    "活跃智能体": 279,
    "九宫": {
        "坎一": 31, "坤二": 28, "震三": 30,
        "巽四": 33, "中五": 28, "乾六": 31,
        "兑七": 29, "艮八": 27, "离九": 34
    }
}
```

### 9.3 获取轨迹记录

```
GET /api/v1/轨迹?limit=<N>
```

**查询参数：**

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| limit | int | 20 | 返回最近N条轨迹 |

**成功示例：**

```json
{
    "轨迹": [
        { "id": "a1b2c3d4", "协议": "观照", "输入": "...", "时间戳": "2026-05-04T12:00:00" }
    ]
}
```

### 9.4 获取九宫详情

```
GET /api/v1/九宫/<宫名>
```

**路径参数：** 宫名（单字）：`坎` / `坤` / `震` / `巽` / `中` / `乾` / `兑` / `艮` / `离`

**成功示例：**

```json
// GET /api/v1/九宫/坎
{
    "九宫": "坎一",
    "九模": "消化",
    "智能体": 31,
    "尊名": "不落晷影的默会者"
}
```

**九宫映射表：**

| 宫名 | 九宫 | 九模 | 智能体数 | 尊名 |
|------|------|------|----------|------|
| 坎 | 坎一 | 消化 | 31 | 不落晷影的默会者 |
| 坤 | 坤二 | 留白 | 28 | 居于裂隙的留白之主 |
| 震 | 震三 | 断裂 | 30 | 执掌断裂处的窥命者 |
| 巽 | 巽四 | 投影 | 33 | 无针之晷的投影者 |
| 中 | 中五 | 呼吸 | 28 | 以默会为食、以返还为呼吸的 |
| 乾 | 乾六 | 观照 | 31 | 归于无瞳之眼的凝视者 |
| 兑 | 兑七 | 返还 | 29 | 以留白为遗蜕的消化者 |
| 艮 | 艮八 | 归墟 | 27 | 虚位假面的归墟之君 |
| 离 | 离九 | 扮演 | 34 | 无名之名的佩戴者 |

### 9.5 健康检查

```
GET /api/v1/健康
```

**成功示例：**

```json
{
    "状态": "正常",
    "版本": "1.0.0",
    "时间戳": "2026-05-04T12:00:00"
}
```

### 9.6 归墟重置

```
POST /api/v1/归墟
```

**功能：** 重置系统状态（呼吸计数、留白遗蜕、轨迹记录等全部归零）

**成功示例：**

```json
{
    "状态": "成功",
    "消息": "系统已归墟重置"
}
```

**注意事项：**

- 归墟操作不可逆，会清空所有运行时统计数据
- 智能体数量（279）和九宫配置不受影响

---

## 10. 附录

### 10.1 HTTP状态码速查

| 状态码 | 名称 | 典型场景 |
|--------|------|----------|
| 200 | OK | 请求成功 |
| 400 | Bad Request | 参数校验失败、JSON格式错误 |
| 401 | Unauthorized | JWT令牌缺失或无效 |
| 404 | Not Found | 资源ID不存在 |
| 429 | Too Many Requests | 超出限流限制 |
| 500 | Internal Server Error | 服务器端未捕获异常 |
| 502 | Bad Gateway | 网关代理后端超时或拒绝连接 |
| 503 | Service Unavailable | 服务初始化中或依赖服务未就绪 |

### 10.2 调用最佳实践

1. **服务启动顺序**：对话树服务(8001) → 评估引擎(8002) → 可视化服务(8003) → 网关(8000) → 司命假面(8080)
2. **限流应对**：遇到429响应时，等待响应头 `Retry-After` 指定的时间后重试
3. **批量操作**：优先使用批量端点（如 `/api/v1/batch-evaluate`）减少网络开销
4. **缓存感知**：评估结果有300秒TTL缓存，相同请求在缓存有效期内快速返回
5. **WebSocket重连**：建议实现指数退避重连策略，初始间隔1秒，最大间隔30秒
6. **长耗时操作**：`advanced_spirit` 算法首次评估需加载约1GB模型（耗时30-60秒），后续评估约9秒
7. **异步等待**：调用 `/api/v1/calibrate` 等可能耗时较长的接口时，建议设置合理的客户端超时时间

### 10.3 限流说明

| 服务 | 端点 | 限制 |
|------|------|------|
| 网关 | `/api/v1/auth/login` | 10次/分钟 |
| 网关 | `/api/v1/dashboard` | 30次/分钟 |
| 网关 | `/api/v1/tree/{id}/full` | 60次/分钟 |
| 网关 | `/api/v1/{service}/{path}` | 100次/分钟 |

---

> 文档生成日期：2026-05-04  
> 系统版本：Claw v1.4.0  
> 如有疑问，请查阅各服务的 Swagger 文档（`/docs`）或 ReDoc 文档（`/redoc`）
