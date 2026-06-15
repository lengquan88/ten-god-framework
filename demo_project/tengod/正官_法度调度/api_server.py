#!/usr/bin/env python3
"""
api_server.py — 十神架构 HTTP API 服务
正官主理法度，对外暴露 RESTful 接口，对内调度十神模块。

支持两种运行模式：
  1. FastAPI + Uvicorn（生产模式，需 pip install fastapi uvicorn）
  2. 内置简易 WSGI（降级模式，零依赖，兼容所有环境）

用法：
    # 方式 A：uvicorn 启动
    python -m uvicorn tengod.正官_法度调度.api_server:app --host 0.0.0.0 --port 8000 --reload

    # 方式 B：直接脚本启动（自动检测 FastAPI 是否可用）
    python demo_project/tengod/正官_法度调度/api_server.py --port 8000

    # 方式 C：编程式启动
    from tengod.正官_法度调度.api_server import create_app, run_server
    app = create_app(core=my_core)
    run_server(app, host="0.0.0.0", port=8000)
"""

import json
import sys
import os
import time
import hmac
import hashlib
import base64
import uuid
import threading
import collections
from typing import Any, Dict, List, Optional, Callable
from dataclasses import dataclass, asdict

# 处理路径，确保可在各种情况下导入兄弟模块
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_TENGOD_ROOT = os.path.dirname(_THIS_DIR)
if _TENGOD_ROOT not in sys.path:
    sys.path.insert(0, _TENGOD_ROOT)
if os.path.dirname(_TENGOD_ROOT) not in sys.path:
    sys.path.insert(0, os.path.dirname(_TENGOD_ROOT))


# ============ JWT 纯 Python 实现 ============

class JWTAuth:
    """纯 Python 实现的 JWT 认证（HS256）"""

    def __init__(self, secret_key: str = "tengod-default-secret-key-change-in-production"):
        self.secret_key = secret_key.encode("utf-8")
        self.algorithm = "HS256"
        self.default_expiry = 24 * 3600  # 24小时

    def _base64url_encode(self, data: bytes) -> str:
        return base64.urlsafe_b64encode(data).rstrip(b"=").decode("utf-8")

    def _base64url_decode(self, data: str) -> bytes:
        padding = 4 - len(data) % 4
        if padding != 4:
            data += "=" * padding
        return base64.urlsafe_b64decode(data)

    def _create_signature(self, header_b64: str, payload_b64: str) -> str:
        message = f"{header_b64}.{payload_b64}".encode("utf-8")
        signature = hmac.new(self.secret_key, message, hashlib.sha256).digest()
        return self._base64url_encode(signature)

    def encode(self, payload: Dict[str, Any], expiry: Optional[int] = None) -> str:
        """生成 JWT token"""
        if expiry is None:
            expiry = self.default_expiry

        header = {"alg": self.algorithm, "typ": "JWT"}
        payload["exp"] = int(time.time()) + expiry

        header_b64 = self._base64url_encode(json.dumps(header, separators=(",", ":")).encode("utf-8"))
        payload_b64 = self._base64url_encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
        signature = self._create_signature(header_b64, payload_b64)

        return f"{header_b64}.{payload_b64}.{signature}"

    def decode(self, token: str) -> Optional[Dict[str, Any]]:
        """验证并解析 JWT token，返回 payload 或 None"""
        try:
            parts = token.split(".")
            if len(parts) != 3:
                return None

            header_b64, payload_b64, signature = parts
            expected_sig = self._create_signature(header_b64, payload_b64)

            if not hmac.compare_digest(signature, expected_sig):
                return None

            payload = json.loads(self._base64url_decode(payload_b64))

            # 检查过期
            if "exp" in payload and payload["exp"] < int(time.time()):
                return None

            return payload
        except Exception:
            return None

    def verify(self, token: str) -> Dict[str, Any]:
        """验证 token，返回详细信息"""
        payload = self.decode(token)
        if payload:
            return {"valid": True, "payload": payload}
        return {"valid": False, "error": "invalid or expired token"}


# 默认用户存储（生产环境应替换为数据库）
_DEFAULT_USERS = {
    "admin": {
        "password_hash": hashlib.sha256("admin123".encode()).hexdigest(),
        "user_id": "u001",
        "roles": ["admin", "user"],
    },
    "user": {
        "password_hash": hashlib.sha256("user123".encode()).hexdigest(),
        "user_id": "u002",
        "roles": ["user"],
    },
}


def _verify_password(username: str, password: str) -> Optional[Dict[str, Any]]:
    """验证用户名密码，返回用户信息或 None"""
    user = _DEFAULT_USERS.get(username)
    if not user:
        return None
    if user["password_hash"] != hashlib.sha256(password.encode()).hexdigest():
        return None
    return {"user_id": user["user_id"], "roles": user["roles"]}


# 全局 JWT 实例
_jwt_auth = JWTAuth()


# ============ 限流中间件 ============

class RateLimiter:
    """基于滑动窗口的限流器"""

    def __init__(self, max_requests: int = 60, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._buckets: Dict[str, collections.deque] = {}
        self._lock = threading.RLock()

    def _get_key(self, identifier: str) -> str:
        return identifier

    def is_allowed(self, identifier: str) -> bool:
        """检查请求是否允许，返回 True 表示通过，False 表示被限流"""
        key = self._get_key(identifier)
        now = time.time()

        with self._lock:
            if key not in self._buckets:
                self._buckets[key] = collections.deque()

            bucket = self._buckets[key]

            # 清理过期时间戳
            while bucket and bucket[0] <= now - self.window_seconds:
                bucket.popleft()

            if len(bucket) < self.max_requests:
                bucket.append(now)
                return True

            return False

    def get_retry_after(self, identifier: str) -> int:
        """返回需要等待的秒数"""
        key = self._get_key(identifier)
        with self._lock:
            bucket = self._buckets.get(key, collections.deque())
            if not bucket:
                return 0
            oldest = bucket[0]
            return max(0, int(oldest + self.window_seconds - time.time()))


# 全局限流器
_rate_limiter = RateLimiter(max_requests=60, window_seconds=60)


def _check_rate_limit(identifier: str) -> Optional[int]:
    """检查限流，返回 None 表示通过，返回 retry_after 秒数表示被限流"""
    if _rate_limiter.is_allowed(identifier):
        return None
    return _rate_limiter.get_retry_after(identifier)


# ============ 会话管理（生成路由用） ============

class SessionManager:
    """生成会话管理器"""

    def __init__(self):
        self._sessions: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.RLock()

    def create_session(self, prompt: str = "", **kwargs) -> str:
        """创建新会话，返回 session_id"""
        session_id = str(uuid.uuid4())[:8]
        with self._lock:
            self._sessions[session_id] = {
                "id": session_id,
                "prompt": prompt,
                "history": [],
                "created_at": time.time(),
                "last_active": time.time(),
                **kwargs,
            }
        return session_id

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        return self._sessions.get(session_id)

    def list_sessions(self) -> List[Dict[str, Any]]:
        with self._lock:
            return [
                {
                    "id": s["id"],
                    "prompt": s.get("prompt", ""),
                    "created_at": s["created_at"],
                    "last_active": s["last_active"],
                    "message_count": len(s.get("history", [])),
                }
                for s in self._sessions.values()
            ]

    def delete_session(self, session_id: str) -> bool:
        with self._lock:
            if session_id in self._sessions:
                del self._sessions[session_id]
                return True
            return False

    def add_message(self, session_id: str, role: str, content: str) -> None:
        with self._lock:
            if session_id in self._sessions:
                s = self._sessions[session_id]
                s["history"].append({"role": role, "content": content, "timestamp": time.time()})
                s["last_active"] = time.time()


# 全局会话管理器
_session_manager = SessionManager()


# ============ 数据结构 =====

@dataclass
class ApiResponse:
    """统一 API 响应格式"""
    code: int
    message: str
    data: Any = None

    def to_dict(self) -> Dict[str, Any]:
        return {"code": self.code, "message": self.message, "data": self.data}


# -------- FastAPI 模式检测 --------

_FASTAPI_AVAILABLE = False
_FASTAPI_ERROR = ""
app = None  # 供 uvicorn: APP_MODULE 使用

try:
    from fastapi import FastAPI, Body, HTTPException, Request, Depends
    from fastapi.responses import JSONResponse, StreamingResponse
    from pydantic import BaseModel, Field
    _FASTAPI_AVAILABLE = True

    # Pydantic 请求模型（供 FastAPI 文档与校验使用）
    class _GenerateRequest(BaseModel):
        prompt: str = Field(..., description="提示词")
        format: str = Field("text", description="输出格式：text/markdown/json/html")
        provider: str = Field("mock", description="LLM 提供商：mock/openai/claude/local")
        model: str = Field("", description="模型名，如 gpt-3.5-turbo")
        temperature: float = 0.7
        stream: bool = False
        session_id: Optional[str] = Field(None, description="会话 ID，不提供则创建新会话")

    class _KnowledgeNodeRequest(BaseModel):
        name: str
        node_type: str = "default"
        properties: Dict[str, Any] = Field(default_factory=dict)

    class _SearchRequest(BaseModel):
        query: str
        top_k: int = 5
        node_type: Optional[str] = None

    class _TaskRequest(BaseModel):
        items: Dict[str, float]
        weights: Optional[Dict[str, float]] = None

    class _LoginRequest(BaseModel):
        username: str
        password: str

    class _TokenVerifyRequest(BaseModel):
        token: str

    class _TaskSubmitRequest(BaseModel):
        func_name: Optional[str] = Field(None, description="预定义任务名称")
        task_id: Optional[str] = Field(None, description="任务 ID，不提供则自动生成")
        func_args: Optional[Dict[str, Any]] = Field(None, description="任务参数（JSON）")
        priority: str = Field("NORMAL", description="优先级：CRITICAL/HIGH/NORMAL/LOW")
        max_retries: int = Field(0, description="最大重试次数")

    class _ComponentCallRequest(BaseModel):
        method: str = Field(..., description="组件方法名")
        args: Dict[str, Any] = Field(default_factory=dict, description="方法参数")

except Exception as _e:
    _FASTAPI_AVAILABLE = False
    _FASTAPI_ERROR = str(_e)


def _build_generation_config(data: Dict[str, Any]):
    """根据字典构造 GenerationConfig（统一给 FastAPI / SimpleHttp 使用）"""
    from 食神_创生输出 import GenerationConfig, LLMProvider, OutputFormat
    fmt = data.get("format", "text")
    provider = data.get("provider", "mock")
    fmt_map = {"text": OutputFormat.TEXT, "markdown": OutputFormat.MARKDOWN,
               "json": OutputFormat.JSON, "html": OutputFormat.HTML, "code": OutputFormat.CODE}
    provider_map = {"mock": LLMProvider.MOCK, "openai": LLMProvider.OPENAI,
                    "claude": LLMProvider.CLAUDE, "local": LLMProvider.LOCAL}
    return GenerationConfig(
        format=fmt_map.get(fmt, OutputFormat.TEXT),
        provider=provider_map.get(provider, LLMProvider.MOCK),
        model=data.get("model", ""),
        temperature=float(data.get("temperature", 0.7)),
    )


# ============ 认证依赖 =====

async def _get_current_user(request: Request) -> Dict[str, Any]:
    """FastAPI 依赖：提取并验证当前用户"""
    # 公开路由白名单
    if request.url.path in ("/", "/health", "/api/status", "/api/auth/token", "/api/auth/verify"):
        return {"user_id": "anonymous", "roles": []}

    # 限流检查
    client_ip = request.client.host if request.client else "unknown"
    user_id = "anonymous"
    retry_after = _check_rate_limit(client_ip)
    if retry_after is not None:
        raise HTTPException(status_code=429, detail=f"Rate limit exceeded. Retry after {retry_after} seconds")

    # 检查 Authorization header
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
        payload = _jwt_auth.decode(token)
        if payload:
            user_id = payload.get("user_id", "unknown")
            # 对已认证用户也限流
            retry_after = _check_rate_limit(user_id)
            if retry_after is not None:
                raise HTTPException(status_code=429, detail=f"Rate limit exceeded. Retry after {retry_after} seconds")
            return payload

    if request.url.path.startswith("/api/"):
        raise HTTPException(status_code=401, detail="Missing or invalid authorization token")

    return {"user_id": "anonymous", "roles": []}


# 预定义任务注册表
_PREDEFINED_TASKS: Dict[str, Callable] = {}


def _register_predefined_task(name: str, func: Callable) -> None:
    _PREDEFINED_TASKS[name] = func


def _get_predefined_task(name: str) -> Optional[Callable]:
    return _PREDEFINED_TASKS.get(name)


def create_app(core: Optional[Any] = None) -> Any:
    """创建 HTTP 应用。FastAPI 可用时返回 FastAPI 实例，否则返回 None。

    在 FastAPI 不可用的情况下，run_server 会自动回退到内置 SimpleHttpServer。
    """
    if core is None:
        from tengod import get_core
        core = get_core()

    if not _FASTAPI_AVAILABLE:
        return None

    fast_app = FastAPI(
        title="十神架构 API",
        description="中华文明数字永生体 - 十神协同架构的 RESTful 接口",
        version="1.3.0",
    )

    # 注册预定义任务
    if core and core.scheduler:
        def _sample_task(x: int = 1, y: int = 2) -> int:
            return x + y
        _register_predefined_task("sample_add", _sample_task)

    # -------- 健康检查 --------

    @fast_app.get("/", tags=["系统"])
    def root():
        return ApiResponse(code=0, message="十神架构服务运行中", data={
            "version": "1.3.0",
            "modules": {
                "比肩": "已就绪" if core.registry else "未启用",
                "劫财": "已就绪" if core.guard else "未启用",
                "食神": "已就绪" if core.generator else "未启用",
                "伤官": "已就绪" if core.innovator else "未启用",
                "正财": "已就绪" if core.kb else "未启用",
                "偏财": "已就绪",
                "正官": "已就绪",
                "七杀": "已就绪" if core.judge else "未启用",
                "正印": "已就绪" if core.config else "未启用",
                "偏印": "已就绪" if core.bridge else "未启用",
                "元辰": "已就绪" if getattr(core, "locator", None) else "未启用",
                "太极": "已就绪" if getattr(core, "balancer", None) else "未启用",
            },
        }).to_dict()

    @fast_app.get("/health", tags=["系统"])
    def health():
        return {"status": "ok", "timestamp": time.time()}

    @fast_app.get("/api/status", tags=["系统"])
    def api_status():
        state = core.export_state()
        return ApiResponse(code=0, message="ok", data=state).to_dict()

    # -------- 认证路由 --------

    @fast_app.post("/api/auth/token", tags=["认证"])
    def api_login(req: _LoginRequest):
        """登录获取 JWT token"""
        user = _verify_password(req.username, req.password)
        if not user:
            raise HTTPException(status_code=401, detail="Invalid username or password")

        token = _jwt_auth.encode({
            "user_id": user["user_id"],
            "roles": user["roles"],
            "username": req.username,
        })
        return ApiResponse(code=0, message="Login successful", data={
            "access_token": token,
            "token_type": "bearer",
            "expires_in": _jwt_auth.default_expiry,
        }).to_dict()

    @fast_app.post("/api/auth/verify", tags=["认证"])
    def api_verify(req: _TokenVerifyRequest):
        """验证 JWT token"""
        result = _jwt_auth.verify(req.token)
        return ApiResponse(code=0, message="ok", data=result).to_dict()

    # -------- 任务管理路由 --------

    @fast_app.post("/api/tasks/submit", tags=["任务管理"])
    def api_submit_task(req: _TaskSubmitRequest, current_user: Dict = Depends(_get_current_user)):
        """提交任务到调度器"""
        if not core.scheduler:
            raise HTTPException(status_code=503, detail="调度器未就绪")

        from 正官_法度调度.task_scheduler import TaskPriority, TaskStatus

        task_id = req.task_id or f"task-{uuid.uuid4().hex[:8]}"

        priority_map = {
            "CRITICAL": TaskPriority.CRITICAL,
            "HIGH": TaskPriority.HIGH,
            "NORMAL": TaskPriority.NORMAL,
            "LOW": TaskPriority.LOW,
        }
        priority = priority_map.get(req.priority, TaskPriority.NORMAL)

        func = None
        if req.func_name:
            func = _get_predefined_task(req.func_name)
            if not func and hasattr(core, req.func_name):
                func = getattr(core, req.func_name)
            if not func:
                raise HTTPException(status_code=400, detail=f"Unknown func_name: {req.func_name}")
        elif req.func_args:
            def _generic_task(**kwargs):
                return kwargs
            func = _generic_task
        else:
            raise HTTPException(status_code=400, detail="Either func_name or func_args must be provided")

        core.scheduler.submit(
            task_id,
            func,
            kwargs=req.func_args or {},
            priority=priority,
            max_retries=req.max_retries,
        )

        return ApiResponse(code=0, message="Task submitted", data={
            "task_id": task_id,
            "status": "pending",
        }).to_dict()

    @fast_app.get("/api/tasks", tags=["任务管理"])
    def api_list_tasks(
        page: int = 1,
        page_size: int = 20,
        status_filter: Optional[str] = None,
        current_user: Dict = Depends(_get_current_user),
    ):
        """列出所有任务（分页）"""
        if not core.scheduler:
            raise HTTPException(status_code=503, detail="调度器未就绪")

        from 正官_法度调度.task_scheduler import TaskStatus

        all_tasks = list(core.scheduler._tasks.values())

        if status_filter:
            try:
                filter_status = TaskStatus(status_filter)
                all_tasks = [t for t in all_tasks if t.status == filter_status]
            except ValueError:
                pass

        all_tasks.sort(key=lambda t: t.created_at, reverse=True)

        total = len(all_tasks)
        start = (page - 1) * page_size
        end = start + page_size
        page_tasks = all_tasks[start:end]

        return ApiResponse(code=0, message="ok", data={
            "total": total,
            "page": page,
            "page_size": page_size,
            "items": [
                {
                    "task_id": t.task_id,
                    "status": t.status.value,
                    "priority": t.priority.name,
                    "created_at": t.created_at,
                    "started_at": t.started_at,
                    "completed_at": t.completed_at,
                    "result": str(t.result) if t.result else None,
                    "error": t.error,
                    "retry_count": t.retry_count,
                    "max_retries": t.max_retries,
                }
                for t in page_tasks
            ],
        }).to_dict()

    @fast_app.get("/api/tasks/{task_id}", tags=["任务管理"])
    def api_get_task(task_id: str, current_user: Dict = Depends(_get_current_user)):
        """查询单个任务状态"""
        if not core.scheduler:
            raise HTTPException(status_code=503, detail="调度器未就绪")

        task = core.scheduler._tasks.get(task_id)
        if not task:
            raise HTTPException(status_code=404, detail=f"Task not found: {task_id}")

        return ApiResponse(code=0, message="ok", data={
            "task_id": task.task_id,
            "status": task.status.value,
            "priority": task.priority.name,
            "created_at": task.created_at,
            "started_at": task.started_at,
            "completed_at": task.completed_at,
            "result": task.result,
            "error": task.error,
            "retry_count": task.retry_count,
            "max_retries": task.max_retries,
        }).to_dict()

    @fast_app.post("/api/tasks/{task_id}/cancel", tags=["任务管理"])
    def api_cancel_task(task_id: str, current_user: Dict = Depends(_get_current_user)):
        """取消任务"""
        if not core.scheduler:
            raise HTTPException(status_code=503, detail="调度器未就绪")

        task = core.scheduler._tasks.get(task_id)
        if not task:
            raise HTTPException(status_code=404, detail=f"Task not found: {task_id}")

        from 正官_法度调度.task_scheduler import TaskStatus

        if task.status in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED):
            return ApiResponse(code=1, message=f"Task already {task.status.value}", data={
                "task_id": task_id,
                "status": task.status.value,
            }).to_dict()

        task.status = TaskStatus.CANCELLED
        task.completed_at = time.time()

        return ApiResponse(code=0, message="Task cancelled", data={
            "task_id": task_id,
            "status": "cancelled",
        }).to_dict()

    @fast_app.get("/api/tasks/stats", tags=["任务管理"])
    def api_task_stats(current_user: Dict = Depends(_get_current_user)):
        """获取调度器统计"""
        if not core.scheduler:
            raise HTTPException(status_code=503, detail="调度器未就绪")

        return ApiResponse(code=0, message="ok", data=core.scheduler.stats()).to_dict()

    # -------- 食神 · 内容生成 --------

    @fast_app.post("/api/generate", tags=["食神 · 创生输出"])
    def api_generate(req: _GenerateRequest, current_user: Dict = Depends(_get_current_user)):
        """调用食神生成内容（非流式）"""
        if not core.generator:
            raise HTTPException(status_code=503, detail="食神模块未就绪")

        session_id = req.session_id
        if not session_id:
            session_id = _session_manager.create_session(prompt=req.prompt)

        cfg = _build_generation_config(req.dict())
        text = core.generator.generate(req.prompt, cfg)

        _session_manager.add_message(session_id, "user", req.prompt)
        _session_manager.add_message(session_id, "assistant", text)

        return ApiResponse(code=0, message="ok", data={
            "content": text,
            "length": len(text),
            "format": cfg.format.value,
            "provider": cfg.provider.value,
            "session_id": session_id,
        }).to_dict()

    @fast_app.post("/api/generate/stream", tags=["食神 · 创生输出"])
    def api_generate_stream(req: _GenerateRequest, current_user: Dict = Depends(_get_current_user)):
        """流式生成内容（SSE）"""
        if not core.generator:
            raise HTTPException(status_code=503, detail="食神模块未就绪")

        session_id = req.session_id or _session_manager.create_session(prompt=req.prompt)
        cfg = _build_generation_config(req.dict())

        def _gen():
            full_content = ""
            for chunk in core.generator.generate_stream(req.prompt, cfg):
                full_content += chunk
                yield f"data: {json.dumps({'chunk': chunk}, ensure_ascii=False)}\n\n"
            yield "data: [DONE]\n\n"
            _session_manager.add_message(session_id, "user", req.prompt)
            _session_manager.add_message(session_id, "assistant", full_content)

        return StreamingResponse(_gen(), media_type="text/event-stream")

    @fast_app.get("/api/generate/sessions", tags=["食神 · 创生输出"])
    def api_list_sessions(current_user: Dict = Depends(_get_current_user)):
        """列出所有生成会话"""
        sessions = _session_manager.list_sessions()
        return ApiResponse(code=0, message="ok", data={
            "total": len(sessions),
            "items": sessions,
        }).to_dict()

    @fast_app.delete("/api/generate/sessions/{session_id}", tags=["食神 · 创生输出"])
    def api_delete_session(session_id: str, current_user: Dict = Depends(_get_current_user)):
        """清空指定会话"""
        if _session_manager.delete_session(session_id):
            return ApiResponse(code=0, message="Session deleted", data={
                "session_id": session_id,
            }).to_dict()
        raise HTTPException(status_code=404, detail=f"Session not found: {session_id}")

    # -------- 正财 · 知识库 --------

    @fast_app.post("/api/knowledge/node", tags=["正财 · 知识固化"])
    def api_add_node(req: _KnowledgeNodeRequest):
        if not core.kb:
            raise HTTPException(status_code=503, detail="正财模块未就绪")
        node = core.kb.add_node(req.name, node_type=req.node_type, properties=req.properties)
        return ApiResponse(code=0, message="ok", data={
            "id": node.id, "name": node.name, "node_type": node.node_type
        }).to_dict()

    @fast_app.get("/api/knowledge/nodes", tags=["正财 · 知识固化"])
    def api_list_nodes(node_type: Optional[str] = None):
        if not core.kb:
            raise HTTPException(status_code=503, detail="正财模块未就绪")
        nodes = core.kb.find_by_type(node_type) if node_type else list(core.kb._nodes.values())
        return ApiResponse(code=0, message="ok", data={
            "total": len(nodes),
            "items": [
                {"id": n.id, "name": n.name, "node_type": n.node_type, "properties": n.properties}
                for n in nodes
            ],
        }).to_dict()

    @fast_app.post("/api/knowledge/search", tags=["正财 · 知识固化"])
    def api_search_knowledge(req: _SearchRequest):
        """向量相似度搜索"""
        if not core.kb:
            raise HTTPException(status_code=503, detail="正财模块未就绪")
        results = core.kb.query_nearest(req.query, top_k=req.top_k, node_type=req.node_type)
        return ApiResponse(code=0, message="ok", data={
            "query": req.query,
            "total": len(results),
            "items": [
                {"id": r["id"], "name": r["name"], "node_type": r["node_type"], "score": r["score"]}
                for r in results
            ],
        }).to_dict()

    @fast_app.get("/api/knowledge/stats", tags=["正财 · 知识固化"])
    def api_kb_stats():
        if not core.kb:
            raise HTTPException(status_code=503, detail="正财模块未就绪")
        return ApiResponse(code=0, message="ok", data=core.kb.stats()).to_dict()

    # -------- 七杀 · 品质裁决 --------

    @fast_app.post("/api/evaluate", tags=["七杀 · 品质裁决"])
    def api_evaluate(req: _TaskRequest):
        if not core.judge:
            raise HTTPException(status_code=503, detail="七杀模块未就绪")
        result = core.evaluate(req.items, weights=req.weights)
        return ApiResponse(code=0, message="ok", data=result).to_dict()

    # -------- 偏财 · 参数寻优 --------

    @fast_app.post("/api/optimize/search", tags=["偏财 · 奇招演化"])
    def api_optimize_search(
        space: Dict[str, List[Any]] = Body(..., example={"lr": [0.001, 0.01, 0.1], "batch": [16, 32, 64]}),
        trials: int = 20,
    ):
        """网格/随机参数搜索"""
        try:
            from 偏财_奇招演化 import SearchOptimizer, SearchSpace
            ss = SearchSpace(space)
            def default_obj(params):
                score = 0.0
                for k, vs in space.items():
                    mid_idx = len(vs) // 2
                    val = params.get(k, vs[0])
                    if val in vs:
                        score -= abs(vs.index(val) - mid_idx)
                return score
            opt = SearchOptimizer(ss, mode="grid")
            res = opt.optimize(default_obj, n_trials=trials, maximize=True)
            return ApiResponse(code=0, message="ok", data={
                "best_params": res.best_params,
                "best_score": res.best_score,
                "iterations": res.iterations,
                "duration": res.duration,
            }).to_dict()
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    # -------- 伤官 · 创新思维 --------

    @fast_app.post("/api/innovate", tags=["伤官 · 破界创新"])
    def api_innovate(items: List[str] = Body(..., example=["AI", "知识图谱", "区块链"])):
        if not core.innovator:
            raise HTTPException(status_code=503, detail="伤官模块未就绪")
        core.innovator.combine(items)
        ideas = [
            {"title": i.title, "description": i.description, "feasibility": i.feasibility,
             "impact": i.impact, "score": round(i.score, 3)}
            for i in getattr(core.innovator, "_ideas", [])[-20:]
        ]
        return ApiResponse(code=0, message="ok", data={"total": len(ideas), "ideas": ideas}).to_dict()

    # -------- 元辰 · 项目定位 --------

    @fast_app.get("/api/locate", tags=["元辰 · 本源定位"])
    def api_locate():
        locator = getattr(core, "locator", None)
        if not locator:
            raise HTTPException(status_code=503, detail="元辰模块未就绪")
        locator.locate()
        return ApiResponse(code=0, message="ok", data=locator.summary()).to_dict()

    # -------- 太极 · 阴阳调和 --------

    @fast_app.get("/api/balance", tags=["太极 · 阴阳调和"])
    def api_balance():
        balancer = getattr(core, "balancer", None)
        if not balancer:
            raise HTTPException(status_code=503, detail="太极模块未就绪")
        return ApiResponse(code=0, message="ok", data=balancer.stats()).to_dict()

    @fast_app.post("/api/balance/{state}", tags=["太极 · 阴阳调和"])
    def api_set_balance(state: str):
        """设置状态：yin / yang / balanced"""
        balancer = getattr(core, "balancer", None)
        if not balancer:
            raise HTTPException(status_code=503, detail="太极模块未就绪")
        from 太极_阴阳调和 import YinYang as YY
        state_map = {"yin": YY.YIN, "yang": YY.YANG, "balanced": YY.BALANCED}
        if state not in state_map:
            raise HTTPException(status_code=400, detail="state must be yin/yang/balanced")
        balancer.set_state(state_map[state], reason="api request")
        return ApiResponse(code=0, message="ok", data=balancer.stats()).to_dict()

    # -------- 组件路由 --------

    @fast_app.get("/api/components", tags=["组件管理"])
    def api_list_components(current_user: Dict = Depends(_get_current_user)):
        """列出所有已注册组件"""
        if not core.registry:
            raise HTTPException(status_code=503, detail="组件注册表未就绪")
        components = core.registry.list_all() if hasattr(core.registry, "list_all") else []
        return ApiResponse(code=0, message="ok", data={
            "total": len(components),
            "items": components,
        }).to_dict()

    @fast_app.post("/api/components/{name}/call", tags=["组件管理"])
    def api_call_component(
        name: str,
        req: _ComponentCallRequest,
        current_user: Dict = Depends(_get_current_user),
    ):
        """调用指定组件的方法"""
        if not core.registry:
            raise HTTPException(status_code=503, detail="组件注册表未就绪")

        component = None
        if hasattr(core.registry, "get"):
            component = core.registry.get(name)
        elif hasattr(core.registry, name):
            component = getattr(core.registry, name)

        if not component:
            raise HTTPException(status_code=404, detail=f"Component not found: {name}")

        if not hasattr(component, req.method):
            raise HTTPException(status_code=400, detail=f"Method not found: {req.method}")

        try:
            method = getattr(component, req.method)
            result = method(**req.args)
            return ApiResponse(code=0, message="ok", data={"result": result}).to_dict()
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    return fast_app


# 默认 app（供 uvicorn 直接使用，FastAPI 不可用时为 None）
if _FASTAPI_AVAILABLE:
    try:
        from tengod import get_core
        app = create_app(get_core())
    except Exception:
        app = None


# -------- 降级：简易内置 HTTP Server（零依赖） --------

class SimpleHttpServer:
    """无 FastAPI 时的降级方案，基于 http.server"""

    def __init__(self, core: Any, host: str = "0.0.0.0", port: int = 8000):
        self.core = core
        self.host = host
        self.port = port

    def _dispatch(self, method: str, path: str, body: str) -> (int, Dict[str, Any]):
        """根据路径分发到对应处理逻辑"""
        try:
            data = json.loads(body) if body else {}
        except json.JSONDecodeError:
            data = {}

        # 健康检查
        if path in ("/", "/health") and method == "GET":
            return 200, {"status": "ok", "version": "1.3.0", "mode": "simple-http"}

        # 状态总览
        if path == "/api/status" and method == "GET":
            return 200, ApiResponse(code=0, message="ok", data=self.core.export_state()).to_dict()

        # 食神生成
        if path == "/api/generate" and method == "POST":
            from 食神_创生输出 import GenerationConfig, LLMProvider, OutputFormat
            cfg = GenerationConfig(
                format=OutputFormat(data.get("format", "text")),
                provider=LLMProvider(data.get("provider", "mock")),
                model=data.get("model", ""),
                temperature=float(data.get("temperature", 0.7)),
            )
            text = self.core.generator.generate(data.get("prompt", ""), cfg)
            return 200, ApiResponse(code=0, message="ok", data={"content": text, "length": len(text)}).to_dict()

        # 正财搜索
        if path == "/api/knowledge/search" and method == "POST":
            results = self.core.kb.query_nearest(
                data.get("query", ""),
                top_k=int(data.get("top_k", 5)),
                node_type=data.get("node_type"),
            )
            items = [{"id": r["id"], "name": r["name"], "node_type": r["node_type"], "score": r["score"]} for r in results]
            return 200, ApiResponse(code=0, message="ok", data={"total": len(items), "items": items}).to_dict()

        # 正财添加节点
        if path == "/api/knowledge/node" and method == "POST":
            node = self.core.kb.add_node(
                data.get("name", ""),
                node_type=data.get("node_type", "default"),
                properties=data.get("properties", {}),
            )
            return 200, ApiResponse(code=0, message="ok", data={"id": node.id, "name": node.name}).to_dict()

        # 正财节点列表
        if path == "/api/knowledge/nodes" and method == "GET":
            all_nodes = list(self.core.kb._nodes.values())
            items = [{"id": n.id, "name": n.name, "node_type": n.node_type} for n in all_nodes]
            return 200, ApiResponse(code=0, message="ok", data={"total": len(items), "items": items}).to_dict()

        # 七杀评估
        if path == "/api/evaluate" and method == "POST":
            result = self.core.evaluate(data.get("items", {}), weights=data.get("weights"))
            return 200, ApiResponse(code=0, message="ok", data=result).to_dict()

        # 元辰
        if path == "/api/locate" and method == "GET":
            locator = getattr(self.core, "locator", None)
            if locator:
                locator.locate()
                return 200, ApiResponse(code=0, message="ok", data=locator.summary()).to_dict()
            return 503, {"code": 503, "message": "元辰模块未就绪"}

        # 太极
        if path == "/api/balance" and method == "GET":
            balancer = getattr(self.core, "balancer", None)
            if balancer:
                return 200, ApiResponse(code=0, message="ok", data=balancer.stats()).to_dict()
            return 503, {"code": 503, "message": "太极模块未就绪"}

        # -------- 认证路由 --------
        if path == "/api/auth/token" and method == "POST":
            username = data.get("username", "")
            password = data.get("password", "")
            user = _verify_password(username, password)
            if not user:
                return 401, {"code": 401, "message": "Invalid username or password"}
            token = _jwt_auth.encode({
                "user_id": user["user_id"],
                "roles": user["roles"],
                "username": username,
            })
            return 200, ApiResponse(code=0, message="Login successful", data={
                "access_token": token,
                "token_type": "bearer",
                "expires_in": _jwt_auth.default_expiry,
            }).to_dict()

        if path == "/api/auth/verify" and method == "POST":
            token = data.get("token", "")
            result = _jwt_auth.verify(token)
            return 200, ApiResponse(code=0, message="ok", data=result).to_dict()

        # -------- 任务管理路由 --------
        if path == "/api/tasks/submit" and method == "POST":
            if not self.core.scheduler:
                return 503, {"code": 503, "message": "调度器未就绪"}
            task_id = data.get("task_id") or f"task-{uuid.uuid4().hex[:8]}"
            func_name = data.get("func_name")
            func_args = data.get("func_args", {})
            priority_str = data.get("priority", "NORMAL")
            from 正官_法度调度.task_scheduler import TaskPriority
            priority_map = {
                "CRITICAL": TaskPriority.CRITICAL,
                "HIGH": TaskPriority.HIGH,
                "NORMAL": TaskPriority.NORMAL,
                "LOW": TaskPriority.LOW,
            }
            priority = priority_map.get(priority_str, TaskPriority.NORMAL)
            func = None
            if func_name:
                func = _get_predefined_task(func_name)
                if not func and hasattr(self.core, func_name):
                    func = getattr(self.core, func_name)
            if not func:
                return 400, {"code": 400, "message": f"Unknown func_name: {func_name}"}
            self.core.scheduler.submit(task_id, func, kwargs=func_args, priority=priority)
            return 200, ApiResponse(code=0, message="Task submitted", data={
                "task_id": task_id,
                "status": "pending",
            }).to_dict()

        if path == "/api/tasks" and method == "GET":
            if not self.core.scheduler:
                return 503, {"code": 503, "message": "调度器未就绪"}
            all_tasks = list(self.core.scheduler._tasks.values())
            all_tasks.sort(key=lambda t: t.created_at, reverse=True)
            return 200, ApiResponse(code=0, message="ok", data={
                "total": len(all_tasks),
                "items": [
                    {
                        "task_id": t.task_id,
                        "status": t.status.value,
                        "priority": t.priority.name,
                        "created_at": t.created_at,
                    }
                    for t in all_tasks[:20]
                ],
            }).to_dict()

        if path.startswith("/api/tasks/") and path.endswith("/cancel") and method == "POST":
            if not self.core.scheduler:
                return 503, {"code": 503, "message": "调度器未就绪"}
            task_id = path.split("/")[3]
            task = self.core.scheduler._tasks.get(task_id)
            if not task:
                return 404, {"code": 404, "message": f"Task not found: {task_id}"}
            from 正官_法度调度.task_scheduler import TaskStatus
            task.status = TaskStatus.CANCELLED
            task.completed_at = time.time()
            return 200, ApiResponse(code=0, message="Task cancelled", data={
                "task_id": task_id,
                "status": "cancelled",
            }).to_dict()

        if path == "/api/tasks/stats" and method == "GET":
            if not self.core.scheduler:
                return 503, {"code": 503, "message": "调度器未就绪"}
            return 200, ApiResponse(code=0, message="ok", data=self.core.scheduler.stats()).to_dict()

        # 匹配 /api/tasks/{task_id}
        if path.startswith("/api/tasks/") and method == "GET":
            task_id = path.split("/api/tasks/")[1]
            if not self.core.scheduler:
                return 503, {"code": 503, "message": "调度器未就绪"}
            task = self.core.scheduler._tasks.get(task_id)
            if not task:
                return 404, {"code": 404, "message": f"Task not found: {task_id}"}
            return 200, ApiResponse(code=0, message="ok", data={
                "task_id": task.task_id,
                "status": task.status.value,
                "priority": task.priority.name,
                "created_at": task.created_at,
                "result": task.result,
                "error": task.error,
            }).to_dict()

        # -------- 会话路由 --------
        if path == "/api/generate/sessions" and method == "GET":
            sessions = _session_manager.list_sessions()
            return 200, ApiResponse(code=0, message="ok", data={
                "total": len(sessions),
                "items": sessions,
            }).to_dict()

        if path.startswith("/api/generate/sessions/") and method == "DELETE":
            session_id = path.split("/api/generate/sessions/")[1]
            if _session_manager.delete_session(session_id):
                return 200, ApiResponse(code=0, message="Session deleted", data={
                    "session_id": session_id,
                }).to_dict()
            return 404, {"code": 404, "message": f"Session not found: {session_id}"}

        # -------- 组件路由 --------
        if path == "/api/components" and method == "GET":
            if not self.core.registry:
                return 503, {"code": 503, "message": "组件注册表未就绪"}
            components = self.core.registry.list_all() if hasattr(self.core.registry, "list_all") else []
            return 200, ApiResponse(code=0, message="ok", data={
                "total": len(components),
                "items": components,
            }).to_dict()

        if path.startswith("/api/components/") and "/call" in path and method == "POST":
            name = path.split("/api/components/")[1].split("/call")[0]
            if not self.core.registry:
                return 503, {"code": 503, "message": "组件注册表未就绪"}
            component = None
            if hasattr(self.core.registry, "get"):
                component = self.core.registry.get(name)
            elif hasattr(self.core.registry, name):
                component = getattr(self.core.registry, name)
            if not component:
                return 404, {"code": 404, "message": f"Component not found: {name}"}
            method_name = data.get("method", "")
            args = data.get("args", {})
            if not hasattr(component, method_name):
                return 400, {"code": 400, "message": f"Method not found: {method_name}"}
            try:
                result = getattr(component, method_name)(**args)
                return 200, ApiResponse(code=0, message="ok", data={"result": result}).to_dict()
            except Exception as e:
                return 500, {"code": 500, "message": str(e)}

        return 404, {"code": 404, "message": f"Route not found: {method} {path}"}

    def serve_forever(self) -> None:
        """启动内置 HTTP 服务器"""
        from http.server import BaseHTTPRequestHandler, HTTPServer
        server_self = self

        class Handler(BaseHTTPRequestHandler):
            def _send_json(self, status: int, payload: Dict[str, Any]) -> None:
                body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
                self.send_response(status)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def do_GET(self):
                status, payload = server_self._dispatch("GET", self.path, "")
                self._send_json(status, payload)

            def do_POST(self):
                length = int(self.headers.get("Content-Length", 0))
                body = self.rfile.read(length).decode("utf-8") if length else ""
                status, payload = server_self._dispatch("POST", self.path, body)
                self._send_json(status, payload)

            def log_message(self, fmt, *args):
                print(f"[十神-API] {self.log_date_time_string()} {args[0]}")

        httpd = HTTPServer((self.host, self.port), Handler)
        print(f"✅ 十神架构 HTTP API 服务已启动（内置简易模式）")
        print(f"   访问地址: http://{self.host}:{self.port}")
        print(f"   健康检查: http://{self.host}:{self.port}/health")
        print(f"   状态总览: http://{self.host}:{self.port}/api/status")
        print(f"\n   提示: pip install fastapi uvicorn 可升级为生产模式（SSE/文档/校验）")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n正在关闭服务...")
            httpd.server_close()


# -------- 统一入口：run_server --------

def run_server(app_or_core: Any = None, host: str = "0.0.0.0", port: int = 8000) -> None:
    """启动 HTTP 服务。

    - 若传入 FastAPI app 或 fastapi 可用：用 uvicorn 启动
    - 否则用内置简易 HTTP 服务
    """
    # 优先 FastAPI 模式
    if _FASTAPI_AVAILABLE:
        try:
            import uvicorn
            if app_or_core is None:
                from tengod import get_core
                app_to_run = create_app(get_core())
            elif hasattr(app_or_core, "openapi"):
                app_to_run = app_or_core
            else:
                app_to_run = create_app(app_or_core)
            uvicorn.run(app_to_run, host=host, port=port, log_level="info")
            return
        except ImportError:
            print("[提示] fastapi 已检测到但 uvicorn 未安装，切换至内置 HTTP 服务...")

    # 内置降级模式
    if app_or_core is None or not hasattr(app_or_core, "export_state"):
        from tengod import get_core
        core = get_core()
    else:
        core = app_or_core
    SimpleHttpServer(core, host=host, port=port).serve_forever()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="十神架构 HTTP API 服务")
    parser.add_argument("--host", default="0.0.0.0", help="绑定地址")
    parser.add_argument("--port", type=int, default=8000, help="监听端口")
    args = parser.parse_args()

    run_server(host=args.host, port=args.port)


__all__ = ["create_app", "run_server", "SimpleHttpServer", "ApiResponse", "app"]
__version__ = "1.3.0"
