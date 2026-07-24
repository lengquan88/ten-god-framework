"""
test_latent_image.py — 潜影门禁与记忆固化测试 v2.26.0
"""
import pytest
import math

from tengod.tbce_unit import GateState
from tengod.latent_image import (
    MemoryTrace, VerificationResult, VerificationGate,
    Retrospection, RetrospectionResult, LatentImageEngine,
)


# ── Fixtures ──────────────────────────────────────────────

@pytest.fixture
def retro():
    return Retrospection()


@pytest.fixture
def engine():
    return LatentImageEngine()


# ── 1. MemoryTrace ────────────────────────────────────────

class TestMemoryTrace:
    def test_create(self):
        trace = MemoryTrace(
            trace_id="test",
            content={"key": "value"},
            confidence=0.8,
            source="inference",
            trace_level=1,
        )
        assert trace.trace_id == "test"
        assert trace.verified is False
        assert trace.consolidated is False

    def test_compute_hash(self):
        trace = MemoryTrace(
            trace_id="test",
            content={"a": "b"},
            confidence=0.5,
            source="test",
            trace_level=1,
        )
        h = trace.compute_hash()
        assert len(h) == 16
        assert isinstance(h, str)

    def test_hash_consistent(self):
        t1 = MemoryTrace("t1", {"a": "b"}, 0.5, "test", 1)
        t2 = MemoryTrace("t2", {"a": "b"}, 0.5, "test", 1)
        assert t1.compute_hash() == t2.compute_hash()


# ── 2. VerificationResult ─────────────────────────────────

class TestVerificationResult:
    def test_create(self):
        result = VerificationResult(
            verified=True,
            confidence=0.9,
            method="self_consistency",
            evidence=["consistent"],
            contradictions=[],
            retrospection_score=0.8,
        )
        assert result.verified is True
        assert result.confidence == 0.9


# ── 3. VerificationGate ───────────────────────────────────

class TestVerificationGate:
    def test_all_passed(self):
        gate = VerificationGate(required_methods=2)
        results = [
            VerificationResult(True, 0.9, "m1", ["e1"], [], 0.8),
            VerificationResult(True, 0.85, "m2", ["e2"], [], 0.8),
        ]
        trace = MemoryTrace("t", {}, 0.5, "test", 1)
        retro = RetrospectionResult(
            original_chain=[], retrospected_chain=[],
            consistency_score=0.95, gaps_found=[], corrections=[],
            score=0.95,
        )
        final = gate.verify(trace, results, retro)
        assert final.verified is True
        assert final.confidence > 0.6

    def test_not_enough_passed(self):
        gate = VerificationGate(required_methods=2)
        results = [
            VerificationResult(True, 0.9, "m1", ["e1"], [], 0.8),
            VerificationResult(False, 0.3, "m2", [], ["c1"], 0.5),
        ]
        trace = MemoryTrace("t", {}, 0.5, "test", 1)
        final = gate.verify(trace, results)
        assert final.verified is False

    def test_judge_open(self):
        gate = VerificationGate()
        trace = MemoryTrace("t", {}, 0.5, "test", 1)
        final = VerificationResult(True, 0.95, "test", ["e"], [], 0.9)
        state, reason = gate.judge(trace, final)
        assert state == GateState.OPEN

    def test_judge_pending(self):
        gate = VerificationGate()
        trace = MemoryTrace("t", {}, 0.5, "test", 1)
        final = VerificationResult(True, 0.7, "test", ["e"], [], 0.7)
        state, reason = gate.judge(trace, final)
        assert state == GateState.PENDING

    def test_judge_closed(self):
        gate = VerificationGate()
        trace = MemoryTrace("t", {}, 0.5, "test", 1)
        final = VerificationResult(False, 0.2, "test", [], ["c1", "c2"], 0.3)
        state, reason = gate.judge(trace, final)
        assert state == GateState.CLOSED


# ── 4. Retrospection ──────────────────────────────────────

class TestRetrospection:
    def test_retrospect_connected(self, retro):
        chain = [
            "宇宙的终极答案是42",
            "因此42是正确的答案",
        ]
        result = retro.retrospect(chain, "42是正确的", ["宇宙", "答案"])
        assert isinstance(result, RetrospectionResult)
        # 即使两个词都有"宇宙"和"答案"，也会发现最终结论没用到前提
        # 但一致性应该 >= 0.4
        assert result.consistency_score > 0.4
        assert result.score > 0.2

    def test_retrospect_gap_found(self, retro):
        chain = [
            "第一步：关于宇宙",
            "第二步：完全无关的讨论",
        ]
        result = retro.retrospect(chain, "结论", ["前提"])
        assert isinstance(result, RetrospectionResult)
        # 前后不相关 → 应该有断层
        assert len(result.gaps_found) > 0

    def test_retrospect_unused_premises(self, retro):
        chain = ["只涉及主题A", "也只涉及主题A"]
        result = retro.retrospect(chain, "A", ["主题B"])
        assert len(result.gaps_found) > 0
        assert "主题B" in str(result.gaps_found)


# ── 5. LatentImageEngine ──────────────────────────────────

class TestLatentImageEngine:
    def test_process(self, engine):
        trace, ver, gate = engine.process(
            content={"result": "42"},
            reasoning_chain=["前提", "推论"],
            conclusion="结论",
            premises=["前提"],
            confidence=0.8,
        )
        assert isinstance(trace, MemoryTrace)
        assert isinstance(ver, VerificationResult)
        assert gate in (GateState.OPEN, GateState.PENDING, GateState.CLOSED)

    def test_force_consolidate(self, engine):
        trace, ver, gate = engine.process(
            content={"result": "42"},
            reasoning_chain=["前提", "推论"],
            conclusion="结论",
            premises=["前提"],
        )
        ok, reason = engine.consolidate(trace.trace_id, force=True)
        assert ok is True
        assert trace.consolidated is True
        assert trace.trace_level == 3

    def test_consolidate_fails_without_force(self, engine):
        trace, ver, gate = engine.process(
            content={"result": "42"},
            reasoning_chain=["a", "b"],
            conclusion="b",
            premises=["a"],
        )
        if not trace.verified:
            ok, reason = engine.consolidate(trace.trace_id, force=False)
            assert ok is False

    def test_get_consolidated_memories(self, engine):
        trace, _, _ = engine.process(
            content={"r": "1"},
            reasoning_chain=["a", "b"],
            conclusion="b",
            premises=["a"],
        )
        engine.consolidate(trace.trace_id, force=True)
        memories = engine.get_consolidated_memories()
        assert len(memories) == 1

    def test_get_memory(self, engine):
        trace, _, _ = engine.process(
            content={"r": "1"},
            reasoning_chain=["a", "b"],
            conclusion="b",
            premises=["a"],
        )
        found = engine.get_memory(trace.trace_id)
        assert found is not None
        assert found.trace_id == trace.trace_id

    def test_get_memory_not_found(self, engine):
        assert engine.get_memory("nonexistent") is None

    def test_statistics(self, engine):
        engine.process(
            content={"r": "1"},
            reasoning_chain=["a", "b"],
            conclusion="b",
            premises=["a"],
        )
        stats = engine.get_statistics()
        assert stats["total_traces"] == 1
        assert "verification_rate" in stats
        assert "consolidation_rate" in stats


# ── 6. Integration ────────────────────────────────────────

class TestIntegration:
    def test_full_pipeline(self):
        engine = LatentImageEngine()
        trace, ver, gate = engine.process(
            content={"answer": "42"},
            reasoning_chain=[
                "根据已知信息，宇宙的终极答案是42",
                "经过验证，42确实是正确答案",
                "因此可以得出结论：42是正确的",
            ],
            conclusion="42是正确的",
            premises=["宇宙终极答案", "42", "验证通过"],
            confidence=0.85,
        )
        assert trace is not None
        assert ver is not None
        assert isinstance(trace.trace_id, str)
        engine.consolidate(trace.trace_id, force=True)
        assert len(engine.get_consolidated_memories()) == 1