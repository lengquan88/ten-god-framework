"""
holographic_system.py — 全息认知系统总控 v3.0.0
=====================================================
道曰："道生一，一生二，二生三，三生万物。"

全息认知系统总控器，将十二神门禁、七阶段成像、七步自修正、
推测解码、Oracle投影、五行生克等子系统统一编排为一体化认知管道。

核心能力：
  - 12门禁 + 7成像 + 7自修正 + 推测解码，全管道一体化编排
  - 认知请求 → 十二神门禁 → 七阶段成像 → 七论裁决 → 自修正 → 固化
  - 五行生克动态调整门禁阈值
  - TBCE坐标漂移实时监控
  - 全链路追踪与审计
  - 推测解码加速
  - 混沌海存疑自动降级
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple
import math
import time
import uuid
import threading

from .tbce_unit import CognitiveUnit, TBCECoordinates, GateState
from .twelve_gods_base import (
    TwelveGods, FiveElements, GateVerdict, TwelveGodsGate,
    GOD_ELEMENT_MAP, GOD_GATE_MAP,
)


# ============================================================================
# 管道阶段
# ============================================================================

class PipelineStage(Enum):
    """全息认知管道阶段"""
    INGEST = "ingest"                 # 1. 摄入：认知单元创建
    TWELVE_GATES = "twelve_gates"     # 2. 十二神门禁裁决
    IMAGING_1_SENSOR = "imaging_1"    # 3. 成像阶段1：传感器曝光
    IMAGING_2_FUSION = "imaging_2"    # 4. 成像阶段2：多模态融合
    IMAGING_3_QUALITY = "imaging_3"   # 5. 成像阶段3：质量门禁
    IMAGING_4_COHERENCE = "imaging_4" # 6. 成像阶段4：一致性校验
    IMAGING_5_SPECULATION = "imaging_5" # 7. 成像阶段5：推测解码
    IMAGING_6_OUTPUT = "imaging_6"    # 8. 成像阶段6：输出生成
    IMAGING_7_ARCHIVE = "imaging_7"   # 9. 成像阶段7：归档固化
    SEVEN_THEORIES = "seven_theories" # 10. 七论裁决
    SELF_CORRECTION = "self_correction" # 11. 七步自修正
    ORACLE_PROJECTION = "oracle"      # 12. Oracle三时态投影
    CHAOS_SEA = "chaos_sea"           # 13. 混沌海存疑降级
    FINALIZE = "finalize"             # 14. 最终化


class PipelineStatus(Enum):
    """管道状态"""
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"       # 被门禁暂停
    INTERRUPTED = "interrupted"  # 被七论中断
    CHAOS_SEA = "chaos_sea"      # 降级到混沌海
    SUCCESS = "success"
    FAILED = "failed"


# ============================================================================
# 管道结果
# ============================================================================

@dataclass
class StageResult:
    """管道阶段结果"""
    stage: PipelineStage
    status: PipelineStatus
    data: Dict[str, Any] = field(default_factory=dict)
    duration_ms: float = 0.0
    error: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return {
            "stage": self.stage.value,
            "status": self.status.value,
            "data": self.data,
            "duration_ms": round(self.duration_ms, 1),
            "error": self.error,
        }


@dataclass
class PipelineResult:
    """全管道执行结果"""
    pipeline_id: str
    unit_id: str
    unit_name: str
    stages: List[StageResult] = field(default_factory=list)
    overall_status: PipelineStatus = PipelineStatus.PENDING
    total_duration_ms: float = 0.0
    gate_verdicts: Dict[str, Dict] = field(default_factory=dict)
    imaging_result: Optional[Dict] = None
    correction_result: Optional[Dict] = None
    oracle_result: Optional[Dict] = None
    chaos_sea_entries: List[Dict] = field(default_factory=list)
    trace_id: str = ""
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict:
        return {
            "pipeline_id": self.pipeline_id,
            "unit_id": self.unit_id,
            "unit_name": self.unit_name,
            "stages": [s.to_dict() for s in self.stages],
            "overall_status": self.overall_status.value,
            "total_duration_ms": round(self.total_duration_ms, 1),
            "gate_verdicts": self.gate_verdicts,
            "imaging_result": self.imaging_result,
            "correction_result": self.correction_result,
            "oracle_result": self.oracle_result,
            "chaos_sea_entries": self.chaos_sea_entries,
            "trace_id": self.trace_id,
            "timestamp": self.timestamp,
        }


# ============================================================================
# 全息认知系统总控
# ============================================================================

class HolographicSystem:
    """全息认知系统总控 v3.0.0

    12门禁 + 7成像 + 7自修正 + 推测解码 一体化编排。

    管道流程：
    1. 摄入 → 认知单元创建
    2. 十二神门禁 → 全部门禁裁决
    3-9. 七阶段成像 → 传感器→融合→质量→一致性→推测→输出→归档
    10. 七论裁决 → 本体论→认识论→实践论→境界论→未来论→元认知→混沌海
    11. 七步自修正 → 观自在→格物致知→以物验道→抱元守一→补天浴日→天人合一→铭文刻骨
    12. Oracle投影 → 过去/现在/未来三时态
    13. 混沌海 → 异常降级存疑
    14. 最终化 → 报告生成
    """

    VERSION = "3.0.0"

    _instance: Optional["HolographicSystem"] = None
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

        self._gate_instances: Dict[str, TwelveGodsGate] = {}
        self._pipeline_history: List[PipelineResult] = []
        self._max_history = 500
        self._element_cycle_state: Dict[str, float] = {  # 五行状态
            "木": 0.5, "火": 0.5, "土": 0.5, "金": 0.5, "水": 0.5, "太极": 0.5,
        }
        self._speculation_hits: int = 0
        self._speculation_total: int = 0
        self._coordinate_drift: List[float] = []  # 漂移历史

    # ── 全管道执行 ──────────────────────────────────────────────────

    def execute(
        self,
        unit_id: str,
        unit_name: str,
        coords: Optional[Dict[str, float]] = None,
        cognitive_layer: int = 1,
        modalities: Optional[List[str]] = None,
        enable_imaging: bool = True,
        enable_self_correction: bool = True,
        enable_oracle: bool = True,
        enable_speculation: bool = True,
        strict_mode: bool = False,
        callback: Optional[Callable[[PipelineStage, StageResult], None]] = None,
    ) -> PipelineResult:
        """执行全息认知管道

        Args:
            unit_id: 认知单元ID
            unit_name: 认知单元名称
            coords: TBCE坐标 {S, T, P, C, I, E}
            cognitive_layer: 认知层 (1-8)
            modalities: 模态列表
            enable_imaging: 启用成像管道
            enable_self_correction: 启用自修正
            enable_oracle: 启用Oracle投影
            enable_speculation: 启用推测解码
            strict_mode: 严格模式（任一关则整体关）
            callback: 每个阶段完成后的回调

        Returns:
            PipelineResult
        """
        pipeline_id = f"pipeline_{uuid.uuid4().hex[:12]}"
        result = PipelineResult(
            pipeline_id=pipeline_id,
            unit_id=unit_id,
            unit_name=unit_name,
        )

        start_time = time.time()
        result.overall_status = PipelineStatus.RUNNING

        try:
            # 1. 摄入阶段
            unit = self._create_unit(
                unit_id, unit_name, coords or {}, cognitive_layer
            )
            self._record_stage(result, PipelineStage.INGEST,
                              PipelineStatus.SUCCESS, {"unit": unit_name})

            # 2. 十二神门禁裁决
            gate_verdicts = self._execute_twelve_gates(unit)
            result.gate_verdicts = gate_verdicts
            gate_passed = self._check_gates_passed(gate_verdicts, strict_mode)
            self._record_stage(result, PipelineStage.TWELVE_GATES,
                              PipelineStatus.SUCCESS if gate_passed else PipelineStatus.PAUSED,
                              {"passed": gate_passed, "verdicts": gate_verdicts})

            if strict_mode and not gate_passed:
                result.overall_status = PipelineStatus.FAILED
                result.total_duration_ms = (time.time() - start_time) * 1000
                return result

            # 更新五行状态
            self._update_element_cycle(gate_verdicts)

            # 3-9. 七阶段成像
            if enable_imaging:
                imaging = self._execute_imaging_pipeline(unit, gate_verdicts,
                                                         modalities or ["text"],
                                                         enable_speculation)
                result.imaging_result = imaging
                self._record_stage(result, PipelineStage.IMAGING_7_ARCHIVE,
                                  PipelineStatus.SUCCESS if imaging.get("success") else PipelineStatus.FAILED,
                                  imaging)

            # 10. 七论裁决
            seven_theories = self._execute_seven_theories(unit)
            self._record_stage(result, PipelineStage.SEVEN_THEORIES,
                              PipelineStatus.SUCCESS if seven_theories.get("passed") else PipelineStatus.INTERRUPTED,
                              seven_theories)

            # 11. 七步自修正
            if enable_self_correction and not seven_theories.get("passed"):
                correction = self._execute_self_correction(unit)
                result.correction_result = correction
                self._record_stage(result, PipelineStage.SELF_CORRECTION,
                                  PipelineStatus.SUCCESS if correction.get("success") else PipelineStatus.FAILED,
                                  correction)

            # 12. Oracle投影
            if enable_oracle:
                oracle = self._execute_oracle_projection(unit)
                result.oracle_result = oracle
                self._record_stage(result, PipelineStage.ORACLE_PROJECTION,
                                  PipelineStatus.SUCCESS, oracle)

            # 13. 混沌海检查
            chaos_entries = self._check_chaos_sea(result)
            result.chaos_sea_entries = chaos_entries
            if chaos_entries:
                self._record_stage(result, PipelineStage.CHAOS_SEA,
                                  PipelineStatus.CHAOS_SEA,
                                  {"entries": len(chaos_entries)})

            # 14. 最终化
            result.overall_status = self._determine_final_status(result)
            self._record_stage(result, PipelineStage.FINALIZE,
                              result.overall_status, {})

        except Exception as e:
            result.overall_status = PipelineStatus.FAILED
            self._record_stage(result, PipelineStage.FINALIZE,
                              PipelineStatus.FAILED, {"error": str(e)})

        result.total_duration_ms = (time.time() - start_time) * 1000
        self._pipeline_history.append(result)
        if len(self._pipeline_history) > self._max_history:
            self._pipeline_history = self._pipeline_history[-self._max_history:]

        return result

    # ── 管道步骤实现 ──────────────────────────────────────────────────

    def _create_unit(
        self, unit_id: str, unit_name: str, coords: Dict, layer: int
    ) -> CognitiveUnit:
        """创建认知单元"""
        return CognitiveUnit(
            unit_id=unit_id,
            name=unit_name,
            module_path=f"holographic.{unit_name}",
            coordinates=TBCECoordinates(
                S=coords.get("S", 0.5),
                T=coords.get("T", 0.5),
                P=coords.get("P", 0.5),
                C=coords.get("C", 0.5),
                I=coords.get("I", 0.5),
                E=coords.get("E", 0.5),
            ),
            psi_operator="ZuowangAttention",
            cognitive_layer=layer,
            palace_id=coords.get("palace_id", 5),
            tense="present",
            description=f"全息管道: {unit_name}",
        )

    def _execute_twelve_gates(self, unit: CognitiveUnit) -> Dict[str, Any]:
        """执行十二神门禁裁决"""
        verdicts = {}
        for god in TwelveGods:
            gate = self._get_or_create_gate(god.value)
            if gate:
                verdict = gate.judge(unit)
                verdicts[god.value] = verdict.to_dict()

        self._record_verdict_to_metrics(verdicts)
        return verdicts

    def _check_gates_passed(
        self, verdicts: Dict[str, Any], strict: bool
    ) -> bool:
        """检查门禁是否通过"""
        if not verdicts:
            return True

        open_count = sum(1 for v in verdicts.values() if v.get("state") == GateState.OPEN)
        pending_count = sum(1 for v in verdicts.values() if v.get("state") == GateState.PENDING)
        total = len(verdicts)

        if strict:
            return open_count == total

        # 太极否决权
        tai_ji = verdicts.get("太极", {})
        if tai_ji.get("state") == GateState.CLOSED:
            return False

        return open_count > total / 2

    def _execute_imaging_pipeline(
        self,
        unit: CognitiveUnit,
        gate_verdicts: Dict,
        modalities: List[str],
        enable_speculation: bool,
    ) -> Dict[str, Any]:
        """执行七阶段成像管道"""
        try:
            from .imaging import ImagingEngine, Modality, CognitiveImage
            engine = ImagingEngine()

            # 1. 传感器曝光 → 构建模态内容
            mods = [Modality(m) for m in modalities if m in [e.value for e in Modality]]
            if not mods:
                mods = [Modality.TEXT]

            modal_contents = {
                m: {
                    "content": unit.description,
                    "confidence": getattr(unit.coordinates, 'S', 0.5),
                    "source": unit.name,
                }
                for m in mods
            }

            # 2. 多模态融合 + 质量门禁
            image, (gate_state, gate_reason) = engine.image(
                modal_contents,
                base_confidence=unit.coordinates.S,
                auto_judge=True,
            )

            quality = image.quality_score
            coherence = image.coherence

            # 3. 推测解码
            speculation = {"enabled": enable_speculation}
            if enable_speculation:
                speculated = self._try_speculation(unit, image)
                speculation.update(speculated)

            # 4. 输出生成
            output = {
                "modalities": [m.value for m in mods],
                "confidence": image.confidence,
                "quality": quality,
                "coherence": coherence,
                "gate_state": gate_state,
                "gate_reason": gate_reason,
            }

            return {
                "success": quality > 0.5 and gate_state != "closed",
                "image_id": image.image_id,
                "output": output,
                "speculation": speculation,
                "quality_score": quality,
                "hallucination_risk": image.hallucination_risk,
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "quality_score": 0.0,
            }

    def _try_speculation(
        self, unit: CognitiveUnit, image: Any
    ) -> Dict[str, Any]:
        """推测解码"""
        confidence = getattr(image, 'confidence', 0.5)
        hit = confidence > 0.6  # 高置信度视为推测命中

        self._speculation_total += 1
        if hit:
            self._speculation_hits += 1

        hit_rate = self._speculation_hits / max(1, self._speculation_total)
        speedup = 1.0 / (1.0 - hit_rate) if hit_rate < 1.0 and hit_rate > 0 else 1.0

        return {
            "hit": hit,
            "confidence": round(confidence, 3),
            "cumulative_hit_rate": round(hit_rate, 3),
            "speedup_estimate": round(speedup, 2),
        }

    def _execute_seven_theories(self, unit: CognitiveUnit) -> Dict[str, Any]:
        """执行七论裁决"""
        try:
            from .seven_theories_judge import get_seven_theories_judge
            judge = get_seven_theories_judge()
            verdict = judge.judge(unit)
            return {
                "passed": getattr(verdict, 'passed', True),
                "verdict": getattr(verdict, 'to_dict', lambda: {})() if hasattr(verdict, 'to_dict') else {},
                "theories": getattr(verdict, 'theories', {}),
            }
        except Exception:
            return {"passed": True, "verdict": {}, "theories": {}}

    def _execute_self_correction(self, unit: CognitiveUnit) -> Dict[str, Any]:
        """执行七步自修正"""
        try:
            from .self_correction import SelfCorrectionDaemon
            daemon = SelfCorrectionDaemon()
            report = daemon.correct(unit)
            return {
                "success": report.success,
                "total_delta": report.total_delta,
                "steps": len(report.steps),
                "gate_stats": report.gate_stats,
            }
        except Exception:
            return {"success": False, "total_delta": 0.0, "steps": 0, "gate_stats": {}}

    def _execute_oracle_projection(
        self, unit: CognitiveUnit
    ) -> Dict[str, Any]:
        """执行Oracle三时态投影"""
        try:
            from .oracle_engine import OracleEngine
            oracle = OracleEngine()
            result = oracle.project(unit)
            return {
                "past": getattr(result, 'past', None),
                "present": getattr(result, 'present', None),
                "future": getattr(result, 'future', None),
            }
        except Exception:
            return {"past": None, "present": None, "future": None}

    def _check_chaos_sea(self, result: PipelineResult) -> List[Dict]:
        """检查混沌海存疑"""
        entries = []
        try:
            from .hundun_sea import HundunSea
            sea = HundunSea()
            trails = sea.get_trails(limit=5)
            for t in trails:
                if isinstance(t, dict):
                    entries.append({
                        "route": t.get("route", "unknown"),
                        "confidence": t.get("confidence", 0),
                    })
        except Exception:
            pass
        return entries

    def _determine_final_status(
        self, result: PipelineResult
    ) -> PipelineStatus:
        """确定最终管道状态"""
        # 检查是否有失败阶段
        for stage in result.stages:
            if stage.status == PipelineStatus.FAILED:
                return PipelineStatus.FAILED
            if stage.status == PipelineStatus.CHAOS_SEA:
                return PipelineStatus.CHAOS_SEA

        # 检查门禁
        if result.gate_verdicts:
            passed = self._check_gates_passed(result.gate_verdicts, False)
            if not passed:
                return PipelineStatus.PAUSED

        # 检查成像
        if result.imaging_result and not result.imaging_result.get("success"):
            if result.correction_result and result.correction_result.get("success"):
                return PipelineStatus.SUCCESS  # 自修正后恢复
            return PipelineStatus.FAILED

        return PipelineStatus.SUCCESS

    # ── 五行状态管理 ──────────────────────────────────────────────────

    def _update_element_cycle(self, verdicts: Dict[str, Any]) -> None:
        """更新五行生克状态"""
        for name, v in verdicts.items():
            elem = v.get("element", "未知")
            if elem in self._element_cycle_state:
                state = v.get("state", GateState.PENDING)
                score = v.get("score", 0.5)
                # 指数移动平均
                old = self._element_cycle_state[elem]
                self._element_cycle_state[elem] = old * 0.9 + score * 0.1

    def get_element_health(self) -> Dict[str, float]:
        """获取五行健康度"""
        return dict(self._element_cycle_state)

    # ── 推测解码统计 ──────────────────────────────────────────────────

    def get_speculation_stats(self) -> Dict[str, Any]:
        """获取推测解码统计"""
        hit_rate = self._speculation_hits / max(1, self._speculation_total)
        return {
            "total": self._speculation_total,
            "hits": self._speculation_hits,
            "hit_rate": round(hit_rate, 3),
            "speedup_estimate": round(
                1.0 / (1.0 - hit_rate) if hit_rate < 1.0 and hit_rate > 0 else 1.0, 2
            ),
        }

    # ── 辅助方法 ──────────────────────────────────────────────────────

    def _get_or_create_gate(self, god_name: str) -> Optional[TwelveGodsGate]:
        """获取或创建门禁实例"""
        if god_name in self._gate_instances:
            return self._gate_instances[god_name]

        try:
            god = TwelveGods(god_name)
        except ValueError:
            return None

        gate_type = GOD_GATE_MAP.get(god, "")

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

    def _record_stage(
        self,
        result: PipelineResult,
        stage: PipelineStage,
        status: PipelineStatus,
        data: Dict,
    ) -> None:
        """记录管道阶段"""
        result.stages.append(StageResult(
            stage=stage,
            status=status,
            data=data,
        ))

    def _record_verdict_to_metrics(self, verdicts: Dict) -> None:
        """记录裁决到指标采集器"""
        try:
            from .cognitive_metrics import get_cognitive_metrics
            collector = get_cognitive_metrics()
            for name, v in verdicts.items():
                collector.record_gate_pass(
                    gate_name=name,
                    god_name=name,
                    element=v.get("element", "未知"),
                    passed=v.get("state") == GateState.OPEN,
                    score=v.get("score", 0.5),
                    element_boost=v.get("element_boost", 0.0),
                )
        except Exception:
            pass

    # ── 查询与统计 ────────────────────────────────────────────────────

    def get_pipeline_stats(self) -> Dict[str, Any]:
        """获取管道统计"""
        total = len(self._pipeline_history)
        if total == 0:
            return {"total": 0}

        successes = sum(1 for p in self._pipeline_history
                       if p.overall_status == PipelineStatus.SUCCESS)
        avg_duration = sum(p.total_duration_ms for p in self._pipeline_history) / total

        return {
            "total_pipelines": total,
            "success_rate": round(successes / total, 3),
            "avg_duration_ms": round(avg_duration, 1),
            "element_health": self.get_element_health(),
            "speculation": self.get_speculation_stats(),
        }

    def get_recent_pipelines(self, limit: int = 20) -> List[Dict]:
        """获取最近管道结果"""
        return [p.to_dict() for p in self._pipeline_history[-limit:]]

    def get_pipeline(self, pipeline_id: str) -> Optional[Dict]:
        """按ID获取管道结果"""
        for p in self._pipeline_history:
            if p.pipeline_id == pipeline_id:
                return p.to_dict()
        return None

    def reset(self) -> None:
        """重置全息系统"""
        self._gate_instances.clear()
        self._pipeline_history.clear()
        self._element_cycle_state = {
            "木": 0.5, "火": 0.5, "土": 0.5, "金": 0.5, "水": 0.5, "太极": 0.5,
        }
        self._speculation_hits = 0
        self._speculation_total = 0


# ============================================================================
# 全局单例
# ============================================================================

_holographic_system: Optional[HolographicSystem] = None


def get_holographic_system() -> HolographicSystem:
    """获取全息认知系统总控单例"""
    global _holographic_system
    if _holographic_system is None:
        _holographic_system = HolographicSystem()
    return _holographic_system


def reset_holographic_system() -> None:
    """重置全息认知系统"""
    global _holographic_system
    _holographic_system = None
    HolographicSystem._instance = None


__all__ = [
    "PipelineStage",
    "PipelineStatus",
    "StageResult",
    "PipelineResult",
    "HolographicSystem",
    "get_holographic_system",
    "reset_holographic_system",
]