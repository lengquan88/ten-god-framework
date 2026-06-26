#!/usr/bin/env python3
"""
test_pipeline.py — 十神编排管道综合测试 v2.17.0
================================================
使用 unittest.mock 全面 mock 所有子模块导入，测试 TenStemPipeline 的所有功能。

覆盖：
- PipelineStage 枚举（12 阶段，顺序）
- PipelineContext 数据类（默认值、自定义值、方法）
- StageHandler 基类
- 所有 12 个阶段处理器（正官→比肩）
- TenStemPipeline（__init__、run、run_quick、disable/enable、get_handler、pipeline_info）
- get_pipeline() 单例
- 错误处理与边界条件

用法：
    pytest tests/test_pipeline.py -v --tb=short
    pytest tests/test_pipeline.py --cov=tengod.pipeline --cov-report=term-missing
"""
import sys
import time
from unittest.mock import MagicMock, PropertyMock, patch

import pytest

# ════════════════════════════════════════════════════════════════
# Mock 所有子模块导入（必须在导入 tengod.pipeline 之前）
# ════════════════════════════════════════════════════════════════

# ── 正官_法度调度 ──
_mock_api_router = MagicMock()
_mock_api_router_module = MagicMock()
_mock_api_router_module.APIRouter = MagicMock(return_value=_mock_api_router)
sys.modules["tengod.正官_法度调度.api_router"] = _mock_api_router_module

# ── 元辰_本源定位 ──
_mock_locator = MagicMock()
_mock_locator_module = MagicMock()
_mock_locator_module.YuanChenLocator = MagicMock(return_value=_mock_locator)
_mock_locator_module.ProjectRoot = MagicMock()
sys.modules["tengod.元辰_本源定位.locator"] = _mock_locator_module

# ── 正财_知识固化 ──
_mock_kb = MagicMock()
_mock_kb.query_nearest.return_value = [{"id": "n1", "name": "金", "node_type": "五行", "score": 0.95}]
_mock_kb.find_by_name.return_value = []
_mock_kb.query_by_prefix.return_value = []
_mock_kb.neighbors.return_value = []
_mock_kb.stats.return_value = {"nodes": 7, "edges": 3}
_mock_kb.add_node.return_value = None

_mock_knowledge_node = MagicMock()
_mock_kb_module = MagicMock()
_mock_kb_module.KnowledgeBase = MagicMock(return_value=_mock_kb)
_mock_kb_module.KnowledgeNode = MagicMock(return_value=_mock_knowledge_node)
sys.modules["tengod.正财_知识固化.knowledge_base"] = _mock_kb_module

# ── 偏财_奇招演化 ──
_mock_search_space = MagicMock()
_mock_search_result = MagicMock()
_mock_search_optimizer = MagicMock()
_mock_search_module = MagicMock()
_mock_search_module.SearchOptimizer = MagicMock(return_value=_mock_search_optimizer)
_mock_search_module.SearchSpace = MagicMock(return_value=_mock_search_space)
_mock_search_module.SearchResult = MagicMock(return_value=_mock_search_result)
sys.modules["tengod.偏财_奇招演化.search_optimizer"] = _mock_search_module

# ── 食神_创生输出 ──
_mock_content_generator = MagicMock()
_mock_gen_config = MagicMock()
_mock_output_format = MagicMock()
_mock_llm_provider = MagicMock()
_mock_cg_module = MagicMock()
_mock_cg_module.ContentGenerator = MagicMock(return_value=_mock_content_generator)
_mock_cg_module.GenerationConfig = MagicMock(return_value=_mock_gen_config)
_mock_cg_module.OutputFormat = MagicMock()
_mock_cg_module.LLMProvider = MagicMock()
sys.modules["tengod.食神_创生输出.content_generator"] = _mock_cg_module

# ── 伤官_破界创新 ──
_mock_innovator = MagicMock()
_mock_idea = MagicMock()
_mock_innovation_type = MagicMock()
_mock_innovation_type.COMBINATION = MagicMock()
_mock_innovation_type.COMBINATION.value = "combination"
_mock_innovator_module = MagicMock()
_mock_innovator_module.Innovator = MagicMock(return_value=_mock_innovator)
_mock_innovator_module.Idea = MagicMock(return_value=_mock_idea)
_mock_innovator_module.InnovationType = _mock_innovation_type
sys.modules["tengod.伤官_破界创新.innovator"] = _mock_innovator_module

# ── 七杀_品质裁决 ──
_mock_quality_judge = MagicMock()
_mock_quality_judge.total_weighted.return_value = 85.0
_mock_quality_judge.grade.return_value = MagicMock(value="A")
_mock_quality_judge.report.return_value = {"overall": "优秀"}
_mock_quality_judge.add_score.return_value = MagicMock()

_mock_score = MagicMock()
_mock_grade = MagicMock()
_mock_qj_module = MagicMock()
_mock_qj_module.QualityJudge = MagicMock(return_value=_mock_quality_judge)
_mock_qj_module.Score = MagicMock(return_value=_mock_score)
_mock_qj_module.Grade = MagicMock()
sys.modules["tengod.七杀_品质裁决.quality_judge"] = _mock_qj_module

# ── 太极_阴阳调和 ──
_mock_balancer = MagicMock()
_mock_balancer.get_state.return_value = MagicMock(value="balanced")
_mock_yinyang = MagicMock()
_mock_yinyang.YANG = MagicMock()
_mock_yinyang.YIN = MagicMock()
_mock_yinyang.BALANCED = MagicMock()
_mock_balancer_module = MagicMock()
_mock_balancer_module.TaiChiBalancer = MagicMock(return_value=_mock_balancer)
_mock_balancer_module.YinYang = _mock_yinyang
sys.modules["tengod.太极_阴阳调和.balancer"] = _mock_balancer_module

# ── 正印_滋养守护 ──
_mock_config_manager = MagicMock()
_mock_config_manager.list_all.return_value = {"TENGOD_VERSION": "2.17.0", "TENGOD_ENV": "production"}
_mock_config = MagicMock()
_mock_config_module = MagicMock()
_mock_config_module.ConfigManager = MagicMock(return_value=_mock_config_manager)
_mock_config_module.Config = MagicMock(return_value=_mock_config)
sys.modules["tengod.正印_滋养守护.config_manager"] = _mock_config_module

# ── 劫财_攻防边界 ──
_mock_guard = MagicMock()
_mock_permission = MagicMock()
_mock_security_context = MagicMock()
_mock_guard_module = MagicMock()
_mock_guard_module.Guard = MagicMock(return_value=_mock_guard)
_mock_guard_module.Permission = MagicMock()
_mock_guard_module.SecurityContext = MagicMock(return_value=_mock_security_context)
sys.modules["tengod.劫财_攻防边界.guard"] = _mock_guard_module

# ── 偏印_桥接通变 ──
_mock_adapter = MagicMock()
_mock_protocol_converter = MagicMock()
_mock_dict_to_json = MagicMock()
_mock_adapter_module = MagicMock()
_mock_adapter_module.Adapter = MagicMock(return_value=_mock_adapter)
_mock_adapter_module.ProtocolConverter = MagicMock()
_mock_adapter_module.DictToJsonConverter = MagicMock(return_value=_mock_dict_to_json)
sys.modules["tengod.偏印_桥接通变.adapter"] = _mock_adapter_module

# ── 比肩_架构协同 ──
_mock_component_registry = MagicMock()
_mock_lifecycle_manager = MagicMock()
_mock_lifecycle_manager.summary.return_value = {"total": 12, "ready": 12}
_mock_component_state = MagicMock()
_mock_component_state.READY = MagicMock()
_mock_registry_module = MagicMock()
_mock_registry_module.ComponentRegistry = MagicMock(return_value=_mock_component_registry)
_mock_registry_module.ComponentState = _mock_component_state
_mock_registry_module.LifecycleManager = MagicMock(return_value=_mock_lifecycle_manager)
sys.modules["tengod.比肩_架构协同.registry"] = _mock_registry_module

# ── 现在安全导入 tengod.pipeline ──
from tengod.pipeline import (
    BiJianHandler,
    JieCaiHandler,
    PIPELINE_ORDER,
    PianCaiHandler,
    PianYinHandler,
    PipelineContext,
    PipelineStage,
    QiShaHandler,
    ShangGuanHandler,
    ShiShenHandler,
    StageHandler,
    TaiJiHandler,
    TenStemPipeline,
    YuanChenHandler,
    ZhengCaiHandler,
    ZhengGuanHandler,
    ZhengYinHandler,
    get_pipeline,
)


# ════════════════════════════════════════════════════════════════
# Fixtures
# ════════════════════════════════════════════════════════════════

@pytest.fixture
def mock_kb():
    """创建 mock 知识库"""
    kb = MagicMock()
    kb.query_nearest.return_value = [{"id": "n1", "name": "金", "node_type": "五行", "score": 0.95}]
    kb.find_by_name.return_value = []
    kb.query_by_prefix.return_value = []
    kb.neighbors.return_value = []
    kb.stats.return_value = {"nodes": 7, "edges": 3}
    kb.add_node.return_value = None
    return kb


@pytest.fixture
def pipeline(mock_kb):
    """创建管道实例"""
    return TenStemPipeline(mock_kb)


@pytest.fixture
def ctx():
    """创建管道上下文"""
    return PipelineContext(
        method="GET",
        path="/api/graph/search",
        params={"q": "金"},
    )


@pytest.fixture
def basic_ctx():
    """创建基础管道上下文"""
    return PipelineContext()


# ════════════════════════════════════════════════════════════════
# 1. PipelineStage 枚举测试
# ════════════════════════════════════════════════════════════════

class TestPipelineStageEnum:
    """PipelineStage 枚举测试"""

    def test_all_12_stages_exist(self):
        """验证 12 个阶段全部存在"""
        assert len(PipelineStage) == 12

    def test_stage_names_correct(self):
        """验证所有阶段名称正确"""
        expected_names = {
            "正官_法度", "元辰_路由", "正财_知识", "偏财_搜索",
            "食神_生成", "伤官_创新", "七杀_裁决", "太极_调和",
            "正印_配置", "劫财_安全", "偏印_适配", "比肩_协同",
        }
        actual_names = {s.value for s in PipelineStage}
        assert actual_names == expected_names

    def test_pipeline_order_length(self):
        """验证 PIPELINE_ORDER 长度为 12"""
        assert len(PIPELINE_ORDER) == 12

    def test_pipeline_order_first_is_zheng_guan(self):
        """验证管道顺序：第一个是正官"""
        assert PIPELINE_ORDER[0] == PipelineStage.ZHENG_GUAN

    def test_pipeline_order_last_is_bi_jian(self):
        """验证管道顺序：最后一个是比肩"""
        assert PIPELINE_ORDER[-1] == PipelineStage.BI_JIAN

    def test_pipeline_order_correct_sequence(self):
        """验证管道顺序完全正确"""
        expected = [
            PipelineStage.ZHENG_GUAN,
            PipelineStage.YUAN_CHEN,
            PipelineStage.ZHENG_CAI,
            PipelineStage.PIAN_CAI,
            PipelineStage.SHI_SHEN,
            PipelineStage.SHANG_GUAN,
            PipelineStage.QI_SHA,
            PipelineStage.TAI_JI,
            PipelineStage.ZHENG_YIN,
            PipelineStage.JIE_CAI,
            PipelineStage.PIAN_YIN,
            PipelineStage.BI_JIAN,
        ]
        assert PIPELINE_ORDER == expected

    def test_stage_enum_values_unique(self):
        """验证所有阶段值唯一"""
        values = [s.value for s in PipelineStage]
        assert len(values) == len(set(values))


# ════════════════════════════════════════════════════════════════
# 2. PipelineContext 数据类测试
# ════════════════════════════════════════════════════════════════

class TestPipelineContext:
    """PipelineContext 数据类测试"""

    def test_default_creation(self):
        """测试默认值创建"""
        ctx = PipelineContext()
        assert ctx.method == "GET"
        assert ctx.path == "/"
        assert ctx.params == {}
        assert ctx.body is None
        assert ctx.user is None
        assert ctx.request_id is not None
        assert len(ctx.request_id) == 12
        assert ctx.started_at > 0
        assert ctx.finished_at == 0.0
        assert ctx.status_code == 200
        assert ctx.pipeline_version == "2.17.0"

    def test_custom_values(self):
        """测试自定义值创建"""
        ctx = PipelineContext(
            method="POST",
            path="/api/bazi/calc",
            params={"year": 1990, "month": 6},
            body={"data": "test"},
            user={"id": "user123"},
        )
        assert ctx.method == "POST"
        assert ctx.path == "/api/bazi/calc"
        assert ctx.params == {"year": 1990, "month": 6}
        assert ctx.body == {"data": "test"}
        assert ctx.user == {"id": "user123"}

    def test_default_containers_are_distinct(self):
        """测试默认容器实例独立"""
        ctx1 = PipelineContext()
        ctx2 = PipelineContext()
        ctx1.params["key"] = "val"
        assert ctx2.params == {}

    def test_add_stage_result(self):
        """测试 add_stage_result 方法"""
        ctx = PipelineContext()
        ctx.add_stage_result(PipelineStage.ZHENG_GUAN, "ok", 0.0015)
        assert PipelineStage.ZHENG_GUAN.value in ctx.stage_results
        assert ctx.stage_results[PipelineStage.ZHENG_GUAN.value] == "ok"
        assert ctx.stage_timings[PipelineStage.ZHENG_GUAN.value] == 0.0015

    def test_add_stage_result_multiple(self):
        """测试添加多个阶段结果"""
        ctx = PipelineContext()
        ctx.add_stage_result(PipelineStage.ZHENG_GUAN, "ok", 0.001)
        ctx.add_stage_result(PipelineStage.YUAN_CHEN, "routed", 0.002)
        assert len(ctx.stage_results) == 2
        assert len(ctx.stage_timings) == 2

    def test_add_error(self):
        """测试 add_error 方法"""
        ctx = PipelineContext()
        ctx.add_error(PipelineStage.QI_SHA, "质量评估超时")
        assert PipelineStage.QI_SHA.value in ctx.errors
        assert ctx.errors[PipelineStage.QI_SHA.value] == "质量评估超时"

    def test_add_error_multiple(self):
        """测试添加多个错误"""
        ctx = PipelineContext()
        ctx.add_error(PipelineStage.ZHENG_CAI, "知识检索失败")
        ctx.add_error(PipelineStage.SHI_SHEN, "内容生成超时")
        assert len(ctx.errors) == 2

    def test_summary_basic(self):
        """测试 summary 方法基本功能"""
        ctx = PipelineContext(method="GET", path="/api/test")
        s = ctx.summary()
        assert s["request_id"] == ctx.request_id
        assert s["path"] == "/api/test"
        assert s["stages_executed"] == 0
        assert s["stages_skipped"] == 0
        assert s["errors"] == 0
        assert "total_time_ms" in s
        assert "stage_timings" in s

    def test_summary_with_stages(self):
        """测试 summary 方法（有阶段执行后）"""
        ctx = PipelineContext()
        ctx.add_stage_result(PipelineStage.ZHENG_GUAN, "ok", 0.001)
        ctx.add_stage_result(PipelineStage.YUAN_CHEN, "ok", 0.002)
        ctx.skipped_stages.append("伤官_创新")
        ctx.add_error(PipelineStage.QI_SHA, "error")
        ctx.finished_at = time.time()
        s = ctx.summary()
        assert s["stages_executed"] == 2
        assert s["stages_skipped"] == 1
        assert s["errors"] == 1

    def test_initial_state(self):
        """测试初始状态字段"""
        ctx = PipelineContext()
        assert ctx.current_stage is None
        assert ctx.routed_target == ""
        assert ctx.knowledge_hits == []
        assert ctx.search_results == []
        assert ctx.generated_content == ""
        assert ctx.innovation_ideas == []
        assert ctx.quality_report == {}
        assert ctx.balance_state == "balanced"
        assert ctx.security_context == {}
        assert ctx.adapted_output is None
        assert ctx.response == {}
        assert ctx.skipped_stages == []


# ════════════════════════════════════════════════════════════════
# 3. StageHandler 基类测试
# ════════════════════════════════════════════════════════════════

class TestStageHandler:
    """StageHandler 基类测试"""

    def test_init_defaults(self):
        """测试默认初始化"""
        handler = StageHandler(PipelineStage.ZHENG_GUAN)
        assert handler.name == PipelineStage.ZHENG_GUAN
        assert handler.timeout == 5.0
        assert handler.enabled is True

    def test_init_custom_timeout(self):
        """测试自定义超时"""
        handler = StageHandler(PipelineStage.SHI_SHEN, timeout=30.0)
        assert handler.timeout == 30.0

    def test_handle_raises_not_implemented(self):
        """测试 handle 抛出 NotImplementedError"""
        handler = StageHandler(PipelineStage.ZHENG_GUAN)
        with pytest.raises(NotImplementedError):
            handler.handle(PipelineContext())

    def test_call_when_disabled(self):
        """测试禁用时 __call__ 跳过执行"""
        handler = StageHandler(PipelineStage.ZHENG_GUAN)
        handler.enabled = False
        ctx = PipelineContext()
        result = handler(ctx)
        assert result is True
        assert PipelineStage.ZHENG_GUAN.value in ctx.skipped_stages

    def test_call_when_enabled(self):
        """测试启用时 __call__ 执行 handle"""
        handler = StageHandler(PipelineStage.ZHENG_GUAN)
        handler.handle = MagicMock(return_value=True)

        ctx = PipelineContext()
        result = handler(ctx)

        assert result is True
        handler.handle.assert_called_once_with(ctx)
        assert PipelineStage.ZHENG_GUAN.value in ctx.stage_results

    def test_call_sets_current_stage(self):
        """测试 __call__ 设置 current_stage"""
        handler = StageHandler(PipelineStage.ZHENG_GUAN)
        handler.handle = MagicMock(return_value=True)

        ctx = PipelineContext()
        handler(ctx)

        assert ctx.current_stage == PipelineStage.ZHENG_GUAN

    def test_call_handle_returns_false(self):
        """测试 handle 返回 False 时管道终止"""
        handler = StageHandler(PipelineStage.ZHENG_GUAN)
        handler.handle = MagicMock(return_value=False)

        ctx = PipelineContext()
        result = handler(ctx)

        assert result is False

    def test_call_handle_raises_exception(self):
        """测试 handle 抛出异常时优雅降级"""
        handler = StageHandler(PipelineStage.ZHENG_GUAN)
        handler.handle = MagicMock(side_effect=ValueError("测试错误"))

        ctx = PipelineContext()
        result = handler(ctx)

        assert result is True  # 默认继续
        assert PipelineStage.ZHENG_GUAN.value in ctx.errors
        assert "测试错误" in ctx.errors[PipelineStage.ZHENG_GUAN.value]

    def test_call_records_timing(self):
        """测试 __call__ 记录阶段耗时"""
        handler = StageHandler(PipelineStage.ZHENG_GUAN)
        handler.handle = MagicMock(return_value=True)

        ctx = PipelineContext()
        handler(ctx)

        assert PipelineStage.ZHENG_GUAN.value in ctx.stage_timings
        assert ctx.stage_timings[PipelineStage.ZHENG_GUAN.value] >= 0


# ════════════════════════════════════════════════════════════════
# 4. 各阶段处理器测试
# ════════════════════════════════════════════════════════════════

class TestZhengGuanHandler:
    """正官_法度 处理器测试"""

    def test_init(self):
        """测试初始化"""
        h = ZhengGuanHandler()
        assert h.name == PipelineStage.ZHENG_GUAN
        assert h.timeout == 1.0
        assert h.enabled is True

    def test_handle_valid_path(self):
        """测试有效路径"""
        h = ZhengGuanHandler()
        ctx = PipelineContext(method="GET", path="/api/test")
        result = h.handle(ctx)
        assert result is True

    def test_handle_invalid_path(self):
        """测试无效路径（不以 / 开头）"""
        h = ZhengGuanHandler()
        ctx = PipelineContext(method="GET", path="invalid_path")
        result = h.handle(ctx)
        assert result is False
        assert ctx.status_code == 400
        assert ctx.response == {"error": "非法路径格式"}

    def test_handle_empty_path(self):
        """测试空路径 — 空字符串为 falsy，不触发非法路径检查"""
        h = ZhengGuanHandler()
        ctx = PipelineContext(method="GET", path="")
        result = h.handle(ctx)
        # 空字符串是 falsy，短路跳过非法路径检查，返回 True
        assert result is True


class TestYuanChenHandler:
    """元辰_路由 处理器测试"""

    def test_init(self):
        """测试初始化"""
        h = YuanChenHandler()
        assert h.name == PipelineStage.YUAN_CHEN
        assert h.timeout == 1.0

    def test_handle_bazi_route(self):
        """测试八字路由"""
        h = YuanChenHandler()
        ctx = PipelineContext(method="POST", path="/api/bazi/calc")
        result = h.handle(ctx)
        assert result is True
        assert ctx.routed_target == "八字排盘"

    def test_handle_ziwei_route(self):
        """测试紫微路由"""
        h = YuanChenHandler()
        ctx = PipelineContext(method="GET", path="/api/ziwei/pan")
        result = h.handle(ctx)
        assert result is True
        assert ctx.routed_target == "紫微斗数"

    def test_handle_graph_route(self):
        """测试图谱路由"""
        h = YuanChenHandler()
        ctx = PipelineContext(method="GET", path="/api/graph/search")
        result = h.handle(ctx)
        assert result is True
        assert ctx.routed_target == "知识图谱"

    def test_handle_unknown_route(self):
        """测试未知路由"""
        h = YuanChenHandler()
        ctx = PipelineContext(method="GET", path="/api/unknown/endpoint")
        result = h.handle(ctx)
        assert result is True
        assert ctx.routed_target == "通用请求"

    def test_handle_health_route(self):
        """测试健康检查路由"""
        h = YuanChenHandler()
        ctx = PipelineContext(method="GET", path="/api/health")
        result = h.handle(ctx)
        assert result is True
        assert ctx.routed_target == "健康检查"

    def test_handle_auth_route(self):
        """测试认证路由"""
        h = YuanChenHandler()
        ctx = PipelineContext(method="POST", path="/api/auth/login")
        result = h.handle(ctx)
        assert result is True
        assert ctx.routed_target == "认证系统"

    def test_handle_records_route(self):
        """测试记录管理路由"""
        h = YuanChenHandler()
        ctx = PipelineContext(method="GET", path="/api/records/list")
        result = h.handle(ctx)
        assert result is True
        assert ctx.routed_target == "记录管理"


class TestZhengCaiHandler:
    """正财_知识 处理器测试"""

    def test_init(self):
        """测试初始化"""
        kb = MagicMock()
        h = ZhengCaiHandler(kb)
        assert h.name == PipelineStage.ZHENG_CAI
        assert h.timeout == 3.0

    def test_handle_with_query(self):
        """测试带查询参数"""
        kb = MagicMock()
        kb.query_nearest.return_value = [
            {"id": "n1", "name": "金", "node_type": "五行", "score": 0.95},
        ]
        h = ZhengCaiHandler(kb)
        ctx = PipelineContext(params={"q": "金"})
        result = h.handle(ctx)
        assert result is True
        assert len(ctx.knowledge_hits) == 1

    def test_handle_with_keyword_param(self):
        """测试 keyword 参数"""
        kb = MagicMock()
        kb.query_nearest.return_value = [{"id": "n2", "name": "木", "node_type": "五行", "score": 0.9}]
        h = ZhengCaiHandler(kb)
        ctx = PipelineContext(params={"keyword": "木"})
        result = h.handle(ctx)
        assert result is True
        assert len(ctx.knowledge_hits) == 1

    def test_handle_empty_query(self):
        """测试空查询"""
        kb = MagicMock()
        h = ZhengCaiHandler(kb)
        ctx = PipelineContext(params={})
        result = h.handle(ctx)
        assert result is True
        assert ctx.knowledge_hits == []

    def test_handle_cache_hit(self):
        """测试缓存命中"""
        kb = MagicMock()
        kb.query_nearest.return_value = [{"id": "n1", "name": "金", "score": 0.95}]
        h = ZhengCaiHandler(kb)
        ctx = PipelineContext(params={"q": "金"})
        # 第一次查询
        h.handle(ctx)
        kb.query_nearest.assert_called_once()
        # 第二次查询应命中缓存
        kb.query_nearest.reset_mock()
        ctx2 = PipelineContext(params={"q": "金"})
        h.handle(ctx2)
        kb.query_nearest.assert_not_called()

    def test_handle_lru_eviction(self):
        """测试 LRU 缓存淘汰"""
        kb = MagicMock()
        kb.query_nearest.return_value = [{"id": "n1", "name": "test"}]
        h = ZhengCaiHandler(kb)
        h._cache_max_size = 2  # 小缓存便于测试

        # 填充缓存
        for i in range(3):
            ctx = PipelineContext(params={"q": f"query_{i}"})
            h.handle(ctx)

        # 缓存大小不超过最大限制
        assert len(h._cache) <= 2


class TestPianCaiHandler:
    """偏财_搜索 处理器测试"""

    def test_init(self):
        """测试初始化"""
        kb = MagicMock()
        h = PianCaiHandler(kb)
        assert h.name == PipelineStage.PIAN_CAI
        assert h.timeout == 3.0

    def test_handle_with_query_and_knowledge_hits(self):
        """测试有知识命中的搜索"""
        kb = MagicMock()
        kb.find_by_name.return_value = []
        kb.query_by_prefix.return_value = []
        kb.neighbors.return_value = []
        h = PianCaiHandler(kb)
        ctx = PipelineContext(params={"q": "金"})
        ctx.knowledge_hits = [{"id": "n1", "name": "金", "node_type": "五行", "score": 0.95}]
        result = h.handle(ctx)
        assert result is True

    def test_handle_empty_query(self):
        """测试空查询"""
        kb = MagicMock()
        h = PianCaiHandler(kb)
        ctx = PipelineContext(params={})
        result = h.handle(ctx)
        assert result is True

    def test_handle_semantic_fallback(self):
        """测试语义搜索回退"""
        kb = MagicMock()
        kb.query_nearest.return_value = [{"id": "n1", "name": "金", "node_type": "五行", "score": 0.95}]
        kb.find_by_name.return_value = []
        kb.query_by_prefix.return_value = []
        kb.neighbors.return_value = []
        h = PianCaiHandler(kb)
        ctx = PipelineContext(params={"q": "金"})
        result = h.handle(ctx)
        assert result is True

    def test_handle_keyword_matches(self):
        """测试关键词搜索匹配（find_by_name 返回结果）"""
        kb = MagicMock()
        kb.query_nearest.return_value = []
        # 模拟 find_by_name 返回节点列表
        mock_node = MagicMock()
        mock_node.id = "n_keyword"
        mock_node.name = "金"
        mock_node.node_type = "五行"
        kb.find_by_name.return_value = [mock_node]
        kb.neighbors.return_value = []
        h = PianCaiHandler(kb)
        ctx = PipelineContext(params={"q": "金"})
        result = h.handle(ctx)
        assert result is True
        assert len(ctx.search_results) > 0

    def test_handle_keyword_prefix_fallback(self):
        """测试关键词搜索前缀回退（find_by_name 返回空，query_by_prefix 返回结果）"""
        kb = MagicMock()
        kb.query_nearest.return_value = []
        kb.find_by_name.return_value = []
        mock_node = MagicMock()
        mock_node.id = "n_prefix"
        mock_node.name = "金元素"
        mock_node.node_type = "五行"
        kb.query_by_prefix.return_value = [mock_node]
        kb.neighbors.return_value = []
        h = PianCaiHandler(kb)
        ctx = PipelineContext(params={"q": "金"})
        result = h.handle(ctx)
        assert result is True
        assert len(ctx.search_results) > 0

    def test_handle_graph_neighbors(self):
        """测试图谱邻居搜索"""
        kb = MagicMock()
        kb.query_nearest.return_value = [{"id": "n1", "name": "金", "node_type": "五行", "score": 0.95}]
        kb.find_by_name.return_value = []
        kb.query_by_prefix.return_value = []
        mock_neighbor = MagicMock()
        mock_neighbor.id = "n_neighbor"
        mock_neighbor.name = "土"
        mock_neighbor.node_type = "五行"
        kb.neighbors.return_value = [mock_neighbor]
        h = PianCaiHandler(kb)
        ctx = PipelineContext(params={"q": "金"})
        result = h.handle(ctx)
        assert result is True
        assert len(ctx.search_results) > 0


class TestShiShenHandler:
    """食神_生成 处理器测试"""

    def test_init(self):
        """测试初始化"""
        h = ShiShenHandler()
        assert h.name == PipelineStage.SHI_SHEN
        assert h.timeout == 30.0

    def test_handle_with_results(self):
        """测试有搜索结果时生成内容"""
        h = ShiShenHandler()
        ctx = PipelineContext(
            params={"q": "五行"},
        )
        ctx.search_results = [{"name": "金", "node_type": "五行"}]
        ctx.routed_target = "知识图谱"
        result = h.handle(ctx)
        assert result is True
        assert len(ctx.generated_content) > 0
        assert "五行" in ctx.generated_content

    def test_handle_with_knowledge_hits_only(self):
        """测试仅有知识命中时生成内容"""
        h = ShiShenHandler()
        ctx = PipelineContext(params={"q": "金"})
        ctx.knowledge_hits = [{"name": "金", "node_type": "五行"}]
        result = h.handle(ctx)
        assert result is True
        assert len(ctx.generated_content) > 0

    def test_handle_empty(self):
        """测试无结果时不生成"""
        h = ShiShenHandler()
        ctx = PipelineContext()
        result = h.handle(ctx)
        assert result is True
        assert ctx.generated_content == ""

    def test_handle_with_keyword_param(self):
        """测试 keyword 参数"""
        h = ShiShenHandler()
        ctx = PipelineContext(params={"keyword": "道家"})
        ctx.search_results = [{"name": "道家", "node_type": "学派"}]
        result = h.handle(ctx)
        assert result is True
        assert "道家" in ctx.generated_content


class TestShangGuanHandler:
    """伤官_创新 处理器测试"""

    def test_init(self):
        """测试初始化"""
        h = ShangGuanHandler()
        assert h.name == PipelineStage.SHANG_GUAN
        assert h.timeout == 5.0

    def test_handle_with_results(self):
        """测试有搜索结果时生成创意"""
        h = ShangGuanHandler()
        ctx = PipelineContext(
            params={"q": "金"},
        )
        ctx.request_id = "test123"
        ctx.search_results = [
            {"name": "金", "node_type": "五行"},
            {"name": "木", "node_type": "五行"},
            {"name": "水", "node_type": "五行"},
        ]
        result = h.handle(ctx)
        assert result is True
        assert len(ctx.innovation_ideas) > 0

    def test_handle_empty_results(self):
        """测试无搜索结果时跳过"""
        h = ShangGuanHandler()
        ctx = PipelineContext()
        result = h.handle(ctx)
        assert result is True
        assert ctx.innovation_ideas == []


class TestQiShaHandler:
    """七杀_裁决 处理器测试"""

    def test_init(self):
        """测试初始化"""
        h = QiShaHandler()
        assert h.name == PipelineStage.QI_SHA
        assert h.timeout == 3.0

    def test_handle_with_content(self):
        """测试有内容时评估质量"""
        h = QiShaHandler()
        ctx = PipelineContext(
            params={"q": "金"},
        )
        ctx.search_results = [{"name": "金", "node_type": "五行"}]
        ctx.generated_content = "测试内容" * 20
        ctx.innovation_ideas = [{"title": "test"}]
        result = h.handle(ctx)
        assert result is True
        assert "score" in ctx.quality_report
        assert "grade" in ctx.quality_report

    def test_handle_empty_pipeline(self):
        """测试空管道质量评估"""
        h = QiShaHandler()
        ctx = PipelineContext()
        result = h.handle(ctx)
        assert result is True
        assert "score" in ctx.quality_report


class TestTaiJiHandler:
    """太极_调和 处理器测试"""

    def test_init(self):
        """测试初始化"""
        h = TaiJiHandler()
        assert h.name == PipelineStage.TAI_JI
        assert h.timeout == 2.0

    def test_handle_high_quality(self):
        """测试高质量响应"""
        h = TaiJiHandler()
        ctx = PipelineContext()
        ctx.quality_report = {"score": 85}
        result = h.handle(ctx)
        assert result is True
        assert ctx.balance_state is not None

    def test_handle_low_quality(self):
        """测试低质量响应"""
        h = TaiJiHandler()
        ctx = PipelineContext()
        ctx.quality_report = {"score": 50}
        result = h.handle(ctx)
        assert result is True

    def test_handle_normal_quality(self):
        """测试正常质量响应"""
        h = TaiJiHandler()
        ctx = PipelineContext()
        ctx.quality_report = {"score": 70}
        result = h.handle(ctx)
        assert result is True


class TestZhengYinHandler:
    """正印_配置 处理器测试"""

    def test_init(self):
        """测试初始化"""
        h = ZhengYinHandler()
        assert h.name == PipelineStage.ZHENG_YIN
        assert h.timeout == 1.0

    def test_handle(self):
        """测试配置注入"""
        h = ZhengYinHandler()
        ctx = PipelineContext()
        result = h.handle(ctx)
        assert result is True
        assert "pipeline_version" in ctx.response
        assert "config" in ctx.response


class TestJieCaiHandler:
    """劫财_安全 处理器测试"""

    def test_init(self):
        """测试初始化"""
        h = JieCaiHandler()
        assert h.name == PipelineStage.JIE_CAI
        assert h.timeout == 1.0

    def test_handle_safe_params(self):
        """测试安全参数"""
        h = JieCaiHandler()
        ctx = PipelineContext(params={"q": "金"})
        result = h.handle(ctx)
        assert result is True
        assert ctx.security_context["validated"] is True
        assert len(ctx.security_context["threats"]) == 0

    def test_handle_sql_injection(self):
        """测试 SQL 注入检测"""
        h = JieCaiHandler()
        ctx = PipelineContext(params={"q": "' OR 1=1 --"})
        result = h.handle(ctx)
        assert result is False
        assert ctx.status_code == 400
        assert "检测到攻击签名" in ctx.response.get("error", "")

    def test_handle_drop_table(self):
        """测试 DROP TABLE 检测"""
        h = JieCaiHandler()
        ctx = PipelineContext(params={"q": "DROP TABLE users"})
        result = h.handle(ctx)
        assert result is False
        assert ctx.status_code == 400

    def test_handle_xss(self):
        """测试 XSS 检测"""
        h = JieCaiHandler()
        ctx = PipelineContext(params={"q": "<script>alert(1)</script>"})
        result = h.handle(ctx)
        assert result is False
        assert ctx.status_code == 400

    def test_handle_exec_injection(self):
        """测试 exec() 注入检测"""
        h = JieCaiHandler()
        ctx = PipelineContext(params={"q": "exec('rm -rf /')"})
        result = h.handle(ctx)
        assert result is False
        assert ctx.status_code == 400

    def test_handle_empty_params(self):
        """测试空参数"""
        h = JieCaiHandler()
        ctx = PipelineContext(params={})
        result = h.handle(ctx)
        assert result is True


class TestPianYinHandler:
    """偏印_适配 处理器测试"""

    def test_init(self):
        """测试初始化"""
        h = PianYinHandler()
        assert h.name == PipelineStage.PIAN_YIN
        assert h.timeout == 2.0

    def test_handle(self):
        """测试格式适配"""
        h = PianYinHandler()
        ctx = PipelineContext(
            params={"q": "金"},
        )
        ctx.routed_target = "知识图谱"
        ctx.search_results = [{"name": "金", "node_type": "五行"}]
        ctx.generated_content = "测试内容"
        ctx.innovation_ideas = [{"title": "test"}]
        ctx.quality_report = {"score": 85, "grade": "A"}
        ctx.balance_state = "balanced"
        result = h.handle(ctx)
        assert result is True
        assert ctx.adapted_output is not None
        assert "output" in ctx.response
        assert "confidence" in ctx.response
        assert "uncertainty" in ctx.response

    def test_handle_empty_results(self):
        """测试空结果"""
        h = PianYinHandler()
        ctx = PipelineContext()
        result = h.handle(ctx)
        assert result is True
        assert ctx.adapted_output is not None


class TestBiJianHandler:
    """比肩_协同 处理器测试"""

    def test_init(self):
        """测试初始化"""
        h = BiJianHandler()
        assert h.name == PipelineStage.BI_JIAN
        assert h.timeout == 1.0

    def test_handle(self):
        """测试组件协同"""
        h = BiJianHandler()
        ctx = PipelineContext()
        result = h.handle(ctx)
        assert result is True
        assert "components" in ctx.response
        assert ctx.finished_at > 0


# ════════════════════════════════════════════════════════════════
# 5. TenStemPipeline 测试
# ════════════════════════════════════════════════════════════════

class TestTenStemPipelineInit:
    """TenStemPipeline 初始化测试"""

    def test_init_with_default_kb(self):
        """测试默认 KB 初始化"""
        p = TenStemPipeline()
        assert p is not None
        assert len(p._handlers) == 12

    def test_init_with_custom_kb(self, mock_kb):
        """测试自定义 KB 初始化"""
        p = TenStemPipeline(mock_kb)
        assert p._kb is mock_kb

    def test_init_all_handlers_registered(self, pipeline):
        """测试所有 12 个处理器已注册"""
        for stage in PIPELINE_ORDER:
            assert stage in pipeline._handlers
            assert pipeline._handlers[stage] is not None

    def test_pipeline_info(self, pipeline, mock_kb):
        """测试 pipeline_info 方法"""
        info = pipeline.pipeline_info()
        assert info["version"] == "2.17.0"
        assert len(info["stages"]) == 12
        assert "knowledge_base" in info
        # 验证每个阶段信息
        for stage_info in info["stages"]:
            assert "name" in stage_info
            assert "enabled" in stage_info
            assert "timeout" in stage_info

    def test_pipeline_info_all_stages_enabled_by_default(self, pipeline):
        """测试默认所有阶段启用"""
        info = pipeline.pipeline_info()
        for stage_info in info["stages"]:
            assert stage_info["enabled"] is True


class TestTenStemPipelineRun:
    """TenStemPipeline run 方法测试"""

    def test_run_returns_context(self, pipeline, ctx):
        """测试 run 返回 PipelineContext"""
        result = pipeline.run(ctx)
        assert result is ctx

    def test_run_all_stages_executed(self, pipeline, ctx):
        """测试完整管道执行（所有阶段）"""
        result = pipeline.run(ctx)
        executed = set(ctx.stage_results.keys()) | set(ctx.skipped_stages)
        expected = {s.value for s in PIPELINE_ORDER}
        assert executed == expected

    def test_run_with_disabled_stage(self, pipeline):
        """测试禁用某个阶段后执行"""
        pipeline.disable_stage(PipelineStage.SHANG_GUAN)
        ctx = PipelineContext(
            method="GET", path="/api/graph/search", params={"q": "金"}
        )
        pipeline.run(ctx)
        assert PipelineStage.SHANG_GUAN.value in ctx.skipped_stages

    def test_run_with_multiple_disabled_stages(self, pipeline):
        """测试禁用多个阶段后执行"""
        pipeline.disable_stage(PipelineStage.SHANG_GUAN)
        pipeline.disable_stage(PipelineStage.QI_SHA)
        pipeline.disable_stage(PipelineStage.TAI_JI)
        ctx = PipelineContext(
            method="GET", path="/api/graph/search", params={"q": "水"}
        )
        pipeline.run(ctx)
        assert len(ctx.skipped_stages) >= 3

    def test_run_with_all_disabled(self, pipeline):
        """测试全部禁用后执行"""
        for stage in PIPELINE_ORDER:
            pipeline.disable_stage(stage)
        ctx = PipelineContext(method="GET", path="/api/health")
        result = pipeline.run(ctx)
        assert result is ctx
        assert len(ctx.skipped_stages) == 12

    def test_run_sets_finished_at(self, pipeline, ctx):
        """测试 run 设置 finished_at"""
        pipeline.run(ctx)
        assert ctx.finished_at > ctx.started_at
        assert ctx.finished_at > 0

    def test_run_with_sql_injection_stops_early(self, pipeline):
        """测试 SQL 注入导致管道提前终止"""
        ctx = PipelineContext(
            method="GET", path="/api/graph/search", params={"q": "' OR 1=1 --"}
        )
        pipeline.run(ctx)
        assert ctx.status_code == 400

    def test_run_with_invalid_path_stops_early(self, pipeline):
        """测试无效路径导致管道提前终止"""
        ctx = PipelineContext(method="GET", path="bad_path")
        pipeline.run(ctx)
        assert ctx.status_code == 400

    def test_run_multiple_times(self, pipeline):
        """测试多次运行"""
        queries = ["金", "木", "水", "火", "土"]
        for q in queries:
            ctx = PipelineContext(
                method="GET", path="/api/graph/search", params={"q": q}
            )
            pipeline.run(ctx)
            assert len(ctx.errors) == 0

    def test_run_different_routes(self, pipeline):
        """测试不同路由"""
        routes = [
            ("GET", "/api/health", {}),
            ("GET", "/api/graph/search", {"q": "儒家"}),
            ("POST", "/api/bazi/calc", {}),
            ("GET", "/api/auth/me", {}),
            ("GET", "/api/knowledge/items", {"q": "火"}),
        ]
        for method, path, params in routes:
            ctx = PipelineContext(method=method, path=path, params=params)
            pipeline.run(ctx)
            assert len(ctx.errors) == 0

    def test_run_with_custom_context(self, pipeline):
        """测试带自定义上下文运行"""
        ctx = PipelineContext(
            method="POST",
            path="/api/bazi/calc",
            params={"year": 1990, "month": 6, "day": 15},
            body={"source": "web"},
            user={"id": "user_001"},
        )
        pipeline.run(ctx)
        assert ctx.routed_target == "八字排盘"
        assert len(ctx.errors) == 0


class TestTenStemPipelineQuickRun:
    """TenStemPipeline run_quick 方法测试"""

    def test_run_quick_returns_dict(self, pipeline):
        """测试返回 dict"""
        response = pipeline.run_quick("GET", "/api/graph/search", {"q": "金"})
        assert isinstance(response, dict)

    def test_run_quick_has_output(self, pipeline):
        """测试响应包含 output"""
        response = pipeline.run_quick("GET", "/api/graph/search", {"q": "金"})
        assert "output" in response

    def test_run_quick_has_confidence(self, pipeline):
        """测试响应包含 confidence"""
        response = pipeline.run_quick("GET", "/api/graph/search", {"q": "金"})
        assert "confidence" in response

    def test_run_quick_has_uncertainty(self, pipeline):
        """测试响应包含 uncertainty"""
        response = pipeline.run_quick("GET", "/api/graph/search", {"q": "金"})
        assert "uncertainty" in response

    def test_run_quick_with_body(self, pipeline):
        """测试带 body 的快速运行"""
        response = pipeline.run_quick(
            "POST", "/api/bazi/calc", params={}, body={"year": 1990}
        )
        assert "output" in response

    def test_run_quick_no_params(self, pipeline):
        """测试不带参数"""
        response = pipeline.run_quick("GET", "/api/health")
        assert "output" in response

    def test_run_quick_health(self, pipeline):
        """测试健康检查快速运行"""
        response = pipeline.run_quick("GET", "/api/health")
        assert isinstance(response, dict)


class TestTenStemPipelineStageControl:
    """TenStemPipeline 阶段控制测试"""

    def test_disable_stage(self, pipeline):
        """测试禁用阶段"""
        pipeline.disable_stage(PipelineStage.SHANG_GUAN)
        assert pipeline._handlers[PipelineStage.SHANG_GUAN].enabled is False

    def test_enable_stage(self, pipeline):
        """测试启用阶段"""
        pipeline.disable_stage(PipelineStage.SHANG_GUAN)
        pipeline.enable_stage(PipelineStage.SHANG_GUAN)
        assert pipeline._handlers[PipelineStage.SHANG_GUAN].enabled is True

    def test_disable_and_enable_cycle(self, pipeline):
        """测试禁用/启用循环"""
        stage = PipelineStage.QI_SHA
        assert pipeline._handlers[stage].enabled is True
        pipeline.disable_stage(stage)
        assert pipeline._handlers[stage].enabled is False
        pipeline.enable_stage(stage)
        assert pipeline._handlers[stage].enabled is True

    def test_get_handler(self, pipeline):
        """测试获取处理器"""
        handler = pipeline.get_handler(PipelineStage.ZHENG_CAI)
        assert handler is not None
        assert handler.name == PipelineStage.ZHENG_CAI

    def test_get_handler_all_stages(self, pipeline):
        """测试获取所有处理器"""
        for stage in PIPELINE_ORDER:
            handler = pipeline.get_handler(stage)
            assert handler is not None
            assert handler.name == stage


# ════════════════════════════════════════════════════════════════
# 6. get_pipeline 单例测试
# ════════════════════════════════════════════════════════════════

class TestGetPipeline:
    """get_pipeline 单例测试"""

    def test_singleton_same_instance(self):
        """测试单例返回同一实例"""
        p1 = get_pipeline()
        p2 = get_pipeline()
        assert p1 is p2

    def test_singleton_accepts_kb(self, mock_kb):
        """测试单例接受 KB 参数"""
        p = get_pipeline(mock_kb)
        assert p is not None
        assert p._kb is mock_kb

    def test_singleton_new_kb_replaces(self, mock_kb):
        """测试传入新 KB 会创建新实例（kb is not None 时总是创建新实例）"""
        import tengod.pipeline as pipeline_mod
        pipeline_mod._global_pipeline = None
        p1 = get_pipeline()
        p2 = get_pipeline(mock_kb)
        # 传入 kb 参数时创建新实例，全局单例被替换
        assert p2._kb is mock_kb
        # 之后再调用不带 kb 参数的 get_pipeline 会返回新实例
        p3 = get_pipeline()
        assert p3 is p2

    def test_singleton_none_kb_keeps_existing(self):
        """测试传入 None 保持现有实例"""
        import tengod.pipeline as pipeline_mod
        pipeline_mod._global_pipeline = None
        p1 = get_pipeline()
        p2 = get_pipeline()
        assert p1 is p2


# ════════════════════════════════════════════════════════════════
# 7. 错误处理与边界条件测试
# ════════════════════════════════════════════════════════════════

class TestEdgeCases:
    """错误处理与边界条件测试"""

    def test_empty_params(self, pipeline):
        """测试空参数不会崩溃"""
        ctx = PipelineContext(method="GET", path="/api/health")
        pipeline.run(ctx)
        assert len(ctx.errors) == 0

    def test_large_query(self, pipeline):
        """测试超长查询字符串"""
        long_query = "金" * 500
        ctx = PipelineContext(
            method="GET", path="/api/graph/search", params={"q": long_query}
        )
        pipeline.run(ctx)
        assert len(ctx.errors) == 0

    def test_unknown_path(self, pipeline):
        """测试未知路径"""
        ctx = PipelineContext(method="GET", path="/api/unknown/endpoint")
        pipeline.run(ctx)
        assert ctx.routed_target == "通用请求"
        assert len(ctx.errors) == 0

    def test_special_characters_in_params(self, pipeline):
        """测试参数中的特殊字符（非攻击性）"""
        ctx = PipelineContext(
            method="GET", path="/api/graph/search", params={"q": "金&木&水"}
        )
        pipeline.run(ctx)
        assert len(ctx.errors) == 0

    def test_numeric_params(self, pipeline):
        """测试数值参数"""
        ctx = PipelineContext(
            method="POST", path="/api/bazi/calc", params={"year": 1990, "month": 6}
        )
        pipeline.run(ctx)
        assert len(ctx.errors) == 0

    def test_boolean_params(self, pipeline):
        """测试布尔参数"""
        ctx = PipelineContext(
            method="GET", path="/api/graph/search", params={"q": "金", "verbose": True}
        )
        pipeline.run(ctx)
        assert len(ctx.errors) == 0

    def test_pipeline_timing_reasonable(self, pipeline):
        """测试管道执行时间合理"""
        ctx = PipelineContext(
            method="GET", path="/api/graph/search", params={"q": "木"}
        )
        pipeline.run(ctx)
        elapsed = ctx.finished_at - ctx.started_at
        assert elapsed < 10.0  # 应在 10 秒内完成

    def test_response_has_all_fields(self, pipeline):
        """测试响应包含所有字段"""
        response = pipeline.run_quick("GET", "/api/graph/search", {"q": "道家"})
        output = response.get("output", {})
        assert "request_id" in output
        assert "target" in output
        assert "pipeline" in output
        assert "quality" in output

    def test_quality_report_fields(self, pipeline):
        """测试质量报告包含关键字段"""
        ctx = PipelineContext(
            method="GET", path="/api/graph/search", params={"q": "儒家"}
        )
        pipeline.run(ctx)
        assert ctx.quality_report is not None
        assert "score" in ctx.quality_report
        assert "grade" in ctx.quality_report

    def test_run_with_zero_stages_configured(self, pipeline):
        """测试零阶段配置（全部禁用）"""
        for stage in PIPELINE_ORDER:
            pipeline.disable_stage(stage)
        ctx = PipelineContext()
        result = pipeline.run(ctx)
        assert result is ctx
        assert len(ctx.skipped_stages) == 12
        assert len(ctx.stage_results) == 0

    def test_multiple_run_calls(self, pipeline):
        """测试连续多次 run 调用"""
        for i in range(5):
            ctx = PipelineContext(
                method="GET", path="/api/graph/search", params={"q": f"测试{i}"}
            )
            pipeline.run(ctx)
            assert len(ctx.errors) == 0

    def test_pipeline_instance_reuse(self, pipeline):
        """测试管道实例复用"""
        for i in range(3):
            ctx = PipelineContext(
                method="GET", path="/api/graph/search", params={"q": f"query_{i}"}
            )
            pipeline.run(ctx)
            assert len(ctx.errors) == 0


# ════════════════════════════════════════════════════════════════
# 8. 综合覆盖测试
# ════════════════════════════════════════════════════════════════

class TestComprehensiveCoverage:
    """综合覆盖测试"""

    def test_all_stages_covered(self, pipeline):
        """验证所有 12 个阶段都被执行或跳过"""
        ctx = PipelineContext(
            method="GET", path="/api/graph/search", params={"q": "五行"}
        )
        pipeline.run(ctx)
        executed = set(ctx.stage_results.keys()) | set(ctx.skipped_stages)
        expected = {s.value for s in PIPELINE_ORDER}
        assert executed == expected, f"未覆盖的阶段: {expected - executed}"

    def test_all_stage_handlers_instantiable(self, mock_kb):
        """验证所有阶段处理器都可以实例化"""
        handlers = [
            ZhengGuanHandler(),
            YuanChenHandler(),
            ZhengCaiHandler(mock_kb),
            PianCaiHandler(mock_kb),
            ShiShenHandler(),
            ShangGuanHandler(),
            QiShaHandler(),
            TaiJiHandler(),
            ZhengYinHandler(),
            JieCaiHandler(),
            PianYinHandler(),
            BiJianHandler(),
        ]
        assert len(handlers) == 12
        for h in handlers:
            assert h.enabled is True

    def test_all_stage_names_unique(self):
        """验证所有阶段名称唯一"""
        names = [s.value for s in PIPELINE_ORDER]
        assert len(names) == len(set(names))

    def test_pipeline_stage_order_stable(self):
        """验证管道阶段顺序稳定"""
        order1 = PIPELINE_ORDER
        order2 = list(PipelineStage)
        assert order1 == order2

    def test_context_request_id_unique(self):
        """验证每个上下文 request_id 唯一"""
        ids = {PipelineContext().request_id for _ in range(100)}
        assert len(ids) == 100

    def test_router_prefix(self):
        """验证 ZhengGuanHandler 中 APIRouter 前缀"""
        h = ZhengGuanHandler()
        # 验证 APIRouter 被正确调用
        _mock_api_router_module.APIRouter.assert_called_with(prefix="/api")


# ════════════════════════════════════════════════════════════════
# 9. 阶段处理器异常处理测试
# ════════════════════════════════════════════════════════════════

class TestHandlerExceptionHandling:
    """阶段处理器异常处理测试"""

    def test_zheng_guan_handler_exception(self):
        """测试正官处理器异常"""
        h = ZhengGuanHandler()
        ctx = PipelineContext(method="GET", path="/api/test")
        result = h(ctx)
        assert result is True
        assert PipelineStage.ZHENG_GUAN.value in ctx.stage_results

    def test_yuan_chen_handler_exception(self):
        """测试元辰处理器异常"""
        h = YuanChenHandler()
        ctx = PipelineContext(method="GET", path="/api/unknown")
        result = h(ctx)
        assert result is True

    def test_zheng_cai_handler_exception(self, mock_kb):
        """测试正财处理器异常"""
        mock_kb.query_nearest.side_effect = RuntimeError("数据库连接失败")
        h = ZhengCaiHandler(mock_kb)
        ctx = PipelineContext(params={"q": "金"})
        result = h(ctx)
        # StageHandler.__call__ 会捕获异常
        assert result is True

    def test_handler_call_exception_is_caught(self):
        """测试 __call__ 捕获异常并记录"""
        handler = StageHandler(PipelineStage.ZHENG_GUAN)
        handler.handle = MagicMock(side_effect=RuntimeError("严重错误"))

        ctx = PipelineContext()
        result = handler(ctx)

        assert result is True
        assert PipelineStage.ZHENG_GUAN.value in ctx.errors
        assert "严重错误" in ctx.errors[PipelineStage.ZHENG_GUAN.value]
        assert PipelineStage.ZHENG_GUAN.value in ctx.stage_results

    def test_handler_call_chained_exception(self):
        """测试链式异常"""
        handler = StageHandler(PipelineStage.ZHENG_CAI)
        handler.handle = MagicMock(side_effect=Exception("链式错误"))

        ctx = PipelineContext()
        result = handler(ctx)

        assert result is True
        assert PipelineStage.ZHENG_CAI.value in ctx.errors


# ════════════════════════════════════════════════════════════════
# 10. 所有路由覆盖测试
# ════════════════════════════════════════════════════════════════

class TestAllRoutes:
    """所有路由覆盖测试"""

    def test_all_route_mappings(self):
        """验证所有路由映射"""
        h = YuanChenHandler()
        routes = [
            ("/api/bazi/calc", "八字排盘"),
            ("/api/ziwei/pan", "紫微斗数"),
            ("/api/liuyao/divine", "六爻占卜"),
            ("/api/name/analyze", "姓名分析"),
            ("/api/graph/search", "知识图谱"),
            ("/api/knowledge/wuxing/金", "知识查询"),
            ("/api/auth/login", "认证系统"),
            ("/api/health", "健康检查"),
            ("/api/records/list", "记录管理"),
        ]
        for path, expected_target in routes:
            ctx = PipelineContext(method="GET", path=path)
            h.handle(ctx)
            assert ctx.routed_target == expected_target, f"路径 {path} 路由到 {ctx.routed_target}，期望 {expected_target}"

    def test_route_matching_precedence(self):
        """测试路由匹配优先级（bazi 在 knowledge 中）"""
        h = YuanChenHandler()
        # path 同时包含 "knowledge" 和 "records"，应匹配先出现的
        ctx = PipelineContext(method="GET", path="/api/knowledge/records")
        h.handle(ctx)
        # 按 ROUTE_MAP 顺序，先匹配 knowledge
        assert ctx.routed_target == "知识查询"