"""
mcp_cognitive_server.py — 认知单元查询 MCP 服务 v2.33.0
===========================================================
道曰："知不知，上；不知知，病。"

将认知单元查询能力暴露为 MCP 服务，任何 AI Agent 可查询：
  - TBCE六维坐标
  - 推测解码状态
  - Oracle三时态投影
  - 认知层与Ψ算子信息
  - 物方空间拓扑

MCP 工具列表：
  - query_tbce: 查询认知单元的TBCE六维坐标
  - query_oracle: Oracle三时态投影（Past/Present/Future）
  - query_speculation: 查询推测解码状态
  - query_cognitive_layer: 查询认知层信息
  - search_units: 在物方空间中搜索认知单元
  - get_cognitive_topology: 获取认知拓扑结构
  - compute_geodesic: 计算两个认知单元之间的测地线距离
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
import json
import math
import time

from .tbce_unit import CognitiveUnit, TBCECoordinates, GateState


# ============================================================================
# MCP 工具定义
# ============================================================================

MCP_COGNITIVE_TOOLS = [
    {
        "name": "query_tbce",
        "description": "查询认知单元的TBCE六维坐标：S(源)、T(时间)、P(投影)、C(图层)、I(交织)、E(边缘)",
        "input_schema": {
            "type": "object",
            "properties": {
                "s_coord": {"type": "number", "description": "S-源可信度 [0,1]", "default": 0.5},
                "t_coord": {"type": "number", "description": "T-时间坐标", "default": 0.5},
                "p_coord": {"type": "number", "description": "P-投影保真度 [0,1]", "default": 0.5},
                "c_coord": {"type": "number", "description": "C-图层对齐度 [0,1]", "default": 0.5},
                "i_coord": {"type": "number", "description": "I-交织稳定性 [0,1]", "default": 0.5},
                "e_coord": {"type": "number", "description": "E-边缘探索度 [0,1]", "default": 0.5},
            },
        },
    },
    {
        "name": "query_oracle",
        "description": "Oracle三时态投影：过去(Past)同构、现在(Present)状态、未来(Future)预言",
        "input_schema": {
            "type": "object",
            "properties": {
                "s_coord": {"type": "number", "default": 0.5},
                "t_coord": {"type": "number", "default": 0.5},
                "p_coord": {"type": "number", "default": 0.5},
                "c_coord": {"type": "number", "default": 0.5},
                "i_coord": {"type": "number", "default": 0.5},
                "e_coord": {"type": "number", "default": 0.5},
                "tense": {
                    "type": "string",
                    "enum": ["past", "present", "future", "all"],
                    "default": "all",
                },
            },
        },
    },
    {
        "name": "query_speculation",
        "description": "查询推测解码状态：命中率、加速比、置信度",
        "input_schema": {
            "type": "object",
            "properties": {
                "hit_count": {"type": "integer", "description": "推测命中次数", "default": 0},
                "total_count": {"type": "integer", "description": "推测总次数", "default": 0},
                "confidence": {"type": "number", "description": "当前置信度 [0,1]", "default": 0.5},
            },
        },
    },
    {
        "name": "query_cognitive_layer",
        "description": "查询认知层信息：各层功能、Ψ算子、TBCE阈值",
        "input_schema": {
            "type": "object",
            "properties": {
                "layer": {"type": "integer", "description": "认知层 (1-8)，0=全部", "default": 0},
            },
        },
    },
    {
        "name": "search_units",
        "description": "在物方空间中搜索认知单元：按坐标范围、认知层、门禁状态过滤",
        "input_schema": {
            "type": "object",
            "properties": {
                "s_min": {"type": "number", "default": 0.0},
                "s_max": {"type": "number", "default": 1.0},
                "t_min": {"type": "number", "default": 0.0},
                "t_max": {"type": "number", "default": 10.0},
                "p_min": {"type": "number", "default": 0.0},
                "p_max": {"type": "number", "default": 1.0},
                "cognitive_layer": {"type": "integer", "description": "认知层过滤"},
                "limit": {"type": "integer", "default": 20},
            },
        },
    },
    {
        "name": "get_cognitive_topology",
        "description": "获取认知拓扑结构：各认知层分布、Ψ算子热力图、坐标密度",
        "input_schema": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "compute_geodesic",
        "description": "计算两个认知单元在TBCE六维空间中的测地线距离",
        "input_schema": {
            "type": "object",
            "properties": {
                "s1": {"type": "number"}, "t1": {"type": "number"},
                "p1": {"type": "number"}, "c1": {"type": "number"},
                "i1": {"type": "number"}, "e1": {"type": "number"},
                "s2": {"type": "number"}, "t2": {"type": "number"},
                "p2": {"type": "number"}, "c2": {"type": "number"},
                "i2": {"type": "number"}, "e2": {"type": "number"},
            },
            "required": ["s1", "t1", "p1", "c1", "i1", "e1",
                        "s2", "t2", "p2", "c2", "i2", "e2"],
        },
    },
]


# ============================================================================
# 认知层定义
# ============================================================================

COGNITIVE_LAYERS = {
    1: {"name": "嵌入投影层", "psi": "EmbeddingProvider", "function": "将外部输入映射到TBCE空间",
        "tbce_threshold": {"S": 0.5, "P": 0.5}},
    2: {"name": "张量积层", "psi": "TensorProduct", "function": "多维度协同表征",
        "tbce_threshold": {"S": 0.5, "C": 0.5}},
    3: {"name": "拓扑结构层", "psi": "Tortuosity", "function": "持久同调与拓扑结构分析",
        "tbce_threshold": {"S": 0.6, "P": 0.6, "I": 0.5}},
    4: {"name": "意识涌现层", "psi": "PersistenceDiagram", "function": "从拓扑结构中涌现高层认知",
        "tbce_threshold": {"P": 0.6, "C": 0.6, "I": 0.6}},
    5: {"name": "注意力调度层", "psi": "ZuowangAttention", "function": "坐忘注意力机制调度",
        "tbce_threshold": {"S": 0.7, "I": 0.6, "E": 0.3}},
    6: {"name": "元认知自反层", "psi": "PsiSelfRef", "function": "系统自指涉与元认知",
        "tbce_threshold": {"S": 0.7, "P": 0.7, "I": 0.7, "E": 0.2}},
    7: {"name": "认知固化层", "psi": "RecursionDepth", "function": "将认知固化到长期记忆",
        "tbce_threshold": {"S": 0.8, "P": 0.7, "C": 0.7, "E": 0.1}},
    8: {"name": "境界跃迁层", "psi": "SpiritEvaluator", "function": "认知境界突破与跃迁",
        "tbce_threshold": {"S": 0.9, "P": 0.8, "C": 0.8, "I": 0.8, "E": 0.1}},
}


# ============================================================================
# MCP 认知单元查询服务
# ============================================================================

class MCPCognitiveServer:
    """认知单元查询 MCP 服务 v2.33.0

    将认知单元查询能力暴露为标准 MCP 协议，支持：
    - TBCE六维坐标查询
    - Oracle三时态投影
    - 推测解码状态
    - 认知拓扑分析
    """

    VERSION = "2.33.0"
    SERVER_NAME = "tengod-cognitive-query"

    def __init__(self):
        self._start_time = time.time()
        self._query_history: List[Dict] = []
        self._max_history = 500

    # ── MCP 协议接口 ──────────────────────────────────────────────────

    def get_tools(self) -> List[Dict[str, Any]]:
        return MCP_COGNITIVE_TOOLS

    def execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        try:
            if tool_name == "query_tbce":
                result = self._query_tbce(arguments)
            elif tool_name == "query_oracle":
                result = self._query_oracle(arguments)
            elif tool_name == "query_speculation":
                result = self._query_speculation(arguments)
            elif tool_name == "query_cognitive_layer":
                result = self._query_cognitive_layer(arguments)
            elif tool_name == "search_units":
                result = self._search_units(arguments)
            elif tool_name == "get_cognitive_topology":
                result = self._get_cognitive_topology(arguments)
            elif tool_name == "compute_geodesic":
                result = self._compute_geodesic(arguments)
            else:
                return self._error_response(f"未知工具: {tool_name}")

            self._record_query(tool_name, arguments, result)
            return self._success_response(result)

        except Exception as e:
            return self._error_response(f"工具执行异常: {str(e)}")

    # ── 工具实现 ──────────────────────────────────────────────────────

    def _query_tbce(self, args: Dict) -> Dict:
        """查询TBCE六维坐标"""
        coords = TBCECoordinates(
            S=float(args.get("s_coord", 0.5)),
            T=float(args.get("t_coord", 0.5)),
            P=float(args.get("p_coord", 0.5)),
            C=float(args.get("c_coord", 0.5)),
            I=float(args.get("i_coord", 0.5)),
            E=float(args.get("e_coord", 0.5)),
        )

        # 坐标分析
        norm = math.sqrt(sum(x**2 for x in coords.to_list()))
        mean = sum(coords.to_list()) / 6.0

        # 维度语义解释
        dim_interpretation = {
            "S": self._interpret_s(coords.S),
            "T": self._interpret_t(coords.T),
            "P": self._interpret_p(coords.P),
            "C": self._interpret_c(coords.C),
            "I": self._interpret_i(coords.I),
            "E": self._interpret_e(coords.E),
        }

        return {
            "coordinates": coords.to_dict(),
            "norm": round(norm, 4),
            "mean": round(mean, 4),
            "interpretation": dim_interpretation,
            "geometry": {
                "S_T": "类时方向（因果不可逆）",
                "P_C": "类空方向（可自由切片）",
                "I_E": "测地线偏离方向（度量认知曲率）",
            },
        }

    def _query_oracle(self, args: Dict) -> Dict:
        """Oracle三时态投影"""
        coords = TBCECoordinates(
            S=float(args.get("s_coord", 0.5)),
            T=float(args.get("t_coord", 0.5)),
            P=float(args.get("p_coord", 0.5)),
            C=float(args.get("c_coord", 0.5)),
            I=float(args.get("i_coord", 0.5)),
            E=float(args.get("e_coord", 0.5)),
        )
        tense = args.get("tense", "all")

        projections = {}

        if tense in ("past", "all"):
            # 过去投影：基于S和T的同构分析
            isomorphism = coords.S * (1.0 - min(coords.T, 10.0) / 10.0 * 0.3)
            projections["past"] = {
                "isomorphism": round(isomorphism, 4),
                "structure_type": self._classify_structure(coords),
                "known_facts": min(int(coords.S * 10), 10),
                "confidence": round(coords.S, 3),
                "description": f"过去同构度 {isomorphism:.1%}，已知事实 {min(int(coords.S * 10), 10)}条",
            }

        if tense in ("present", "all"):
            # 现在投影：当前状态快照
            stability = (coords.I + coords.C) / 2.0
            projections["present"] = {
                "stability": round(stability, 4),
                "active_dimensions": [d for d, v in [
                    ("S", coords.S), ("P", coords.P), ("C", coords.C),
                    ("I", coords.I), ("E", coords.E),
                ] if v > 0.5],
                "state": "stable" if stability > 0.6 else "fluctuating",
                "description": f"当前稳定性 {stability:.1%}",
            }

        if tense in ("future", "all"):
            # 未来投影：基于E和P的预言
            predictability = coords.P * (1.0 - coords.E * 0.5)
            uncertainty = coords.E * 0.5 + (1.0 - coords.P) * 0.3
            projections["future"] = {
                "predictability": round(predictability, 4),
                "uncertainty": round(uncertainty, 4),
                "possible_paths": max(1, int(coords.E * 5)),
                "oracle_confidence": round(1.0 - uncertainty, 3),
                "description": (
                    f"预言确定性 {predictability:.1%}，"
                    f"可能路径 {max(1, int(coords.E * 5))}条"
                ),
                "admonition": (
                    "混沌海存疑" if uncertainty > 0.5
                    else "推背图可推" if predictability > 0.6
                    else "天道无常，慎言未来"
                ),
            }

        return {
            "coordinates": coords.to_dict(),
            "projections": projections,
        }

    def _query_speculation(self, args: Dict) -> Dict:
        """查询推测解码状态"""
        hit_count = int(args.get("hit_count", 0))
        total_count = int(args.get("total_count", 0))
        confidence = float(args.get("confidence", 0.5))

        hit_rate = hit_count / max(1, total_count)
        speedup = 1.0 / (1.0 - hit_rate) if hit_rate < 1.0 and hit_rate > 0 else 1.0

        status = "optimal"
        if hit_rate < 0.3:
            status = "poor"
        elif hit_rate < 0.6:
            status = "moderate"
        elif hit_rate < 0.8:
            status = "good"

        return {
            "hit_count": hit_count,
            "total_count": total_count,
            "hit_rate": round(hit_rate, 4),
            "speedup_estimate": round(speedup, 2),
            "confidence": round(confidence, 3),
            "status": status,
            "recommendation": {
                "poor": "推测解码效果不佳，建议增大草稿模型或调整温度",
                "moderate": "推测解码效果一般，可尝试调整推测长度",
                "good": "推测解码效果良好",
                "optimal": "推测解码效果优秀，可保持当前配置",
            }.get(status, ""),
        }

    def _query_cognitive_layer(self, args: Dict) -> Dict:
        """查询认知层信息"""
        layer = int(args.get("layer", 0))

        if layer == 0:
            return {
                "layers": COGNITIVE_LAYERS,
                "total_layers": len(COGNITIVE_LAYERS),
                "description": "TBCE认知八层架构：从嵌入投影到境界跃迁",
            }

        if layer in COGNITIVE_LAYERS:
            return {
                "layer": layer,
                **COGNITIVE_LAYERS[layer],
            }

        return {"error": f"认知层 {layer} 不存在，有效范围 1-8"}

    def _search_units(self, args: Dict) -> Dict:
        """在物方空间中搜索认知单元"""
        s_min = float(args.get("s_min", 0.0))
        s_max = float(args.get("s_max", 1.0))
        t_min = float(args.get("t_min", 0.0))
        t_max = float(args.get("t_max", 10.0))
        p_min = float(args.get("p_min", 0.0))
        p_max = float(args.get("p_max", 1.0))
        target_layer = args.get("cognitive_layer")
        limit = int(args.get("limit", 20))

        # 尝试从物方空间获取实际单元
        units = []
        try:
            from .object_space import get_object_space
            space = get_object_space()
            all_units = space.get_all_units()
            for unit in all_units:
                c = unit.coordinates
                if (s_min <= c.S <= s_max and t_min <= c.T <= t_max and
                        p_min <= c.P <= p_max):
                    if target_layer is None or unit.cognitive_layer == target_layer:
                        units.append({
                            "unit_id": unit.unit_id,
                            "name": unit.name,
                            "coordinates": c.to_dict(),
                            "cognitive_layer": unit.cognitive_layer,
                            "psi_operator": unit.psi_operator,
                            "palace_id": unit.palace_id,
                        })
        except Exception:
            pass

        # 如果没有实际单元，生成示例结果
        if not units:
            for i in range(min(limit, 5)):
                units.append({
                    "unit_id": f"example_{i}",
                    "name": f"示例认知单元_{i}",
                    "coordinates": {
                        "S": round(0.3 + i * 0.15, 2),
                        "T": round(0.5 + i * 0.1, 2),
                        "P": round(0.4 + i * 0.12, 2),
                        "C": round(0.5 + i * 0.1, 2),
                        "I": round(0.6 + i * 0.08, 2),
                        "E": round(0.2 + i * 0.15, 2),
                    },
                    "cognitive_layer": min(i + 1, 8),
                    "psi_operator": COGNITIVE_LAYERS.get(min(i + 1, 8), {}).get("psi", ""),
                    "palace_id": (i % 9) + 1,
                })

        return {
            "filters": {
                "S": [s_min, s_max], "T": [t_min, t_max], "P": [p_min, p_max],
                "cognitive_layer": target_layer,
            },
            "total_found": len(units),
            "units": units[:limit],
        }

    def _get_cognitive_topology(self, args: Dict) -> Dict:
        """获取认知拓扑结构"""
        # 尝试从真实模块注册表获取数据
        layer_distribution = {}
        psi_heatmap = {}
        try:
            from .module_registry import TENGOD_MODULES
            for mod in TENGOD_MODULES:
                layer = mod.get("consensus_layer", 1)
                layer_distribution[layer] = layer_distribution.get(layer, 0) + 1
                psi = mod.get("psi_operator", "unknown")
                psi_heatmap[psi] = psi_heatmap.get(psi, 0) + 1
        except Exception:
            layer_distribution = {i: i * 3 for i in range(1, 9)}
            psi_heatmap = {
                "EmbeddingProvider": 15, "Tortuosity": 8,
                "ZuowangAttention": 5, "PsiSelfRef": 3,
                "RecursionDepth": 3, "SpiritEvaluator": 2,
            }

        return {
            "layer_distribution": layer_distribution,
            "psi_heatmap": psi_heatmap,
            "total_modules": sum(layer_distribution.values()),
            "topology_description": (
                "TBCE八层认知架构，支持Ψ算子梯度传播，"
                "每层有独立的门禁阈值和自修正策略"
            ),
        }

    def _compute_geodesic(self, args: Dict) -> Dict:
        """计算两个认知单元在TBCE六维空间中的测地线距离"""
        c1 = [
            float(args["s1"]), float(args["t1"]), float(args["p1"]),
            float(args["c1"]), float(args["i1"]), float(args["e1"]),
        ]
        c2 = [
            float(args["s2"]), float(args["t2"]), float(args["p2"]),
            float(args["c2"]), float(args["i2"]), float(args["e2"]),
        ]

        # 欧几里得距离
        euclidean = math.sqrt(sum((a - b) ** 2 for a, b in zip(c1, c2)))

        # 测地线距离（考虑S-T类时方向）
        # dS² = -(dt)² + (ds)² + (dp)² + (dc)² + (di)² + (de)²
        dt = c1[1] - c2[1]  # T维度
        ds = c1[0] - c2[0]  # S维度
        spatial = sum((c1[i] - c2[i]) ** 2 for i in [2, 3, 4, 5])  # P, C, I, E
        temporal = ds**2 - dt**2  # 类时
        geodesic_sq = temporal + spatial
        geodesic = math.sqrt(abs(geodesic_sq))

        # 每维度距离
        dim_names = ["S(源)", "T(时)", "P(投影)", "C(图层)", "I(交织)", "E(边缘)"]
        per_dim = [
            {"dimension": name, "distance": round(abs(c1[i] - c2[i]), 4)}
            for i, name in enumerate(dim_names)
        ]

        return {
            "coordinates": {"unit1": c1, "unit2": c2},
            "euclidean_distance": round(euclidean, 4),
            "geodesic_distance": round(geodesic, 4),
            "per_dimension": per_dim,
            "is_timelike": geodesic_sq < 0,  # 类时间隔
            "is_spacelike": geodesic_sq > 0,  # 类空间隔
            "interpretation": (
                "类时间隔：两个单元之间存在因果联系"
                if geodesic_sq < 0
                else "类空间隔：两个单元之间无因果联系，可自由切片"
                if geodesic_sq > 0
                else "光锥面：两个单元处于因果边界"
            ),
        }

    # ── 维度解释 ──────────────────────────────────────────────────────

    def _interpret_s(self, s: float) -> str:
        if s >= 0.8: return "高度可信，事实基础牢固"
        if s >= 0.6: return "基本可信，存在一定不确定性"
        if s >= 0.4: return "可信度一般，建议交叉验证"
        return "可信度低，建议存疑"

    def _interpret_t(self, t: float) -> str:
        if t >= 5.0: return "近期信息，时效性强"
        if t >= 2.0: return "较新信息"
        if t >= 0.5: return "中等时效"
        return "较早信息，可能过时"

    def _interpret_p(self, p: float) -> str:
        if p >= 0.8: return "投影保真度高，结构保留完整"
        if p >= 0.6: return "投影保真度良好"
        if p >= 0.4: return "投影存在失真"
        return "投影严重失真，建议重新映射"

    def _interpret_c(self, c: float) -> str:
        if c >= 0.8: return "多模态语义高度一致"
        if c >= 0.6: return "多模态基本对齐"
        if c >= 0.4: return "多模态存在不一致"
        return "多模态严重冲突"

    def _interpret_i(self, i: float) -> str:
        if i >= 0.8: return "跨层通信稳定可靠"
        if i >= 0.6: return "跨层通信基本正常"
        if i >= 0.4: return "跨层通信存在丢包"
        return "跨层通信严重不稳定"

    def _interpret_e(self, e: float) -> str:
        if e >= 0.7: return "高度探索，接近认知边界"
        if e >= 0.4: return "适度探索"
        if e >= 0.2: return "保守探索"
        return "极度保守，缺乏探索"

    def _classify_structure(self, coords: TBCECoordinates) -> str:
        """分类拓扑结构类型"""
        if coords.I > 0.7 and coords.C > 0.7: return "grid"
        if coords.E > 0.6: return "chaos"
        if coords.P > 0.7: return "tree"
        if coords.S > 0.7: return "chain"
        return "cycle"

    # ── MCP 响应格式 ──────────────────────────────────────────────────

    def _success_response(self, data: Any) -> Dict:
        return {
            "content": [{"type": "text", "text": json.dumps(data, ensure_ascii=False, default=str)}],
            "isError": False,
        }

    def _error_response(self, message: str) -> Dict:
        return {
            "content": [{"type": "text", "text": json.dumps({"error": message}, ensure_ascii=False)}],
            "isError": True,
        }

    def _record_query(self, tool: str, args: Dict, result: Dict) -> None:
        self._query_history.append({
            "tool": tool,
            "args": {k: str(v)[:50] for k, v in args.items()},
            "timestamp": time.time(),
        })
        if len(self._query_history) > self._max_history:
            self._query_history = self._query_history[-self._max_history:]

    def get_server_info(self) -> Dict:
        return {
            "name": self.SERVER_NAME,
            "version": self.VERSION,
            "tool_count": len(MCP_COGNITIVE_TOOLS),
            "uptime_seconds": round(time.time() - self._start_time, 1),
        }


# ============================================================================
# 全局单例
# ============================================================================

_mcp_cognitive_server: Optional[MCPCognitiveServer] = None


def get_mcp_cognitive_server() -> MCPCognitiveServer:
    global _mcp_cognitive_server
    if _mcp_cognitive_server is None:
        _mcp_cognitive_server = MCPCognitiveServer()
    return _mcp_cognitive_server


def reset_mcp_cognitive_server() -> None:
    global _mcp_cognitive_server
    _mcp_cognitive_server = None


__all__ = [
    "MCPCognitiveServer",
    "MCP_COGNITIVE_TOOLS",
    "COGNITIVE_LAYERS",
    "get_mcp_cognitive_server",
    "reset_mcp_cognitive_server",
]