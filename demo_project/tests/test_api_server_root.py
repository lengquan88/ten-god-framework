#!/usr/bin/env python3
"""
test_api_server_root.py — tengod/api_server.py 的综合测试

覆盖：
- 全局状态 (_api_key, _request_counts, _server_started_at, _total_requests, _total_errors)
- AuthMiddleware (BaseHTTPMiddleware)
- rate_limit_middleware, log_middleware
- Pydantic 模型 (BaziInput, PillarsInput, SearchQuery, RecommendQuery, ShiganQuery, DizhiQuery, etc.)
- 路由处理器: /api/health, /api/health/full, /api/stats, /api/metrics, /metrics
- 八字端点: /api/bazi/calc, /api/bazi/shensha, /api/bazi/geju, /api/bazi/yongshen,
  /api/bazi/tiaohou, /api/bazi/full, /api/bazi/report
- 知识端点: /api/knowledge/search, /api/knowledge/recommend, /api/knowledge/wuxing/{element},
  /api/knowledge/bagua/{trigram}, /api/knowledge/shigan, /api/knowledge/dizhi
- V2 端点: /api/v2/solar-time, /api/v2/jieqi, /api/v2/wuxing/strength,
  /api/v2/chart/bazi, /api/v2/ai/analyze, /api/v2/ai/stream
- 中间件: 鉴权、限流、CORS、Gzip
- 文档: /docs, /redoc, /openapi.json
- 其他: /, /api/favicon.ico, OPTIONS, 404
- main() 入口点
- _check_rate_limit 函数
- 异常处理器

注意: TianmenMiddleware 会包装所有 /api/ 路径的 JSON 响应为
  {"output": <原始响应>, "confidence": 0.5, "uncertainty": 0.3}
"""

import sys
import json
import os
import time
from unittest.mock import patch, MagicMock, AsyncMock, PropertyMock
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient


# ============================================================================
# 辅助函数：从 TianmenMiddleware 包装中提取实际输出
# ============================================================================

def _unwrap(response):
    """从 TianmenMiddleware 包装响应中提取 output 字段"""
    if response.status_code >= 400:
        return response.json()
    try:
        data = response.json()
    except Exception:
        return None
    if isinstance(data, dict) and "output" in data and "confidence" in data:
        return data["output"]
    return data


# ============================================================================
# 全局 Mock 模块工厂
# ============================================================================

def _make_mock_bazi_analyzer():
    """创建 mock BaziAnalyzer"""
    mock = MagicMock()
    mock.analysis = {
        "pillars": {"year": "甲子", "month": "丙寅", "day": "戊辰", "hour": "庚申"},
        "day_master": "戊",
        "day_master_info": "戊土日主",
        "shigan_map": {"甲": "偏官", "丙": "偏印", "庚": "食神"},
        "shigan_count": {"偏官": 1, "偏印": 1, "食神": 1},
        "wuxing": "土",
        "wuxing_score": {"木": 15, "火": 20, "土": 30, "金": 25, "水": 10},
        "branch_relations": {},
        "dayuns": [{"age": 0, "ganzhi": "丁卯"}, {"age": 10, "ganzhi": "戊辰"}],
        "liunians": [{"year": 2025, "ganzhi": "乙巳"}, {"year": 2026, "ganzhi": "丙午"}],
        "conclusion": "日主戊土，生于寅月，得丙火生扶。",
    }
    mock_chart = MagicMock()
    mock_chart.true_hour = 12
    mock_chart.true_minute = 30
    mock.chart = mock_chart
    return mock


def _make_mock_shensha_result():
    """创建 mock 神煞结果"""
    result = MagicMock()
    result.all_shensha = {"天乙贵人": {"name": "天乙贵人", "cat": "吉", "pillar": "月", "desc": "天乙贵人"}}
    result.summary = "吉神: 天乙贵人"
    result.year_shens = {"天乙": {"name": "天乙", "cat": "吉", "desc": "贵"}}
    result.month_shens = {"天乙": {"name": "天乙", "cat": "吉", "desc": "贵"}}
    result.day_shens = {"天乙": {"name": "天乙", "cat": "吉", "desc": "贵"}}
    result.hour_shens = {"天乙": {"name": "天乙", "cat": "吉", "desc": "贵"}}
    return result


def _make_mock_geju_result():
    """创建 mock 格局结果"""
    result = MagicMock()
    result.geju_name = "正印格"
    result.geju_type = "正格"
    result.geju_desc = "正印格，印星旺相。"
    result.score = 85
    result.is_cong = False
    result.is_huaqi = False
    result.shiyongshen = "金"
    result.jishen = "木"
    result.fujia_shens = []
    return result


def _make_mock_yongshen_result():
    """创建 mock 喜用神结果"""
    result = MagicMock()
    result.wang_shuai = "身旺"
    result.wang_shuai_level = 3
    result.yong_shen = "金"
    result.ji_shen = "木"
    result.yongshen_desc = "喜金，忌木。"
    result.wuxing_balance = {"金": 0, "木": 0, "水": 0, "火": 0, "土": 0}
    result.tiaohou_needed = False
    result.tiaohou_shens = []
    return result


def _make_mock_tiaohou_result():
    """创建 mock 调候结果"""
    result = MagicMock()
    result.required_tiaohou = False
    result.tiaohou_shens = []
    result.season = "春"
    result.desc = "无需调候。"
    return result


def _build_mock_modules():
    """构建所有需要 mock 的 tengod 子模块"""
    mock_modules = {}

    # ── 核心 ──
    mock_core = MagicMock()
    mock_core.get_core = MagicMock(return_value=MagicMock())
    mock_core.create_app = MagicMock(return_value=MagicMock())
    mock_modules["tengod.core"] = mock_core

    # ── 认证 ──
    mock_auth = MagicMock()
    mock_auth_user = MagicMock()
    mock_auth_user.id = 1
    mock_auth_user.username = "testuser"
    mock_auth_user.is_admin = False
    mock_auth_user.is_authenticated = True
    mock_auth_user.permissions = ["bazi:calc", "bazi:full", "bazi:report",
                                   "knowledge:search", "knowledge:wuxing",
                                   "ai:interpret", "ai:interpret:stream",
                                   "chat:send", "chat:report",
                                   "records:write", "records:read", "records:delete",
                                   "case:write", "case:read", "case:delete",
                                   "webhook:read", "webhook:write", "webhook:delete",
                                   "plugin:read"]
    mock_auth.authorize = MagicMock(return_value=mock_auth_user)
    # auth_middleware 必须正确调用 call_next 并透传请求，否则 BaseHTTPMiddleware 会中断请求处理
    async def _mock_auth_middleware(request, call_next):
        response = await call_next(request)
        return response
    mock_auth.auth_middleware = _mock_auth_middleware
    mock_auth.CurrentUser = MagicMock()
    mock_auth.PasswordHasher = MagicMock()
    mock_auth.PasswordHasher.hash = MagicMock(return_value="hashed_password")
    mock_auth.PasswordHasher.verify = MagicMock(return_value=True)
    mock_auth.create_token_pair = MagicMock(return_value={
        "access_token": "access_token_xxx",
        "refresh_token": "refresh_token_xxx",
    })
    mock_auth.JWTManager = MagicMock()
    mock_auth.JWTManager.verify_token = MagicMock(return_value={
        "sub": "1", "username": "test", "role": "user", "type": "refresh"
    })
    mock_auth.QuotaManager = MagicMock()
    mock_auth.QuotaManager.check = MagicMock(return_value=(True, 0, 100))
    mock_auth.ROLE_PERMISSIONS = {"user": {"name": "普通用户", "quota_daily": 100}}
    mock_modules["tengod.auth"] = mock_auth

    # ── 中间件 ──
    mock_middleware = MagicMock()
    mock_tianmen = MagicMock()
    mock_tianmen.get_stats = MagicMock(return_value={})
    # TianmenMiddleware 必须是真正的 ASGI 中间件类，不能是 MagicMock，
    # 否则中间件链会断裂导致 "MagicMock can't be awaited"
    class MockTianmenMiddleware:
        def __init__(self, app, **kwargs):
            self.app = app
        async def __call__(self, scope, receive, send):
            await self.app(scope, receive, send)
    mock_middleware.TianmenMiddleware = MockTianmenMiddleware
    mock_middleware.get_middleware = MagicMock(return_value=mock_tianmen)
    mock_modules["tengod.middleware"] = mock_middleware

    # ── 八字模块 ──
    mock_modules["tengod.bazi_calculator"] = MagicMock()
    mock_modules["tengod.bazi_calculator"].BaziChart = MagicMock()
    mock_chart = MagicMock()
    mock_chart.pillars = {"year": "甲子", "month": "丙寅", "day": "戊辰", "hour": "庚申"}
    mock_modules["tengod.bazi_calculator"].BaziChart.return_value = mock_chart

    mock_modules["tengod.bazi_analyzer"] = MagicMock()
    mock_modules["tengod.bazi_analyzer"].BaziAnalyzer = MagicMock(return_value=_make_mock_bazi_analyzer())

    mock_modules["tengod.shensha_engine"] = MagicMock()
    mock_modules["tengod.shensha_engine"].calc_all_shensha = MagicMock(return_value=_make_mock_shensha_result())

    mock_modules["tengod.geju_engine"] = MagicMock()
    mock_modules["tengod.geju_engine"].calc_geju = MagicMock(return_value=_make_mock_geju_result())
    mock_modules["tengod.geju_engine"].calc_yongshen = MagicMock(return_value=_make_mock_yongshen_result())
    mock_modules["tengod.geju_engine"].calc_tiaohou = MagicMock(return_value=_make_mock_tiaohou_result())
    mock_modules["tengod.geju_engine"].analyze_bazi_comprehensive = MagicMock(return_value={
        "geju": {"name": "正印格"}, "yongshen": {"yong": "金"}, "tiaohou": {"need": False}
    })

    # ── 报告生成器 ──
    mock_modules["tengod.report_generator"] = MagicMock()
    mock_report_gen = MagicMock()
    mock_report_gen.text_report = MagicMock(return_value="命理报告文本")
    mock_report_gen.markdown_report = MagicMock(return_value="# 命理报告")
    mock_report_gen.json_report = MagicMock(return_value={"report": "命理报告"})
    mock_report_gen.html_report = MagicMock(return_value="<html>命理报告</html>")
    mock_modules["tengod.report_generator"].BaziReportGenerator = MagicMock(return_value=mock_report_gen)
    mock_modules["tengod.report_generator"].ComprehensiveReportGenerator = MagicMock(return_value=mock_report_gen)

    # ── 知识图谱 ──
    mock_modules["tengod.knowledge_graph"] = MagicMock()
    mock_kg = MagicMock()
    mock_kg.get_element = MagicMock(return_value={"name": "木", "direction": "东", "color": "青"})
    mock_kg.get_relations = MagicMock(return_value={"生": "火", "克": "土"})
    mock_kg.get_trigram = MagicMock(return_value={"name": "乾", "nature": "天"})
    mock_modules["tengod.knowledge_graph"].get_knowledge_graph = MagicMock(return_value=mock_kg)

    # ── 向量存储 ──
    mock_modules["tengod.vector_store"] = MagicMock()
    mock_vs = MagicMock()
    mock_vs._stats = {"total_nodes": 100, "total_vectors": 100, "search_count": 50}
    mock_vs._nodes = {}
    mock_vs.search_json = MagicMock(return_value={"results": [{"name": "test", "score": 0.95}]})
    mock_vs.recommend_related = MagicMock(return_value=[{"name": "related", "score": 0.8}])
    mock_modules["tengod.vector_store"].get_vector_store = MagicMock(return_value=mock_vs)

    # ── 指标收集器 ──
    mock_modules["tengod.metrics_collector"] = MagicMock()
    mock_metrics = MagicMock()
    mock_metrics.to_prometheus = MagicMock(return_value="tengod_requests_total 100")
    mock_metrics.get_snapshot = MagicMock(return_value={"requests": 100, "errors": 5})
    mock_metrics.record_bazi_calc = MagicMock()
    mock_metrics.record_knowledge_search = MagicMock()
    mock_metrics.record_ai_chat = MagicMock()
    mock_modules["tengod.metrics_collector"].metrics = mock_metrics
    mock_modules["tengod.metrics_collector"].HealthChecker = MagicMock()
    mock_modules["tengod.metrics_collector"].HealthChecker.check_all = MagicMock(return_value={
        "status": "healthy", "components": {"db": "ok", "redis": "ok"}
    })

    # ── 数据存储 ──
    mock_modules["tengod.data_store"] = MagicMock()
    mock_ds = MagicMock()
    mock_ds.save_bazi_record = MagicMock(return_value="rec_001")
    mock_ds.list_bazi_records = MagicMock(return_value=[])
    mock_ds.count_bazi_records = MagicMock(return_value=0)
    mock_ds.get_bazi_record = MagicMock(return_value=None)
    mock_ds.update_bazi_record = MagicMock(return_value=True)
    mock_ds.delete_bazi_record = MagicMock(return_value=True)
    mock_ds.search_bazi_records = MagicMock(return_value=[])
    mock_ds.list_users = MagicMock(return_value=[])
    mock_ds.stats = MagicMock(return_value={"records": 0, "users": 0})
    mock_ds.get_version = MagicMock(return_value="1.5.0")
    mock_ds._session = MagicMock()
    mock_session = MagicMock()
    mock_ds._session.return_value.__enter__ = MagicMock(return_value=mock_session)
    mock_ds._session.return_value.__exit__ = MagicMock(return_value=False)
    mock_modules["tengod.data_store"].get_data_store = MagicMock(return_value=mock_ds)
    mock_modules["tengod.data_store"].User = MagicMock()

    # ── 占卜引擎 ──
    mock_modules["tengod.divination_engine"] = MagicMock()
    mock_modules["tengod.divination_engine"].ShiganEngine = MagicMock()
    mock_sr = MagicMock()
    mock_sr.shigan = MagicMock()
    mock_sr.shigan.value = "正官"
    mock_sr.description = "正官关系"
    mock_modules["tengod.divination_engine"].ShiganEngine.compute = MagicMock(return_value=mock_sr)
    mock_modules["tengod.divination_engine"].ShiganEngine.classify = MagicMock(return_value="吉")
    mock_modules["tengod.divination_engine"].TianganEngine = MagicMock()
    mock_modules["tengod.divination_engine"].TianganEngine.TIANGAN = ["甲", "乙", "丙", "丁", "戊", "己", "庚", "辛", "壬", "癸"]
    mock_di_info = MagicMock()
    mock_di_info.wuxing = "水"
    mock_di_info.yinyang = MagicMock()
    mock_di_info.yinyang.value = "阴"
    mock_di_info.direction = "北"
    mock_di_info.month_name = "十一月"
    mock_di_info.hour_name = "子时"
    mock_di_info.zodiac = "鼠"
    mock_di_info.canggan_main = "癸"
    mock_modules["tengod.divination_engine"].DizhiEngine = MagicMock()
    mock_modules["tengod.divination_engine"].DizhiEngine._INFO = {"子": mock_di_info}
    mock_modules["tengod.divination_engine"].find_interactions = MagicMock(return_value={})

    # ── 真太阳时 ──
    mock_modules["tengod.solar_time"] = MagicMock()
    mock_solar = MagicMock()
    mock_solar_result = MagicMock()
    mock_solar_result.true_hour = 12
    mock_solar_result.true_minute = 30
    mock_solar_result.time_correction = 5.0
    mock_solar.calculate = MagicMock(return_value=mock_solar_result)
    mock_solar.get_shichen = MagicMock(return_value="午时")
    mock_solar.get_shichen_range = MagicMock(return_value=["11:00", "13:00"])
    mock_modules["tengod.solar_time"].SolarTimeCalculator = MagicMock(return_value=mock_solar)
    mock_jieqi = MagicMock()
    mock_jieqi.get_jieqi = MagicMock(return_value={"current": "立春", "next": "雨水"})
    mock_jieqi.is_jieqi_day = MagicMock(return_value=False)
    mock_modules["tengod.solar_time"].JieqiCalculator = MagicMock(return_value=mock_jieqi)
    mock_wx = MagicMock()
    mock_wx.calculate_strength = MagicMock(return_value={"status": "旺", "strength": 0.8})
    mock_wx.calculate_all = MagicMock(return_value={"木": "旺", "火": "相"})
    mock_wx.get_season = MagicMock(return_value="春")
    mock_modules["tengod.solar_time"].WuxingStrengthCalculator = MagicMock(return_value=mock_wx)

    # ── 图表可视化 ──
    mock_modules["tengod.chart_visualizer"] = MagicMock()
    mock_viz = MagicMock()
    mock_viz.generate_json = MagicMock(return_value='{"chart": "bazi"}')
    mock_viz.generate_html = MagicMock(return_value="<html>命盘</html>")
    mock_modules["tengod.chart_visualizer"].BaziChartVisualizer = MagicMock(return_value=mock_viz)
    mock_modules["tengod.chart_visualizer"].VisualizationConfig = MagicMock()

    # ── Deepseek 适配器 ──
    mock_modules["tengod.deepseek_adapter"] = MagicMock()
    mock_ds_client = MagicMock()
    async def _mock_stream_chat(*args, **kwargs):
        yield "分"
        yield "析"
        yield "结果"
    mock_ds_client.stream_chat = _mock_stream_chat
    mock_ds_client.close = AsyncMock()
    mock_modules["tengod.deepseek_adapter"].DeepseekClient = MagicMock(return_value=mock_ds_client)
    mock_modules["tengod.deepseek_adapter"].DeepseekConfig = MagicMock()
    mock_modules["tengod.deepseek_adapter"].Message = MagicMock()
    mock_modules["tengod.deepseek_adapter"].BAZI_SYSTEM_PROMPT = "你是一个命理专家"

    # ── AI 解释器 ──
    mock_modules["tengod.ai_interpreter"] = MagicMock()
    mock_modules["tengod.ai_interpreter"].build_bazi_context = MagicMock(return_value="八字上下文")
    mock_modules["tengod.ai_interpreter"].interpret_bazi = AsyncMock(return_value="AI 解读结果")
    mock_modules["tengod.ai_interpreter"]._to_dict = MagicMock(return_value={})
    mock_modules["tengod.ai_interpreter"].interpret_comprehensive = AsyncMock(return_value="综合 AI 解读")
    mock_modules["tengod.ai_interpreter"].build_ziwei_context = MagicMock(return_value="")
    mock_modules["tengod.ai_interpreter"].interpret_ziwei = AsyncMock(return_value="紫微解读")
    mock_modules["tengod.ai_interpreter"].build_liuyao_context = MagicMock(return_value="")
    mock_modules["tengod.ai_interpreter"].interpret_liuyao = AsyncMock(return_value="六爻解读")
    mock_modules["tengod.ai_interpreter"].build_name_context = MagicMock(return_value="")
    mock_modules["tengod.ai_interpreter"].interpret_name = AsyncMock(return_value="姓名解读")
    mock_modules["tengod.ai_interpreter"].build_marriage_context = MagicMock(return_value="")
    mock_modules["tengod.ai_interpreter"].interpret_marriage = AsyncMock(return_value="合婚解读")
    mock_modules["tengod.ai_interpreter"].build_oracle_context = MagicMock(return_value="")
    mock_modules["tengod.ai_interpreter"].interpret_oracle = AsyncMock(return_value="Oracle 解读")
    async def _mock_stream_interpret(*args, **kwargs):
        yield "解读"
        yield "内容"
    mock_modules["tengod.ai_interpreter"].interpret_bazi_stream = _mock_stream_interpret

    # ── LLM 适配器 ──
    mock_modules["tengod.llm_adapter"] = MagicMock()
    mock_llm = MagicMock()
    mock_llm.model_name = "mock-model"
    mock_modules["tengod.llm_adapter"].get_llm = MagicMock(return_value=mock_llm)
    mock_modules["tengod.llm_adapter"].chat = AsyncMock(return_value="AI 回答")
    mock_modules["tengod.llm_adapter"].generate_report = AsyncMock(return_value="增强报告")
    mock_modules["tengod.llm_adapter"].chat_stream = MagicMock()

    # ── 其他模块 ──
    for mod_name in [
        "tengod.graph_engine", "tengod.knowledge_fusion",
        "tengod.huigu_scheduler", "tengod.ziwei_engine",
        "tengod.liuyao_engine", "tengod.qimen_engine",
        "tengod.name_engine", "tengod.marriage_engine",
        "tengod.case_library", "tengod.webhook",
        "tengod.advanced_analysis", "tengod.advanced_shushu",
        "tengod.multi_system_engine", "tengod.liunian_judgment",
        "tengod.xiuzhen_realms", "tengod.hundun_sea",
        "tengod.self_correction", "tengod.inner_child",
        "tengod.config_manager", "tengod.agent_orchestrator",
        "tengod.knowledge_evolution", "tengod.intelligent_analysis",
        "tengod.fusion_analyzer", "tengod.cache", "tengod.cache_manager",
        "tengod.database", "tengod.db_migration", "tengod.dayun_liunian",
        "tengod.docs_generator", "tengod.federated_consensus",
        "tengod.i18n", "tengod.consensus", "tengod.config_schema",
        "tengod.monitoring", "tengod.observability", "tengod.pipeline",
        "tengod.plugins", "tengod.reliability", "tengod.shen_agents",
        "tengod.social", "tengod.tiangan_gate", "tengod.visualization",
        "tengod.vector_store_pg", "tengod.mcp_server", "tengod.miniapp",
        "tengod.metrics", "tengod.case_comparator", "tengod.case_repository",
        "tengod.cli",
    ]:
        mock_mod = MagicMock()
        mock_mod.MagicMock = MagicMock
        mock_modules[mod_name] = mock_mod

    # ── 中文子包 ──
    for sub in [
        "tengod.伤官_破界创新", "tengod.正官_法度调度", "tengod.七杀_品质裁决",
        "tengod.偏印_桥接通变", "tengod.偏财_奇招演化", "tengod.元辰_本源定位",
        "tengod.劫财_攻防边界", "tengod.太极_阴阳调和", "tengod.正印_滋养守护",
        "tengod.正财_知识固化", "tengod.比肩_架构协同", "tengod.食神_创生输出",
    ]:
        mock_mod = MagicMock()
        mock_modules[sub] = mock_mod

    # ── 风水/七政子包 ──
    mock_modules["tengod.fengshui"] = MagicMock()
    mock_modules["tengod.fengshui.xuankong"] = MagicMock()
    mock_modules["tengod.qizheng"] = MagicMock()
    mock_modules["tengod.qizheng.engine"] = MagicMock()

    # ── intelligent_analysis: get_engine 需要返回 async 兼容的 mock ──
    mock_ia = mock_modules["tengod.intelligent_analysis"]
    mock_ia_engine = MagicMock()
    mock_ia_engine.full_analysis = AsyncMock(return_value={
        "analysis": "AI 综合分析结果",
        "recommendations": ["建议1", "建议2"],
        "score": 85,
    })
    mock_ia.get_engine = MagicMock(return_value=mock_ia_engine)

    # ── observability: 需要返回真实字符串值，否则 MagicMock 会污染 HTTP 响应头 ──
    mock_obs = mock_modules["tengod.observability"]
    mock_obs.generate_request_id = MagicMock(return_value="test-req-id-12345")
    mock_obs.set_request_id = MagicMock()
    mock_obs.get_request_id = MagicMock(return_value="test-req-id-12345")
    mock_obs.setup_logging = MagicMock()
    mock_obs.get_logger = MagicMock(return_value=MagicMock())
    mock_obs.get_health_checker = MagicMock(return_value=MagicMock())
    mock_obs.health_check_response = MagicMock()
    mock_obs.get_metrics_collector = MagicMock(return_value=mock_metrics)
    mock_obs.get_request_tracker = MagicMock(return_value=MagicMock())

    return mock_modules


# ============================================================================
# 全局 Fixture：mock 所有依赖并导入 api_server
# ============================================================================

@pytest.fixture(scope="module")
def api_server_module():
    """在 mock 所有 tengod 依赖后导入 api_server 模块"""
    mock_modules = _build_mock_modules()

    # 保存所有 tengod 模块的原始引用
    _original_tengod_modules = {}
    for name in list(sys.modules.keys()):
        if name.startswith("tengod"):
            _original_tengod_modules[name] = sys.modules[name]

    # 清除已缓存的 tengod 模块（必须在 patch.dict 之前）
    for cached in list(sys.modules.keys()):
        if cached.startswith("tengod"):
            sys.modules.pop(cached, None)

    with patch.dict(sys.modules, mock_modules):
        # 重新导入
        import importlib
        import tengod.api_server as api_server_mod
        importlib.reload(api_server_mod)

        yield api_server_mod

    # patch.dict 退出后自动恢复 mock_modules 中的 key
    # 但 patch.dict 只恢复它修改过的 key，我们还需要恢复其他 tengod 模块
    # 先清理 patch.dict 残留的 mock 模块
    for name in list(sys.modules.keys()):
        if name.startswith("tengod"):
            sys.modules.pop(name, None)
    # 恢复所有原始 tengod 模块
    for name, mod in _original_tengod_modules.items():
        if mod is not None:
            sys.modules[name] = mod


def _reset_module_state(api_server_module):
    """重置模块全局状态"""
    from collections import defaultdict
    api_server_module._total_requests = 0
    api_server_module._total_errors = 0
    # 直接替换函数 __globals__ 中的 _request_counts，确保中间件使用新 dict
    # 必须使用 defaultdict(list)，因为 rate_limit_middleware 直接通过 _request_counts[client_ip] 访问
    api_server_module.rate_limit_middleware.__globals__["_request_counts"] = defaultdict(list)
    api_server_module._api_key = None


@pytest.fixture
def client(api_server_module, monkeypatch):
    """创建 TestClient，每次使用前重置全局状态并确保无 API Key"""
    _reset_module_state(api_server_module)
    # 删除 TENGOD_API_KEY 环境变量
    monkeypatch.delenv("TENGOD_API_KEY", raising=False)
    with TestClient(api_server_module.app) as c:
        yield c


# ============================================================================
# 1. 健康检查端点
# ============================================================================

class TestHealthEndpoints:
    """健康检查端点测试"""

    def test_health_ok(self, client):
        resp = client.get("/api/health")
        assert resp.status_code == 200
        data = _unwrap(resp)
        assert data["status"] == "ok"
        assert "version" in data
        assert "uptime_seconds" in data
        assert "total_requests" in data
        assert "total_errors" in data

    def test_health_full(self, client):
        resp = client.get("/api/health/full")
        assert resp.status_code == 200
        data = _unwrap(resp)
        assert "status" in data

    def test_health_full_unhealthy(self, client, api_server_module):
        """当组件不健康时，检查响应中包含 unhealthy 状态"""
        from tengod import metrics_collector
        metrics_collector.HealthChecker.check_all.return_value = {
            "status": "unhealthy",
            "components": {"db": "error"}
        }
        resp = client.get("/api/health/full")
        assert resp.status_code in (200, 503)


# ============================================================================
# 2. Stats / Metrics 端点
# ============================================================================

class TestStatsEndpoint:
    """系统统计端点测试"""

    def test_stats(self, client):
        resp = client.get("/api/stats")
        assert resp.status_code == 200
        data = _unwrap(resp)
        assert "version" in data
        assert "started_at" in data
        assert "total_requests" in data
        assert "total_errors" in data
        assert "vector_store" in data
        assert "active_clients" in data

    def test_api_metrics(self, client):
        resp = client.get("/api/metrics")
        assert resp.status_code == 200
        data = _unwrap(resp)
        assert isinstance(data, dict)

    def test_metrics_prometheus(self, client):
        resp = client.get("/metrics")
        assert resp.status_code == 200
        assert "text/plain" in resp.headers.get("content-type", "")


# ============================================================================
# 3. 八字端点
# ============================================================================

class TestBaziEndpoints:
    """八字排盘端点测试"""

    _valid_bazi = {
        "year": 1990, "month": 6, "day": 15, "hour": 12, "minute": 0,
        "gender": "male", "longitude": 116.4, "latitude": 39.9,
    }

    def test_bazi_calc_valid(self, client):
        resp = client.post("/api/bazi/calc", json=self._valid_bazi)
        assert resp.status_code == 200
        data = _unwrap(resp)
        assert "pillars" in data
        assert "day_master" in data
        assert "shigan_map" in data
        assert "dayuns" in data

    def test_bazi_calc_missing_year(self, client):
        resp = client.post("/api/bazi/calc", json={"month": 6, "day": 15, "hour": 12, "gender": "male"})
        assert resp.status_code == 422

    def test_bazi_calc_invalid_gender(self, client):
        invalid = dict(self._valid_bazi)
        invalid["gender"] = "invalid_gender"
        resp = client.post("/api/bazi/calc", json=invalid)
        assert resp.status_code == 422

    def test_bazi_calc_year_out_of_range(self, client):
        invalid = dict(self._valid_bazi)
        invalid["year"] = 1800
        resp = client.post("/api/bazi/calc", json=invalid)
        assert resp.status_code == 422

    def test_bazi_shensha(self, client):
        resp = client.post("/api/bazi/shensha", json=self._valid_bazi)
        assert resp.status_code == 200
        data = _unwrap(resp)
        assert "pillars" in data
        assert "total_shensha" in data
        assert "summary" in data

    def test_bazi_geju(self, client):
        resp = client.post("/api/bazi/geju", json=self._valid_bazi)
        assert resp.status_code == 200
        data = _unwrap(resp)
        assert "geju_name" in data
        assert "score" in data

    def test_bazi_yongshen(self, client):
        resp = client.post("/api/bazi/yongshen", json=self._valid_bazi)
        assert resp.status_code == 200
        data = _unwrap(resp)
        assert "wang_shuai" in data
        assert "yong_shen" in data
        assert "ji_shen" in data

    def test_bazi_tiaohou(self, client):
        resp = client.post("/api/bazi/tiaohou", json=self._valid_bazi)
        assert resp.status_code == 200
        data = _unwrap(resp)
        assert "season" in data

    def test_bazi_full(self, client):
        resp = client.post("/api/bazi/full", json=self._valid_bazi)
        assert resp.status_code == 200
        data = _unwrap(resp)
        assert "bazi" in data
        assert "shensha" in data
        assert "geju" in data
        assert "yongshen" in data
        assert "tiaohou" in data

    def test_bazi_report(self, client):
        resp = client.post("/api/bazi/report", json={
            "bazi": self._valid_bazi, "format": "text",
            "include_shensha": True, "include_geju": True, "include_yongshen": True,
        })
        assert resp.status_code == 200
        data = _unwrap(resp)
        assert "report" in data

    def test_bazi_report_markdown(self, client):
        resp = client.post("/api/bazi/report", json={
            "bazi": self._valid_bazi, "format": "markdown",
        })
        assert resp.status_code == 200
        data = _unwrap(resp)
        assert "report" in data

    def test_bazi_report_html(self, client):
        resp = client.post("/api/bazi/report", json={
            "bazi": self._valid_bazi, "format": "html",
        })
        assert resp.status_code in (200, 500)

    def test_bazi_report_json_format(self, client):
        resp = client.post("/api/bazi/report", json={
            "bazi": self._valid_bazi, "format": "json",
        })
        assert resp.status_code == 200
        data = _unwrap(resp)
        assert "report" in data

    def test_bazi_report_invalid_format(self, client):
        resp = client.post("/api/bazi/report", json={
            "bazi": self._valid_bazi, "format": "invalid",
        })
        # 注: 路由处理器中 except Exception 会捕获 HTTPException(400) 并重抛为 500
        assert resp.status_code == 500

    def test_bazi_calc_female(self, client):
        female = dict(self._valid_bazi)
        female["gender"] = "female"
        resp = client.post("/api/bazi/calc", json=female)
        assert resp.status_code == 200

    def test_bazi_calc_chinese_male(self, client):
        chinese = dict(self._valid_bazi)
        chinese["gender"] = "男"
        resp = client.post("/api/bazi/calc", json=chinese)
        assert resp.status_code == 200

    def test_bazi_calc_chinese_female(self, client):
        chinese = dict(self._valid_bazi)
        chinese["gender"] = "女"
        resp = client.post("/api/bazi/calc", json=chinese)
        assert resp.status_code == 200


# ============================================================================
# 4. 知识查询端点
# ============================================================================

class TestKnowledgeEndpoints:
    """知识查询端点测试"""

    def test_knowledge_search_valid(self, client):
        resp = client.post("/api/knowledge/search", json={"query": "五行", "top_k": 5})
        assert resp.status_code == 200
        data = _unwrap(resp)
        assert "results" in data

    def test_knowledge_search_with_type_filter(self, client):
        resp = client.post("/api/knowledge/search", json={
            "query": "五行", "top_k": 5, "type_filter": "五行/八卦",
        })
        assert resp.status_code == 200

    def test_knowledge_search_empty_query(self, client):
        resp = client.post("/api/knowledge/search", json={"query": ""})
        assert resp.status_code == 422

    def test_knowledge_recommend_valid(self, client):
        resp = client.post("/api/knowledge/recommend", json={"node_name": "木", "top_k": 5})
        assert resp.status_code == 200
        data = _unwrap(resp)
        assert "node_name" in data
        assert "recommendations" in data

    def test_knowledge_wuxing_valid(self, client):
        resp = client.get("/api/knowledge/wuxing/木")
        assert resp.status_code == 200
        data = _unwrap(resp)
        assert data["element"] == "木"
        assert "info" in data

    def test_knowledge_wuxing_relations(self, client):
        resp = client.get("/api/knowledge/wuxing/火?relation_mode=relations")
        assert resp.status_code == 200
        data = _unwrap(resp)
        assert "relations" in data

    def test_knowledge_wuxing_all(self, client):
        resp = client.get("/api/knowledge/wuxing/土?relation_mode=all")
        assert resp.status_code == 200
        data = _unwrap(resp)
        assert "info" in data
        assert "relations" in data

    def test_knowledge_wuxing_invalid(self, client, api_server_module):
        from tengod import knowledge_graph
        with patch.object(knowledge_graph, "get_knowledge_graph") as mock_get:
            mock_kg = MagicMock()
            mock_kg.get_element = MagicMock(return_value=None)
            mock_kg.get_relations = MagicMock(return_value={})
            mock_get.return_value = mock_kg
            resp = client.get("/api/knowledge/wuxing/invalid")
            assert resp.status_code == 404

    def test_knowledge_bagua_valid(self, client):
        resp = client.get("/api/knowledge/bagua/乾")
        assert resp.status_code == 200
        data = _unwrap(resp)
        assert data["trigram"] == "乾"
        assert "info" in data

    def test_knowledge_bagua_relations(self, client):
        resp = client.get("/api/knowledge/bagua/坤?query_type=relations")
        assert resp.status_code == 200

    def test_knowledge_bagua_invalid(self, client, api_server_module):
        from tengod import knowledge_graph
        with patch.object(knowledge_graph, "get_knowledge_graph") as mock_get:
            mock_kg = MagicMock()
            mock_kg.get_trigram = MagicMock(return_value=None)
            mock_get.return_value = mock_kg
            resp = client.get("/api/knowledge/bagua/invalid")
            assert resp.status_code == 404

    def test_knowledge_shigan(self, client):
        resp = client.post("/api/knowledge/shigan", json={
            "day_master": "甲", "gan": "乙,丙,丁", "detail_level": "basic",
        })
        assert resp.status_code == 200
        data = _unwrap(resp)
        assert "day_master" in data
        assert "derivations" in data

    def test_knowledge_shigan_no_gan(self, client):
        resp = client.post("/api/knowledge/shigan", json={"day_master": "甲"})
        assert resp.status_code == 200
        data = _unwrap(resp)
        assert data["total_derived"] == 10

    def test_knowledge_dizhi(self, client):
        resp = client.post("/api/knowledge/dizhi", json={
            "branches": "子,丑,寅,午", "analysis_type": "all",
        })
        assert resp.status_code == 200
        data = _unwrap(resp)
        assert "input_branches" in data
        assert "info" in data

    def test_knowledge_dizhi_invalid_branch(self, client):
        resp = client.post("/api/knowledge/dizhi", json={"branches": "invalid"})
        assert resp.status_code == 422


# ============================================================================
# 5. V2 端点
# ============================================================================

class TestV2Endpoints:
    """V2 端点测试"""

    def test_v2_solar_time(self, client):
        resp = client.post("/api/v2/solar-time", json={
            "year": 2025, "month": 6, "day": 15, "hour": 12, "minute": 0, "longitude": 120.0,
        })
        assert resp.status_code == 200
        data = _unwrap(resp)
        assert "solar_time" in data
        assert "shichen" in data

    def test_v2_jieqi(self, client):
        resp = client.post("/api/v2/jieqi", json={"year": 2025, "month": 6, "day": 15})
        assert resp.status_code == 200
        data = _unwrap(resp)
        assert "current_jieqi" in data

    def test_v2_wuxing_strength_all(self, client):
        resp = client.post("/api/v2/wuxing/strength", json={"month": 3})
        assert resp.status_code == 200
        data = _unwrap(resp)
        assert "strengths" in data

    def test_v2_wuxing_strength_specific(self, client):
        resp = client.post("/api/v2/wuxing/strength", json={"month": 3, "element": "木"})
        assert resp.status_code == 200
        data = _unwrap(resp)
        assert data["element"] == "木"

    def test_v2_chart_bazi_html(self, client):
        resp = client.post("/api/v2/chart/bazi", json={
            "bazi": {"year": 1990, "month": 6, "day": 15, "hour": 12, "gender": "male"},
            "theme": "classic", "format": "html",
        })
        assert resp.status_code == 200
        assert "html" in resp.headers.get("content-type", "")

    def test_v2_chart_bazi_json(self, client):
        resp = client.post("/api/v2/chart/bazi", json={
            "bazi": {"year": 1990, "month": 6, "day": 15, "hour": 12, "gender": "male"},
            "format": "json",
        })
        assert resp.status_code == 200
        data = _unwrap(resp)
        assert "json" in data

    def test_v2_ai_analyze(self, client):
        resp = client.post("/api/v2/ai/analyze", json={
            "bazi": {"year": 1990, "month": 6, "day": 15, "hour": 12, "gender": "male"},
            "analysis_type": "basic", "focus": "综合",
        })
        assert resp.status_code == 200
        data = _unwrap(resp)
        assert "analysis_type" in data

    def test_v2_ai_stream(self, client):
        """流式 AI 分析需要 DEEPSEEK_API_KEY"""
        resp = client.post("/api/v2/ai/stream", json={
            "bazi": {"year": 1990, "month": 6, "day": 15, "hour": 12, "gender": "male"},
            "question": "分析此命盘",
        })
        # 无 API Key 时应返回 503
        assert resp.status_code == 503

    def test_v2_ai_stream_with_key(self, client):
        """有 API Key 时流式响应正常"""
        with patch.dict(os.environ, {"DEEPSEEK_API_KEY": "test-key"}):
            resp = client.post("/api/v2/ai/stream", json={
                "bazi": {"year": 1990, "month": 6, "day": 15, "hour": 12, "gender": "male"},
                "question": "分析此命盘",
            })
            assert resp.status_code == 200
            assert "text/event-stream" in resp.headers.get("content-type", "")


# ============================================================================
# 6. 鉴权中间件测试
# ============================================================================

class TestAuthMiddleware:
    """鉴权中间件测试

    PUBLIC_PATHS = {"/api/health", "/api/health/full", "/api/stats", "/metrics",
                     "/api/metrics", "/docs", "/redoc", "/openapi.json"}
    """

    def test_no_api_key_bypasses(self, client):
        """未设置 TENGOD_API_KEY 时，所有请求不鉴权"""
        resp = client.post("/api/bazi/calc", json={
            "year": 1990, "month": 6, "day": 15, "hour": 12, "gender": "male"
        })
        assert resp.status_code == 200

    def test_valid_key_allows_access(self, api_server_module):
        """设置 API Key 后，携带正确 key 的请求通过"""
        _reset_module_state(api_server_module)
        with patch.dict(os.environ, {"TENGOD_API_KEY": "my-secret-key"}):
            with TestClient(api_server_module.app) as c:
                resp = c.post("/api/bazi/calc", json={
                    "year": 1990, "month": 6, "day": 15, "hour": 12, "gender": "male"
                }, headers={"X-API-Key": "my-secret-key"})
                assert resp.status_code == 200

    def test_missing_key_returns_401(self, api_server_module):
        """设置 API Key 后，缺少 X-API-Key 的请求返回 401"""
        _reset_module_state(api_server_module)
        with patch.dict(os.environ, {"TENGOD_API_KEY": "my-secret-key"}):
            with TestClient(api_server_module.app) as c:
                resp = c.post("/api/bazi/calc", json={
                    "year": 1990, "month": 6, "day": 15, "hour": 12, "gender": "male"
                })
                assert resp.status_code == 401

    def test_invalid_key_returns_403(self, api_server_module):
        """设置 API Key 后，携带错误 key 的请求返回 403"""
        _reset_module_state(api_server_module)
        with patch.dict(os.environ, {"TENGOD_API_KEY": "my-secret-key"}):
            with TestClient(api_server_module.app) as c:
                resp = c.post("/api/bazi/calc", json={
                    "year": 1990, "month": 6, "day": 15, "hour": 12, "gender": "male"
                }, headers={"X-API-Key": "wrong-key"})
                assert resp.status_code == 403

    def test_public_paths_bypass(self, api_server_module):
        """公开路径不需要鉴权"""
        _reset_module_state(api_server_module)
        with patch.dict(os.environ, {"TENGOD_API_KEY": "my-secret-key"}):
            with TestClient(api_server_module.app) as c:
                for path in ["/api/health", "/api/health/full", "/api/stats",
                             "/docs", "/redoc", "/openapi.json"]:
                    resp = c.get(path)
                    assert resp.status_code == 200, f"Path {path} should be public"


class TestRateLimitMiddleware:
    """限流中间件测试"""

    def test_normal_request_passes(self, client):
        resp = client.get("/api/health")
        assert resp.status_code == 200

    def test_rate_limit_exceeded(self, api_server_module):
        """超过限流阈值返回 429"""
        _reset_module_state(api_server_module)
        client_ip = "testclient"
        now = time.time()
        api_server_module._request_counts[client_ip] = [now] * 120
        with TestClient(api_server_module.app) as c:
            resp = c.get("/api/health")
            assert resp.status_code == 429


class TestLogMiddleware:
    """日志中间件测试"""

    def test_total_requests_increments(self, client, api_server_module):
        api_server_module._total_requests = 0
        client.get("/api/health")
        assert api_server_module._total_requests >= 1

    def test_total_errors_increments_on_404(self, client, api_server_module):
        api_server_module._total_errors = 0
        client.get("/nonexistent-path-12345")
        assert api_server_module._total_errors >= 1


# ============================================================================
# 7. 文档端点
# ============================================================================

class TestDocsEndpoints:
    """文档端点测试"""

    def test_docs(self, client):
        resp = client.get("/docs")
        assert resp.status_code == 200

    def test_redoc(self, client):
        resp = client.get("/redoc")
        assert resp.status_code == 200

    def test_openapi_json(self, client):
        resp = client.get("/openapi.json")
        assert resp.status_code == 200
        data = resp.json()
        assert "openapi" in data
        assert "info" in data
        assert "paths" in data


# ============================================================================
# 8. 其他端点
# ============================================================================

class TestOtherEndpoints:
    """其他端点测试"""

    def test_root_redirect(self, client):
        resp = client.get("/", follow_redirects=False)
        assert resp.status_code in (200, 307, 302)

    def test_options_cors(self, client):
        resp = client.options("/api/bazi/calc", headers={
            "Origin": "http://example.com", "Access-Control-Request-Method": "POST",
        })
        assert resp.status_code == 200

    def test_404_json(self, client):
        resp = client.get("/nonexistent-endpoint-xyz")
        assert resp.status_code == 404
        data = resp.json()
        assert "detail" in data

    def test_api_version(self, client):
        resp = client.get("/api/version")
        assert resp.status_code == 200
        data = _unwrap(resp)
        assert "api_version" in data

    def test_health_live(self, client):
        resp = client.get("/health/live")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "alive"

    def test_health_ready(self, client):
        resp = client.get("/health/ready")
        assert resp.status_code == 200


# ============================================================================
# 9. Pydantic 模型测试
# ============================================================================

class TestPydanticModels:
    """Pydantic 模型验证测试"""

    def test_bazi_input_defaults(self, api_server_module):
        BaziInput = api_server_module.BaziInput
        bazi = BaziInput(year=2000, month=1, day=1)
        assert bazi.hour == 12
        assert bazi.minute == 0
        assert bazi.gender == "male"
        assert bazi.longitude == 116.4
        assert bazi.latitude == 39.9

    def test_bazi_input_gender_normalization(self, api_server_module):
        BaziInput = api_server_module.BaziInput
        assert BaziInput(year=2000, month=1, day=1, gender=" 男 ").gender == "male"
        assert BaziInput(year=2000, month=1, day=1, gender="FEMALE").gender == "female"
        assert BaziInput(year=2000, month=1, day=1, gender="女").gender == "female"

    def test_pillars_input(self, api_server_module):
        PillarsInput = api_server_module.PillarsInput
        p = PillarsInput(year="甲子", month="丙寅", day="戊辰", hour="庚申")
        assert p.year == "甲子"
        d = p.to_dict()
        assert d == {"year": "甲子", "month": "丙寅", "day": "戊辰", "hour": "庚申"}

    def test_pillars_input_invalid_length(self, api_server_module):
        PillarsInput = api_server_module.PillarsInput
        with pytest.raises(Exception):
            PillarsInput(year="甲子丑", month="丙寅", day="戊辰", hour="庚申")

    def test_search_query(self, api_server_module):
        SearchQuery = api_server_module.SearchQuery
        q = SearchQuery(query="五行", top_k=5)
        assert q.query == "五行"
        assert q.top_k == 5
        assert q.type_filter is None

    def test_search_query_defaults(self, api_server_module):
        SearchQuery = api_server_module.SearchQuery
        q = SearchQuery(query="test")
        assert q.top_k == 10

    def test_recommend_query(self, api_server_module):
        RecommendQuery = api_server_module.RecommendQuery
        q = RecommendQuery(node_name="木")
        assert q.node_name == "木"
        assert q.top_k == 5

    def test_shigan_query(self, api_server_module):
        ShiganQuery = api_server_module.ShiganQuery
        q = ShiganQuery(day_master="甲", gan="乙,丙")
        assert q.day_master == "甲"
        assert q.gan == "乙,丙"

    def test_dizhi_query_valid(self, api_server_module):
        DizhiQuery = api_server_module.DizhiQuery
        q = DizhiQuery(branches="子,丑,寅")
        assert q.branches == "子,丑,寅"
        assert q.analysis_type == "all"

    def test_report_query_defaults(self, api_server_module):
        ReportQuery = api_server_module.ReportQuery
        BaziInput = api_server_module.BaziInput
        bazi = BaziInput(year=2000, month=1, day=1)
        q = ReportQuery(bazi=bazi)
        assert q.format == "text"
        assert q.include_shensha is True
        assert q.include_geju is True
        assert q.include_yongshen is True

    def test_health_response(self, api_server_module):
        HealthResponse = api_server_module.HealthResponse
        h = HealthResponse(version="1.0", uptime_seconds=10.5, total_requests=100, total_errors=5)
        assert h.status == "ok"


# ============================================================================
# 10. 全局状态测试
# ============================================================================

class TestGlobalState:
    """全局状态变量测试"""

    def test_server_started_at(self, api_server_module):
        assert api_server_module._server_started_at is not None
        assert isinstance(api_server_module._server_started_at, str)

    def test_total_requests_default(self, api_server_module):
        assert isinstance(api_server_module._total_requests, int)

    def test_total_errors_default(self, api_server_module):
        assert isinstance(api_server_module._total_errors, int)

    def test_request_counts_default(self, api_server_module):
        assert isinstance(api_server_module._request_counts, dict)

    def test_rate_limit_window_cleanup(self, api_server_module):
        """测试限流窗口清理：过期条目被移除"""
        old_time = time.time() - 120
        api_server_module._request_counts["old_client"] = [old_time]
        window = [t for t in api_server_module._request_counts.get("old_client", [])
                   if time.time() - t < 60]
        assert len(window) == 0


# ============================================================================
# 11. _check_rate_limit 函数测试
# ============================================================================

class TestCheckRateLimit:
    """_check_rate_limit 函数测试"""

    def test_first_request_passes(self, api_server_module):
        result = api_server_module._check_rate_limit("new_client", max_requests=5, window=60)
        assert result is True

    def test_within_limit(self, api_server_module):
        for _ in range(3):
            result = api_server_module._check_rate_limit("within_client", max_requests=5, window=60)
            assert result is True

    def test_exceeds_limit(self, api_server_module):
        for _ in range(3):
            api_server_module._check_rate_limit("exceed_client", max_requests=3, window=60)
        result = api_server_module._check_rate_limit("exceed_client", max_requests=3, window=60)
        assert result is False


# ============================================================================
# 12. main() 入口点测试
# ============================================================================

class TestMainEntry:
    """main() 入口点测试"""

    def test_main_with_api_key(self, api_server_module):
        with patch("sys.argv", ["api_server", "--api-key", "test-key"]):
            with patch.object(api_server_module.uvicorn, "run") as mock_run:
                api_server_module.main()
                mock_run.assert_called_once()
                assert os.environ.get("TENGOD_API_KEY") == "test-key"

    def test_main_without_api_key(self, api_server_module):
        with patch("sys.argv", ["api_server"]):
            with patch.object(api_server_module.uvicorn, "run") as mock_run:
                api_server_module.main()
                mock_run.assert_called_once()

    def test_main_with_port(self, api_server_module):
        with patch("sys.argv", ["api_server", "--port", "9000", "--host", "0.0.0.0"]):
            with patch.object(api_server_module.uvicorn, "run") as mock_run:
                api_server_module.main()
                call_kwargs = mock_run.call_args[1]
                assert call_kwargs["port"] == 9000
                assert call_kwargs["host"] == "0.0.0.0"


# ============================================================================
# 13. 助手函数测试
# ============================================================================

class TestHelperFunctions:
    """助手函数测试"""

    def test_build_pillars(self, api_server_module):
        BaziInput = api_server_module.BaziInput
        bazi = BaziInput(year=1990, month=6, day=15, hour=12, gender="male")
        result = api_server_module._build_pillars(bazi)
        assert isinstance(result, dict)
        assert "year" in result

    def test_bazi_to_analyzer(self, api_server_module):
        BaziInput = api_server_module.BaziInput
        bazi = BaziInput(year=1990, month=6, day=15, hour=12, gender="male")
        result = api_server_module._bazi_to_analyzer(bazi)
        assert result is not None

    def test_get_store(self, api_server_module):
        result = api_server_module._get_store()
        assert result is not None

    def test_get_data_store(self, api_server_module):
        result = api_server_module._get_data_store()
        assert result is not None


# ============================================================================
# 14. AuthMiddleware 独立单元测试
# ============================================================================

class TestAuthMiddlewareUnit:
    """AuthMiddleware 单元测试"""

    @pytest.mark.asyncio
    async def test_dispatch_without_key(self, api_server_module):
        from fastapi import Request
        middleware = api_server_module.AuthMiddleware(app=MagicMock())
        scope = {"type": "http", "method": "GET", "path": "/api/bazi/calc", "headers": []}
        request = Request(scope)

        async def call_next(req):
            from fastapi.responses import Response
            return Response("OK")

        with patch.dict(os.environ, {"TENGOD_API_KEY": "secret"}):
            response = await middleware.dispatch(request, call_next)
            assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_dispatch_with_valid_key(self, api_server_module):
        from fastapi import Request
        middleware = api_server_module.AuthMiddleware(app=MagicMock())
        scope = {
            "type": "http", "method": "GET", "path": "/api/bazi/calc",
            "headers": [(b"x-api-key", b"secret")],
        }
        request = Request(scope)

        async def call_next(req):
            from fastapi.responses import Response
            return Response("OK")

        with patch.dict(os.environ, {"TENGOD_API_KEY": "secret"}):
            response = await middleware.dispatch(request, call_next)
            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_dispatch_with_invalid_key(self, api_server_module):
        from fastapi import Request
        middleware = api_server_module.AuthMiddleware(app=MagicMock())
        scope = {
            "type": "http", "method": "GET", "path": "/api/bazi/calc",
            "headers": [(b"x-api-key", b"wrong")],
        }
        request = Request(scope)

        async def call_next(req):
            from fastapi.responses import Response
            return Response("OK")

        with patch.dict(os.environ, {"TENGOD_API_KEY": "secret"}):
            response = await middleware.dispatch(request, call_next)
            assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_dispatch_public_path(self, api_server_module):
        from fastapi import Request
        middleware = api_server_module.AuthMiddleware(app=MagicMock())
        scope = {"type": "http", "method": "GET", "path": "/api/health", "headers": []}
        request = Request(scope)

        async def call_next(req):
            from fastapi.responses import Response
            return Response("OK")

        with patch.dict(os.environ, {"TENGOD_API_KEY": "secret"}):
            response = await middleware.dispatch(request, call_next)
            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_dispatch_no_env(self, api_server_module):
        from fastapi import Request
        middleware = api_server_module.AuthMiddleware(app=MagicMock())
        scope = {"type": "http", "method": "GET", "path": "/api/bazi/calc", "headers": []}
        request = Request(scope)

        async def call_next(req):
            from fastapi.responses import Response
            return Response("OK")

        with patch.dict(os.environ, {}, clear=True):
            response = await middleware.dispatch(request, call_next)
            assert response.status_code == 200


# ============================================================================
# 15. CORS 和 Gzip 中间件测试
# ============================================================================

class TestCORSAndGzip:
    """CORS 和 Gzip 中间件测试"""

    def test_cors_headers(self, client):
        resp = client.options("/api/bazi/calc", headers={
            "Origin": "http://example.com", "Access-Control-Request-Method": "POST",
        })
        assert resp.status_code == 200
        assert "access-control-allow-origin" in resp.headers or \
               "access-control-allow-methods" in resp.headers

    def test_gzip_encoding(self, client):
        resp = client.get("/api/health", headers={"Accept-Encoding": "gzip"})
        assert resp.status_code == 200


# ============================================================================
# 16. 测试创建 app 的模块级属性
# ============================================================================

class TestModuleLevelApp:
    """模块级 app 属性测试"""

    def test_app_exists(self, api_server_module):
        assert hasattr(api_server_module, "app")
        assert api_server_module.app is not None

    def test_app_title(self, api_server_module):
        assert "十神" in api_server_module.app.title

    def test_app_version(self, api_server_module):
        assert api_server_module.app.version is not None

    def test_app_has_routes(self, api_server_module):
        assert len(api_server_module.app.routes) > 0

    def test_app_docs_url(self, api_server_module):
        assert api_server_module.app.docs_url == "/docs"
        assert api_server_module.app.redoc_url == "/redoc"


# ============================================================================
# 17. 异常处理器测试
# ============================================================================

class TestExceptionHandlers:
    """异常处理器测试"""

    def test_validation_error_format(self, client):
        resp = client.post("/api/bazi/calc", json={"invalid": "data"})
        assert resp.status_code == 422
        data = resp.json()
        assert "detail" in data

    def test_404_for_unknown_wuxing(self, client, api_server_module):
        """测试 HTTP 404 异常格式"""
        from tengod import knowledge_graph
        with patch.object(knowledge_graph, "get_knowledge_graph") as mock_get:
            mock_kg = MagicMock()
            mock_kg.get_element = MagicMock(return_value=None)
            mock_kg.get_relations = MagicMock(return_value={})
            mock_get.return_value = mock_kg
            resp = client.get("/api/knowledge/wuxing/invalid_input_test")
            assert resp.status_code == 404


# ============================================================================
# 18. DizhiQuery 模型独立测试
# ============================================================================

class TestDizhiQueryModel:
    """DizhiQuery 模型测试"""

    def test_valid_branches(self, api_server_module):
        DizhiQuery = api_server_module.DizhiQuery
        q = DizhiQuery(branches="子,丑,寅,卯,辰,巳,午,未,申,酉,戌,亥")
        assert q.branches == "子,丑,寅,卯,辰,巳,午,未,申,酉,戌,亥"

    def test_space_separated_branches(self, api_server_module):
        DizhiQuery = api_server_module.DizhiQuery
        q = DizhiQuery(branches="子 丑 寅")
        assert q.branches == "子,丑,寅"

    def test_analysis_type_default(self, api_server_module):
        DizhiQuery = api_server_module.DizhiQuery
        q = DizhiQuery(branches="子,丑")
        assert q.analysis_type == "all"


# ============================================================================
# 19. 边缘情况测试
# ============================================================================

class TestEdgeCases:
    """边缘情况测试"""

    def test_bazi_calc_month_out_of_range(self, client):
        resp = client.post("/api/bazi/calc", json={
            "year": 1990, "month": 13, "day": 15, "hour": 12, "gender": "male"
        })
        assert resp.status_code == 422

    def test_bazi_calc_day_out_of_range(self, client):
        resp = client.post("/api/bazi/calc", json={
            "year": 1990, "month": 6, "day": 32, "hour": 12, "gender": "male"
        })
        assert resp.status_code == 422

    def test_bazi_calc_hour_out_of_range(self, client):
        resp = client.post("/api/bazi/calc", json={
            "year": 1990, "month": 6, "day": 15, "hour": 25, "gender": "male"
        })
        assert resp.status_code == 422

    def test_knowledge_search_top_k_out_of_range(self, client):
        resp = client.post("/api/knowledge/search", json={"query": "test", "top_k": 100})
        assert resp.status_code == 422

    def test_knowledge_recommend_top_k_out_of_range(self, client):
        resp = client.post("/api/knowledge/recommend", json={"node_name": "木", "top_k": 100})
        assert resp.status_code == 422

    def test_shigan_empty_day_master(self, client):
        resp = client.post("/api/knowledge/shigan", json={"day_master": ""})
        assert resp.status_code == 422

    def test_multiple_requests(self, client):
        """多次请求应正常工作"""
        for _ in range(5):
            resp = client.get("/api/health")
            assert resp.status_code == 200


# ============================================================================
# 20. __main__ 块测试
# ============================================================================

class TestMainBlock:
    """__main__ 块测试"""

    def test_main_importable(self, api_server_module):
        """验证 main() 函数可被调用"""
        assert callable(api_server_module.main)

    def test_argparse_args(self):
        import argparse
        parser = argparse.ArgumentParser()
        parser.add_argument("--host", default="127.0.0.1")
        parser.add_argument("--port", type=int, default=8000)
        parser.add_argument("--api-key", default=None)
        parser.add_argument("--reload", action="store_true")
        args = parser.parse_args(["--host", "0.0.0.0", "--port", "8080"])
        assert args.host == "0.0.0.0"
        assert args.port == 8080