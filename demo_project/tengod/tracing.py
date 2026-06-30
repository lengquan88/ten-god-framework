"""
tracing.py — 全链路追踪与审计日志 v2.32.0
=============================================
道曰："执古之道，以御今之有。能知古始，是谓道纪。"

全链路追踪，使每一次推理都可追溯、可审计、可复现。

核心能力：
  - Span-based 全链路追踪（TraceID → SpanID → ParentSpanID）
  - 推理链可追溯：从输入到输出的完整推理路径
  - 七步自修正审计日志：每步修正的门禁裁决与状态变更
  - 十二神门禁追踪：每个门禁的裁决过程与生克影响
  - TBCE坐标漂移追踪：认知单元在推理过程中的坐标变化
  - 审计合规：支持按时间/模块/门禁/认知层多维度查询
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple
import threading
import time
import uuid


# ============================================================================
# 追踪跨度
# ============================================================================

class SpanKind(Enum):
    """跨度类型"""
    ROOT = "root"               # 根跨度（推理入口）
    GATE_JUDGE = "gate_judge"   # 门禁裁决
    SELF_CORRECTION = "self_correction"  # 自修正步骤
    IMAGING = "imaging"         # 认知成像
    TBCE_DRIFT = "tbce_drift"   # TBCE坐标漂移
    LLM_CALL = "llm_call"       # LLM调用
    KNOWLEDGE_QUERY = "knowledge_query"  # 知识查询
    ORACLE_PROJECTION = "oracle_projection"  # Oracle投影
    CONSENSUS = "consensus"     # 共识
    CUSTOM = "custom"           # 自定义


class SpanStatus(Enum):
    """跨度状态"""
    STARTED = "started"
    SUCCESS = "success"
    FAILED = "failed"
    INTERRUPTED = "interrupted"  # 被门禁中断
    CHAOS_SEA = "chaos_sea"      # 转入混沌海


# ============================================================================
# 追踪数据结构
# ============================================================================

@dataclass
class TraceSpan:
    """追踪跨度 — 最小追踪单元"""
    span_id: str
    parent_span_id: Optional[str]
    trace_id: str
    name: str
    kind: SpanKind
    status: SpanStatus = SpanStatus.STARTED
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None
    duration_ms: float = 0.0

    # 上下文
    module: str = ""
    function: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    # 门禁相关
    gate_verdict: Optional[Dict] = None
    gate_name: str = ""
    element_boost: float = 0.0

    # TBCE相关
    tbce_before: Optional[Dict] = None
    tbce_after: Optional[Dict] = None
    tbce_drift: float = 0.0

    # 自修正相关
    correction_step: int = 0
    correction_name: str = ""
    correction_delta: float = 0.0

    # 错误
    error: str = ""
    error_level: str = ""

    # 标签
    tags: Dict[str, str] = field(default_factory=dict)

    def finish(
        self,
        status: SpanStatus = SpanStatus.SUCCESS,
        error: str = "",
        metadata: Optional[Dict] = None,
    ) -> None:
        """结束跨度"""
        self.end_time = time.time()
        self.duration_ms = (self.end_time - self.start_time) * 1000
        self.status = status
        self.error = error
        if metadata:
            self.metadata.update(metadata)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "span_id": self.span_id,
            "parent_span_id": self.parent_span_id,
            "trace_id": self.trace_id,
            "name": self.name,
            "kind": self.kind.value,
            "status": self.status.value,
            "duration_ms": round(self.duration_ms, 2),
            "module": self.module,
            "function": self.function,
            "gate_name": self.gate_name,
            "gate_verdict": self.gate_verdict,
            "element_boost": round(self.element_boost, 4),
            "tbce_drift": round(self.tbce_drift, 4),
            "correction_step": self.correction_step,
            "correction_delta": round(self.correction_delta, 4),
            "error": self.error[:200] if self.error else "",
            "tags": self.tags,
            "metadata": {k: str(v)[:100] for k, v in self.metadata.items()},
        }


@dataclass
class Trace:
    """全链路追踪 — 一次推理的完整追踪链"""
    trace_id: str
    root_span_id: str
    spans: List[TraceSpan] = field(default_factory=list)
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None
    total_duration_ms: float = 0.0
    status: SpanStatus = SpanStatus.STARTED

    # 统计
    gate_pass_count: int = 0
    gate_fail_count: int = 0
    correction_step_count: int = 0
    correction_success_count: int = 0
    llm_call_count: int = 0
    chaos_sea_count: int = 0

    def finish(self, status: SpanStatus = SpanStatus.SUCCESS) -> None:
        """结束追踪"""
        self.end_time = time.time()
        self.total_duration_ms = (self.end_time - self.start_time) * 1000
        self.status = status

        # 汇总统计
        for span in self.spans:
            if span.kind == SpanKind.GATE_JUDGE:
                if span.status == SpanStatus.SUCCESS:
                    self.gate_pass_count += 1
                else:
                    self.gate_fail_count += 1
            elif span.kind == SpanKind.SELF_CORRECTION:
                self.correction_step_count += 1
                if span.status == SpanStatus.SUCCESS:
                    self.correction_success_count += 1
            elif span.kind == SpanKind.LLM_CALL:
                self.llm_call_count += 1
            elif span.status == SpanStatus.CHAOS_SEA:
                self.chaos_sea_count += 1

    def to_dict(self) -> Dict[str, Any]:
        return {
            "trace_id": self.trace_id,
            "root_span_id": self.root_span_id,
            "total_duration_ms": round(self.total_duration_ms, 2),
            "status": self.status.value,
            "span_count": len(self.spans),
            "gate_pass_count": self.gate_pass_count,
            "gate_fail_count": self.gate_fail_count,
            "correction_step_count": self.correction_step_count,
            "correction_success_count": self.correction_success_count,
            "llm_call_count": self.llm_call_count,
            "chaos_sea_count": self.chaos_sea_count,
            "spans": [s.to_dict() for s in self.spans],
        }


# ============================================================================
# 七步自修正审计日志
# ============================================================================

@dataclass
class CorrectionAuditEntry:
    """自修正审计条目"""
    trace_id: str
    step_index: int
    step_name: str
    tech_name: str
    status: str
    gate_verdict: Optional[Dict]
    gate_passed: bool
    interrupted_reason: str
    delta: float
    confidence: float
    duration_ms: float
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "trace_id": self.trace_id,
            "step": self.step_index,
            "name": self.step_name,
            "tech": self.tech_name,
            "status": self.status,
            "gate_passed": self.gate_passed,
            "gate_verdict": self.gate_verdict,
            "interrupted_reason": self.interrupted_reason,
            "delta": round(self.delta, 4),
            "confidence": round(self.confidence, 3),
            "duration_ms": round(self.duration_ms, 1),
            "timestamp": self.timestamp,
        }


# ============================================================================
# 链路追踪管理器
# ============================================================================

class TraceManager:
    """全链路追踪管理器 v2.32.0

    Span-based 追踪模型，支持嵌套子跨度、门禁追踪、自修正审计。
    """

    _instance: Optional["TraceManager"] = None
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

        self._active_traces: Dict[str, Trace] = {}
        self._completed_traces: List[Trace] = []
        self._audit_log: List[CorrectionAuditEntry] = []
        self._max_completed_traces: int = 1000
        self._max_audit_entries: int = 5000

    # ── 追踪生命周期 ──────────────────────────────────────────────────

    def start_trace(
        self,
        name: str = "inference",
        module: str = "",
        metadata: Optional[Dict] = None,
    ) -> Trace:
        """开始一个新的追踪链

        Returns:
            Trace 对象
        """
        trace_id = self._generate_id("trace")
        root_span_id = self._generate_id("span")

        trace = Trace(
            trace_id=trace_id,
            root_span_id=root_span_id,
        )

        # 创建根跨度
        root_span = TraceSpan(
            span_id=root_span_id,
            parent_span_id=None,
            trace_id=trace_id,
            name=name,
            kind=SpanKind.ROOT,
            module=module,
            metadata=metadata or {},
        )
        trace.spans.append(root_span)

        self._active_traces[trace_id] = trace
        return trace

    def start_span(
        self,
        trace_id: str,
        name: str,
        kind: SpanKind,
        parent_span_id: Optional[str] = None,
        module: str = "",
        function: str = "",
        metadata: Optional[Dict] = None,
    ) -> Optional[TraceSpan]:
        """在追踪链中创建一个子跨度

        Args:
            trace_id: 追踪ID
            name: 跨度名称
            kind: 跨度类型
            parent_span_id: 父跨度ID（None则使用根跨度）
            module: 模块名
            function: 函数名
            metadata: 附加元数据

        Returns:
            TraceSpan 或 None（如果追踪不存在）
        """
        trace = self._active_traces.get(trace_id)
        if trace is None:
            return None

        if parent_span_id is None:
            parent_span_id = trace.root_span_id

        span = TraceSpan(
            span_id=self._generate_id("span"),
            parent_span_id=parent_span_id,
            trace_id=trace_id,
            name=name,
            kind=kind,
            module=module,
            function=function,
            metadata=metadata or {},
        )
        trace.spans.append(span)
        return span

    def finish_span(
        self,
        span: TraceSpan,
        status: SpanStatus = SpanStatus.SUCCESS,
        error: str = "",
        metadata: Optional[Dict] = None,
    ) -> None:
        """结束一个跨度"""
        span.finish(status, error, metadata)

    def finish_trace(
        self,
        trace_id: str,
        status: SpanStatus = SpanStatus.SUCCESS,
    ) -> Optional[Trace]:
        """结束一个追踪链"""
        trace = self._active_traces.pop(trace_id, None)
        if trace is None:
            return None

        trace.finish(status)

        # 归档
        self._completed_traces.append(trace)
        if len(self._completed_traces) > self._max_completed_traces:
            self._completed_traces = self._completed_traces[-self._max_completed_traces:]

        return trace

    # ── 门禁追踪 ──────────────────────────────────────────────────────

    def trace_gate_judge(
        self,
        trace_id: str,
        gate_name: str,
        verdict: Any,
        element_boost: float = 0.0,
        parent_span_id: Optional[str] = None,
    ) -> Optional[TraceSpan]:
        """追踪门禁裁决

        Args:
            trace_id: 追踪ID
            gate_name: 门禁名称（如"比肩·劫财"）
            verdict: 门禁裁决结果
            element_boost: 五行生克加成
            parent_span_id: 父跨度ID

        Returns:
            TraceSpan 或 None
        """
        passed = getattr(verdict, 'passed', None)
        if passed is None and hasattr(verdict, 'state'):
            passed = getattr(verdict.state, 'value', 'unknown') == 'open'

        status = SpanStatus.SUCCESS if passed else SpanStatus.FAILED

        span = self.start_span(
            trace_id=trace_id,
            name=f"门禁裁决·{gate_name}",
            kind=SpanKind.GATE_JUDGE,
            parent_span_id=parent_span_id,
            module="twelve_gods",
            function=gate_name,
        )
        if span is None:
            return None

        span.gate_name = gate_name
        span.element_boost = element_boost
        try:
            span.gate_verdict = verdict.to_dict()
        except Exception:
            span.gate_verdict = {"state": str(verdict)}

        self.finish_span(span, status)
        return span

    # ── 自修正审计 ────────────────────────────────────────────────────

    def trace_correction_step(
        self,
        trace_id: str,
        step_index: int,
        step_name: str,
        tech_name: str,
        status: str,
        gate_passed: bool,
        gate_verdict: Optional[Dict],
        interrupted_reason: str,
        delta: float,
        confidence: float,
        duration_ms: float,
        parent_span_id: Optional[str] = None,
    ) -> Optional[TraceSpan]:
        """追踪自修正步骤

        Returns:
            TraceSpan 或 None
        """
        span_status = SpanStatus.SUCCESS
        if status == "interrupted":
            span_status = SpanStatus.INTERRUPTED
        elif status == "failed":
            span_status = SpanStatus.FAILED

        span = self.start_span(
            trace_id=trace_id,
            name=f"自修正·{step_name}",
            kind=SpanKind.SELF_CORRECTION,
            parent_span_id=parent_span_id,
            module="self_correction",
            function=f"step_{step_index}",
        )
        if span is None:
            return None

        span.correction_step = step_index
        span.correction_name = step_name
        span.correction_delta = delta
        span.gate_verdict = gate_verdict
        span.gate_name = "七论裁决"

        self.finish_span(span, span_status, interrupted_reason)

        # 写入审计日志
        entry = CorrectionAuditEntry(
            trace_id=trace_id,
            step_index=step_index,
            step_name=step_name,
            tech_name=tech_name,
            status=status,
            gate_verdict=gate_verdict,
            gate_passed=gate_passed,
            interrupted_reason=interrupted_reason,
            delta=delta,
            confidence=confidence,
            duration_ms=duration_ms,
        )
        self._audit_log.append(entry)
        if len(self._audit_log) > self._max_audit_entries:
            self._audit_log = self._audit_log[-self._max_audit_entries:]

        return span

    # ── TBCE漂移追踪 ──────────────────────────────────────────────────

    def trace_tbce_drift(
        self,
        trace_id: str,
        unit_name: str,
        coords_before: Dict,
        coords_after: Dict,
        drift: float,
        parent_span_id: Optional[str] = None,
    ) -> Optional[TraceSpan]:
        """追踪TBCE坐标漂移"""
        span = self.start_span(
            trace_id=trace_id,
            name=f"TBCE漂移·{unit_name}",
            kind=SpanKind.TBCE_DRIFT,
            parent_span_id=parent_span_id,
            module="tbce",
            function=unit_name,
        )
        if span is None:
            return None

        span.tbce_before = coords_before
        span.tbce_after = coords_after
        span.tbce_drift = drift

        status = SpanStatus.SUCCESS
        if drift > 0.5:
            status = SpanStatus.FAILED
        elif drift > 0.3:
            status = SpanStatus.INTERRUPTED

        self.finish_span(span, status)
        return span

    # ── 查询与统计 ────────────────────────────────────────────────────

    def get_trace(self, trace_id: str) -> Optional[Dict]:
        """获取指定追踪链"""
        trace = self._active_traces.get(trace_id)
        if trace is None:
            for t in reversed(self._completed_traces):
                if t.trace_id == trace_id:
                    trace = t
                    break
        return trace.to_dict() if trace else None

    def get_active_traces(self) -> List[Dict]:
        """获取所有活跃追踪"""
        return [t.to_dict() for t in self._active_traces.values()]

    def get_completed_traces(self, limit: int = 20) -> List[Dict]:
        """获取最近完成的追踪"""
        return [t.to_dict() for t in self._completed_traces[-limit:]]

    def get_audit_log(
        self,
        limit: int = 50,
        trace_id: Optional[str] = None,
        step_index: Optional[int] = None,
    ) -> List[Dict]:
        """查询自修正审计日志

        Args:
            limit: 返回条数
            trace_id: 按追踪ID过滤
            step_index: 按步骤索引过滤

        Returns:
            审计条目列表
        """
        entries = self._audit_log

        if trace_id:
            entries = [e for e in entries if e.trace_id == trace_id]
        if step_index is not None:
            entries = [e for e in entries if e.step_index == step_index]

        return [e.to_dict() for e in entries[-limit:]]

    def get_audit_summary(self) -> Dict[str, Any]:
        """获取审计摘要"""
        total = len(self._audit_log)
        if total == 0:
            return {"total_entries": 0}

        passed = sum(1 for e in self._audit_log if e.gate_passed)
        interrupted = sum(1 for e in self._audit_log if e.status == "interrupted")
        failed = sum(1 for e in self._audit_log if e.status == "failed")

        step_stats = {}
        for e in self._audit_log:
            s = e.step_index
            if s not in step_stats:
                step_stats[s] = {"total": 0, "passed": 0, "interrupted": 0}
            step_stats[s]["total"] += 1
            if e.gate_passed:
                step_stats[s]["passed"] += 1
            if e.status == "interrupted":
                step_stats[s]["interrupted"] += 1

        return {
            "total_entries": total,
            "passed": passed,
            "interrupted": interrupted,
            "failed": failed,
            "pass_rate": round(passed / total, 3),
            "interrupt_rate": round(interrupted / total, 3),
            "by_step": step_stats,
        }

    def get_trace_stats(self) -> Dict[str, Any]:
        """获取追踪统计"""
        total = len(self._completed_traces)
        if total == 0:
            return {"total_traces": 0}

        successes = sum(1 for t in self._completed_traces if t.status == SpanStatus.SUCCESS)
        avg_duration = sum(t.total_duration_ms for t in self._completed_traces) / total
        avg_gate_passes = sum(t.gate_pass_count for t in self._completed_traces) / total
        avg_gate_fails = sum(t.gate_fail_count for t in self._completed_traces) / total
        avg_corrections = sum(t.correction_step_count for t in self._completed_traces) / total
        avg_chaos_sea = sum(t.chaos_sea_count for t in self._completed_traces) / total

        return {
            "total_traces": total,
            "active_traces": len(self._active_traces),
            "success_rate": round(successes / total, 3),
            "avg_duration_ms": round(avg_duration, 1),
            "avg_gate_passes": round(avg_gate_passes, 1),
            "avg_gate_fails": round(avg_gate_fails, 1),
            "avg_correction_steps": round(avg_corrections, 1),
            "avg_chaos_sea": round(avg_chaos_sea, 1),
        }

    def get_inference_chain(self, trace_id: str) -> Optional[Dict]:
        """获取推理链可追溯视图

        从输入到输出的完整推理路径，包括所有门禁裁决和自修正步骤。
        """
        trace_dict = self.get_trace(trace_id)
        if trace_dict is None:
            return None

        # 构建推理链：按时间排序的跨度树
        spans = trace_dict.get("spans", [])
        spans_by_id = {s["span_id"]: s for s in spans}

        def build_chain(span_id: str) -> Dict:
            span = spans_by_id.get(span_id, {})
            children = [
                build_chain(s["span_id"])
                for s in spans
                if s.get("parent_span_id") == span_id and s["span_id"] != span_id
            ]
            return {
                "name": span.get("name", ""),
                "kind": span.get("kind", ""),
                "status": span.get("status", ""),
                "duration_ms": span.get("duration_ms", 0),
                "gate_name": span.get("gate_name", ""),
                "gate_verdict": span.get("gate_verdict"),
                "correction_step": span.get("correction_step", 0),
                "error": span.get("error", ""),
                "children": children,
            }

        return {
            "trace_id": trace_id,
            "total_duration_ms": trace_dict.get("total_duration_ms", 0),
            "status": trace_dict.get("status", ""),
            "chain": build_chain(trace_dict.get("root_span_id", "")),
        }

    # ── 辅助方法 ──────────────────────────────────────────────────────

    def _generate_id(self, prefix: str) -> str:
        """生成唯一ID"""
        return f"{prefix}_{uuid.uuid4().hex[:12]}"

    def reset(self) -> None:
        """重置追踪管理器"""
        self._active_traces.clear()
        self._completed_traces.clear()
        self._audit_log.clear()


# ============================================================================
# 全局单例
# ============================================================================

_trace_manager: Optional[TraceManager] = None


def get_trace_manager() -> TraceManager:
    """获取追踪管理器单例"""
    global _trace_manager
    if _trace_manager is None:
        _trace_manager = TraceManager()
    return _trace_manager


def reset_trace_manager() -> None:
    """重置追踪管理器"""
    global _trace_manager
    _trace_manager = None
    TraceManager._instance = None


__all__ = [
    "SpanKind",
    "SpanStatus",
    "TraceSpan",
    "Trace",
    "CorrectionAuditEntry",
    "TraceManager",
    "get_trace_manager",
    "reset_trace_manager",
]