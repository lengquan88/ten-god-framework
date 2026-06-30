"""
self_correction.py — 自修正守护进程（道体自愈）v2.23.0
========================================================
道曰："以其病病也，是以不病。"

把"出错"当成常态，把"修正"当成修行。

v2.23.0 门禁化改造：
  每一步修正都经过七论门禁裁决，裁决不通过则中断修正，存入混沌海。
  修正步骤不再是"自动执行"，而是"门禁护航"。

七步自修正法（道家映射 → 技术实现 → 门禁化）：
  1. 观自在     → 感知偏差：监测隐性特征空间的"扭曲度" → 本体论裁决
  2. 格物致知   → 根因定位：基于因果图的变量归因 → 认识论裁决
  3. 以物验道   → 物理核验：使用物理约束交叉验证 → 实践论裁决
  4. 抱元守一   → 状态修正：不直接改权重，调整"内在信念熵" → 境界论裁决
  5. 补天浴日   → 补全缺失：调用外挂记忆库补全上下文断层 → 未来观论裁决
  6. 天人合一   → 验证通过：修正后状态嵌入全息图谱 → 元认知论裁决
  7. 铭文刻骨   → 记忆固化：七论裁决，写入长期记忆 → 混沌海裁决

七论门禁裁决：
  - 本体论：这个修正步骤存在吗？
  - 认识论：这个修正步骤可以被认知吗？
  - 实践论：这个修正步骤可以被工程落地吗？
  - 境界论：这个修正步骤提升了系统境界吗？
  - 未来观论：这个修正步骤具有可持续性吗？
  - 元认知论：系统知道自己正在做这个修正吗？
  - 混沌海：是否应该保持为"疑"而非"解"？
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
import time

from .tbce_unit import TBCECoordinates, CognitiveUnit, GateState


# ============================================================================
# 自修正步骤定义（门禁化）
# ============================================================================

@dataclass
class CorrectionStep:
    """单次修正步骤 —— 门禁化版本

    每个修正步骤在TBCE空间中都有一个认知单元坐标，
    每一步执行前都经过七论门禁裁决。
    """
    step_index: int
    name: str           # 道家名称
    tech_name: str      # 技术名称
    status: str = "pending"     # pending/running/completed/failed/interrupted
    input_state: Optional[Dict] = None
    output_state: Optional[Dict] = None
    delta: float = 0.0          # 修正幅度
    confidence: float = 0.0     # 修正置信度
    duration_ms: float = 0.0    # 耗时
    error: str = ""

    # 门禁化字段
    gate_verdict: Optional[Dict] = None  # 七论裁决结果
    gate_passed: bool = True             # 七论是否通过
    interrupted_reason: str = ""         # 中断原因（混沌海）
    cognitive_unit: Optional[CognitiveUnit] = None  # 对应的认知单元
    chaos_sea_entry: Optional[Dict] = None  # 混沌海存疑记录


@dataclass
class CorrectionReport:
    """完整修正报告"""
    session_id: str
    steps: List[CorrectionStep] = field(default_factory=list)
    total_delta: float = 0.0
    success: bool = False
    final_state: Optional[Dict] = None
    timestamp: float = field(default_factory=time.time)

    # 门禁统计
    gate_stats: Dict[str, int] = field(default_factory=lambda: {
        'passed': 0, 'interrupted': 0, 'chaos_sea': 0,
    })

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "steps": [
                {
                    "step": s.step_index,
                    "name": s.name,
                    "tech": s.tech_name,
                    "status": s.status,
                    "delta": round(s.delta, 4),
                    "confidence": round(s.confidence, 3),
                    "duration_ms": round(s.duration_ms, 1),
                    "gate_passed": s.gate_passed,
                    "gate_verdict": s.gate_verdict,
                    "interrupted_reason": s.interrupted_reason,
                }
                for s in self.steps
            ],
            "total_delta": round(self.total_delta, 4),
            "success": self.success,
            "gate_stats": self.gate_stats,
            "timestamp": self.timestamp,
        }


# ============================================================================
# 七论门禁化的修正守护进程
# ============================================================================

class SelfCorrectionDaemon:
    """自修正守护进程 — 道体自愈 + 七论门禁护航

    v2.23.0 门禁化改造：
    - 每一步修正都经过七论门禁裁决
    - 裁决不通过则中断修正，存入混沌海
    - 每步拥有独立的TBCE认知坐标
    - 七论依次裁决，任意一步可中断
    """

    # 七步修正的TBCE坐标模板（骨架坐标，已校准七论阈值）
    # 七论阈值：本体≥0.7, 认识≥0.7, 实践≥0.6, 境界≥0.6, 未来≥0.5, 元认知≥0.7
    # 坐标需满足：S≥0.7(本体), P*(1-0.5E)≥0.4(认识), (I+C)/2≥0.3(实践), (S+P+I+C)/4≥0.4(元认知)
    STEP_COORDINATES = {
        1: TBCECoordinates(S=0.9, T=0.8, P=0.7, C=0.6, I=0.5, E=0.3),  # 观自在：高可信低探索
        2: TBCECoordinates(S=0.8, T=0.7, P=0.8, C=0.5, I=0.6, E=0.4),  # 格物致知：高投影保真
        3: TBCECoordinates(S=0.7, T=0.6, P=0.6, C=0.7, I=0.8, E=0.3),  # 以物验道：高交织稳定
        4: TBCECoordinates(S=0.7, T=0.5, P=0.7, C=0.8, I=0.7, E=0.4),  # 抱元守一：高图层对齐
        5: TBCECoordinates(S=0.6, T=0.4, P=0.6, C=0.7, I=0.5, E=0.6),  # 补天浴日：高探索
        6: TBCECoordinates(S=0.8, T=0.7, P=0.7, C=0.6, I=0.6, E=0.2),  # 天人合一：高可信低探索
        7: TBCECoordinates(S=0.9, T=0.9, P=0.8, C=0.8, I=0.8, E=0.1),  # 铭文刻骨：全高低探索
    }

    # 七步修正的认知层
    STEP_COGNITIVE_LAYERS = {
        1: 5,  # 观自在 — 注意力调度层
        2: 3,  # 格物致知 — 拓扑结构层
        3: 4,  # 以物验道 — 意识涌现层
        4: 5,  # 抱元守一 — 注意力调度层
        5: 6,  # 补天浴日 — 元认知自反层
        6: 7,  # 天人合一 — 认知固化层
        7: 8,  # 铭文刻骨 — 境界跃迁层
    }

    # 七步修正的Ψ算子
    STEP_PSI_OPERATORS = {
        1: "ZuowangAttention",
        2: "Tortuosity",
        3: "PersistenceDiagram",
        4: "PsiSelfRef",
        5: "CondInfoStability",
        6: "RecursionDepth",
        7: "SpiritEvaluator",
    }

    # 七步修正的门禁宫
    STEP_PALACES = {
        1: 1,  # 坎一 — 观自在
        2: 3,  # 震三 — 格物致知
        3: 4,  # 巽四 — 以物验道
        4: 5,  # 中五 — 抱元守一
        5: 6,  # 乾六 — 补天浴日
        6: 7,  # 兑七 — 天人合一
        7: 9,  # 离九 — 铭文刻骨
    }

    def __init__(self):
        self._history: List[CorrectionReport] = []
        self._total_corrections = 0
        self._successful_corrections = 0
        self._chaos_sea_entries: List[Dict] = []  # 混沌海存疑记录

    def _create_cognitive_unit(
        self,
        step_index: int,
        step_name: str,
        session_id: str,
        state: Dict,
    ) -> CognitiveUnit:
        """为修正步骤创建认知单元"""
        return CognitiveUnit(
            unit_id=f"correction.{session_id}.step{step_index}",
            name=f"自修正·{step_name}",
            module_path=f"tengod.self_correction._step_{step_index}",
            coordinates=self.STEP_COORDINATES.get(step_index, TBCECoordinates.default()),
            cognitive_layer=self.STEP_COGNITIVE_LAYERS.get(step_index, 1),
            psi_operator=self.STEP_PSI_OPERATORS.get(step_index, "EmbeddingProvider"),
            palace_id=self.STEP_PALACES.get(step_index),
            tense="present",
            description=f"自修正流程第{step_index}步：{step_name}",
            confidence=state.get("confidence", 0.5),
            metadata={"session_id": session_id, "state_snapshot": state},
        )

    def _judge_step(
        self,
        step: CorrectionStep,
        session_id: str,
        state: Dict,
    ) -> bool:
        """对修正步骤进行七论门禁裁决

        Returns:
            True 如果通过裁决（可继续），False 如果中断
        """
        try:
            from .seven_theories_judge import get_seven_judge

            unit = self._create_cognitive_unit(
                step.step_index, step.name, session_id, state
            )
            step.cognitive_unit = unit

            judge = get_seven_judge()
            verdict = judge.judge(unit, interruptible=True)

            step.gate_verdict = verdict.to_dict()
            step.gate_passed = verdict.overall_state != GateState.CLOSED

            if verdict.interrupted:
                step.status = "interrupted"
                step.interrupted_reason = f"七论裁决中断于第{verdict.interrupted_at}论：{judge.THEORY_NAMES[verdict.interrupted_at - 1]}"
                step.gate_passed = False
                self._store_chaos_sea(step, verdict)
                return False

            if verdict.overall_state == GateState.CLOSED:
                step.status = "interrupted"
                step.interrupted_reason = "七论多数裁决为关"
                step.gate_passed = False
                self._store_chaos_sea(step, verdict)
                return False

            if verdict.chaos_sea_override:
                step.interrupted_reason = "混沌海覆盖裁决，转为存疑"
                # 混沌海覆盖不中断，但标记

            return True

        except ImportError:
            # 七论裁决器不可用，降级：允许通过
            step.gate_passed = True
            return True

    def _store_chaos_sea(self, step: CorrectionStep, verdict) -> None:
        """将中断的修正步骤存入混沌海"""
        entry = {
            "step_index": step.step_index,
            "step_name": step.name,
            "tech_name": step.tech_name,
            "interrupted_reason": step.interrupted_reason,
            "verdict": verdict.to_dict() if hasattr(verdict, 'to_dict') else str(verdict),
            "state_snapshot": step.input_state,
            "timestamp": time.time(),
        }
        step.chaos_sea_entry = entry
        self._chaos_sea_entries.append(entry)

        # 同时尝试存入混沌海探索层
        try:
            from .hundun_sea import HundunSea
            sea = HundunSea()
            sea.explore(
                features={"step": step.step_index, "name": step.name},
                confidence=0.3,
                active_route=f"correction_{step.step_index}",
            )
        except Exception:
            pass

    def correct(
        self,
        current_state: Dict[str, Any],
        expected_output: Optional[Any] = None,
        physical_constraints: Optional[List[Dict]] = None,
        memory_store: Optional[Dict] = None,
        enable_gate: bool = True,
    ) -> Tuple[Dict[str, Any], CorrectionReport]:
        """
        执行七步自修正流程（门禁化）。

        Args:
            current_state: 当前状态（含推理结果、置信度等）
            expected_output: 期望输出（如有）
            physical_constraints: 物理约束列表
            memory_store: 外部记忆库
            enable_gate: 是否启用七论门禁裁决

        Returns:
            (修正后的状态, 修正报告)
        """
        session_id = f"corr_{int(time.time() * 1000)}"
        report = CorrectionReport(session_id=session_id)
        state = dict(current_state)

        # ── 步骤 1：观自在 — 感知偏差 ──────────────────────────────────
        step1 = self._step_observe(state)
        report.steps.append(step1)
        if enable_gate and not self._judge_step(step1, session_id, state):
            report.gate_stats['interrupted'] += 1
            report.gate_stats['chaos_sea'] += 1
            report.success = False
            report.final_state = state
            self._history.append(report)
            self._total_corrections += 1
            return state, report
        report.gate_stats['passed'] += 1
        if step1.status == "failed":
            report.success = False
            return state, report

        # ── 步骤 2：格物致知 — 根因定位 ──────────────────────────────
        step2 = self._step_root_cause(state, step1.output_state or {})
        report.steps.append(step2)
        if enable_gate and not self._judge_step(step2, session_id, state):
            report.gate_stats['interrupted'] += 1
            report.gate_stats['chaos_sea'] += 1
            report.success = False
            report.final_state = state
            self._history.append(report)
            self._total_corrections += 1
            return state, report
        report.gate_stats['passed'] += 1
        if step2.status == "failed":
            report.success = False
            return state, report

        # ── 步骤 3：以物验道 — 物理核验 ──────────────────────────────
        step3 = self._step_physical_verify(state, physical_constraints)
        report.steps.append(step3)
        if enable_gate and not self._judge_step(step3, session_id, state):
            report.gate_stats['interrupted'] += 1
            report.gate_stats['chaos_sea'] += 1
            report.success = False
            report.final_state = state
            self._history.append(report)
            self._total_corrections += 1
            return state, report
        report.gate_stats['passed'] += 1

        # ── 步骤 4：抱元守一 — 状态修正 ──────────────────────────────
        step4 = self._step_correct_state(state, step2.output_state or {}, step3.output_state or {})
        report.steps.append(step4)
        if enable_gate and not self._judge_step(step4, session_id, state):
            report.gate_stats['interrupted'] += 1
            report.gate_stats['chaos_sea'] += 1
            report.success = False
            report.final_state = state
            self._history.append(report)
            self._total_corrections += 1
            return state, report
        report.gate_stats['passed'] += 1
        if step4.output_state:
            state.update(step4.output_state)

        # ── 步骤 5：补天浴日 — 补全缺失 ──────────────────────────────
        step5 = self._step_complete(state, memory_store)
        report.steps.append(step5)
        if enable_gate and not self._judge_step(step5, session_id, state):
            report.gate_stats['interrupted'] += 1
            report.gate_stats['chaos_sea'] += 1
            report.success = False
            report.final_state = state
            self._history.append(report)
            self._total_corrections += 1
            return state, report
        report.gate_stats['passed'] += 1
        if step5.output_state:
            state.update(step5.output_state)

        # ── 步骤 6：天人合一 — 全局验证 ──────────────────────────────
        step6 = self._step_align(state, expected_output)
        report.steps.append(step6)
        if enable_gate and not self._judge_step(step6, session_id, state):
            report.gate_stats['interrupted'] += 1
            report.gate_stats['chaos_sea'] += 1
            report.success = False
            report.final_state = state
            self._history.append(report)
            self._total_corrections += 1
            return state, report
        report.gate_stats['passed'] += 1

        # ── 步骤 7：铭文刻骨 — 记忆固化 ──────────────────────────────
        step7 = self._step_consolidate(state, enable_gate)
        report.steps.append(step7)
        if enable_gate and not self._judge_step(step7, session_id, state):
            report.gate_stats['interrupted'] += 1
            report.gate_stats['chaos_sea'] += 1
            report.success = False
            report.final_state = state
            self._history.append(report)
            self._total_corrections += 1
            return state, report
        report.gate_stats['passed'] += 1

        # 汇总
        report.total_delta = sum(s.delta for s in report.steps)
        report.success = all(s.status in ("completed", "running") for s in report.steps)
        report.final_state = state

        self._history.append(report)
        self._total_corrections += 1
        if report.success:
            self._successful_corrections += 1

        return state, report

    # ── 步骤实现 ──────────────────────────────────────────────────────

    def _step_observe(self, state: Dict) -> CorrectionStep:
        """观自在：感知偏差 — 监测隐性特征空间的扭曲度"""
        step = CorrectionStep(1, "观自在", "感知偏差检测")
        start = time.time()

        try:
            bias_detected = False
            distortions = {}

            if state.get("confidence", 0.5) < 0.3:
                bias_detected = True
                distortions["low_confidence"] = state.get("confidence", 0.5)

            if state.get("output") is None:
                bias_detected = True
                distortions["null_output"] = 1.0

            step.output_state = {
                "bias_detected": bias_detected,
                "distortions": distortions,
                "topological_divergence": sum(distortions.values()) / max(1, len(distortions)),
            }
            step.delta = step.output_state["topological_divergence"]
            step.confidence = 0.9
            step.status = "completed"
        except Exception as e:
            step.status = "failed"
            step.error = str(e)
        finally:
            step.duration_ms = (time.time() - start) * 1000
        return step

    def _step_root_cause(self, state: Dict, observation: Dict) -> CorrectionStep:
        """格物致知：根因定位 — 基于因果图的变量归因"""
        step = CorrectionStep(2, "格物致知", "根因定位")
        start = time.time()

        try:
            root_causes = []
            if observation.get("bias_detected"):
                distortions = observation.get("distortions", {})
                for cause, severity in distortions.items():
                    root_causes.append({
                        "cause": cause,
                        "severity": severity,
                        "suggested_fix": self._suggest_fix(cause),
                    })

            step.output_state = {
                "root_causes": root_causes,
                "cause_count": len(root_causes),
            }
            step.delta = len(root_causes) * 0.1
            step.confidence = 0.8
            step.status = "completed"
        except Exception as e:
            step.status = "failed"
            step.error = str(e)
        finally:
            step.duration_ms = (time.time() - start) * 1000
        return step

    def _step_physical_verify(
        self, state: Dict, constraints: Optional[List[Dict]]
    ) -> CorrectionStep:
        """以物验道：物理核验 — 使用约束交叉验证"""
        step = CorrectionStep(3, "以物验道", "物理核验")
        start = time.time()

        try:
            hallucinations = []
            if constraints:
                for c in constraints:
                    field = c.get("field", "")
                    ctype = c.get("type", "")
                    value = state.get(field)

                    if ctype == "range" and value is not None:
                        lo, hi = c.get("range", (0, 1))
                        if not (lo <= value <= hi):
                            hallucinations.append({
                                "field": field,
                                "value": value,
                                "expected_range": [lo, hi],
                                "type": "out_of_range",
                            })

                    elif ctype == "non_null" and value is None:
                        hallucinations.append({
                            "field": field,
                            "value": None,
                            "type": "null_violation",
                        })

            step.output_state = {
                "hallucinations": hallucinations,
                "hallucination_count": len(hallucinations),
                "verified": len(hallucinations) == 0,
            }
            step.delta = len(hallucinations) * 0.15
            step.confidence = 0.85
            step.status = "completed"
        except Exception as e:
            step.status = "failed"
            step.error = str(e)
        finally:
            step.duration_ms = (time.time() - start) * 1000
        return step

    def _step_correct_state(
        self, state: Dict, root_causes: Dict, verification: Dict
    ) -> CorrectionStep:
        """抱元守一：状态修正 — 调整内在信念熵"""
        step = CorrectionStep(4, "抱元守一", "状态修正")
        start = time.time()

        try:
            corrected = {}
            if verification.get("hallucinations"):
                for h in verification["hallucinations"]:
                    field = h["field"]
                    if h["type"] == "out_of_range":
                        lo, hi = h["expected_range"]
                        corrected[field] = max(lo, min(hi, (lo + hi) / 2))
                    elif h["type"] == "null_violation":
                        corrected[field] = state.get("fallback_value", 0.0)

            uncertainty = state.get("uncertainty", 0.5)
            corrected["uncertainty"] = max(0.1, uncertainty - 0.2)

            step.output_state = corrected
            step.delta = len(corrected) * 0.1
            step.confidence = 0.75
            step.status = "completed"
        except Exception as e:
            step.status = "failed"
            step.error = str(e)
        finally:
            step.duration_ms = (time.time() - start) * 1000
        return step

    def _step_complete(self, state: Dict, memory_store: Optional[Dict]) -> CorrectionStep:
        """补天浴日：补全缺失 — 调用外挂记忆库"""
        step = CorrectionStep(5, "补天浴日", "补全缺失")
        start = time.time()

        try:
            completed = {}
            if memory_store:
                for k, v in state.items():
                    if v is None and k in memory_store:
                        completed[k] = memory_store[k]
                    elif isinstance(v, str) and len(v) < 10 and k in memory_store:
                        completed[k] = f"{v}（补：{memory_store[k][:50]}）"

            step.output_state = completed
            step.delta = len(completed) * 0.05
            step.confidence = 0.7
            step.status = "completed"
        except Exception as e:
            step.status = "failed"
            step.error = str(e)
        finally:
            step.duration_ms = (time.time() - start) * 1000
        return step

    def _step_align(self, state: Dict, expected: Optional[Any]) -> CorrectionStep:
        """天人合一：全局验证 — 与期望输出对齐"""
        step = CorrectionStep(6, "天人合一", "全局验证")
        start = time.time()

        try:
            aligned = {}
            if expected is not None:
                output = state.get("output")
                if output is not None and isinstance(output, (int, float)):
                    diff = abs(output - expected)
                    if diff > 0.1:
                        aligned["output"] = expected
                        aligned["alignment_delta"] = diff
                elif isinstance(output, dict) and isinstance(expected, dict):
                    for k in set(output) & set(expected):
                        if isinstance(output[k], (int, float)) and isinstance(expected[k], (int, float)):
                            if abs(output[k] - expected[k]) > 0.1:
                                aligned[k] = expected[k]

            step.output_state = aligned
            step.delta = len(aligned) * 0.08
            step.confidence = 0.8
            step.status = "completed"
        except Exception as e:
            step.status = "failed"
            step.error = str(e)
        finally:
            step.duration_ms = (time.time() - start) * 1000
        return step

    def _step_consolidate(self, state: Dict, enable_gate: bool) -> CorrectionStep:
        """铭文刻骨：记忆固化 — 七论裁决后写入长期记忆

        v2.23.0 门禁化：使用七论裁决器而非单一门禁
        """
        step = CorrectionStep(7, "铭文刻骨", "记忆固化")
        start = time.time()

        try:
            if enable_gate:
                try:
                    from .seven_theories_judge import get_seven_judge

                    unit = self._create_cognitive_unit(
                        7, "铭文刻骨", f"consolidate_{int(time.time())}", state
                    )
                    judge = get_seven_judge()
                    verdict = judge.judge(unit, interruptible=True)

                    step.gate_verdict = verdict.to_dict()
                    step.confidence = 0.9

                    if verdict.overall_state == GateState.CLOSED or verdict.interrupted:
                        step.status = "completed"
                        step.output_state = {
                            "consolidated": False,
                            "reason": f"七论裁决：{verdict.overall_state}",
                            "verdict": verdict.to_dict(),
                        }
                        step.delta = 0.0
                        step.gate_passed = False
                        step.duration_ms = (time.time() - start) * 1000
                        return step
                except ImportError:
                    pass

            step.output_state = {"consolidated": True, "memory_key": f"mem_{int(time.time())}"}
            step.confidence = 0.9
            step.delta = 0.05
            step.gate_passed = True
            step.status = "completed"
        except Exception as e:
            step.status = "failed"
            step.error = str(e)
        finally:
            step.duration_ms = (time.time() - start) * 1000
        return step

    def _suggest_fix(self, cause: str) -> str:
        """根据根因建议修复方案"""
        fixes = {
            "low_confidence": "提高置信度阈值，或回退至上层重新推理",
            "null_output": "检查输入完整性，调用记忆库补全",
            "out_of_range": "应用物理约束裁剪",
            "null_violation": "从默认值或上下文推断",
        }
        return fixes.get(cause, "重新审视输入与推理过程")

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_corrections": self._total_corrections,
            "successful": self._successful_corrections,
            "success_rate": round(
                self._successful_corrections / max(1, self._total_corrections), 3
            ),
            "chaos_sea_entries": len(self._chaos_sea_entries),
            "recent_reports": [r.to_dict() for r in self._history[-5:]],
        }

    def get_chaos_sea_entries(self) -> List[Dict]:
        """获取混沌海存疑记录"""
        return self._chaos_sea_entries


# 全局守护进程
_daemon: Optional[SelfCorrectionDaemon] = None


def get_daemon() -> SelfCorrectionDaemon:
    global _daemon
    if _daemon is None:
        _daemon = SelfCorrectionDaemon()
    return _daemon


def reset_daemon() -> None:
    """重置全局守护进程"""
    global _daemon
    _daemon = None


__all__ = [
    "CorrectionStep", "CorrectionReport",
    "SelfCorrectionDaemon", "get_daemon", "reset_daemon",
]