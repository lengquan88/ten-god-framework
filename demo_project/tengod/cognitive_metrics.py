"""
cognitive_metrics.py — 认知指标采集器 v4.6.0
=================================================
道曰："知人者智，自知者明。"

企业级认知指标采集，在现有 metrics_collector 基础上扩展：
  - 认知指标采集：TBCE多维坐标统计、认知层覆盖率
  - TBCE坐标漂移监控：检测认知单元在推理过程中的坐标变化
  - 十二神门禁通过率统计：每个门禁的裁决历史与趋势
  - 认知健康仪表盘数据：为可视化提供结构化数据
  - 推测解码加速比统计
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
import threading
import time
import math


# ============================================================================
# 认知指标数据结构
# ============================================================================

@dataclass
class TBCEDriftRecord:
    """TBCE坐标漂移记录"""
    unit_id: str
    unit_name: str
    coords_before: List[float]  # 漂移前坐标 [S, T, P, C, I, E]
    coords_after: List[float]   # 漂移后坐标
    drift_distance: float       # 欧几里得漂移距离
    drift_per_dimension: List[float]  # 每维漂移量
    timestamp: float = field(default_factory=time.time)
    trigger: str = ""           # 触发原因（门禁裁决/自修正/成像等）

    @property
    def is_warning(self) -> bool:
        """漂移是否达到警告级别 (>0.3)"""
        return self.drift_distance > 0.3

    @property
    def is_critical(self) -> bool:
        """漂移是否达到严重级别 (>0.5)"""
        return self.drift_distance > 0.5

    def to_dict(self) -> Dict:
        return {
            "unit_id": self.unit_id,
            "unit_name": self.unit_name,
            "coords_before": [round(c, 4) for c in self.coords_before],
            "coords_after": [round(c, 4) for c in self.coords_after],
            "drift_distance": round(self.drift_distance, 4),
            "drift_per_dim": [round(d, 4) for d in self.drift_per_dimension],
            "is_warning": self.is_warning,
            "is_critical": self.is_critical,
            "trigger": self.trigger,
            "timestamp": self.timestamp,
        }


@dataclass
class GatePassRecord:
    """门禁通过记录"""
    gate_name: str          # 门禁名称（如"比肩·劫财"）
    god_name: str           # 十二神名称
    element: str            # 五行
    passed: bool            # 是否通过
    score: float            # 裁决分数
    element_boost: float    # 五行生克加成
    reason: str             # 裁决理由
    timestamp: float = field(default_factory=time.time)
    unit_id: str = ""

    def to_dict(self) -> Dict:
        return {
            "gate_name": self.gate_name,
            "god_name": self.god_name,
            "element": self.element,
            "passed": self.passed,
            "score": round(self.score, 4),
            "element_boost": round(self.element_boost, 4),
            "reason": self.reason[:100],
            "timestamp": self.timestamp,
            "unit_id": self.unit_id,
        }


@dataclass
class CognitiveSnapshot:
    """认知系统快照"""
    timestamp: float = field(default_factory=time.time)
    # TBCE统计
    tbce_mean: List[float] = field(default_factory=lambda: [0.0] * 6)
    tbce_std: List[float] = field(default_factory=lambda: [0.0] * 6)
    tbce_unit_count: int = 0
    # 漂移统计
    drift_count: int = 0
    drift_warning_count: int = 0
    drift_critical_count: int = 0
    drift_mean: float = 0.0
    # 门禁统计
    gate_total: int = 0
    gate_passed: int = 0
    gate_failed: int = 0
    gate_pass_rate: float = 0.0
    # 推理统计
    inference_count: int = 0
    inference_avg_duration_ms: float = 0.0
    speculation_hit_rate: float = 0.0  # 推测解码命中率
    # 自修正统计
    correction_count: int = 0
    correction_success_rate: float = 0.0
    chaos_sea_entries: int = 0

    def to_dict(self) -> Dict:
        return {
            "timestamp": self.timestamp,
            "tbce": {
                "mean": [round(c, 4) for c in self.tbce_mean],
                "std": [round(c, 4) for c in self.tbce_std],
                "unit_count": self.tbce_unit_count,
            },
            "drift": {
                "total": self.drift_count,
                "warnings": self.drift_warning_count,
                "critical": self.drift_critical_count,
                "mean_distance": round(self.drift_mean, 4),
            },
            "gates": {
                "total": self.gate_total,
                "passed": self.gate_passed,
                "failed": self.gate_failed,
                "pass_rate": round(self.gate_pass_rate, 4),
            },
            "inference": {
                "count": self.inference_count,
                "avg_duration_ms": round(self.inference_avg_duration_ms, 1),
                "speculation_hit_rate": round(self.speculation_hit_rate, 4),
            },
            "correction": {
                "count": self.correction_count,
                "success_rate": round(self.correction_success_rate, 4),
                "chaos_sea_entries": self.chaos_sea_entries,
            },
        }


# ============================================================================
# 认知指标采集器
# ============================================================================

class CognitiveMetricsCollector:
    """认知指标采集器 v2.32.0

    企业级认知指标采集，包括：
    - TBCE坐标漂移监控
    - 十二神门禁通过率统计
    - 认知层覆盖率
    - 推测解码命中率
    - 认知健康仪表盘数据
    """

    _instance: Optional["CognitiveMetricsCollector"] = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True

        # TBCE坐标漂移记录
        self._drift_records: List[TBCEDriftRecord] = []
        self._max_drift_records: int = 1000

        # 门禁通过记录
        self._gate_records: List[GatePassRecord] = []
        self._max_gate_records: int = 2000

        # 推理统计
        self._inference_durations: List[float] = []
        self._max_inference_records: int = 500

        # 推测解码统计
        self._speculation_hits: int = 0
        self._speculation_total: int = 0

        # 自修正统计
        self._correction_success_count: int = 0
        self._correction_total_count: int = 0
        self._chaos_sea_entry_count: int = 0

        # 认知层覆盖
        self._layer_unit_counts: Dict[int, int] = {}

        # 历史快照
        self._snapshots: List[CognitiveSnapshot] = []
        self._max_snapshots: int = 100

    # ── TBCE坐标漂移监控 ──────────────────────────────────────────────

    def record_tbce_drift(
        self,
        unit_id: str,
        unit_name: str,
        coords_before: List[float],
        coords_after: List[float],
        trigger: str = "",
    ) -> TBCEDriftRecord:
        """记录TBCE坐标漂移

        Args:
            unit_id: 认知单元ID
            unit_name: 认知单元名称
            coords_before: 漂移前坐标 [S, T, P, C, I, E]
            coords_after: 漂移后坐标
            trigger: 触发原因

        Returns:
            TBCEDriftRecord
        """
        # 计算欧几里得漂移距离
        drift_distance = math.sqrt(
            sum((a - b) ** 2 for a, b in zip(coords_after, coords_before))
        )
        drift_per_dim = [abs(a - b) for a, b in zip(coords_after, coords_before)]

        record = TBCEDriftRecord(
            unit_id=unit_id,
            unit_name=unit_name,
            coords_before=list(coords_before),
            coords_after=list(coords_after),
            drift_distance=drift_distance,
            drift_per_dimension=drift_per_dim,
            trigger=trigger,
        )

        self._drift_records.append(record)
        if len(self._drift_records) > self._max_drift_records:
            self._drift_records = self._drift_records[-self._max_drift_records:]

        return record

    def check_drift_alerts(self) -> List[Dict]:
        """检查TBCE漂移告警

        Returns:
            告警列表
        """
        alerts = []
        recent = self._drift_records[-50:]

        # 检查最近的严重漂移
        critical_drifts = [r for r in recent if r.is_critical]
        if critical_drifts:
            alerts.append({
                "level": "critical",
                "type": "tbce_drift",
                "message": f"检测到 {len(critical_drifts)} 次严重TBCE坐标漂移",
                "max_drift": max(r.drift_distance for r in critical_drifts),
                "affected_units": list(set(r.unit_name for r in critical_drifts)),
            })

        # 检查警告漂移趋势
        warning_drifts = [r for r in recent if r.is_warning]
        if len(warning_drifts) > 10:
            alerts.append({
                "level": "warning",
                "type": "tbce_drift_trend",
                "message": f"最近50次漂移中有 {len(warning_drifts)} 次警告级别",
                "trend": "increasing" if len(warning_drifts) > 25 else "stable",
            })

        # 检查单维度漂移
        if recent:
            dim_names = ["S(源)", "T(时)", "P(投影)", "C(图层)", "I(交织)", "E(边缘)"]
            for i, name in enumerate(dim_names):
                dim_drifts = [r.drift_per_dimension[i] for r in recent]
                avg_dim_drift = sum(dim_drifts) / len(dim_drifts)
                if avg_dim_drift > 0.2:
                    alerts.append({
                        "level": "warning",
                        "type": "dimension_drift",
                        "message": f"维度 {name} 平均漂移 {avg_dim_drift:.3f}，超过阈值",
                        "dimension": name,
                        "avg_drift": round(avg_dim_drift, 4),
                    })

        return alerts

    def get_drift_stats(self) -> Dict[str, Any]:
        """获取漂移统计"""
        total = len(self._drift_records)
        if total == 0:
            return {"total": 0}

        warnings = sum(1 for r in self._drift_records if r.is_warning)
        criticals = sum(1 for r in self._drift_records if r.is_critical)
        mean_drift = sum(r.drift_distance for r in self._drift_records) / total

        # 每维度平均漂移
        dim_names = ["S", "T", "P", "C", "I", "E"]
        dim_avgs = {}
        for i, name in enumerate(dim_names):
            dim_drifts = [r.drift_per_dimension[i] for r in self._drift_records]
            dim_avgs[name] = round(sum(dim_drifts) / total, 4)

        return {
            "total": total,
            "warnings": warnings,
            "critical": criticals,
            "warning_rate": round(warnings / total, 3),
            "critical_rate": round(criticals / total, 3),
            "mean_drift": round(mean_drift, 4),
            "max_drift": round(max(r.drift_distance for r in self._drift_records), 4),
            "by_dimension": dim_avgs,
        }

    # ── 门禁通过率统计 ─────────────────────────────────────────────────

    def record_gate_pass(
        self,
        gate_name: str,
        god_name: str,
        element: str,
        passed: bool,
        score: float,
        element_boost: float = 0.0,
        reason: str = "",
        unit_id: str = "",
    ) -> GatePassRecord:
        """记录门禁通过裁决

        Args:
            gate_name: 门禁名称
            god_name: 十二神名称
            element: 五行
            passed: 是否通过
            score: 分数
            element_boost: 五行生克加成
            reason: 裁决理由
            unit_id: 认知单元ID

        Returns:
            GatePassRecord
        """
        record = GatePassRecord(
            gate_name=gate_name,
            god_name=god_name,
            element=element,
            passed=passed,
            score=score,
            element_boost=element_boost,
            reason=reason,
            unit_id=unit_id,
        )

        self._gate_records.append(record)
        if len(self._gate_records) > self._max_gate_records:
            self._gate_records = self._gate_records[-self._max_gate_records:]

        return record

    def record_gate_verdict(
        self,
        verdict: Any,
        unit_id: str = "",
    ) -> GatePassRecord:
        """从门禁裁决对象记录门禁通过"""
        try:
            gate_name = getattr(verdict, 'gate_name', 'unknown')
            god_name = getattr(verdict, 'god_name', 'unknown')
            element = getattr(verdict, 'element', '未知')
            passed = getattr(verdict, 'passed', False)
            score = getattr(verdict, 'score', 0.0)
            element_boost = getattr(verdict, 'element_boost', 0.0)
            reason = getattr(verdict, 'reason', '')
        except Exception:
            return GatePassRecord(
                gate_name="unknown",
                god_name="unknown",
                element="未知",
                passed=False,
                score=0.0,
                unit_id=unit_id,
            )

        return self.record_gate_pass(
            gate_name=gate_name,
            god_name=god_name,
            element=element,
            passed=passed,
            score=score,
            element_boost=element_boost,
            reason=reason,
            unit_id=unit_id,
        )

    def get_gate_stats(self) -> Dict[str, Any]:
        """获取门禁统计"""
        total = len(self._gate_records)
        if total == 0:
            return {"total": 0}

        passed = sum(1 for r in self._gate_records if r.passed)

        # 按门禁分组
        by_gate: Dict[str, Dict] = {}
        for r in self._gate_records:
            if r.gate_name not in by_gate:
                by_gate[r.gate_name] = {
                    "total": 0, "passed": 0, "scores": [], "boosts": [],
                    "element": r.element, "god_name": r.god_name,
                }
            by_gate[r.gate_name]["total"] += 1
            if r.passed:
                by_gate[r.gate_name]["passed"] += 1
            by_gate[r.gate_name]["scores"].append(r.score)
            by_gate[r.gate_name]["boosts"].append(r.element_boost)

        gate_details = {}
        for name, stats in by_gate.items():
            scores = stats["scores"]
            boosts = stats["boosts"]
            gate_details[name] = {
                "god_name": stats["god_name"],
                "element": stats["element"],
                "total": stats["total"],
                "passed": stats["passed"],
                "pass_rate": round(stats["passed"] / stats["total"], 3),
                "avg_score": round(sum(scores) / len(scores), 4),
                "min_score": round(min(scores), 4),
                "max_score": round(max(scores), 4),
                "avg_element_boost": round(sum(boosts) / len(boosts), 4),
            }

        # 按五行分组
        by_element: Dict[str, Dict] = {}
        for r in self._gate_records:
            elem = r.element
            if elem not in by_element:
                by_element[elem] = {"total": 0, "passed": 0}
            by_element[elem]["total"] += 1
            if r.passed:
                by_element[elem]["passed"] += 1

        element_stats = {}
        for elem, stats in by_element.items():
            element_stats[elem] = {
                "total": stats["total"],
                "passed": stats["passed"],
                "pass_rate": round(stats["passed"] / stats["total"], 3),
            }

        return {
            "total": total,
            "passed": passed,
            "failed": total - passed,
            "overall_pass_rate": round(passed / total, 3),
            "by_gate": gate_details,
            "by_element": element_stats,
        }

    def get_gate_trend(self, window_size: int = 20) -> Dict[str, List[float]]:
        """获取门禁通过率趋势

        Args:
            window_size: 滑动窗口大小

        Returns:
            {gate_name: [pass_rate, ...]}
        """
        if len(self._gate_records) < window_size:
            return {}

        trends: Dict[str, List[float]] = {}
        for i in range(0, len(self._gate_records) - window_size + 1, window_size // 2):
            window = self._gate_records[i:i + window_size]
            gate_counts: Dict[str, Dict] = {}
            for r in window:
                if r.gate_name not in gate_counts:
                    gate_counts[r.gate_name] = {"total": 0, "passed": 0}
                gate_counts[r.gate_name]["total"] += 1
                if r.passed:
                    gate_counts[r.gate_name]["passed"] += 1

            for name, counts in gate_counts.items():
                if name not in trends:
                    trends[name] = []
                rate = counts["passed"] / counts["total"]
                trends[name].append(round(rate, 3))

        return trends

    # ── 推理统计 ──────────────────────────────────────────────────────

    def record_inference(self, duration_ms: float) -> None:
        """记录推理耗时"""
        self._inference_durations.append(duration_ms)
        if len(self._inference_durations) > self._max_inference_records:
            self._inference_durations = self._inference_durations[-self._max_inference_records:]

    def record_speculation(self, hit: bool) -> None:
        """记录推测解码命中"""
        self._speculation_total += 1
        if hit:
            self._speculation_hits += 1

    def get_speculation_stats(self) -> Dict[str, Any]:
        """获取推测解码统计"""
        return {
            "total": self._speculation_total,
            "hits": self._speculation_hits,
            "hit_rate": round(
                self._speculation_hits / max(1, self._speculation_total), 4
            ),
            "speedup_estimate": round(
                1.0 / (1.0 - self._speculation_hits / max(1, self._speculation_total))
                if self._speculation_hits > 0 else 1.0, 2
            ),
        }

    def get_inference_stats(self) -> Dict[str, Any]:
        """获取推理统计"""
        if not self._inference_durations:
            return {"count": 0}

        durations = self._inference_durations
        n = len(durations)
        mean = sum(durations) / n
        variance = sum((d - mean) ** 2 for d in durations) / n

        sorted_durations = sorted(durations)
        p50 = sorted_durations[n // 2]
        p95 = sorted_durations[int(n * 0.95)]
        p99 = sorted_durations[int(n * 0.99)]

        return {
            "count": n,
            "mean_ms": round(mean, 1),
            "std_ms": round(math.sqrt(variance), 1),
            "min_ms": round(min(durations), 1),
            "max_ms": round(max(durations), 1),
            "p50_ms": round(p50, 1),
            "p95_ms": round(p95, 1),
            "p99_ms": round(p99, 1),
        }

    # ── 自修正统计 ────────────────────────────────────────────────────

    def record_correction(self, success: bool) -> None:
        """记录自修正结果"""
        self._correction_total_count += 1
        if success:
            self._correction_success_count += 1

    def record_chaos_sea_entry(self) -> None:
        """记录混沌海存疑"""
        self._chaos_sea_entry_count += 1

    def get_correction_stats(self) -> Dict[str, Any]:
        """获取自修正统计"""
        return {
            "total": self._correction_total_count,
            "success": self._correction_success_count,
            "success_rate": round(
                self._correction_success_count / max(1, self._correction_total_count), 3
            ),
            "chaos_sea_entries": self._chaos_sea_entry_count,
        }

    # ── 认知层覆盖 ────────────────────────────────────────────────────

    def update_layer_coverage(self, layer_unit_counts: Dict[int, int]) -> None:
        """更新认知层覆盖统计"""
        self._layer_unit_counts = dict(layer_unit_counts)

    def get_layer_coverage(self) -> Dict[int, int]:
        """获取认知层覆盖"""
        return dict(self._layer_unit_counts)

    # ── 认知快照 ──────────────────────────────────────────────────────

    def take_snapshot(self) -> CognitiveSnapshot:
        """采集认知系统快照"""
        snap = CognitiveSnapshot()

        # TBCE统计
        if self._drift_records:
            recent_drifts = self._drift_records[-100:]
            n = len(recent_drifts)
            dim_names = 6
            for i in range(dim_names):
                coords = [r.coords_after[i] for r in recent_drifts]
                snap.tbce_mean[i] = sum(coords) / n
                mean = snap.tbce_mean[i]
                snap.tbce_std[i] = math.sqrt(
                    sum((c - mean) ** 2 for c in coords) / n
                )

        snap.tbce_unit_count = len(set(
            r.unit_id for r in self._drift_records[-100:]
        )) if self._drift_records else 0

        # 漂移统计
        snap.drift_count = len(self._drift_records)
        snap.drift_warning_count = sum(1 for r in self._drift_records if r.is_warning)
        snap.drift_critical_count = sum(1 for r in self._drift_records if r.is_critical)
        snap.drift_mean = (
            sum(r.drift_distance for r in self._drift_records) / snap.drift_count
            if snap.drift_count > 0 else 0.0
        )

        # 门禁统计
        snap.gate_total = len(self._gate_records)
        snap.gate_passed = sum(1 for r in self._gate_records if r.passed)
        snap.gate_failed = snap.gate_total - snap.gate_passed
        snap.gate_pass_rate = (
            snap.gate_passed / snap.gate_total if snap.gate_total > 0 else 0.0
        )

        # 推理统计
        snap.inference_count = len(self._inference_durations)
        snap.inference_avg_duration_ms = (
            sum(self._inference_durations) / snap.inference_count
            if snap.inference_count > 0 else 0.0
        )
        snap.speculation_hit_rate = (
            self._speculation_hits / max(1, self._speculation_total)
        )

        # 自修正统计
        snap.correction_count = self._correction_total_count
        snap.correction_success_rate = (
            self._correction_success_count / max(1, self._correction_total_count)
        )
        snap.chaos_sea_entries = self._chaos_sea_entry_count

        self._snapshots.append(snap)
        if len(self._snapshots) > self._max_snapshots:
            self._snapshots = self._snapshots[-self._max_snapshots:]

        return snap

    def get_latest_snapshot(self) -> Optional[Dict]:
        """获取最新认知快照"""
        if not self._snapshots:
            return None
        return self._snapshots[-1].to_dict()

    def get_snapshot_history(self, limit: int = 20) -> List[Dict]:
        """获取快照历史"""
        return [s.to_dict() for s in self._snapshots[-limit:]]

    # ── 认知健康仪表盘数据 ────────────────────────────────────────────

    def get_dashboard_data(self) -> Dict[str, Any]:
        """获取认知健康仪表盘数据

        为可视化仪表盘提供结构化数据。
        """
        snap = self.get_latest_snapshot() or {}
        gate_stats = self.get_gate_stats()
        drift_stats = self.get_drift_stats()
        inference_stats = self.get_inference_stats()
        correction_stats = self.get_correction_stats()
        speculation_stats = self.get_speculation_stats()
        drift_alerts = self.check_drift_alerts()

        return {
            "timestamp": time.time(),
            "overall_health": self._compute_health_score(),
            "snapshot": snap,
            "gates": gate_stats,
            "drift": drift_stats,
            "inference": inference_stats,
            "correction": correction_stats,
            "speculation": speculation_stats,
            "alerts": drift_alerts,
            "layer_coverage": self.get_layer_coverage(),
        }

    def _compute_health_score(self) -> float:
        """计算综合认知健康分数 (0-1)"""
        scores = []

        # 门禁通过率 (权重 0.3)
        gate_stats = self.get_gate_stats()
        if gate_stats.get("total", 0) > 0:
            scores.append((gate_stats["overall_pass_rate"], 0.3))

        # 漂移严重度 (权重 0.25)
        drift_stats = self.get_drift_stats()
        if drift_stats.get("total", 0) > 0:
            drift_severity = 1.0 - min(1.0, drift_stats["critical_rate"] * 2)
            scores.append((drift_severity, 0.25))

        # 自修正成功率 (权重 0.2)
        correction_stats = self.get_correction_stats()
        if correction_stats.get("total", 0) > 0:
            scores.append((correction_stats["success_rate"], 0.2))

        # 推测解码命中率 (权重 0.15)
        spec_stats = self.get_speculation_stats()
        if spec_stats.get("total", 0) > 0:
            scores.append((spec_stats["hit_rate"], 0.15))

        # 推理延迟 (权重 0.1)
        inference_stats = self.get_inference_stats()
        if inference_stats.get("count", 0) > 0:
            # 延迟越低越好，1000ms以内为满分
            latency_score = max(0.0, 1.0 - inference_stats["p95_ms"] / 1000.0)
            scores.append((latency_score, 0.1))

        if not scores:
            return 1.0

        total_weight = sum(w for _, w in scores)
        if total_weight == 0:
            return 1.0

        return round(sum(s * w for s, w in scores) / total_weight, 4)

    def get_health_status(self) -> Dict[str, Any]:
        """获取认知健康状态"""
        score = self._compute_health_score()

        if score >= 0.8:
            status = "healthy"
        elif score >= 0.6:
            status = "warning"
        elif score >= 0.4:
            status = "degraded"
        else:
            status = "critical"

        return {
            "status": status,
            "score": score,
            "gates": self.get_gate_stats(),
            "drift": self.get_drift_stats(),
            "alerts": self.check_drift_alerts(),
        }

    # ── 重置 ──────────────────────────────────────────────────────────

    def reset(self) -> None:
        """重置所有指标"""
        self._drift_records.clear()
        self._gate_records.clear()
        self._inference_durations.clear()
        self._speculation_hits = 0
        self._speculation_total = 0
        self._correction_success_count = 0
        self._correction_total_count = 0
        self._chaos_sea_entry_count = 0
        self._layer_unit_counts.clear()
        self._snapshots.clear()


# ============================================================================
# 全局单例
# ============================================================================

_cognitive_metrics: Optional[CognitiveMetricsCollector] = None


def get_cognitive_metrics() -> CognitiveMetricsCollector:
    """获取认知指标采集器单例"""
    global _cognitive_metrics
    if _cognitive_metrics is None:
        _cognitive_metrics = CognitiveMetricsCollector()
    return _cognitive_metrics


def reset_cognitive_metrics() -> None:
    """重置认知指标采集器"""
    global _cognitive_metrics
    _cognitive_metrics = None
    CognitiveMetricsCollector._instance = None


__all__ = [
    "TBCEDriftRecord",
    "GatePassRecord",
    "CognitiveSnapshot",
    "CognitiveMetricsCollector",
    "get_cognitive_metrics",
    "reset_cognitive_metrics",
]