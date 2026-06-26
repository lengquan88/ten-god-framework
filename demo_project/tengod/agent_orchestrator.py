"""
agent_orchestrator.py — 智能体编排引擎 v2.9
=============================================
Plan → Execute → Observe → Reflect 循环
工具链自动编排，LLM 自主决策
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Callable, Dict, List, Optional
import time

# v2.13.0: 十神智能体工具导入
from .shen_agents import (
    ALL_AGENTS,
    agent_tool_dispatcher,
)


# ============================================================================
# 工具定义
# ============================================================================

@dataclass
class Tool:
    """工具定义"""
    name: str
    description: str
    func: Callable
    parameters: Dict[str, Any] = field(default_factory=dict)
    category: str = "general"

    def to_openai_spec(self) -> Dict:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }


# ── 标准工具集 ──────────────────────────────────────────────────────────────

def _analyze_bazi_tool(params: Dict) -> Dict:
    """八字分析工具"""
    return {"tool": "analyze_bazi", "result": "八字分析完成", "params": params}


def _analyze_ziwei_tool(params: Dict) -> Dict:
    return {"tool": "analyze_ziwei", "result": "紫微斗数分析完成", "params": params}


def _cast_qimen_tool(params: Dict) -> Dict:
    return {"tool": "cast_qimen", "result": "奇门遁甲起盘完成", "params": params}


def _cast_liuyao_tool(params: Dict) -> Dict:
    return {"tool": "cast_liuyao", "result": "六爻起卦完成", "params": params}


def _compare_cases_tool(params: Dict) -> Dict:
    return {"tool": "compare_cases", "result": "案例对比完成", "params": params}


def _generate_report_tool(params: Dict) -> Dict:
    return {"tool": "generate_report", "result": "综合报告生成完成", "params": params}


def _fusion_analyze_tool(params: Dict) -> Dict:
    return {"tool": "fusion_analyze", "result": "三体系融合分析完成", "params": params}


def _fengshui_evaluate_tool(params: Dict) -> Dict:
    return {"tool": "fengshui_evaluate", "result": "风水评估完成", "params": params}


STANDARD_TOOLS: List[Tool] = [
    Tool("analyze_bazi", "八字命理分析，包括日主、五行、格局、神煞、大运流年", _analyze_bazi_tool,
         {"type": "object", "properties": {"birth_date": {"type": "string"}, "birth_time": {"type": "string"}},
          "required": ["birth_date"]}, "divination"),
    Tool("analyze_ziwei", "紫微斗数分析，十二宫位、星曜分布、四化飞星", _analyze_ziwei_tool,
         {"type": "object", "properties": {"birth_date": {"type": "string"}, "birth_time": {"type": "string"}},
          "required": ["birth_date", "birth_time"]}, "divination"),
    Tool("cast_qimen", "奇门遁甲时空盘，八门九星八神天地盘", _cast_qimen_tool,
         {"type": "object", "properties": {"datetime": {"type": "string"}, "question": {"type": "string"}},
          "required": []}, "divination"),
    Tool("cast_liuyao", "六爻起卦占卜，本卦变卦互卦六亲六神", _cast_liuyao_tool,
         {"type": "object", "properties": {"question": {"type": "string"}, "date": {"type": "string"}},
          "required": ["question"]}, "divination"),
    Tool("compare_cases", "相似命盘案例对比，历史验证参考", _compare_cases_tool,
         {"type": "object", "properties": {"bazi_data": {"type": "object"}, "top_k": {"type": "integer"}},
          "required": ["bazi_data"]}, "analysis"),
    Tool("generate_report", "综合命理报告生成，支持多语言", _generate_report_tool,
         {"type": "object", "properties": {"lang": {"type": "string"}, "systems": {"type": "array"}},
          "required": []}, "report"),
    Tool("fusion_analyze", "三体系融合分析，八字+紫微+奇门交叉验证", _fusion_analyze_tool,
         {"type": "object", "properties": {"bazi": {"type": "object"}, "ziwei": {"type": "object"}, "qimen": {"type": "object"}},
          "required": []}, "analysis"),
    Tool("fengshui_evaluate", "风水评估，玄空飞星+山向分析", _fengshui_evaluate_tool,
         {"type": "object", "properties": {"direction": {"type": "string"}, "year": {"type": "integer"}},
          "required": ["direction"]}, "divination"),
]

# v2.13.0: 十神智能体工具注册
def _shen_agent_tool_factory(agent_name: str, agent_title: str, agent_desc: str) -> Callable:
    """创建十神智能体工具函数"""
    def _tool(params: Dict) -> Dict:
        return agent_tool_dispatcher(agent_name, params)
    _tool.__name__ = f"_shen_{agent_name}_tool"
    return _tool

for agent_name, agent in ALL_AGENTS.items():
    tool_func = _shen_agent_tool_factory(agent_name, agent.title, agent.description)
    tool = Tool(
        f"shen_{agent_name}",
        f"{agent.title}：{agent.description}",
        tool_func,
        {"type": "object", "properties": {
            "bazi_data": {"type": "object", "description": "八字命盘数据"},
            "question": {"type": "string", "description": "用户具体问题"},
        }, "required": ["bazi_data"]},
        "shen",
    )
    STANDARD_TOOLS.append(tool)  # type: ignore[arg-type]


# ============================================================================
# 编排结果
# ============================================================================

@dataclass
class StepResult:
    """单步执行结果"""
    step: int
    tool_name: str
    input_params: Dict[str, Any] = field(default_factory=dict)
    output: Any = None
    success: bool = True
    error: Optional[str] = None
    duration_ms: float = 0

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class OrchestrationResult:
    """编排结果"""
    session_id: str = ""
    user_intent: str = ""
    plan: List[str] = field(default_factory=list)
    steps: List[StepResult] = field(default_factory=list)
    final_response: str = ""
    tool_calls_count: int = 0
    total_duration_ms: float = 0
    success: bool = True

    def to_dict(self) -> Dict:
        return {
            "session_id": self.session_id,
            "user_intent": self.user_intent,
            "plan": self.plan,
            "steps": [s.to_dict() for s in self.steps],
            "final_response": self.final_response,
            "tool_calls_count": self.tool_calls_count,
            "total_duration_ms": self.total_duration_ms,
            "success": self.success,
        }


# ============================================================================
# 智能体编排器
# ============================================================================

class AgentOrchestrator:
    """智能体编排引擎

    基于 Plan → Execute → Observe → Reflect 循环，
    自动编排工具链，支持 LLM 自主决策。
    """

    def __init__(self, tools: Optional[List[Tool]] = None, max_steps: int = 10):
        self._tools = tools or STANDARD_TOOLS
        self._tool_map = {t.name: t for t in self._tools}
        self._max_steps = max_steps

    @property
    def tools(self) -> List[Tool]:
        return self._tools

    def get_tool_specs(self) -> List[Dict]:
        """获取工具规格（OpenAI function calling 格式）"""
        return [t.to_openai_spec() for t in self._tools]

    def get_tool_descriptions(self) -> str:
        """获取工具描述文本"""
        lines = ["可用工具："]
        for t in self._tools:
            lines.append(f"  - {t.name}: {t.description} [{t.category}]")
        return "\n".join(lines)

    # ── 意图识别 ──────────────────────────────────────────────────────────

    def detect_intent(self, user_message: str) -> Dict[str, Any]:
        """识别用户意图"""
        # 规则匹配
        intent_map = {
            "八字": ["八字", "命理", "生辰", "日主", "五行", "格局", "用神", "大运"],
            "紫微": ["紫微", "斗数", "命宫", "十二宫", "星曜", "四化"],
            "奇门": ["奇门", "遁甲", "时空", "八门", "九星"],
            "六爻": ["六爻", "占卜", "卦象", "起卦", "算卦"],
            "风水": ["风水", "玄空", "飞星", "罗盘", "山向"],
            "融合": ["综合", "融合", "全面", "多方", "对比"],
            "报告": ["报告", "总结", "汇总"],
            "案例": ["案例", "相似", "对比", "参考"],
        }

        matched = []
        for intent, keywords in intent_map.items():
            if any(kw in user_message for kw in keywords):
                matched.append(intent)

        return {
            "intents": matched,
            "primary": matched[0] if matched else "综合",
            "confidence": min(len(matched) * 0.25, 1.0),
        }

    # ── 计划生成 ──────────────────────────────────────────────────────────

    def plan_actions(self, user_message: str, intent: Dict) -> List[str]:
        """根据意图生成行动计划"""
        plans = {
            "八字": ["analyze_bazi", "generate_report"],
            "紫微": ["analyze_ziwei", "generate_report"],
            "奇门": ["cast_qimen", "generate_report"],
            "六爻": ["cast_liuyao", "generate_report"],
            "风水": ["fengshui_evaluate", "generate_report"],
            "融合": ["analyze_bazi", "analyze_ziwei", "fusion_analyze", "generate_report"],
            "报告": ["generate_report"],
            "案例": ["analyze_bazi", "compare_cases", "generate_report"],
            "综合": ["analyze_bazi", "fusion_analyze", "generate_report"],
        }

        primary = intent.get("primary", "综合")
        return plans.get(primary, ["analyze_bazi", "generate_report"])

    # ── 执行 ──────────────────────────────────────────────────────────────

    def execute_step(self, tool_name: str, params: Dict[str, Any]) -> StepResult:
        """执行单个工具步骤"""
        tool = self._tool_map.get(tool_name)
        if not tool:
            return StepResult(step=0, tool_name=tool_name, success=False,
                              error=f"工具 '{tool_name}' 不存在")

        start = time.time()
        try:
            output = tool.func(params)
            duration_ms = (time.time() - start) * 1000
            return StepResult(
                step=0, tool_name=tool_name,
                input_params=params, output=output,
                success=True, duration_ms=duration_ms,
            )
        except Exception as e:
            duration_ms = (time.time() - start) * 1000
            return StepResult(
                step=0, tool_name=tool_name,
                success=False, error=str(e), duration_ms=duration_ms,
            )

    def execute_plan(
        self,
        plan: List[str],
        params: Optional[Dict[str, Any]] = None,
    ) -> List[StepResult]:
        """执行完整计划"""
        params = params or {}
        results = []

        for i, tool_name in enumerate(plan):
            if i >= self._max_steps:
                break
            result = self.execute_step(tool_name, params)
            result.step = i + 1
            results.append(result)
            if not result.success:
                break

        return results

    # ── 主入口 ────────────────────────────────────────────────────────────

    def orchestrate(
        self,
        user_message: str,
        params: Optional[Dict[str, Any]] = None,
        session_id: str = "",
    ) -> OrchestrationResult:
        """编排执行

        Args:
            user_message: 用户消息
            params: 额外参数
            session_id: 会话ID

        Returns:
            OrchestrationResult
        """
        start = time.time()

        # 1. Plan: 意图识别 + 计划生成
        intent = self.detect_intent(user_message)
        plan = self.plan_actions(user_message, intent)

        # 2. Execute: 执行计划
        steps = self.execute_plan(plan, params)

        # 3. Observe: 聚合结果
        success_count = sum(1 for s in steps if s.success)
        final_response = self._build_final_response(intent, steps)

        duration_ms = (time.time() - start) * 1000

        return OrchestrationResult(
            session_id=session_id,
            user_intent=intent.get("primary", "综合"),
            plan=plan,
            steps=steps,
            final_response=final_response,
            tool_calls_count=len(steps),
            total_duration_ms=duration_ms,
            success=success_count == len(plan),
        )

    def _build_final_response(
        self, intent: Dict, steps: List[StepResult],
    ) -> str:
        """构建最终回复"""
        lines = []
        lines.append(f"已为您完成{intent.get('primary', '综合')}分析：")
        for step in steps:
            if step.success:
                lines.append(f"  ✓ {step.tool_name}: {step.output.get('result', '完成')}")
            else:
                lines.append(f"  ✗ {step.tool_name}: {step.error}")
        return "\n".join(lines)


# ── 便捷函数 ────────────────────────────────────────────────────────────────

_orchestrator: Optional[AgentOrchestrator] = None


def get_orchestrator() -> AgentOrchestrator:
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = AgentOrchestrator()
    return _orchestrator


def quick_orchestrate(
    user_message: str,
    params: Optional[Dict] = None,
) -> OrchestrationResult:
    """快速编排"""
    return get_orchestrator().orchestrate(user_message, params)


__all__ = [
    "AgentOrchestrator",
    "OrchestrationResult",
    "StepResult",
    "Tool",
    "STANDARD_TOOLS",
    "get_orchestrator",
    "quick_orchestrate",
]