"""
dashboard.py — 门禁仪表盘与可视化数据 v4.6.0
===================================================
道曰："五色令人目盲，五音令人耳聋。"

门禁仪表盘：十二神状态可视化，TBCE六维雷达图数据。
为前端可视化提供结构化 JSON 数据，不依赖特定前端框架。

核心能力：
  - 十二神门禁状态仪表盘数据
  - TBCE六维雷达图数据
  - 五行生克矩阵热力图数据
  - 门禁通过率趋势图数据
  - 认知健康总览
  - 七论裁决分布数据
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
import math
import time

from .tbce_unit import GateState
from .twelve_gods_base import TwelveGods, FiveElements, GOD_ELEMENT_MAP


# ============================================================================
# 仪表盘数据模型
# ============================================================================

@dataclass
class DashboardData:
    """仪表盘完整数据"""
    timestamp: float = field(default_factory=time.time)
    health_overview: Dict[str, Any] = field(default_factory=dict)
    twelve_gods_status: List[Dict[str, Any]] = field(default_factory=list)
    tbce_radar: Dict[str, Any] = field(default_factory=dict)
    element_matrix: Dict[str, Any] = field(default_factory=dict)
    gate_trends: Dict[str, Any] = field(default_factory=dict)
    seven_theories: Dict[str, Any] = field(default_factory=dict)
    chaos_sea: Dict[str, Any] = field(default_factory=dict)
    alerts: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {
            "timestamp": self.timestamp,
            "health_overview": self.health_overview,
            "twelve_gods_status": self.twelve_gods_status,
            "tbce_radar": self.tbce_radar,
            "element_matrix": self.element_matrix,
            "gate_trends": self.gate_trends,
            "seven_theories": self.seven_theories,
            "chaos_sea": self.chaos_sea,
            "alerts": self.alerts,
        }


# ============================================================================
# 仪表盘生成器
# ============================================================================

class DashboardGenerator:
    """门禁仪表盘生成器 v2.34.0

    从认知指标采集器和门禁服务器中提取数据，
    生成结构化的仪表盘 JSON 数据。
    """

    VERSION = "2.34.0"

    def __init__(self):
        self._gate_history: List[Dict] = []
        self._unit_history: List[Dict] = []
        self._max_history = 500

    # ── 数据录入 ──────────────────────────────────────────────────────

    def record_gate_result(
        self,
        god_name: str,
        element: str,
        passed: bool,
        score: float,
        boost: float = 0.0,
        unit_id: str = "",
    ) -> None:
        """记录门禁裁决结果"""
        self._gate_history.append({
            "god_name": god_name,
            "element": element,
            "passed": passed,
            "score": score,
            "boost": boost,
            "unit_id": unit_id,
            "timestamp": time.time(),
        })
        if len(self._gate_history) > self._max_history:
            self._gate_history = self._gate_history[-self._max_history:]

    def record_unit_snapshot(
        self,
        unit_id: str,
        coords: List[float],
        layer: int,
        psi: str,
    ) -> None:
        """记录认知单元快照"""
        self._unit_history.append({
            "unit_id": unit_id,
            "coords": coords,
            "layer": layer,
            "psi": psi,
            "timestamp": time.time(),
        })
        if len(self._unit_history) > self._max_history:
            self._unit_history = self._unit_history[-self._max_history:]

    # ── 仪表盘数据生成 ──────────────────────────────────────────────

    def generate(self) -> DashboardData:
        """生成完整仪表盘数据"""
        data = DashboardData()

        data.health_overview = self._build_health_overview()
        data.twelve_gods_status = self._build_twelve_gods_status()
        data.tbce_radar = self._build_tbce_radar()
        data.element_matrix = self._build_element_matrix()
        data.gate_trends = self._build_gate_trends()
        data.seven_theories = self._build_seven_theories()
        data.chaos_sea = self._build_chaos_sea()
        data.alerts = self._detect_alerts()

        return data

    def generate_json(self) -> Dict:
        """生成 JSON 格式仪表盘数据"""
        return self.generate().to_dict()

    # ── 健康总览 ──────────────────────────────────────────────────────

    def _build_health_overview(self) -> Dict:
        """构建健康总览"""
        if not self._gate_history:
            return {
                "status": "no_data",
                "score": 0.0,
                "message": "尚无门禁数据",
                "uptime": 0,
                "total_judgments": 0,
            }

        total = len(self._gate_history)
        passed = sum(1 for r in self._gate_history if r["passed"])
        pass_rate = passed / total

        # 健康评分
        recent = self._gate_history[-50:]
        recent_pass_rate = sum(1 for r in recent if r["passed"]) / len(recent)

        score = (pass_rate * 0.6 + recent_pass_rate * 0.4)

        status = "healthy"
        if score < 0.4:
            status = "critical"
        elif score < 0.6:
            status = "warning"
        elif score < 0.8:
            status = "degraded"

        return {
            "status": status,
            "score": round(score, 3),
            "overall_pass_rate": round(pass_rate, 3),
            "recent_pass_rate": round(recent_pass_rate, 3),
            "total_judgments": total,
            "message": {
                "healthy": "十二神门禁运行正常，系统健康",
                "degraded": "部分门禁通过率下降，建议关注",
                "warning": "多个门禁触发警告，需要排查",
                "critical": "门禁系统严重异常，建议立即干预",
                "no_data": "尚无门禁数据",
            }.get(status, ""),
        }

    # ── 十二神状态 ────────────────────────────────────────────────────

    def _build_twelve_gods_status(self) -> List[Dict]:
        """构建十二神门禁状态列表"""
        status_list = []

        for god in TwelveGods:
            elem = GOD_ELEMENT_MAP.get(god, FiveElements.TRANSCENDENT).value

            # 统计该神位的裁决
            god_records = [r for r in self._gate_history if r["god_name"] == god.value]
            total = len(god_records)
            passed = sum(1 for r in god_records if r["passed"])
            avg_score = (sum(r["score"] for r in god_records) / total) if total > 0 else 0.0
            avg_boost = (sum(r["boost"] for r in god_records) / total) if total > 0 else 0.0

            # 状态
            if total == 0:
                gate_state = "unknown"
            elif passed / total >= 0.7:
                gate_state = "open"
            elif passed / total >= 0.4:
                gate_state = "pending"
            else:
                gate_state = "closed"

            status_list.append({
                "name": god.value,
                "element": elem,
                "state": gate_state,
                "total": total,
                "passed": passed,
                "pass_rate": round(passed / max(1, total), 3),
                "avg_score": round(avg_score, 4),
                "avg_element_boost": round(avg_boost, 4),
                "icon": self._get_god_icon(god),
                "color": self._get_element_color(elem),
            })

        return status_list

    # ── TBCE六维雷达图 ─────────────────────────────────────────────────

    def _build_tbce_radar(self) -> Dict:
        """构建TBCE六维雷达图数据"""
        if not self._unit_history:
            # 默认雷达图
            return {
                "labels": ["S(源)", "T(时)", "P(投影)", "C(图层)", "I(交织)", "E(边缘)"],
                "datasets": [{
                    "label": "全局平均",
                    "data": [0.5, 0.5, 0.5, 0.5, 0.5, 0.5],
                    "color": "#3B82F6",
                }],
                "max_value": 1.0,
                "description": "TBCE六维认知空间坐标分布",
            }

        # 按认知层分组
        layer_coords: Dict[int, List[List[float]]] = {}
        for unit in self._unit_history:
            layer = unit["layer"]
            if layer not in layer_coords:
                layer_coords[layer] = []
            layer_coords[layer].append(unit["coords"])

        dim_names = ["S(源)", "T(时)", "P(投影)", "C(图层)", "I(交织)", "E(边缘)"]
        colors = ["#3B82F6", "#EF4444", "#10B981", "#F59E0B", "#8B5CF6", "#EC4899", "#06B6D4", "#84CC16"]

        datasets = []
        # 全局平均
        all_coords = [u["coords"] for u in self._unit_history]
        global_avg = [sum(c[i] for c in all_coords) / len(all_coords) for i in range(6)]
        datasets.append({
            "label": "全局平均",
            "data": [round(v, 3) for v in global_avg],
            "color": "#3B82F6",
        })

        # 按认知层
        for layer, coords_list in sorted(layer_coords.items()):
            avg = [sum(c[i] for c in coords_list) / len(coords_list) for i in range(6)]
            datasets.append({
                "label": f"认知层 {layer}",
                "data": [round(v, 3) for v in avg],
                "color": colors[(layer - 1) % len(colors)],
            })

        return {
            "labels": dim_names,
            "datasets": datasets,
            "max_value": 1.0,
            "description": "TBCE六维认知空间坐标分布（按认知层区分）",
        }

    # ── 五行生克矩阵 ──────────────────────────────────────────────────

    def _build_element_matrix(self) -> Dict:
        """构建五行生克矩阵热力图数据"""
        elements = ["木", "火", "土", "金", "水", "太极"]

        # 统计每行元素的通过率
        elem_stats = {}
        for elem in elements:
            records = [r for r in self._gate_history if r["element"] == elem]
            total = len(records)
            passed = sum(1 for r in records if r["passed"])
            elem_stats[elem] = {
                "total": total,
                "passed": passed,
                "pass_rate": round(passed / max(1, total), 3),
            }

        # 生克关系矩阵
        generating_cycle = {"木": "火", "火": "土", "土": "金", "金": "水", "水": "木"}
        overcoming_cycle = {"木": "土", "土": "水", "水": "火", "火": "金", "金": "木"}

        matrix = []
        for row_elem in elements:
            row_data = []
            for col_elem in elements:
                if row_elem == col_elem:
                    relation = "self"
                    value = 0.5
                elif generating_cycle.get(row_elem) == col_elem:
                    relation = "generates"
                    value = 0.85
                elif overcoming_cycle.get(row_elem) == col_elem:
                    relation = "overcomes"
                    value = 0.15
                elif generating_cycle.get(col_elem) == row_elem:
                    relation = "generated_by"
                    value = 0.7
                elif overcoming_cycle.get(col_elem) == row_elem:
                    relation = "overcome_by"
                    value = 0.3
                else:
                    relation = "neutral"
                    value = 0.5

                row_data.append({
                    "row": row_elem,
                    "col": col_elem,
                    "relation": relation,
                    "value": value,
                })
            matrix.append(row_data)

        return {
            "elements": elements,
            "matrix": matrix,
            "element_stats": elem_stats,
            "generating_cycle": "木→火→土→金→水→木",
            "overcoming_cycle": "木→土→水→火→金→木",
        }

    # ── 门禁趋势 ──────────────────────────────────────────────────────

    def _build_gate_trends(self) -> Dict:
        """构建门禁通过率趋势图数据"""
        if len(self._gate_history) < 10:
            return {"labels": [], "datasets": []}

        window_size = max(10, len(self._gate_history) // 10)
        trend_data: Dict[str, List[float]] = {}

        for i in range(0, len(self._gate_history) - window_size + 1, max(1, window_size // 2)):
            window = self._gate_history[i:i + window_size]
            gate_counts: Dict[str, Dict] = {}

            for r in window:
                name = r["god_name"]
                if name not in gate_counts:
                    gate_counts[name] = {"total": 0, "passed": 0}
                gate_counts[name]["total"] += 1
                if r["passed"]:
                    gate_counts[name]["passed"] += 1

            for name, counts in gate_counts.items():
                if name not in trend_data:
                    trend_data[name] = []
                rate = counts["passed"] / counts["total"]
                trend_data[name].append(round(rate, 3))

        labels = [f"w{i+1}" for i in range(len(next(iter(trend_data.values()), [])))]

        colors = ["#3B82F6", "#EF4444", "#10B981", "#F59E0B", "#8B5CF6",
                   "#EC4899", "#06B6D4", "#84CC16", "#F97316", "#6366F1",
                   "#14B8A6", "#E11D48"]

        datasets = []
        for i, (name, values) in enumerate(trend_data.items()):
            datasets.append({
                "label": name,
                "data": values,
                "color": colors[i % len(colors)],
                "current": values[-1] if values else 0,
                "trend": "up" if len(values) >= 2 and values[-1] > values[-2]
                         else "down" if len(values) >= 2 and values[-1] < values[-2]
                         else "stable",
            })

        return {
            "labels": labels,
            "datasets": datasets,
            "window_size": window_size,
        }

    # ── 七论裁决分布 ──────────────────────────────────────────────────

    def _build_seven_theories(self) -> Dict:
        """构建七论裁决分布数据"""
        theories = [
            {"name": "本体论", "key": "ontology", "description": "所信即所是？"},
            {"name": "认识论", "key": "epistemology", "description": "所知即所信？"},
            {"name": "实践论", "key": "practice", "description": "所行即所知？"},
            {"name": "境界论", "key": "realm", "description": "所是即所行？"},
            {"name": "未来论", "key": "future", "description": "所趋即所是？"},
            {"name": "元认知", "key": "metacognition", "description": "所观即所趋？"},
            {"name": "混沌海", "key": "chaos_sea", "description": "所疑即所观？"},
        ]

        # 尝试获取实际七论数据
        theory_data = []
        try:
            from .seven_theories_judge import get_seven_theories_judge
            judge = get_seven_theories_judge()
            history = judge.get_verdict_history()
            if history:
                for t in theories:
                    t_records = [r for r in history if r.get("theory") == t["key"]]
                    passed = sum(1 for r in t_records if r.get("passed"))
                    total = len(t_records)
                    theory_data.append({
                        **t,
                        "total": total,
                        "passed": passed,
                        "pass_rate": round(passed / max(1, total), 3),
                    })
        except Exception:
            # 默认数据
            for t in theories:
                theory_data.append({
                    **t,
                    "total": 0,
                    "passed": 0,
                    "pass_rate": 0.0,
                })

        return {
            "theories": theory_data,
            "total_judgments": sum(t["total"] for t in theory_data),
            "overall_pass_rate": round(
                sum(t["passed"] for t in theory_data) /
                max(1, sum(t["total"] for t in theory_data)),
                3,
            ),
        }

    # ── 混沌海存疑 ────────────────────────────────────────────────────

    def _build_chaos_sea(self) -> Dict:
        """构建混沌海存疑汇总"""
        try:
            from .hundun_sea import HundunSea
            sea = HundunSea()
            trails = sea.get_trails(limit=20)
            return {
                "total_doubts": len(trails),
                "doubts": [
                    {
                        "route": t.get("route", ""),
                        "confidence": t.get("confidence", 0),
                        "features": t.get("features", {}),
                        "timestamp": t.get("timestamp", 0),
                    }
                    for t in trails
                ],
                "status": "active" if len(trails) > 0 else "clear",
            }
        except Exception:
            return {
                "total_doubts": 0,
                "doubts": [],
                "status": "clear",
            }

    # ── 告警检测 ──────────────────────────────────────────────────────

    def _detect_alerts(self) -> List[Dict]:
        """检测告警"""
        alerts = []

        if not self._gate_history:
            return alerts

        # 按门禁检查
        for god in TwelveGods:
            records = [r for r in self._gate_history[-20:] if r["god_name"] == god.value]
            if not records:
                continue

            passed = sum(1 for r in records if r["passed"])
            rate = passed / len(records)

            if rate < 0.3:
                alerts.append({
                    "level": "critical",
                    "god": god.value,
                    "message": f"{god.value}门禁最近20次通过率仅{rate:.0%}",
                    "pass_rate": round(rate, 3),
                })
            elif rate < 0.5:
                alerts.append({
                    "level": "warning",
                    "god": god.value,
                    "message": f"{god.value}门禁最近20次通过率偏低{rate:.0%}",
                    "pass_rate": round(rate, 3),
                })

        return alerts

    # ── 辅助方法 ──────────────────────────────────────────────────────

    def _get_god_icon(self, god: TwelveGods) -> str:
        """获取十二神图标符号"""
        icons = {
            TwelveGods.BIJIAN: "⚖️", TwelveGods.JIECAI: "🛡️",
            TwelveGods.SHISHEN: "✨", TwelveGods.SHANGGUAN: "⚡",
            TwelveGods.ZHENGCAI: "📚", TwelveGods.PIANCAI: "🎯",
            TwelveGods.ZHENGGUAN: "⚖️", TwelveGods.QISHA: "🔍",
            TwelveGods.ZHENGYIN: "🌿", TwelveGods.PIANYIN: "🔗",
            TwelveGods.TAIJI: "☯️", TwelveGods.YUANCHEN: "🔮",
        }
        return icons.get(god, "❓")

    def _get_element_color(self, element: str) -> str:
        """获取五行颜色"""
        colors = {
            "木": "#10B981", "火": "#EF4444", "土": "#F59E0B",
            "金": "#F8FAFC", "水": "#3B82F6", "太极": "#8B5CF6",
        }
        return colors.get(element, "#6B7280")

    def reset(self) -> None:
        """重置仪表盘数据"""
        self._gate_history.clear()
        self._unit_history.clear()


# ============================================================================
# 全局单例
# ============================================================================

_dashboard_generator: Optional[DashboardGenerator] = None


def get_dashboard_generator() -> DashboardGenerator:
    global _dashboard_generator
    if _dashboard_generator is None:
        _dashboard_generator = DashboardGenerator()
    return _dashboard_generator


def reset_dashboard_generator() -> None:
    global _dashboard_generator
    _dashboard_generator = None


__all__ = [
    "DashboardData",
    "DashboardGenerator",
    "get_dashboard_generator",
    "reset_dashboard_generator",
]