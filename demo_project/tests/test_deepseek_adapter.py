#!/usr/bin/env python3
"""
test_deepseek_adapter.py — Deepseek AI 适配器单元测试
覆盖：配置、消息构建、客户端管理、便捷函数
使用 mock 避免真实 API 调用
"""
import os
import sys
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

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


# ════════════════════════════════════════
# 1. 配置与数据类
# ════════════════════════════════════════

class TestDeepseekConfig:
    """配置类测试"""

    def test_default_config(self):
        cfg = DeepseekConfig()
        assert cfg.base_url == "https://api.deepseek.com/v1"
        assert cfg.model == "deepseek-chat"
        assert cfg.max_tokens == 2048
        assert cfg.temperature == 0.7
        assert cfg.timeout == 60.0

    def test_api_key_from_env(self, monkeypatch):
        monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key-123")
        cfg = DeepseekConfig()
        assert cfg.api_key == "test-key-123"

    def test_custom_config(self):
        cfg = DeepseekConfig(
            api_key="custom",
            model="deepseek-reasoner",
            max_tokens=4096,
            temperature=0.5
        )
        assert cfg.api_key == "custom"
        assert cfg.model == "deepseek-reasoner"
        assert cfg.max_tokens == 4096
        assert cfg.temperature == 0.5


class TestMessage:
    """消息类测试"""

    def test_message_creation(self):
        msg = Message(role="user", content="hello")
        assert msg.role == "user"
        assert msg.content == "hello"

    def test_system_message(self):
        msg = Message(role="system", content="system prompt")
        assert msg.role == "system"

    def test_assistant_message(self):
        msg = Message(role="assistant", content="response")
        assert msg.role == "assistant"


class TestDeepseekResponse:
    """响应类测试"""

    def test_response_creation(self):
        resp = DeepseekResponse(
            content="分析结果",
            model="deepseek-chat",
            usage={"prompt_tokens": 10, "completion_tokens": 20},
            finish_reason="stop"
        )
        assert resp.content == "分析结果"
        assert resp.model == "deepseek-chat"
        assert resp.usage["completion_tokens"] == 20
        assert resp.finish_reason == "stop"
        assert resp.created_at is not None


# ════════════════════════════════════════
# 2. 系统提示词
# ════════════════════════════════════════

class TestSystemPrompts:
    """系统提示词完整性"""

    def test_bazi_prompt_not_empty(self):
        assert len(BAZI_SYSTEM_PROMPT) > 50
        assert "命理" in BAZI_SYSTEM_PROMPT or "八字" in BAZI_SYSTEM_PROMPT

    def test_qimen_prompt_not_empty(self):
        assert len(QIMEN_SYSTEM_PROMPT) > 50
        assert "奇门" in QIMEN_SYSTEM_PROMPT


# ════════════════════════════════════════
# 3. 客户端管理
# ════════════════════════════════════════

class TestDeepseekClient:
    """客户端测试"""

    def test_init_with_default_config(self):
        client = DeepseekClient()
        assert client.config is not None
        assert client._client is None

    def test_init_with_custom_config(self):
        cfg = DeepseekConfig(api_key="custom")
        client = DeepseekClient(cfg)
        assert client.config.api_key == "custom"

    @pytest.mark.asyncio
    async def test_close_when_no_client(self):
        """无客户端时关闭不应报错"""
        client = DeepseekClient()
        await client.close()  # 不应抛出异常

    @pytest.mark.asyncio
    async def test_chat_with_mock(self):
        """使用 mock 测试 chat 方法"""
        # 准备 mock 响应
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {
            "choices": [
                {"message": {"content": "测试响应"}, "finish_reason": "stop"}
            ],
            "model": "deepseek-chat",
            "usage": {"prompt_tokens": 5, "completion_tokens": 10}
        }

        # mock httpx 客户端
        mock_httpx = AsyncMock()
        mock_httpx.post = AsyncMock(return_value=mock_response)
        mock_httpx.is_closed = False

        client = DeepseekClient(DeepseekConfig(api_key="test"))
        client._client = mock_httpx

        messages = [Message(role="user", content="你好")]
        response = await client.chat(messages)

        assert response.content == "测试响应"
        assert response.model == "deepseek-chat"
        assert response.usage["completion_tokens"] == 10

    @pytest.mark.asyncio
    async def test_chat_with_system_prompt(self):
        """测试带系统提示词的请求"""
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "ok"}, "finish_reason": "stop"}],
            "model": "deepseek-chat",
            "usage": {}
        }

        mock_httpx = AsyncMock()
        mock_httpx.post = AsyncMock(return_value=mock_response)
        mock_httpx.is_closed = False

        client = DeepseekClient(DeepseekConfig(api_key="test"))
        client._client = mock_httpx

        await client.chat(
            [Message(role="user", content="分析")],
            system_prompt="你是命理专家"
        )

        # 验证调用参数
        call_args = mock_httpx.post.call_args
        payload = call_args.kwargs["json"]
        assert payload["messages"][0]["role"] == "system"
        assert payload["messages"][0]["content"] == "你是命理专家"


# ════════════════════════════════════════
# 4. 便捷函数
# ════════════════════════════════════════

class TestConvenienceFunctions:
    """便捷函数测试"""

    def test_get_client_singleton(self):
        """get_client 应返回单例"""
        # 重置全局客户端
        import tengod.deepseek_adapter as adapter
        adapter._client = None

        c1 = get_client()
        c2 = get_client()
        assert c1 is c2

    def test_format_bazi_with_pillars(self):
        data = {
            "pillars": {
                "year": "甲子",
                "month": "丙寅",
                "day": "戊午",
                "hour": "庚申"
            }
        }
        result = _format_bazi(data)
        assert "年柱：甲子" in result
        assert "月柱：丙寅" in result
        assert "日柱：戊午" in result
        assert "时柱：庚申" in result

    def test_format_bazi_with_wuxing(self):
        data = {"wuxing": "木2火1土1金1水3"}
        result = _format_bazi(data)
        assert "五行：木2火1土1金1水3" in result

    def test_format_bazi_with_geju(self):
        data = {"geju": "正官格"}
        result = _format_bazi(data)
        assert "格局：正官格" in result

    def test_format_bazi_with_shensha(self):
        data = {"shensha": "天乙贵人, 文昌"}
        result = _format_bazi(data)
        assert "神煞：天乙贵人, 文昌" in result

    def test_format_bazi_empty(self):
        result = _format_bazi({})
        assert result == ""


# ════════════════════════════════════════
# 5. analyze_bazi 异步函数
# ════════════════════════════════════════

class TestAnalyzeBazi:
    """analyze_bazi 异步函数测试"""

    @pytest.mark.asyncio
    async def test_analyze_bazi_with_mock(self):
        """使用 mock 测试 analyze_bazi"""
        mock_response = DeepseekResponse(
            content="命盘分析结果",
            model="deepseek-chat",
            usage={},
            finish_reason="stop"
        )

        mock_client = AsyncMock()
        mock_client.chat = AsyncMock(return_value=mock_response)

        with patch("tengod.deepseek_adapter.get_client", return_value=mock_client):
            bazi_data = {
                "pillars": {"year": "甲子", "day": "戊午"},
                "wuxing": "木2火1"
            }
            result = await analyze_bazi(bazi_data, "事业如何？")

            assert result == "命盘分析结果"
            mock_client.chat.assert_awaited_once()
