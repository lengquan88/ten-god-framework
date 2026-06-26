#!/usr/bin/env python3
"""
test_v22_api.py — v2.2 新 API 端点单元测试
覆盖：真太阳时/节气/五行旺衰/命盘可视化/AI分析 端点
使用 FastAPI TestClient 或直接调用函数
"""
import os
import sys
import json
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

# ── v2.17.0: 将模块级 sys.modules 污染移到 autouse fixture 中 ──
# 原模块级代码 sys.modules['tengod.auth'] = MagicMock() 在 pytest 收集阶段
# 即污染全局状态，导致 test_bazi_api.py 等测试的 PasswordHasher.hash() 返回 MagicMock。
# 现在通过 fixture 设置 mock 并在测试结束后清理，不影响其他测试。

@pytest.fixture(autouse=True)
def _mock_tengod_modules_for_v22():
    """仅在本文件测试中 mock tengod.auth 和 metrics_collector，测试后恢复"""
    # 保存原始模块
    _orig_auth = sys.modules.get('tengod.auth')
    _orig_metrics = sys.modules.get('tengod.metrics_collector')

    # 设置 mock
    mock_auth = MagicMock()
    mock_auth.authorize = MagicMock(return_value=None)
    mock_metrics = MagicMock()
    mock_metrics.metrics = MagicMock()

    sys.modules['tengod.auth'] = mock_auth
    sys.modules['tengod.metrics_collector'] = mock_metrics

    yield

    # 恢复原始模块
    if _orig_auth is not None:
        sys.modules['tengod.auth'] = _orig_auth
    else:
        sys.modules.pop('tengod.auth', None)

    if _orig_metrics is not None:
        sys.modules['tengod.metrics_collector'] = _orig_metrics
    else:
        sys.modules.pop('tengod.metrics_collector', None)

@pytest.fixture
def mock_auth():
    """Mock authorize 函数"""
    yield


@pytest.fixture
def mock_metrics():
    """Mock metrics"""
    yield


# ════════════════════════════════════════
# 1. 真太阳时端点
# ════════════════════════════════════════

class TestSolarTimeAPI:
    """/api/v2/solar-time"""

    @pytest.mark.asyncio
    async def test_solar_time_valid(self, mock_auth):
        from tengod.api_server import v2_solar_time, SolarTimeRequest, Request
        from fastapi import Request as FastAPIRequest
        req = SolarTimeRequest(year=1990, month=6, day=15, hour=10, minute=30, longitude=116.4)
        mock_request = MagicMock(spec=Request)
        result = await v2_solar_time(req, mock_request)
        assert result["solar_time"] is not None
        assert result["shichen"] in ["子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥"]
        assert "time_correction_minutes" in result

    @pytest.mark.asyncio
    async def test_solar_time_default_longitude(self, mock_auth):
        from tengod.api_server import v2_solar_time, SolarTimeRequest, Request
        req = SolarTimeRequest(year=2026, month=6, day=22, hour=12, minute=0, longitude=120.0)
        mock_request = MagicMock(spec=Request)
        result = await v2_solar_time(req, mock_request)
        assert result["input"]["longitude"] == 120.0

    @pytest.mark.asyncio
    async def test_solar_time_extreme_longitude(self, mock_auth):
        from tengod.api_server import v2_solar_time, SolarTimeRequest, Request
        req = SolarTimeRequest(year=2000, month=1, day=1, hour=12, minute=0, longitude=70.0)
        mock_request = MagicMock(spec=Request)
        result = await v2_solar_time(req, mock_request)
        assert "solar_time" in result


# ════════════════════════════════════════
# 2. 节气端点
# ════════════════════════════════════════

class TestJieqiAPI:
    """ /api/v2/jieqi """

    @pytest.mark.asyncio
    async def test_jieqi_lichun(self, mock_auth):
        from tengod.api_server import v2_jieqi, JieqiRequest, Request
        req = JieqiRequest(year=2026, month=2, day=4)
        mock_request = MagicMock(spec=Request)
        result = await v2_jieqi(req, mock_request)
        assert result["current_jieqi"] == "立春"
        assert result["is_jieqi_day"] is True

    @pytest.mark.asyncio
    async def test_jieqi_normal_day(self, mock_auth):
        from tengod.api_server import v2_jieqi, JieqiRequest, Request
        req = JieqiRequest(year=2026, month=6, day=22)
        mock_request = MagicMock(spec=Request)
        result = await v2_jieqi(req, mock_request)
        assert result["current_jieqi"] is not None
        assert result["next_jieqi"] is not None


# ════════════════════════════════════════
# 3. 五行旺衰端点
# ════════════════════════════════════════

class TestWuxingStrengthAPI:
    """ /api/v2/wuxing/strength """

    @pytest.mark.asyncio
    async def test_wuxing_all(self, mock_auth):
        from tengod.api_server import v2_wuxing_strength, WuxingStrengthRequest, Request
        req = WuxingStrengthRequest(month=3)
        mock_request = MagicMock(spec=Request)
        result = await v2_wuxing_strength(req, mock_request)
        assert result["season"] == "春"
        assert len(result["strengths"]) == 5
        assert result["strengths"]["木"]["status"] == "旺"

    @pytest.mark.asyncio
    async def test_wuxing_single(self, mock_auth):
        from tengod.api_server import v2_wuxing_strength, WuxingStrengthRequest, Request
        req = WuxingStrengthRequest(month=6, element="火")
        mock_request = MagicMock(spec=Request)
        result = await v2_wuxing_strength(req, mock_request)
        assert result["element"] == "火"
        assert result["status"] == "旺"
        assert result["strength"] == 100


# ════════════════════════════════════════
# 4. 命盘可视化端点
# ════════════════════════════════════════

class TestChartBaziAPI:
    """ /api/v2/chart/bazi """

    @pytest.mark.asyncio
    async def test_chart_html(self, mock_auth):
        from tengod.api_server import v2_chart_bazi, ChartBaziRequest, BaziInput, Request
        bazi = BaziInput(year=1990, month=6, day=15, hour=10, minute=30, gender="male")
        req = ChartBaziRequest(bazi=bazi, theme="classic", format="html")
        mock_request = MagicMock(spec=Request)
        from fastapi.responses import HTMLResponse
        result = await v2_chart_bazi(req, mock_request)
        assert isinstance(result, HTMLResponse)
        assert b"<!DOCTYPE html>" in result.body

    @pytest.mark.asyncio
    async def test_chart_json(self, mock_auth):
        from tengod.api_server import v2_chart_bazi, ChartBaziRequest, BaziInput, Request
        bazi = BaziInput(year=1990, month=6, day=15, hour=10, minute=30, gender="female")
        req = ChartBaziRequest(bazi=bazi, theme="modern", format="json")
        mock_request = MagicMock(spec=Request)
        result = await v2_chart_bazi(req, mock_request)
        assert "json" in result
        assert result["json"]["pillars"]["year"] is not None


# ════════════════════════════════════════
# 5. AI 分析端点
# ════════════════════════════════════════

class TestAIAnalyzeAPI:
    """ /api/v2/ai/analyze """

    @pytest.mark.asyncio
    async def test_ai_analyze_basic(self, mock_auth, mock_metrics):
        from tengod.api_server import v2_ai_analyze, AIAnalyzeRequest, BaziInput, Request
        from tengod.deepseek_adapter import DeepseekResponse

        bazi = BaziInput(year=1990, month=6, day=15, hour=10, minute=30, gender="male")
        req = AIAnalyzeRequest(bazi=bazi, analysis_type="basic", focus="综合")
        mock_request = MagicMock(spec=Request)

        mock_response = DeepseekResponse(content="八字分析测试", model="deepseek-chat", usage={}, finish_reason="stop")
        with patch("tengod.intelligent_analysis.IntelligentAnalysisEngine.full_analysis",
                   new_callable=AsyncMock) as mock_engine:
            from tengod.intelligent_analysis import AnalysisResult
            mock_engine.return_value = {
                "基础": AnalysisResult(title="综合解读", content="八字分析测试", score=80.0, tags=["综合"])
            }
            result = await v2_ai_analyze(req, mock_request)

        assert result["analysis_type"] == "basic"
        assert "results" in result
        assert "基础" in result["results"]

    @pytest.mark.asyncio
    async def test_ai_analyze_career(self, mock_auth, mock_metrics):
        from tengod.api_server import v2_ai_analyze, AIAnalyzeRequest, BaziInput, Request
        from tengod.intelligent_analysis import AnalysisResult

        bazi = BaziInput(year=1990, month=6, day=15, hour=10, minute=30, gender="female")
        req = AIAnalyzeRequest(bazi=bazi, analysis_type="career", focus="事业", age=35)
        mock_request = MagicMock(spec=Request)

        with patch("tengod.intelligent_analysis.IntelligentAnalysisEngine.full_analysis",
                   new_callable=AsyncMock) as mock_engine:
            mock_engine.return_value = {
                "基础": AnalysisResult(title="综合解读", content="分析", score=75.0),
                "事业": AnalysisResult(title="事业分析", content="事业方向", score=78.0, tags=["事业"])
            }
            result = await v2_ai_analyze(req, mock_request)

        assert "事业" in result["results"]


# ════════════════════════════════════════
# 6. 知识融合引擎
# ════════════════════════════════════════

class TestKnowledgeFusion:
    """知识融合引擎测试"""

    def test_get_fusion_engine_singleton(self):
        from tengod.knowledge_fusion import get_fusion_engine
        e1 = get_fusion_engine()
        e2 = get_fusion_engine()
        assert e1 is e2

    def test_init_base_knowledge(self):
        from tengod.knowledge_fusion import get_fusion_engine, init_base_knowledge
        engine = get_fusion_engine()
        n = init_base_knowledge(engine)
        assert n >= 37  # 27节点 + 10边

    def test_keyword_extraction(self):
        from tengod.knowledge_fusion import get_fusion_engine
        engine = get_fusion_engine()
        bazi_data = {
            "pillars": {"year": "甲子", "month": "丙寅", "day": "戊午", "hour": "庚申"},
            "wuxing": {"木": 1, "火": 1, "土": 1, "金": 1, "水": 1},
            "geju": "正官格",
            "shensha": ["天乙贵人", "文昌"]
        }
        keywords = engine._extract_keywords(bazi_data)
        assert "甲" in keywords
        assert "木" in keywords
        assert "正官格" in keywords
        assert "天乙贵人" in keywords

    def test_export_graph_visualization(self):
        from tengod.knowledge_fusion import get_fusion_engine, init_base_knowledge
        from tengod.graph_engine import get_graph_db
        engine = get_fusion_engine()
        init_base_knowledge(engine)
        graph_db = get_graph_db()
        nodes = list(graph_db._nodes.values())[:10]
        edges = list(graph_db._edges)[:5]
        vis = engine.export_graph_visualization(nodes, edges)
        assert "nodes" in vis
        assert "links" in vis
        assert "categories" in vis

    def test_knowledge_graph_visualization(self):
        from tengod.knowledge_fusion import KnowledgeGraphVisualization, get_fusion_engine, init_base_knowledge
        from tengod.graph_engine import get_graph_db
        engine = get_fusion_engine()
        init_base_knowledge(engine)
        graph_db = get_graph_db()
        nodes = list(graph_db._nodes.values())[:10]
        edges = list(graph_db._edges)[:5]

        echart_json = KnowledgeGraphVisualization.to_echarts_json(engine, nodes, edges)
        data = json.loads(echart_json)
        assert "nodes" in data

        d3_json = KnowledgeGraphVisualization.to_d3_json(engine, nodes, edges)
        d3_data = json.loads(d3_json)
        assert "nodes" in d3_data
        assert "links" in d3_data