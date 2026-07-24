#!/usr/bin/env python3
"""
agent_orchestrator.py 测试套件
===============================
覆盖: Tool, StepResult, OrchestrationResult, AgentOrchestrator
"""

import pytest

from tengod.agent_orchestrator import (
    Tool,
    StepResult,
    OrchestrationResult,
    AgentOrchestrator,
    STANDARD_TOOLS,
)


# ═══════════════════════════════════════════════════════════
# Tool 测试
# ═══════════════════════════════════════════════════════════

class TestTool:

    def test_tool_creation(self):
        def test_func(params):
            return {"result": params}

        tool = Tool(
            name="test_tool",
            description="Test tool",
            func=test_func,
            parameters={"type": "object", "properties": {"key": {"type": "string"}}},
            category="test",
        )
        assert tool.name == "test_tool"
        assert tool.description == "Test tool"
        assert tool.category == "test"

    def test_to_openai_spec(self):
        def test_func(params):
            return {}

        tool = Tool(
            name="test_tool",
            description="Test tool",
            func=test_func,
            parameters={"type": "object", "properties": {"key": {"type": "string"}}},
        )
        spec = tool.to_openai_spec()
        assert spec["type"] == "function"
        assert spec["function"]["name"] == "test_tool"
        assert spec["function"]["description"] == "Test tool"


# ═══════════════════════════════════════════════════════════
# StepResult 测试
# ═══════════════════════════════════════════════════════════

class TestStepResult:

    def test_step_result_creation(self):
        result = StepResult(
            step=1,
            tool_name="test_tool",
            input_params={"key": "value"},
            output={"result": "ok"},
            success=True,
            duration_ms=100.0,
        )
        assert result.step == 1
        assert result.tool_name == "test_tool"
        assert result.success is True
        assert result.output == {"result": "ok"}

    def test_step_result_failure(self):
        result = StepResult(
            step=1,
            tool_name="test_tool",
            success=False,
            error="Failed",
        )
        assert result.success is False
        assert result.error == "Failed"

    def test_step_result_to_dict(self):
        result = StepResult(step=1, tool_name="test", output="ok")
        d = result.to_dict()
        assert d["step"] == 1
        assert d["tool_name"] == "test"
        assert d["success"] is True


# ═══════════════════════════════════════════════════════════
# OrchestrationResult 测试
# ═══════════════════════════════════════════════════════════

class TestOrchestrationResult:

    def test_orchestration_result_creation(self):
        steps = [StepResult(step=1, tool_name="tool1")]
        result = OrchestrationResult(
            session_id="test_session",
            user_intent="test intent",
            plan=["step1", "step2"],
            steps=steps,
            final_response="test response",
            tool_calls_count=1,
            total_duration_ms=200.0,
            success=True,
        )
        assert result.session_id == "test_session"
        assert result.user_intent == "test intent"
        assert len(result.steps) == 1
        assert result.success is True

    def test_orchestration_result_to_dict(self):
        steps = [StepResult(step=1, tool_name="tool1")]
        result = OrchestrationResult(
            session_id="test",
            plan=["step1"],
            steps=steps,
            success=True,
        )
        d = result.to_dict()
        assert d["session_id"] == "test"
        assert d["plan"] == ["step1"]
        assert len(d["steps"]) == 1
        assert d["success"] is True


# ═══════════════════════════════════════════════════════════
# AgentOrchestrator 测试
# ═══════════════════════════════════════════════════════════

class TestAgentOrchestrator:

    @pytest.fixture
    def orchestrator(self):
        return AgentOrchestrator()

    def test_initialization(self, orchestrator):
        assert len(orchestrator.tools) > 0
        assert orchestrator._max_steps == 10

    def test_get_tool_specs(self, orchestrator):
        specs = orchestrator.get_tool_specs()
        assert isinstance(specs, list)
        assert len(specs) > 0
        for spec in specs:
            assert "type" in spec
            assert "function" in spec

    def test_get_tool_descriptions(self, orchestrator):
        desc = orchestrator.get_tool_descriptions()
        assert isinstance(desc, str)
        assert "可用工具" in desc

    def test_detect_intent(self, orchestrator):
        result = orchestrator.detect_intent("帮我分析一下八字")
        assert isinstance(result, dict)
        assert "intents" in result
        assert "primary" in result
        assert "confidence" in result
        assert "八字" in result["intents"]
        assert result["primary"] == "八字"

        result = orchestrator.detect_intent("紫微斗数分析")
        assert "紫微" in result["intents"]

        result = orchestrator.detect_intent("随便说说")
        assert result["primary"] == "综合"

    def test_plan_actions(self, orchestrator):
        intent = {"primary": "八字"}
        plan = orchestrator.plan_actions("分析八字", intent)
        assert isinstance(plan, list)
        assert "analyze_bazi" in plan

        intent = {"primary": "融合"}
        plan = orchestrator.plan_actions("综合分析", intent)
        assert "fusion_analyze" in plan

    def test_execute_step(self, orchestrator):
        result = orchestrator.execute_step("analyze_bazi", {"birth_date": "1990-06-15"})
        assert isinstance(result, StepResult)
        assert result.tool_name == "analyze_bazi"
        assert result.success is True

    def test_execute_step_not_found(self, orchestrator):
        result = orchestrator.execute_step("nonexistent_tool", {})
        assert result.success is False
        assert "不存在" in result.error

    def test_execute_plan(self, orchestrator):
        plan = ["analyze_bazi", "generate_report"]
        results = orchestrator.execute_plan(plan, {"birth_date": "1990-06-15"})
        assert isinstance(results, list)
        assert len(results) == 2
        for r in results:
            assert isinstance(r, StepResult)
            assert r.success is True

    def test_execute_plan_failure(self, orchestrator):
        plan = ["nonexistent_tool", "generate_report"]
        results = orchestrator.execute_plan(plan, {})
        assert len(results) == 1
        assert results[0].success is False

    def test_execute_plan_max_steps(self):
        orchestrator = AgentOrchestrator(max_steps=2)
        plan = ["analyze_bazi", "generate_report", "fusion_analyze"]
        results = orchestrator.execute_plan(plan, {})
        assert len(results) == 2

    def test_custom_tools(self):
        def custom_tool(params):
            return {"custom": params}

        custom_tools = [
            Tool("custom_tool", "Custom tool", custom_tool, {})
        ]
        orchestrator = AgentOrchestrator(tools=custom_tools)
        assert len(orchestrator.tools) == 1
        assert orchestrator.tools[0].name == "custom_tool"

        result = orchestrator.execute_step("custom_tool", {"key": "value"})
        assert result.success is True
        assert result.output == {"custom": {"key": "value"}}
