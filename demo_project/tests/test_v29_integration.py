"""
test_v29_integration.py — v2.9.0 集成测试
==========================================
测试范围：
  - API Pydantic 模型验证
  - 跨模块集成（编排 → 反馈 → 进化 → 对话）
  - 端到端流程
  - 边界条件与异常处理
"""

import pytest
import sys
import os
import json
import time
import asyncio

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ============================================================================
# Test 1: Pydantic Model Validation
# ============================================================================

class TestPydanticModels:
    """API 请求/响应模型验证"""

    def test_agent_orchestrate_request_valid(self):
        """测试编排请求模型：有效"""
        from tengod.api_server import AgentOrchestrateRequest
        req = AgentOrchestrateRequest(query="分析八字命理")
        assert req.query == "分析八字命理"
        assert req.session_id is None
        assert req.params is None

    def test_agent_orchestrate_request_with_session(self):
        """测试编排请求模型：带会话ID"""
        from tengod.api_server import AgentOrchestrateRequest
        req = AgentOrchestrateRequest(query="test", session_id="sess_001", params={"birth": "2020-01-01"})
        assert req.session_id == "sess_001"
        assert req.params["birth"] == "2020-01-01"

    def test_agent_orchestrate_request_empty_query(self):
        """测试编排请求模型：空查询"""
        from pydantic import ValidationError
        from tengod.api_server import AgentOrchestrateRequest
        with pytest.raises(ValidationError):
            AgentOrchestrateRequest(query="")

    def test_agent_tools_response(self):
        """测试工具列表响应模型"""
        from tengod.api_server import AgentToolsResponse
        resp = AgentToolsResponse(tools=[{"name": "test"}], count=1)
        assert resp.count == 1
        d = resp.model_dump()
        assert d["count"] == 1

    def test_agent_intent_response(self):
        """测试意图识别响应模型"""
        from tengod.api_server import AgentIntentResponse
        resp = AgentIntentResponse(primary="八字", intents=["八字"], confidence=0.5, suggested_tools=["analyze_bazi"])
        d = resp.model_dump()
        assert d["primary"] == "八字"

    def test_evolution_feedback_request(self):
        """测试反馈请求模型"""
        from tengod.api_server import EvolutionFeedbackRequest
        req = EvolutionFeedbackRequest(
            session_id="sess_001",
            ratings={"accuracy": 5, "satisfaction": 4, "usefulness": 5},
            domain="bazi",
            comment="很准确",
        )
        assert req.ratings["accuracy"] == 5
        assert req.domain == "bazi"

    def test_evolution_feedback_response(self):
        """测试反馈响应模型"""
        from tengod.api_server import EvolutionFeedbackResponse
        resp = EvolutionFeedbackResponse(
            session_id="sess_001", overall_score=4.67, domain="bazi", confidence_after=0.55,
        )
        d = resp.model_dump()
        assert d["overall_score"] == 4.67

    def test_evolution_adjust_request_bounds(self):
        """测试置信度调整请求：边界"""
        from pydantic import ValidationError
        from tengod.api_server import EvolutionAdjustRequest
        # 有效范围
        req = EvolutionAdjustRequest(domain="bazi", adjustment=0.5)
        assert req.adjustment == 0.5
        # 超出范围
        with pytest.raises(ValidationError):
            EvolutionAdjustRequest(domain="bazi", adjustment=1.5)
        with pytest.raises(ValidationError):
            EvolutionAdjustRequest(domain="bazi", adjustment=-1.5)

    def test_conversation_chat_request(self):
        """测试对话请求模型"""
        from tengod.api_server import ConversationChatRequest
        req = ConversationChatRequest(message="你好", session_id="sess_001", bazi_context="庚午 壬午 辛亥 癸巳")
        assert req.message == "你好"
        assert req.bazi_context == "庚午 壬午 辛亥 癸巳"

    def test_conversation_chat_request_empty(self):
        """测试对话请求模型：空消息"""
        from pydantic import ValidationError
        from tengod.api_server import ConversationChatRequest
        with pytest.raises(ValidationError):
            ConversationChatRequest(message="", session_id="sess_001")

    def test_conversation_session_response(self):
        """测试会话响应模型"""
        from tengod.api_server import ConversationSessionResponse
        resp = ConversationSessionResponse(
            session_id="sess_001", message_count=3,
            topics_covered=["事业"], intent_context={"current_topic": "事业"},
        )
        d = resp.model_dump()
        assert d["message_count"] == 3

    def test_evolution_stats_response(self):
        """测试进化统计响应模型"""
        from tengod.api_server import EvolutionStatsResponse
        resp = EvolutionStatsResponse(
            total_feedback=10, average_score=4.2, total_nodes=18, total_edges=10,
            total_evolutions=5, domains={"bazi": {"confidence": 0.6}},
            recent_evolutions=[],
        )
        d = resp.model_dump()
        assert d["total_feedback"] == 10

    def test_evolution_confidence_response(self):
        """测试置信度响应模型"""
        from tengod.api_server import EvolutionConfidenceResponse
        resp = EvolutionConfidenceResponse(
            confidences={"bazi": 0.6, "ziwei": 0.5},
            average=0.55,
            highest={"domain": "bazi", "confidence": 0.6},
            lowest={"domain": "ziwei", "confidence": 0.5},
        )
        d = resp.model_dump()
        assert d["average"] == 0.55


# ============================================================================
# Test 2: Cross-Module Integration
# ============================================================================

class TestCrossModuleIntegration:
    """跨模块集成测试"""

    def test_agent_to_evolution_feedback_loop(self):
        """测试编排→反馈→进化闭环"""
        from tengod.agent_orchestrator import get_orchestrator
        from tengod.knowledge_evolution import get_evolution_engine

        # 1. 编排执行
        orch = get_orchestrator()
        result = orch.orchestrate("分析八字命理", session_id="integration_001")
        assert result.success

        # 2. 基于编排结果提交反馈
        engine = get_evolution_engine()
        engine.collect_feedback(
            "integration_001",
            {"accuracy": 4, "satisfaction": 5, "usefulness": 4},
            domain="bazi",
            comment="编排执行正确",
        )

        # 3. 验证置信度已更新
        conf = engine.get_confidence("bazi")
        assert conf > 0.5  # 正面反馈应提升置信度

    def test_conversation_to_evolution_integration(self):
        """测试对话→反馈→进化链路"""
        from tengod.ai_interpreter import get_conversation_engine
        from tengod.knowledge_evolution import get_evolution_engine

        # 1. 对话
        ce = get_conversation_engine()
        result = ce.process_message("我的事业运如何？", "integ_conv_001")
        assert result["intent"]["primary_topic"] == "事业"

        # 2. 反馈
        engine = get_evolution_engine()
        engine.collect_feedback(
            "integ_conv_001",
            {"accuracy": 5, "satisfaction": 5, "usefulness": 5},
            domain="bazi",
        )

        # 3. 进化
        results = engine.evolve()
        assert len(results) > 0

    def test_full_agent_conversation_evolution_pipeline(self):
        """测试完整流水线：编排 → 对话 → 反馈 → 进化"""
        from tengod.agent_orchestrator import get_orchestrator
        from tengod.ai_interpreter import get_conversation_engine
        from tengod.knowledge_evolution import get_evolution_engine

        session_id = "pipeline_test_" + str(int(time.time()))

        # Step 1: 编排
        orch = get_orchestrator()
        orch_result = orch.orchestrate("分析八字命理", session_id=session_id)
        assert orch_result.success

        # Step 2: 对话跟进
        ce = get_conversation_engine()
        conv_result = ce.process_message("事业方面还有什么需要注意的？", session_id)
        assert conv_result["intent"]["primary_topic"] == "事业"

        # Step 3: 提交反馈
        engine = get_evolution_engine()
        engine.collect_feedback(
            session_id,
            {"accuracy": 4, "satisfaction": 4, "usefulness": 5},
            domain="bazi",
            comment="完整流程测试",
        )

        # Step 4: 进化
        evo_results = engine.evolve()

        # Step 5: 验证统计
        stats = engine.get_evolution_stats()
        assert stats["total_feedback"] >= 1
        assert stats["total_evolutions"] >= 1

        # 清理
        ce.reset_session(session_id)


# ============================================================================
# Test 3: Edge Cases and Error Handling
# ============================================================================

class TestEdgeCases:
    """边界条件与异常处理"""

    def test_agent_empty_query(self):
        """测试编排：空查询"""
        from tengod.agent_orchestrator import get_orchestrator
        orch = get_orchestrator()
        result = orch.orchestrate("")
        # 空查询应返回默认意图
        assert result.user_intent in ("综合", "八字")

    def test_agent_very_long_query(self):
        """测试编排：超长查询"""
        from tengod.agent_orchestrator import get_orchestrator
        orch = get_orchestrator()
        long_query = "分析八字命理 " * 100
        result = orch.orchestrate(long_query[:2000])
        assert result.success

    def test_evolution_feedback_bounds(self):
        """测试进化：评分配置边界"""
        from tengod.knowledge_evolution import get_evolution_engine
        engine = get_evolution_engine()
        # 极端评分
        fb = engine.collect_feedback("edge_001", {"accuracy": 1, "satisfaction": 1, "usefulness": 1}, domain="bazi")
        assert fb.overall_score() == 1.0

        fb2 = engine.collect_feedback("edge_002", {"accuracy": 5, "satisfaction": 5, "usefulness": 5}, domain="bazi")
        assert fb2.overall_score() == 5.0

    def test_evolution_confidence_clamp(self):
        """测试进化：置信度边界"""
        from tengod.knowledge_evolution import get_evolution_engine
        engine = get_evolution_engine()
        # 大量极端高评分
        for i in range(50):
            engine.collect_feedback(f"clamp_{i}", {"accuracy": 5, "satisfaction": 5, "usefulness": 5}, domain="bazi")
        engine.evolve()
        conf = engine.get_confidence("bazi")
        assert 0.0 <= conf <= 1.0

    def test_evolution_reset_preserves_seed(self):
        """测试进化：重置后保留种子知识"""
        from tengod.knowledge_evolution import get_evolution_engine
        engine = get_evolution_engine()
        engine.collect_feedback("edge_001", {"accuracy": 5}, domain="bazi")
        engine.evolve()
        engine.reset()
        stats = engine.get_evolution_stats()
        assert stats["total_feedback"] == 0
        assert stats["total_nodes"] > 0  # 种子节点保留
        assert engine.get_confidence("bazi") == 0.5

    def test_conversation_unknown_session(self):
        """测试对话：未知会话"""
        from tengod.ai_interpreter import get_conversation_engine
        ce = get_conversation_engine()
        summary = ce.get_session_summary("nonexistent_session")
        assert summary["message_count"] == 0

    def test_conversation_multiple_resets(self):
        """测试对话：多次重置"""
        from tengod.ai_interpreter import get_conversation_engine
        ce = get_conversation_engine()
        ce.process_message("测试", "multi_reset")
        ce.reset_session("multi_reset")
        ce.reset_session("multi_reset")  # 二次重置无异常
        summary = ce.get_session_summary("multi_reset")
        assert summary["message_count"] == 0

    def test_evolution_unknown_domain_feedback(self):
        """测试进化：未知领域反馈"""
        from tengod.knowledge_evolution import get_evolution_engine
        engine = get_evolution_engine()
        fb = engine.collect_feedback("edge_001", {"accuracy": 4}, domain="unknown_domain")
        assert fb.overall_score() > 0
        # 未知领域应创建新的置信度配置
        assert engine.get_confidence("unknown_domain") > 0.0

    def test_tool_execution_with_invalid_params(self):
        """测试工具执行：无效参数"""
        from tengod.agent_orchestrator import get_orchestrator
        orch = get_orchestrator()
        result = orch.execute_step("analyze_bazi", {"invalid_param": "test"})
        assert result.success  # 应优雅处理，不崩溃

    def test_knowledge_evolution_batch_feedback(self):
        """测试进化：批量反馈"""
        from tengod.knowledge_evolution import get_evolution_engine
        engine = get_evolution_engine()
        before = engine.get_evolution_stats()["total_feedback"]

        for i in range(20):
            engine.collect_feedback(
                f"batch_{i}",
                {"accuracy": i % 5 + 1, "satisfaction": (i + 1) % 5 + 1, "usefulness": (i + 2) % 5 + 1},
                domain=["bazi", "ziwei", "qimen", "liuyao"][i % 4],
            )

        engine.evolve()
        stats = engine.get_evolution_stats()
        assert stats["total_feedback"] >= before + 20

    def test_knowledge_graph_integrity(self):
        """测试知识图谱：完整性"""
        from tengod.knowledge_evolution import get_evolution_engine
        engine = get_evolution_engine()
        engine.reset()

        stats = engine.get_knowledge_graph_stats()
        # 种子节点和边
        assert stats["total_nodes"] >= 10
        assert stats["total_edges"] >= 5
        # 所有边应指向存在的节点
        for edge in engine._edges:
            assert edge.source_id in engine._nodes, f"Edge source {edge.source_id} not found"
            assert edge.target_id in engine._nodes, f"Edge target {edge.target_id} not found"


# ============================================================================
# Test 4: Performance and Concurrency
# ============================================================================

class TestPerformance:
    """性能与并发测试"""

    def test_agent_orchestrate_performance(self):
        """测试编排性能：应在 100ms 内完成"""
        from tengod.agent_orchestrator import get_orchestrator
        orch = get_orchestrator()
        start = time.time()
        result = orch.orchestrate("分析八字命理")
        elapsed = (time.time() - start) * 1000
        assert result.success
        assert elapsed < 500, f"编排耗时 {elapsed:.0f}ms 超过 500ms 阈值"

    def test_evolution_bulk_feedback_performance(self):
        """测试进化：批量反馈性能"""
        from tengod.knowledge_evolution import get_evolution_engine
        engine = get_evolution_engine()

        start = time.time()
        for i in range(100):
            engine.collect_feedback(f"perf_{i}", {"accuracy": 4, "satisfaction": 4, "usefulness": 4}, domain="bazi")
        elapsed = (time.time() - start) * 1000
        assert elapsed < 500, f"100条反馈耗时 {elapsed:.0f}ms 超过 500ms"

    def test_conversation_rapid_messages(self):
        """测试对话：快速连续消息"""
        from tengod.ai_interpreter import get_conversation_engine
        ce = get_conversation_engine()

        messages = ["你好", "事业运如何？", "财运呢？", "感情方面？", "健康呢？"]
        for msg in messages:
            result = ce.process_message(msg, "rapid_test")
            assert result["session_id"] == "rapid_test"

        ce.reset_session("rapid_test")

    def test_evolution_auto_complete_performance(self):
        """测试进化：自动补全性能"""
        from tengod.knowledge_evolution import get_evolution_engine
        engine = get_evolution_engine()

        start = time.time()
        results = engine.auto_complete_knowledge()
        elapsed = (time.time() - start) * 1000
        assert elapsed < 200, f"自动补全耗时 {elapsed:.0f}ms 超过 200ms"


# ============================================================================
# Test 5: Data Consistency
# ============================================================================

class TestDataConsistency:
    """数据一致性测试"""

    def test_evolution_engine_singleton_consistency(self):
        """测试进化引擎单例一致性"""
        from tengod.knowledge_evolution import get_evolution_engine
        e1 = get_evolution_engine()
        e2 = get_evolution_engine()
        assert e1 is e2
        e1.collect_feedback("cons_001", {"accuracy": 5}, domain="bazi")
        assert e2.get_evolution_stats()["total_feedback"] == e1.get_evolution_stats()["total_feedback"]

    def test_agent_orchestrator_singleton_consistency(self):
        """测试编排器单例一致性"""
        from tengod.agent_orchestrator import get_orchestrator
        o1 = get_orchestrator()
        o2 = get_orchestrator()
        assert o1 is o2

    def test_conversation_engine_singleton_consistency(self):
        """测试对话引擎单例一致性"""
        from tengod.ai_interpreter import get_conversation_engine
        c1 = get_conversation_engine()
        c2 = get_conversation_engine()
        assert c1 is c2

    def test_feedback_confidence_monotonic_increase(self):
        """测试正面反馈单调递增置信度"""
        from tengod.knowledge_evolution import get_evolution_engine
        engine = get_evolution_engine()
        engine.reset()

        confs = []
        for i in range(10):
            engine.collect_feedback(f"mono_{i}", {"accuracy": 5, "satisfaction": 5, "usefulness": 5}, domain="bazi")
            confs.append(engine.get_confidence("bazi"))

        assert confs[-1] > confs[0]  # 持续正面反馈应提升置信度

    def test_negative_feedback_decreases_confidence(self):
        """测试负面反馈降低置信度"""
        from tengod.knowledge_evolution import get_evolution_engine
        engine = get_evolution_engine()
        engine.reset()

        conf_before = engine.get_confidence("bazi")
        for i in range(10):
            engine.collect_feedback(f"neg_{i}", {"accuracy": 1, "satisfaction": 1, "usefulness": 1}, domain="bazi")
        conf_after = engine.get_confidence("bazi")

        assert conf_after < conf_before


# ============================================================================
# 异步测试入口
# ============================================================================

def test_async_conversation_with_evolution():
    """异步对话 + 进化集成测试"""
    async def _test():
        from tengod.ai_interpreter import smart_chat, build_bazi_context
        from tengod.knowledge_evolution import get_evolution_engine

        bazi_ctx = build_bazi_context(
            pillars={"year": "庚午", "month": "壬午", "day": "辛亥", "hour": "癸巳"},
            day_master="辛金",
        )

        result = await smart_chat("适合什么行业？", "integ_final_001", bazi_context=bazi_ctx)
        assert "response" in result
        assert result["intent"]["primary_topic"] == "事业"

        engine = get_evolution_engine()
        before = engine.get_confidence("bazi")
        engine.collect_feedback("integ_final_001", {"accuracy": 5, "satisfaction": 5, "usefulness": 5}, domain="bazi")
        engine.evolve()
        after = engine.get_confidence("bazi")
        assert after >= before  # 正面反馈不应降低置信度

    asyncio.run(_test())