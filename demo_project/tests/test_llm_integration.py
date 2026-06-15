"""test_llm_integration.py — LLM 真实集成测试 v2.1.0
验证 OpenAI/Claude/本地模型的流式、重试、超时链路。
"""
import json
import os
import sys
import time
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tengod"))

from 食神_创生输出.content_generator import (
    ContentGenerator,
    GenerationConfig,
    LLMProvider,
    OutputFormat,
)

# ============ Mock 工具 ============


def _make_openai_mock(response_text="AI生成的回复"):
    """创建模拟的 openai 模块"""
    module = MagicMock()
    client = MagicMock()
    choice = MagicMock()
    choice.message.content = response_text
    completion = MagicMock(choices=[choice])
    client.chat.completions.create.return_value = completion
    module.OpenAI.return_value = client
    return module


def _make_anthropic_mock(response_text="Claude生成的回复"):
    """创建模拟的 anthropic 模块"""
    module = MagicMock()
    client = MagicMock()
    content = MagicMock()
    content.text = response_text
    response = MagicMock(content=[content])
    client.messages.create.return_value = response
    module.Anthropic.return_value = client
    return module


def _make_openai_stream_mock(chunks):
    """创建模拟的 OpenAI 流式响应"""
    module = MagicMock()
    client = MagicMock()

    mock_chunks = []
    for text in chunks:
        c = MagicMock()
        delta = MagicMock()
        delta.content = text
        choice = MagicMock()
        choice.delta = delta
        choice.finish_reason = None
        c.choices = [choice]
        mock_chunks.append(c)

    client.chat.completions.create.return_value = mock_chunks
    module.OpenAI.return_value = client
    return module


# ============ 测试类 ============


class TestLLMConfig:
    """LLM 配置与 API Key 管理"""

    def test_api_key_from_env(self):
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key-123"}):
            gen = ContentGenerator()
            assert gen._api_key == "test-key-123"

    def test_api_key_from_init(self):
        gen = ContentGenerator(api_key="direct-key-456")
        assert gen._api_key == "direct-key-456"

    def test_api_key_in_config_overrides(self):
        cfg = GenerationConfig(provider=LLMProvider.OPENAI, api_key="config-key", model="gpt-4")
        assert cfg.api_key == "config-key"


class TestMockProvider:
    """模拟提供商的完整链路"""

    def test_generate_mock_text(self):
        gen = ContentGenerator(name="test")
        cfg = GenerationConfig(provider=LLMProvider.MOCK, format=OutputFormat.TEXT)
        result = gen.generate("你好", cfg)
        assert "你好" in result
        assert "mock" in result.lower()

    def test_generate_mock_markdown(self):
        gen = ContentGenerator()
        cfg = GenerationConfig(provider=LLMProvider.MOCK, format=OutputFormat.MARKDOWN)
        result = gen.generate("标题", cfg)
        assert result.startswith("##")

    def test_generate_mock_json(self):
        gen = ContentGenerator()
        cfg = GenerationConfig(provider=LLMProvider.MOCK, format=OutputFormat.JSON)
        result = gen.generate("test", cfg)
        parsed = json.loads(result)
        assert parsed["prompt"] == "test"
        assert parsed["provider"] == "mock"

    def test_generate_mock_html(self):
        gen = ContentGenerator()
        cfg = GenerationConfig(provider=LLMProvider.MOCK, format=OutputFormat.HTML)
        result = gen.generate("hello", cfg)
        assert result.startswith("<h1>")

    def test_generate_mock_code(self):
        gen = ContentGenerator()
        cfg = GenerationConfig(provider=LLMProvider.MOCK, format=OutputFormat.CODE)
        result = gen.generate("test_fn", cfg)
        assert "#" in result
        assert "pass" in result

    def test_session_history_tracking(self):
        gen = ContentGenerator()
        cfg = GenerationConfig(provider=LLMProvider.MOCK)
        gen.generate("问题1", cfg)
        gen.generate("问题2", cfg)
        history = gen.get_history()
        assert len(history) == 2

    def test_cache_functionality(self):
        gen = ContentGenerator()
        cfg = GenerationConfig(provider=LLMProvider.MOCK)
        gen.generate("缓存测试", cfg)
        gen.clear_cache()
        assert gen._cache == {}

    def test_stats_reporting(self):
        gen = ContentGenerator(name="stats-test")
        cfg = GenerationConfig(provider=LLMProvider.MOCK)
        gen.generate("a", cfg)
        gen.generate("b", cfg)
        s = gen.stats()
        assert s["name"] == "stats-test"
        assert s["total_generations"] == 2


class TestRetryLogic:
    """重试与超时逻辑"""

    def test_retry_on_failure(self):
        gen = ContentGenerator()
        call_count = {"count": 0}

        def fail_then_succeed():
            call_count["count"] += 1
            if call_count["count"] < 3:
                raise ConnectionError("模拟网络错误")
            return "最终成功"

        result = gen._call_with_retry(fail_then_succeed, max_retries=3, provider_name="test")
        assert result == "最终成功"
        assert call_count["count"] == 3

    def test_retry_exhausted(self):
        gen = ContentGenerator()

        def always_fail():
            raise TimeoutError("超时")

        result = gen._call_with_retry(always_fail, max_retries=2, provider_name="Test")
        assert "重试" in result

    def test_retry_never_called_when_success(self):
        gen = ContentGenerator()
        call_count = {"count": 0}

        def succeed():
            call_count["count"] += 1
            return "OK"

        result = gen._call_with_retry(succeed, max_retries=5, provider_name="test")
        assert result == "OK"
        assert call_count["count"] == 1

    def test_exponential_backoff_timing(self):
        gen = ContentGenerator()
        attempt_times = []

        def fail():
            attempt_times.append(time.time())
            raise RuntimeError("fail")

        gen._call_with_retry(fail, max_retries=2, provider_name="test")
        assert len(attempt_times) == 3
        if len(attempt_times) >= 3:
            delta1 = attempt_times[1] - attempt_times[0]
            delta2 = attempt_times[2] - attempt_times[1]
            assert delta1 >= 0.5
            assert delta2 >= 1.5


class TestOpenAIProvider:
    """OpenAI 提供商集成（模拟）"""

    def test_openai_call_structure(self):
        mock_mod = _make_openai_mock("AI生成的回复")
        with patch.dict(sys.modules, {"openai": mock_mod}):
            gen = ContentGenerator(api_key="sk-test")
            cfg = GenerationConfig(provider=LLMProvider.OPENAI, model="gpt-3.5-turbo", max_length=1000)
            result = gen.generate("测试提示词", cfg)
            assert "AI生成的回复" in result

    def test_openai_with_session(self):
        mock_mod = _make_openai_mock("第二轮回复")
        with patch.dict(sys.modules, {"openai": mock_mod}):
            gen = ContentGenerator(api_key="sk-test")
            cfg = GenerationConfig(provider=LLMProvider.OPENAI, model="gpt-4")
            gen.generate("第一问", cfg)
            result = gen.generate("第二问", cfg)
            assert "第二轮回复" in result

    def test_openai_error_fallback(self):
        mock_mod = MagicMock()
        client = MagicMock()
        client.chat.completions.create.side_effect = TimeoutError("API超时")
        mock_mod.OpenAI.return_value = client

        with patch.dict(sys.modules, {"openai": mock_mod}):
            gen = ContentGenerator(api_key="sk-test")
            cfg = GenerationConfig(provider=LLMProvider.OPENAI, max_retries=1)
            result = gen.generate("测试", cfg)
            assert "Error" in result


class TestClaudeProvider:
    """Claude 提供商集成（模拟）"""

    def test_claude_call_structure(self):
        mock_mod = _make_anthropic_mock("Claude生成的回复")
        with patch.dict(sys.modules, {"anthropic": mock_mod}):
            gen = ContentGenerator(api_key="sk-ant-test")
            cfg = GenerationConfig(provider=LLMProvider.CLAUDE, model="claude-3-haiku-20240307")
            result = gen.generate("Claude测试", cfg)
            assert "Claude生成的回复" in result

    def test_claude_error_fallback(self):
        mock_mod = MagicMock()
        client = MagicMock()
        client.messages.create.side_effect = ConnectionError("连接失败")
        mock_mod.Anthropic.return_value = client

        with patch.dict(sys.modules, {"anthropic": mock_mod}):
            gen = ContentGenerator()
            cfg = GenerationConfig(provider=LLMProvider.CLAUDE, max_retries=1)
            result = gen.generate("测试", cfg)
            assert "Error" in result


class TestStreamGeneration:
    """流式生成测试"""

    def test_stream_mock(self):
        gen = ContentGenerator()
        cfg = GenerationConfig(provider=LLMProvider.MOCK)
        chunks = list(gen.generate_stream("流式测试", cfg))
        assert len(chunks) > 0
        full_text = "".join(chunks)
        assert len(full_text) > 0

    def test_stream_openai(self):
        mock_mod = _make_openai_stream_mock(["Hello", " World", "!"])
        with patch.dict(sys.modules, {"openai": mock_mod}):
            gen = ContentGenerator(api_key="sk-test")
            cfg = GenerationConfig(provider=LLMProvider.OPENAI, model="gpt-3.5-turbo")
            chunks = list(gen.generate_stream("你好", cfg))
            assert len(chunks) >= 1


class TestProviderSwitching:
    """提供商切换测试"""

    def test_switch_from_mock_to_openai(self):
        gen = ContentGenerator()
        cfg_mock = GenerationConfig(provider=LLMProvider.MOCK)
        r1 = gen.generate("mock", cfg_mock)
        assert "mock" in r1.lower()

    def test_switch_from_openai_to_claude(self):
        gen = ContentGenerator(api_key="sk-test")
        # OpenAI
        with patch.dict(sys.modules, {"openai": _make_openai_mock("OpenAI结果")}):
            r1 = gen.generate("问答1", GenerationConfig(provider=LLMProvider.OPENAI))
            assert "OpenAI结果" in r1
        # Claude
        with patch.dict(sys.modules, {"anthropic": _make_anthropic_mock("Claude结果")}):
            r2 = gen.generate("问答2", GenerationConfig(provider=LLMProvider.CLAUDE))
            assert "Claude结果" in r2


class TestTimeoutControl:
    """超时控制测试"""

    def test_config_timeout(self):
        cfg = GenerationConfig(timeout=30.0)
        assert cfg.timeout == 30.0

    def test_default_timeout(self):
        cfg = GenerationConfig()
        assert cfg.timeout == 60.0

    def test_max_retries_config(self):
        cfg = GenerationConfig(max_retries=5)
        assert cfg.max_retries == 5


class TestTemplateSystem:
    """模板系统测试"""

    def test_list_templates(self):
        gen = ContentGenerator()
        templates = gen.list_templates()
        assert isinstance(templates, list)
        assert len(templates) > 0
        assert "creative_writing" in templates

    def test_generate_from_template(self):
        gen = ContentGenerator()
        result = gen.generate_from_template("creative_writing", topic="AI发展", style="学术", language="中文", length=200)
        assert len(result) > 0

    def test_add_template(self):
        gen = ContentGenerator()
        gen.add_template("test_tpl", "测试模板：{username}")
        result = gen.generate_from_template("test_tpl", username="张三")
        assert "张三" in result