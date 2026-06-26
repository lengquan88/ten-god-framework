"""
test_content_generator.py — ContentGenerator 模块全面测试
食神_创生输出/content_generator.py 的 pytest 测试套件。
"""

import json
import time
from unittest.mock import Mock, patch

import pytest

from tengod.食神_创生输出.content_generator import (
    ContentGenerator,
    GenerationConfig,
    LLMProvider,
    OutputFormat,
)


# ═══════════════════════════════════════════════════════════════
# 辅助 fixtures
# ═══════════════════════════════════════════════════════════════

@pytest.fixture
def gen():
    """返回一个默认 ContentGenerator 实例"""
    return ContentGenerator()


@pytest.fixture
def gen_named():
    """返回一个带自定义名称的 ContentGenerator 实例"""
    return ContentGenerator(name="test_gen")


@pytest.fixture
def gen_with_key():
    """返回一个带 API Key 的 ContentGenerator 实例"""
    return ContentGenerator(name="key_gen", api_key="sk-test-key")


@pytest.fixture
def mock_sleep():
    """Mock time.sleep 避免测试中的实际延迟"""
    with patch("time.sleep", return_value=None):
        yield


# ═══════════════════════════════════════════════════════════════
# OutputFormat 枚举测试
# ═══════════════════════════════════════════════════════════════

class TestOutputFormat:
    """OutputFormat 枚举值测试"""

    def test_all_values_present(self):
        assert OutputFormat.TEXT.value == "text"
        assert OutputFormat.MARKDOWN.value == "markdown"
        assert OutputFormat.JSON.value == "json"
        assert OutputFormat.HTML.value == "html"
        assert OutputFormat.CODE.value == "code"

    def test_enum_length(self):
        assert len(list(OutputFormat)) == 5

    def test_enum_is_enum(self):
        assert isinstance(OutputFormat.TEXT, OutputFormat)

    def test_enum_membership(self):
        for fmt in ["text", "markdown", "json", "html", "code"]:
            assert OutputFormat(fmt) is not None

    def test_enum_invalid_value(self):
        with pytest.raises(ValueError):
            OutputFormat("invalid")


# ═══════════════════════════════════════════════════════════════
# LLMProvider 枚举测试
# ═══════════════════════════════════════════════════════════════

class TestLLMProvider:
    """LLMProvider 枚举值测试"""

    def test_all_values_present(self):
        assert LLMProvider.MOCK.value == "mock"
        assert LLMProvider.OPENAI.value == "openai"
        assert LLMProvider.CLAUDE.value == "claude"
        assert LLMProvider.LOCAL.value == "local"
        assert LLMProvider.CUSTOM.value == "custom"

    def test_enum_length(self):
        assert len(list(LLMProvider)) == 5

    def test_enum_is_enum(self):
        assert isinstance(LLMProvider.MOCK, LLMProvider)

    def test_enum_membership(self):
        for prov in ["mock", "openai", "claude", "local", "custom"]:
            assert LLMProvider(prov) is not None

    def test_enum_invalid_value(self):
        with pytest.raises(ValueError):
            LLMProvider("invalid")


# ═══════════════════════════════════════════════════════════════
# GenerationConfig 数据类测试
# ═══════════════════════════════════════════════════════════════

class TestGenerationConfig:
    """GenerationConfig 数据类测试"""

    def test_default_creation(self):
        cfg = GenerationConfig()
        assert cfg.format == OutputFormat.TEXT
        assert cfg.max_length == 2000
        assert cfg.temperature == 0.7
        assert cfg.style == "default"
        assert cfg.language == "zh-CN"
        assert cfg.provider == LLMProvider.MOCK
        assert cfg.model == ""
        assert cfg.api_key == ""
        assert cfg.base_url == ""
        assert cfg.session_id == ""
        assert cfg.timeout == 60.0
        assert cfg.max_retries == 3
        assert cfg.extra == {}

    def test_custom_format(self):
        cfg = GenerationConfig(format=OutputFormat.MARKDOWN)
        assert cfg.format == OutputFormat.MARKDOWN

    def test_custom_provider(self):
        cfg = GenerationConfig(provider=LLMProvider.OPENAI)
        assert cfg.provider == LLMProvider.OPENAI

    def test_custom_max_length(self):
        cfg = GenerationConfig(max_length=500)
        assert cfg.max_length == 500

    def test_custom_temperature(self):
        cfg = GenerationConfig(temperature=0.3)
        assert cfg.temperature == 0.3

    def test_custom_model(self):
        cfg = GenerationConfig(model="gpt-4")
        assert cfg.model == "gpt-4"

    def test_custom_api_key(self):
        cfg = GenerationConfig(api_key="sk-custom")
        assert cfg.api_key == "sk-custom"

    def test_custom_base_url(self):
        cfg = GenerationConfig(base_url="https://custom.api.com")
        assert cfg.base_url == "https://custom.api.com"

    def test_custom_session_id(self):
        cfg = GenerationConfig(session_id="session-123")
        assert cfg.session_id == "session-123"

    def test_custom_timeout(self):
        cfg = GenerationConfig(timeout=30.0)
        assert cfg.timeout == 30.0

    def test_custom_max_retries(self):
        cfg = GenerationConfig(max_retries=5)
        assert cfg.max_retries == 5

    def test_custom_style_language(self):
        cfg = GenerationConfig(style="creative", language="en-US")
        assert cfg.style == "creative"
        assert cfg.language == "en-US"

    def test_extra_dict_default(self):
        cfg = GenerationConfig()
        assert isinstance(cfg.extra, dict)
        assert cfg.extra == {}

    def test_extra_dict_custom(self):
        cfg = GenerationConfig(extra={"foo": "bar"})
        assert cfg.extra == {"foo": "bar"}


# ═══════════════════════════════════════════════════════════════
# ContentGenerator __init__ 测试
# ═══════════════════════════════════════════════════════════════

class TestContentGeneratorInit:
    """ContentGenerator 初始化测试"""

    def test_default_name(self, gen):
        assert gen._name == "default"
        assert gen._cache == {}
        assert gen._history == []
        assert gen._api_key == ""
        assert gen._custom_generator is None
        assert gen._sessions == {}
        assert gen._token_counts == {}

    def test_custom_name(self, gen_named):
        assert gen_named._name == "test_gen"

    def test_with_api_key(self, gen_with_key):
        assert gen_with_key._api_key == "sk-test-key"

    def test_has_default_templates(self, gen):
        templates = gen._templates
        assert "creative_writing" in templates
        assert "technical_explanation" in templates
        assert "analysis_report" in templates
        assert "code_explanation" in templates
        assert "innovation_idea" in templates
        assert "knowledge_summary" in templates
        assert "qa_answer" in templates


# ═══════════════════════════════════════════════════════════════
# ContentGenerator set_api_key / set_custom_generator / register_template
# ═══════════════════════════════════════════════════════════════

class TestContentGeneratorSetters:
    """ContentGenerator setter 方法测试"""

    def test_set_api_key(self, gen):
        gen.set_api_key("new-key")
        assert gen._api_key == "new-key"

    def test_set_api_key_overwrite(self, gen_with_key):
        gen_with_key.set_api_key("updated-key")
        assert gen_with_key._api_key == "updated-key"

    def test_set_custom_generator(self, gen):
        func = Mock(return_value="custom output")
        gen.set_custom_generator(func)
        assert gen._custom_generator is func

    def test_register_template(self, gen):
        gen.register_template("my_template", "Hello {name}")
        assert "my_template" in gen._templates
        assert gen._templates["my_template"] == "Hello {name}"


# ═══════════════════════════════════════════════════════════════
# ContentGenerator _render_mock 测试
# ═══════════════════════════════════════════════════════════════

class TestRenderMock:
    """_render_mock 方法测试"""

    def test_text_format(self, gen):
        cfg = GenerationConfig(format=OutputFormat.TEXT)
        result = gen._render_mock("你好", cfg)
        assert "你好" in result
        assert "default" in result
        assert "mock" in result

    def test_text_format_custom_name(self, gen_named):
        cfg = GenerationConfig(format=OutputFormat.TEXT)
        result = gen_named._render_mock("测试", cfg)
        assert "测试" in result
        assert "test_gen" in result

    def test_markdown_format(self, gen):
        cfg = GenerationConfig(format=OutputFormat.MARKDOWN)
        result = gen._render_mock("标题", cfg)
        assert result.startswith("## 标题")
        assert "default" in result
        assert "模拟" in result

    def test_json_format(self, gen):
        cfg = GenerationConfig(format=OutputFormat.JSON)
        result = gen._render_mock("测试提示", cfg)
        parsed = json.loads(result)
        assert parsed["prompt"] == "测试提示"
        assert parsed["generator"] == "default"
        assert parsed["provider"] == "mock"
        assert "generated_at" in parsed

    def test_html_format(self, gen):
        cfg = GenerationConfig(format=OutputFormat.HTML)
        result = gen._render_mock("标题内容", cfg)
        assert result == "<h1>标题内容</h1><p>由 default 生成</p>"

    def test_code_format(self, gen):
        cfg = GenerationConfig(format=OutputFormat.CODE)
        result = gen._render_mock("注释", cfg)
        assert result == "# 注释\n# 由 default 生成\npass"


# ═══════════════════════════════════════════════════════════════
# ContentGenerator _call_with_retry 测试
# ═══════════════════════════════════════════════════════════════

class TestCallWithRetry:
    """_call_with_retry 方法测试"""

    def test_success_on_first_try(self, gen, mock_sleep):
        func = Mock(return_value="success")
        result = gen._call_with_retry(func, max_retries=3, provider_name="Test")
        assert result == "success"
        assert func.call_count == 1

    def test_success_after_retry(self, gen, mock_sleep):
        func = Mock(side_effect=[Exception("fail1"), Exception("fail2"), "success"])
        result = gen._call_with_retry(func, max_retries=3, provider_name="Test")
        assert result == "success"
        assert func.call_count == 3

    def test_all_retries_exhausted(self, gen, mock_sleep):
        func = Mock(side_effect=Exception("always fail"))
        result = gen._call_with_retry(func, max_retries=2, provider_name="Test")
        assert "Error" in result
        assert "Test" in result
        assert "重试" in result
        assert "always fail" in result
        assert func.call_count == 3  # max_retries + 1

    def test_zero_retries_failure(self, gen, mock_sleep):
        func = Mock(side_effect=Exception("fail"))
        result = gen._call_with_retry(func, max_retries=0, provider_name="Zero")
        assert "Error" in result
        assert "Zero" in result
        assert "fail" in result
        assert func.call_count == 1


# ═══════════════════════════════════════════════════════════════
# ContentGenerator generate 测试 (MOCK)
# ═══════════════════════════════════════════════════════════════

class TestGenerate:
    """generate 方法测试"""

    def test_generate_text_default(self, gen):
        result = gen.generate("你好")
        assert isinstance(result, str)
        assert "你好" in result

    def test_generate_text_format(self, gen):
        cfg = GenerationConfig(format=OutputFormat.TEXT)
        result = gen.generate("测试", cfg)
        assert "测试" in result
        assert "default" in result

    def test_generate_markdown_format(self, gen):
        cfg = GenerationConfig(format=OutputFormat.MARKDOWN)
        result = gen.generate("标题", cfg)
        assert result.startswith("## 标题")

    def test_generate_json_format(self, gen):
        cfg = GenerationConfig(format=OutputFormat.JSON)
        result = gen.generate("提示词", cfg)
        parsed = json.loads(result)
        assert parsed["prompt"] == "提示词"

    def test_generate_html_format(self, gen):
        cfg = GenerationConfig(format=OutputFormat.HTML)
        result = gen.generate("内容", cfg)
        assert result.startswith("<h1>内容</h1>")

    def test_generate_code_format(self, gen):
        cfg = GenerationConfig(format=OutputFormat.CODE)
        result = gen.generate("注释", cfg)
        assert result.startswith("# 注释")

    def test_generate_none_config(self, gen):
        result = gen.generate("测试", None)
        assert "测试" in result

    def test_generate_adds_to_history(self, gen):
        gen.generate("prompt1")
        history = gen.get_history()
        assert len(history) == 1
        entry = history[0]
        assert entry["prompt"] == "prompt1"
        assert "id" in entry
        assert "timestamp" in entry
        assert "length" in entry
        assert "est_tokens" in entry
        assert entry["format"] == "text"
        assert entry["provider"] == "mock"

    def test_generate_history_fields(self, gen):
        cfg = GenerationConfig(format=OutputFormat.MARKDOWN, provider=LLMProvider.MOCK)
        gen.generate("prompt2", cfg)
        entry = gen.get_history()[0]
        assert entry["prompt"] == "prompt2"
        assert entry["format"] == "markdown"
        assert entry["provider"] == "mock"
        assert len(entry["id"]) == 8
        assert entry["length"] > 0
        assert entry["est_tokens"] > 0

    def test_generate_no_session_id_in_history(self, gen):
        gen.generate("test")
        entry = gen.get_history()[0]
        assert entry["session_id"] == ""


# ═══════════════════════════════════════════════════════════════
# ContentGenerator generate 缓存测试
# ═══════════════════════════════════════════════════════════════

class TestGenerateCache:
    """generate 缓存测试"""

    def test_cache_hit(self, gen):
        cfg = GenerationConfig(format=OutputFormat.TEXT)
        result1 = gen.generate("cache test", cfg, use_cache=True)
        result2 = gen.generate("cache test", cfg, use_cache=True)
        assert result1 == result2
        # 缓存命中时 history 仍会追加，所以有 2 条
        assert len(gen.get_history()) == 2

    def test_cache_miss_then_hit(self, gen):
        cfg = GenerationConfig(format=OutputFormat.MARKDOWN)
        result1 = gen.generate("miss then hit", cfg, use_cache=True)
        # 第一次 miss，写入缓存；第二次 hit
        result2 = gen.generate("miss then hit", cfg, use_cache=True)
        assert result1 == result2

    def test_no_cache_when_use_cache_false(self, gen):
        cfg = GenerationConfig(format=OutputFormat.TEXT)
        result1 = gen.generate("no cache", cfg, use_cache=False)
        result2 = gen.generate("no cache", cfg, use_cache=False)
        assert result1 == result2  # mock 固定输出，但未使用缓存
        # 各有独立的 history 条目
        assert len(gen.get_history()) == 2

    def test_clear_cache(self, gen):
        cfg = GenerationConfig(format=OutputFormat.TEXT)
        gen.generate("clear me", cfg, use_cache=True)
        assert len(gen._cache) == 1
        gen.clear_cache()
        assert len(gen._cache) == 0

    def test_different_formats_different_cache_keys(self, gen):
        cfg_text = GenerationConfig(format=OutputFormat.TEXT)
        cfg_md = GenerationConfig(format=OutputFormat.MARKDOWN)
        gen.generate("same prompt", cfg_text, use_cache=True)
        gen.generate("same prompt", cfg_md, use_cache=True)
        assert len(gen._cache) == 2


# ═══════════════════════════════════════════════════════════════
# ContentGenerator generate 会话管理测试
# ═══════════════════════════════════════════════════════════════

class TestGenerateSession:
    """generate 会话管理测试"""

    def test_generate_with_session(self, gen):
        cfg = GenerationConfig(session_id="sess-1")
        result = gen.generate("你好", cfg)
        assert "你好" in result
        session_msgs = gen.get_session("sess-1")
        assert len(session_msgs) == 2
        assert session_msgs[0]["role"] == "user"
        assert session_msgs[0]["content"] == "你好"
        assert session_msgs[1]["role"] == "assistant"
        assert session_msgs[1]["content"] == result

    def test_generate_multi_turn_session(self, gen):
        cfg = GenerationConfig(session_id="sess-2")
        gen.generate("问题1", cfg)
        gen.generate("问题2", cfg)
        session_msgs = gen.get_session("sess-2")
        assert len(session_msgs) == 4
        assert session_msgs[0]["content"] == "问题1"
        assert session_msgs[2]["content"] == "问题2"

    def test_session_id_in_history(self, gen):
        cfg = GenerationConfig(session_id="sess-3")
        gen.generate("test", cfg)
        entry = gen.get_history()[0]
        assert entry["session_id"] == "sess-3"

    def test_multiple_sessions_independent(self, gen):
        cfg1 = GenerationConfig(session_id="sess-a")
        cfg2 = GenerationConfig(session_id="sess-b")
        gen.generate("A问题", cfg1)
        gen.generate("B问题", cfg2)
        assert len(gen.get_session("sess-a")) == 2
        assert len(gen.get_session("sess-b")) == 2
        assert gen.get_session("sess-a")[0]["content"] == "A问题"
        assert gen.get_session("sess-b")[0]["content"] == "B问题"

    def test_session_truncation_at_50(self, gen):
        """Session 消息保留最近 50 条消息（messages[-50:]）"""
        cfg = GenerationConfig(session_id="sess-trunc")
        # 生成 60 轮 → 120 条消息，但保留最近 50 条消息
        for i in range(60):
            gen.generate(f"msg{i}", cfg)
        session_msgs = gen.get_session("sess-trunc")
        # 50 条消息（不是 50 轮）
        assert len(session_msgs) == 50
        # 第一条消息的 index 应该是 35 (最早保留的第 36 轮 user 消息)
        assert session_msgs[0]["content"] == "msg35"
        assert session_msgs[-1]["role"] == "assistant"

    def test_get_session_non_existing(self, gen):
        assert gen.get_session("nonexistent") == []

    def test_list_sessions(self, gen):
        assert gen.list_sessions() == []
        gen.generate("test", GenerationConfig(session_id="s1"))
        gen.generate("test", GenerationConfig(session_id="s2"))
        sessions = gen.list_sessions()
        assert len(sessions) == 2
        assert "s1" in sessions
        assert "s2" in sessions

    def test_clear_session_existing(self, gen):
        gen.generate("test", GenerationConfig(session_id="sess-clear"))
        assert gen.clear_session("sess-clear") is True
        assert gen.get_session("sess-clear") == []

    def test_clear_session_non_existing(self, gen):
        assert gen.clear_session("no-such") is False

    def test_clear_all_sessions(self, gen):
        gen.generate("test", GenerationConfig(session_id="s1"))
        gen.generate("test", GenerationConfig(session_id="s2"))
        gen.generate("test", GenerationConfig(session_id="s3"))
        count = gen.clear_all_sessions()
        assert count == 3
        assert gen.list_sessions() == []
        assert gen._sessions == {}

    def test_clear_all_sessions_empty(self, gen):
        count = gen.clear_all_sessions()
        assert count == 0


# ═══════════════════════════════════════════════════════════════
# ContentGenerator get_history 测试
# ═══════════════════════════════════════════════════════════════

class TestGetHistory:
    """get_history 方法测试"""

    def test_default_limit(self, gen):
        for i in range(15):
            gen.generate(f"prompt{i}")
        assert len(gen.get_history()) == 10

    def test_custom_limit(self, gen):
        for i in range(15):
            gen.generate(f"prompt{i}")
        assert len(gen.get_history(limit=5)) == 5

    def test_limit_larger_than_total(self, gen):
        for i in range(3):
            gen.generate(f"prompt{i}")
        assert len(gen.get_history(limit=100)) == 3

    def test_empty_history(self, gen):
        assert gen.get_history() == []


# ═══════════════════════════════════════════════════════════════
# ContentGenerator stats 测试
# ═══════════════════════════════════════════════════════════════

class TestStats:
    """stats 方法测试"""

    def test_initial_stats(self, gen):
        s = gen.stats()
        assert s["name"] == "default"
        assert s["total_generations"] == 0
        assert s["cache_size"] == 0
        assert s["sessions"] == 0
        assert s["by_provider"] == {}
        assert s["est_tokens_by_provider"] == {}
        assert s["total_est_tokens"] == 0

    def test_stats_after_generation(self, gen):
        gen.generate("test")
        s = gen.stats()
        assert s["total_generations"] == 1
        assert s["by_provider"] == {"mock": 1}
        assert s["total_est_tokens"] > 0

    def test_stats_with_multiple_providers(self, gen):
        gen.generate("a", GenerationConfig(provider=LLMProvider.MOCK))
        gen.generate("b", GenerationConfig(provider=LLMProvider.MOCK))
        s = gen.stats()
        assert s["total_generations"] == 2
        assert s["by_provider"]["mock"] == 2

    def test_stats_with_cache(self, gen):
        cfg = GenerationConfig(format=OutputFormat.TEXT)
        gen.generate("cached", cfg, use_cache=True)
        gen.generate("cached", cfg, use_cache=True)
        s = gen.stats()
        assert s["total_generations"] == 2
        assert s["cache_size"] == 1

    def test_stats_with_sessions(self, gen):
        gen.generate("test", GenerationConfig(session_id="s1"))
        gen.generate("test", GenerationConfig(session_id="s2"))
        s = gen.stats()
        assert s["sessions"] == 2

    def test_stats_custom_name(self, gen_named):
        s = gen_named.stats()
        assert s["name"] == "test_gen"


# ═══════════════════════════════════════════════════════════════
# ContentGenerator generate_stream 测试
# ═══════════════════════════════════════════════════════════════

class TestGenerateStream:
    """generate_stream 方法测试"""

    def test_stream_mock_yields_tokens(self, gen, mock_sleep):
        tokens = list(gen.generate_stream("你好", token_delay=0))
        assert len(tokens) > 0
        full = "".join(tokens)
        assert "你好" in full

    def test_stream_mock_collects_all_tokens(self, gen, mock_sleep):
        tokens = list(gen.generate_stream("测试流式输出", token_delay=0))
        full = "".join(tokens)
        assert "测试流式输出" in full
        assert "default" in full

    def test_stream_mock_chinese_text(self, gen, mock_sleep):
        """中文文本按单字拆分"""
        tokens = list(gen.generate_stream("中华文明", token_delay=0))
        assert len(tokens) >= 4  # 中、华、文、明，至少4个字符
        assert "中" in tokens

    def test_stream_mock_english_text(self, gen, mock_sleep):
        """英文文本按词/标点聚合"""
        tokens = list(gen.generate_stream("Hello World", token_delay=0))
        assert len(tokens) > 0
        assert "Hello" in tokens

    def test_stream_adds_to_history(self, gen, mock_sleep):
        list(gen.generate_stream("stream test", token_delay=0))
        history = gen.get_history()
        assert len(history) == 1
        entry = history[0]
        assert entry["prompt"] == "stream test"
        assert entry["stream"] is True
        assert "duration" in entry

    def test_stream_none_config(self, gen, mock_sleep):
        tokens = list(gen.generate_stream("test", None, token_delay=0))
        assert len(tokens) > 0

    def test_stream_with_token_delay_zero(self, gen, mock_sleep):
        tokens = list(gen.generate_stream("test", token_delay=0))
        assert len(tokens) > 0

    def test_stream_markdown_format(self, gen, mock_sleep):
        cfg = GenerationConfig(format=OutputFormat.MARKDOWN)
        tokens = list(gen.generate_stream("标题", cfg, token_delay=0))
        full = "".join(tokens)
        assert full.startswith("## 标题")

    def test_stream_json_format(self, gen, mock_sleep):
        cfg = GenerationConfig(format=OutputFormat.JSON)
        tokens = list(gen.generate_stream("测试", cfg, token_delay=0))
        full = "".join(tokens)
        parsed = json.loads(full)
        assert parsed["prompt"] == "测试"

    def test_stream_html_format(self, gen, mock_sleep):
        cfg = GenerationConfig(format=OutputFormat.HTML)
        tokens = list(gen.generate_stream("内容", cfg, token_delay=0))
        full = "".join(tokens)
        assert full.startswith("<h1>内容</h1>")

    def test_stream_code_format(self, gen, mock_sleep):
        cfg = GenerationConfig(format=OutputFormat.CODE)
        tokens = list(gen.generate_stream("注释", cfg, token_delay=0))
        full = "".join(tokens)
        assert full.startswith("# 注释")

    def test_stream_custom_provider_falls_back_to_mock(self, gen, mock_sleep):
        cfg = GenerationConfig(provider=LLMProvider.CUSTOM)
        tokens = list(gen.generate_stream("test", cfg, token_delay=0))
        full = "".join(tokens)
        assert "test" in full


# ═══════════════════════════════════════════════════════════════
# ContentGenerator _stream_mock 测试
# ═══════════════════════════════════════════════════════════════

class TestStreamMock:
    """_stream_mock 方法测试"""

    def test_chinese_yields_single_char(self, gen, mock_sleep):
        cfg = GenerationConfig(format=OutputFormat.TEXT)
        tokens = list(gen._stream_mock("中华", cfg, 0))
        assert "中" in tokens
        assert "华" in tokens

    def test_english_yields_words(self, gen, mock_sleep):
        cfg = GenerationConfig(format=OutputFormat.TEXT)
        tokens = list(gen._stream_mock("Hello World", cfg, 0))
        assert "Hello" in tokens
        # " World"（含前导空格）作为一个 token
        assert " World" in tokens

    def test_mixed_chinese_english(self, gen, mock_sleep):
        cfg = GenerationConfig(format=OutputFormat.TEXT)
        tokens = list(gen._stream_mock("AI生成", cfg, 0))
        assert len(tokens) >= 3  # AI, 生, 成


# ═══════════════════════════════════════════════════════════════
# ContentGenerator generate_collect 测试
# ═══════════════════════════════════════════════════════════════

class TestGenerateCollect:
    """generate_collect 方法测试"""

    def test_returns_full_string(self, gen, mock_sleep):
        result = gen.generate_collect("收集测试")
        assert isinstance(result, str)
        assert "收集测试" in result
        assert "default" in result

    def test_equivalent_to_stream_join(self, gen, mock_sleep):
        cfg = GenerationConfig(format=OutputFormat.MARKDOWN)
        result = gen.generate_collect("标题", cfg)
        expected = "".join(gen.generate_stream("标题", cfg, token_delay=0))
        assert result == expected

    def test_none_config(self, gen, mock_sleep):
        result = gen.generate_collect("test", None)
        assert "test" in result


# ═══════════════════════════════════════════════════════════════
# ContentGenerator 模板管理测试
# ═══════════════════════════════════════════════════════════════

class TestTemplates:
    """模板管理测试"""

    def test_list_templates(self, gen):
        templates = gen.list_templates()
        assert isinstance(templates, list)
        assert "creative_writing" in templates
        assert "technical_explanation" in templates
        assert "analysis_report" in templates
        assert "code_explanation" in templates
        assert "innovation_idea" in templates
        assert "knowledge_summary" in templates
        assert "qa_answer" in templates

    def test_render_template_valid(self, gen):
        result = gen.render_template(
            "creative_writing",
            topic="中华文明",
            style="古典",
            length=500,
            language="中文"
        )
        assert "中华文明" in result
        assert "古典" in result
        assert "500" in result
        assert "中文" in result

    def test_render_template_unknown(self, gen):
        with pytest.raises(ValueError, match="未知模板"):
            gen.render_template("nonexistent_template")

    def test_render_template_missing_kwargs(self, gen):
        with pytest.raises(ValueError, match="缺少参数"):
            gen.render_template("creative_writing")  # 缺少 topic, style, length, language

    def test_generate_from_template(self, gen):
        result = gen.generate_from_template(
            "creative_writing",
            topic="测试主题",
            style="现代",
            length=300,
            language="中文"
        )
        assert isinstance(result, str)
        assert "测试主题" in result

    def test_generate_from_template_with_config(self, gen):
        cfg = GenerationConfig(format=OutputFormat.MARKDOWN)
        result = gen.generate_from_template(
            "creative_writing",
            cfg,
            topic="标题",
            style="古典",
            length=200,
            language="中文"
        )
        assert result.startswith("## ")

    def test_add_template(self, gen):
        gen.add_template("custom_tpl", "自定义模板：{var}")
        assert "custom_tpl" in gen.list_templates()
        result = gen.render_template("custom_tpl", var="测试值")
        assert result == "自定义模板：测试值"

    def test_remove_template_existing(self, gen):
        gen.add_template("to_remove", "test")
        assert gen.remove_template("to_remove") is True
        assert "to_remove" not in gen.list_templates()

    def test_remove_template_non_existing(self, gen):
        assert gen.remove_template("not_there") is False

    def test_remove_template_builtin(self, gen):
        """内置模板也可被移除"""
        assert gen.remove_template("creative_writing") is True
        assert "creative_writing" not in gen.list_templates()

    def test_render_template_qa_answer(self, gen):
        result = gen.render_template(
            "qa_answer",
            question="什么是AI？",
            context="技术讨论",
            language="中文"
        )
        assert "什么是AI？" in result
        assert "技术讨论" in result
        assert "中文" in result

    def test_render_template_technical_explanation(self, gen):
        result = gen.render_template(
            "technical_explanation",
            concept="机器学习",
            audience="初学者",
            depth="入门",
            language="中文"
        )
        assert "机器学习" in result
        assert "初学者" in result

    def test_render_template_analysis_report(self, gen):
        result = gen.render_template(
            "analysis_report",
            topic="AI市场",
            dimensions="技术、商业、政策",
            language="中文"
        )
        assert "AI市场" in result
        assert "技术、商业、政策" in result

    def test_render_template_code_explanation(self, gen):
        result = gen.render_template(
            "code_explanation",
            language="Python",
            code="print('hello')"
        )
        assert "Python" in result
        assert "print('hello')" in result

    def test_render_template_innovation_idea(self, gen):
        result = gen.render_template(
            "innovation_idea",
            challenge="能源危机",
            constraints="预算有限",
            language="中文"
        )
        assert "能源危机" in result
        assert "预算有限" in result

    def test_render_template_knowledge_summary(self, gen):
        result = gen.render_template(
            "knowledge_summary",
            content="人工智能是计算机科学的一个分支",
            language="中文"
        )
        assert "人工智能是计算机科学的一个分支" in result


# ═══════════════════════════════════════════════════════════════
# ContentGenerator CUSTOM provider 测试
# ═══════════════════════════════════════════════════════════════

class TestCustomProvider:
    """CUSTOM provider 测试"""

    def test_custom_provider_with_generator(self, gen):
        gen.set_custom_generator(lambda p, c: f"CUSTOM: {p}")
        cfg = GenerationConfig(provider=LLMProvider.CUSTOM)
        result = gen.generate("自定义提示", cfg)
        assert result == "CUSTOM: 自定义提示"

    def test_custom_provider_without_generator_falls_back(self, gen):
        cfg = GenerationConfig(provider=LLMProvider.CUSTOM)
        result = gen.generate("fallback test", cfg)
        assert "fallback test" in result
        assert "mock" in result

    def test_custom_provider_receives_config(self, gen):
        received = []
        gen.set_custom_generator(lambda p, c: received.append(c) or f"got: {p}")
        cfg = GenerationConfig(provider=LLMProvider.CUSTOM, format=OutputFormat.MARKDOWN)
        gen.generate("test", cfg)
        assert received[0] is cfg


# ═══════════════════════════════════════════════════════════════
# 边界情况测试
# ═══════════════════════════════════════════════════════════════

class TestEdgeCases:
    """边界情况测试"""

    def test_empty_prompt(self, gen):
        result = gen.generate("")
        assert isinstance(result, str)
        # 空 prompt 仍然产生输出
        assert len(result) > 0

    def test_very_long_prompt(self, gen):
        long_prompt = "测试" * 5000  # 10000 字符
        result = gen.generate(long_prompt)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_token_count_estimation(self, gen):
        """验证 token 估算逻辑"""
        result = gen.generate("你好世界")
        # len(content) // 2 + len(prompt) // 2
        s = gen.stats()
        assert s["total_est_tokens"] > 0

    def test_stream_token_delay_zero(self, gen, mock_sleep):
        """token_delay=0 时仍然正常产出"""
        tokens = list(gen.generate_stream("快速输出", token_delay=0))
        assert len(tokens) > 0

    def test_multiple_operations_stats(self, gen):
        gen.generate("a")
        gen.generate("b")
        gen.generate("c", GenerationConfig(session_id="s1"))
        gen.generate("d", GenerationConfig(session_id="s2"))
        s = gen.stats()
        assert s["total_generations"] == 4
        assert s["sessions"] == 2

    def test_two_generators_independent(self, gen, gen_named):
        r1 = gen.generate("test")
        r2 = gen_named.generate("test")
        assert "default" in r1
        assert "test_gen" in r2
        assert r1 != r2

    def test_generate_with_use_cache_default(self, gen):
        """use_cache 默认为 True"""
        cfg = GenerationConfig(format=OutputFormat.TEXT)
        gen.generate("cache default", cfg)
        assert len(gen._cache) == 1
        gen.generate("cache default", cfg)
        assert len(gen._cache) == 1  # 缓存命中，不新增


# ═══════════════════════════════════════════════════════════════
# 集成场景测试
# ═══════════════════════════════════════════════════════════════

class TestIntegration:
    """集成场景测试"""

    def test_full_pipeline_template_to_stream(self, gen, mock_sleep):
        """模板 → 生成 → 流式输出 → 收集"""
        prompt = gen.render_template(
            "creative_writing",
            topic="集成测试",
            style="现代",
            length=200,
            language="中文"
        )
        assert "集成测试" in prompt

        cfg = GenerationConfig(format=OutputFormat.MARKDOWN)
        # 流式
        tokens = list(gen.generate_stream(prompt, cfg, token_delay=0))
        full = "".join(tokens)
        assert full.startswith("## ")

        # 收集
        collected = gen.generate_collect(prompt, cfg)
        assert collected == "".join(gen.generate_stream(prompt, cfg, token_delay=0))

    def test_session_with_cache(self, gen):
        """会话 + 缓存联合使用"""
        cfg = GenerationConfig(session_id="sess-cache", format=OutputFormat.TEXT)
        r1 = gen.generate("会话缓存测试", cfg, use_cache=True)
        r2 = gen.generate("会话缓存测试", cfg, use_cache=True)
        assert r1 == r2
        session = gen.get_session("sess-cache")
        # 两次调用，每次一轮（user+assistant），共 4 条消息
        assert len(session) == 4

    def test_multiple_formats_stream(self, gen, mock_sleep):
        """所有格式的流式输出"""
        for fmt in OutputFormat:
            cfg = GenerationConfig(format=fmt)
            tokens = list(gen.generate_stream("test", cfg, token_delay=0))
            full = "".join(tokens)
            assert len(full) > 0

    def test_template_add_remove_cycle(self, gen):
        gen.add_template("cycle_test", "Hello {user_name}")
        assert "cycle_test" in gen.list_templates()
        assert gen.render_template("cycle_test", user_name="World") == "Hello World"
        gen.remove_template("cycle_test")
        assert "cycle_test" not in gen.list_templates()
        with pytest.raises(ValueError):
            gen.render_template("cycle_test", user_name="World")

    def test_generate_from_template_adds_to_history(self, gen):
        gen.generate_from_template(
            "creative_writing",
            topic="历史",
            style="古典",
            length=100,
            language="中文"
        )
        assert len(gen.get_history()) == 1


# ═══════════════════════════════════════════════════════════════
# Fixtures for mocking external API modules
# ═══════════════════════════════════════════════════════════════

@pytest.fixture
def mock_openai_module():
    """在 sys.modules 中注入 mock openai 模块"""
    import sys

    mock_mod = Mock()
    mock_mod.OpenAI = Mock()
    with patch.dict(sys.modules, {"openai": mock_mod}):
        yield mock_mod


@pytest.fixture
def mock_anthropic_module():
    """在 sys.modules 中注入 mock anthropic 模块"""
    import sys

    mock_mod = Mock()
    mock_mod.Anthropic = Mock()
    with patch.dict(sys.modules, {"anthropic": mock_mod}):
        yield mock_mod


# ═══════════════════════════════════════════════════════════════
# _call_openai / _call_claude / _call_local 测试（mock 外部依赖）
# ═══════════════════════════════════════════════════════════════

class TestCallOpenai:
    """_call_openai 方法测试（mock openai）"""

    def test_call_openai_with_messages(self, gen, mock_sleep, mock_openai_module):
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "OpenAI response"

        mock_client = Mock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai_module.OpenAI.return_value = mock_client

        gen.set_api_key("sk-test")
        cfg = GenerationConfig(provider=LLMProvider.OPENAI, model="gpt-4")
        result = gen._call_openai("hello", cfg, messages=[{"role": "user", "content": "hello"}])
        assert result == "OpenAI response"

    def test_call_openai_single_prompt(self, gen, mock_sleep, mock_openai_module):
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "single prompt response"

        mock_client = Mock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai_module.OpenAI.return_value = mock_client

        cfg = GenerationConfig(provider=LLMProvider.OPENAI, model="gpt-4")
        result = gen._call_openai("prompt", cfg)
        assert result == "single prompt response"

    def test_call_openai_empty_content(self, gen, mock_sleep, mock_openai_module):
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = ""

        mock_client = Mock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai_module.OpenAI.return_value = mock_client

        cfg = GenerationConfig(provider=LLMProvider.OPENAI)
        result = gen._call_openai("test", cfg)
        assert result == ""

    def test_call_openai_uses_config_api_key(self, gen, mock_sleep, mock_openai_module):
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "key from config"

        mock_client = Mock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai_module.OpenAI.return_value = mock_client

        cfg = GenerationConfig(provider=LLMProvider.OPENAI, api_key="sk-cfg", base_url="https://custom.api")
        result = gen._call_openai("test", cfg)
        assert result == "key from config"

    def test_call_openai_default_model(self, gen, mock_sleep, mock_openai_module):
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "default model"

        mock_client = Mock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai_module.OpenAI.return_value = mock_client

        cfg = GenerationConfig(provider=LLMProvider.OPENAI)  # model="" → defaults to gpt-3.5-turbo
        gen._call_openai("test", cfg)
        call_kwargs = mock_client.chat.completions.create.call_args[1]
        assert call_kwargs["model"] == "gpt-3.5-turbo"

    def test_call_openai_retry_on_failure(self, gen, mock_sleep, mock_openai_module):
        mock_client = Mock()
        mock_client.chat.completions.create.side_effect = [
            Exception("API error"),
            Exception("API error"),
            Mock(
                choices=[Mock(message=Mock(content="retry success"))]
            ),
        ]
        mock_openai_module.OpenAI.return_value = mock_client

        cfg = GenerationConfig(provider=LLMProvider.OPENAI, max_retries=3)
        result = gen._call_openai("test", cfg)
        assert result == "retry success"

    def test_call_openai_retry_exhausted(self, gen, mock_sleep, mock_openai_module):
        mock_client = Mock()
        mock_client.chat.completions.create.side_effect = Exception("persistent error")
        mock_openai_module.OpenAI.return_value = mock_client

        cfg = GenerationConfig(provider=LLMProvider.OPENAI, max_retries=1)
        result = gen._call_openai("test", cfg)
        assert "Error" in result
        assert "OpenAI" in result
        assert "persistent error" in result

    def test_call_openai_multi_message_session(self, gen, mock_sleep, mock_openai_module):
        """多轮会话消息（len > 1）走 messages 分支"""
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "multi turn"

        mock_client = Mock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai_module.OpenAI.return_value = mock_client

        cfg = GenerationConfig(provider=LLMProvider.OPENAI, model="gpt-4")
        msgs = [
            {"role": "user", "content": "hello"},
            {"role": "assistant", "content": "hi"},
            {"role": "user", "content": "how are you"},
        ]
        result = gen._call_openai("how are you", cfg, messages=msgs)
        assert result == "multi turn"
        # 验证使用了传入的 messages 列表
        call_kwargs = mock_client.chat.completions.create.call_args[1]
        assert call_kwargs["messages"] is msgs


class TestCallClaude:
    """_call_claude 方法测试（mock anthropic）"""

    def test_call_claude_with_messages(self, gen, mock_sleep, mock_anthropic_module):
        mock_response = Mock()
        mock_response.content = [Mock()]
        mock_response.content[0].text = "Claude response"

        mock_client = Mock()
        mock_client.messages.create.return_value = mock_response
        mock_anthropic_module.Anthropic.return_value = mock_client

        gen.set_api_key("sk-test")
        cfg = GenerationConfig(provider=LLMProvider.CLAUDE, model="claude-3-opus")
        result = gen._call_claude("hello", cfg, messages=[{"role": "user", "content": "hello"}])
        assert result == "Claude response"

    def test_call_claude_single_prompt(self, gen, mock_sleep, mock_anthropic_module):
        mock_response = Mock()
        mock_response.content = [Mock()]
        mock_response.content[0].text = "single prompt"

        mock_client = Mock()
        mock_client.messages.create.return_value = mock_response
        mock_anthropic_module.Anthropic.return_value = mock_client

        cfg = GenerationConfig(provider=LLMProvider.CLAUDE)
        result = gen._call_claude("prompt", cfg)
        assert result == "single prompt"

    def test_call_claude_uses_config_api_key(self, gen, mock_sleep, mock_anthropic_module):
        mock_response = Mock()
        mock_response.content = [Mock()]
        mock_response.content[0].text = "config key"

        mock_client = Mock()
        mock_client.messages.create.return_value = mock_response
        mock_anthropic_module.Anthropic.return_value = mock_client

        cfg = GenerationConfig(provider=LLMProvider.CLAUDE, api_key="sk-cfg")
        gen._call_claude("test", cfg)
        call_kwargs = mock_anthropic_module.Anthropic.call_args[1]
        assert call_kwargs["api_key"] == "sk-cfg"

    def test_call_claude_default_model(self, gen, mock_sleep, mock_anthropic_module):
        mock_response = Mock()
        mock_response.content = [Mock()]
        mock_response.content[0].text = "default"

        mock_client = Mock()
        mock_client.messages.create.return_value = mock_response
        mock_anthropic_module.Anthropic.return_value = mock_client

        cfg = GenerationConfig(provider=LLMProvider.CLAUDE)  # model="" → default
        gen._call_claude("test", cfg)
        call_kwargs = mock_client.messages.create.call_args[1]
        assert call_kwargs["model"] == "claude-3-haiku-20240307"

    def test_call_claude_retry_on_failure(self, gen, mock_sleep, mock_anthropic_module):
        mock_client = Mock()
        mock_client.messages.create.side_effect = [
            Exception("Claude error"),
            Mock(content=[Mock(text="retry success")]),
        ]
        mock_anthropic_module.Anthropic.return_value = mock_client

        cfg = GenerationConfig(provider=LLMProvider.CLAUDE, max_retries=2)
        result = gen._call_claude("test", cfg)
        assert result == "retry success"

    def test_call_claude_retry_exhausted(self, gen, mock_sleep, mock_anthropic_module):
        mock_client = Mock()
        mock_client.messages.create.side_effect = Exception("claude down")
        mock_anthropic_module.Anthropic.return_value = mock_client

        cfg = GenerationConfig(provider=LLMProvider.CLAUDE, max_retries=0)
        result = gen._call_claude("test", cfg)
        assert "Error" in result
        assert "Claude" in result

    def test_call_claude_multi_message_session(self, gen, mock_sleep, mock_anthropic_module):
        """多轮会话消息（len > 1）走 messages 分支"""
        mock_response = Mock()
        mock_response.content = [Mock()]
        mock_response.content[0].text = "multi turn claude"

        mock_client = Mock()
        mock_client.messages.create.return_value = mock_response
        mock_anthropic_module.Anthropic.return_value = mock_client

        cfg = GenerationConfig(provider=LLMProvider.CLAUDE, model="claude-3-opus")
        msgs = [
            {"role": "user", "content": "hello"},
            {"role": "assistant", "content": "hi"},
            {"role": "user", "content": "how are you"},
        ]
        result = gen._call_claude("how are you", cfg, messages=msgs)
        assert result == "multi turn claude"
        call_kwargs = mock_client.messages.create.call_args[1]
        assert call_kwargs["messages"] is msgs


class TestCallLocal:
    """_call_local 方法测试（mock requests）"""

    def test_call_local_success(self, gen, mock_sleep):
        mock_resp = Mock()
        mock_resp.json.return_value = {"response": "local model response"}

        with patch("requests.post", return_value=mock_resp):
            cfg = GenerationConfig(provider=LLMProvider.LOCAL)
            result = gen._call_local("test", cfg)
            assert result == "local model response"

    def test_call_local_custom_base_url(self, gen, mock_sleep):
        mock_resp = Mock()
        mock_resp.json.return_value = {"response": "custom url"}

        with patch("requests.post", return_value=mock_resp) as mock_post:
            cfg = GenerationConfig(provider=LLMProvider.LOCAL, base_url="http://custom:9999")
            gen._call_local("test", cfg)
            assert mock_post.call_args[0][0] == "http://custom:9999/api/generate"

    def test_call_local_default_url(self, gen, mock_sleep):
        mock_resp = Mock()
        mock_resp.json.return_value = {"response": "default"}

        with patch("requests.post", return_value=mock_resp) as mock_post:
            cfg = GenerationConfig(provider=LLMProvider.LOCAL)
            gen._call_local("test", cfg)
            assert mock_post.call_args[0][0] == "http://localhost:11434/api/generate"

    def test_call_local_custom_model(self, gen, mock_sleep):
        mock_resp = Mock()
        mock_resp.json.return_value = {"response": "custom model"}

        with patch("requests.post", return_value=mock_resp) as mock_post:
            cfg = GenerationConfig(provider=LLMProvider.LOCAL, model="mistral")
            gen._call_local("test", cfg)
            body = mock_post.call_args[1]["json"]
            assert body["model"] == "mistral"

    def test_call_local_retry_on_failure(self, gen, mock_sleep):
        mock_resp = Mock()
        mock_resp.json.return_value = {"response": "retry win"}

        with patch("requests.post", side_effect=[Exception("conn err"), mock_resp]):
            cfg = GenerationConfig(provider=LLMProvider.LOCAL, max_retries=2)
            result = gen._call_local("test", cfg)
            assert result == "retry win"

    def test_call_local_retry_exhausted(self, gen, mock_sleep):
        with patch("requests.post", side_effect=Exception("no connection")):
            cfg = GenerationConfig(provider=LLMProvider.LOCAL, max_retries=0)
            result = gen._call_local("test", cfg)
            assert "Error" in result
            assert "Local" in result


# ═══════════════════════════════════════════════════════════════
# 流式 API 测试（mock 外部依赖）
# ═══════════════════════════════════════════════════════════════

class TestStreamOpenai:
    """_stream_openai 方法测试（mock openai）"""

    def test_stream_openai_yields_chunks(self, gen, mock_sleep, mock_openai_module):
        chunk1 = Mock()
        chunk1.choices = [Mock()]
        chunk1.choices[0].delta.content = "Hello"

        chunk2 = Mock()
        chunk2.choices = [Mock()]
        chunk2.choices[0].delta.content = " World"

        chunk3 = Mock()
        chunk3.choices = [Mock()]
        chunk3.choices[0].delta.content = ""

        mock_client = Mock()
        mock_client.chat.completions.create.return_value = [chunk1, chunk2, chunk3]
        mock_openai_module.OpenAI.return_value = mock_client

        cfg = GenerationConfig(provider=LLMProvider.OPENAI)
        tokens = list(gen._stream_openai("test", cfg))
        assert tokens == ["Hello", " World"]

    def test_stream_openai_import_error(self, gen, mock_sleep, mock_openai_module):
        mock_openai_module.OpenAI.side_effect = ImportError("no openai")
        cfg = GenerationConfig(provider=LLMProvider.OPENAI)
        tokens = list(gen._stream_openai("test", cfg))
        assert any("Error" in t for t in tokens)
        full = "".join(tokens)
        assert "test" in full

    def test_stream_openai_runtime_error(self, gen, mock_sleep, mock_openai_module):
        mock_client = Mock()
        mock_client.chat.completions.create.side_effect = RuntimeError("API gone")
        mock_openai_module.OpenAI.return_value = mock_client

        cfg = GenerationConfig(provider=LLMProvider.OPENAI)
        tokens = list(gen._stream_openai("test", cfg))
        full = "".join(tokens)
        assert "Error" in full
        assert "test" in full  # 回退 MOCK 内容


class TestStreamClaude:
    """_stream_claude 方法测试（mock anthropic）"""

    def test_stream_claude_yields_text(self, gen, mock_sleep, mock_anthropic_module):
        mock_stream_ctx = Mock()
        mock_stream_ctx.text_stream = ["Claude", " says", " hello"]
        mock_stream_ctx.__enter__ = Mock(return_value=mock_stream_ctx)
        mock_stream_ctx.__exit__ = Mock(return_value=None)

        mock_client = Mock()
        mock_client.messages.stream.return_value = mock_stream_ctx
        mock_anthropic_module.Anthropic.return_value = mock_client

        cfg = GenerationConfig(provider=LLMProvider.CLAUDE)
        tokens = list(gen._stream_claude("test", cfg))
        assert tokens == ["Claude", " says", " hello"]

    def test_stream_claude_import_error(self, gen, mock_sleep, mock_anthropic_module):
        mock_anthropic_module.Anthropic.side_effect = ImportError("no anthropic")
        cfg = GenerationConfig(provider=LLMProvider.CLAUDE)
        tokens = list(gen._stream_claude("test", cfg))
        full = "".join(tokens)
        assert "Error" in full
        assert "test" in full

    def test_stream_claude_runtime_error(self, gen, mock_sleep, mock_anthropic_module):
        mock_client = Mock()
        mock_client.messages.stream.side_effect = RuntimeError("Claude down")
        mock_anthropic_module.Anthropic.return_value = mock_client

        cfg = GenerationConfig(provider=LLMProvider.CLAUDE)
        tokens = list(gen._stream_claude("test", cfg))
        full = "".join(tokens)
        assert "Error" in full
        assert "test" in full


class TestStreamLocal:
    """_stream_local 方法测试（mock requests）"""

    def test_stream_local_yields_chunks(self, gen, mock_sleep):
        mock_resp = Mock()
        mock_resp.iter_lines.return_value = [
            '{"response": "local"}',
            '{"response": " stream"}',
            '{"response": ""}',
            "invalid json",
        ]

        with patch("requests.post", return_value=mock_resp):
            cfg = GenerationConfig(provider=LLMProvider.LOCAL)
            tokens = list(gen._stream_local("test", cfg))
            assert tokens == ["local", " stream"]

    def test_stream_local_import_error(self, gen, mock_sleep):
        with patch("builtins.__import__", side_effect=ImportError("no requests")):
            cfg = GenerationConfig(provider=LLMProvider.LOCAL)
            tokens = list(gen._stream_local("test", cfg))
            full = "".join(tokens)
            assert "Error" in full
            assert "test" in full

    def test_stream_local_runtime_error(self, gen, mock_sleep):
        with patch("requests.post", side_effect=RuntimeError("no server")):
            cfg = GenerationConfig(provider=LLMProvider.LOCAL)
            tokens = list(gen._stream_local("test", cfg))
            full = "".join(tokens)
            assert "Error" in full
            assert "test" in full


# ═══════════════════════════════════════════════════════════════
# generate 通过真实 provider 路径测试
# ═══════════════════════════════════════════════════════════════

class TestGenerateViaRealProviders:
    """generate 通过 OPENAI/CLAUDE/LOCAL provider 的集成测试"""

    def test_generate_via_openai(self, gen, mock_sleep, mock_openai_module):
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "via openai"

        mock_client = Mock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai_module.OpenAI.return_value = mock_client

        cfg = GenerationConfig(provider=LLMProvider.OPENAI, model="gpt-4")
        result = gen.generate("test", cfg)
        assert result == "via openai"

    def test_generate_via_claude(self, gen, mock_sleep, mock_anthropic_module):
        mock_response = Mock()
        mock_response.content = [Mock()]
        mock_response.content[0].text = "via claude"

        mock_client = Mock()
        mock_client.messages.create.return_value = mock_response
        mock_anthropic_module.Anthropic.return_value = mock_client

        cfg = GenerationConfig(provider=LLMProvider.CLAUDE)
        result = gen.generate("test", cfg)
        assert result == "via claude"

    def test_generate_via_local(self, gen, mock_sleep):
        mock_resp = Mock()
        mock_resp.json.return_value = {"response": "via local"}

        with patch("requests.post", return_value=mock_resp):
            cfg = GenerationConfig(provider=LLMProvider.LOCAL)
            result = gen.generate("test", cfg)
            assert result == "via local"

    def test_generate_stream_via_openai(self, gen, mock_sleep, mock_openai_module):
        chunk = Mock()
        chunk.choices = [Mock()]
        chunk.choices[0].delta.content = "stream openai"

        mock_client = Mock()
        mock_client.chat.completions.create.return_value = [chunk]
        mock_openai_module.OpenAI.return_value = mock_client

        cfg = GenerationConfig(provider=LLMProvider.OPENAI)
        tokens = list(gen.generate_stream("test", cfg, token_delay=0))
        assert tokens == ["stream openai"]

    def test_generate_stream_via_claude(self, gen, mock_sleep, mock_anthropic_module):
        mock_stream_ctx = Mock()
        mock_stream_ctx.text_stream = ["stream claude"]
        mock_stream_ctx.__enter__ = Mock(return_value=mock_stream_ctx)
        mock_stream_ctx.__exit__ = Mock(return_value=None)

        mock_client = Mock()
        mock_client.messages.stream.return_value = mock_stream_ctx
        mock_anthropic_module.Anthropic.return_value = mock_client

        cfg = GenerationConfig(provider=LLMProvider.CLAUDE)
        tokens = list(gen.generate_stream("test", cfg, token_delay=0))
        assert tokens == ["stream claude"]

    def test_generate_stream_via_local(self, gen, mock_sleep):
        mock_resp = Mock()
        mock_resp.iter_lines.return_value = ['{"response": "stream local"}']

        with patch("requests.post", return_value=mock_resp):
            cfg = GenerationConfig(provider=LLMProvider.LOCAL)
            tokens = list(gen.generate_stream("test", cfg, token_delay=0))
            assert tokens == ["stream local"]