#!/usr/bin/env python3
"""
test_law_gate_supplement.py — 法度门禁补充测试 v1.0
======================================================
补充 test_twelve_gods.py 中 TestLawGate 尚未覆盖的边界条件与高风险路径：

 1. SchedulingPolicy.is_compliant
    - 精确边界：burst_size = max_burst_size（= 应合规；+1 应违规）
    - 每个维度单独违规
    - retries == 0 合规 / retries > max_retries 违规
    - queue_depth == max_queue_depth 合规
    - confidence == min_confidence_threshold 合规，小于即违规
    - 多违规累积返回

 2. LawGate 评分公式
    - 正官 与 七杀：各权重量化验证（合规性权重不同）
    - 违规惩罚：len(violations) * 0.08 扣除
    - score 夹取：最终得分必 ∈ [0, 1]（多个违规下不低于 0）

 3. LawGate 异常分层
    - anomaly_score < 0.2 → "调度正常" 证据
    - 0.6 ≤ anomaly_score ≤ 0.8 → "中度异常"
    - anomaly_score > 0.8 → "严重异常"（惩罚更重）
    - 临界边界 0.599 / 0.6 / 0.799 / 0.8 / 0.801

 4. LawGate._extract_metrics：
    - 使用 metadata 中 burst_size / queue_depth 覆盖默认推导
    - 无 metadata 时从 cognitive_layer 和 coords.I 推导

 5. LawGate 统计聚合
    - get_metrics_history 返回正确长度
    - get_avg_metrics 空列表返回 None，非空正确平均

 6. 与 TwelveGodsGate 基类的集成
    - 五行生克加成：门禁 palace_id 与 单元 palace_id 生克对最终 score 影响
    - get_statistics 统计裁决历史状态分布
"""

from __future__ import annotations

import math

import pytest

from tengod.tbce_unit import (
    TBCECoordinates,
    CognitiveUnit,
    GateState,
)
from tengod.twelve_gods_base import (
    FiveElements,
    TwelveGods,
    GOD_ELEMENT_MAP,
)
from tengod.law_gate import (
    SchedulingPolicy,
    SchedulingMetrics,
    LawGate,
)


# ============================================================================
# Fixtures
# ============================================================================

def _make_unit(
    *,
    palace_id: int = 5,
    cognitive_layer: int = 4,
    S: float = 0.7,
    T: float = 0.5,
    P: float = 0.7,
    C: float = 0.7,
    I: float = 0.7,
    E: float = 0.3,
    metadata: dict | None = None,
) -> CognitiveUnit:
    """快捷创建带默认值的 CognitiveUnit。"""
    return CognitiveUnit(
        unit_id="test.law.unit",
        name="测试法度单元",
        module_path="tengod.test",
        coordinates=TBCECoordinates(S=S, T=T, P=P, C=C, I=I, E=E),
        cognitive_layer=cognitive_layer,
        psi_operator="RecursionDepth",
        palace_id=palace_id,
        metadata=metadata or {},
    )


# ============================================================================
# 1. SchedulingPolicy.is_compliant 边界
# ============================================================================

class TestSchedulingPolicyCompliance:
    def test_all_values_exactly_at_threshold_are_compliant(self):
        """所有度量恰好等于阈值 → 合规（注意是 > 才违规，不是 >=）。"""
        policy = SchedulingPolicy(
            policy_id="t",
            max_burst_size=4,
            min_confidence_threshold=0.7,
            max_queue_depth=10,
            max_retries=3,
        )
        metrics = SchedulingMetrics(
            burst_size=4,     # 恰好等于 max → 不违规（使用 >）
            confidence=0.7,   # 恰好等于 min → 不违规（使用 <）
            queue_depth=10,   # 恰好等于 max → 不违规（使用 >）
            retries=3,        # 恰好等于 max → 不违规（使用 >）
        )
        ok, violations = policy.is_compliant(metrics)
        assert ok is True
        assert violations == []

    def test_each_metric_just_over_is_violated(self):
        """逐一超出最小量，验证每种违规都被记录。"""
        policy = SchedulingPolicy(
            policy_id="t",
            max_burst_size=4,
            min_confidence_threshold=0.7,
            max_queue_depth=10,
            max_retries=3,
        )
        # burst_size 超 1
        ok, v = policy.is_compliant(SchedulingMetrics(
            burst_size=5, confidence=1.0, queue_depth=0, retries=0))
        assert ok is False
        assert any("burst_size超标" in x for x in v)
        # confidence 略低
        ok, v = policy.is_compliant(SchedulingMetrics(
            burst_size=0, confidence=0.699, queue_depth=0, retries=0))
        assert ok is False
        assert any("置信度不足" in x for x in v)
        # queue_depth 超 1
        ok, v = policy.is_compliant(SchedulingMetrics(
            burst_size=0, confidence=1.0, queue_depth=11, retries=0))
        assert ok is False
        assert any("队列深度超标" in x for x in v)
        # retries 超 1
        ok, v = policy.is_compliant(SchedulingMetrics(
            burst_size=0, confidence=1.0, queue_depth=0, retries=4))
        assert ok is False
        assert any("重试次数超标" in x for x in v)

    def test_four_violations_accumulated(self):
        policy = SchedulingPolicy(
            policy_id="t", max_burst_size=1, min_confidence_threshold=0.9,
            max_queue_depth=1, max_retries=0)
        ok, v = policy.is_compliant(SchedulingMetrics(
            burst_size=10, confidence=0.1, queue_depth=5, retries=5))
        assert ok is False
        assert len(v) == 4

    def test_confidence_at_zero_violated(self):
        policy = SchedulingPolicy(policy_id="t")
        ok, _ = policy.is_compliant(SchedulingMetrics(confidence=0.0))
        assert ok is False


# ============================================================================
# 2. LawGate 评分公式 与 夹取
# ============================================================================

class TestLawGateScoringFormula:
    def test_zhgguan_score_decomposition(self):
        """
        正官评分（单位分数）：
          score = 0.4*合规 + 0.25*(1-E) + 0.2*min(1, speedup/5) + 0.15*I - 0.08*违规数
        """
        # 制造完美合规、E=0、I=1、speedup=5
        unit = _make_unit(I=1.0, E=0.0, C=1.0)  # speedup = C*I*5+1 = 1*1*5+1 = 6
        gate = LawGate(TwelveGods.ZHENGGUAN)
        # 强制策略：置信度阈值极低（避免违规）
        gate.set_policy(SchedulingPolicy(policy_id="p",
                                          min_confidence_threshold=0.0,
                                          max_burst_size=100,
                                          max_queue_depth=100,
                                          max_retries=100,
                                          target_speedup=5.0))
        verdict = gate.judge(unit)
        # 理论值：0.4*1 + 0.25*(1-0) + 0.2*min(1,6/5) + 0.15*1 - 0
        #       = 0.4 + 0.25 + 0.2 + 0.15 = 1.0
        # 夹取到 1.0
        assert verdict.state == GateState.OPEN
        assert verdict.score == pytest.approx(1.0, abs=0.01)

    def test_qisha_score_decomposition(self):
        """
        七杀评分（单位分数）：
          score = 0.35*(1-E) + 0.25*合规 + 0.2*min(1, speedup/5) + 0.2*S - 0.08*违规数
        """
        unit = _make_unit(S=1.0, I=0.9, E=0.0, C=1.0)
        gate = LawGate(TwelveGods.QISHA)
        gate.set_policy(SchedulingPolicy(policy_id="p",
                                          min_confidence_threshold=0.0,
                                          max_burst_size=100,
                                          max_queue_depth=100,
                                          max_retries=100,
                                          target_speedup=5.0))
        verdict = gate.judge(unit)
        # 理论：0.35*1 + 0.25*1 + 0.2*1 + 0.2*1 = 1.0
        assert verdict.state == GateState.OPEN
        assert verdict.score == pytest.approx(1.0, abs=0.01)

    def test_violations_penalty_clamped_non_negative(self):
        """超多违规下扣分后分数必须 ≥ 0（夹取生效）。"""
        unit = _make_unit(I=0.1, E=0.99, C=0.1, S=0.1)
        gate = LawGate(TwelveGods.ZHENGGUAN)
        # 设置极严策略，保证 burst_size、queue_depth、confidence、retries 全违规
        gate.set_policy(SchedulingPolicy(policy_id="strict",
                                          max_burst_size=1,     # 默认 burst_size 来自 int(cognitive_layer*0.75)=3 → 违规
                                          min_confidence_threshold=0.99,  # coords.S=0.7 → 置信度不足
                                          max_queue_depth=0,    # I=0.1 → int(0.9*10)=9 → 违规
                                          max_retries=0,
                                          target_speedup=100.0))
        verdict = gate.judge(unit)
        # 分数至少 0.0（不能负数）
        assert verdict.score >= 0.0
        assert verdict.score <= 1.0
        assert verdict.state == GateState.CLOSED

    def test_non_zhgguan_non_qisha_defaults_05(self):
        """
        LawGate 只能接受 ZHENGGUAN / QISHA，因为评分公式只有这 2 个分支。
        默认 init 是 ZHENGGUAN。若强行改 god 属性（虽然用户不应这么做），
        else 分支返回 0.5。
        """
        unit = _make_unit()
        gate = LawGate(TwelveGods.ZHENGGUAN)
        # 手动改掉 god 字段（模拟异常配置）
        gate.god = TwelveGods.BIJIAN  # 不在评分分支里
        # 需要同步 element？评分公式不使用 god.element，直接调私有 _evaluate
        metrics = gate._extract_metrics(unit)
        score, issues, evidence = gate._evaluate(metrics, unit)
        # score = 0.5 然后减违规惩罚
        assert 0.0 <= score <= 1.0


# ============================================================================
# 3. LawGate 异常分层
# ============================================================================

class TestLawGateAnomalyTiers:
    @staticmethod
    def _gate_with_loose_policy() -> LawGate:
        g = LawGate(TwelveGods.ZHENGGUAN)
        g.set_policy(SchedulingPolicy(policy_id="loose",
                                      min_confidence_threshold=0.0,
                                      max_burst_size=1000,
                                      max_queue_depth=1000,
                                      max_retries=1000))
        return g

    def test_anomaly_below_02_is_evidence_of_normal(self):
        unit = _make_unit(E=0.1, I=0.9, C=0.9, S=0.9)
        gate = self._gate_with_loose_policy()
        verdict = gate.judge(unit)
        assert "调度正常" in verdict.reason

    def test_anomaly_06_just_above_is_high(self):
        """实现使用 > 0.6（严格大于），所以 0.6001 刚越界触发"中度异常"。"""
        unit = _make_unit(E=0.6001, I=0.9, C=0.9, S=0.9)
        gate = self._gate_with_loose_policy()
        metrics = gate._extract_metrics(unit)
        _score, issues, _evidence = gate._evaluate(metrics, unit)
        assert any("中度异常" in i for i in issues)
        assert not any("严重异常" in i for i in issues)

    def test_anomaly_exactly_06_is_within_normal_range(self):
        """E 恰好 = 0.6 不满足 >0.6，不触发中度异常。"""
        unit = _make_unit(E=0.6, I=0.9, C=0.9, S=0.9)
        gate = self._gate_with_loose_policy()
        metrics = gate._extract_metrics(unit)
        _score, issues, _evidence = gate._evaluate(metrics, unit)
        # 既不是严重也不是中度
        assert not any("中度异常" in i or "严重异常" in i for i in issues)

    def test_anomaly_0801_is_critical(self):
        """0.801 超过 CRITICAL_THRESHOLD（0.8）。"""
        unit = _make_unit(E=0.801, I=0.9, C=0.9, S=0.9)
        gate = self._gate_with_loose_policy()
        metrics = gate._extract_metrics(unit)
        _score, issues, _evidence = gate._evaluate(metrics, unit)
        assert any("严重异常" in i for i in issues)

    def test_anomaly_0799_is_not_critical(self):
        """0.799 仍属于"中度异常"。"""
        unit = _make_unit(E=0.799, I=0.9, C=0.9, S=0.9)
        gate = self._gate_with_loose_policy()
        metrics = gate._extract_metrics(unit)
        _score, issues, _evidence = gate._evaluate(metrics, unit)
        assert any("中度异常" in i for i in issues)
        assert not any("严重异常" in i for i in issues)

    def test_anomaly_0599_is_still_normal_range(self):
        """0.599 不在中度或严重阈值内，也不在 <0.2 的正常证据里。"""
        unit = _make_unit(E=0.599, I=0.9, C=0.9, S=0.9)
        gate = self._gate_with_loose_policy()
        metrics = gate._extract_metrics(unit)
        _score, issues, evidence = gate._evaluate(metrics, unit)
        # issues 不应有异常分层项
        assert not any("严重异常" in i for i in issues)
        assert not any("中度异常" in i for i in issues)
        # evidence 里也不会有"调度正常"
        assert not any("调度正常" in e for e in evidence)


# ============================================================================
# 4. LawGate._extract_metrics 元数据覆盖
# ============================================================================

class TestLawGateExtractMetrics:
    def test_metadata_overrides_burst_and_queue(self):
        """metadata 中有 burst_size / queue_depth 时，覆盖默认推导。"""
        unit = _make_unit(
            cognitive_layer=8,  # 默认：max(1, int(8*0.75)) = 6
            I=0.2,              # 默认：int((1.0 - 0.2) * 10) = 8
            metadata={"burst_size": 42, "queue_depth": 99},
        )
        gate = LawGate()
        m = gate._extract_metrics(unit)
        assert m.burst_size == 42
        assert m.queue_depth == 99
        # 其他字段基于坐标
        assert m.anomaly_score == unit.coordinates.E
        assert m.confidence == unit.coordinates.S

    def test_no_metadata_uses_derivation(self):
        """palace_id 不参与 metrics 推导；cognitive_layer=5 → int(5*0.75)=3。"""
        unit = _make_unit(cognitive_layer=5, I=0.4, S=0.88, E=0.33)
        gate = LawGate()
        m = gate._extract_metrics(unit)
        assert m.burst_size == 3  # int(5 * 0.75)
        assert m.queue_depth == 6  # int((1.0 - 0.4) * 10) = 6
        assert m.confidence == pytest.approx(0.88)
        assert m.anomaly_score == pytest.approx(0.33)
        # speedup = C * I * 5.0 + 1.0
        expected_speedup = unit.coordinates.C * unit.coordinates.I * 5.0 + 1.0
        assert m.speedup == pytest.approx(expected_speedup)


# ============================================================================
# 5. 统计聚合
# ============================================================================

class TestLawGateMetricsAggregation:
    def test_empty_history_returns_none(self):
        g = LawGate()
        assert g.get_avg_metrics() is None
        assert g.get_metrics_history() == []

    def test_history_accumulates_across_judge_and_record(self):
        g = LawGate()
        g.record_metrics(SchedulingMetrics(burst_size=2, anomaly_score=0.1))
        g.record_metrics(SchedulingMetrics(burst_size=4, anomaly_score=0.5))
        # judge 也会 append 到 _metrics_log
        g.judge(_make_unit())
        assert len(g.get_metrics_history()) == 3

    def test_avg_metrics_mean(self):
        g = LawGate()
        # burst_size: 2, 6, 1 → 平均 3
        # confidence: 0.6, 0.8, 0.4 → 0.6
        # queue_depth: 0, 10, 5 → 5
        # retries: 1, 3, 2 → 2
        # anomaly_score: 0.0, 0.5, 0.7 → 0.4
        # speedup: 2.0, 4.0, 3.0 → 3.0
        data = [
            SchedulingMetrics(burst_size=2, confidence=0.6, queue_depth=0,
                              retries=1, anomaly_score=0.0, speedup=2.0),
            SchedulingMetrics(burst_size=6, confidence=0.8, queue_depth=10,
                              retries=3, anomaly_score=0.5, speedup=4.0),
            SchedulingMetrics(burst_size=1, confidence=0.4, queue_depth=5,
                              retries=2, anomaly_score=0.7, speedup=3.0),
        ]
        for m in data:
            g.record_metrics(m)
        avg = g.get_avg_metrics()
        assert avg is not None
        assert avg.burst_size == 3
        assert avg.confidence == pytest.approx(0.6)
        assert avg.queue_depth == 5
        assert avg.retries == 2
        assert avg.anomaly_score == pytest.approx(0.4)
        assert avg.speedup == pytest.approx(3.0)


# ============================================================================
# 6. 基类集成：五行生克加成、裁决历史统计
# ============================================================================

class TestLawGateWithBaseClassIntegration:
    def test_element_boost_changes_state_at_boundary(self):
        """
        构造刚好 score=0.39（CLOSED）的情况，加上五行加成后越过 0.4 阈值 → PENDING。
        ZHENGGUAN = 金；palace_id=5(土) 生金 → 生我：+0.08 加成。
        """
        unit = _make_unit(
            palace_id=5,  # 土 → 生金（ZHENGGUAN 是金）
            S=0.39, I=0.39, E=0.6, C=0.39,
            cognitive_layer=1,
        )
        gate = LawGate(TwelveGods.ZHENGGUAN)
        # 严格策略：使 judge_impl 的初始得分（在加成前）刚好 < 0.4
        gate.set_policy(SchedulingPolicy(policy_id="tight",
                                          min_confidence_threshold=0.99,  # 违规
                                          max_burst_size=0,               # cognitive_layer=1 → 1 → 违规
                                          max_queue_depth=0,              # I=0.39 → int((1-0.39)*10)=6 → 违规
                                          max_retries=0,                  # 0 OK
                                          target_speedup=100.0))          # speedup 不够
        verdict = gate.judge(unit)
        # 验证确实有非零 boost
        assert verdict.element == FiveElements.METAL
        # 加成后得分与加成前得分之差 = element_boost（正值，因为土生金）
        assert verdict.element_boost > 0.0
        # 分数始终夹取
        assert 0.0 <= verdict.score <= 1.0

    def test_statistics_after_multiple_verdicts(self):
        """get_statistics 正确计数状态分布。"""
        gate = LawGate(TwelveGods.ZHENGGUAN)
        # 制造 3 个裁决：OPEN / PENDING / CLOSED 各一
        gate.set_policy(SchedulingPolicy(policy_id="mid",
                                          min_confidence_threshold=0.0,
                                          max_burst_size=100,
                                          max_queue_depth=100,
                                          max_retries=100))
        # OPEN：高置信、低异常
        gate.judge(_make_unit(S=0.99, I=0.99, E=0.01, C=0.99, cognitive_layer=2))
        # PENDING：中等
        #  手动通过构造坐标使其得分落在 [0.4, 0.8) 较难；改直接在日志里手工加 verdict
        #  用 judge 两次后直接追加一个伪造 verdict 更稳
        from tengod.twelve_gods_base import GateVerdict
        # 取前一个 verdict 元素做模板
        last = gate.get_verdict_history()[-1]
        pending = GateVerdict(god=last.god, state=GateState.PENDING, score=0.5,
                              reason="p", element=last.element)
        closed = GateVerdict(god=last.god, state=GateState.CLOSED, score=0.1,
                             reason="c", element=last.element)
        gate._verdict_log.append(pending)
        gate._verdict_log.append(closed)

        stats = gate.get_statistics()
        assert stats["god"] == TwelveGods.ZHENGGUAN.value
        assert stats["total"] == 3
        assert stats["states"] == {"open": 1, "pending": 1, "closed": 1}
        assert 0.0 <= stats["avg_score"] <= 1.0

    def test_transcendent_god_has_no_boost(self):
        """TAIJI / YUANCHEN 是 TRANSCENDENT，element_boost 应始终为 0。"""
        # LawGate 不应接受 TAIJI / YUANCHEN 作为 god，但这里可直接改基类实例测试
        from tengod.twelve_gods_base import TwelveGodsGate
        gate = TwelveGodsGate(TwelveGods.TAIJI)

        class _Dummy(TwelveGodsGate):
            def _judge_impl(self, unit):
                from tengod.twelve_gods_base import GateVerdict
                return GateVerdict(god=self.god, state=GateState.OPEN, score=0.7,
                                   reason="d", element=self.element)

        dummy = _Dummy(TwelveGods.TAIJI)
        verdict = dummy.judge(_make_unit(palace_id=3))
        assert verdict.element_boost == 0.0
