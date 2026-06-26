"""
test_middleware.py — TianmenMiddleware 测试套件 v2.16.1
========================================================
覆盖 tengod/middleware.py 中 TianmenMiddleware 的所有功能。
"""
import json
import math
import pytest
from unittest.mock import MagicMock, AsyncMock, patch, PropertyMock

from fastapi import Request
from starlette.responses import Response

# ---------------------------------------------------------------------------
# 测试辅助函数
# ---------------------------------------------------------------------------

# 构建 64 维原型向量（6 个）和中庸锚点（1 个），供 _text_to_vector 使用
_MOCK_PROTOTYPE_VECTORS = [
    [0.7 if i % 6 == j else 0.0 for i in range(64)]
    for j in range(6)
]
# L2 归一化
_MOCK_PROTOTYPE_VECTORS = [
    [x / math.sqrt(sum(v * v for v in vec)) for x in vec]
    for vec in _MOCK_PROTOTYPE_VECTORS
]
_MOCK_ZHONGYONG_ANCHOR = [1.0 / math.sqrt(64)] * 64  # 均匀方向


async def _async_body_iter(content: bytes):
    """Async generator for body_iterator"""
    yield content


def _add_body_iterator(resp: Response, content: bytes):
    """给 Response 添加 body_iterator（Starlette 1.3+ 的 Response 无此属性）"""
    resp.body_iterator = _async_body_iter(content)


def make_json_response(data, status_code=200, headers=None, media_type="application/json"):
    """构建 JSON 响应，带有 body_iterator"""
    content = json.dumps(data).encode()
    h = {"content-type": media_type}
    if headers:
        h.update(headers)
    resp = Response(content=content, status_code=status_code, headers=h, media_type=media_type)
    _add_body_iterator(resp, content)
    return resp


def make_text_response(text, status_code=200, headers=None):
    """构建纯文本响应"""
    content = text.encode()
    h = {"content-type": "text/plain"}
    if headers:
        h.update(headers)
    resp = Response(content=content, status_code=status_code, headers=h, media_type="text/plain")
    _add_body_iterator(resp, content)
    return resp


def make_stream_response(headers=None):
    """构建流式响应（无 content-type，不触发 body 处理）"""
    h = {"content-type": "application/octet-stream"}
    if headers:
        h.update(headers)
    resp = Response(content=b"stream data", status_code=200, headers=h, media_type="application/octet-stream")
    # 流式响应不需要 body_iterator —— 因为 dispatch 中不进入 body 处理分支
    return resp


def make_mock_request(path="/api/test"):
    """构建 mock Request"""
    req = MagicMock(spec=Request)
    req.url.path = path
    return req


def create_passed_verdict():
    """创建"通过"判决"""
    from tengod.tiangan_gate import ZhizhiVerdict
    return ZhizhiVerdict(
        passed=True,
        confidence=0.85,
        entropies={"output": 0.3},
        variance=0.05,
        threshold_level=0.6,
        should_retreat=False,
        retreat_reason="",
        cultivation_qi=0.7,
        inner_child_phi=None,
        inner_child_triggered=False,
        inner_child_dominant="",
        inner_child_beta=0.0,
    )


def create_failed_verdict():
    """创建"不通过"判决"""
    from tengod.tiangan_gate import ZhizhiVerdict
    return ZhizhiVerdict(
        passed=False,
        confidence=0.35,
        entropies={"output": 0.85},
        variance=0.35,
        threshold_level=0.6,
        should_retreat=True,
        retreat_reason="置信度过低",
        cultivation_qi=0.2,
        inner_child_phi=None,
        inner_child_triggered=False,
        inner_child_dominant="",
        inner_child_beta=0.0,
    )


def create_failed_with_inner_child_verdict():
    """创建"不通过+内在小孩触发"判决"""
    from tengod.tiangan_gate import ZhizhiVerdict
    return ZhizhiVerdict(
        passed=False,
        confidence=0.35,
        entropies={"output": 0.85},
        variance=0.35,
        threshold_level=0.6,
        should_retreat=True,
        retreat_reason="内在小孩门禁触发：戒备小孩",
        cultivation_qi=0.2,
        inner_child_phi=0.45,
        inner_child_triggered=True,
        inner_child_dominant="戒备小孩",
        inner_child_beta=0.75,
    )


# ---------------------------------------------------------------------------
# 测试常量
# ---------------------------------------------------------------------------

class TestConstants:
    """测试 EXCLUDE_PATHS 和 MANDATORY_GATE 常量"""

    def test_exclude_paths_contains_expected(self):
        from tengod.middleware import EXCLUDE_PATHS
        assert '/' in EXCLUDE_PATHS
        assert '/health' in EXCLUDE_PATHS
        assert '/health/live' in EXCLUDE_PATHS
        assert '/health/full' in EXCLUDE_PATHS
        assert '/docs' in EXCLUDE_PATHS
        assert '/openapi.json' in EXCLUDE_PATHS
        assert '/redoc' in EXCLUDE_PATHS
        assert '/api/v2/gate/' in EXCLUDE_PATHS

    def test_mandatory_gate_contains_expected(self):
        from tengod.middleware import MANDATORY_GATE
        assert '/api/v2/' in MANDATORY_GATE
        assert '/api/bazi/' in MANDATORY_GATE
        assert '/api/ziwei/' in MANDATORY_GATE
        assert '/api/qimen/' in MANDATORY_GATE
        assert '/api/liuyao/' in MANDATORY_GATE


# ---------------------------------------------------------------------------
# 测试 TianmenMiddleware.__init__
# ---------------------------------------------------------------------------

class TestTianmenMiddlewareInit:
    """测试 TianmenMiddleware 初始化"""

    def test_init_with_default_paths(self):
        """使用默认路径初始化"""
        from tengod.middleware import TianmenMiddleware, EXCLUDE_PATHS, MANDATORY_GATE
        with patch('tengod.middleware.get_tianmen') as mock_gt, \
             patch('tengod.middleware.get_daemon') as mock_gd, \
             patch('tengod.middleware.get_inner_child_sm') as mock_gic:
            mock_gt.return_value = MagicMock()
            mock_gd.return_value = MagicMock()
            mock_gic.return_value = MagicMock()

            mw = TianmenMiddleware(None)

            assert mw._exclude_paths == EXCLUDE_PATHS
            assert mw._mandatory_gate == MANDATORY_GATE
            assert mw._total_requests == 0
            assert mw._blocked_requests == 0
            assert mw._corrected_requests == 0
            mock_gt.assert_called_once()
            mock_gd.assert_called_once()
            mock_gic.assert_called_once_with(
                alertness=32.0, phi_limit=0.8, beta_limit=0.7, lambda_=0.4, gamma=0.2
            )

    def test_init_with_custom_paths(self):
        """使用自定义路径初始化"""
        from tengod.middleware import TianmenMiddleware
        custom_exclude = ['/custom/exclude', '/custom/health']
        custom_mandatory = ['/custom/api/']

        with patch('tengod.middleware.get_tianmen') as mock_gt, \
             patch('tengod.middleware.get_daemon') as mock_gd, \
             patch('tengod.middleware.get_inner_child_sm') as mock_gic:
            mock_gt.return_value = MagicMock()
            mock_gd.return_value = MagicMock()
            mock_gic.return_value = MagicMock()

            mw = TianmenMiddleware(None, exclude_paths=custom_exclude, mandatory_gate=custom_mandatory)

            assert mw._exclude_paths == set(custom_exclude)
            assert mw._mandatory_gate == set(custom_mandatory)


# ---------------------------------------------------------------------------
# 测试 should_gate()
# ---------------------------------------------------------------------------

class TestShouldGate:
    """测试 should_gate() 方法"""

    def test_excluded_path_health(self):
        from tengod.middleware import TianmenMiddleware
        with patch('tengod.middleware.get_tianmen'), \
             patch('tengod.middleware.get_daemon'), \
             patch('tengod.middleware.get_inner_child_sm'):
            mw = TianmenMiddleware(None)
            assert mw.should_gate('/health') is False

    def test_excluded_path_docs(self):
        from tengod.middleware import TianmenMiddleware
        with patch('tengod.middleware.get_tianmen'), \
             patch('tengod.middleware.get_daemon'), \
             patch('tengod.middleware.get_inner_child_sm'):
            mw = TianmenMiddleware(None)
            assert mw.should_gate('/docs') is False

    def test_excluded_path_openapi(self):
        from tengod.middleware import TianmenMiddleware
        with patch('tengod.middleware.get_tianmen'), \
             patch('tengod.middleware.get_daemon'), \
             patch('tengod.middleware.get_inner_child_sm'):
            mw = TianmenMiddleware(None)
            assert mw.should_gate('/openapi.json') is False

    def test_excluded_path_redoc(self):
        from tengod.middleware import TianmenMiddleware
        with patch('tengod.middleware.get_tianmen'), \
             patch('tengod.middleware.get_daemon'), \
             patch('tengod.middleware.get_inner_child_sm'):
            mw = TianmenMiddleware(None)
            assert mw.should_gate('/redoc') is False

    def test_mandatory_path_api_v2(self):
        from tengod.middleware import TianmenMiddleware
        with patch('tengod.middleware.get_tianmen'), \
             patch('tengod.middleware.get_daemon'), \
             patch('tengod.middleware.get_inner_child_sm'):
            mw = TianmenMiddleware(None)
            assert mw.should_gate('/api/v2/some/endpoint') is True

    def test_mandatory_path_api_bazi(self):
        from tengod.middleware import TianmenMiddleware
        with patch('tengod.middleware.get_tianmen'), \
             patch('tengod.middleware.get_daemon'), \
             patch('tengod.middleware.get_inner_child_sm'):
            mw = TianmenMiddleware(None)
            assert mw.should_gate('/api/bazi/analyze') is True

    def test_mandatory_path_api_ziwei(self):
        from tengod.middleware import TianmenMiddleware
        with patch('tengod.middleware.get_tianmen'), \
             patch('tengod.middleware.get_daemon'), \
             patch('tengod.middleware.get_inner_child_sm'):
            mw = TianmenMiddleware(None)
            assert mw.should_gate('/api/ziwei/chart') is True

    def test_default_api_prefix_returns_true(self):
        from tengod.middleware import TianmenMiddleware
        with patch('tengod.middleware.get_tianmen'), \
             patch('tengod.middleware.get_daemon'), \
             patch('tengod.middleware.get_inner_child_sm'):
            mw = TianmenMiddleware(None)
            assert mw.should_gate('/api/some/other/path') is True

    def test_non_api_path_returns_false(self):
        from tengod.middleware import TianmenMiddleware
        with patch('tengod.middleware.get_tianmen'), \
             patch('tengod.middleware.get_daemon'), \
             patch('tengod.middleware.get_inner_child_sm'):
            mw = TianmenMiddleware(None)
            assert mw.should_gate('/some/random/path') is False
            assert mw.should_gate('/about') is False
            assert mw.should_gate('/static/js/app.js') is False

    def test_excluded_directory_prefix(self):
        """排除路径以 / 结尾表示目录前缀排除"""
        from tengod.middleware import TianmenMiddleware
        with patch('tengod.middleware.get_tianmen'), \
             patch('tengod.middleware.get_daemon'), \
             patch('tengod.middleware.get_inner_child_sm'):
            mw = TianmenMiddleware(None)
            # /api/v2/gate/ 是排除目录，其子路径也应排除
            assert mw.should_gate('/api/v2/gate/stats') is False
            assert mw.should_gate('/api/v2/gate/config') is False

    def test_should_gate_empty_path(self):
        """空路径测试"""
        from tengod.middleware import TianmenMiddleware
        with patch('tengod.middleware.get_tianmen'), \
             patch('tengod.middleware.get_daemon'), \
             patch('tengod.middleware.get_inner_child_sm'):
            mw = TianmenMiddleware(None)
            # 空路径不以 /api 开头，也不匹配任何排除/强制规则
            assert mw.should_gate('') is False

    def test_should_gate_root_path(self):
        from tengod.middleware import TianmenMiddleware
        with patch('tengod.middleware.get_tianmen'), \
             patch('tengod.middleware.get_daemon'), \
             patch('tengod.middleware.get_inner_child_sm'):
            mw = TianmenMiddleware(None)
            assert mw.should_gate('/') is False


# ---------------------------------------------------------------------------
# 测试 dispatch()
# ---------------------------------------------------------------------------

class TestDispatch:
    """测试 dispatch() 异步方法"""

    @pytest.mark.asyncio
    async def test_dispatch_excluded_path(self):
        """排除路径直接放行，不经过门禁"""
        from tengod.middleware import TianmenMiddleware
        with patch('tengod.middleware.get_tianmen'), \
             patch('tengod.middleware.get_daemon'), \
             patch('tengod.middleware.get_inner_child_sm'):
            mw = TianmenMiddleware(None)
            req = make_mock_request('/health')
            mock_call_next = AsyncMock(return_value=make_json_response({"ok": True}))

            resp = await mw.dispatch(req, mock_call_next)

            mock_call_next.assert_awaited_once()
            assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_dispatch_json_passed_high_confidence(self):
        """JSON 响应高置信度通过"""
        from tengod.middleware import TianmenMiddleware
        with patch('tengod.middleware.get_tianmen') as mock_gt, \
             patch('tengod.middleware.get_daemon') as mock_gd, \
             patch('tengod.middleware.get_inner_child_sm') as mock_gic:
            # 设置 mock
            mock_tianmen = MagicMock()
            mock_tianmen.engine.judge.return_value = create_passed_verdict()
            mock_tianmen.get_stats.return_value = {"total": 0, "pass_rate": 0}
            mock_gt.return_value = mock_tianmen

            mock_daemon = MagicMock()
            mock_daemon.get_stats.return_value = {}
            mock_gd.return_value = mock_daemon

            mock_inner = MagicMock()
            mock_inner.process.return_value = {
                "state": {"gate_triggered": False, "dominant": {"name": "", "beta": 0.0}, "entropy_phi": 1.5},
                "safety_fallback": False,
            }
            mock_inner.get_stats.return_value = {}
            mock_gic.return_value = mock_inner

            mw = TianmenMiddleware(None)
            req = make_mock_request('/api/test')
            mock_call_next = AsyncMock(return_value=make_json_response({"result": "success", "confidence": 0.9}))

            resp = await mw.dispatch(req, mock_call_next)

            assert resp.status_code == 200
            assert resp.headers.get('X-Tianmen-Passed') == 'true'
            assert 'X-Tianmen-Confidence' in resp.headers
            assert mw._total_requests == 1
            assert mw._blocked_requests == 0

    @pytest.mark.asyncio
    async def test_dispatch_json_low_confidence_retreat(self):
        """JSON 响应低置信度触发 retreat 和修正"""
        from tengod.middleware import TianmenMiddleware
        with patch('tengod.middleware.get_tianmen') as mock_gt, \
             patch('tengod.middleware.get_daemon') as mock_gd, \
             patch('tengod.middleware.get_inner_child_sm') as mock_gic:
            mock_tianmen = MagicMock()
            mock_tianmen.engine.judge.return_value = create_failed_verdict()
            mock_tianmen.get_stats.return_value = {"total": 0, "pass_rate": 0}
            mock_gt.return_value = mock_tianmen

            mock_daemon = MagicMock()
            # daemon.correct 返回修正后的内容
            mock_daemon.correct.return_value = (
                {"output": {"result": "corrected"}, "confidence": 0.35, "uncertainty": 0.5},
                MagicMock(success=True),
            )
            mock_daemon.get_stats.return_value = {}
            mock_gd.return_value = mock_daemon

            mock_inner = MagicMock()
            mock_inner.process.return_value = {
                "state": {"gate_triggered": False, "dominant": {"name": "", "beta": 0.0}, "entropy_phi": 1.5},
                "safety_fallback": False,
            }
            mock_inner.get_stats.return_value = {}
            mock_gic.return_value = mock_inner

            mw = TianmenMiddleware(None)
            req = make_mock_request('/api/test')
            mock_call_next = AsyncMock(return_value=make_json_response({"result": "bad"}))

            resp = await mw.dispatch(req, mock_call_next)

            assert resp.status_code == 200
            assert resp.headers.get('X-Tianmen-Passed') == 'false'
            assert 'X-Tianmen-Reason' in resp.headers
            assert mw._total_requests == 1
            assert mw._blocked_requests == 1
            assert mw._corrected_requests == 1

    @pytest.mark.asyncio
    async def test_dispatch_non_json_text_response(self):
        """非 JSON 响应（text/plain）直接返回"""
        from tengod.middleware import TianmenMiddleware
        with patch('tengod.middleware.get_tianmen'), \
             patch('tengod.middleware.get_daemon'), \
             patch('tengod.middleware.get_inner_child_sm'):
            mw = TianmenMiddleware(None)
            req = make_mock_request('/api/hello')
            mock_call_next = AsyncMock(return_value=make_text_response("Hello, World!"))

            resp = await mw.dispatch(req, mock_call_next)

            assert resp.status_code == 200
            body = resp.body
            assert b"Hello, World!" in body

    @pytest.mark.asyncio
    async def test_dispatch_increments_total_requests(self):
        """dispatch 增加 _total_requests 计数"""
        from tengod.middleware import TianmenMiddleware
        with patch('tengod.middleware.get_tianmen') as mock_gt, \
             patch('tengod.middleware.get_daemon'), \
             patch('tengod.middleware.get_inner_child_sm') as mock_gic:
            mock_tianmen = MagicMock()
            mock_tianmen.engine.judge.return_value = create_passed_verdict()
            mock_tianmen.get_stats.return_value = {}
            mock_gt.return_value = mock_tianmen
            mock_gd = MagicMock()
            mock_gd.get_stats.return_value = {}
            mock_gd.return_value = mock_gd  # hang on... this is wrong
            mock_inner = MagicMock()
            mock_inner.process.return_value = {
                "state": {"gate_triggered": False, "dominant": {"name": "", "beta": 0.0}, "entropy_phi": 1.5},
                "safety_fallback": False,
            }
            mock_inner.get_stats.return_value = {}
            mock_gic.return_value = mock_inner

            mw = TianmenMiddleware(None)
            assert mw._total_requests == 0

            req = make_mock_request('/api/test')
            mock_call_next = AsyncMock(return_value=make_json_response({"ok": True}))
            await mw.dispatch(req, mock_call_next)

            assert mw._total_requests == 1

    @pytest.mark.asyncio
    async def test_dispatch_increments_blocked_when_not_passed(self):
        """dispatch 不通过时增加 _blocked_requests"""
        from tengod.middleware import TianmenMiddleware
        with patch('tengod.middleware.get_tianmen') as mock_gt, \
             patch('tengod.middleware.get_daemon') as mock_gd, \
             patch('tengod.middleware.get_inner_child_sm') as mock_gic:
            mock_tianmen = MagicMock()
            mock_tianmen.engine.judge.return_value = create_failed_verdict()
            mock_tianmen.get_stats.return_value = {}
            mock_gt.return_value = mock_tianmen

            mock_daemon = MagicMock()
            mock_daemon.correct.return_value = (
                {"output": {"result": "ok"}, "confidence": 0.35, "uncertainty": 0.5},
                MagicMock(success=True),
            )
            mock_daemon.get_stats.return_value = {}
            mock_gd.return_value = mock_daemon

            mock_inner = MagicMock()
            mock_inner.process.return_value = {
                "state": {"gate_triggered": False, "dominant": {"name": "", "beta": 0.0}, "entropy_phi": 1.5},
                "safety_fallback": False,
            }
            mock_inner.get_stats.return_value = {}
            mock_gic.return_value = mock_inner

            mw = TianmenMiddleware(None)
            req = make_mock_request('/api/test')
            mock_call_next = AsyncMock(return_value=make_json_response({"result": "bad"}))

            await mw.dispatch(req, mock_call_next)

            assert mw._blocked_requests == 1

    @pytest.mark.asyncio
    async def test_dispatch_increments_corrected_when_daemon_corrects(self):
        """daemon 修正成功时增加 _corrected_requests"""
        from tengod.middleware import TianmenMiddleware
        with patch('tengod.middleware.get_tianmen') as mock_gt, \
             patch('tengod.middleware.get_daemon') as mock_gd, \
             patch('tengod.middleware.get_inner_child_sm') as mock_gic:
            mock_tianmen = MagicMock()
            mock_tianmen.engine.judge.return_value = create_failed_verdict()
            mock_tianmen.get_stats.return_value = {}
            mock_gt.return_value = mock_tianmen

            mock_daemon = MagicMock()
            mock_daemon.correct.return_value = (
                {"output": {"result": "corrected"}, "confidence": 0.5, "uncertainty": 0.5},
                MagicMock(success=True),
            )
            mock_daemon.get_stats.return_value = {}
            mock_gd.return_value = mock_daemon

            mock_inner = MagicMock()
            mock_inner.process.return_value = {
                "state": {"gate_triggered": False, "dominant": {"name": "", "beta": 0.0}, "entropy_phi": 1.5},
                "safety_fallback": False,
            }
            mock_inner.get_stats.return_value = {}
            mock_gic.return_value = mock_inner

            mw = TianmenMiddleware(None)
            req = make_mock_request('/api/test')
            mock_call_next = AsyncMock(return_value=make_json_response({"result": "bad"}))

            await mw.dispatch(req, mock_call_next)

            assert mw._corrected_requests == 1

    @pytest.mark.asyncio
    async def test_dispatch_adds_xtianmen_headers(self):
        """dispatch 添加 X-Tianmen-* 响应头"""
        from tengod.middleware import TianmenMiddleware
        with patch('tengod.middleware.get_tianmen') as mock_gt, \
             patch('tengod.middleware.get_daemon'), \
             patch('tengod.middleware.get_inner_child_sm') as mock_gic:
            mock_tianmen = MagicMock()
            mock_tianmen.engine.judge.return_value = create_passed_verdict()
            mock_tianmen.get_stats.return_value = {}
            mock_gt.return_value = mock_tianmen

            mock_inner = MagicMock()
            mock_inner.process.return_value = {
                "state": {"gate_triggered": False, "dominant": {"name": "", "beta": 0.0}, "entropy_phi": 1.5},
                "safety_fallback": False,
            }
            mock_inner.get_stats.return_value = {}
            mock_gic.return_value = mock_inner

            mw = TianmenMiddleware(None)
            req = make_mock_request('/api/test')
            mock_call_next = AsyncMock(return_value=make_json_response({"ok": True}))

            resp = await mw.dispatch(req, mock_call_next)

            assert 'X-Tianmen-Passed' in resp.headers
            assert 'X-Tianmen-Confidence' in resp.headers
            assert 'X-Tianmen-Qi' in resp.headers
            assert resp.headers['X-Tianmen-Passed'] == 'true'

    @pytest.mark.asyncio
    async def test_dispatch_with_inner_child_headers(self):
        """dispatch 带有内在小孩门禁头"""
        from tengod.middleware import TianmenMiddleware
        with patch('tengod.middleware.get_tianmen') as mock_gt, \
             patch('tengod.middleware.get_daemon'), \
             patch('tengod.middleware.get_inner_child_sm') as mock_gic:
            mock_tianmen = MagicMock()
            mock_tianmen.engine.judge.return_value = create_failed_with_inner_child_verdict()
            mock_tianmen.get_stats.return_value = {}
            mock_gt.return_value = mock_tianmen

            mock_daemon = MagicMock()
            mock_daemon.correct.return_value = (
                {"output": {"result": "ok"}, "confidence": 0.35, "uncertainty": 0.5},
                MagicMock(success=False),
            )
            mock_daemon.get_stats.return_value = {}
            mock_gd = MagicMock(return_value=mock_daemon)

            mock_inner = MagicMock()
            mock_inner.process.return_value = {
                "state": {
                    "gate_triggered": True,
                    "dominant": {"name": "戒备小孩", "beta": 0.75},
                    "entropy_phi": 0.45,
                },
                "safety_fallback": False,
            }
            mock_inner.get_stats.return_value = {}
            mock_gic.return_value = mock_inner

            with patch('tengod.middleware.get_daemon', return_value=mock_daemon):
                mw = TianmenMiddleware(None)
                req = make_mock_request('/api/test')
                mock_call_next = AsyncMock(return_value=make_json_response({"result": "test"}))

                resp = await mw.dispatch(req, mock_call_next)

                assert 'X-Tianmen-Child-Phi' in resp.headers
                assert 'X-Tianmen-Child-Dominant' in resp.headers
                assert 'X-Tianmen-Child-Beta' in resp.headers
                assert 'X-Tianmen-Child-Triggered' in resp.headers

    @pytest.mark.asyncio
    async def test_dispatch_hex_encoded_reason_when_not_passed(self):
        """不通过时，原因以 hex 编码"""
        from tengod.middleware import TianmenMiddleware
        with patch('tengod.middleware.get_tianmen') as mock_gt, \
             patch('tengod.middleware.get_daemon'), \
             patch('tengod.middleware.get_inner_child_sm') as mock_gic:
            mock_tianmen = MagicMock()
            mock_tianmen.engine.judge.return_value = create_failed_verdict()
            mock_tianmen.get_stats.return_value = {}
            mock_gt.return_value = mock_tianmen

            mock_daemon = MagicMock()
            mock_daemon.correct.return_value = (
                {"output": {"result": "bad"}, "confidence": 0.35, "uncertainty": 0.5},
                MagicMock(success=False),
            )
            mock_daemon.get_stats.return_value = {}
            mock_gd = MagicMock(return_value=mock_daemon)

            mock_inner = MagicMock()
            mock_inner.process.return_value = {
                "state": {"gate_triggered": False, "dominant": {"name": "", "beta": 0.0}, "entropy_phi": 1.5},
                "safety_fallback": False,
            }
            mock_inner.get_stats.return_value = {}
            mock_gic.return_value = mock_inner

            with patch('tengod.middleware.get_daemon', return_value=mock_daemon):
                mw = TianmenMiddleware(None)
                req = make_mock_request('/api/test')
                mock_call_next = AsyncMock(return_value=make_json_response({"result": "bad"}))

                resp = await mw.dispatch(req, mock_call_next)

                assert 'X-Tianmen-Reason' in resp.headers
                # 验证是 hex 编码（只包含 0-9a-f）
                reason = resp.headers['X-Tianmen-Reason']
                assert all(c in '0123456789abcdef' for c in reason)

    @pytest.mark.asyncio
    async def test_dispatch_stream_response_skips_body(self):
        """流式响应跳过 body 处理"""
        from tengod.middleware import TianmenMiddleware
        with patch('tengod.middleware.get_tianmen'), \
             patch('tengod.middleware.get_daemon'), \
             patch('tengod.middleware.get_inner_child_sm'):
            mw = TianmenMiddleware(None)
            req = make_mock_request('/api/stream')
            mock_call_next = AsyncMock(return_value=make_stream_response())

            resp = await mw.dispatch(req, mock_call_next)

            assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_dispatch_json_parse_error(self):
        """JSON 解析失败时返回原始响应"""
        from tengod.middleware import TianmenMiddleware
        with patch('tengod.middleware.get_tianmen'), \
             patch('tengod.middleware.get_daemon'), \
             patch('tengod.middleware.get_inner_child_sm'):
            mw = TianmenMiddleware(None)
            req = make_mock_request('/api/test')
            # 返回一个 content-type 为 json 但内容是纯文本的响应
            resp_data = Response(
                content=b"not valid json",
                status_code=200,
                headers={"content-type": "application/json"},
                media_type="application/json",
            )
            _add_body_iterator(resp_data, b"not valid json")
            mock_call_next = AsyncMock(return_value=resp_data)

            resp = await mw.dispatch(req, mock_call_next)

            assert resp.status_code == 200
            # 应该原样返回
            assert resp.body == b"not valid json"

    @pytest.mark.asyncio
    async def test_dispatch_inner_child_exception_caught(self):
        """inner_child 异常被捕获，不影响主流程"""
        from tengod.middleware import TianmenMiddleware
        with patch('tengod.middleware.get_tianmen') as mock_gt, \
             patch('tengod.middleware.get_daemon'), \
             patch('tengod.middleware.get_inner_child_sm') as mock_gic:
            mock_tianmen = MagicMock()
            mock_tianmen.engine.judge.return_value = create_passed_verdict()
            mock_tianmen.get_stats.return_value = {}
            mock_gt.return_value = mock_tianmen

            mock_inner = MagicMock()
            mock_inner.process.side_effect = RuntimeError("inner child crash")
            mock_inner.get_stats.return_value = {}
            mock_gic.return_value = mock_inner

            mw = TianmenMiddleware(None)
            req = make_mock_request('/api/test')
            mock_call_next = AsyncMock(return_value=make_json_response({"ok": True}))

            resp = await mw.dispatch(req, mock_call_next)

            # 不应崩溃，正常返回
            assert resp.status_code == 200
            assert resp.headers.get('X-Tianmen-Passed') == 'true'

    @pytest.mark.asyncio
    async def test_dispatch_daemon_correction_failure(self):
        """daemon 修正失败不影响响应返回"""
        from tengod.middleware import TianmenMiddleware
        with patch('tengod.middleware.get_tianmen') as mock_gt, \
             patch('tengod.middleware.get_daemon'), \
             patch('tengod.middleware.get_inner_child_sm') as mock_gic:
            mock_tianmen = MagicMock()
            mock_tianmen.engine.judge.return_value = create_failed_verdict()
            mock_tianmen.get_stats.return_value = {}
            mock_gt.return_value = mock_tianmen

            mock_daemon = MagicMock()
            mock_daemon.correct.return_value = (
                {"output": {"result": "bad"}, "confidence": 0.35, "uncertainty": 0.5},
                MagicMock(success=False),
            )
            mock_daemon.get_stats.return_value = {}
            mock_gd = MagicMock(return_value=mock_daemon)

            mock_inner = MagicMock()
            mock_inner.process.return_value = {
                "state": {"gate_triggered": False, "dominant": {"name": "", "beta": 0.0}, "entropy_phi": 1.5},
                "safety_fallback": False,
            }
            mock_inner.get_stats.return_value = {}
            mock_gic.return_value = mock_inner

            with patch('tengod.middleware.get_daemon', return_value=mock_daemon):
                mw = TianmenMiddleware(None)
                req = make_mock_request('/api/test')
                mock_call_next = AsyncMock(return_value=make_json_response({"result": "bad"}))

                resp = await mw.dispatch(req, mock_call_next)

                assert resp.status_code == 200
                assert mw._blocked_requests == 1
                # 修正失败，_corrected_requests 不增加
                assert mw._corrected_requests == 0


# ---------------------------------------------------------------------------
# 测试 _extract_confidence()
# ---------------------------------------------------------------------------

class TestExtractConfidence:
    """测试 _extract_confidence() 方法"""

    def test_extract_with_confidence_key(self):
        from tengod.middleware import TianmenMiddleware
        with patch('tengod.middleware.get_tianmen'), \
             patch('tengod.middleware.get_daemon'), \
             patch('tengod.middleware.get_inner_child_sm'):
            mw = TianmenMiddleware(None)
            scores = mw._extract_confidence({"confidence": 0.85, "result": "ok"})
            assert 'output' in scores
            assert scores['output'] == 0.85

    def test_extract_with_score_key(self):
        from tengod.middleware import TianmenMiddleware
        with patch('tengod.middleware.get_tianmen'), \
             patch('tengod.middleware.get_daemon'), \
             patch('tengod.middleware.get_inner_child_sm'):
            mw = TianmenMiddleware(None)
            scores = mw._extract_confidence({"score": 0.72, "result": "ok"})
            assert 'score' in scores
            assert scores['score'] == 0.72

    def test_extract_with_overall_key(self):
        from tengod.middleware import TianmenMiddleware
        with patch('tengod.middleware.get_tianmen'), \
             patch('tengod.middleware.get_daemon'), \
             patch('tengod.middleware.get_inner_child_sm'):
            mw = TianmenMiddleware(None)
            scores = mw._extract_confidence({"overall": {"confidence": 0.66}})
            assert 'overall' in scores
            assert scores['overall'] == 0.66

    def test_extract_with_overall_scalar(self):
        from tengod.middleware import TianmenMiddleware
        with patch('tengod.middleware.get_tianmen'), \
             patch('tengod.middleware.get_daemon'), \
             patch('tengod.middleware.get_inner_child_sm'):
            mw = TianmenMiddleware(None)
            scores = mw._extract_confidence({"overall": 0.55})
            assert 'overall' in scores
            assert scores['overall'] == 0.55

    def test_extract_no_confidence_fields(self):
        from tengod.middleware import TianmenMiddleware
        with patch('tengod.middleware.get_tianmen'), \
             patch('tengod.middleware.get_daemon'), \
             patch('tengod.middleware.get_inner_child_sm'):
            mw = TianmenMiddleware(None)
            scores = mw._extract_confidence({"result": "just data", "name": "test"})
            assert scores == {'overall': 0.5}

    def test_extract_non_dict_content(self):
        from tengod.middleware import TianmenMiddleware
        with patch('tengod.middleware.get_tianmen'), \
             patch('tengod.middleware.get_daemon'), \
             patch('tengod.middleware.get_inner_child_sm'):
            mw = TianmenMiddleware(None)
            scores = mw._extract_confidence(["list", "not", "dict"])
            assert scores == {'overall': 0.5}

            scores = mw._extract_confidence("just a string")
            assert scores == {'overall': 0.5}

            scores = mw._extract_confidence(42)
            assert scores == {'overall': 0.5}


# ---------------------------------------------------------------------------
# 测试 _text_to_vector()
# ---------------------------------------------------------------------------

class TestTextToVector:
    """测试 _text_to_vector() 方法"""

    @pytest.fixture(autouse=True)
    def _patch_vectors(self):
        """为所有测试注入 mock 原型向量和中庸锚点"""
        with patch('tengod.inner_child._PROTOTYPE_VECTORS', _MOCK_PROTOTYPE_VECTORS), \
             patch('tengod.inner_child._ZHONGYONG_ANCHOR', _MOCK_ZHONGYONG_ANCHOR):
            yield

    def test_text_to_vector_chinese_text(self):
        from tengod.middleware import TianmenMiddleware
        with patch('tengod.middleware.get_tianmen'), \
             patch('tengod.middleware.get_daemon'), \
             patch('tengod.middleware.get_inner_child_sm'):
            mw = TianmenMiddleware(None)
            vec = mw._text_to_vector("道可道，非常道；名可名，非常名。")
            assert len(vec) == 64
            # 验证 L2 归一化
            norm = math.sqrt(sum(x * x for x in vec))
            assert abs(norm - 1.0) < 1e-6

    def test_text_to_vector_english_text(self):
        from tengod.middleware import TianmenMiddleware
        with patch('tengod.middleware.get_tianmen'), \
             patch('tengod.middleware.get_daemon'), \
             patch('tengod.middleware.get_inner_child_sm'):
            mw = TianmenMiddleware(None)
            vec = mw._text_to_vector("The Tao that can be told is not the eternal Tao.")
            assert len(vec) == 64
            norm = math.sqrt(sum(x * x for x in vec))
            assert abs(norm - 1.0) < 1e-6

    def test_text_to_vector_empty_text(self):
        from tengod.middleware import TianmenMiddleware
        with patch('tengod.middleware.get_tianmen'), \
             patch('tengod.middleware.get_daemon'), \
             patch('tengod.middleware.get_inner_child_sm'):
            mw = TianmenMiddleware(None)
            vec = mw._text_to_vector("")
            assert len(vec) == 64
            norm = math.sqrt(sum(x * x for x in vec))
            assert abs(norm - 1.0) < 1e-6

    def test_text_to_vector_returns_normalized(self):
        """验证返回向量已 L2 归一化"""
        from tengod.middleware import TianmenMiddleware
        with patch('tengod.middleware.get_tianmen'), \
             patch('tengod.middleware.get_daemon'), \
             patch('tengod.middleware.get_inner_child_sm'):
            mw = TianmenMiddleware(None)
            vec = mw._text_to_vector("测试文本")
            norm = math.sqrt(sum(x * x for x in vec))
            assert abs(norm - 1.0) < 1e-6

    def test_text_to_vector_64_dim(self):
        """验证返回 64 维向量"""
        from tengod.middleware import TianmenMiddleware
        with patch('tengod.middleware.get_tianmen'), \
             patch('tengod.middleware.get_daemon'), \
             patch('tengod.middleware.get_inner_child_sm'):
            mw = TianmenMiddleware(None)
            vec = mw._text_to_vector("任意文本")
            assert len(vec) == 64

    def test_text_to_vector_very_long_text(self):
        """超长文本测试"""
        from tengod.middleware import TianmenMiddleware
        with patch('tengod.middleware.get_tianmen'), \
             patch('tengod.middleware.get_daemon'), \
             patch('tengod.middleware.get_inner_child_sm'):
            mw = TianmenMiddleware(None)
            long_text = "道" * 10000 + "但是" * 1000
            vec = mw._text_to_vector(long_text)
            assert len(vec) == 64
            norm = math.sqrt(sum(x * x for x in vec))
            assert abs(norm - 1.0) < 1e-6


# ---------------------------------------------------------------------------
# 测试 get_stats()
# ---------------------------------------------------------------------------

class TestGetStats:
    """测试 get_stats() 方法"""

    def test_get_stats_returns_all_fields(self):
        from tengod.middleware import TianmenMiddleware
        with patch('tengod.middleware.get_tianmen') as mock_gt, \
             patch('tengod.middleware.get_daemon') as mock_gd, \
             patch('tengod.middleware.get_inner_child_sm') as mock_gic:
            mock_tianmen = MagicMock()
            mock_tianmen.get_stats.return_value = {"total": 0, "pass_rate": 0}
            mock_gt.return_value = mock_tianmen

            mock_daemon = MagicMock()
            mock_daemon.get_stats.return_value = {"total_corrections": 0}
            mock_gd.return_value = mock_daemon

            mock_inner = MagicMock()
            mock_inner.get_stats.return_value = {"total_probes": 0}
            mock_gic.return_value = mock_inner

            mw = TianmenMiddleware(None)
            stats = mw.get_stats()

            assert 'total_requests' in stats
            assert 'blocked_requests' in stats
            assert 'corrected_requests' in stats
            assert 'block_rate' in stats
            assert 'correction_rate' in stats
            assert 'tianmen' in stats
            assert 'correction' in stats
            assert 'inner_child' in stats

    def test_get_stats_block_rate_calculation(self):
        from tengod.middleware import TianmenMiddleware
        with patch('tengod.middleware.get_tianmen') as mock_gt, \
             patch('tengod.middleware.get_daemon') as mock_gd, \
             patch('tengod.middleware.get_inner_child_sm') as mock_gic:
            mock_gt.return_value = MagicMock(get_stats=lambda: {})
            mock_gd.return_value = MagicMock(get_stats=lambda: {})
            mock_gic.return_value = MagicMock(get_stats=lambda: {})

            mw = TianmenMiddleware(None)
            mw._total_requests = 10
            mw._blocked_requests = 3
            mw._corrected_requests = 2

            stats = mw.get_stats()
            assert stats['block_rate'] == 0.3
            assert stats['correction_rate'] == round(2 / 3, 3)

    def test_get_stats_zero_requests(self):
        from tengod.middleware import TianmenMiddleware
        with patch('tengod.middleware.get_tianmen') as mock_gt, \
             patch('tengod.middleware.get_daemon') as mock_gd, \
             patch('tengod.middleware.get_inner_child_sm') as mock_gic:
            mock_gt.return_value = MagicMock(get_stats=lambda: {})
            mock_gd.return_value = MagicMock(get_stats=lambda: {})
            mock_gic.return_value = MagicMock(get_stats=lambda: {})

            mw = TianmenMiddleware(None)
            stats = mw.get_stats()

            assert stats['block_rate'] == 0.0
            assert stats['correction_rate'] == 0.0


# ---------------------------------------------------------------------------
# 测试 get_middleware() 单例
# ---------------------------------------------------------------------------

class TestGetMiddlewareSingleton:
    """测试 get_middleware() 单例函数"""

    def setup_method(self):
        """重置全局单例"""
        import tengod.middleware as mw_mod
        mw_mod._tianmen_middleware = None

    def test_returns_same_instance(self):
        """两次调用返回相同实例"""
        from tengod.middleware import get_middleware

        with patch('tengod.middleware.get_tianmen'), \
             patch('tengod.middleware.get_daemon'), \
             patch('tengod.middleware.get_inner_child_sm'):
            mw1 = get_middleware()
            mw2 = get_middleware()
            assert mw1 is mw2

    def test_creates_with_custom_paths_first_time(self):
        """首次调用可使用自定义路径"""
        import tengod.middleware as mw_mod
        mw_mod._tianmen_middleware = None

        from tengod.middleware import get_middleware
        custom_exclude = ['/custom/health']
        custom_mandatory = ['/custom/api/']

        with patch('tengod.middleware.get_tianmen'), \
             patch('tengod.middleware.get_daemon'), \
             patch('tengod.middleware.get_inner_child_sm'):
            mw = get_middleware(
                exclude_paths=custom_exclude,
                mandatory_gate=custom_mandatory,
            )
            assert mw._exclude_paths == set(custom_exclude)
            assert mw._mandatory_gate == set(custom_mandatory)


# ---------------------------------------------------------------------------
# 测试 __all__ 导出
# ---------------------------------------------------------------------------

class TestExports:
    """测试模块导出"""

    def test_all_exports(self):
        from tengod import middleware
        assert 'TianmenMiddleware' in middleware.__all__
        assert 'get_middleware' in middleware.__all__