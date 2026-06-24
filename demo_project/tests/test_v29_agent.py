"""
test_v29_agent.py — v2.9.0 新增功能测试
==========================================
测试范围：
  - 智能体编排引擎 (agent_orchestrator)
  - 知识进化系统 (knowledge_evolution)
  - 智能对话引擎 (ai_interpreter v2.9: IntentTracker/ProactiveAdvisor/ConversationEngine)
  - 向后兼容性
"""

import pytest
import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ============================================================================
# Test 1: Agent Orchestrator
# ============================================================================

class TestAgentOrchestrator:
    """智能体编排引擎测试"""

    def test_tool_creation(self):
        """测试工具创建"""
        from tengod.agent_orchestrator import Tool
        tool = Tool("test", "测试工具", lambda x: x, {"type": "object"}, "test")
        assert tool.name == "test"
        assert tool.category == "test"
        spec = tool.to_openai_spec()
        assert spec["type"] == "function"
        assert spec["function"]["name"] == "test"

    def test_standard_tools_count(self):
        """测试标准工具集数量"""
        from tengod.agent_orchestrator import STANDARD_TOOLS
        assert len(STANDARD_TOOLS) == 8

    def test_standard_tools_categories(self):
        """测试标准工具分类"""
        from tengod.agent_orchestrator import STANDARD_TOOLS
        categories = {t.category for t in STANDARD_TOOLS}
        assert "divination" in categories
        assert "analysis" in categories
        assert "report" in categories

    def test_standard_tools_execution(self):
        """测试标准工具执行"""
        from tengod.agent_orchestrator import STANDARD_TOOLS
        for tool in STANDARD_TOOLS:
            result = tool.func({"test": True})
            assert result["tool"] == tool.name
            assert "result" in result

    def test_orchestrator_init(self):
        """测试编排器初始化"""
        from tengod.agent_orchestrator import AgentOrchestrator
        orch = AgentOrchestrator()
        assert len(orch.tools) == 8
        assert orch._max_steps == 10

    def test_orchestrator_custom_tools(self):
        """测试自定义工具"""
        from tengod.agent_orchestrator import AgentOrchestrator, Tool
        custom = [Tool("custom", "custom", lambda x: {"result": "ok"})]
        orch = AgentOrchestrator(tools=custom, max_steps=5)
        assert len(orch.tools) == 1
        assert orch._max_steps == 5

    def test_orchestrator_get_tool_specs(self):
        """测试获取工具规格"""
        from tengod.agent_orchestrator import AgentOrchestrator
        orch = AgentOrchestrator()
        specs = orch.get_tool_specs()
        assert len(specs) == 8
        assert all("type" in s for s in specs)

    def test_orchestrator_get_tool_descriptions(self):
        """测试获取工具描述"""
        from tengod.agent_orchestrator import AgentOrchestrator
        orch = AgentOrchestrator()
        desc = orch.get_tool_descriptions()
        assert "可用工具" in desc
        assert "analyze_bazi" in desc

    def test_detect_intent_bazi(self):
        """测试意图识别：八字"""
        from tengod.agent_orchestrator import AgentOrchestrator
        orch = AgentOrchestrator()
        result = orch.detect_intent("帮我分析八字命理")
        assert result["primary"] == "八字"
        assert result["confidence"] >= 0.25

    def test_detect_intent_ziwei(self):
        """测试意图识别：紫微"""
        from tengod.agent_orchestrator import AgentOrchestrator
        orch = AgentOrchestrator()
        result = orch.detect_intent("紫微斗数命盘分析")
        assert result["primary"] == "紫微"
        assert "紫微" in result["intents"]

    def test_detect_intent_qimen(self):
        """测试意图识别：奇门"""
        from tengod.agent_orchestrator import AgentOrchestrator
        orch = AgentOrchestrator()
        result = orch.detect_intent("奇门遁甲时空盘")
        assert result["primary"] == "奇门"

    def test_detect_intent_liuyao(self):
        """测试意图识别：六爻"""
        from tengod.agent_orchestrator import AgentOrchestrator
        orch = AgentOrchestrator()
        result = orch.detect_intent("帮我起卦占卜")
        assert result["primary"] == "六爻"

    def test_detect_intent_fengshui(self):
        """测试意图识别：风水"""
        from tengod.agent_orchestrator import AgentOrchestrator
        orch = AgentOrchestrator()
        result = orch.detect_intent("风水玄空飞星评估")
        assert result["primary"] == "风水"

    def test_detect_intent_fusion(self):
        """测试意图识别：融合"""
        from tengod.agent_orchestrator import AgentOrchestrator
        orch = AgentOrchestrator()
        result = orch.detect_intent("综合全面分析")
        assert result["primary"] == "融合"

    def test_detect_intent_default(self):
        """测试意图识别：默认"""
        from tengod.agent_orchestrator import AgentOrchestrator
        orch = AgentOrchestrator()
        result = orch.detect_intent("你好")
        assert result["primary"] == "综合"
        assert result["confidence"] == 0.0

    def test_plan_actions(self):
        """测试计划生成"""
        from tengod.agent_orchestrator import AgentOrchestrator
        orch = AgentOrchestrator()
        plan = orch.plan_actions("测试", {"primary": "八字"})
        assert plan == ["analyze_bazi", "generate_report"]

    def test_plan_actions_fusion(self):
        """测试计划生成：融合"""
        from tengod.agent_orchestrator import AgentOrchestrator
        orch = AgentOrchestrator()
        plan = orch.plan_actions("测试", {"primary": "融合"})
        assert len(plan) == 4
        assert "fusion_analyze" in plan

    def test_execute_step(self):
        """测试单步执行"""
        from tengod.agent_orchestrator import AgentOrchestrator
        orch = AgentOrchestrator()
        result = orch.execute_step("analyze_bazi", {"birth_date": "2020-01-01"})
        assert result.success
        assert result.tool_name == "analyze_bazi"
        assert result.output["tool"] == "analyze_bazi"

    def test_execute_step_unknown_tool(self):
        """测试执行未知工具"""
        from tengod.agent_orchestrator import AgentOrchestrator
        orch = AgentOrchestrator()
        result = orch.execute_step("unknown_tool", {})
        assert not result.success
        assert "不存在" in result.error

    def test_execute_plan(self):
        """测试执行完整计划"""
        from tengod.agent_orchestrator import AgentOrchestrator
        orch = AgentOrchestrator()
        plan = ["analyze_bazi", "generate_report"]
        results = orch.execute_plan(plan)
        assert len(results) == 2
        assert all(r.success for r in results)

    def test_execute_plan_with_params(self):
        """测试执行计划（带参数）"""
        from tengod.agent_orchestrator import AgentOrchestrator
        orch = AgentOrchestrator()
        results = orch.execute_plan(["analyze_bazi"], {"birth_date": "2020-01-01"})
        assert results[0].input_params == {"birth_date": "2020-01-01"}

    def test_orchestrate(self):
        """测试完整编排"""
        from tengod.agent_orchestrator import AgentOrchestrator
        orch = AgentOrchestrator()
        result = orch.orchestrate("分析八字命理", session_id="test_001")
        assert result.session_id == "test_001"
        assert result.user_intent == "八字"
        assert len(result.plan) == 2
        assert len(result.steps) == 2
        assert result.tool_calls_count == 2
        assert result.success
        assert result.total_duration_ms > 0

    def test_orchestrate_result_to_dict(self):
        """测试编排结果序列化"""
        from tengod.agent_orchestrator import AgentOrchestrator
        orch = AgentOrchestrator()
        result = orch.orchestrate("分析八字命理")
        d = result.to_dict()
        assert "session_id" in d
        assert "user_intent" in d
        assert "plan" in d
        assert "steps" in d

    def test_quick_orchestrate(self):
        """测试快速编排"""
        from tengod.agent_orchestrator import quick_orchestrate
        result = quick_orchestrate("分析八字命理")
        assert result.success
        assert result.user_intent == "八字"

    def test_get_orchestrator_singleton(self):
        """测试编排器单例"""
        from tengod.agent_orchestrator import get_orchestrator
        o1 = get_orchestrator()
        o2 = get_orchestrator()
        assert o1 is o2

    def test_step_result_to_dict(self):
        """测试步骤结果序列化"""
        from tengod.agent_orchestrator import StepResult
        sr = StepResult(step=1, tool_name="test", output={"a": 1})
        d = sr.to_dict()
        assert d["step"] == 1
        assert d["tool_name"] == "test"


# ============================================================================
# Test 2: Knowledge Evolution
# ============================================================================

class TestKnowledgeEvolution:
    """知识进化系统测试"""

    def test_init(self):
        """测试初始化"""
        from tengod.knowledge_evolution import KnowledgeEvolution
        ke = KnowledgeEvolution()
        assert len(ke._nodes) > 0
        assert len(ke._edges) > 0
        assert len(ke._confidence_profiles) == 9

    def test_collect_feedback(self):
        """测试反馈收集"""
        from tengod.knowledge_evolution import KnowledgeEvolution
        ke = KnowledgeEvolution()
        fb = ke.collect_feedback("sess_001", {"accuracy": 5, "satisfaction": 4, "usefulness": 5}, domain="bazi")
        assert fb.session_id == "sess_001"
        assert fb.accuracy == 5
        assert fb.overall_score() == pytest.approx(4.67, 0.1)
        assert len(ke._feedbacks) == 1

    def test_feedback_updates_confidence(self):
        """测试反馈更新置信度"""
        from tengod.knowledge_evolution import KnowledgeEvolution
        ke = KnowledgeEvolution()
        old_conf = ke.get_confidence("bazi")
        ke.collect_feedback("sess_001", {"accuracy": 5, "satisfaction": 5, "usefulness": 5}, domain="bazi")
        new_conf = ke.get_confidence("bazi")
        assert new_conf > old_conf  # 高评分应提升置信度

    def test_feedback_negative_confidence(self):
        """测试负面反馈降低置信度"""
        from tengod.knowledge_evolution import KnowledgeEvolution
        ke = KnowledgeEvolution()
        old_conf = ke.get_confidence("bazi")
        ke.collect_feedback("sess_001", {"accuracy": 1, "satisfaction": 1, "usefulness": 1}, domain="bazi")
        new_conf = ke.get_confidence("bazi")
        assert new_conf < old_conf

    def test_feedback_tag_extraction(self):
        """测试反馈标签提取"""
        from tengod.knowledge_evolution import KnowledgeEvolution
        ke = KnowledgeEvolution()
        fb = ke.collect_feedback("sess_001", {"accuracy": 5}, comment="非常准确，很有帮助")
        assert "accurate" in fb.tags
        assert "useful" in fb.tags

    def test_feedback_with_corrections(self):
        """测试带纠正的反馈"""
        from tengod.knowledge_evolution import KnowledgeEvolution
        ke = KnowledgeEvolution()
        fb = ke.collect_feedback("sess_001", {"accuracy": 3},
                                 corrections=[{"field": "yongshen", "correct": "金"}])
        assert len(fb.corrections) == 1

    def test_adjust_confidence_manual(self):
        """测试手动置信度调整"""
        from tengod.knowledge_evolution import KnowledgeEvolution
        ke = KnowledgeEvolution()
        profile = ke.adjust_confidence("bazi", 0.1, "测试调整")
        assert profile.current_confidence == 0.6
        assert len(profile.adjustments) == 1

    def test_adjust_confidence_clamp(self):
        """测试置信度边界"""
        from tengod.knowledge_evolution import KnowledgeEvolution
        ke = KnowledgeEvolution()
        profile = ke.adjust_confidence("bazi", 2.0)  # 超出上限
        assert profile.current_confidence == 1.0
        profile = ke.adjust_confidence("bazi", -2.0)  # 超出下限
        assert profile.current_confidence == 0.0

    def test_get_all_confidences(self):
        """测试获取所有置信度"""
        from tengod.knowledge_evolution import KnowledgeEvolution
        ke = KnowledgeEvolution()
        confs = ke.get_all_confidences()
        assert len(confs) == 9
        assert "bazi" in confs
        assert all(0.0 <= v <= 1.0 for v in confs.values())

    def test_add_node(self):
        """测试添加知识节点"""
        from tengod.knowledge_evolution import KnowledgeEvolution
        ke = KnowledgeEvolution()
        node = ke.add_node("test_node", "bazi", "测试概念", confidence=0.7)
        assert node.id == "test_node"
        assert node.domain == "bazi"
        assert node.confidence == 0.7
        assert ke.get_node("test_node") is not None

    def test_add_edge(self):
        """测试添加知识边"""
        from tengod.knowledge_evolution import KnowledgeEvolution
        ke = KnowledgeEvolution()
        edge = ke.add_edge("bazi_gan", "bazi_zhi", "correlates", weight=0.8)
        assert edge is not None
        assert edge.relation == "correlates"
        assert edge.weight == 0.8

    def test_add_edge_invalid(self):
        """测试添加无效边"""
        from tengod.knowledge_evolution import KnowledgeEvolution
        ke = KnowledgeEvolution()
        edge = ke.add_edge("nonexistent1", "nonexistent2", "correlates")
        assert edge is None

    def test_get_neighbors(self):
        """测试获取邻居节点"""
        from tengod.knowledge_evolution import KnowledgeEvolution
        ke = KnowledgeEvolution()
        neighbors = ke.get_neighbors("bazi_wuxing")
        assert len(neighbors) > 0

    def test_auto_complete_knowledge(self):
        """测试知识图谱自动补全"""
        from tengod.knowledge_evolution import KnowledgeEvolution
        ke = KnowledgeEvolution()
        initial_edges = len(ke._edges)
        results = ke.auto_complete_knowledge()
        assert len(ke._edges) > initial_edges  # 应有新边产生
        assert len(results) > 0

    def test_evolve(self):
        """测试知识进化主循环"""
        from tengod.knowledge_evolution import KnowledgeEvolution
        ke = KnowledgeEvolution()
        ke.collect_feedback("sess_001", {"accuracy": 5, "satisfaction": 5, "usefulness": 5}, domain="bazi")
        ke.collect_feedback("sess_002", {"accuracy": 4, "satisfaction": 4, "usefulness": 4}, domain="bazi")
        results = ke.evolve()
        assert len(results) > 0

    def test_get_evolution_stats(self):
        """测试进化统计"""
        from tengod.knowledge_evolution import KnowledgeEvolution
        ke = KnowledgeEvolution()
        stats = ke.get_evolution_stats()
        assert "total_feedback" in stats
        assert "total_nodes" in stats
        assert "total_edges" in stats
        assert "domains" in stats
        assert "bazi" in stats["domains"]

    def test_get_feedback_trend(self):
        """测试反馈趋势"""
        from tengod.knowledge_evolution import KnowledgeEvolution
        ke = KnowledgeEvolution()
        ke.collect_feedback("sess_001", {"accuracy": 5, "satisfaction": 5, "usefulness": 5}, domain="bazi")
        trend = ke.get_feedback_trend()
        assert len(trend) == 1
        assert trend[0]["domain"] == "bazi"

    def test_get_knowledge_graph_stats(self):
        """测试知识图谱统计"""
        from tengod.knowledge_evolution import KnowledgeEvolution
        ke = KnowledgeEvolution()
        stats = ke.get_knowledge_graph_stats()
        assert "total_nodes" in stats
        assert "total_edges" in stats
        assert "nodes_by_domain" in stats
        assert "edges_by_relation" in stats

    def test_reset(self):
        """测试重置"""
        from tengod.knowledge_evolution import KnowledgeEvolution
        ke = KnowledgeEvolution()
        ke.collect_feedback("sess_001", {"accuracy": 5}, domain="bazi")
        ke.reset()
        assert len(ke._feedbacks) == 0
        assert ke.get_confidence("bazi") == 0.5

    def test_quick_feedback(self):
        """测试快速反馈"""
        from tengod.knowledge_evolution import quick_feedback
        fb = quick_feedback("sess_quick", {"accuracy": 5, "satisfaction": 4, "usefulness": 5})
        assert fb.session_id == "sess_quick"
        assert fb.overall_score() > 3

    def test_quick_evolve(self):
        """测试快速进化"""
        from tengod.knowledge_evolution import quick_evolve, quick_feedback
        quick_feedback("sess_001", {"accuracy": 5, "satisfaction": 5, "usefulness": 5})
        results = quick_evolve()
        assert isinstance(results, list)

    def test_feedback_record_to_dict(self):
        """测试反馈记录序列化"""
        from tengod.knowledge_evolution import FeedbackRecord
        fb = FeedbackRecord(session_id="test", accuracy=4, satisfaction=5, usefulness=4)
        d = fb.to_dict()
        assert d["session_id"] == "test"
        assert d["accuracy"] == 4

    def test_confidence_profile_to_dict(self):
        """测试置信度配置序列化"""
        from tengod.knowledge_evolution import ConfidenceProfile
        cp = ConfidenceProfile(domain="bazi", current_confidence=0.8)
        d = cp.to_dict()
        assert d["domain"] == "bazi"
        assert d["current_confidence"] == 0.8

    def test_evolution_result_to_dict(self):
        """测试进化结果序列化"""
        from tengod.knowledge_evolution import EvolutionResult
        er = EvolutionResult(domain="bazi", action="adjusted",
                             before_confidence=0.5, after_confidence=0.7,
                             description="测试")
        d = er.to_dict()
        assert d["domain"] == "bazi"
        assert d["action"] == "adjusted"


# ============================================================================
# Test 3: Conversation Engine (v2.9)
# ============================================================================

class TestIntentTracker:
    """意图追踪器测试"""

    def test_init(self):
        """测试初始化"""
        from tengod.ai_interpreter import IntentTracker
        tracker = IntentTracker()
        ctx = tracker.get_context()
        assert ctx["topic_depth"] == 0
        assert ctx["state"] == "greeting"

    def test_detect_single_topic(self):
        """测试单话题检测"""
        from tengod.ai_interpreter import IntentTracker
        tracker = IntentTracker()
        result = tracker.track("我的事业运怎么样？")
        assert result["primary_topic"] == "事业"
        assert result["topic_changed"] is False

    def test_detect_topic_switch(self):
        """测试话题切换"""
        from tengod.ai_interpreter import IntentTracker
        tracker = IntentTracker()
        tracker.track("我的事业运怎么样？")
        result = tracker.track("那财运方面呢？")
        assert result["primary_topic"] == "财运"
        assert result["topic_changed"] is True

    def test_topic_depth_increment(self):
        """测试话题深度递增"""
        from tengod.ai_interpreter import IntentTracker
        tracker = IntentTracker()
        tracker.track("事业运怎么样？")
        r2 = tracker.track("事业方面还有什么？")
        r3 = tracker.track("详细说说事业")
        assert r2["topic_depth"] == 2
        assert r3["topic_depth"] == 3

    def test_topic_depth_reset_on_switch(self):
        """测试话题切换时深度重置"""
        from tengod.ai_interpreter import IntentTracker
        tracker = IntentTracker()
        tracker.track("事业运怎么样？")
        tracker.track("事业方面还有什么？")
        result = tracker.track("那财运呢？")
        assert result["topic_depth"] == 1  # 切换后重置

    def test_state_greeting(self):
        """测试状态：问候"""
        from tengod.ai_interpreter import IntentTracker
        tracker = IntentTracker()
        result = tracker.track("你好")
        assert result["state"] == "greeting"

    def test_state_exploring(self):
        """测试状态：探索"""
        from tengod.ai_interpreter import IntentTracker
        tracker = IntentTracker()
        result = tracker.track("我的事业运怎么样？")
        assert result["state"] in ("greeting", "exploring")

    def test_state_deep_analysis(self):
        """测试状态：深度分析"""
        from tengod.ai_interpreter import IntentTracker
        tracker = IntentTracker()
        tracker.track("事业")
        tracker.track("事业")
        tracker.track("事业")
        result = tracker.track("详细说说事业为什么这样")
        assert result["state"] == "deep_analysis"

    def test_state_summary(self):
        """测试状态：总结"""
        from tengod.ai_interpreter import IntentTracker
        tracker = IntentTracker()
        result = tracker.track("总结一下刚才的分析")
        assert result["state"] == "summary"

    def test_get_context(self):
        """测试获取上下文"""
        from tengod.ai_interpreter import IntentTracker
        tracker = IntentTracker()
        tracker.track("事业")
        tracker.track("事业")
        ctx = tracker.get_context()
        assert ctx["current_topic"] == "事业"
        assert ctx["topic_depth"] == 2
        assert ctx["total_turns"] == 2

    def test_reset(self):
        """测试重置"""
        from tengod.ai_interpreter import IntentTracker
        tracker = IntentTracker()
        tracker.track("事业")
        tracker.reset()
        ctx = tracker.get_context()
        assert ctx["topic_depth"] == 0
        assert ctx["total_turns"] == 0


class TestProactiveAdvisor:
    """主动建议生成器测试"""

    def test_generate_suggestions(self):
        """测试建议生成"""
        from tengod.ai_interpreter import ProactiveAdvisor
        advisor = ProactiveAdvisor()
        ctx = {"current_topic": "事业", "topic_depth": 1, "state": "follow_up"}
        suggestions = advisor.generate_suggestions(ctx)
        assert len(suggestions) > 0
        assert all("question" in s for s in suggestions)
        assert all("type" in s for s in suggestions)

    def test_no_duplicate_suggestions(self):
        """测试无重复建议"""
        from tengod.ai_interpreter import ProactiveAdvisor
        advisor = ProactiveAdvisor()
        ctx = {"current_topic": "事业", "topic_depth": 1, "state": "follow_up"}
        s1 = advisor.generate_suggestions(ctx)
        s2 = advisor.generate_suggestions(ctx)
        # 不应有重复
        q1 = {s["question"] for s in s1}
        q2 = {s["question"] for s in s2}
        assert len(q1 & q2) == 0

    def test_depth_trigger_suggestions(self):
        """测试深度触发建议"""
        from tengod.ai_interpreter import ProactiveAdvisor
        advisor = ProactiveAdvisor()
        ctx = {"current_topic": "事业", "topic_depth": 3, "state": "deep_analysis"}
        suggestions = advisor.generate_suggestions(ctx)
        types = {s["type"] for s in suggestions}
        assert "depth_trigger" in types

    def test_summary_suggestions(self):
        """测试总结状态建议"""
        from tengod.ai_interpreter import ProactiveAdvisor
        advisor = ProactiveAdvisor()
        ctx = {"current_topic": "事业", "topic_depth": 1, "state": "summary"}
        suggestions = advisor.generate_suggestions(ctx)
        types = {s["type"] for s in suggestions}
        assert "state_trigger" in types

    def test_max_suggestions(self):
        """测试最大建议数限制"""
        from tengod.ai_interpreter import ProactiveAdvisor
        advisor = ProactiveAdvisor()
        ctx = {"current_topic": "事业", "topic_depth": 1, "state": "follow_up"}
        suggestions = advisor.generate_suggestions(ctx, max_suggestions=1)
        assert len(suggestions) <= 1

    def test_reset(self):
        """测试重置"""
        from tengod.ai_interpreter import ProactiveAdvisor
        advisor = ProactiveAdvisor()
        ctx = {"current_topic": "事业", "topic_depth": 1, "state": "follow_up"}
        advisor.generate_suggestions(ctx)
        advisor.reset()
        # 重置后应能再次生成相同建议
        s2 = advisor.generate_suggestions(ctx)
        assert len(s2) > 0


class TestConversationEngine:
    """智能对话引擎测试"""

    def test_process_message(self):
        """测试消息处理"""
        from tengod.ai_interpreter import ConversationEngine
        engine = ConversationEngine()
        result = engine.process_message("我的事业运如何？", "sess_001")
        assert result["session_id"] == "sess_001"
        assert "intent" in result
        assert "suggestions" in result
        assert "conversation_state" in result
        assert "session_stats" in result

    def test_process_message_session_stats(self):
        """测试会话统计"""
        from tengod.ai_interpreter import ConversationEngine
        engine = ConversationEngine()
        engine.process_message("事业运如何？", "sess_001")
        result = engine.process_message("财运呢？", "sess_001")
        stats = result["session_stats"]
        assert stats["message_count"] == 2
        assert "事业" in stats["topics_covered"]
        assert "财运" in stats["topics_covered"]

    def test_get_session_summary(self):
        """测试会话摘要"""
        from tengod.ai_interpreter import ConversationEngine
        engine = ConversationEngine()
        engine.process_message("事业", "sess_001")
        summary = engine.get_session_summary("sess_001")
        assert summary["message_count"] == 1
        assert "topics_covered" in summary

    def test_reset_session(self):
        """测试重置会话"""
        from tengod.ai_interpreter import ConversationEngine
        engine = ConversationEngine()
        engine.process_message("事业", "sess_001")
        engine.reset_session("sess_001")
        summary = engine.get_session_summary("sess_001")
        assert summary["message_count"] == 0

    def test_chat(self):
        """测试自主对话"""
        import asyncio
        from tengod.ai_interpreter import ConversationEngine, build_bazi_context
        engine = ConversationEngine()
        bazi_ctx = build_bazi_context(
            pillars={"year": "庚午", "month": "壬午", "day": "辛亥", "hour": "癸巳"},
            day_master="辛金",
        )
        result = asyncio.run(engine.chat("我的事业运如何？", "sess_chat", bazi_context=bazi_ctx))
        assert "response" in result
        assert "intent" in result
        assert "suggestions" in result
        assert len(result["response"]) > 0

    def test_get_conversation_engine_singleton(self):
        """测试全局引擎单例"""
        from tengod.ai_interpreter import get_conversation_engine
        e1 = get_conversation_engine()
        e2 = get_conversation_engine()
        assert e1 is e2


# ============================================================================
# Test 4: Backward Compatibility
# ============================================================================

class TestBackwardCompatibility:
    """向后兼容性测试"""

    def test_agent_imports(self):
        """测试 agent_orchestrator 导入"""
        from tengod.agent_orchestrator import (
            AgentOrchestrator, Tool, StepResult, OrchestrationResult,
            STANDARD_TOOLS, get_orchestrator, quick_orchestrate,
        )
        assert AgentOrchestrator is not None

    def test_knowledge_evolution_imports(self):
        """测试 knowledge_evolution 导入"""
        from tengod.knowledge_evolution import (
            KnowledgeEvolution, FeedbackRecord, ConfidenceProfile,
            KnowledgeNode, KnowledgeEdge, EvolutionResult,
            get_evolution_engine, quick_feedback, quick_evolve,
            KNOWLEDGE_DOMAINS,
        )
        assert KnowledgeEvolution is not None
        assert len(KNOWLEDGE_DOMAINS) == 9

    def test_conversation_imports(self):
        """测试对话引擎导入"""
        from tengod.ai_interpreter import (
            IntentTracker, ProactiveAdvisor, ConversationEngine,
            get_conversation_engine, smart_chat,
        )
        assert IntentTracker is not None

    def test_existing_api_unchanged(self):
        """测试现有 API 不变"""
        from tengod.ai_interpreter import interpret_bazi, build_bazi_context, \
            chat_with_memory, generate_personalized_recommendations
        assert callable(interpret_bazi)
        assert callable(build_bazi_context)
        assert callable(chat_with_memory)
        assert callable(generate_personalized_recommendations)


# ============================================================================
# 异步测试入口
# ============================================================================

def test_conversation_engine_chat():
    """pytest 异步测试：对话"""
    import asyncio
    from tengod.ai_interpreter import ConversationEngine, build_bazi_context
    engine = ConversationEngine()
    bazi_ctx = build_bazi_context(
        pillars={"year": "庚午", "month": "壬午", "day": "辛亥", "hour": "癸巳"},
        day_master="辛金",
    )
    result = asyncio.run(engine.chat("我的事业运如何？", "sess_test_async", bazi_context=bazi_ctx))
    assert "response" in result
    assert len(result["response"]) > 0