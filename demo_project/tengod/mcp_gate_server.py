"""
mcp_gate_server.py — 十二神门禁 MCP 服务 v4.6.0
=====================================================
道曰："圣人无常心，以百姓心为心。"

将十二神门禁体系暴露为 MCP (Model Context Protocol) 服务，
任何 AI Agent 均可通过标准 MCP 协议调用门禁裁决。

MCP 工具列表：
  - judge_unit: 对单个认知单元执行十二神门禁裁决
  - judge_all_gates: 执行全部十二神门禁裁决
  - get_gate_status: 查询指定门禁状态与统计
  - get_element_cycle: 查询五行生克关系
  - get_twelve_gods_info: 获取十二神门禁体系元信息
  - get_gate_health: 获取门禁整体健康度
  - get_verdict_history: 获取门禁裁决历史
  - get_blind_spots: 获取系统盲点（太极·元辰）
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import json
import time

from .tbce_unit import CognitiveUnit, TBCECoordinates, GateState
from .twelve_gods_base import (
    TwelveGods, FiveElements, GateVerdict, TwelveGodsGate,
    GOD_ELEMENT_MAP, GOD_GATE_MAP,
)


# ============================================================================
# MCP 工具定义
# ============================================================================

MCP_GATE_TOOLS = [
    {
        "name": "judge_unit",
        "description": "对单个认知单元执行十二神门禁裁决，返回十二维非线性纠缠裁决结果",
        "input_schema": {
            "type": "object",
            "properties": {
                "unit_id": {"type": "string", "description": "认知单元ID"},
                "unit_name": {"type": "string", "description": "认知单元名称"},
                "s_coord": {"type": "number", "description": "TBCE-S源可信度 [0,1]", "default": 0.5},
                "t_coord": {"type": "number", "description": "TBCE-T时间坐标 [0,∞)", "default": 0.5},
                "p_coord": {"type": "number", "description": "TBCE-P投影保真度 [0,1]", "default": 0.5},
                "c_coord": {"type": "number", "description": "TBCE-C图层对齐度 [0,1]", "default": 0.5},
                "i_coord": {"type": "number", "description": "TBCE-I交织稳定性 [0,1]", "default": 0.5},
                "e_coord": {"type": "number", "description": "TBCE-E边缘探索度 [0,1]", "default": 0.5},
                "palace_id": {"type": "integer", "description": "九宫格ID (1-9)", "default": 5},
                "cognitive_layer": {"type": "integer", "description": "认知层 (1-8)", "default": 1},
                "gates": {"type": "array", "items": {"type": "string"},
                    "description": "指定门禁列表，空则全部执行"},
            },
            "required": ["unit_id", "unit_name"]
        },
    },
    {
        "name": "judge_all_gates",
        "description": "执行全部十二神门禁裁决，返回多数投票结果与太极否决状态",
        "input_schema": {
            "type": "object",
            "properties": {
                "unit_id": {"type": "string", "description": "认知单元ID"},
                "unit_name": {"type": "string", "description": "认知单元名称"},
                "s_coord": {"type": "number", "default": 0.5},
                "t_coord": {"type": "number", "default": 0.5},
                "p_coord": {"type": "number", "default": 0.5},
                "c_coord": {"type": "number", "default": 0.5},
                "i_coord": {"type": "number", "default": 0.5},
                "e_coord": {"type": "number", "default": 0.5},
                "palace_id": {"type": "integer", "default": 5},
                "cognitive_layer": {"type": "integer", "default": 1},
            },
            "required": ["unit_id", "unit_name"]
        },
    },
    {
        "name": "get_gate_status",
        "description": "查询指定十二神门禁的当前状态与统计信息",
        "input_schema": {
            "type": "object",
            "properties": {
                "god_name": {
                    "type": "string",
                    "description": "十二神名称：比肩/劫财/食神/伤官/正财/偏财/正官/七杀/正印/偏印/太极/元辰",
                },
            },
            "required": ["god_name"]
        },
    },
    {
        "name": "get_element_cycle",
        "description": "查询五行生克关系：木火土金水之间的相生相克链",
        "input_schema": {
            "type": "object",
            "properties": {
                "element": {
                    "type": "string",
                    "description": "五行元素：木/火/土/金/水/太极",
                    "default": "木",
                },
            },
        },
    },
    {
        "name": "get_twelve_gods_info",
        "description": "获取十二神门禁体系完整元信息：神位、五行、门禁类型、生克关系",
        "input_schema": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "get_gate_health",
        "description": "获取十二神门禁整体健康度：通过率、平衡度、盲点检测",
        "input_schema": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "get_verdict_history",
        "description": "获取指定门禁的裁决历史记录",
        "input_schema": {
            "type": "object",
            "properties": {
                "god_name": {"type": "string", "description": "十二神名称"},
                "limit": {"type": "integer", "description": "返回条数", "default": 20},
            },
            "required": ["god_name"]
        },
    },
    {
        "name": "get_blind_spots",
        "description": "获取系统自指涉盲点：太极·元辰门禁检测到的系统盲区",
        "input_schema": {
            "type": "object",
            "properties": {},
        },
    },
]


# ============================================================================
# MCP 十二神门禁服务
# ============================================================================

class MCPGateServer:
    """十二神门禁 MCP 服务 v2.33.0

    将十二神门禁系统暴露为标准 MCP 协议，任何 AI Agent 可调用。
    支持同步调用模式，返回结构化 JSON 响应。
    """

    VERSION = "2.33.0"
    SERVER_NAME = "tengod-twelve-gods-gate"

    def __init__(self):
        self._gate_instances: Dict[str, TwelveGodsGate] = {}
        self._verdict_history: List[Dict] = []
        self._max_history = 1000
        self._start_time = time.time()

    # ── MCP 协议接口 ──────────────────────────────────────────────────

    def get_tools(self) -> List[Dict[str, Any]]:
        """获取可用工具列表（MCP tools/list）"""
        return MCP_GATE_TOOLS

    def execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """执行工具调用（MCP tools/call）

        Args:
            tool_name: 工具名称
            arguments: 工具参数

        Returns:
            MCP 响应格式：{"content": [{"type": "text", "text": "..."}]}
        """
        try:
            if tool_name == "judge_unit":
                result = self._judge_unit(arguments)
            elif tool_name == "judge_all_gates":
                result = self._judge_all_gates(arguments)
            elif tool_name == "get_gate_status":
                result = self._get_gate_status(arguments)
            elif tool_name == "get_element_cycle":
                result = self._get_element_cycle(arguments)
            elif tool_name == "get_twelve_gods_info":
                result = self._get_twelve_gods_info(arguments)
            elif tool_name == "get_gate_health":
                result = self._get_gate_health(arguments)
            elif tool_name == "get_verdict_history":
                result = self._get_verdict_history(arguments)
            elif tool_name == "get_blind_spots":
                result = self._get_blind_spots(arguments)
            else:
                return self._error_response(f"未知工具: {tool_name}")

            return self._success_response(result)

        except Exception as e:
            return self._error_response(f"工具执行异常: {str(e)}")

    # ── 工具实现 ──────────────────────────────────────────────────────

    def _judge_unit(self, args: Dict) -> Dict:
        """对单个认知单元执行指定门禁裁决"""
        unit = self._build_unit(args)
        gate_names = args.get("gates", [])

        verdicts = {}
        all_passed = True

        if gate_names:
            # 指定门禁
            for name in gate_names:
                gate = self._get_or_create_gate(name)
                if gate:
                    verdict = gate.judge(unit)
                    verdicts[name] = verdict.to_dict()
                    if verdict.state != GateState.OPEN:
                        all_passed = False
        else:
            # 全部十二神
            for god in TwelveGods:
                gate = self._get_or_create_gate(god.value)
                if gate:
                    verdict = gate.judge(unit)
                    verdicts[god.value] = verdict.to_dict()
                    if verdict.state != GateState.OPEN:
                        all_passed = False

        self._record_verdicts(verdicts)

        return {
            "unit_id": unit.unit_id,
            "unit_name": unit.name,
            "verdicts": verdicts,
            "all_passed": all_passed,
            "gate_count": len(verdicts),
            "passed_count": sum(1 for v in verdicts.values() if v["state"] == GateState.OPEN),
        }

    def _judge_all_gates(self, args: Dict) -> Dict:
        """执行全部十二神门禁裁决，返回多数投票结果"""
        unit = self._build_unit(args)
        verdicts = {}
        element_results = {}

        for god in TwelveGods:
            gate = self._get_or_create_gate(god.value)
            if gate:
                verdict = gate.judge(unit)
                d = verdict.to_dict()
                verdicts[god.value] = d

                elem = d.get("element", "未知")
                if elem not in element_results:
                    element_results[elem] = {"passed": 0, "total": 0}
                element_results[elem]["total"] += 1
                if d["state"] == GateState.OPEN:
                    element_results[elem]["passed"] += 1

        self._record_verdicts(verdicts)

        # 多数投票
        open_count = sum(1 for v in verdicts.values() if v["state"] == GateState.OPEN)
        pending_count = sum(1 for v in verdicts.values() if v["state"] == GateState.PENDING)
        closed_count = sum(1 for v in verdicts.values() if v["state"] == GateState.CLOSED)
        total = len(verdicts)

        # 太极否决权
        tai_ji_verdict = verdicts.get("太极", {})
        veto_triggered = tai_ji_verdict.get("state") == GateState.CLOSED
        majority_passed = open_count > total / 2

        overall = "open"
        if veto_triggered:
            overall = "closed_by_veto"
        elif majority_passed:
            overall = "open"
        elif open_count + pending_count > total / 2:
            overall = "pending"
        else:
            overall = "closed"

        return {
            "unit_id": unit.unit_id,
            "unit_name": unit.name,
            "verdicts": verdicts,
            "majority": {
                "open": open_count,
                "pending": pending_count,
                "closed": closed_count,
                "total": total,
                "majority_passed": majority_passed,
            },
            "tai_ji_veto": veto_triggered,
            "overall": overall,
            "by_element": {
                elem: {
                    "passed": s["passed"],
                    "total": s["total"],
                    "pass_rate": round(s["passed"] / s["total"], 3),
                }
                for elem, s in element_results.items()
            },
        }

    def _get_gate_status(self, args: Dict) -> Dict:
        """查询指定门禁状态"""
        god_name = args.get("god_name", "")
        try:
            god = TwelveGods(god_name)
        except ValueError:
            return {"error": f"未知神位: {god_name}，可用: {[g.value for g in TwelveGods]}"}

        gate = self._get_or_create_gate(god.value)
        stats = gate.get_statistics() if gate else {}

        return {
            "god_name": god.value,
            "god_enum": god.name,
            "element": GOD_ELEMENT_MAP.get(god, FiveElements.TRANSCENDENT).value,
            "gate_type": GOD_GATE_MAP.get(god, "unknown"),
            "statistics": stats,
        }

    def _get_element_cycle(self, args: Dict) -> Dict:
        """查询五行生克关系"""
        element_name = args.get("element", "木")
        try:
            element = FiveElements(element_name)
        except ValueError:
            element = FiveElements.WOOD

        return {
            "element": element.value,
            "generates": element.generates.value,
            "overcomes": element.overcomes.value,
            "generated_by": [e.value for e in FiveElements if e.generates == element],
            "overcome_by": [e.value for e in FiveElements if e.overcomes == element],
            "full_cycle": {
                "generating": "木→火→土→金→水→木",
                "overcoming": "木→土→水→火→金→木",
            },
            "gods_by_element": {
                "木": ["比肩", "劫财"],
                "火": ["食神", "伤官"],
                "土": ["正财", "偏财"],
                "金": ["正官", "七杀"],
                "水": ["正印", "偏印"],
                "太极": ["太极", "元辰"],
            },
        }

    def _get_twelve_gods_info(self, args: Dict) -> Dict:
        """获取十二神门禁体系完整元信息"""
        gods_info = []
        for god in TwelveGods:
            gods_info.append({
                "name": god.value,
                "enum": god.name,
                "element": GOD_ELEMENT_MAP.get(god, FiveElements.TRANSCENDENT).value,
                "gate_type": GOD_GATE_MAP.get(god, "unknown"),
                "role": self._get_god_role(god),
            })

        return {
            "version": self.VERSION,
            "total_gods": len(TwelveGods),
            "elements": ["木", "火", "土", "金", "水", "太极"],
            "gods": gods_info,
            "element_cycles": {
                "generating": "木→火→土→金→水→木",
                "overcoming": "木→土→水→火→金→木",
            },
            "gate_types": {
                "architecture": "架构门禁（比肩·劫财/木）",
                "innovation": "创新门禁（食神·伤官/火）",
                "knowledge": "知识门禁（正财·偏财/土）",
                "law": "法度门禁（正官·七杀/金）",
                "nourish": "滋养门禁（正印·偏印/水）",
                "self_referential": "自指涉门禁（太极·元辰/超越五行）",
            },
        }

    def _get_gate_health(self, args: Dict) -> Dict:
        """获取十二神门禁整体健康度"""
        all_verdicts = self._verdict_history

        if not all_verdicts:
            return {
                "status": "no_data",
                "message": "尚无裁决记录",
                "uptime_seconds": round(time.time() - self._start_time, 1),
            }

        # 按门禁统计
        gate_stats = {}
        for record in all_verdicts:
            for god_name, verdict in record.get("verdicts", {}).items():
                if god_name not in gate_stats:
                    gate_stats[god_name] = {"total": 0, "open": 0, "pending": 0, "closed": 0}
                gate_stats[god_name]["total"] += 1
                state = verdict.get("state", "closed")
                gate_stats[god_name][state] += 1

        # 按五行统计
        element_stats = {}
        for god_name, stats in gate_stats.items():
            try:
                god = TwelveGods(god_name)
                elem = GOD_ELEMENT_MAP.get(god, FiveElements.TRANSCENDENT).value
            except ValueError:
                elem = "未知"
            if elem not in element_stats:
                element_stats[elem] = {"total": 0, "open": 0}
            element_stats[elem]["total"] += stats["total"]
            element_stats[elem]["open"] += stats["open"]

        # 整体通过率
        total_judgments = sum(s["total"] for s in gate_stats.values())
        total_passed = sum(s["open"] for s in gate_stats.values())
        overall_rate = round(total_passed / max(1, total_judgments), 3)

        # 阴阳平衡
        open_ratio = total_passed / max(1, total_judgments)
        balance = 1.0 - abs(open_ratio - 0.5) * 2  # 0.5为最佳平衡

        status = "healthy"
        if overall_rate < 0.4:
            status = "critical"
        elif overall_rate < 0.6:
            status = "warning"
        elif overall_rate < 0.3:
            status = "blocked"

        return {
            "status": status,
            "overall_pass_rate": overall_rate,
            "total_judgments": total_judgments,
            "yin_yang_balance": round(balance, 3),
            "by_gate": {
                name: {
                    "total": s["total"],
                    "pass_rate": round(s["open"] / max(1, s["total"]), 3),
                }
                for name, s in gate_stats.items()
            },
            "by_element": {
                elem: {
                    "total": s["total"],
                    "pass_rate": round(s["open"] / max(1, s["total"]), 3),
                }
                for elem, s in element_stats.items()
            },
            "uptime_seconds": round(time.time() - self._start_time, 1),
        }

    def _get_verdict_history(self, args: Dict) -> Dict:
        """获取门禁裁决历史"""
        god_name = args.get("god_name", "")
        limit = args.get("limit", 20)

        filtered = []
        for record in self._verdict_history:
            verdicts = record.get("verdicts", {})
            if god_name in verdicts:
                filtered.append({
                    "unit_id": record.get("unit_id", ""),
                    "unit_name": record.get("unit_name", ""),
                    "verdict": verdicts[god_name],
                    "timestamp": record.get("timestamp", 0),
                })
            elif not god_name:
                filtered.append(record)

        return {
            "god_name": god_name or "all",
            "total": len(filtered),
            "history": filtered[-limit:],
        }

    def _get_blind_spots(self, args: Dict) -> Dict:
        """获取系统盲点"""
        # 检查哪些门禁从未被裁决
        all_gods = {g.value for g in TwelveGods}
        judged_gods = set()
        for record in self._verdict_history:
            judged_gods.update(record.get("verdicts", {}).keys())

        missing = all_gods - judged_gods

        # 检查通过率异常低的门禁
        gate_stats = {}
        for record in self._verdict_history:
            for god_name, verdict in record.get("verdicts", {}).items():
                if god_name not in gate_stats:
                    gate_stats[god_name] = {"total": 0, "open": 0}
                gate_stats[god_name]["total"] += 1
                if verdict.get("state") == GateState.OPEN:
                    gate_stats[god_name]["open"] += 1

        low_performers = []
        for name, stats in gate_stats.items():
            rate = stats["open"] / max(1, stats["total"])
            if rate < 0.3 and stats["total"] >= 3:
                low_performers.append({
                    "god": name,
                    "pass_rate": round(rate, 3),
                    "total": stats["total"],
                })

        return {
            "never_judged": list(missing),
            "low_performers": low_performers,
            "total_blind_spots": len(missing) + len(low_performers),
            "recommendation": (
                "建议对盲点门禁进行针对性测试" if missing or low_performers
                else "所有门禁运行正常，无盲点"
            ),
        }

    # ── 辅助方法 ──────────────────────────────────────────────────────

    def _build_unit(self, args: Dict) -> CognitiveUnit:
        """从参数构建认知单元"""
        return CognitiveUnit(
            unit_id=args["unit_id"],
            name=args["unit_name"],
            module_path=f"mcp.{args.get('unit_name', 'unknown')}",
            coordinates=TBCECoordinates(
                S=float(args.get("s_coord", 0.5)),
                T=float(args.get("t_coord", 0.5)),
                P=float(args.get("p_coord", 0.5)),
                C=float(args.get("c_coord", 0.5)),
                I=float(args.get("i_coord", 0.5)),
                E=float(args.get("e_coord", 0.5)),
            ),
            psi_operator=args.get("psi_operator", "ZuowangAttention"),
            palace_id=args.get("palace_id"),
            cognitive_layer=args.get("cognitive_layer", 1),
            tense="present",
            description=f"MCP调用: {args.get('unit_name', 'unknown')}",
        )

    def _get_or_create_gate(self, god_name: str) -> Optional[TwelveGodsGate]:
        """获取或创建门禁实例"""
        if god_name in self._gate_instances:
            return self._gate_instances[god_name]

        try:
            god = TwelveGods(god_name)
        except ValueError:
            return None

        gate_type = GOD_GATE_MAP.get(god, "")

        # 根据门禁类型创建对应实例
        if gate_type == "architecture":
            from .architecture_gate import ArchitectureGate
            gate = ArchitectureGate()
        elif gate_type == "innovation":
            from .innovation_gate import InnovationGate
            gate = InnovationGate()
        elif gate_type == "knowledge":
            from .knowledge_gate import KnowledgeGate
            gate = KnowledgeGate()
        elif gate_type == "law":
            from .law_gate import LawGate
            gate = LawGate()
        elif gate_type == "nourish":
            from .nourish_gate import NourishGate
            gate = NourishGate()
        elif gate_type == "self_referential":
            from .self_referential_gate import SelfReferentialGate
            gate = SelfReferentialGate()
        else:
            return None

        self._gate_instances[god_name] = gate
        return gate

    def _record_verdicts(self, verdicts: Dict) -> None:
        """记录裁决历史"""
        self._verdict_history.append({
            "verdicts": verdicts,
            "timestamp": time.time(),
        })
        if len(self._verdict_history) > self._max_history:
            self._verdict_history = self._verdict_history[-self._max_history:]

    def _get_god_role(self, god: TwelveGods) -> str:
        """获取十二神角色描述"""
        roles = {
            TwelveGods.BIJIAN: "架构协同：模块间依赖是否健康？",
            TwelveGods.JIECAI: "攻防边界：系统边界是否安全？",
            TwelveGods.SHISHEN: "创生输出：生成质量是否达标？",
            TwelveGods.SHANGGUAN: "破界创新：创新是否带来系统性风险？",
            TwelveGods.ZHENGCAI: "知识固化：知识存储是否可靠？",
            TwelveGods.PIANCAI: "奇招演化：知识演化是否健康？",
            TwelveGods.ZHENGGUAN: "法度调度：调度策略是否合规？",
            TwelveGods.QISHA: "品质裁决：输出品质是否达标？",
            TwelveGods.ZHENGYIN: "滋养守护：配置与文档是否健康？",
            TwelveGods.PIANYIN: "桥接通变：微调与外挂是否安全？",
            TwelveGods.TAIJI: "阴阳调和：系统整体是否平衡？",
            TwelveGods.YUANCHEN: "本源定位：系统是否在观察自身？",
        }
        return roles.get(god, "未知")

    # ── MCP 响应格式 ──────────────────────────────────────────────────

    def _success_response(self, data: Any) -> Dict:
        """构建 MCP 成功响应"""
        return {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps(data, ensure_ascii=False, default=str),
                }
            ],
            "isError": False,
        }

    def _error_response(self, message: str) -> Dict:
        """构建 MCP 错误响应"""
        return {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps({"error": message}, ensure_ascii=False),
                }
            ],
            "isError": True,
        }

    def get_server_info(self) -> Dict:
        """获取服务信息"""
        return {
            "name": self.SERVER_NAME,
            "version": self.VERSION,
            "tool_count": len(MCP_GATE_TOOLS),
            "uptime_seconds": round(time.time() - self._start_time, 1),
        }


# ============================================================================
# 全局单例
# ============================================================================

_mcp_gate_server: Optional[MCPGateServer] = None


def get_mcp_gate_server() -> MCPGateServer:
    """获取 MCP 门禁服务单例"""
    global _mcp_gate_server
    if _mcp_gate_server is None:
        _mcp_gate_server = MCPGateServer()
    return _mcp_gate_server


def reset_mcp_gate_server() -> None:
    """重置 MCP 门禁服务"""
    global _mcp_gate_server
    _mcp_gate_server = None


__all__ = [
    "MCPGateServer",
    "MCP_GATE_TOOLS",
    "get_mcp_gate_server",
    "reset_mcp_gate_server",
]