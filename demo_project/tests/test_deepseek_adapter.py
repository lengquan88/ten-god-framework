#!/usr/bin/env python3
"""
test_deepseek_adapter.py — Deepseek AI 适配器全面单元测试
覆盖：配置、消息构建、客户端管理、聊天、流式聊天、便捷函数、边界情况
使用 mock 避免真实 API 调用
"""
import os
import sys
import json
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from tengod.deepseek_adapter import (
    DeepseekConfig,
    DeepseekClient,
    DeepseekResponse,
    Message,
    BAZI_SYSTEM_PROMPT,
    QIMEN_SYSTEM_PROMPT,
    get_client,
    analyze_bazi,
    _format_bazi,
)

# ════════════════════════════════════════════════════════════════
# 辅助：创建模拟 httpx 响应的工具函数
# ════════════════════════════════════════════════════════════════


def _make_mock_response(content="测试响应", model="deepseek-chat", usage=None, finish_reason="stop"):
    """创建模拟的 httpx Response 对象"""
    if usage is None:
        usage = {"prompt_tokens": 5, "completion_tokens": 10, "total_tokens": 15}
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = {
        "choices": [{"message": {"content": content}, "finish_reason": finish_reason}],
        "model": model,
        "usage": usage,
    }
    return mock_resp


def _make_mock_httpx_client(post_return=None):
    """创建模拟的 httpx.AsyncClient"""
    mock_client = AsyncMock()
    mock_client.is_closed = False
    if post_return:
        mock_client.post = AsyncMock(return_value=post_return)
    return mock_client


# ════════════════════════════════════════════════════════════════
# 1. DeepseekConfig 数据类
# ════════════════════════════════════════════════════════════════


class TestDeepseekConfig:
    """配置类测试"""

    def test_default_values(self):
        """测试默认配置值"""
        cfg = DeepseekConfig()
        assert cfg.base_url == "https://api.deepseek.com/v1"
        assert cfg.model == "deepseek-chat"
        assert cfg.max_tokens == 2048
        assert cfg.temperature == 0.7
        assert cfg.timeout == 60.0

    def test_api_key_from_env(self, monkeypatch):
        """测试从环境变量读取 api_key"""
        monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key-from-env")
        cfg = DeepseekConfig()
        assert cfg.api_key == "test-key-from-env"

    def test_api_key_default_empty(self, monkeypatch):
        """测试无环境变量时 api_key 默认为空字符串"""
        monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
        cfg = DeepseekConfig()
        assert cfg.api_key == ""

    def test_custom_values(self):
        """测试自定义配置值"""
        cfg = DeepseekConfig(
            api_key="custom-key",
            base_url="https://custom.api.com",
            model="deepseek-reasoner",
            max_tokens=4096,
            temperature=0.3,
            timeout=30.0,
        )
        assert cfg.api_key == "custom-key"
        assert cfg.base_url == "https://custom.api.com"
        assert cfg.model == "deepseek-reasoner"
        assert cfg.max_tokens == 4096
        assert cfg.temperature == 0.3
        assert cfg.timeout == 30.0

    def test_partial_custom_values(self):
        """测试部分自定义值，其余使用默认"""
        cfg = DeepseekConfig(api_key="only-key", temperature=0.1)
        assert cfg.api_key == "only-key"
        assert cfg.temperature == 0.1
        assert cfg.base_url == "https://api.deepseek.com/v1"  # 默认值
        assert cfg.model == "deepseek-chat"  # 默认值


# ════════════════════════════════════════════════════════════════
# 2. Message 数据类
# ════════════════════════════════════════════════════════════════


class TestMessage:
    """消息类测试"""

    def test_user_message(self):
        msg = Message(role="user", content="你好")
        assert msg.role == "user"
        assert msg.content == "你好"

    def test_system_message(self):
        msg = Message(role="system", content="你是专家")
        assert msg.role == "system"
        assert msg.content == "你是专家"

    def test_assistant_message(self):
        msg = Message(role="assistant", content="回答内容")
        assert msg.role == "assistant"
        assert msg.content == "回答内容"

    def test_empty_content(self):
        msg = Message(role="user", content="")
        assert msg.role == "user"
        assert msg.content == ""


# ════════════════════════════════════════════════════════════════
# 3. DeepseekResponse 数据类
# ════════════════════════════════════════════════════════════════


class TestDeepseekResponse:
    """响应类测试"""

    def test_full_response(self):
        resp = DeepseekResponse(
            content="分析结果",
            model="deepseek-chat",
            usage={"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30},
            finish_reason="stop",
        )
        assert resp.content == "分析结果"
        assert resp.model == "deepseek-chat"
        assert resp.usage["prompt_tokens"] == 10
        assert resp.usage["completion_tokens"] == 20
        assert resp.finish_reason == "stop"
        assert resp.created_at is not None

    def test_response_with_empty_usage(self):
        """测试 usage 为空字典的情况"""
        resp = DeepseekResponse(
            content="结果",
            model="deepseek-chat",
            usage={},
            finish_reason="stop",
        )
        assert resp.content == "结果"
        assert resp.usage == {}

    def test_response_with_length_finish_reason(self):
        """测试 finish_reason 为 length"""
        resp = DeepseekResponse(
            content="内容被截断",
            model="deepseek-chat",
            usage={"prompt_tokens": 100, "completion_tokens": 2048},
            finish_reason="length",
        )
        assert resp.finish_reason == "length"


# ════════════════════════════════════════════════════════════════
# 4. 系统提示词常量
# ════════════════════════════════════════════════════════════════


class TestSystemPrompts:
    """系统提示词测试"""

    def test_bazi_prompt_not_empty(self):
        assert len(BAZI_SYSTEM_PROMPT) > 50
        assert "命理" in BAZI_SYSTEM_PROMPT or "八字" in BAZI_SYSTEM_PROMPT

    def test_bazi_prompt_contains_keywords(self):
        assert "五行" in BAZI_SYSTEM_PROMPT or "神煞" in BAZI_SYSTEM_PROMPT or "大运" in BAZI_SYSTEM_PROMPT

    def test_qimen_prompt_not_empty(self):
        assert len(QIMEN_SYSTEM_PROMPT) > 50
        assert "奇门" in QIMEN_SYSTEM_PROMPT

    def test_qimen_prompt_contains_keywords(self):
        assert "九宫" in QIMEN_SYSTEM_PROMPT or "八门" in QIMEN_SYSTEM_PROMPT or "九星" in QIMEN_SYSTEM_PROMPT

    def test_prompts_are_different(self):
        assert BAZI_SYSTEM_PROMPT != QIMEN_SYSTEM_PROMPT


# ════════════════════════════════════════════════════════════════
# 5. DeepseekClient 客户端
# ════════════════════════════════════════════════════════════════


class TestDeepseekClientInit:
    """客户端初始化测试"""

    def test_init_with_default_config(self):
        client = DeepseekClient()
        assert client.config is not None
        assert isinstance(client.config, DeepseekConfig)
        assert client._client is None

    def test_init_with_custom_config(self):
        cfg = DeepseekConfig(api_key="custom-key", model="deepseek-reasoner")
        client = DeepseekClient(cfg)
        assert client.config.api_key == "custom-key"
        assert client.config.model == "deepseek-reasoner"
        assert client._client is None

    def test_init_with_none_config(self):
        """测试传入 None 时使用默认配置"""
        client = DeepseekClient(None)
        assert isinstance(client.config, DeepseekConfig)
        assert client._client is None


class TestDeepseekClientGetClient:
    """_get_client 方法测试"""

    @pytest.mark.asyncio
    async def test_creates_client_with_correct_headers(self):
        """测试 _get_client 创建带正确 headers 的 AsyncClient"""
        with patch("tengod.deepseek_adapter.httpx") as mock_httpx:
            mock_async_client = AsyncMock()
            mock_async_client.is_closed = False
            mock_httpx.AsyncClient.return_value = mock_async_client

            client = DeepseekClient(DeepseekConfig(api_key="test-key", timeout=30.0))
            result = await client._get_client()

            mock_httpx.AsyncClient.assert_called_once_with(
                base_url="https://api.deepseek.com/v1",
                headers={
                    "Authorization": "Bearer test-key",
                    "Content-Type": "application/json",
                },
                timeout=30.0,
            )
            assert result is mock_async_client

    @pytest.mark.asyncio
    async def test_reuses_existing_client(self):
        """测试 _get_client 复用已有客户端"""
        mock_client = AsyncMock()
        mock_client.is_closed = False

        client = DeepseekClient()
        client._client = mock_client

        result = await client._get_client()
        assert result is mock_client

    @pytest.mark.asyncio
    async def test_recreates_closed_client(self):
        """测试 _get_client 在客户端关闭后重新创建"""
        old_client = AsyncMock()
        old_client.is_closed = True

        with patch("tengod.deepseek_adapter.httpx") as mock_httpx:
            new_client = AsyncMock()
            new_client.is_closed = False
            mock_httpx.AsyncClient.return_value = new_client

            client = DeepseekClient()
            client._client = old_client

            result = await client._get_client()
            assert result is new_client

    @pytest.mark.asyncio
    async def test_recreates_when_none_client(self):
        """测试 _get_client 在 _client 为 None 时创建"""
        with patch("tengod.deepseek_adapter.httpx") as mock_httpx:
            new_client = AsyncMock()
            new_client.is_closed = False
            mock_httpx.AsyncClient.return_value = new_client

            client = DeepseekClient()
            result = await client._get_client()
            assert result is new_client


class TestDeepseekClientClose:
    """close 方法测试"""

    @pytest.mark.asyncio
    async def test_close_active_client(self):
        """测试关闭活跃客户端"""
        mock_client = AsyncMock()
        mock_client.is_closed = False

        client = DeepseekClient()
        client._client = mock_client

        await client.close()
        mock_client.aclose.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_close_none_client(self):
        """测试 _client 为 None 时关闭不报错"""
        client = DeepseekClient()
        client._client = None
        await client.close()  # 不应抛出异常

    @pytest.mark.asyncio
    async def test_close_already_closed_client(self):
        """测试关闭已关闭的客户端不重复关闭"""
        mock_client = AsyncMock()
        mock_client.is_closed = True

        client = DeepseekClient()
        client._client = mock_client

        await client.close()
        mock_client.aclose.assert_not_called()


class TestDeepseekClientChat:
    """chat 方法测试"""

    @pytest.mark.asyncio
    async def test_chat_basic(self):
        """测试基本的 chat 调用"""
        mock_resp = _make_mock_response(content="测试响应")
        mock_httpx = _make_mock_httpx_client(post_return=mock_resp)

        client = DeepseekClient(DeepseekConfig(api_key="test"))
        client._client = mock_httpx

        response = await client.chat([Message(role="user", content="你好")])

        assert response.content == "测试响应"
        assert response.model == "deepseek-chat"
        assert response.usage["completion_tokens"] == 10
        assert response.finish_reason == "stop"

    @pytest.mark.asyncio
    async def test_chat_with_system_prompt(self):
        """测试带系统提示词的 chat"""
        mock_resp = _make_mock_response(content="ok")
        mock_httpx = _make_mock_httpx_client(post_return=mock_resp)

        client = DeepseekClient(DeepseekConfig(api_key="test"))
        client._client = mock_httpx

        await client.chat(
            [Message(role="user", content="分析")],
            system_prompt="你是命理专家",
        )

        call_args = mock_httpx.post.call_args
        payload = call_args.kwargs["json"]
        assert payload["messages"][0]["role"] == "system"
        assert payload["messages"][0]["content"] == "你是命理专家"

    @pytest.mark.asyncio
    async def test_chat_with_custom_temperature_and_max_tokens(self):
        """测试自定义 temperature 和 max_tokens"""
        mock_resp = _make_mock_response(content="ok")
        mock_httpx = _make_mock_httpx_client(post_return=mock_resp)

        client = DeepseekClient(DeepseekConfig(api_key="test"))
        client._client = mock_httpx

        await client.chat(
            [Message(role="user", content="测试")],
            temperature=0.2,
            max_tokens=512,
        )

        call_args = mock_httpx.post.call_args
        payload = call_args.kwargs["json"]
        assert payload["temperature"] == 0.2
        assert payload["max_tokens"] == 512

    @pytest.mark.asyncio
    async def test_chat_uses_config_values_when_not_provided(self):
        """测试未提供参数时使用配置值"""
        mock_resp = _make_mock_response(content="ok")
        mock_httpx = _make_mock_httpx_client(post_return=mock_resp)

        client = DeepseekClient(DeepseekConfig(api_key="test", temperature=0.9, max_tokens=1024))
        client._client = mock_httpx

        await client.chat([Message(role="user", content="测试")])

        call_args = mock_httpx.post.call_args
        payload = call_args.kwargs["json"]
        assert payload["temperature"] == 0.9
        assert payload["max_tokens"] == 1024

    @pytest.mark.asyncio
    async def test_chat_with_empty_messages(self):
        """测试空消息列表"""
        mock_resp = _make_mock_response(content="ok")
        mock_httpx = _make_mock_httpx_client(post_return=mock_resp)

        client = DeepseekClient(DeepseekConfig(api_key="test"))
        client._client = mock_httpx

        response = await client.chat([])
        assert response.content == "ok"

    @pytest.mark.asyncio
    async def test_chat_payload_endpoint(self):
        """测试 chat 请求发送到正确的端点"""
        mock_resp = _make_mock_response(content="ok")
        mock_httpx = _make_mock_httpx_client(post_return=mock_resp)

        client = DeepseekClient(DeepseekConfig(api_key="test"))
        client._client = mock_httpx

        await client.chat([Message(role="user", content="测试")])

        mock_httpx.post.assert_called_once()
        call_args = mock_httpx.post.call_args
        assert call_args.args[0] == "/chat/completions"

    @pytest.mark.asyncio
    async def test_chat_without_usage_field(self):
        """测试 API 响应中缺少 usage 字段"""
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {
            "choices": [{"message": {"content": "ok"}, "finish_reason": "stop"}],
            "model": "deepseek-chat",
            # 没有 usage 字段
        }

        mock_httpx = _make_mock_httpx_client(post_return=mock_resp)
        client = DeepseekClient(DeepseekConfig(api_key="test"))
        client._client = mock_httpx

        response = await client.chat([Message(role="user", content="测试")])
        assert response.content == "ok"
        assert response.usage == {}

    @pytest.mark.asyncio
    async def test_chat_without_finish_reason(self):
        """测试 API 响应中缺少 finish_reason 字段"""
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {
            "choices": [{"message": {"content": "ok"}}],
            "model": "deepseek-chat",
            "usage": {},
        }

        mock_httpx = _make_mock_httpx_client(post_return=mock_resp)
        client = DeepseekClient(DeepseekConfig(api_key="test"))
        client._client = mock_httpx

        response = await client.chat([Message(role="user", content="测试")])
        assert response.finish_reason == "stop"

    @pytest.mark.asyncio
    async def test_chat_httpx_none_import_error(self):
        """测试 httpx 未安装时抛出 ImportError"""
        with patch("tengod.deepseek_adapter.httpx", None):
            client = DeepseekClient(DeepseekConfig(api_key="test"))
            with pytest.raises(ImportError, match="httpx is required"):
                await client.chat([Message(role="user", content="测试")])

    @pytest.mark.asyncio
    async def test_chat_http_status_error(self):
        """测试 HTTP 错误时抛出 RuntimeError"""
        import httpx as real_httpx

        mock_resp = MagicMock()
        mock_resp.raise_for_status.side_effect = real_httpx.HTTPStatusError(
            "error", request=MagicMock(), response=MagicMock(status_code=401, text="Unauthorized")
        )

        mock_httpx = _make_mock_httpx_client(post_return=mock_resp)
        client = DeepseekClient(DeepseekConfig(api_key="test"))
        client._client = mock_httpx

        with pytest.raises(RuntimeError, match="Deepseek API error"):
            await client.chat([Message(role="user", content="测试")])

    @pytest.mark.asyncio
    async def test_chat_generic_exception(self):
        """测试通用异常时抛出 RuntimeError"""
        mock_httpx = AsyncMock()
        mock_httpx.is_closed = False
        mock_httpx.post = AsyncMock(side_effect=ValueError("unexpected error"))

        client = DeepseekClient(DeepseekConfig(api_key="test"))
        client._client = mock_httpx

        with pytest.raises(RuntimeError, match="Deepseek request failed"):
            await client.chat([Message(role="user", content="测试")])


class TestDeepseekClientStreamChat:
    """stream_chat 方法测试"""

    def _make_stream_lines(self, *lines):
        """创建模拟流式响应的行迭代器"""
        async def _aiter_lines():
            for line in lines:
                yield line

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.aiter_lines = _aiter_lines
        return mock_response

    def _make_stream_context_manager(self, lines):
        """创建模拟 stream 上下文管理器"""
        mock_response = self._make_stream_lines(*lines)

        class _AsyncCtxManager:
            async def __aenter__(self):
                return mock_response

            async def __aexit__(self, *args):
                pass

        return _AsyncCtxManager()

    @pytest.mark.asyncio
    async def test_stream_chat_yields_content(self):
        """测试流式聊天正常产出内容"""
        lines = [
            'data: {"choices":[{"delta":{"content":"你好"}}]}',
            'data: {"choices":[{"delta":{"content":"世界"}}]}',
            'data: [DONE]',
        ]
        ctx_manager = self._make_stream_context_manager(lines)

        mock_httpx = AsyncMock()
        mock_httpx.is_closed = False
        mock_httpx.stream = MagicMock(return_value=ctx_manager)

        client = DeepseekClient(DeepseekConfig(api_key="test"))
        client._client = mock_httpx

        chunks = []
        async for chunk in client.stream_chat([Message(role="user", content="你好")]):
            chunks.append(chunk)

        assert chunks == ["你好", "世界"]

    @pytest.mark.asyncio
    async def test_stream_chat_with_system_prompt(self):
        """测试带系统提示词的流式聊天"""
        lines = [
            'data: {"choices":[{"delta":{"content":"分析"}}]}',
            'data: [DONE]',
        ]
        ctx_manager = self._make_stream_context_manager(lines)

        mock_httpx = AsyncMock()
        mock_httpx.is_closed = False
        mock_httpx.stream = MagicMock(return_value=ctx_manager)

        client = DeepseekClient(DeepseekConfig(api_key="test"))
        client._client = mock_httpx

        chunks = []
        async for chunk in client.stream_chat(
            [Message(role="user", content="测试")],
            system_prompt="你是专家",
        ):
            chunks.append(chunk)

        assert chunks == ["分析"]

        # 验证系统提示词被包含在请求中
        call_args = mock_httpx.stream.call_args
        payload = call_args.kwargs["json"]
        assert payload["messages"][0]["role"] == "system"
        assert payload["messages"][0]["content"] == "你是专家"

    @pytest.mark.asyncio
    async def test_stream_chat_handles_done_marker(self):
        """测试流式聊天正确处理 [DONE] 标记"""
        lines = [
            'data: {"choices":[{"delta":{"content":"结果"}}]}',
            'data: [DONE]',
            'data: {"choices":[{"delta":{"content":"不应出现"}}]}',  # DONE 后不再处理
        ]
        ctx_manager = self._make_stream_context_manager(lines)

        mock_httpx = AsyncMock()
        mock_httpx.is_closed = False
        mock_httpx.stream = MagicMock(return_value=ctx_manager)

        client = DeepseekClient(DeepseekConfig(api_key="test"))
        client._client = mock_httpx

        chunks = []
        async for chunk in client.stream_chat([Message(role="user", content="测试")]):
            chunks.append(chunk)

        assert chunks == ["结果"]

    @pytest.mark.asyncio
    async def test_stream_chat_handles_json_decode_error(self):
        """测试流式聊天处理 JSON 解码错误"""
        lines = [
            'data: {"choices":[{"delta":{"content":"正常"}}]}',
            'data: not-valid-json',
            'data: {"choices":[{"delta":{"content":"继续"}}]}',
            'data: [DONE]',
        ]
        ctx_manager = self._make_stream_context_manager(lines)

        mock_httpx = AsyncMock()
        mock_httpx.is_closed = False
        mock_httpx.stream = MagicMock(return_value=ctx_manager)

        client = DeepseekClient(DeepseekConfig(api_key="test"))
        client._client = mock_httpx

        chunks = []
        async for chunk in client.stream_chat([Message(role="user", content="测试")]):
            chunks.append(chunk)

        assert chunks == ["正常", "继续"]

    @pytest.mark.asyncio
    async def test_stream_chat_handles_empty_delta_content(self):
        """测试流式聊天处理空的 delta content"""
        lines = [
            'data: {"choices":[{"delta":{"content":""}}]}',
            'data: {"choices":[{"delta":{}}]}',
            'data: {"choices":[{"delta":{"content":"有效"}}]}',
            'data: [DONE]',
        ]
        ctx_manager = self._make_stream_context_manager(lines)

        mock_httpx = AsyncMock()
        mock_httpx.is_closed = False
        mock_httpx.stream = MagicMock(return_value=ctx_manager)

        client = DeepseekClient(DeepseekConfig(api_key="test"))
        client._client = mock_httpx

        chunks = []
        async for chunk in client.stream_chat([Message(role="user", content="测试")]):
            chunks.append(chunk)

        assert chunks == ["有效"]

    @pytest.mark.asyncio
    async def test_stream_chat_empty_chunks(self):
        """测试流式聊天只有空内容时不产出"""
        lines = [
            'data: {"choices":[{"delta":{"content":""}}]}',
            'data: [DONE]',
        ]
        ctx_manager = self._make_stream_context_manager(lines)

        mock_httpx = AsyncMock()
        mock_httpx.is_closed = False
        mock_httpx.stream = MagicMock(return_value=ctx_manager)

        client = DeepseekClient(DeepseekConfig(api_key="test"))
        client._client = mock_httpx

        chunks = []
        async for chunk in client.stream_chat([Message(role="user", content="测试")]):
            chunks.append(chunk)

        assert chunks == []

    @pytest.mark.asyncio
    async def test_stream_chat_non_data_lines(self):
        """测试流式聊天忽略非 data: 开头的行"""
        lines = [
            'data: {"choices":[{"delta":{"content":"有效"}}]}',
            ': ping',
            'data: [DONE]',
        ]
        ctx_manager = self._make_stream_context_manager(lines)

        mock_httpx = AsyncMock()
        mock_httpx.is_closed = False
        mock_httpx.stream = MagicMock(return_value=ctx_manager)

        client = DeepseekClient(DeepseekConfig(api_key="test"))
        client._client = mock_httpx

        chunks = []
        async for chunk in client.stream_chat([Message(role="user", content="测试")]):
            chunks.append(chunk)

        assert chunks == ["有效"]

    @pytest.mark.asyncio
    async def test_stream_chat_httpx_none(self):
        """测试 httpx 未安装时流式聊天抛出 ImportError"""
        with patch("tengod.deepseek_adapter.httpx", None):
            client = DeepseekClient(DeepseekConfig(api_key="test"))
            with pytest.raises(ImportError, match="httpx is required"):
                async for _ in client.stream_chat([Message(role="user", content="测试")]):
                    pass

    @pytest.mark.asyncio
    async def test_stream_chat_generic_exception(self):
        """测试流式聊天的通用异常"""
        mock_httpx = AsyncMock()
        mock_httpx.is_closed = False
        mock_httpx.stream.side_effect = ValueError("stream error")

        client = DeepseekClient(DeepseekConfig(api_key="test"))
        client._client = mock_httpx

        with pytest.raises(RuntimeError, match="Deepseek stream error"):
            async for _ in client.stream_chat([Message(role="user", content="测试")]):
                pass

    @pytest.mark.asyncio
    async def test_stream_chat_payload_flags(self):
        """测试流式聊天请求中包含 stream: True"""
        lines = ['data: [DONE]']
        ctx_manager = self._make_stream_context_manager(lines)

        mock_httpx = AsyncMock()
        mock_httpx.is_closed = False
        mock_httpx.stream = MagicMock(return_value=ctx_manager)

        client = DeepseekClient(DeepseekConfig(api_key="test"))
        client._client = mock_httpx

        async for _ in client.stream_chat([Message(role="user", content="测试")]):
            pass

        call_args = mock_httpx.stream.call_args
        assert call_args.args[0] == "POST"
        assert call_args.args[1] == "/chat/completions"
        assert call_args.kwargs["json"]["stream"] is True


# ════════════════════════════════════════════════════════════════
# 6. get_client 单例
# ════════════════════════════════════════════════════════════════


class TestGetClient:
    """get_client 单例测试"""

    def test_returns_singleton(self):
        """测试 get_client 返回同一个实例"""
        import tengod.deepseek_adapter as adapter
        adapter._client = None

        c1 = get_client()
        c2 = get_client()
        assert c1 is c2

    def test_returns_different_after_reset(self):
        """测试全局变量重置后返回新实例"""
        import tengod.deepseek_adapter as adapter
        adapter._client = None

        c1 = get_client()
        adapter._client = None
        c2 = get_client()
        assert c1 is not c2

    def test_returns_instance_type(self):
        """测试返回类型是 DeepseekClient"""
        import tengod.deepseek_adapter as adapter
        adapter._client = None

        client = get_client()
        assert isinstance(client, DeepseekClient)


# ════════════════════════════════════════════════════════════════
# 7. _format_bazi 格式化函数
# ════════════════════════════════════════════════════════════════


class TestFormatBazi:
    """_format_bazi 函数测试"""

    def test_full_data(self):
        """测试完整八字数据"""
        data = {
            "pillars": {"year": "甲子", "month": "丙寅", "day": "戊午", "hour": "庚申"},
            "wuxing": "木2火1土1金1水3",
            "geju": "正官格",
            "shensha": "天乙贵人, 文昌",
        }
        result = _format_bazi(data)
        assert "年柱：甲子" in result
        assert "月柱：丙寅" in result
        assert "日柱：戊午" in result
        assert "时柱：庚申" in result
        assert "五行：木2火1土1金1水3" in result
        assert "格局：正官格" in result
        assert "神煞：天乙贵人, 文昌" in result

    def test_only_pillars(self):
        """测试仅包含四柱数据"""
        data = {"pillars": {"year": "甲子", "month": "丙寅", "day": "戊午", "hour": "庚申"}}
        result = _format_bazi(data)
        assert "年柱：甲子" in result
        assert "月柱：丙寅" in result
        assert "日柱：戊午" in result
        assert "时柱：庚申" in result
        assert "五行" not in result
        assert "格局" not in result

    def test_only_wuxing(self):
        """测试仅包含五行数据"""
        data = {"wuxing": "木2火1土1金1水3"}
        result = _format_bazi(data)
        assert "五行：木2火1土1金1水3" in result
        assert "年柱" not in result

    def test_only_geju(self):
        """测试仅包含格局数据"""
        data = {"geju": "正官格"}
        result = _format_bazi(data)
        assert "格局：正官格" in result

    def test_only_shensha(self):
        """测试仅包含神煞数据"""
        data = {"shensha": "天乙贵人, 文昌"}
        result = _format_bazi(data)
        assert "神煞：天乙贵人, 文昌" in result

    def test_empty_data(self):
        """测试空数据"""
        result = _format_bazi({})
        assert result == ""

    def test_partial_pillars(self):
        """测试部分四柱数据"""
        data = {"pillars": {"year": "甲子", "day": "戊午"}}
        result = _format_bazi(data)
        assert "年柱：甲子" in result
        assert "月柱：" in result
        assert "日柱：戊午" in result
        assert "时柱：" in result

    def test_pillars_empty_dict(self):
        """测试空四柱字典"""
        data = {"pillars": {}}
        result = _format_bazi(data)
        assert "年柱：" in result
        assert "月柱：" in result
        assert "日柱：" in result
        assert "时柱：" in result

    def test_line_order(self):
        """测试输出行顺序正确（年柱在前）"""
        data = {"pillars": {"year": "甲子"}, "wuxing": "水"}
        result = _format_bazi(data)
        lines = result.split("\n")
        assert lines[0].startswith("年柱")
        # 五行在年柱之后
        assert any("五行" in l for l in lines)


# ════════════════════════════════════════════════════════════════
# 8. analyze_bazi 异步函数
# ════════════════════════════════════════════════════════════════


class TestAnalyzeBazi:
    """analyze_bazi 函数测试"""

    @pytest.mark.asyncio
    async def test_analyze_bazi_returns_content(self):
        """测试 analyze_bazi 返回分析内容"""
        mock_response = DeepseekResponse(
            content="命盘分析结果",
            model="deepseek-chat",
            usage={},
            finish_reason="stop",
        )

        mock_client = AsyncMock()
        mock_client.chat = AsyncMock(return_value=mock_response)

        with patch("tengod.deepseek_adapter.get_client", return_value=mock_client):
            bazi_data = {
                "pillars": {"year": "甲子", "month": "丙寅", "day": "戊午", "hour": "庚申"},
                "wuxing": "木2火1",
            }
            result = await analyze_bazi(bazi_data, "事业如何？")
            assert result == "命盘分析结果"

    @pytest.mark.asyncio
    async def test_analyze_bazi_calls_chat_with_system_prompt(self):
        """测试 analyze_bazi 使用 BAZI_SYSTEM_PROMPT"""
        mock_response = DeepseekResponse(
            content="结果",
            model="deepseek-chat",
            usage={},
            finish_reason="stop",
        )

        mock_client = AsyncMock()
        mock_client.chat = AsyncMock(return_value=mock_response)

        with patch("tengod.deepseek_adapter.get_client", return_value=mock_client):
            await analyze_bazi({"pillars": {"year": "甲子"}}, "运势如何？")

            mock_client.chat.assert_awaited_once()
            call_args = mock_client.chat.call_args
            assert call_args.kwargs["system_prompt"] == BAZI_SYSTEM_PROMPT

    @pytest.mark.asyncio
    async def test_analyze_bazi_formats_question(self):
        """测试 analyze_bazi 正确格式化问题和数据"""
        mock_response = DeepseekResponse(
            content="结果",
            model="deepseek-chat",
            usage={},
            finish_reason="stop",
        )

        mock_client = AsyncMock()
        mock_client.chat = AsyncMock(return_value=mock_response)

        with patch("tengod.deepseek_adapter.get_client", return_value=mock_client):
            await analyze_bazi(
                {"pillars": {"year": "甲子", "day": "戊午"}, "wuxing": "木"},
                "事业如何？",
            )

            mock_client.chat.assert_awaited_once()
            call_args = mock_client.chat.call_args
            messages = call_args.args[0]
            assert len(messages) == 1
            assert messages[0].role == "user"
            assert "八字命盘数据" in messages[0].content
            assert "年柱：甲子" in messages[0].content
            assert "事业如何？" in messages[0].content


# ════════════════════════════════════════════════════════════════
# 9. 边界情况与集成测试
# ════════════════════════════════════════════════════════════════


class TestEdgeCases:
    """边界情况测试"""

    def test_config_with_empty_api_key(self):
        """测试 api_key 为空字符串"""
        cfg = DeepseekConfig(api_key="")
        assert cfg.api_key == ""

    @pytest.mark.asyncio
    async def test_chat_with_multiple_messages(self):
        """测试多轮对话消息"""
        mock_resp = _make_mock_response(content="综合回答")
        mock_httpx = _make_mock_httpx_client(post_return=mock_resp)

        client = DeepseekClient(DeepseekConfig(api_key="test"))
        client._client = mock_httpx

        messages = [
            Message(role="user", content="第一问"),
            Message(role="assistant", content="第一答"),
            Message(role="user", content="第二问"),
        ]
        response = await client.chat(messages)
        assert response.content == "综合回答"

        # 验证所有消息都被发送
        call_args = mock_httpx.post.call_args
        payload = call_args.kwargs["json"]
        assert len(payload["messages"]) == 3

    @pytest.mark.asyncio
    async def test_stream_chat_with_multiple_delta_fields(self):
        """测试流式聊天中 delta 包含多个字段"""
        lines = [
            'data: {"choices":[{"delta":{"content":"文本","role":"assistant"}}]}',
            'data: [DONE]',
        ]
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()

        async def _aiter_lines():
            for line in lines:
                yield line

        mock_response.aiter_lines = _aiter_lines

        class _AsyncCtxManager:
            async def __aenter__(self):
                return mock_response

            async def __aexit__(self, *args):
                pass

        mock_httpx = AsyncMock()
        mock_httpx.is_closed = False
        mock_httpx.stream = MagicMock(return_value=_AsyncCtxManager())

        client = DeepseekClient(DeepseekConfig(api_key="test"))
        client._client = mock_httpx

        chunks = []
        async for chunk in client.stream_chat([Message(role="user", content="测试")]):
            chunks.append(chunk)

        assert chunks == ["文本"]

    @pytest.mark.asyncio
    async def test_stream_chat_no_data_prefix(self):
        """测试流式聊天中行不以 'data: ' 开头"""
        lines = [
            'data: {"choices":[{"delta":{"content":"有效"}}]}',
            'not-data: {"choices":[{"delta":{"content":"忽略"}}]}',
            'data: [DONE]',
        ]
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()

        async def _aiter_lines():
            for line in lines:
                yield line

        mock_response.aiter_lines = _aiter_lines

        class _AsyncCtxManager:
            async def __aenter__(self):
                return mock_response

            async def __aexit__(self, *args):
                pass

        mock_httpx = AsyncMock()
        mock_httpx.is_closed = False
        mock_httpx.stream = MagicMock(return_value=_AsyncCtxManager())

        client = DeepseekClient(DeepseekConfig(api_key="test"))
        client._client = mock_httpx

        chunks = []
        async for chunk in client.stream_chat([Message(role="user", content="测试")]):
            chunks.append(chunk)

        assert chunks == ["有效"]

    @pytest.mark.asyncio
    async def test_chat_with_zero_temperature(self):
        """测试 temperature 为 0 时，0 是 falsy，使用配置默认值"""
        mock_resp = _make_mock_response(content="ok")
        mock_httpx = _make_mock_httpx_client(post_return=mock_resp)

        client = DeepseekClient(DeepseekConfig(api_key="test"))
        client._client = mock_httpx

        await client.chat([Message(role="user", content="测试")], temperature=0.0)

        call_args = mock_httpx.post.call_args
        payload = call_args.kwargs["json"]
        # 0.0 is falsy, so `0.0 or self.config.temperature` → 0.7
        assert payload["temperature"] == 0.7

    @pytest.mark.asyncio
    async def test_chat_with_zero_max_tokens(self):
        """测试 max_tokens 为 0 时，0 是 falsy，使用配置默认值"""
        mock_resp = _make_mock_response(content="ok")
        mock_httpx = _make_mock_httpx_client(post_return=mock_resp)

        client = DeepseekClient(DeepseekConfig(api_key="test"))
        client._client = mock_httpx

        await client.chat([Message(role="user", content="测试")], max_tokens=0)

        call_args = mock_httpx.post.call_args
        payload = call_args.kwargs["json"]
        # 0 is falsy, so `0 or self.config.max_tokens` → 2048
        assert payload["max_tokens"] == 2048