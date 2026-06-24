#!/usr/bin/env python3
"""
test_pipeline.py — 十神管道集成测试 v2.17.0
===========================================
测试 12 个十神模块的端到端编排管道。
覆盖：管道创建、阶段执行、错误处理、禁用/启用、快速运行。

用法：
    pytest tests/test_pipeline.py -v
    pytest tests/test_pipeline.py -v --runxfail
"""
import os
import sys
import time

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from tengod.pipeline import (
    TenStemPipeline,
    PipelineContext,
    PipelineStage,
    PIPELINE_ORDER,
    get_pipeline,
)
from tengod.正财_知识固化.knowledge_base import KnowledgeBase


# ── Fixtures ──

@pytest.fixture
def kb():
    """创建带测试数据的知识库"""
    kb = KnowledgeBase()
    kb.add_node("金", node_type="五行", properties={"方位": "西", "季节": "秋"})
    kb.add_node("木", node_type="五行", properties={"方位": "东", "季节": "春"})
    kb.add_node("水", node_type="五行", properties={"方位": "北", "季节": "冬"})
    kb.add_node("火", node_type="五行", properties={"方位": "南", "季节": "夏"})
    kb.add_node("土", node_type="五行", properties={"方位": "中", "季节": "长夏"})
    kb.add_node("儒家", node_type="学派", properties={"代表": "孔子"})
    kb.add_node("道家", node_type="学派", properties={"代表": "老子"})
    return kb


@pytest.fixture
def pipeline(kb):
    """创建管道实例"""
    return TenStemPipeline(kb)


@pytest.fixture
def ctx():
    """创建管道上下文"""
    return PipelineContext(
        method="GET",
        path="/api/graph/search",
        params={"q": "金"},
    )


# ════════════════════════════════════════════════════════════════
# 1. 管道创建与基础 (5)
# ════════════════════════════════════════════════════════════════

class TestPipelineCreation:
    """管道创建与基础结构"""

    def test_create_pipeline(self):
        """创建 TenStemPipeline"""
        p = TenStemPipeline()
        assert p is not None
        assert len(p._handlers) == 12

    def test_create_pipeline_with_kb(self, kb):
        """使用知识库创建管道"""
        p = TenStemPipeline(kb)
        assert p._kb is kb

    def test_pipeline_info(self, pipeline):
        """管道信息"""
        info = pipeline.pipeline_info()
        assert info["version"] == "2.17.0"
        assert len(info["stages"]) == 12
        assert info["knowledge_base"]["nodes"] >= 7

    def test_pipeline_stages_order(self):
        """管道阶段顺序正确"""
        assert len(PIPELINE_ORDER) == 12
        assert PIPELINE_ORDER[0] == PipelineStage.ZHENG_GUAN
        assert PIPELINE_ORDER[-1] == PipelineStage.BI_JIAN

    def test_get_pipeline_global(self):
        """全局管道单例"""
        p1 = get_pipeline()
        p2 = get_pipeline()
        assert p1 is p2


# ════════════════════════════════════════════════════════════════
# 2. 管道上下文 (4)
# ════════════════════════════════════════════════════════════════

class TestPipelineContext:
    """管道上下文测试"""

    def test_context_creation(self):
        """创建上下文"""
        ctx = PipelineContext(method="POST", path="/api/bazi/calc")
        assert ctx.method == "POST"
        assert ctx.path == "/api/bazi/calc"
        assert len(ctx.request_id) == 12
        assert ctx.started_at > 0

    def test_context_add_stage_result(self):
        """添加阶段结果"""
        ctx = PipelineContext()
        ctx.add_stage_result(PipelineStage.ZHENG_GUAN, "ok", 0.001)
        assert PipelineStage.ZHENG_GUAN.value in ctx.stage_results
        assert ctx.stage_timings[PipelineStage.ZHENG_GUAN.value] == 0.001

    def test_context_add_error(self):
        """添加错误"""
        ctx = PipelineContext()
        ctx.add_error(PipelineStage.QI_SHA, "质量评估超时")
        assert PipelineStage.QI_SHA.value in ctx.errors
        assert ctx.errors[PipelineStage.QI_SHA.value] == "质量评估超时"

    def test_context_summary(self, ctx):
        """上下文摘要"""
        summary = ctx.summary()
        assert "request_id" in summary
        assert summary["path"] == "/api/graph/search"
        assert "total_time_ms" in summary


# ════════════════════════════════════════════════════════════════
# 3. 管道执行 (8)
# ════════════════════════════════════════════════════════════════

class TestPipelineExecution:
    """管道执行测试"""

    def test_run_full_pipeline(self, pipeline, ctx):
        """运行完整 12 阶段管道"""
        result = pipeline.run(ctx)
        assert result is ctx
        assert len(ctx.stage_results) >= 10  # 部分阶段可能无操作
        assert len(ctx.errors) == 0
        assert ctx.response is not None

    def test_run_quick(self, pipeline):
        """快速运行"""
        response = pipeline.run_quick("GET", "/api/graph/search", {"q": "金"})
        assert "output" in response
        assert "confidence" in response
        assert "uncertainty" in response

    def test_pipeline_with_knowledge_query(self, pipeline):
        """知识查询管道"""
        ctx = PipelineContext(method="GET", path="/api/knowledge/wuxing/金", params={"q": "金"})
        result = pipeline.run(ctx)
        assert len(ctx.errors) == 0
        assert len(ctx.knowledge_hits) > 0 or ctx.search_results  # 至少命中一阶段

    def test_pipeline_with_bazi_route(self, pipeline):
        """八字排盘路由"""
        ctx = PipelineContext(method="POST", path="/api/bazi/calc", params={})
        result = pipeline.run(ctx)
        assert ctx.routed_target == "八字排盘"
        assert len(ctx.errors) == 0

    def test_pipeline_with_auth_route(self, pipeline):
        """认证路由"""
        ctx = PipelineContext(method="POST", path="/api/auth/login", params={})
        result = pipeline.run(ctx)
        assert ctx.routed_target == "认证系统"
        assert len(ctx.errors) == 0

    def test_pipeline_response_has_all_fields(self, pipeline):
        """响包含所有字段"""
        response = pipeline.run_quick("GET", "/api/graph/search", {"q": "道家"})
        output = response.get("output", {})
        assert "request_id" in output
        assert "target" in output
        assert "pipeline" in output
        assert "quality" in output

    def test_pipeline_timing(self, pipeline):
        """管道计时正常"""
        ctx = PipelineContext(method="GET", path="/api/graph/search", params={"q": "木"})
        pipeline.run(ctx)
        assert ctx.finished_at > ctx.started_at
        elapsed = ctx.finished_at - ctx.started_at
        assert elapsed < 10.0  # 应在 10 秒内完成

    def test_pipeline_quality_report(self, pipeline):
        """质量报告包含关键字段"""
        ctx = PipelineContext(method="GET", path="/api/graph/search", params={"q": "儒家"})
        pipeline.run(ctx)
        assert ctx.quality_report is not None
        assert "score" in ctx.quality_report
        assert "grade" in ctx.quality_report


# ════════════════════════════════════════════════════════════════
# 4. 阶段控制 (4)
# ════════════════════════════════════════════════════════════════

class TestStageControl:
    """阶段控制测试"""

    def test_disable_stage(self, pipeline):
        """禁用阶段"""
        pipeline.disable_stage(PipelineStage.SHANG_GUAN)
        assert pipeline._handlers[PipelineStage.SHANG_GUAN].enabled is False

        ctx = PipelineContext(method="GET", path="/api/graph/search", params={"q": "火"})
        pipeline.run(ctx)
        assert PipelineStage.SHANG_GUAN.value in ctx.skipped_stages

    def test_enable_stage(self, pipeline):
        """启用阶段"""
        pipeline.disable_stage(PipelineStage.SHANG_GUAN)
        pipeline.enable_stage(PipelineStage.SHANG_GUAN)
        assert pipeline._handlers[PipelineStage.SHANG_GUAN].enabled is True

    def test_disable_multiple_stages(self, pipeline):
        """禁用多个阶段"""
        pipeline.disable_stage(PipelineStage.SHANG_GUAN)
        pipeline.disable_stage(PipelineStage.QI_SHA)
        pipeline.disable_stage(PipelineStage.TAI_JI)

        ctx = PipelineContext(method="GET", path="/api/graph/search", params={"q": "水"})
        pipeline.run(ctx)
        assert len(ctx.skipped_stages) >= 3

    def test_get_handler(self, pipeline):
        """获取阶段处理器"""
        handler = pipeline.get_handler(PipelineStage.ZHENG_CAI)
        assert handler is not None
        assert handler.name == PipelineStage.ZHENG_CAI


# ════════════════════════════════════════════════════════════════
# 5. 错误与边界 (5)
# ════════════════════════════════════════════════════════════════

class TestErrorHandling:
    """错误处理与边界条件"""

    def test_empty_params(self, pipeline):
        """空参数不回导致崩溃"""
        ctx = PipelineContext(method="GET", path="/api/health", params={})
        result = pipeline.run(ctx)
        assert len(ctx.errors) == 0

    def test_large_search_query(self, pipeline):
        """长查询字符串"""
        long_query = "金" * 100
        ctx = PipelineContext(method="GET", path="/api/graph/search", params={"q": long_query})
        result = pipeline.run(ctx)
        assert len(ctx.errors) == 0

    def test_unknown_path(self, pipeline):
        """未知路径"""
        ctx = PipelineContext(method="GET", path="/api/unknown/endpoint", params={})
        result = pipeline.run(ctx)
        assert ctx.routed_target == "通用请求"
        assert len(ctx.errors) == 0

    def test_sql_injection_detected(self, pipeline):
        """SQL 注入检测"""
        ctx = PipelineContext(method="GET", path="/api/graph/search",
                              params={"q": "' OR 1=1 --"})
        result = pipeline.run(ctx)
        # 应被劫财阶段拦截
        assert ctx.status_code == 400 or "检测到攻击签名" in str(ctx.response.get("error", ""))

    def test_xss_detected(self, pipeline):
        """XSS 检测"""
        ctx = PipelineContext(method="GET", path="/api/graph/search",
                              params={"q": "<script>alert(1)</script>"})
        result = pipeline.run(ctx)
        assert ctx.status_code == 400 or "检测到攻击签名" in str(ctx.response.get("error", ""))


# ════════════════════════════════════════════════════════════════
# 6. 多请求并发 (3)
# ════════════════════════════════════════════════════════════════

class TestConcurrentRequests:
    """并发请求测试"""

    def test_multiple_sequential_requests(self, pipeline):
        """连续多次请求"""
        queries = ["金", "木", "水", "火", "土"]
        for q in queries:
            ctx = PipelineContext(method="GET", path="/api/graph/search", params={"q": q})
            pipeline.run(ctx)
            assert len(ctx.errors) == 0

    def test_different_routes(self, pipeline):
        """不同路由"""
        routes = [
            ("GET", "/api/health", {}),
            ("GET", "/api/graph/search", {"q": "儒家"}),
            ("POST", "/api/bazi/calc", {}),
            ("GET", "/api/auth/me", {}),
            ("GET", "/api/knowledge/wuxing/火", {"q": "火"}),
        ]
        for method, path, params in routes:
            ctx = PipelineContext(method=method, path=path, params=params)
            pipeline.run(ctx)
            assert len(ctx.errors) == 0

    def test_pipeline_instance_reuse(self, pipeline):
        """管道实例复用"""
        for i in range(5):
            ctx = PipelineContext(method="GET", path="/api/graph/search",
                                 params={"q": f"测试{i}"})
            pipeline.run(ctx)
            assert len(ctx.errors) == 0


# ════════════════════════════════════════════════════════════════
# 7. 快速运行 API (3)
# ════════════════════════════════════════════════════════════════

class TestQuickRun:
    """快速运行 API 测试"""

    def test_run_quick_health(self, pipeline):
        """健康检查快速运行"""
        response = pipeline.run_quick("GET", "/api/health")
        assert "output" in response

    def test_run_quick_with_body(self, pipeline):
        """带 body 的快速运行"""
        response = pipeline.run_quick("POST", "/api/bazi/calc",
                                      params={}, body={"year": 1990})
        assert "output" in response

    def test_run_quick_returns_dict(self, pipeline):
        """快速运行返回 dict"""
        response = pipeline.run_quick("GET", "/api/graph/search", {"q": "道"})
        assert isinstance(response, dict)
        assert "output" in response
        assert "confidence" in response
        assert "uncertainty" in response


# ════════════════════════════════════════════════════════════════
# 8. 覆盖度验证 (2)
# ════════════════════════════════════════════════════════════════

def test_all_stages_covered(pipeline):
    """验证所有 12 个阶段都被执行"""
    ctx = PipelineContext(method="GET", path="/api/graph/search", params={"q": "五行"})
    pipeline.run(ctx)
    executed = set(ctx.stage_results.keys()) | set(ctx.skipped_stages)
    expected = {s.value for s in PIPELINE_ORDER}
    assert executed == expected, f"未覆盖的阶段: {expected - executed}"


def test_stage_count():
    """验证管道阶段数量"""
    assert len(PIPELINE_ORDER) == 12
    stage_names = {s.value for s in PIPELINE_ORDER}
    expected_names = {
        "正官_法度", "元辰_路由", "正财_知识", "偏财_搜索",
        "食神_生成", "伤官_创新", "七杀_裁决", "太极_调和",
        "正印_配置", "劫财_安全", "偏印_适配", "比肩_协同",
    }
    assert stage_names == expected_names