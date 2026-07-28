"""
test_tracing.py — 全链路追踪系统测试 v4.6.0
==================================================
测试覆盖：
- TraceSpan: 创建/结束/序列化/状态转换
- Trace: 追踪链生命周期/统计汇总/序列化
- TraceManager: 单例模式/追踪生命周期/子跨度嵌套
- 门禁追踪: trace_gate_judge 与裁决集成
- 自修正审计: trace_correction_step 与审计日志查询
- TBCE漂移追踪: trace_tbce_drift 与阈值判断
- 查询与统计: get_trace/get_audit_log/get_trace_stats
- 推理链构建: get_inference_chain 树形结构
- 并发安全: 多线程下追踪管理器行为
"""

import pytest
import threading
import time
from unittest.mock import MagicMock

from tengod.tracing import (
    SpanKind,
    SpanStatus,
    TraceSpan,
    Trace,
    CorrectionAuditEntry,
    TraceManager,
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture(autouse=True)
def reset_trace_manager():
    """每个测试前重置 TraceManager 单例状态。"""
    tm = TraceManager()
    tm.reset()
    yield
    tm.reset()


@pytest.fixture
def sample_trace_id():
    """创建一个追踪并返回 trace_id。"""
    tm = TraceManager()
    trace = tm.start_trace(name="test_inference", module="test_module")
    return trace.trace_id


# ============================================================================
# SpanKind 枚举测试
# ============================================================================

class TestSpanKind:
    def test_all_kinds_exist(self):
        """验证所有跨度类型枚举值"""
        kinds = [
            SpanKind.ROOT, SpanKind.GATE_JUDGE, SpanKind.SELF_CORRECTION,
            SpanKind.IMAGING, SpanKind.TBCE_DRIFT, SpanKind.LLM_CALL,
            SpanKind.KNOWLEDGE_QUERY, SpanKind.ORACLE_PROJECTION,
            SpanKind.CONSENSUS, SpanKind.CUSTOM,
        ]
        assert len(kinds) == 10
        for k in kinds:
            assert isinstance(k.value, str)

    def test_span_kind_values(self):
        assert SpanKind.ROOT.value == "root"
        assert SpanKind.GATE_JUDGE.value == "gate_judge"
        assert SpanKind.SELF_CORRECTION.value == "self_correction"


# ============================================================================
# SpanStatus 枚举测试
# ============================================================================

class TestSpanStatus:
    def test_all_statuses_exist(self):
        statuses = [
            SpanStatus.STARTED, SpanStatus.SUCCESS, SpanStatus.FAILED,
            SpanStatus.INTERRUPTED, SpanStatus.CHAOS_SEA,
        ]
        assert len(statuses) == 5

    def test_status_values(self):
        assert SpanStatus.STARTED.value == "started"
        assert SpanStatus.SUCCESS.value == "success"
        assert SpanStatus.FAILED.value == "failed"
        assert SpanStatus.INTERRUPTED.value == "interrupted"
        assert SpanStatus.CHAOS_SEA.value == "chaos_sea"


# ============================================================================
# TraceSpan 测试
# ============================================================================

class TestTraceSpan:
    def test_create_span(self):
        """创建基本跨度"""
        span = TraceSpan(
            span_id="span_123",
            parent_span_id=None,
            trace_id="trace_456",
            name="test_span",
            kind=SpanKind.ROOT,
        )
        assert span.span_id == "span_123"
        assert span.parent_span_id is None
        assert span.trace_id == "trace_456"
        assert span.name == "test_span"
        assert span.kind == SpanKind.ROOT
        assert span.status == SpanStatus.STARTED
        assert span.duration_ms == 0.0
        assert span.end_time is None

    def test_span_finish_success(self):
        """跨度成功结束"""
        span = TraceSpan(
            span_id="s1", parent_span_id=None, trace_id="t1",
            name="op", kind=SpanKind.CUSTOM,
        )
        time.sleep(0.01)
        span.finish(SpanStatus.SUCCESS)
        assert span.status == SpanStatus.SUCCESS
        assert span.end_time is not None
        assert span.duration_ms > 0

    def test_span_finish_with_error(self):
        """跨度失败结束并附带错误信息"""
        span = TraceSpan(
            span_id="s1", parent_span_id=None, trace_id="t1",
            name="op", kind=SpanKind.CUSTOM,
        )
        span.finish(SpanStatus.FAILED, error="something went wrong")
        assert span.status == SpanStatus.FAILED
        assert span.error == "something went wrong"

    def test_span_finish_with_metadata(self):
        """结束时附加元数据"""
        span = TraceSpan(
            span_id="s1", parent_span_id=None, trace_id="t1",
            name="op", kind=SpanKind.CUSTOM,
            metadata={"key1": "val1"},
        )
        span.finish(metadata={"key2": "val2"})
        assert span.metadata["key1"] == "val1"
        assert span.metadata["key2"] == "val2"

    def test_span_to_dict(self):
        """跨度序列化"""
        span = TraceSpan(
            span_id="s1", parent_span_id="ps1", trace_id="t1",
            name="test", kind=SpanKind.GATE_JUDGE,
            module="mod", function="func",
            gate_name="比肩·劫财", element_boost=0.15,
            tbce_drift=0.25, correction_step=3, correction_delta=0.1,
        )
        span.finish(SpanStatus.SUCCESS, error="err" * 100)
        d = span.to_dict()
        assert d["span_id"] == "s1"
        assert d["parent_span_id"] == "ps1"
        assert d["trace_id"] == "t1"
        assert d["kind"] == "gate_judge"
        assert d["status"] == "success"
        assert d["module"] == "mod"
        assert d["gate_name"] == "比肩·劫财"
        assert d["element_boost"] == 0.15
        assert d["tbce_drift"] == 0.25
        assert d["correction_step"] == 3
        assert len(d["error"]) <= 200  # 错误截断
        assert "metadata" in d


# ============================================================================
# Trace 测试
# ============================================================================

class TestTrace:
    def test_create_trace(self):
        """创建追踪链"""
        trace = Trace(trace_id="t1", root_span_id="rs1")
        assert trace.trace_id == "t1"
        assert trace.root_span_id == "rs1"
        assert trace.status == SpanStatus.STARTED
        assert len(trace.spans) == 0
        assert trace.gate_pass_count == 0
        assert trace.gate_fail_count == 0

    def test_trace_finish_success(self):
        """追踪链成功结束"""
        trace = Trace(trace_id="t1", root_span_id="rs1")
        time.sleep(0.01)
        trace.finish(SpanStatus.SUCCESS)
        assert trace.status == SpanStatus.SUCCESS
        assert trace.end_time is not None
        assert trace.total_duration_ms > 0

    def test_trace_statistics_aggregation(self):
        """追踪链统计汇总正确"""
        trace = Trace(trace_id="t1", root_span_id="rs1")

        # 添加门禁跨度
        span1 = TraceSpan(
            span_id="s1", parent_span_id="rs1", trace_id="t1",
            name="gate1", kind=SpanKind.GATE_JUDGE,
        )
        span1.status = SpanStatus.SUCCESS
        trace.spans.append(span1)

        span2 = TraceSpan(
            span_id="s2", parent_span_id="rs1", trace_id="t1",
            name="gate2", kind=SpanKind.GATE_JUDGE,
        )
        span2.status = SpanStatus.FAILED
        trace.spans.append(span2)

        # 添加自修正跨度
        span3 = TraceSpan(
            span_id="s3", parent_span_id="rs1", trace_id="t1",
            name="corr1", kind=SpanKind.SELF_CORRECTION,
        )
        span3.status = SpanStatus.SUCCESS
        trace.spans.append(span3)

        # 添加 LLM 调用跨度
        span4 = TraceSpan(
            span_id="s4", parent_span_id="rs1", trace_id="t1",
            name="llm1", kind=SpanKind.LLM_CALL,
        )
        span4.status = SpanStatus.SUCCESS
        trace.spans.append(span4)

        # 添加混沌海跨度
        span5 = TraceSpan(
            span_id="s5", parent_span_id="rs1", trace_id="t1",
            name="chaos", kind=SpanKind.CUSTOM,
        )
        span5.status = SpanStatus.CHAOS_SEA
        trace.spans.append(span5)

        trace.finish(SpanStatus.SUCCESS)

        assert trace.gate_pass_count == 1
        assert trace.gate_fail_count == 1
        assert trace.correction_step_count == 1
        assert trace.correction_success_count == 1
        assert trace.llm_call_count == 1
        assert trace.chaos_sea_count == 1

    def test_trace_to_dict(self):
        """追踪链序列化"""
        trace = Trace(trace_id="t1", root_span_id="rs1")
        span = TraceSpan(
            span_id="s1", parent_span_id="rs1", trace_id="t1",
            name="test", kind=SpanKind.ROOT,
        )
        trace.spans.append(span)
        trace.finish(SpanStatus.SUCCESS)
        d = trace.to_dict()
        assert d["trace_id"] == "t1"
        assert d["span_count"] == 1
        assert "spans" in d
        assert "gate_pass_count" in d


# ============================================================================
# CorrectionAuditEntry 测试
# ============================================================================

class TestCorrectionAuditEntry:
    def test_create_entry(self):
        """创建审计条目"""
        entry = CorrectionAuditEntry(
            trace_id="t1",
            step_index=2,
            step_name="语义对齐",
            tech_name="semantic_alignment",
            status="success",
            gate_verdict={"passed": True},
            gate_passed=True,
            interrupted_reason="",
            delta=0.15,
            confidence=0.85,
            duration_ms=120.5,
        )
        assert entry.trace_id == "t1"
        assert entry.step_index == 2
        assert entry.gate_passed is True
        assert entry.delta == 0.15

    def test_entry_to_dict(self):
        """审计条目序列化"""
        entry = CorrectionAuditEntry(
            trace_id="t1", step_index=1, step_name="test",
            tech_name="tech", status="success",
            gate_verdict={"p": 1}, gate_passed=True,
            interrupted_reason="", delta=0.1, confidence=0.9,
            duration_ms=100.0,
        )
        d = entry.to_dict()
        assert d["trace_id"] == "t1"
        assert d["step"] == 1
        assert d["name"] == "test"
        assert d["gate_passed"] is True
        assert "delta" in d
        assert "confidence" in d


# ============================================================================
# TraceManager 单例模式测试
# ============================================================================

class TestTraceManagerSingleton:
    def test_singleton_instance(self):
        """TraceManager 是单例"""
        tm1 = TraceManager()
        tm2 = TraceManager()
        assert tm1 is tm2

    def test_reset_clears_state(self):
        """reset 方法清空状态"""
        tm = TraceManager()
        tm.start_trace("test")
        assert len(tm._active_traces) == 1
        tm.reset()
        assert len(tm._active_traces) == 0
        assert len(tm._completed_traces) == 0
        assert len(tm._audit_log) == 0


# ============================================================================
# TraceManager 追踪生命周期测试
# ============================================================================

class TestTraceManagerLifecycle:
    def test_start_trace(self):
        """开始新追踪"""
        tm = TraceManager()
        trace = tm.start_trace(name="inference_1", module="bazi")
        assert trace.trace_id.startswith("trace_")
        assert trace.root_span_id.startswith("span_")
        assert len(trace.spans) == 1  # 根跨度
        assert trace.spans[0].kind == SpanKind.ROOT
        assert trace.spans[0].name == "inference_1"
        assert trace.spans[0].module == "bazi"
        assert trace.trace_id in tm._active_traces

    def test_start_span(self, sample_trace_id):
        """创建子跨度"""
        tm = TraceManager()
        span = tm.start_span(
            trace_id=sample_trace_id,
            name="gate_judge_1",
            kind=SpanKind.GATE_JUDGE,
            module="twelve_gods",
            function="judge",
        )
        assert span is not None
        assert span.name == "gate_judge_1"
        assert span.kind == SpanKind.GATE_JUDGE
        assert span.parent_span_id is not None  # 默认使用根跨度

    def test_start_span_with_parent(self, sample_trace_id):
        """创建带指定父跨度的子跨度"""
        tm = TraceManager()
        parent = tm.start_span(
            trace_id=sample_trace_id,
            name="parent",
            kind=SpanKind.CUSTOM,
        )
        child = tm.start_span(
            trace_id=sample_trace_id,
            name="child",
            kind=SpanKind.CUSTOM,
            parent_span_id=parent.span_id,
        )
        assert child.parent_span_id == parent.span_id

    def test_start_span_nonexistent_trace(self):
        """对不存在的追踪创建跨度返回 None"""
        tm = TraceManager()
        span = tm.start_span(
            trace_id="nonexistent_trace",
            name="test",
            kind=SpanKind.CUSTOM,
        )
        assert span is None

    def test_finish_span(self, sample_trace_id):
        """结束跨度"""
        tm = TraceManager()
        span = tm.start_span(
            trace_id=sample_trace_id,
            name="op",
            kind=SpanKind.CUSTOM,
        )
        tm.finish_span(span, SpanStatus.SUCCESS)
        assert span.status == SpanStatus.SUCCESS
        assert span.end_time is not None

    def test_finish_trace(self, sample_trace_id):
        """结束追踪链并归档"""
        tm = TraceManager()
        assert sample_trace_id in tm._active_traces
        completed = tm.finish_trace(sample_trace_id)
        assert completed is not None
        assert completed.status == SpanStatus.SUCCESS
        assert sample_trace_id not in tm._active_traces
        assert len(tm._completed_traces) == 1

    def test_finish_nonexistent_trace(self):
        """结束不存在的追踪返回 None"""
        tm = TraceManager()
        result = tm.finish_trace("nonexistent")
        assert result is None

    def test_completed_traces_ring_buffer(self):
        """已完成追踪环形缓冲区"""
        tm = TraceManager()
        tm._max_completed_traces = 5
        for i in range(10):
            trace = tm.start_trace(name=f"trace_{i}")
            tm.finish_trace(trace.trace_id)
        assert len(tm._completed_traces) == 5


# ============================================================================
# TraceManager 门禁追踪测试
# ============================================================================

class TestTraceManagerGateJudge:
    def test_trace_gate_judge_passed(self, sample_trace_id):
        """追踪通过的门禁裁决"""
        tm = TraceManager()

        mock_verdict = MagicMock()
        mock_verdict.passed = True
        mock_verdict.to_dict.return_value = {"passed": True, "score": 0.85}

        span = tm.trace_gate_judge(
            trace_id=sample_trace_id,
            gate_name="比肩·劫财",
            verdict=mock_verdict,
            element_boost=0.1,
        )
        assert span is not None
        assert span.kind == SpanKind.GATE_JUDGE
        assert span.status == SpanStatus.SUCCESS
        assert span.gate_name == "比肩·劫财"
        assert span.element_boost == 0.1
        assert span.gate_verdict == {"passed": True, "score": 0.85}

    def test_trace_gate_judge_failed(self, sample_trace_id):
        """追踪失败的门禁裁决"""
        tm = TraceManager()

        mock_verdict = MagicMock()
        mock_verdict.passed = False
        mock_verdict.to_dict.return_value = {"passed": False, "reason": "score too low"}

        span = tm.trace_gate_judge(
            trace_id=sample_trace_id,
            gate_name="七杀·品质裁决",
            verdict=mock_verdict,
        )
        assert span is not None
        assert span.status == SpanStatus.FAILED

    def test_trace_gate_judge_with_state_attr(self, sample_trace_id):
        """裁决对象使用 state 属性（GateState 风格）"""
        tm = TraceManager()

        mock_verdict = MagicMock()
        del mock_verdict.passed
        mock_verdict.state = MagicMock()
        mock_verdict.state.value = "open"
        mock_verdict.to_dict.return_value = {"state": "open"}

        span = tm.trace_gate_judge(
            trace_id=sample_trace_id,
            gate_name="test_gate",
            verdict=mock_verdict,
        )
        assert span.status == SpanStatus.SUCCESS

    def test_trace_gate_judge_nonexistent_trace(self):
        """对不存在的追踪追踪门禁返回 None"""
        tm = TraceManager()
        mock_verdict = MagicMock()
        mock_verdict.passed = True
        result = tm.trace_gate_judge("nonexistent", "gate", mock_verdict)
        assert result is None

    def test_trace_gate_judge_to_dict_fallback(self, sample_trace_id):
        """裁决对象 to_dict 失败时回退到字符串表示"""
        tm = TraceManager()

        class BadVerdict:
            passed = True
            def to_dict(self):
                raise RuntimeError("cannot serialize")

        span = tm.trace_gate_judge(
            trace_id=sample_trace_id,
            gate_name="test",
            verdict=BadVerdict(),
        )
        assert span.gate_verdict is not None
        assert "state" in span.gate_verdict


# ============================================================================
# TraceManager 自修正审计测试
# ============================================================================

class TestTraceManagerCorrectionAudit:
    def test_trace_correction_step_success(self, sample_trace_id):
        """追踪成功的自修正步骤"""
        tm = TraceManager()
        span = tm.trace_correction_step(
            trace_id=sample_trace_id,
            step_index=1,
            step_name="语义对齐",
            tech_name="semantic_alignment",
            status="success",
            gate_passed=True,
            gate_verdict={"passed": True},
            interrupted_reason="",
            delta=0.15,
            confidence=0.85,
            duration_ms=120.0,
        )
        assert span is not None
        assert span.kind == SpanKind.SELF_CORRECTION
        assert span.status == SpanStatus.SUCCESS
        assert span.correction_step == 1
        assert span.correction_name == "语义对齐"
        assert span.correction_delta == 0.15
        assert len(tm._audit_log) == 1

    def test_trace_correction_step_interrupted(self, sample_trace_id):
        """追踪被中断的自修正步骤"""
        tm = TraceManager()
        span = tm.trace_correction_step(
            trace_id=sample_trace_id,
            step_index=2,
            step_name="混沌探索",
            tech_name="chaos_exploration",
            status="interrupted",
            gate_passed=False,
            gate_verdict={"passed": False},
            interrupted_reason="门禁否决",
            delta=0.05,
            confidence=0.5,
            duration_ms=50.0,
        )
        assert span.status == SpanStatus.INTERRUPTED
        assert span.error == "门禁否决"

    def test_trace_correction_step_failed(self, sample_trace_id):
        """追踪失败的自修正步骤"""
        tm = TraceManager()
        span = tm.trace_correction_step(
            trace_id=sample_trace_id,
            step_index=3,
            step_name="质量校验",
            tech_name="quality_check",
            status="failed",
            gate_passed=False,
            gate_verdict={"passed": False},
            interrupted_reason="质量不达标",
            delta=0.0,
            confidence=0.3,
            duration_ms=200.0,
        )
        assert span.status == SpanStatus.FAILED

    def test_trace_correction_nonexistent_trace(self):
        """对不存在的追踪追踪修正步骤返回 None"""
        tm = TraceManager()
        result = tm.trace_correction_step(
            "nonexistent", 1, "step", "tech", "success",
            True, {}, "", 0.1, 0.9, 100.0,
        )
        assert result is None

    def test_audit_log_ring_buffer(self, sample_trace_id):
        """审计日志环形缓冲区"""
        tm = TraceManager()
        tm._max_audit_entries = 10
        for i in range(20):
            tm.trace_correction_step(
                sample_trace_id, i, f"step_{i}", f"tech_{i}",
                "success", True, {}, "", 0.1, 0.9, 10.0,
            )
        assert len(tm._audit_log) == 10


# ============================================================================
# TraceManager TBCE 漂移追踪测试
# ============================================================================

class TestTraceManagerTBCEDrift:
    def test_trace_tbce_drift_normal(self, sample_trace_id):
        """正常范围内的 TBCE 漂移"""
        tm = TraceManager()
        span = tm.trace_tbce_drift(
            trace_id=sample_trace_id,
            unit_name="test_unit",
            coords_before={"S": 0.5, "T": 0.5},
            coords_after={"S": 0.55, "T": 0.52},
            drift=0.1,
        )
        assert span is not None
        assert span.kind == SpanKind.TBCE_DRIFT
        assert span.status == SpanStatus.SUCCESS
        assert span.tbce_drift == 0.1

    def test_trace_tbce_drift_warning(self, sample_trace_id):
        """警告级别的 TBCE 漂移 (0.3-0.5)"""
        tm = TraceManager()
        span = tm.trace_tbce_drift(
            trace_id=sample_trace_id,
            unit_name="drifting_unit",
            coords_before={"S": 0.5},
            coords_after={"S": 0.9},
            drift=0.4,
        )
        assert span.status == SpanStatus.INTERRUPTED

    def test_trace_tbce_drift_critical(self, sample_trace_id):
        """严重级别的 TBCE 漂移 (>0.5)"""
        tm = TraceManager()
        span = tm.trace_tbce_drift(
            sample_trace_id, "critical_unit",
            {"S": 0.1}, {"S": 0.9}, drift=0.8,
        )
        assert span.status == SpanStatus.FAILED

    def test_trace_tbce_drift_nonexistent_trace(self):
        """对不存在的追踪追踪漂移返回 None"""
        tm = TraceManager()
        result = tm.trace_tbce_drift("nonexistent", "u", {}, {}, 0.1)
        assert result is None


# ============================================================================
# TraceManager 查询与统计测试
# ============================================================================

class TestTraceManagerQueries:
    def test_get_trace_active(self, sample_trace_id):
        """获取活跃追踪"""
        tm = TraceManager()
        result = tm.get_trace(sample_trace_id)
        assert result is not None
        assert result["trace_id"] == sample_trace_id

    def test_get_trace_completed(self):
        """获取已完成追踪"""
        tm = TraceManager()
        trace = tm.start_trace(name="completed")
        trace_id = trace.trace_id
        tm.finish_trace(trace_id)
        result = tm.get_trace(trace_id)
        assert result is not None
        assert result["status"] == "success"

    def test_get_trace_nonexistent(self):
        """获取不存在的追踪返回 None"""
        tm = TraceManager()
        result = tm.get_trace("nonexistent")
        assert result is None

    def test_get_active_traces(self):
        """获取所有活跃追踪"""
        tm = TraceManager()
        tm.start_trace(name="trace1")
        tm.start_trace(name="trace2")
        active = tm.get_active_traces()
        assert len(active) == 2

    def test_get_completed_traces(self):
        """获取最近完成的追踪"""
        tm = TraceManager()
        for i in range(5):
            t = tm.start_trace(name=f"t{i}")
            tm.finish_trace(t.trace_id)
        completed = tm.get_completed_traces(limit=3)
        assert len(completed) == 3

    def test_get_audit_log(self, sample_trace_id):
        """查询审计日志"""
        tm = TraceManager()
        for i in range(5):
            tm.trace_correction_step(
                sample_trace_id, i, f"step{i}", f"tech{i}",
                "success", True, {}, "", 0.1, 0.9, 10.0,
            )
        log = tm.get_audit_log(limit=3)
        assert len(log) == 3

    def test_get_audit_log_by_trace(self, sample_trace_id):
        """按追踪ID过滤审计日志"""
        tm = TraceManager()
        t2 = tm.start_trace(name="other")
        tm.trace_correction_step(
            sample_trace_id, 1, "s1", "t1",
            "success", True, {}, "", 0.1, 0.9, 10.0,
        )
        tm.trace_correction_step(
            t2.trace_id, 1, "s2", "t2",
            "success", True, {}, "", 0.1, 0.9, 10.0,
        )
        log = tm.get_audit_log(trace_id=sample_trace_id)
        assert len(log) == 1
        assert log[0]["trace_id"] == sample_trace_id

    def test_get_audit_log_by_step(self, sample_trace_id):
        """按步骤索引过滤审计日志"""
        tm = TraceManager()
        for i in range(3):
            tm.trace_correction_step(
                sample_trace_id, i, f"step{i}", f"tech{i}",
                "success", True, {}, "", 0.1, 0.9, 10.0,
            )
        log = tm.get_audit_log(step_index=1)
        assert len(log) == 1
        assert log[0]["step"] == 1

    def test_get_audit_summary(self, sample_trace_id):
        """获取审计摘要"""
        tm = TraceManager()
        tm.trace_correction_step(
            sample_trace_id, 1, "s1", "t1",
            "success", True, {}, "", 0.1, 0.9, 10.0,
        )
        tm.trace_correction_step(
            sample_trace_id, 2, "s2", "t2",
            "interrupted", False, {}, "veto", 0.0, 0.5, 20.0,
        )
        summary = tm.get_audit_summary()
        assert summary["total_entries"] == 2
        assert summary["passed"] == 1
        assert summary["interrupted"] == 1
        assert summary["failed"] == 0
        assert "pass_rate" in summary
        assert "by_step" in summary

    def test_get_audit_summary_empty(self):
        """空审计日志摘要"""
        tm = TraceManager()
        summary = tm.get_audit_summary()
        assert summary["total_entries"] == 0

    def test_get_trace_stats(self):
        """获取追踪统计"""
        tm = TraceManager()
        for i in range(3):
            t = tm.start_trace(name=f"t{i}")
            tm.finish_trace(t.trace_id)
        stats = tm.get_trace_stats()
        assert stats["total_traces"] == 3
        assert stats["active_traces"] == 0
        assert stats["success_rate"] == 1.0
        assert "avg_duration_ms" in stats

    def test_get_trace_stats_empty(self):
        """无追踪时的统计"""
        tm = TraceManager()
        stats = tm.get_trace_stats()
        assert stats["total_traces"] == 0


# ============================================================================
# TraceManager 推理链构建测试
# ============================================================================

class TestInferenceChain:
    def test_build_simple_chain(self, sample_trace_id):
        """构建简单推理链"""
        tm = TraceManager()
        tm.trace_gate_judge(
            sample_trace_id, "gate1",
            MagicMock(passed=True, to_dict=lambda: {"p": True}),
        )
        tm.finish_trace(sample_trace_id)

        chain = tm.get_inference_chain(sample_trace_id)
        assert chain is not None
        assert chain["trace_id"] == sample_trace_id
        assert "chain" in chain
        assert chain["chain"]["name"] is not None
        assert "children" in chain["chain"]

    def test_nested_span_chain(self, sample_trace_id):
        """嵌套跨度的推理链"""
        tm = TraceManager()
        parent = tm.start_span(
            sample_trace_id, "parent_op", SpanKind.CUSTOM,
        )
        tm.start_span(
            sample_trace_id, "child_op", SpanKind.LLM_CALL,
            parent_span_id=parent.span_id,
        )
        tm.finish_trace(sample_trace_id)

        chain = tm.get_inference_chain(sample_trace_id)
        assert chain is not None
        # 根跨度至少有一个子跨度（parent_op）
        assert len(chain["chain"]["children"]) >= 1

    def test_nonexistent_trace_chain(self):
        """不存在的追踪返回 None"""
        tm = TraceManager()
        chain = tm.get_inference_chain("nonexistent")
        assert chain is None


# ============================================================================
# TraceManager 并发安全测试
# ============================================================================

class TestTraceManagerConcurrency:
    def test_multithreaded_trace_creation(self):
        """多线程并发创建追踪（验证并发安全，不要求精确数量）"""
        tm = TraceManager()
        tm.reset()

        errors = []
        started_ids = []
        lock = threading.Lock()

        def create_traces(n, thread_id):
            try:
                local_ids = []
                for i in range(n):
                    t = tm.start_trace(name=f"thread_{thread_id}_trace_{i}")
                    tm.start_span(t.trace_id, f"span_{i}", SpanKind.CUSTOM)
                    local_ids.append(t.trace_id)
                    tm.finish_trace(t.trace_id)
                with lock:
                    started_ids.extend(local_ids)
            except Exception as e:
                errors.append(e)

        threads = []
        for tid in range(5):
            t = threading.Thread(target=create_traces, args=(20, tid))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        assert len(errors) == 0
        assert len(started_ids) == 100
        assert len(tm._completed_traces) > 0
        assert len(tm._completed_traces) <= 100

    def test_concurrent_audit_log_writes(self, sample_trace_id):
        """多线程并发写入审计日志"""
        tm = TraceManager()
        errors = []

        def write_audits(n, offset):
            try:
                for i in range(n):
                    tm.trace_correction_step(
                        sample_trace_id,
                        offset + i,
                        f"step_{offset + i}",
                        f"tech_{offset + i}",
                        "success",
                        True,
                        {},
                        "",
                        0.1,
                        0.9,
                        10.0,
                    )
            except Exception as e:
                errors.append(e)

        threads = []
        for i in range(5):
            t = threading.Thread(target=write_audits, args=(20, i * 20))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        assert len(errors) == 0
