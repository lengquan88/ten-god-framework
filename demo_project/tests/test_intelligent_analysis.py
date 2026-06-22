#!/usr/bin/env python3
"""
test_intelligent_analysis.py — 智能分析引擎单元测试
覆盖：八字解读、流年分析、合婚、事业财运、综合引擎
使用 mock 避免真实 AI 调用
"""
import os
import sys
from unittest.mock import AsyncMock, patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from tengod.deepseek_adapter import DeepseekResponse, Message
from tengod.intelligent_analysis import (
    AnalysisResult,
    BaziInterpreter,
    LiunianAnalyzer,
    MarriageAnalyzer,
    CareerAnalyzer,
    IntelligentAnalysisEngine,
    get_engine,
    analyze_bazi as engine_analyze_bazi,
    analyze_year,
)


# ════════════════════════════════════════
# 测试数据
# ════════════════════════════════════════

SAMPLE_BAZI = {
    "pillars": {
        "year": "甲子",
        "month": "丙寅",
        "day": "戊午",
        "hour": "庚申"
    },
    "wuxing": {"木": 2, "火": 1, "土": 1, "金": 1, "水": 3},
    "geju": "正官格",
    "shensha": ["天乙贵人", "文昌"]
}


def make_mock_response(content: str = "AI分析结果") -> DeepseekResponse:
    """构造 mock 响应"""
    return DeepseekResponse(
        content=content,
        model="deepseek-chat",
        usage={"prompt_tokens": 10, "completion_tokens": 20},
        finish_reason="stop"
    )


# ════════════════════════════════════════
# 1. AnalysisResult 数据类
# ════════════════════════════════════════

class TestAnalysisResult:
    """分析结果数据类"""

    def test_default_values(self):
        result = AnalysisResult(title="测试", content="内容")
        assert result.title == "测试"
        assert result.content == "内容"
        assert result.score == 0.0
        assert result.tags == []
        assert result.recommendations == []
        assert result.created_at is not None

    def test_with_values(self):
        result = AnalysisResult(
            title="事业分析",
            content="事业运势良好",
            score=85.5,
            tags=["事业", "财运"],
            recommendations=["建议1", "建议2"]
        )
        assert result.score == 85.5
        assert len(result.tags) == 2
        assert len(result.recommendations) == 2


# ════════════════════════════════════════
# 2. BaziInterpreter 八字解读器
# ════════════════════════════════════════

class TestBaziInterpreter:
    """八字命盘解读器"""

    def test_build_prompt_contains_pillars(self):
        interp = BaziInterpreter(client=AsyncMock())
        prompt = interp._build_prompt(SAMPLE_BAZI, "综合")
        assert "甲子" in prompt
        assert "丙寅" in prompt
        assert "戊午" in prompt
        assert "庚申" in prompt

    def test_build_prompt_contains_focus(self):
        interp = BaziInterpreter(client=AsyncMock())
        prompt = interp._build_prompt(SAMPLE_BAZI, "事业")
        assert "事业" in prompt

    def test_build_prompt_contains_wuxing(self):
        interp = BaziInterpreter(client=AsyncMock())
        prompt = interp._build_prompt(SAMPLE_BAZI, "综合")
        assert "木：2" in prompt
        assert "水：3" in prompt

    def test_build_prompt_contains_geju(self):
        interp = BaziInterpreter(client=AsyncMock())
        prompt = interp._build_prompt(SAMPLE_BAZI, "综合")
        assert "正官格" in prompt

    def test_build_prompt_contains_shensha(self):
        interp = BaziInterpreter(client=AsyncMock())
        prompt = interp._build_prompt(SAMPLE_BAZI, "综合")
        assert "天乙贵人" in prompt

    def test_parse_response_basic(self):
        interp = BaziInterpreter(client=AsyncMock())
        result = interp._parse_response("分析内容", "综合")
        assert isinstance(result, AnalysisResult)
        assert result.title == "综合分析"
        assert result.content == "分析内容"
        assert result.score == 75.0
        assert "综合" in result.tags

    def test_parse_response_extracts_recommendations(self):
        interp = BaziInterpreter(client=AsyncMock())
        content = """命盘分析
建议：多读书
推荐：修身养性
建议：广结善缘"""
        result = interp._parse_response(content, "综合")
        assert len(result.recommendations) <= 3
        assert any("建议" in r or "推荐" in r for r in result.recommendations)

    @pytest.mark.asyncio
    async def test_interpret_with_mock(self):
        mock_client = AsyncMock()
        mock_client.chat = AsyncMock(return_value=make_mock_response("八字解读结果"))

        interp = BaziInterpreter(client=mock_client)
        result = await interp.interpret(SAMPLE_BAZI, "事业")

        assert isinstance(result, AnalysisResult)
        assert result.content == "八字解读结果"
        mock_client.chat.assert_awaited_once()


# ════════════════════════════════════════
# 3. LiunianAnalyzer 流年分析器
# ════════════════════════════════════════

class TestLiunianAnalyzer:
    """流年运势分析器"""

    @pytest.mark.asyncio
    async def test_analyze_year_with_mock(self):
        mock_client = AsyncMock()
        mock_client.chat = AsyncMock(return_value=make_mock_response("2026年运势"))

        analyzer = LiunianAnalyzer()
        with patch("tengod.intelligent_analysis.get_client", return_value=mock_client):
            result = await analyzer.analyze_year(SAMPLE_BAZI, 2026)

        assert isinstance(result, AnalysisResult)
        assert "2026" in result.title
        assert result.score == 80.0
        assert "流年" in result.tags


# ════════════════════════════════════════
# 4. MarriageAnalyzer 合婚分析器
# ════════════════════════════════════════

class TestMarriageAnalyzer:
    """合婚分析器"""

    @pytest.mark.asyncio
    async def test_analyze_compatibility_with_mock(self):
        mock_client = AsyncMock()
        mock_client.chat = AsyncMock(return_value=make_mock_response("匹配度85%"))

        male = {"pillars": {"year": "甲子", "day": "戊午"}}
        female = {"pillars": {"year": "乙丑", "day": "己未"}}

        analyzer = MarriageAnalyzer()
        with patch("tengod.intelligent_analysis.get_client", return_value=mock_client):
            result = await analyzer.analyze_compatibility(male, female)

        assert isinstance(result, AnalysisResult)
        assert result.title == "合婚分析"
        assert result.score == 85.0
        assert "合婚" in result.tags


# ════════════════════════════════════════
# 5. CareerAnalyzer 事业财运分析器
# ════════════════════════════════════════

class TestCareerAnalyzer:
    """事业财运分析器"""

    @pytest.mark.asyncio
    async def test_analyze_career_with_mock(self):
        mock_client = AsyncMock()
        mock_client.chat = AsyncMock(return_value=make_mock_response("事业方向：科技行业"))

        analyzer = CareerAnalyzer()
        with patch("tengod.intelligent_analysis.get_client", return_value=mock_client):
            result = await analyzer.analyze_career(SAMPLE_BAZI, 30)

        assert isinstance(result, AnalysisResult)
        assert "事业" in result.title
        assert result.score == 78.0
        assert "事业" in result.tags


# ════════════════════════════════════════
# 6. IntelligentAnalysisEngine 综合引擎
# ════════════════════════════════════════

class TestIntelligentAnalysisEngine:
    """智能分析综合引擎"""

    def test_init_creates_all_analyzers(self):
        engine = IntelligentAnalysisEngine()
        assert isinstance(engine.bazi_interpreter, BaziInterpreter)
        assert isinstance(engine.liunian_analyzer, LiunianAnalyzer)
        assert isinstance(engine.marriage_analyzer, MarriageAnalyzer)
        assert isinstance(engine.career_analyzer, CareerAnalyzer)

    @pytest.mark.asyncio
    async def test_full_analysis_basic_only(self):
        """仅基础分析（无选项）"""
        mock_client = AsyncMock()
        mock_client.chat = AsyncMock(return_value=make_mock_response("基础解读"))

        engine = IntelligentAnalysisEngine()
        engine.bazi_interpreter.client = mock_client

        result = await engine.full_analysis(SAMPLE_BAZI)
        assert "基础" in result
        assert isinstance(result["基础"], AnalysisResult)

    @pytest.mark.asyncio
    async def test_full_analysis_with_career(self):
        """包含事业分析"""
        mock_client = AsyncMock()
        mock_client.chat = AsyncMock(return_value=make_mock_response("事业分析"))

        engine = IntelligentAnalysisEngine()
        engine.bazi_interpreter.client = mock_client

        with patch("tengod.intelligent_analysis.get_client", return_value=mock_client):
            result = await engine.full_analysis(
                SAMPLE_BAZI,
                options={"career": True, "age": 30}
            )

        assert "基础" in result
        assert "事业" in result

    @pytest.mark.asyncio
    async def test_full_analysis_with_year(self):
        """包含流年分析"""
        mock_client = AsyncMock()
        mock_client.chat = AsyncMock(return_value=make_mock_response("流年"))

        engine = IntelligentAnalysisEngine()
        engine.bazi_interpreter.client = mock_client

        with patch("tengod.intelligent_analysis.get_client", return_value=mock_client):
            result = await engine.full_analysis(
                SAMPLE_BAZI,
                options={"year": 2026}
            )

        assert "基础" in result
        assert "流年" in result

    @pytest.mark.asyncio
    async def test_quick_analysis(self):
        mock_client = AsyncMock()
        mock_client.chat = AsyncMock(return_value=make_mock_response("命盘概括"))

        engine = IntelligentAnalysisEngine()
        with patch("tengod.intelligent_analysis.get_client", return_value=mock_client):
            result = await engine.quick_analysis(SAMPLE_BAZI)

        assert result == "命盘概括"


# ════════════════════════════════════════
# 7. 便捷函数
# ════════════════════════════════════════

class TestConvenienceFunctions:
    """便捷函数测试"""

    def test_get_engine_singleton(self):
        """get_engine 应返回单例"""
        import tengod.intelligent_analysis as mod
        mod._engine = None

        e1 = get_engine()
        e2 = get_engine()
        assert e1 is e2

    @pytest.mark.asyncio
    async def test_analyze_bazi_convenience(self):
        mock_client = AsyncMock()
        mock_client.chat = AsyncMock(return_value=make_mock_response("便捷分析"))

        # 重置全局引擎，确保使用 mock 客户端
        import tengod.intelligent_analysis as mod
        mod._engine = None

        with patch("tengod.intelligent_analysis.get_client", return_value=mock_client):
            # 重新创建引擎以使用 mock 客户端
            engine = IntelligentAnalysisEngine()
            engine.bazi_interpreter.client = mock_client
            with patch("tengod.intelligent_analysis.get_engine", return_value=engine):
                result = await engine_analyze_bazi(SAMPLE_BAZI)

        assert isinstance(result, AnalysisResult)

    @pytest.mark.asyncio
    async def test_analyze_year_convenience(self):
        mock_client = AsyncMock()
        mock_client.chat = AsyncMock(return_value=make_mock_response("流年便捷"))

        with patch("tengod.intelligent_analysis.get_client", return_value=mock_client):
            result = await analyze_year(SAMPLE_BAZI, 2026)

        assert isinstance(result, AnalysisResult)
