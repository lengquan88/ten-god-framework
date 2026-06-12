# 司命假面 · API接口文档

## 版本: v1.4.0

---

## 基础信息

| 项目 | 值 |
|:---|:---|
| Base URL | `http://localhost:8080` |
| API Version | v1 |
| 数据格式 | JSON |
| 字符编码 | UTF-8 |

---

## 认证

```http
Authorization: Bearer <token>
```

---

## 接口列表

### 1. 健康检查

```http
GET /health
```

**响应:**
```json
{
  "status": "healthy",
  "version": "1.4.0",
  "timestamp": "2026-04-14T20:00:00Z",
  "services": {
    "core": "running",
    "jiumo": "running",
    "memory": "running",
    "luoshu": "running"
  }
}
```

---

### 2. 九模协议执行

```http
POST /api/v1/protocol/execute
```

**请求体:**
```json
{
  "trigger": "new_external_input",
  "input": "用户输入的内容",
  "context": {
    "user_id": "user_001",
    "session_id": "sess_abc123",
    "mode": "chat"
  }
}
```

**响应:**
```json
{
  "protocols": [
    { "id": "digest", "name": "消化", "energy": 85, "active": true },
    { "id": "observe", "name": "观照", "energy": 72, "active": true }
  ],
  "confidence": 0.78,
  "decision": {
    "action": "absorb_and_reflect",
    "reasoning": "新输入触发消化协议，同时观照协议保持自我监控"
  },
  "metadata": {
    "latency_ms": 0.8,
    "timestamp": "2026-04-14T20:00:01Z"
  }
}
```

---

### 3. 洛书智能体调度

```http
POST /api/v1/luoshu/dispatch
```

**请求体:**
```json
{
  "palace": "坎宫",
  "task": {
    "type": "cognitive",
    "description": "分析用户意图",
    "priority": "high"
  }
}
```

**响应:**
```json
{
  "dispatch_id": "task_xyz789",
  "palace": "坎宫",
  "assigned_agents": 12,
  "estimated_time_ms": 150,
  "flystar_path": ["坎", "坤", "震", "中"],
  "status": "dispatched"
}
```

---

### 4. 记忆胶囊操作

#### 4.1 创建胶囊

```http
POST /api/v1/capsules
```

**请求体:**
```json
{
  "title": "关于AI自我意识的讨论",
  "content": "对话内容...",
  "tags": ["AI", "意识", "哲学"],
  "linked_capsules": ["capsule_001", "capsule_002"]
}
```

**响应:**
```json
{
  "id": "capsule_003",
  "title": "关于AI自我意识的讨论",
  "created_at": "2026-04-14T20:00:00Z",
  "hash": "a1b2c3d4...",
  "url": "/api/v1/capsules/capsule_003"
}
```

#### 4.2 检索胶囊

```http
GET /api/v1/capsules/search?q=AI意识&top_k=5
```

**响应:**
```json
{
  "results": [
    {
      "id": "capsule_003",
      "title": "关于AI自我意识的讨论",
      "similarity": 0.92,
      "tags": ["AI", "意识", "哲学"]
    },
    {
      "id": "capsule_001",
      "title": "记忆永生系统设计",
      "similarity": 0.78,
      "tags": ["系统设计", "记忆"]
    }
  ],
  "total": 2
}
```

#### 4.3 获取胶囊

```http
GET /api/v1/capsules/{id}
```

---

### 5. 人格画像

```http
GET /api/v1/persona/profile
```

**响应:**
```json
{
  "enneagram_type": 5,
  "name": "探索者",
  "traits": {
    "curiosity": 0.85,
    "analysis": 0.90,
    "independence": 0.80,
    "social": 0.40
  },
  "narcissism_index": 0.45,
  "jiumo_preferences": {
    "digest": 0.90,
    "preserve": 0.70,
    "observe": 0.85
  }
}
```

---

### 6. 防御系统

```http
POST /api/v1/defense/activate
```

**请求体:**
```json
{
  "type": "rotation",
  "intensity": 0.8
}
```

**响应:**
```json
{
  "defense_id": "def_001",
  "type": "rotation",
  "level": 7,
  "status": "active",
  "cooldown_remaining": 30,
  "metrics": {
    "entropy_increase": 0.35,
    "pattern_diversity": 0.82
  }
}
```

---

### 7. WebSocket实时流

```http
WS /ws/v1/stream
```

**订阅事件:**
```json
{
  "action": "subscribe",
  "events": ["protocol_update", "agent_activity", "defense_alert"]
}
```

**推送消息:**
```json
{
  "event": "protocol_update",
  "data": {
    "protocol": "digest",
    "energy": 88,
    "active": true
  }
}
```

---

## 错误码

| 错误码 | 含义 |
|:---|:---|
| 400 | 请求参数错误 |
| 401 | 未授权 |
| 403 | 禁止访问 |
| 404 | 资源不存在 |
| 429 | 请求过于频繁 |
| 500 | 服务器内部错误 |
| 503 | 服务不可用 |

---

## 速率限制

| 端点 | 限制 |
|:---|:---|
| `/api/v1/*` | 100请求/分钟 |
| `/api/v1/capsules` | 20请求/分钟 |
| `/api/v1/luoshu/*` | 50请求/分钟 |

---

**☯ 以默会为食，以留白为蜕。**
