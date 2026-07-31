"""tests/test_law_gate.py — law_gate 门禁系统完整边界测试

覆盖范围:
- SchedulingPolicy 默认值、custom_rules 合并
- 正官 vs 七杀权重差异
- _evaluate_policy 问题分支 (T/P/C 阈值、deadline/priority 惩罚)
- judge 三态 (OPEN/PENDING/CLOSED) 和阈值边界
- get_gate_stats 空/非空统计
"""

from __future__ import annotations

import pytest
from typing import Any, Dict

from tengod.tbce_unit import (
    TBCECoordinates,
    CognitiveUnit,
    GateState,
)
from tengod.twelve_gods_base import (
    TwelveGods,
    GateVerdict,
)
from tengod.law_gate import (
    SchedulingPolicy,
    SchedulingMetrics,
    LawGate,
)


# ============================================================================
# 1. SchedulingPolicy 默认值 & custom_rules 合并
# ============================================================================

class TestSchedulingPolicyDefaults:
    """SchedulingPolicy 参数默认值和自定义规则合并"""

    def test_default_parameter_values(self):
        """默认构造参数有正确默认值"""
        policy = SchedulingPolicy(policy_id="t")
        assert policy.max_burst_size == 4
        assert policy.min_confidence_threshold == pytest.approx(0.7)
        assert policy.max_queue_depth == 10
        assert policy.target_speedup == pytest.approx(5.0)
        assert policy.max_retries == 3
        assert policy.timeout_ms == pytest.approx(1000.0)
        assert policy.policy_id == "t"

    def test_custom_rules_empty_on_creation(self):
        """custom_rules 默认是空 dict"""
        policy = SchedulingPolicy(policy_id="t")
        assert isinstance(policy.custom_rules, dict)
        assert len(policy.custom_rules) == 0

    def test_custom_rules_accept_on_init(self):
        """构造时可以传入自定义规则"""
        custom = {"my_rule": 42, "extra_flag": True}
        policy = SchedulingPolicy(policy_id="t", custom_rules=custom)
        assert policy.custom_rules["my_rule"] == 42
        assert policy.custom_rules["extra_flag"] is True

    def test_merged_rules_contains_all_expected_keys(self):
        """merged_rules 包含所有默认键"""
        policy = SchedulingPolicy(policy_id="t")
        merged = policy.merged_rules()
        expected_keys = {
            "max_burst_size",
            "min_confidence_threshold",
            "max_queue_depth",
            "target_speedup",
            "max_retries",
            "timeout_ms",
            "min_timeliness",
            "min_parallelism",
            "min_consistency",
            "deadline_miss_penalty",
            "priority_mismatch_penalty",
        }
        missing = expected_keys - set(merged.keys())
        assert not missing, f"merged_rules 缺少默认键: {missing}"

    def test_merged_rules_default_threshold_values(self):
        """merged_rules 阈值默认值（0.5 系列 / 惩罚系）"""
        policy = SchedulingPolicy(policy_id="t")
        merged = policy.merged_rules()
        assert merged["min_timeliness"] == pytest.approx(0.5)
        assert merged["min_parallelism"] == pytest.approx(0.5)
        assert merged["min_consistency"] == pytest.approx(0.5)
        assert merged["deadline_miss_penalty"] == pytest.approx(0.1)
        assert merged["priority_mismatch_penalty"] == pytest.approx(0.08)

    def test_custom_rules_override_defaults_in_merged(self):
        """custom_rules 覆盖 merged 中对应默认项"""
        custom: Dict[str, Any] = {
            "min_timeliness": 0.7,
            "deadline_miss_penalty": 0.25,
            "custom_foo": "bar",
        }
        policy = SchedulingPolicy(policy_id="t", custom_rules=custom)
        merged = policy.merged_rules()

        assert merged["min_timeliness"] == pytest.approx(0.7)
        assert merged["deadline_miss_penalty"] == pytest.approx(0.25)
        # 未覆盖的保留默认
        assert merged["min_parallelism"] == pytest.approx(0.5)
        # 自定义新键保留
        assert merged["custom_foo"] == "bar"

    def test_merged_rules_reflects_constructor_overrides(self):
        """merged_rules 里基础字段对应构造参数传入值"""
        policy = SchedulingPolicy(
            policy_id="t", max_burst_size=200, timeout_ms=2500,
        )
        merged = policy.merged_rules()
        assert merged["max_burst_size"] == 200
        assert merged["timeout_ms"] == pytest.approx(2500)
        # 没改的保留默认
        assert merged["min_confidence_threshold"] == pytest.approx(0.7)

    def test_mutate_returned_merged_not_affect_policy(self):
        """修改返回的 merged_rules dict 不影响 policy 下一次 merged 结果"""
        policy = SchedulingPolicy(policy_id="t")
        m1 = policy.merged_rules()
        m1["injected"] = True
        m2 = policy.merged_rules()
        assert "injected" not in m2


# ============================================================================
# 2. 正官(ZhengGuan) vs 七杀(QiSha) 权重差异
#    单元 A: P 高 (0.9)、S 中等 (0.6)  ——调度型
#    单元 B: P 中等 (0.6)、S 极高 (0.9) ——品质型
#    正官更重 P（调度合规）：相对七杀，A 相对于 B 的优势更明显
#    七杀更重 S（品质/异常低）：B 相对于 A 的优势更明显
# ============================================================================

class TestZhengGuanVsQiShaWeights:
    """正官和七杀在不同单元上的权重差异验证"""

    @staticmethod
    def _make_unit(I: float, S: float, T: float = 0.8, P: float = 0.8, C: float = 0.8,
                   E: float = 0.15,
                   metadata: dict | None = None) -> CognitiveUnit:
        """指定 I 和 S 值构造单元（ZG 重 I, QS 重 S），S>=0.75保证合规"""
        coords = TBCECoordinates(S=S, T=T, P=P, C=C, I=I, E=E)
        return CognitiveUnit(
            unit_id=f"u_I{I}_S{S}",
            name=f"u_I{I}_S{S}",
            module_path="x",
            coordinates=coords,
            cognitive_layer=2,
            psi_operator="e",
            metadata=metadata or {},
        )

    def test_unit_ab_numeric_assumptions(self):
        """I-high / S-low 和 I-low / S-high 两个单元数值校验"""
        a = self._make_unit(I=0.95, S=0.75)  # X: I高 S中等
        b = self._make_unit(I=0.55, S=0.95)  # Y: I低 S极高
        # X 相比 Y：I 更高，S 更低
        assert a.coordinates.I > b.coordinates.I
        assert b.coordinates.S > a.coordinates.S
        # S 都至少 0.75 > 0.7 满足置信度合规
        assert a.coordinates.S >= 0.75
        assert b.coordinates.S >= 0.75

    def test_zhengguan_law_diff_exceeds_qisha_law_diff(self):
        """
        正官重I (0.15*I)，七杀重S (0.20*S)。
        构造:
          X: I=0.95, S=0.75 (I高S中等)
          Y: I=0.55, S=0.95 (I低S极高)
        正官下 X-Y 差 值 应该大于 七杀下 X-Y 差值。
        即正官相对七杀更偏好 I 高的单元 (X)
        """
        # 合规 burst、queue、confidence OK
        md = {"burst_size": 1, "queue_depth": 0}  # 保证合规
        unit_x = self._make_unit(I=0.95, S=0.75, E=0.15, metadata=md)
        unit_y = self._make_unit(I=0.55, S=0.95, E=0.15, metadata=md)

        zg = LawGate(TwelveGods.ZHENGGUAN)
        qs = LawGate(TwelveGods.QISHA)

        # 提取相同 metrics 以确保合规判断一致
        mx = zg._extract_metrics(unit_x)
        my = zg._extract_metrics(unit_y)

        zg_x, _, _ = zg._evaluate(mx, unit_x)
        zg_y, _, _ = zg._evaluate(my, unit_y)
        qs_x, _, _ = qs._evaluate(mx, unit_x)
        qs_y, _, _ = qs._evaluate(my, unit_y)

        zg_diff = zg_x - zg_y  # 正官下 X 相对 Y 的优势（X I高）
        qs_diff = qs_x - qs_y  # 七杀下 X 相对 Y 的优势（X S 低）
        # 正官偏好 I 更高的 X → zg_diff > qs_diff （正官下 X 更突出）
        assert zg_diff > qs_diff, (
            f"正官 (X-Y)={zg_diff:.4f} 应大于 七杀 (X-Y)={qs_diff:.4f}"
        )

    def test_zhengguan_score_compliance_over_non(self):
        """合规 vs 违规 → 合规得分更高（正官合规权更重）"""
        md_ok = {"burst_size": 1, "queue_depth": 0}
        md_bad = {"burst_size": 100, "queue_depth": 50}
        unit_ok = self._make_unit(I=0.8, S=0.9, E=0.15, metadata=md_ok)
        unit_bad = self._make_unit(I=0.8, S=0.9, E=0.15, metadata=md_bad)
        zg = LawGate(TwelveGods.ZHENGGUAN)
        m_ok = zg._extract_metrics(unit_ok)
        m_bad = zg._extract_metrics(unit_bad)
        s_ok, _, _ = zg._evaluate(m_ok, unit_ok)
        s_bad, _, _ = zg._evaluate(m_bad, unit_bad)
        assert s_ok > s_bad

    def test_qisha_weights_S_more_than_zg(self):
        """
        七杀 S 权重 0.20 > 正官 S 没有直接权重通过 S confidence
        测试:从 S=0.55→0.95，QS 下得分增量 大于 ZG 下得分增量
        """
        md = {"burst_size": 1, "queue_depth": 0}
        lo = self._make_unit(I=0.9, S=0.75, E=0.1, metadata=md)
        hi = self._make_unit(I=0.9, S=0.95, E=0.1, metadata=md)

        zg = LawGate(TwelveGods.ZHENGGUAN)
        qs = LawGate(TwelveGods.QISHA)
        m_lo = zg._extract_metrics(lo)
        m_hi = zg._extract_metrics(hi)

        zg_delta, _, _ = zg._evaluate(m_hi, hi)
        zg_delta_lo, _, _ = zg._evaluate(m_lo, lo)
        zg_delta = zg_delta - zg_delta_lo

        qs_delta, _, _ = qs._evaluate(m_hi, hi)
        qs_delta_lo, _, _ = qs._evaluate(m_lo, lo)
        qs_delta = qs_delta - qs_delta_lo
        # S 从 0.75 → 0.95，七杀 (QS) 更受益（因为有 explicit 0.20*S）
        assert qs_delta >= zg_delta - 1e-9, (
            f"S提升后 七杀增量({qs_delta:.4f}) 不应小于 正官增量({zg_delta:.4f})"
        )


# ============================================================================
# 3. _evaluate_policy 问题分支 (T/P/C 低阈值 & 惩罚项
#    _evaluate_policy(metrics: SchedulingMetrics, unit)
#       -> Tuple[issues: List[str], evidence: List[str], total_penalty: float]
# ============================================================================

class TestEvaluatePolicyIssueBranches:
    """_evaluate_policy 各问题分支及惩罚项验证"""

    @staticmethod
    def _make_metrics_unit(
        S=0.8, T=0.8, P=0.8, C=0.8,
        deadline_miss=False, priority_mismatch=False,
    ):
        coords = TBCECoordinates(S=S, T=T, P=P, C=C, I=0.8, E=0.2)
        md: Dict[str, Any] = {
            "deadline_miss": deadline_miss,
            "priority_mismatch": priority_mismatch,
        }
        unit = CognitiveUnit(
            unit_id="t", name="t", module_path="t",
            coordinates=coords, cognitive_layer=2,
            psi_operator="e",
            metadata=md,
        )
        gate = LawGate(TwelveGods.ZHENGGUAN)
        metrics = gate._extract_metrics(unit)
        return gate, metrics, unit

    def test_clean_unit_no_issues_or_penalty(self):
        """无问题单元 issues=空， penalty=0，有 evidence"""
        gate, m, u = self._make_metrics_unit()
        issues, evidence, penalty = gate._evaluate_policy(m, u)
        assert len(issues) == 0
        assert penalty == pytest.approx(0.0)
        assert len(evidence) >= 3  # T, P, C 三维都达标

    def test_low_timeliness_below_threshold_adds_issue_and_penalty(self):
        """T=0.4 < 0.5 → timeliness issue + 0.08 penalty"""
        gate, m, u = self._make_metrics_unit(T=0.4)
        issues, evidence, penalty = gate._evaluate_policy(m, u)
        # 至少包含一个 "实时性" 字样的 issue
        assert any("实时性" in i for i in issues)
        assert penalty == pytest.approx(0.08)

    def test_low_parallelism_adds_issue_and_penalty(self):
        """P=0.3 < 0.5 → 并行度 issue + 0.08"""
        gate, m, u = self._make_metrics_unit(P=0.3)
        issues, _, penalty = gate._evaluate_policy(m, u)
        assert any("并行度" in i for i in issues)
        assert penalty == pytest.approx(0.08)

    def test_low_consistency_adds_issue_and_penalty(self):
        """C=0.49 < 0.5 → 一致性 issue + 0.08"""
        gate, m, u = self._make_metrics_unit(C=0.49)
        issues, _, penalty = gate._evaluate_policy(m, u)
        assert any("一致性" in i for i in issues)
        assert penalty == pytest.approx(0.08)

    def test_timeliness_at_threshold_not_an_issue(self):
        """T=0.5 正好等于阈值不应触发 (< 判断)"""
        gate, m, u = self._make_metrics_unit(T=0.5)
        issues, evidence, _ = gate._evaluate_policy(m, u)
        # 没有实时性 issue
        assert not any("实时性" in i and "不足" in i for i in issues)
        assert any("实时性" in e and "达标" in e for e in evidence)

    def test_deadline_miss_applies_penalty_and_issue(self):
        """deadline_miss=True → 惩罚 0.1 + issue"""
        gate, m, u = self._make_metrics_unit(deadline_miss=True)
        issues, _, penalty = gate._evaluate_policy(m, u)
        assert any("deadline_miss" in i or "截止" in i for i in issues)
        assert penalty == pytest.approx(0.1)

    def test_priority_mismatch_applies_penalty_and_issue(self):
        """priority_mismatch=True → 惩罚 0.08 + issue"""
        gate, m, u = self._make_metrics_unit(priority_mismatch=True)
        issues, _, penalty = gate._evaluate_policy(m, u)
        assert any("priority" in i.lower() or "优先级" in i for i in issues)
        assert penalty == pytest.approx(0.08)

    def test_both_penalties_accumulate(self):
        """两个惩罚同时命中 → 0.1+0.08 = 0.18"""
        gate, m, u = self._make_metrics_unit(
            deadline_miss=True, priority_mismatch=True,
        )
        issues, _, penalty = gate._evaluate_policy(m, u)
        assert penalty == pytest.approx(0.18)
        # 两个相关 issue
        assert len(issues) >= 2

    def test_t_p_c_three_low_all_hit(self):
        """T/P/C 三个都低 → 三个 0.08 累计 0.24"""
        gate, m, u = self._make_metrics_unit(T=0.1, P=0.1, C=0.1)
        issues, _, penalty = gate._evaluate_policy(m, u)
        assert penalty == pytest.approx(0.24)
        assert len(issues) == 3

    def test_custom_threshold_min_timeliness_higher(self):
        """custom_rules 设置 min_timeliness=0.7 → T=0.6 应触发"""
        gate, _, _ = self._make_metrics_unit()
        policy = SchedulingPolicy(
            policy_id="t",
            custom_rules={"min_timeliness": 0.7},
        )
        gate.set_policy(policy)
        # 重新取单元和 metrics，T=0.6
        _, m2, u2 = self._make_metrics_unit(T=0.6)
        issues, _, penalty = gate._evaluate_policy(m2, u2)
        assert any("实时性" in i for i in issues)
        assert penalty >= 0.08


# ============================================================================
# 4. judge 三态 OPEN / PENDING / CLOSED 和阈值边界
#    LAW_OPEN = 0.8, LAW_CLOSED = 0.4
# ============================================================================

class TestJudgeThreeStates:
    """judge 返回 OPEN/PENDING/CLOSED 三态及阈值边界"""

    @staticmethod
    def _good_unit():
        """必然 OPEN 的合规优秀单元"""
        coords = TBCECoordinates(
            S=0.95, T=0.9, P=0.9, C=0.9, I=0.95, E=0.1,
        )
        md = {"burst_size": 1, "queue_depth": 0}
        return CognitiveUnit(
            unit_id="good", name="good", module_path="t",
            coordinates=coords, cognitive_layer=2,
            psi_operator="e", metadata=md,
        )

    @staticmethod
    def _bad_unit():
        """必然 CLOSED 的严重违规单元"""
        coords = TBCECoordinates(
            S=0.1, T=0.1, P=0.1, C=0.1, I=0.1, E=0.95,
        )
        md = {"burst_size": 9999, "queue_depth": 9999}
        return CognitiveUnit(
            unit_id="bad", name="bad", module_path="t",
            coordinates=coords, cognitive_layer=2,
            psi_operator="e", metadata=md,
        )

    @staticmethod
    def _mid_unit():
        """可能 PENDING 的中等单元"""
        coords = TBCECoordinates(
            S=0.6, T=0.6, P=0.6, C=0.6, I=0.6, E=0.4,
        )
        md = {"burst_size": 2, "queue_depth": 3}
        return CognitiveUnit(
            unit_id="mid", name="mid", module_path="t",
            coordinates=coords, cognitive_layer=2,
            psi_operator="e", metadata=md,
        )

    def test_good_unit_is_open(self):
        """好单元 → OPEN"""
        gate = LawGate(TwelveGods.ZHENGGUAN)
        v = gate.judge(self._good_unit())
        assert v.state == GateState.OPEN

    def test_bad_unit_is_closed(self):
        """严重违规 → CLOSED"""
        gate = LawGate(TwelveGods.ZHENGGUAN)
        v = gate.judge(self._bad_unit())
        assert v.state == GateState.CLOSED

    def test_mid_unit_is_not_closed(self):
        """中等 → 至少不是 CLOSED（PENDING 或 OPEN）"""
        gate = LawGate(TwelveGods.ZHENGGUAN)
        v = gate.judge(self._mid_unit())
        assert v.state in (GateState.PENDING, GateState.OPEN)

    def test_verdict_fields_complete(self):
        """verdict 的基础字段完整"""
        gate = LawGate(TwelveGods.ZHENGGUAN)
        v = gate.judge(self._good_unit())
        assert isinstance(v, GateVerdict)
        assert isinstance(v.score, float)
        assert 0.0 <= v.score <= 1.0
        assert isinstance(v.reason, str) and len(v.reason) > 0
        assert v.god == TwelveGods.ZHENGGUAN

    def test_qisha_good_unit_is_open(self):
        """七杀门：好单元 → 同样 OPEN"""
        gate = LawGate(TwelveGods.QISHA)
        v = gate.judge(self._good_unit())
        assert v.state == GateState.OPEN

    def test_qisha_bad_unit_is_closed(self):
        """七杀门：坏单元 → CLOSED"""
        gate = LawGate(TwelveGods.QISHA)
        v = gate.judge(self._bad_unit())
        assert v.state == GateState.CLOSED

    def test_layer_1_unit_valid(self):
        """认知层 1 也可通过 judge，不报错"""
        u = self._good_unit()
        u.cognitive_layer = 1
        v = LawGate(TwelveGods.QISHA).judge(u)
        assert v.state in (GateState.OPEN, GateState.PENDING, GateState.CLOSED)


# ============================================================================
# 5. get_gate_stats 空 / 非空统计
# ============================================================================

class TestGetGateStats:
    """门禁统计 get_gate_stats 空和非空行为"""

    @staticmethod
    def _good_unit(i: int):
        coords = TBCECoordinates(
            S=0.9, T=0.9, P=0.9, C=0.9, I=0.9, E=0.1,
        )
        md = {"burst_size": 1, "queue_depth": 0}
        return CognitiveUnit(
            unit_id=f"g{i}", name=f"g{i}", module_path="t",
            coordinates=coords, cognitive_layer=2,
            psi_operator="e", metadata=md,
        )

    @staticmethod
    def _bad_unit(i: int):
        coords = TBCECoordinates(
            S=0.1, T=0.1, P=0.1, C=0.1, I=0.1, E=0.9,
        )
        md = {"burst_size": 99, "queue_depth": 99}
        return CognitiveUnit(
            unit_id=f"b{i}", name=f"b{i}", module_path="t",
            coordinates=coords, cognitive_layer=2,
            psi_operator="e", metadata=md,
        )

    def test_fresh_gate_returns_empty_stats(self):
        """任何 judge 前 → get_gate_stats 返回 {}"""
        gate = LawGate(TwelveGods.ZHENGGUAN)
        stats = gate.get_gate_stats()
        assert stats == {}

    def test_after_three_judges_total_three(self):
        """judge 3 次 → total_verdicts=3"""
        gate = LawGate(TwelveGods.ZHENGGUAN)
        for i in range(3):
            gate.judge(self._good_unit(i))
        stats = gate.get_gate_stats()
        assert stats != {}
        assert stats["total_verdicts"] == 3

    def test_mixed_stats_states_accumulate(self):
        """混合判决 → 状态累加"""
        gate = LawGate(TwelveGods.ZHENGGUAN)
        # 2 good + 1 bad
        gate.judge(self._good_unit(1))
        gate.judge(self._good_unit(2))
        gate.judge(self._bad_unit(1))
        stats = gate.get_gate_stats()
        assert stats["total_verdicts"] == 3
        # states 里 open+closed+pending = 3
        s = stats["states"]
        total_state_count = sum(s.values())
        assert total_state_count == 3

    def test_stats_contains_god_metadata(self):
        """stats 返回 god / element / policy 信息"""
        gate = LawGate(TwelveGods.QISHA)
        gate.judge(self._good_unit(0))
        stats = gate.get_gate_stats()
        assert stats["god"] == TwelveGods.QISHA.value
        assert stats["god_name"] == TwelveGods.QISHA.name
        assert stats["policy_id"] == "default"
        assert "avg_score" in stats
        assert "max_score" in stats
        assert "min_score" in stats

    def test_stats_isolated_between_gate_instances(self):
        """两个独立 gate 实例的 stats 互不影响"""
        g1 = LawGate(TwelveGods.ZHENGGUAN)
        g2 = LawGate(TwelveGods.QISHA)
        g1.judge(self._good_unit(1))
        g1.judge(self._good_unit(2))
        s1 = g1.get_gate_stats()
        s2 = g2.get_gate_stats()
        assert s1["total_verdicts"] == 2
        assert s2 == {}

    def test_mutating_returned_stats_not_affect_internal(self):
        """修改返回的 stats dict 不破坏下一次 get_gate_stats()"""
        gate = LawGate(TwelveGods.ZHENGGUAN)
        gate.judge(self._good_unit(0))
        s1 = gate.get_gate_stats()
        # 手动注入脏数据
        for k in list(s1.keys()):
            s1[k] = "INJECTED"
        s2 = gate.get_gate_stats()
        # 内部没被影响
        assert s2["total_verdicts"] == 1
        assert isinstance(s2["avg_score"], float)
