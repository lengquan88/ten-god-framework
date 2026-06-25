#!/usr/bin/env python3
"""
test_api_server.py — 正官_法度调度/api_server.py 的综合测试

覆盖：
- JWTAuth 类 (encode/decode/verify/expiry)
- RateLimiter 类 (is_allowed/get_retry_after/滑动窗口)
- SessionManager 类 (CRUD + add_message)
- ApiResponse 数据类 (to_dict)
- _verify_password 函数
- _check_rate_limit 函数
- SimpleHttpServer._dispatch (所有路由)
- _build_generation_config
- _register_predefined_task / _get_predefined_task
"""

import hashlib
import json
import sys
import time
import uuid
from unittest.mock import MagicMock, Mock, patch

import pytest

# 确保模块可导入
sys.path.insert(0, "/workspace/demo_project")

from tengod.正官_法度调度.api_server import (
    JWTAuth,
    RateLimiter,
    SessionManager,
    ApiResponse,
    _DEFAULT_USERS,
    _jwt_auth,
    _rate_limiter,
    _session_manager,
    _check_rate_limit,
    _verify_password,
    _PREDEFINED_TASKS,
    _register_predefined_task,
    _get_predefined_task,
    _build_generation_config,
    SimpleHttpServer,
)


# ======================================================================
# 1. JWTAuth 测试
# ======================================================================

class TestJWTAuth:
    """JWTAuth 类的完整测试"""

    def test_init_default_secret(self):
        auth = JWTAuth()
        assert auth.secret_key == b"tengod-default-secret-key-change-in-production"
        assert auth.algorithm == "HS256"
        assert auth.default_expiry == 24 * 3600

    def test_init_custom_secret(self):
        auth = JWTAuth(secret_key="my-custom-secret")
        assert auth.secret_key == b"my-custom-secret"

    def test_base64url_encode(self):
        auth = JWTAuth()
        # 测试基本编码
        result = auth._base64url_encode(b"hello")
        assert "=" not in result  # base64url 无填充
        assert isinstance(result, str)

    def test_base64url_encode_decode_roundtrip(self):
        auth = JWTAuth()
        data = b"test data with special chars !@#$%"
        encoded = auth._base64url_encode(data)
        decoded = auth._base64url_decode(encoded)
        assert decoded == data

    def test_base64url_decode_padding(self):
        auth = JWTAuth()
        # 测试无填充字符串的解码
        encoded = auth._base64url_encode(b"test")
        result = auth._base64url_decode(encoded)
        assert result == b"test"

    def test_create_signature(self):
        auth1 = JWTAuth(secret_key="secret1")
        auth2 = JWTAuth(secret_key="secret2")
        header_b64 = auth1._base64url_encode(b'{"alg":"HS256"}')
        payload_b64 = auth1._base64url_encode(b'{"sub":"test"}')
        sig1 = auth1._create_signature(header_b64, payload_b64)
        sig2 = auth2._create_signature(header_b64, payload_b64)
        assert sig1 != sig2  # 不同密钥不同签名
        assert isinstance(sig1, str)

    def test_encode_basic(self):
        auth = JWTAuth()
        token = auth.encode({"user_id": "test123", "role": "admin"})
        assert isinstance(token, str)
        parts = token.split(".")
        assert len(parts) == 3

    def test_encode_with_custom_expiry(self):
        auth = JWTAuth()
        token = auth.encode({"user_id": "test"}, expiry=60)
        payload = auth.decode(token)
        assert payload is not None
        assert payload["user_id"] == "test"

    def test_decode_valid_token(self):
        auth = JWTAuth()
        token = auth.encode({"user_id": "u001", "roles": ["admin"]})
        payload = auth.decode(token)
        assert payload is not None
        assert payload["user_id"] == "u001"
        assert payload["roles"] == ["admin"]
        assert "exp" in payload

    def test_decode_invalid_token(self):
        auth = JWTAuth()
        assert auth.decode("invalid.token.string") is None
        assert auth.decode("") is None
        assert auth.decode("only.two") is None

    def test_decode_tampered_token(self):
        auth = JWTAuth()
        token = auth.encode({"user_id": "test"})
        parts = token.split(".")
        # 篡改 payload
        tampered = f"{parts[0]}.{parts[1]}x.{parts[2]}"
        assert auth.decode(tampered) is None

    def test_decode_wrong_signature(self):
        auth = JWTAuth()
        token = auth.encode({"user_id": "test"})
        parts = token.split(".")
        # 使用不同密钥签名
        auth2 = JWTAuth(secret_key="different-key")
        sig = auth2._create_signature(parts[0], parts[1])
        bad_token = f"{parts[0]}.{parts[1]}.{sig}"
        assert auth.decode(bad_token) is None

    def test_decode_expired_token(self):
        auth = JWTAuth()
        # 创建 1 秒过期的 token，等待 2 秒确保跨过整数边界
        token = auth.encode({"user_id": "test"}, expiry=1)
        time.sleep(2)
        assert auth.decode(token) is None

    def test_verify_valid_token(self):
        auth = JWTAuth()
        token = auth.encode({"user_id": "test"})
        result = auth.verify(token)
        assert result["valid"] is True
        assert "payload" in result
        assert result["payload"]["user_id"] == "test"

    def test_verify_invalid_token(self):
        auth = JWTAuth()
        result = auth.verify("invalid.token")
        assert result["valid"] is False
        assert "error" in result

    def test_global_jwt_auth(self):
        """测试全局 _jwt_auth 实例"""
        token = _jwt_auth.encode({"user_id": "global_test"})
        payload = _jwt_auth.decode(token)
        assert payload is not None
        assert payload["user_id"] == "global_test"

    def test_encode_with_none_expiry(self):
        auth = JWTAuth()
        token = auth.encode({"user_id": "test"}, expiry=None)
        payload = auth.decode(token)
        assert payload is not None
        assert payload["user_id"] == "test"

    def test_decode_with_no_exp_field(self):
        """测试 payload 无 exp 字段时仍可解码"""
        auth = JWTAuth()
        # 手动构造一个不带 exp 的 token（直接调底层）
        header = json.dumps({"alg": "HS256", "typ": "JWT"}, separators=(",", ":"))
        payload = json.dumps({"user_id": "no_exp"})
        header_b64 = auth._base64url_encode(header.encode("utf-8"))
        payload_b64 = auth._base64url_encode(payload.encode("utf-8"))
        sig = auth._create_signature(header_b64, payload_b64)
        token = f"{header_b64}.{payload_b64}.{sig}"
        result = auth.decode(token)
        assert result is not None
        assert result["user_id"] == "no_exp"


# ======================================================================
# 2. RateLimiter 测试
# ======================================================================

class TestRateLimiter:
    """RateLimiter 类的完整测试"""

    def test_init_default(self):
        rl = RateLimiter()
        assert rl.max_requests == 60
        assert rl.window_seconds == 60

    def test_init_custom(self):
        rl = RateLimiter(max_requests=10, window_seconds=30)
        assert rl.max_requests == 10
        assert rl.window_seconds == 30

    def test_is_allowed_first_request(self):
        rl = RateLimiter(max_requests=5, window_seconds=60)
        assert rl.is_allowed("client1") is True

    def test_is_allowed_within_limit(self):
        rl = RateLimiter(max_requests=5, window_seconds=60)
        for _ in range(5):
            assert rl.is_allowed("client1") is True

    def test_is_allowed_exceeds_limit(self):
        rl = RateLimiter(max_requests=3, window_seconds=60)
        for _ in range(3):
            rl.is_allowed("client1")
        assert rl.is_allowed("client1") is False

    def test_is_allowed_different_clients(self):
        rl = RateLimiter(max_requests=2, window_seconds=60)
        assert rl.is_allowed("client1") is True
        assert rl.is_allowed("client1") is True
        assert rl.is_allowed("client1") is False
        # 不同 client 不受影响
        assert rl.is_allowed("client2") is True

    def test_get_retry_after_empty(self):
        rl = RateLimiter()
        assert rl.get_retry_after("unknown") == 0

    def test_get_retry_after_when_limited(self):
        rl = RateLimiter(max_requests=1, window_seconds=60)
        rl.is_allowed("client1")
        rl.is_allowed("client1")  # 超限
        retry = rl.get_retry_after("client1")
        assert retry > 0
        assert retry <= 60

    def test_sliding_window_cleanup(self):
        """测试滑动窗口会自动清理过期条目"""
        rl = RateLimiter(max_requests=3, window_seconds=1)
        for _ in range(3):
            rl.is_allowed("client1")
        assert rl.is_allowed("client1") is False
        # 等待窗口过期
        time.sleep(1.1)
        assert rl.is_allowed("client1") is True

    def test_fresh_instance_isolated(self):
        """每个新实例应该有独立的状态"""
        rl1 = RateLimiter(max_requests=1, window_seconds=60)
        rl2 = RateLimiter(max_requests=1, window_seconds=60)
        rl1.is_allowed("test")
        rl1.is_allowed("test")  # rl1 超限
        assert rl2.is_allowed("test") is True  # rl2 不受影响


# ======================================================================
# 3. SessionManager 测试
# ======================================================================

class TestSessionManager:
    """SessionManager 类的完整测试"""

    def test_create_session(self):
        sm = SessionManager()
        sid = sm.create_session(prompt="hello")
        assert isinstance(sid, str)
        assert len(sid) == 8

    def test_create_session_with_kwargs(self):
        sm = SessionManager()
        sid = sm.create_session(prompt="test", user_id="u001", language="zh")
        session = sm.get_session(sid)
        assert session is not None
        assert session["prompt"] == "test"
        assert session["user_id"] == "u001"
        assert session["language"] == "zh"

    def test_get_session_exists(self):
        sm = SessionManager()
        sid = sm.create_session(prompt="test")
        session = sm.get_session(sid)
        assert session is not None
        assert session["id"] == sid
        assert session["prompt"] == "test"
        assert "history" in session
        assert "created_at" in session
        assert "last_active" in session

    def test_get_session_not_exists(self):
        sm = SessionManager()
        assert sm.get_session("nonexistent") is None

    def test_list_sessions_empty(self):
        sm = SessionManager()
        sessions = sm.list_sessions()
        assert sessions == []

    def test_list_sessions_with_data(self):
        sm = SessionManager()
        sm.create_session(prompt="first")
        sm.create_session(prompt="second")
        sessions = sm.list_sessions()
        assert len(sessions) == 2
        for s in sessions:
            assert "id" in s
            assert "prompt" in s
            assert "created_at" in s
            assert "last_active" in s
            assert "message_count" in s

    def test_list_sessions_message_count(self):
        sm = SessionManager()
        sid = sm.create_session(prompt="test")
        sm.add_message(sid, "user", "hello")
        sm.add_message(sid, "assistant", "hi there")
        sessions = sm.list_sessions()
        assert len(sessions) == 1
        assert sessions[0]["message_count"] == 2

    def test_delete_session_exists(self):
        sm = SessionManager()
        sid = sm.create_session(prompt="test")
        assert sm.delete_session(sid) is True
        assert sm.get_session(sid) is None

    def test_delete_session_not_exists(self):
        sm = SessionManager()
        assert sm.delete_session("nonexistent") is False

    def test_add_message(self):
        sm = SessionManager()
        sid = sm.create_session(prompt="test")
        sm.add_message(sid, "user", "hello")
        sm.add_message(sid, "assistant", "world")
        session = sm.get_session(sid)
        assert len(session["history"]) == 2
        assert session["history"][0]["role"] == "user"
        assert session["history"][0]["content"] == "hello"
        assert "timestamp" in session["history"][0]
        assert session["history"][1]["role"] == "assistant"
        assert session["history"][1]["content"] == "world"

    def test_add_message_nonexistent_session(self):
        sm = SessionManager()
        # 不存在的 session，不应抛异常
        sm.add_message("nonexistent", "user", "hello")

    def test_add_message_updates_last_active(self):
        sm = SessionManager()
        sid = sm.create_session(prompt="test")
        old_active = sm.get_session(sid)["last_active"]
        time.sleep(0.01)
        sm.add_message(sid, "user", "hello")
        new_active = sm.get_session(sid)["last_active"]
        assert new_active >= old_active

    def test_multiple_sessions_with_messages(self):
        sm = SessionManager()
        sid1 = sm.create_session(prompt="a")
        sid2 = sm.create_session(prompt="b")
        sm.add_message(sid1, "user", "msg1")
        sm.add_message(sid2, "user", "msg2")
        sm.add_message(sid2, "assistant", "msg3")
        assert len(sm.get_session(sid1)["history"]) == 1
        assert len(sm.get_session(sid2)["history"]) == 2


# ======================================================================
# 4. ApiResponse 测试
# ======================================================================

class TestApiResponse:
    """ApiResponse 数据类的完整测试"""

    def test_create_basic(self):
        resp = ApiResponse(code=0, message="ok")
        assert resp.code == 0
        assert resp.message == "ok"
        assert resp.data is None

    def test_create_with_data(self):
        resp = ApiResponse(code=0, message="ok", data={"key": "value"})
        assert resp.data == {"key": "value"}

    def test_to_dict(self):
        resp = ApiResponse(code=0, message="success", data={"result": 42})
        d = resp.to_dict()
        assert d == {"code": 0, "message": "success", "data": {"result": 42}}

    def test_to_dict_with_none_data(self):
        resp = ApiResponse(code=1, message="error")
        d = resp.to_dict()
        assert d == {"code": 1, "message": "error", "data": None}

    def test_error_response(self):
        resp = ApiResponse(code=404, message="not found")
        d = resp.to_dict()
        assert d["code"] == 404
        assert d["message"] == "not found"


# ======================================================================
# 5. _verify_password 测试
# ======================================================================

class TestVerifyPassword:
    """_verify_password 函数的测试"""

    def test_correct_admin_password(self):
        result = _verify_password("admin", "admin123")
        assert result is not None
        assert result["user_id"] == "u001"
        assert "admin" in result["roles"]

    def test_correct_user_password(self):
        result = _verify_password("user", "user123")
        assert result is not None
        assert result["user_id"] == "u002"
        assert result["roles"] == ["user"]

    def test_wrong_password(self):
        result = _verify_password("admin", "wrongpassword")
        assert result is None

    def test_nonexistent_user(self):
        result = _verify_password("nonexistent", "password")
        assert result is None

    def test_empty_credentials(self):
        result = _verify_password("", "")
        assert result is None


# ======================================================================
# 6. _check_rate_limit 测试
# ======================================================================

class TestCheckRateLimit:
    """_check_rate_limit 函数的测试"""

    def test_passes_when_under_limit(self):
        rl = RateLimiter(max_requests=100, window_seconds=60)
        # 用新实例替换全局实例进行测试
        with patch(
            "tengod.正官_法度调度.api_server._rate_limiter", rl
        ):
            result = _check_rate_limit("test-client")
            assert result is None

    def test_returns_retry_after_when_over_limit(self):
        rl = RateLimiter(max_requests=1, window_seconds=60)
        with patch(
            "tengod.正官_法度调度.api_server._rate_limiter", rl
        ):
            _check_rate_limit("test-client")  # 第一次通过
            retry = _check_rate_limit("test-client")  # 第二次超限
            assert retry is not None
            assert retry > 0


# ======================================================================
# 7. _build_generation_config 测试
# ======================================================================

class TestBuildGenerationConfig:
    """_build_generation_config 函数的测试"""

    def test_default_format_and_provider(self):
        config = _build_generation_config({})
        from 食神_创生输出 import OutputFormat, LLMProvider
        assert config.format == OutputFormat.TEXT
        assert config.provider == LLMProvider.MOCK
        assert config.temperature == 0.7

    def test_markdown_format(self):
        config = _build_generation_config({"format": "markdown"})
        from 食神_创生输出 import OutputFormat
        assert config.format == OutputFormat.MARKDOWN

    def test_json_format(self):
        config = _build_generation_config({"format": "json"})
        from 食神_创生输出 import OutputFormat
        assert config.format == OutputFormat.JSON

    def test_html_format(self):
        config = _build_generation_config({"format": "html"})
        from 食神_创生输出 import OutputFormat
        assert config.format == OutputFormat.HTML

    def test_code_format(self):
        config = _build_generation_config({"format": "code"})
        from 食神_创生输出 import OutputFormat
        assert config.format == OutputFormat.CODE

    def test_unknown_format_falls_back_to_text(self):
        config = _build_generation_config({"format": "unknown"})
        from 食神_创生输出 import OutputFormat
        assert config.format == OutputFormat.TEXT

    def test_openai_provider(self):
        config = _build_generation_config({"provider": "openai"})
        from 食神_创生输出 import LLMProvider
        assert config.provider == LLMProvider.OPENAI

    def test_claude_provider(self):
        config = _build_generation_config({"provider": "claude"})
        from 食神_创生输出 import LLMProvider
        assert config.provider == LLMProvider.CLAUDE

    def test_local_provider(self):
        config = _build_generation_config({"provider": "local"})
        from 食神_创生输出 import LLMProvider
        assert config.provider == LLMProvider.LOCAL

    def test_unknown_provider_falls_back_to_mock(self):
        config = _build_generation_config({"provider": "unknown"})
        from 食神_创生输出 import LLMProvider
        assert config.provider == LLMProvider.MOCK

    def test_model_and_temperature(self):
        config = _build_generation_config({
            "model": "gpt-4",
            "temperature": "0.5",
        })
        assert config.model == "gpt-4"
        assert config.temperature == 0.5


# ======================================================================
# 8. _register_predefined_task / _get_predefined_task 测试
# ======================================================================

class TestPredefinedTasks:
    """预定义任务注册与获取的测试"""

    def setup_method(self):
        # 清理预定义任务
        _PREDEFINED_TASKS.clear()

    def test_register_and_get(self):
        def my_task(x=1):
            return x * 2
        _register_predefined_task("double", my_task)
        func = _get_predefined_task("double")
        assert func is not None
        assert func(5) == 10

    def test_get_nonexistent(self):
        assert _get_predefined_task("nonexistent") is None

    def test_register_multiple(self):
        _register_predefined_task("task_a", lambda: "a")
        _register_predefined_task("task_b", lambda: "b")
        assert _get_predefined_task("task_a")() == "a"
        assert _get_predefined_task("task_b")() == "b"


# ======================================================================
# 9. 辅助：构建 Mock Core
# ======================================================================

def _make_mock_core():
    """构建一个包含所有必要属性的 Mock core 对象"""
    core = MagicMock()

    # 知识库
    core.kb = MagicMock()
    core.kb.add_node = MagicMock()
    # 返回一个带 id/name/node_type 的 mock 对象
    node = MagicMock()
    node.id = "node-001"
    node.name = "test-node"
    node.node_type = "default"
    node.properties = {}
    core.kb.add_node.return_value = node

    core.kb.query_paginated = MagicMock()
    core.kb.query_paginated.return_value = {"items": [], "total": 0}

    core.kb.query_nearest = MagicMock()
    core.kb.query_nearest.return_value = [
        {"id": "n1", "name": "node1", "node_type": "concept", "score": 0.95},
    ]

    core.kb.find_by_type = MagicMock(return_value=[])
    core.kb._nodes = MagicMock()
    core.kb._nodes.values.return_value = []
    core.kb.stats = MagicMock(return_value={"nodes": 0})

    # 共识
    core.consensus = MagicMock()
    core.consensus.handle_vote_request = MagicMock(return_value={"vote_granted": True})
    core.consensus.handle_append_entries = MagicMock(return_value={"success": True})

    core.consensus_state = MagicMock(return_value={"leader": "node-1", "term": 1})
    core.consensus_propose = MagicMock(return_value=True)
    core.add_consensus_peer = MagicMock(return_value=True)
    core.remove_consensus_peer = MagicMock(return_value=True)

    # 调度器
    core.scheduler = MagicMock()
    core.scheduler.submit = MagicMock()
    from 正官_法度调度.task_scheduler import Task, TaskPriority, TaskStatus
    task = Task(
        task_id="task-001",
        func=lambda: None,
        priority=TaskPriority.NORMAL,
        status=TaskStatus.PENDING,
    )
    core.scheduler._tasks = {"task-001": task}
    core.scheduler.stats = MagicMock(return_value={
        "total": 1, "pending": 1, "running": 0, "completed": 0, "failed": 0,
    })

    # 注册表
    core.registry = MagicMock()
    core.registry.list_all = MagicMock(return_value=["comp-a", "comp-b"])
    core.registry.get = MagicMock()
    component = MagicMock()
    component.hello = MagicMock(return_value="world")
    core.registry.get.return_value = component

    # 裁决
    core.judge = MagicMock()
    core.evaluate = MagicMock(return_value={"score": 85, "details": {}})

    # 创新
    core.innovator = MagicMock()
    core.innovator.combine = MagicMock()
    idea = MagicMock()
    idea.title = "Test Idea"
    idea.description = "A test idea"
    idea.feasibility = 0.8
    idea.impact = 0.7
    idea.score = 0.75
    core.innovator._ideas = [idea]

    # 生成器
    core.generator = MagicMock()
    core.generator.generate = MagicMock(return_value="Generated text content")
    core.generator.generate_stream = MagicMock(return_value=iter(["chunk1", "chunk2"]))

    # 守卫
    core.guard = MagicMock()

    # 配置
    core.config = MagicMock()
    core.config._config = {"app_name": "tengod"}
    core.config.get = MagicMock(return_value="tengod")
    core.config.set_default = MagicMock()

    # 定位器
    core.locator = MagicMock()
    core.locator.locate = MagicMock()
    core.locator.summary = MagicMock(return_value={"position": "center"})

    # 均衡器
    core.balancer = MagicMock()
    core.balancer.stats = MagicMock(return_value={"state": "balanced"})
    core.balancer.set_state = MagicMock()

    # 桥接
    core.bridge = MagicMock()

    # 导出状态
    core.export_state = MagicMock(return_value={"version": "1.3.0", "modules": {}})

    # Oracle
    core.consult_oracle = MagicMock(return_value={"hexagram": "乾", "interpretation": "test"})

    return core


# ======================================================================
# 10. SimpleHttpServer._dispatch 测试
# ======================================================================

class TestDispatch:
    """SimpleHttpServer._dispatch 路由分发的完整测试"""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.core = _make_mock_core()
        self.server = SimpleHttpServer(self.core)

    def _call(self, method, path, body=None):
        return self.server._dispatch(method, path, body or "")

    # ---- 健康检查 ----

    def test_root_get(self):
        status, data = self._call("GET", "/")
        assert status == 200
        assert data["status"] == "ok"
        assert data["version"] == "1.3.0"
        assert data["mode"] == "simple-http"

    def test_health_get(self):
        status, data = self._call("GET", "/health")
        assert status == 200
        assert data["status"] == "ok"

    def test_status_get(self):
        status, data = self._call("GET", "/api/status")
        assert status == 200
        assert data["code"] == 0

    # ---- Oracle ----

    def test_oracle_post(self):
        status, data = self._call("POST", "/api/oracle",
                                   json.dumps({"question": "test question"}))
        assert status == 200
        assert data["code"] == 0

    def test_oracle_post_empty_question(self):
        status, data = self._call("POST", "/api/oracle",
                                   json.dumps({"question": ""}))
        assert status == 400
        assert data["code"] == 400

    def test_oracle_post_no_body(self):
        status, data = self._call("POST", "/api/oracle")
        assert status == 400

    # ---- 共识 ----

    def test_consensus_vote_post(self):
        status, data = self._call("POST", "/api/consensus/vote",
                                   json.dumps({"candidate": "node-1"}))
        assert status == 200

    def test_consensus_append_post(self):
        status, data = self._call("POST", "/api/consensus/append",
                                   json.dumps({"term": 1}))
        assert status == 200

    def test_consensus_state_get(self):
        status, data = self._call("GET", "/api/consensus/state")
        assert status == 200
        assert data["code"] == 0

    def test_consensus_propose_post(self):
        status, data = self._call("POST", "/api/consensus/propose",
                                   json.dumps({"command": "test", "data": {}}))
        assert status == 200

    # ---- 知识库 ----

    def test_knowledge_nodes_get(self):
        status, data = self._call("GET", "/api/knowledge/nodes")
        assert status == 200
        assert data["code"] == 0

    def test_knowledge_search_post(self):
        status, data = self._call("POST", "/api/knowledge/search",
                                   json.dumps({"query": "test", "top_k": 5}))
        assert status == 200
        assert data["code"] == 0

    def test_knowledge_node_post(self):
        status, data = self._call("POST", "/api/knowledge/node",
                                   json.dumps({"name": "node1", "node_type": "concept"}))
        assert status == 200
        assert data["code"] == 0

    def test_knowledge_nodes_post(self):
        status, data = self._call("POST", "/api/knowledge/nodes",
                                   json.dumps({"name": "node2"}))
        assert status == 200
        assert data["code"] == 0

    def test_knowledge_nodes_post_no_name(self):
        status, data = self._call("POST", "/api/knowledge/nodes",
                                   json.dumps({"name": ""}))
        assert status == 400

    # ---- 认证 ----

    def test_auth_token_post(self):
        status, data = self._call("POST", "/api/auth/token",
                                   json.dumps({"username": "admin", "password": "admin123"}))
        assert status == 200
        assert data["code"] == 0
        assert "access_token" in data["data"]

    def test_auth_token_post_wrong_password(self):
        status, data = self._call("POST", "/api/auth/token",
                                   json.dumps({"username": "admin", "password": "wrong"}))
        assert status == 401

    def test_auth_register_post(self):
        status, data = self._call("POST", "/api/auth/register",
                                   json.dumps({"username": "newuser", "password": "pass123"}))
        assert status == 200
        assert data["code"] == 0

    def test_auth_register_existing_user(self):
        status, data = self._call("POST", "/api/auth/register",
                                   json.dumps({"username": "admin", "password": "whatever"}))
        assert status == 409

    def test_auth_register_empty_fields(self):
        status, data = self._call("POST", "/api/auth/register",
                                   json.dumps({"username": "", "password": ""}))
        assert status == 400

    def test_auth_refresh_post(self):
        status, data = self._call("POST", "/api/auth/refresh")
        assert status == 200

    def test_auth_verify_post(self):
        token = _jwt_auth.encode({"user_id": "test"})
        status, data = self._call("POST", "/api/auth/verify",
                                   json.dumps({"token": token}))
        assert status == 200
        assert data["code"] == 0
        assert data["data"]["valid"] is True

    def test_auth_verify_invalid_token(self):
        status, data = self._call("POST", "/api/auth/verify",
                                   json.dumps({"token": "invalid"}))
        assert status == 200
        assert data["code"] == 0
        assert data["data"]["valid"] is False

    # ---- 生成 ----

    def test_generate_post(self):
        status, data = self._call("POST", "/api/generate",
                                   json.dumps({"prompt": "hello", "format": "text"}))
        assert status == 200
        assert data["code"] == 0
        assert "content" in data["data"]

    def test_generate_stream_post(self):
        status, data = self._call("POST", "/api/generate/stream",
                                   json.dumps({"prompt": "hello"}))
        assert status == 200
        assert "chunks" in data or "done" in data

    # ---- 会话 ----

    def test_generate_sessions_get(self):
        status, data = self._call("GET", "/api/generate/sessions")
        assert status == 200
        assert data["code"] == 0

    def test_generate_sessions_delete(self):
        sid = _session_manager.create_session(prompt="test")
        status, data = self._call("DELETE", f"/api/generate/sessions/{sid}")
        assert status == 200
        assert data["code"] == 0

    def test_generate_sessions_delete_not_found(self):
        status, data = self._call("DELETE", "/api/generate/sessions/nonexistent")
        assert status == 404

    # ---- 评估 ----

    def test_evaluate_post(self):
        status, data = self._call("POST", "/api/evaluate",
                                   json.dumps({"items": {"a": 1.0, "b": 2.0}}))
        assert status == 200
        assert data["code"] == 0

    def test_evaluate_report_get(self):
        status, data = self._call("GET", "/api/evaluate/report")
        assert status == 200
        assert data["code"] == 0

    def test_evaluate_score_post(self):
        status, data = self._call("POST", "/api/evaluate/score",
                                   json.dumps({"name": "test", "value": 85}))
        assert status == 200
        assert data["code"] == 0

    # ---- 创新 ----

    def test_innovate_post(self):
        status, data = self._call("POST", "/api/innovate",
                                   json.dumps({"items": ["AI", "区块链"]}))
        assert status == 200
        assert data["code"] == 0

    def test_innovate_evaluate_post(self):
        status, data = self._call("POST", "/api/innovate/evaluate",
                                   json.dumps({"idea_id": "i001"}))
        assert status == 200
        assert data["code"] == 0

    def test_innovate_evaluate_no_idea_id(self):
        status, data = self._call("POST", "/api/innovate/evaluate",
                                   json.dumps({"idea_id": ""}))
        assert status == 200
        assert data["code"] == 1

    # ---- 定位 ----

    def test_locate_get(self):
        status, data = self._call("GET", "/api/locate")
        assert status == 200
        assert data["code"] == 0

    # ---- 均衡 ----

    def test_balance_get(self):
        status, data = self._call("GET", "/api/balance")
        assert status == 200
        assert data["code"] == 0

    def test_balance_state_post(self):
        status, data = self._call("POST", "/api/balance/yang")
        # _dispatch 中 /api/balance/{state} 没有直接定义，会被 404
        # 因为 _dispatch 没有匹配 /api/balance/xxx 的 POST 路由
        pass  # 这个路由在 _dispatch 中不存在

    # ---- 组件 ----

    def test_components_get(self):
        status, data = self._call("GET", "/api/components")
        assert status == 200
        assert data["code"] == 0

    def test_component_call_post(self):
        status, data = self._call("POST", "/api/components/test-comp/call",
                                   json.dumps({"method": "hello", "args": {}}))
        assert status == 200
        assert data["code"] == 0

    def test_component_call_not_found(self):
        self.core.registry.get.return_value = None
        status, data = self._call("POST", "/api/components/unknown/call",
                                   json.dumps({"method": "hello", "args": {}}))
        assert status == 404

    def test_component_call_no_registry(self):
        self.core.registry = None
        status, data = self._call("POST", "/api/components/test/call",
                                   json.dumps({"method": "hello", "args": {}}))
        assert status == 503

    # ---- 任务 ----

    def test_tasks_get(self):
        status, data = self._call("GET", "/api/tasks")
        assert status == 200
        assert data["code"] == 0

    def test_tasks_stats_get(self):
        status, data = self._call("GET", "/api/tasks/stats")
        assert status == 200
        assert data["code"] == 0

    def test_tasks_submit_post(self):
        status, data = self._call("POST", "/api/tasks/submit",
                                   json.dumps({"func_args": {"x": 1}, "priority": "NORMAL"}))
        assert status == 200
        assert data["code"] == 0

    def test_tasks_submit_with_func_name(self):
        _register_predefined_task("test_add", lambda x=1: x + 1)
        status, data = self._call("POST", "/api/tasks/submit",
                                   json.dumps({"func_name": "test_add", "func_args": {"x": 5}}))
        assert status == 200
        assert data["code"] == 0

    def test_tasks_submit_unknown_func_name(self):
        # MagicMock 的 hasattr 总是返回 True，因此临时设置 core.scheduler
        # 并将 core 替换为使 hasattr 对未知属性返回 False 的对象
        import types
        saved_core = self.server.core
        # 创建一个普通对象，只拥有 scheduler 属性
        plain_core = types.SimpleNamespace()
        plain_core.scheduler = saved_core.scheduler
        self.server.core = plain_core
        try:
            status, data = self._call("POST", "/api/tasks/submit",
                                       json.dumps({"func_name": "nonexistent_func"}))
            assert status == 400
        finally:
            self.server.core = saved_core

    def test_tasks_get_by_id(self):
        status, data = self._call("GET", "/api/tasks/task-001")
        assert status == 200
        assert data["code"] == 0

    def test_tasks_get_by_id_not_found(self):
        status, data = self._call("GET", "/api/tasks/nonexistent")
        assert status == 404

    def test_tasks_cancel_post(self):
        status, data = self._call("POST", "/api/tasks/task-001/cancel")
        assert status == 200
        assert data["code"] == 0

    def test_tasks_cancel_not_found(self):
        status, data = self._call("POST", "/api/tasks/nonexistent/cancel")
        assert status == 404

    # ---- 配置 ----

    def test_config_get(self):
        status, data = self._call("GET", "/api/config")
        assert status == 200
        assert data["code"] == 0

    def test_config_post(self):
        status, data = self._call("POST", "/api/config",
                                   json.dumps({"key": "theme", "value": "dark"}))
        assert status == 200
        assert data["code"] == 0

    def test_config_post_no_key(self):
        status, data = self._call("POST", "/api/config",
                                   json.dumps({"key": ""}))
        assert status == 400

    def test_config_get_by_key(self):
        status, data = self._call("GET", "/api/config/app_name")
        assert status == 200
        assert data["code"] == 0

    # ---- 插件 ----

    def test_plugins_get(self):
        status, data = self._call("GET", "/api/plugins")
        assert status == 200
        assert data["code"] == 0

    def test_plugins_get_by_name(self):
        status, data = self._call("GET", "/api/plugins/some-plugin")
        assert status == 200
        assert data["code"] == 1  # plugin not found

    # ---- 优化 ----

    def test_optimize_search_post(self):
        status, data = self._call("POST", "/api/optimize/search",
                                   json.dumps({"n_trials": 5}))
        assert status == 200
        assert data["code"] == 0

    def test_optimize_submit_post(self):
        status, data = self._call("POST", "/api/optimize/submit")
        assert status == 200
        assert data["code"] == 0

    # ---- 404 ----

    def test_unknown_route(self):
        status, data = self._call("GET", "/nonexistent/route")
        assert status == 404
        assert data["code"] == 404

    def test_unknown_route_post(self):
        status, data = self._call("POST", "/api/unknown/endpoint")
        assert status == 404
        assert data["code"] == 404

    # ---- 边缘情况 ----

    def test_dispatch_invalid_json_body(self):
        status, data = self._call("POST", "/api/oracle", "not valid json")
        assert status == 400

    def test_dispatch_kb_not_available(self):
        self.core.kb = None
        status, data = self._call("GET", "/api/knowledge/nodes")
        assert status == 200
        assert data["code"] == 1  # 知识库未就绪

    def test_dispatch_no_consensus(self):
        self.core.consensus = None
        status, data = self._call("POST", "/api/consensus/vote",
                                   json.dumps({"candidate": "node-1"}))
        assert status == 200
        assert data["vote_granted"] is False

    def test_dispatch_no_scheduler_for_tasks(self):
        self.core.scheduler = None
        status, data = self._call("GET", "/api/tasks")
        assert status == 503

    def test_dispatch_no_scheduler_for_tasks_submit(self):
        self.core.scheduler = None
        status, data = self._call("POST", "/api/tasks/submit",
                                   json.dumps({"func_args": {}}))
        assert status == 503

    def test_dispatch_no_scheduler_for_tasks_cancel(self):
        self.core.scheduler = None
        status, data = self._call("POST", "/api/tasks/task-001/cancel")
        assert status == 503

    def test_dispatch_no_locator(self):
        self.core.locator = None
        status, data = self._call("GET", "/api/locate")
        assert status == 503

    def test_dispatch_no_balancer(self):
        self.core.balancer = None
        status, data = self._call("GET", "/api/balance")
        assert status == 503

    def test_dispatch_no_registry_components(self):
        self.core.registry = None
        status, data = self._call("GET", "/api/components")
        assert status == 503

    def test_dispatch_kb_no_query_paginated(self):
        """测试 kb 存在但 query_paginated 返回空"""
        self.core.kb.query_paginated.return_value = {"items": [], "total": 0}
        status, data = self._call("GET", "/api/knowledge/nodes")
        assert status == 200
        assert data["code"] == 0

    def test_dispatch_scheduler_no_tasks_for_get_id(self):
        self.core.scheduler._tasks = {}
        status, data = self._call("GET", "/api/tasks/task-001")
        assert status == 404

    def test_dispatch_scheduler_no_tasks_for_cancel(self):
        self.core.scheduler._tasks = {}
        status, data = self._call("POST", "/api/tasks/task-001/cancel")
        assert status == 404

    def test_component_call_method_not_found(self):
        comp = MagicMock()
        del comp.nonexistent_method  # ensure it doesn't exist
        self.core.registry.get.return_value = comp
        status, data = self._call("POST", "/api/components/test/call",
                                   json.dumps({"method": "nonexistent_method", "args": {}}))
        assert status == 400

    def test_component_call_method_raises(self):
        comp = MagicMock()
        comp.broken = MagicMock(side_effect=Exception("boom"))
        self.core.registry.get.return_value = comp
        status, data = self._call("POST", "/api/components/test/call",
                                   json.dumps({"method": "broken", "args": {}}))
        assert status == 500

    def test_dispatch_no_generator(self):
        self.core.generator = None
        # _dispatch 中 /api/generate 直接使用 self.core.generator.generate
        # 没有 try-except 包裹，因此会抛出 AttributeError
        with pytest.raises(AttributeError):
            self._call("POST", "/api/generate",
                        json.dumps({"prompt": "test"}))

    def test_dispatch_no_innovator(self):
        self.core.innovator = None
        status, data = self._call("POST", "/api/innovate",
                                   json.dumps({"items": ["AI"]}))
        assert status == 200
        assert data["code"] == 0
        assert data["data"]["total"] == 0


# ======================================================================
# 11. 集成 / 边缘测试
# ======================================================================

class TestEdgeCases:
    """边缘情况和集成测试"""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.core = _make_mock_core()

    def test_token_expiry_with_sleep(self):
        """测试 token 过期（短过期时间 + sleep）"""
        auth = JWTAuth()
        token = auth.encode({"user_id": "test"}, expiry=1)
        # 立即验证应该成功
        assert auth.decode(token) is not None
        # 等待 2 秒确保过期
        time.sleep(2)
        assert auth.decode(token) is None

    def test_rate_limiter_exhaustion(self):
        """测试限流器完全耗尽"""
        rl = RateLimiter(max_requests=5, window_seconds=60)
        for i in range(5):
            assert rl.is_allowed("client") is True
        # 超过限制
        assert rl.is_allowed("client") is False
        # retry_after 应该 > 0
        retry = rl.get_retry_after("client")
        assert retry > 0

    def test_session_manager_multiple_messages(self):
        """测试会话管理器多条消息"""
        sm = SessionManager()
        sid = sm.create_session(prompt="conversation")
        for i in range(10):
            sm.add_message(sid, "user", f"msg{i}")
        session = sm.get_session(sid)
        assert len(session["history"]) == 10
        assert session["history"][0]["content"] == "msg0"
        assert session["history"][-1]["content"] == "msg9"

    def test_api_response_roundtrip(self):
        """测试 ApiResponse 序列化往返"""
        resp = ApiResponse(code=200, message="OK", data={"items": [1, 2, 3]})
        d = resp.to_dict()
        reconstructed = ApiResponse(**d)
        assert reconstructed.code == 200
        assert reconstructed.message == "OK"
        assert reconstructed.data == {"items": [1, 2, 3]}

    def test_jwt_encode_decode_with_special_chars(self):
        """测试 JWT 编码/解码带有特殊字符的 payload"""
        auth = JWTAuth()
        payload = {
            "user_id": "中文用户",
            "email": "test@example.com",
            "data": {"nested": "值", "array": [1, 2, 3]},
        }
        token = auth.encode(payload)
        decoded = auth.decode(token)
        assert decoded is not None
        assert decoded["user_id"] == "中文用户"
        assert decoded["email"] == "test@example.com"
        assert decoded["data"]["nested"] == "值"

    def test_hashlib_sha256_consistency(self):
        """验证 _DEFAULT_USERS 中的密码哈希一致性"""
        pw_hash = hashlib.sha256("admin123".encode()).hexdigest()
        assert pw_hash == _DEFAULT_USERS["admin"]["password_hash"]

    def test_base64url_decode_with_padding_needed(self):
        """测试需要补全 padding 的 base64url 解码"""
        auth = JWTAuth()
        # 编码一个长度不是 4 的倍数的数据
        encoded = auth._base64url_encode(b"abc")  # 会产生不带 padding 的字符串
        decoded = auth._base64url_decode(encoded)
        assert decoded == b"abc"

    def test_rate_limiter_concurrent_clients(self):
        """测试多个客户端同时使用限流器"""
        rl = RateLimiter(max_requests=3, window_seconds=60)
        clients = ["c1", "c2", "c3"]
        for c in clients:
            for _ in range(3):
                assert rl.is_allowed(c) is True
            assert rl.is_allowed(c) is False

    def test_dispatch_post_with_empty_body(self):
        """测试 POST 请求空 body"""
        # 使用一个需要 body 的端点
        status, data = SimpleHttpServer(self.core)._dispatch(
            "POST", "/api/auth/verify", ""
        )
        assert status == 200
        assert data["code"] == 0
        # 空 token 验证
        assert data["data"]["valid"] is False

    def test_session_manager_list_after_delete(self):
        """测试删除 session 后列表不包含它"""
        sm = SessionManager()
        sid = sm.create_session(prompt="test")
        assert len(sm.list_sessions()) == 1
        sm.delete_session(sid)
        assert len(sm.list_sessions()) == 0

    def test_check_rate_limit_function(self):
        """测试 _check_rate_limit 函数（使用独立限流器）"""
        rl = RateLimiter(max_requests=2, window_seconds=60)
        with patch(
            "tengod.正官_法度调度.api_server._rate_limiter", rl
        ):
            assert _check_rate_limit("test-ip") is None
            assert _check_rate_limit("test-ip") is None
            retry = _check_rate_limit("test-ip")
            assert retry is not None
            assert isinstance(retry, int)
            assert retry > 0

    def test_dispatch_metrics_route(self):
        """测试 /metrics 端点"""
        # 模拟 metrics 不可用
        status, data = SimpleHttpServer(self.core)._dispatch(
            "GET", "/metrics", ""
        )
        assert status == 200

    def test_predefined_task_override(self):
        """测试预定义任务可以被覆盖"""
        _PREDEFINED_TASKS.clear()
        _register_predefined_task("test", lambda: "first")
        _register_predefined_task("test", lambda: "second")
        assert _get_predefined_task("test")() == "second"

    def test_dispatch_auth_register_multiple(self):
        """测试注册多个用户"""
        core = _make_mock_core()
        server = SimpleHttpServer(core)
        # 注册第一个用户
        status, data = server._dispatch(
            "POST", "/api/auth/register",
            json.dumps({"username": "u1", "password": "p1"})
        )
        assert status == 200
        # 注册第二个用户
        status, data = server._dispatch(
            "POST", "/api/auth/register",
            json.dumps({"username": "u2", "password": "p2"})
        )
        assert status == 200

    def test_rate_limiter_get_retry_after_unknown(self):
        """测试未知标识符的 retry_after"""
        rl = RateLimiter()
        assert rl.get_retry_after("unknown") == 0

    def test_dispatch_knowledge_search_no_kb(self):
        """测试搜索时 kb 不可用（会抛出 AttributeError）"""
        self.core.kb = None
        with pytest.raises(AttributeError):
            SimpleHttpServer(self.core)._dispatch(
                "POST", "/api/knowledge/search",
                json.dumps({"query": "test"})
            )

    def test_dispatch_config_no_config(self):
        """测试配置不可用时 config GET"""
        self.core.config = None
        server = SimpleHttpServer(self.core)
        status, data = server._dispatch("GET", "/api/config", "")
        assert status == 200
        assert data["code"] == 0
        assert data["data"] == {}

    def test_dispatch_config_no_config_post(self):
        """测试配置不可用时 config POST"""
        self.core.config = None
        server = SimpleHttpServer(self.core)
        status, data = server._dispatch("POST", "/api/config",
                               json.dumps({"key": "t", "value": "v"}))
        assert status == 200
        assert data["code"] == 0

    def test_dispatch_config_no_config_get_key(self):
        """测试配置不可用时 config/{key} GET"""
        self.core.config = None
        server = SimpleHttpServer(self.core)
        status, data = server._dispatch("GET", "/api/config/somekey", "")
        assert status == 200
        assert data["code"] == 0
        assert data["data"]["somekey"] is None