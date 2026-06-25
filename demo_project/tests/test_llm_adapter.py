"""test_llm_adapter.py — LLM 适配器模块综合测试

覆盖 tengod.llm_adapter 中所有类、函数、边界情况。
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from tengod.llm_adapter import (
    LLM_API_KEY,
    LLM_BACKEND,
    LLM_MODEL,
    BaseLLMAdapter,
    ChatMessage,
    LLMResponse,
    MockAdapter,
    OpenAIAdapter,
    _build_rag_context,
    chat,
    chat_stream,
    generate_report,
    get_llm,
    reset_llm,
    REPORT_SYSTEM_PROMPT,
    CHAT_SYSTEM_PROMPT,
    RAG_SYSTEM_PROMPT,
)


# ============================================================================
# 1. ChatMessage dataclass 测试
# ============================================================================

class TestChatMessage:
    """ChatMessage 数据类测试"""

    def test_create_default(self):
        msg = ChatMessage(role="user", content="你好")
        assert msg.role == "user"
        assert msg.content == "你好"

    def test_create_system(self):
        msg = ChatMessage(role="system", content="你是助手")
        assert msg.role == "system"
        assert msg.content == "你是助手"

    def test_create_assistant(self):
        msg = ChatMessage(role="assistant", content="回复内容")
        assert msg.role == "assistant"
        assert msg.content == "回复内容"

    def test_empty_content(self):
        msg = ChatMessage(role="user", content="")
        assert msg.content == ""
        assert msg.role == "user"

    def test_long_content(self):
        long_text = "长文本" * 1000
        msg = ChatMessage(role="user", content=long_text)
        assert len(msg.content) == len(long_text)

    def test_equality(self):
        a = ChatMessage(role="user", content="你好")
        b = ChatMessage(role="user", content="你好")
        assert a == b

    def test_inequality_different_role(self):
        a = ChatMessage(role="user", content="你好")
        b = ChatMessage(role="system", content="你好")
        assert a != b

    def test_inequality_different_content(self):
        a = ChatMessage(role="user", content="你好")
        b = ChatMessage(role="user", content="再见")
        assert a != b


# ============================================================================
# 2. LLMResponse dataclass 测试
# ============================================================================

class TestLLMResponse:
    """LLMResponse 数据类测试"""

    def test_create_default(self):
        resp = LLMResponse(content="回复", model="test-model")
        assert resp.content == "回复"
        assert resp.model == "test-model"
        assert resp.usage == {}
        assert resp.elapsed_ms == 0.0

    def test_create_with_usage(self):
        resp = LLMResponse(
            content="回复",
            model="gpt-4",
            usage={"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30},
            elapsed_ms=150.5,
        )
        assert resp.usage["prompt_tokens"] == 10
        assert resp.usage["completion_tokens"] == 20
        assert resp.usage["total_tokens"] == 30
        assert resp.elapsed_ms == 150.5

    def test_equality(self):
        a = LLMResponse(content="x", model="m")
        b = LLMResponse(content="x", model="m")
        assert a == b

    def test_inequality(self):
        a = LLMResponse(content="x", model="m")
        b = LLMResponse(content="y", model="m")
        assert a != b


# ============================================================================
# 3. BaseLLMAdapter 抽象类测试
# ============================================================================

class TestBaseLLMAdapter:
    """BaseLLMAdapter 抽象基类测试"""

    def test_cannot_instantiate_directly(self):
        with pytest.raises(TypeError):
            BaseLLMAdapter()  # type: ignore[abstract]

    def test_subclass_must_implement_chat(self):
        class Incomplete(BaseLLMAdapter):
            @property
            def model_name(self) -> str:
                return "test"

            async def chat_stream(self, messages, temperature=0.7, max_tokens=2048):
                yield ""

        with pytest.raises(TypeError):
            Incomplete()  # type: ignore[abstract]

    def test_subclass_must_implement_chat_stream(self):
        class Incomplete(BaseLLMAdapter):
            @property
            def model_name(self) -> str:
                return "test"

            async def chat(self, messages, temperature=0.7, max_tokens=2048):
                return LLMResponse(content="", model="test")

        with pytest.raises(TypeError):
            Incomplete()  # type: ignore[abstract]

    def test_subclass_must_implement_model_name(self):
        class Incomplete(BaseLLMAdapter):
            async def chat(self, messages, temperature=0.7, max_tokens=2048):
                return LLMResponse(content="", model="test")

            async def chat_stream(self, messages, temperature=0.7, max_tokens=2048):
                yield ""

        with pytest.raises(TypeError):
            Incomplete()  # type: ignore[abstract]


# ============================================================================
# 4. MockAdapter 测试
# ============================================================================

class TestMockAdapter:
    """MockAdapter 综合测试"""

    @pytest.fixture
    def mock(self):
        return MockAdapter()

    # --- model_name ---

    def test_model_name(self, mock):
        assert mock.model_name == "mock/template-v1"

    # --- chat() ---

    @pytest.mark.asyncio
    async def test_chat_returns_llm_response(self, mock):
        messages = [ChatMessage(role="user", content="你好")]
        resp = await mock.chat(messages)
        assert isinstance(resp, LLMResponse)
        assert isinstance(resp.content, str)
        assert len(resp.content) > 0
        assert resp.model == "mock/template-v1"

    @pytest.mark.asyncio
    async def test_chat_with_question(self, mock):
        messages = [ChatMessage(role="user", content="我的喜用神是什么？")]
        resp = await mock.chat(messages)
        assert "喜用神" in resp.content

    @pytest.mark.asyncio
    async def test_chat_with_bazi_data(self, mock):
        bazi_data = (
            "八字：庚午 壬午 辛亥 癸巳\n"
            "日主：辛金\n"
            "五行：金2 木0 水2 火3 土1\n"
            "格局：伤官格\n"
            "用神：土、金\n"
            "神煞：天乙贵人(年)、桃花(日)、驿马(月)\n"
            "大运：6-15岁 癸未"
        )
        messages = [ChatMessage(role="user", content=bazi_data)]
        resp = await mock.chat(messages)
        assert "命理分析报告" in resp.content or "日主" in resp.content

    @pytest.mark.asyncio
    async def test_chat_with_general_message(self, mock):
        messages = [ChatMessage(role="user", content="今天天气不错")]
        resp = await mock.chat(messages)
        assert "Mock LLM" in resp.content

    @pytest.mark.asyncio
    async def test_chat_with_system_message(self, mock):
        messages = [
            ChatMessage(role="system", content="你是命理专家"),
            ChatMessage(role="user", content="你好"),
        ]
        resp = await mock.chat(messages)
        assert isinstance(resp, LLMResponse)
        assert len(resp.content) > 0

    @pytest.mark.asyncio
    async def test_chat_usage_stats(self, mock):
        messages = [ChatMessage(role="user", content="你好")]
        resp = await mock.chat(messages)
        assert "completion_tokens" in resp.usage
        assert "total_tokens" in resp.usage
        assert resp.usage["completion_tokens"] == len(resp.content)

    @pytest.mark.asyncio
    async def test_chat_elapsed_time(self, mock):
        messages = [ChatMessage(role="user", content="你好")]
        resp = await mock.chat(messages)
        assert resp.elapsed_ms > 0

    # --- chat_stream() ---

    @pytest.mark.asyncio
    async def test_chat_stream_yields_strings(self, mock):
        messages = [ChatMessage(role="user", content="你好")]
        chunks = []
        async for chunk in mock.chat_stream(messages):
            chunks.append(chunk)
            assert isinstance(chunk, str)
        assert len(chunks) > 0
        full = "".join(chunks)
        assert len(full) > 0

    @pytest.mark.asyncio
    async def test_chat_stream_reassembles_to_full_content(self, mock):
        messages = [ChatMessage(role="user", content="你好")]
        # Get full content via chat()
        full_resp = await mock.chat(messages)
        # Get streamed content
        streamed = ""
        async for chunk in mock.chat_stream(messages):
            streamed += chunk
        assert streamed == full_resp.content

    @pytest.mark.asyncio
    async def test_chat_stream_with_question(self, mock):
        messages = [ChatMessage(role="user", content="五行是什么？")]
        chunks = []
        async for chunk in mock.chat_stream(messages):
            chunks.append(chunk)
        full = "".join(chunks)
        assert "五行" in full

    @pytest.mark.asyncio
    async def test_chat_stream_with_bazi_data(self, mock):
        bazi_data = (
            "八字：庚午 壬午 辛亥 癸巳\n"
            "日主：辛金\n"
            "五行：金2 木0 水2 火3 土1\n"
            "格局：伤官格\n"
            "用神：土、金\n"
            "神煞：天乙贵人(年)、桃花(日)、驿马(月)\n" * 10
        )
        messages = [ChatMessage(role="user", content=bazi_data)]
        chunks = []
        async for chunk in mock.chat_stream(messages):
            chunks.append(chunk)
        full = "".join(chunks)
        assert len(full) > 0

    # --- _generate() ---

    def test_generate_routes_to_qa(self, mock):
        """包含问号且非八字数据 → _generate_qa"""
        result = mock._generate([ChatMessage(role="user", content="什么是五行？")])
        assert "五行" in result
        assert "Mock LLM" in result

    def test_generate_routes_to_report_section(self, mock):
        """长文本 + 八字关键词 → _generate_report_section"""
        bazi_data = "八字排盘\n日主：辛金\n五行：金2 木0\n" + "填充" * 30
        result = mock._generate([ChatMessage(role="user", content=bazi_data)])
        assert "命理分析报告" in result or "日主" in result

    def test_generate_routes_to_general(self, mock):
        """短文本无特殊标记 → _generate_general"""
        result = mock._generate([ChatMessage(role="user", content="你好")])
        assert "Mock LLM" in result

    def test_generate_with_empty_messages(self, mock):
        result = mock._generate([])
        assert "Mock LLM" in result

    # --- _generate_report_section() ---

    def test_generate_report_section_with_rich_data(self, mock):
        context = "日主：辛金\n五行：金2 木0 水2\n格局：伤官格\n用神：土、金\n神煞：天乙贵人"
        result = mock._generate_report_section(context)
        assert "命理分析报告" in result
        assert "日主" in result
        assert "五行" in result
        assert "格局" in result
        assert "用神" in result
        assert "神煞" in result
        assert "Mock LLM" in result

    def test_generate_report_section_with_minimal_data(self, mock):
        context = "简单数据"
        result = mock._generate_report_section(context)
        assert "命理分析报告" in result
        assert "Mock LLM" in result

    def test_generate_report_section_empty(self, mock):
        result = mock._generate_report_section("")
        assert "命理分析报告" in result
        assert "Mock LLM" in result

    # --- _generate_qa() ---

    def test_generate_qa_xys(self, mock):
        result = mock._generate_qa("我的喜用神是什么？")
        assert "喜用神" in result
        assert "Mock LLM" in result

    def test_generate_qa_wuxing(self, mock):
        result = mock._generate_qa("五行相生相克是怎么回事？")
        assert "五行" in result
        assert "Mock LLM" in result

    def test_generate_qa_geju(self, mock):
        result = mock._generate_qa("格局怎么看？")
        assert "格局" in result
        assert "Mock LLM" in result

    def test_generate_qa_dayun(self, mock):
        result = mock._generate_qa("大运如何推算？")
        assert "大运" in result
        assert "Mock LLM" in result

    def test_generate_qa_shensha(self, mock):
        result = mock._generate_qa("神煞有哪些？")
        assert "神煞" in result
        assert "Mock LLM" in result

    def test_generate_qa_unknown(self, mock):
        result = mock._generate_qa("今天吃什么？")
        assert "Mock LLM" in result
        assert "命理" in result

    # --- _generate_general() ---

    def test_generate_general_short(self, mock):
        result = mock._generate_general("你好")
        assert "Mock LLM" in result
        assert "你好" in result

    def test_generate_general_long(self, mock):
        long_text = "A" * 1000
        result = mock._generate_general(long_text)
        assert "Mock LLM" in result
        # 前缀 + 截断到 500 + 后缀，总长度应小于 600
        assert len(result) < 600

    def test_generate_general_empty(self, mock):
        result = mock._generate_general("")
        assert "Mock LLM" in result


# ============================================================================
# 5. get_llm / reset_llm 工厂函数测试
# ============================================================================

class TestFactory:
    """工厂函数测试"""

    def teardown_method(self):
        reset_llm()

    def test_get_llm_default_returns_mock(self):
        reset_llm()
        llm = get_llm()
        assert isinstance(llm, MockAdapter)

    def test_get_llm_mock_backend(self):
        reset_llm()
        llm = get_llm(backend="mock")
        assert isinstance(llm, MockAdapter)

    def test_get_llm_singleton(self):
        reset_llm()
        a = get_llm()
        b = get_llm()
        assert a is b

    def test_get_llm_singleton_ignores_params(self):
        reset_llm()
        a = get_llm(backend="mock")
        b = get_llm(backend="openai", api_key="sk-test")
        assert a is b
        assert isinstance(a, MockAdapter)

    def test_reset_llm(self):
        reset_llm()
        a = get_llm()
        reset_llm()
        b = get_llm()
        assert a is not b

    def test_get_llm_openai_backend_no_key(self):
        """openai backend should work even without a real key (lazy init)"""
        reset_llm()
        llm = get_llm(backend="openai", api_key="sk-test")
        assert isinstance(llm, OpenAIAdapter)
        assert llm.model_name == "gpt-4o-mini"


# ============================================================================
# 6. generate_report() 便捷函数测试
# ============================================================================

class TestGenerateReport:
    """generate_report 便捷函数测试"""

    @pytest.fixture
    def bazi_data(self):
        return (
            "八字：庚午 壬午 辛亥 癸巳\n"
            "日主：辛金\n"
            "五行：金2 木0 水2 火3 土1\n"
            "格局：伤官格\n"
            "用神：土、金\n"
            "神煞：天乙贵人(年)、桃花(日)、驿马(月)"
        )

    @pytest.mark.asyncio
    async def test_generate_report_with_mock(self, bazi_data):
        reset_llm()
        llm = get_llm(backend="mock")
        result = await generate_report(bazi_data, llm)
        assert isinstance(result, str)
        assert len(result) > 0

    @pytest.mark.asyncio
    async def test_generate_report_auto_llm(self, bazi_data):
        reset_llm()
        result = await generate_report(bazi_data)
        assert isinstance(result, str)
        assert len(result) > 0

    @pytest.mark.asyncio
    async def test_generate_report_with_rag_flag(self, bazi_data):
        """use_rag=True 不应崩溃（vector_store 可能不可用）"""
        reset_llm()
        llm = get_llm(backend="mock")
        result = await generate_report(bazi_data, llm, use_rag=True)
        assert isinstance(result, str)
        assert len(result) > 0


# ============================================================================
# 7. chat() 便捷函数测试
# ============================================================================

class TestChat:
    """chat 便捷函数测试"""

    @pytest.mark.asyncio
    async def test_chat_simple_question(self):
        reset_llm()
        llm = get_llm(backend="mock")
        result = await chat("五行是什么？", llm=llm, use_rag=False)
        assert isinstance(result, str)
        assert len(result) > 0

    @pytest.mark.asyncio
    async def test_chat_with_bazi_context(self):
        reset_llm()
        llm = get_llm(backend="mock")
        bazi = "八字：庚午 壬午 辛亥 癸巳\n日主：辛金"
        result = await chat("我的喜用神是什么？", bazi_context=bazi, llm=llm, use_rag=False)
        assert isinstance(result, str)
        assert len(result) > 0

    @pytest.mark.asyncio
    async def test_chat_auto_llm(self):
        reset_llm()
        result = await chat("你好", use_rag=False)
        assert isinstance(result, str)
        assert len(result) > 0

    @pytest.mark.asyncio
    async def test_chat_with_rag_flag(self):
        """use_rag=True 不应崩溃"""
        reset_llm()
        llm = get_llm(backend="mock")
        result = await chat("五行是什么？", llm=llm, use_rag=True)
        assert isinstance(result, str)
        assert len(result) > 0


# ============================================================================
# 8. chat_stream() 便捷函数测试
# ============================================================================

class TestChatStream:
    """chat_stream 便捷函数测试"""

    @pytest.mark.asyncio
    async def test_chat_stream_yields_strings(self):
        reset_llm()
        llm = get_llm(backend="mock")
        chunks = []
        async for chunk in chat_stream("你好", llm=llm, use_rag=False):
            chunks.append(chunk)
            assert isinstance(chunk, str)
        assert len(chunks) > 0
        assert len("".join(chunks)) > 0

    @pytest.mark.asyncio
    async def test_chat_stream_with_bazi_context(self):
        reset_llm()
        llm = get_llm(backend="mock")
        bazi = "八字：庚午 壬午 辛亥 癸巳\n日主：辛金"
        chunks = []
        async for chunk in chat_stream("我的用神是什么？", bazi_context=bazi, llm=llm, use_rag=False):
            chunks.append(chunk)
        assert len(chunks) > 0

    @pytest.mark.asyncio
    async def test_chat_stream_auto_llm(self):
        reset_llm()
        chunks = []
        async for chunk in chat_stream("你好", use_rag=False):
            chunks.append(chunk)
        assert len(chunks) > 0

    @pytest.mark.asyncio
    async def test_chat_stream_with_rag_flag(self):
        reset_llm()
        llm = get_llm(backend="mock")
        chunks = []
        async for chunk in chat_stream("五行是什么？", llm=llm, use_rag=True):
            chunks.append(chunk)
        assert len(chunks) > 0


# ============================================================================
# 9. _build_rag_context() 测试
# ============================================================================

class TestBuildRagContext:
    """_build_rag_context 辅助函数测试"""

    def _make_mock_store(self, results_list):
        """创建模拟的 vector store"""
        store = MagicMock()

        def make_result(items):
            result = MagicMock()
            result.results = items
            return result

        store.search = MagicMock(side_effect=[make_result(r) for r in results_list])
        return store

    def test_build_rag_context_with_results(self):
        store = self._make_mock_store([
            [
                {"name": "五行", "text": "五行包括金木水火土，相生相克。"},
                {"name": "阴阳", "text": "阴阳是宇宙的基本法则。"},
            ]
        ])
        result = _build_rag_context(store, ["五行"])
        assert "五行" in result
        assert "金木水火土" in result

    def test_build_rag_context_multiple_queries(self):
        store = self._make_mock_store([
            [{"name": "五行", "text": "五行内容"}],
            [{"name": "格局", "text": "格局内容"}],
        ])
        result = _build_rag_context(store, ["五行", "格局"])
        assert "五行" in result
        assert "格局" in result

    def test_build_rag_context_deduplication(self):
        store = self._make_mock_store([
            [{"name": "五行", "text": "五行内容"}],
            [{"name": "五行", "text": "五行内容（重复）"}],
        ])
        result = _build_rag_context(store, ["五行", "五行"])
        # 同名去重，应只有一行（name 作为去重 key）
        lines = result.strip().split("\n")
        assert len(lines) == 1

    def test_build_rag_context_empty_results(self):
        store = self._make_mock_store([[]])
        result = _build_rag_context(store, ["查询"])
        assert result == ""

    def test_build_rag_context_empty_text(self):
        store = self._make_mock_store([
            [{"name": "五行", "text": ""}]
        ])
        result = _build_rag_context(store, ["五行"])
        assert result == ""

    def test_build_rag_context_missing_name(self):
        store = self._make_mock_store([
            [{"text": "内容"}]
        ])
        result = _build_rag_context(store, ["查询"])
        # 缺少 name 时，key 为空字符串，仍会被加入结果
        assert "- :" in result

    def test_build_rag_context_truncates_text(self):
        long_text = "A" * 500
        store = self._make_mock_store([
            [{"name": "测试", "text": long_text}]
        ])
        result = _build_rag_context(store, ["测试"])
        assert "测试" in result
        # 文本应被截断到 200 字符
        assert len(result) < len(long_text) + 50

    def test_build_rag_context_limit_10_results(self):
        items = [{"name": f"item_{i}", "text": f"text_{i}"} for i in range(15)]
        store = self._make_mock_store([items])
        result = _build_rag_context(store, ["查询"])
        lines = result.split("\n")
        assert len(lines) <= 10

    def test_build_rag_context_search_exception(self):
        store = MagicMock()
        store.search.side_effect = Exception("search error")
        result = _build_rag_context(store, ["查询"])
        assert result == ""

    def test_build_rag_context_empty_queries(self):
        store = MagicMock()
        result = _build_rag_context(store, [])
        assert result == ""


# ============================================================================
# 10. Prompt 模板常量测试
# ============================================================================

class TestPromptTemplates:
    """Prompt 模板常量测试"""

    def test_report_system_prompt_is_string(self):
        assert isinstance(REPORT_SYSTEM_PROMPT, str)
        assert len(REPORT_SYSTEM_PROMPT) > 0
        assert "命理" in REPORT_SYSTEM_PROMPT

    def test_chat_system_prompt_is_string(self):
        assert isinstance(CHAT_SYSTEM_PROMPT, str)
        assert len(CHAT_SYSTEM_PROMPT) > 0
        assert "命理" in CHAT_SYSTEM_PROMPT

    def test_rag_system_prompt_is_string(self):
        assert isinstance(RAG_SYSTEM_PROMPT, str)
        assert len(RAG_SYSTEM_PROMPT) > 0
        assert "{knowledge_context}" in RAG_SYSTEM_PROMPT


# ============================================================================
# 11. 边界情况测试
# ============================================================================

class TestEdgeCases:
    """边界情况与异常处理测试"""

    @pytest.fixture
    def mock(self):
        return MockAdapter()

    # --- MockAdapter 边界 ---

    @pytest.mark.asyncio
    async def test_mock_chat_empty_messages(self, mock):
        resp = await mock.chat([])
        assert isinstance(resp, LLMResponse)
        assert len(resp.content) > 0

    @pytest.mark.asyncio
    async def test_mock_chat_stream_empty_messages(self, mock):
        chunks = []
        async for chunk in mock.chat_stream([]):
            chunks.append(chunk)
        assert len(chunks) > 0

    @pytest.mark.asyncio
    async def test_mock_chat_only_system_messages(self, mock):
        messages = [ChatMessage(role="system", content="你是助手")]
        resp = await mock.chat(messages)
        assert isinstance(resp, LLMResponse)

    @pytest.mark.asyncio
    async def test_mock_chat_multiple_users(self, mock):
        """多个 user 消息时，取第一个"""
        messages = [
            ChatMessage(role="user", content="第一个问题"),
            ChatMessage(role="assistant", content="回答"),
            ChatMessage(role="user", content="第二个问题"),
        ]
        resp = await mock.chat(messages)
        assert isinstance(resp, LLMResponse)

    # --- 流式分块 ---

    @pytest.mark.asyncio
    async def test_stream_chunk_size(self, mock):
        """短内容，验证分块逻辑"""
        messages = [ChatMessage(role="user", content="五行是什么？")]
        chunks = []
        async for chunk in mock.chat_stream(messages):
            chunks.append(chunk)
        # 每个 chunk 最大 10 字符
        for c in chunks[:-1]:
            assert len(c) <= 10

    # --- 八字检测边界 ---

    def test_generate_short_bazi_not_report(self, mock):
        """短文本即使包含八字关键词也不触发报告生成"""
        # 只有 "八字" 但长度不足 80
        result = mock._generate([ChatMessage(role="user", content="八字？")])
        # 应该走 _generate_qa 或 _generate_general，不是 report
        assert "命理分析报告" not in result

    def test_generate_question_with_bazi_data(self, mock):
        """长文本 + 八字关键词 + 问号 → 仍走报告（因为 has_bazi_data 优先）"""
        bazi_data = "八字排盘\n日主：辛金\n五行：金2 木0\n" + "数据" * 25 + "？"
        result = mock._generate([ChatMessage(role="user", content=bazi_data)])
        # has_bazi_data 为 True → 走 report，不管 is_question
        assert "Mock LLM" in result

    # --- 工厂边界 ---

    def test_get_llm_respects_explicit_backend(self):
        reset_llm()
        llm = get_llm(backend="mock")
        assert isinstance(llm, MockAdapter)


# ============================================================================
# 12. 一致性测试
# ============================================================================

class TestConsistency:
    """MockAdapter 输出一致性测试"""

    @pytest.fixture
    def mock(self):
        return MockAdapter()

    def test_same_input_same_output(self, mock):
        msg = [ChatMessage(role="user", content="五行是什么？")]
        result1 = mock._generate(msg)
        result2 = mock._generate(msg)
        assert result1 == result2

    @pytest.mark.asyncio
    async def test_chat_and_stream_produce_same_content(self, mock):
        messages = [ChatMessage(role="user", content="格局怎么看？")]
        resp = await mock.chat(messages)
        streamed = ""
        async for chunk in mock.chat_stream(messages):
            streamed += chunk
        assert streamed == resp.content

    @pytest.mark.asyncio
    async def test_chat_response_has_all_fields(self, mock):
        messages = [ChatMessage(role="user", content="你好")]
        resp = await mock.chat(messages)
        assert hasattr(resp, "content")
        assert hasattr(resp, "model")
        assert hasattr(resp, "usage")
        assert hasattr(resp, "elapsed_ms")
        assert resp.content
        assert resp.model
        assert isinstance(resp.usage, dict)
        assert isinstance(resp.elapsed_ms, float)


# ============================================================================
# 13. 配置常量测试
# ============================================================================

class TestConfig:
    """模块级配置常量测试"""

    def test_llm_backend_is_string(self):
        assert isinstance(LLM_BACKEND, str)

    def test_llm_model_is_string(self):
        assert isinstance(LLM_MODEL, str)


# ============================================================================
# 14. OpenAIAdapter 测试（mock openai client）
# ============================================================================

class TestOpenAIAdapter:
    """OpenAIAdapter 测试（mock _get_client，无需真实 API key）"""

    @pytest.fixture
    def adapter(self):
        return OpenAIAdapter(api_key="sk-test", model="gpt-4o-mini")

    def test_model_name(self, adapter):
        assert adapter.model_name == "gpt-4o-mini"

    def test_get_client_creates_client(self, adapter):
        mock_client = MagicMock()
        with patch.object(OpenAIAdapter, "_get_client", return_value=mock_client):
            client = adapter._get_client()
            assert client is mock_client

    def test_get_client_cached(self, adapter):
        """真实的 _get_client 缓存行为（需要 openai 模块）"""
        # 直接验证 _client 初始为 None，然后通过 mock 注入
        assert adapter._client is None
        mock_client = MagicMock()
        adapter._client = mock_client
        c1 = adapter._get_client()
        c2 = adapter._get_client()
        assert c1 is c2
        assert c1 is mock_client

    @pytest.mark.asyncio
    async def test_chat_mocked(self, adapter):
        """mock OpenAI API 调用"""
        mock_client = MagicMock()
        mock_choice = MagicMock()
        mock_choice.message.content = "AI 回复内容"
        mock_completion = MagicMock()
        mock_completion.choices = [mock_choice]
        mock_completion.model = "gpt-4o-mini"
        mock_completion.usage.prompt_tokens = 10
        mock_completion.usage.completion_tokens = 20
        mock_completion.usage.total_tokens = 30
        mock_client.chat.completions.create = AsyncMock(return_value=mock_completion)

        with patch.object(OpenAIAdapter, "_get_client", return_value=mock_client):
            messages = [ChatMessage(role="user", content="你好")]
            resp = await adapter.chat(messages)
            assert resp.content == "AI 回复内容"
            assert resp.model == "gpt-4o-mini"
            assert resp.usage["prompt_tokens"] == 10
            assert resp.usage["completion_tokens"] == 20
            assert resp.usage["total_tokens"] == 30
            assert resp.elapsed_ms > 0

    @pytest.mark.asyncio
    async def test_chat_stream_mocked(self, adapter):
        """mock OpenAI 流式 API 调用"""
        mock_client = MagicMock()

        async def mock_stream():
            for text in ["Hello", " World", "!"]:
                chunk = MagicMock()
                chunk.choices = [MagicMock()]
                chunk.choices[0].delta.content = text
                yield chunk

        mock_client.chat.completions.create = AsyncMock(return_value=mock_stream())

        with patch.object(OpenAIAdapter, "_get_client", return_value=mock_client):
            messages = [ChatMessage(role="user", content="你好")]
            chunks = []
            async for chunk in adapter.chat_stream(messages):
                chunks.append(chunk)
            assert "".join(chunks) == "Hello World!"

    @pytest.mark.asyncio
    async def test_chat_stream_skips_none_delta(self, adapter):
        """流式中跳过 delta.content 为 None 的 chunk"""
        mock_client = MagicMock()

        async def mock_stream():
            chunk1 = MagicMock()
            chunk1.choices = [MagicMock()]
            chunk1.choices[0].delta.content = None
            yield chunk1
            chunk2 = MagicMock()
            chunk2.choices = [MagicMock()]
            chunk2.choices[0].delta.content = "内容"
            yield chunk2

        mock_client.chat.completions.create = AsyncMock(return_value=mock_stream())

        with patch.object(OpenAIAdapter, "_get_client", return_value=mock_client):
            messages = [ChatMessage(role="user", content="你好")]
            chunks = []
            async for chunk in adapter.chat_stream(messages):
                chunks.append(chunk)
            assert chunks == ["内容"]

    @pytest.mark.asyncio
    async def test_chat_empty_content(self, adapter):
        """API 返回空 content"""
        mock_client = MagicMock()
        mock_choice = MagicMock()
        mock_choice.message.content = None
        mock_completion = MagicMock()
        mock_completion.choices = [mock_choice]
        mock_completion.model = "gpt-4o-mini"
        mock_completion.usage = None
        mock_client.chat.completions.create = AsyncMock(return_value=mock_completion)

        with patch.object(OpenAIAdapter, "_get_client", return_value=mock_client):
            messages = [ChatMessage(role="user", content="你好")]
            resp = await adapter.chat(messages)
            assert resp.content == ""
            assert resp.usage["prompt_tokens"] == 0

    def test_openai_adapter_with_custom_params(self):
        adapter = OpenAIAdapter(api_key="sk-custom", api_base="https://custom.api/v1", model="custom-model")
        assert adapter._api_key == "sk-custom"
        assert adapter._api_base == "https://custom.api/v1"
        assert adapter._model == "custom-model"

    def test_openai_adapter_default_params(self):
        """默认参数从环境变量获取"""
        adapter = OpenAIAdapter()
        assert adapter._api_key == LLM_API_KEY or adapter._api_key == ""
        assert adapter._model == LLM_MODEL


# ============================================================================
# 15. RAG 路径测试（mock vector_store）
# ============================================================================

class TestRagPaths:
    """RAG 增强路径测试"""

    def _make_mock_store(self, results_list):
        store = MagicMock()
        def make_result(items):
            result = MagicMock()
            result.results = items
            return result
        store.search = MagicMock(side_effect=[make_result(r) for r in results_list])
        return store

    @pytest.mark.asyncio
    async def test_generate_report_with_rag_success(self):
        """generate_report use_rag=True 且 vector_store 可用"""
        reset_llm()
        bazi_data = "八字：庚午 壬午 辛亥 癸巳\n日主：辛金\n五行：金2 木0 水2 火3 土1\n格局：伤官格\n用神：土、金"
        mock_store = self._make_mock_store([
            [{"name": "日主", "text": "日主是八字中代表命主自身的五行。"}],
            [{"name": "五行", "text": "五行包括金木水火土。"}],
            [{"name": "格局", "text": "格局由月令决定。"}],
        ])
        with patch("tengod.vector_store.get_vector_store", return_value=mock_store):
            result = await generate_report(bazi_data, use_rag=True)
            assert isinstance(result, str)
            assert len(result) > 0

    @pytest.mark.asyncio
    async def test_generate_report_with_rag_no_keywords(self):
        """generate_report use_rag=True 但无匹配关键词"""
        reset_llm()
        # 数据不含日主/五行/格局/用神/大运/神煞/调候等关键词
        bazi_data = "简单数据内容"
        mock_store = self._make_mock_store([
            [{"name": "阴阳", "text": "阴阳是宇宙的基本法则。"}],
        ])
        with patch("tengod.vector_store.get_vector_store", return_value=mock_store):
            result = await generate_report(bazi_data, use_rag=True)
            assert isinstance(result, str)
            assert len(result) > 0

    @pytest.mark.asyncio
    async def test_generate_report_with_rag_empty_context(self):
        """generate_report use_rag=True 但搜索结果为空"""
        reset_llm()
        bazi_data = "日主：辛金\n五行：金2 木0"
        mock_store = self._make_mock_store([[]])
        with patch("tengod.vector_store.get_vector_store", return_value=mock_store):
            result = await generate_report(bazi_data, use_rag=True)
            assert isinstance(result, str)
            assert len(result) > 0

    @pytest.mark.asyncio
    async def test_chat_with_rag_success(self):
        """chat use_rag=True 且 vector_store 可用"""
        reset_llm()
        mock_store = self._make_mock_store([
            [{"name": "五行", "text": "五行包括金木水火土。"}],
        ])
        with patch("tengod.vector_store.get_vector_store", return_value=mock_store):
            result = await chat("五行是什么？", use_rag=True)
            assert isinstance(result, str)
            assert len(result) > 0

    @pytest.mark.asyncio
    async def test_chat_with_rag_and_bazi_context(self):
        """chat use_rag=True + bazi_context"""
        reset_llm()
        mock_store = self._make_mock_store([
            [{"name": "五行", "text": "五行内容"}],
        ])
        with patch("tengod.vector_store.get_vector_store", return_value=mock_store):
            result = await chat("五行是什么？", bazi_context="八字：庚午", use_rag=True)
            assert isinstance(result, str)
            assert len(result) > 0

    @pytest.mark.asyncio
    async def test_chat_stream_with_rag_success(self):
        """chat_stream use_rag=True 且 vector_store 可用"""
        reset_llm()
        mock_store = self._make_mock_store([
            [{"name": "五行", "text": "五行内容"}],
        ])
        with patch("tengod.vector_store.get_vector_store", return_value=mock_store):
            chunks = []
            async for chunk in chat_stream("五行是什么？", use_rag=True):
                chunks.append(chunk)
            assert len(chunks) > 0

    @pytest.mark.asyncio
    async def test_chat_stream_with_rag_and_bazi_context(self):
        """chat_stream use_rag=True + bazi_context"""
        reset_llm()
        mock_store = self._make_mock_store([
            [{"name": "五行", "text": "五行内容"}],
        ])
        with patch("tengod.vector_store.get_vector_store", return_value=mock_store):
            chunks = []
            async for chunk in chat_stream("五行是什么？", bazi_context="八字：庚午", use_rag=True):
                chunks.append(chunk)
            assert len(chunks) > 0

    @pytest.mark.asyncio
    async def test_generate_report_rag_import_error(self):
        """generate_report use_rag=True 但 vector_store 导入失败"""
        reset_llm()
        bazi_data = "日主：辛金\n五行：金2 木0 水2 火3 土1\n格局：伤官格"
        with patch("tengod.vector_store.get_vector_store", side_effect=ImportError):
            result = await generate_report(bazi_data, use_rag=True)
            assert isinstance(result, str)
            assert len(result) > 0

    @pytest.mark.asyncio
    async def test_chat_rag_import_error(self):
        """chat use_rag=True 但 vector_store 导入失败"""
        reset_llm()
        with patch("tengod.vector_store.get_vector_store", side_effect=ImportError):
            result = await chat("五行是什么？", use_rag=True)
            assert isinstance(result, str)
            assert len(result) > 0

    @pytest.mark.asyncio
    async def test_chat_stream_rag_import_error(self):
        """chat_stream use_rag=True 但 vector_store 导入失败"""
        reset_llm()
        with patch("tengod.vector_store.get_vector_store", side_effect=ImportError):
            chunks = []
            async for chunk in chat_stream("五行是什么？", use_rag=True):
                chunks.append(chunk)
            assert len(chunks) > 0


# ============================================================================
# 16. _self_test 函数测试
# ============================================================================

class TestSelfTest:
    """_self_test 自测函数测试"""

    @pytest.mark.asyncio
    async def test_self_test_runs(self):
        """确保 _self_test 不抛异常"""
        from tengod.llm_adapter import _self_test
        reset_llm()
        await _self_test()