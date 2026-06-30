"""
test_seven_theories_judge.py — 七论裁决器测试
"""
import pytest
import math
from unittest.mock import patch, MagicMock

from tengod.tbce_unit import TBCECoordinates, CognitiveUnit, GateState
from tengod.seven_theories_judge import (
    TheoryVerdict, SevenTheoriesVerdict, SevenTheoriesJudge,
    get_seven_judge, reset_seven_judge,
)


# ── Fixtures ──────────────────────────────────────────────

@pytest.fixture
def judge():
    reset_seven_judge()
    return SevenTheoriesJudge()


@pytest.fixture
def sample_unit():
    return CognitiveUnit(
        unit_id="test.unit",
        name="测试单元",
        module_path="test.module",
        coordinates=TBCECoordinates(S=0.8, T=0.7, P=0.8, C=0.7, I=0.8, E=0.2),
        cognitive_layer=5,
        psi_operator="ZuowangAttention",
        palace_id=1,
    )


@pytest.fixture
def low_quality_unit():
    return CognitiveUnit(
        unit_id="test.low",
        name="低质量",
        module_path="test.low",
        coordinates=TBCECoordinates(S=0.2, T=0.2, P=0.2, C=0.2, I=0.2, E=0.9),
        cognitive_layer=1,
        psi_operator="EmbeddingProvider",
        palace_id=None,
    )


# ── 1. TheoryVerdict ──────────────────────────────────────

class TestTheoryVerdict:
    def test_create(self):
        v = TheoryVerdict("本体论", 1, GateState.OPEN, 0.9, "S=0.90")
        assert v.theory_name == "本体论"
        assert v.theory_index == 1
        assert v.state == GateState.OPEN
        assert v.score == 0.9
        assert v.reason == "S=0.90"

    def test_interruptible(self):
        v = TheoryVerdict("本体论", 1, GateState.CLOSED, 0.0, "S=0.00", interruptible=True)
        assert v.interruptible is True


# ── 2. SevenTheoriesVerdict ───────────────────────────────

class TestSevenTheoriesVerdict:
    def test_create(self):
        v = SevenTheoriesVerdict(
            unit_id="test",
            verdicts=[],
            overall_state=GateState.OPEN,
        )
        assert v.unit_id == "test"
        assert v.overall_state == GateState.OPEN
        assert v.chaos_sea_override is False
        assert v.interrupted is False

    def test_to_dict(self):
        verdicts = [
            TheoryVerdict("本体论", 1, GateState.OPEN, 0.9, "S=0.90"),
            TheoryVerdict("认识论", 2, GateState.PENDING, 0.5, "P=0.50"),
        ]
        v = SevenTheoriesVerdict(
            unit_id="test",
            verdicts=verdicts,
            overall_state=GateState.PENDING,
            chaos_sea_override=True,
            interrupted=False,
        )
        d = v.to_dict()
        assert d['unit_id'] == 'test'
        assert d['overall_state'] == GateState.PENDING
        assert d['chaos_sea_override'] is True
        assert len(d['verdicts']) == 2
        assert d['verdicts'][0]['theory'] == '本体论'
        assert d['verdicts'][0]['score'] == 0.9

    def test_to_dict_interrupted(self):
        verdicts = [TheoryVerdict("本体论", 1, GateState.CLOSED, 0.0, "S=0.00")]
        v = SevenTheoriesVerdict(
            unit_id="test",
            verdicts=verdicts,
            overall_state=GateState.CLOSED,
            interrupted=True,
            interrupted_at=1,
        )
        d = v.to_dict()
        assert d['interrupted'] is True


# ── 3. SevenTheoriesJudge.judge ───────────────────────────

class TestJudge:
    def test_judge_returns_verdict(self, judge, sample_unit):
        verdict = judge.judge(sample_unit)
        assert isinstance(verdict, SevenTheoriesVerdict)
        assert verdict.unit_id == sample_unit.unit_id
        assert len(verdict.verdicts) == 7

    def test_judge_all_seven_theories(self, judge, sample_unit):
        verdict = judge.judge(sample_unit)
        names = [v.theory_name for v in verdict.verdicts]
        assert names == [
            "本体论", "认识论", "实践论", "境界论",
            "未来观论", "元认知论", "混沌海",
        ]

    def test_judge_high_quality_unit(self, judge, sample_unit):
        verdict = judge.judge(sample_unit)
        assert verdict.overall_state in (GateState.OPEN, GateState.PENDING)
        assert not verdict.interrupted

    def test_judge_low_quality_unit(self, judge, low_quality_unit):
        verdict = judge.judge(low_quality_unit)
        # 低质量单元：混沌海覆盖 → pending
        assert verdict.overall_state == GateState.PENDING
        assert verdict.chaos_sea_override is True
        assert verdict.interrupted

    def test_judge_non_interruptible(self, judge, low_quality_unit):
        verdict = judge.judge(low_quality_unit, interruptible=False)
        # 混沌海覆盖 → pending
        assert verdict.overall_state == GateState.PENDING
        assert not verdict.interrupted

    def test_judge_chaos_sea_override(self, judge, low_quality_unit):
        verdict = judge.judge(low_quality_unit)
        # 低质量单元有closed → 混沌海覆盖
        assert verdict.chaos_sea_override is True
        assert verdict.overall_state == GateState.PENDING


# ── 4. _ontology_judge ────────────────────────────────────

class TestOntologyJudge:
    def test_high_s(self, judge, sample_unit):
        v = judge._ontology_judge(sample_unit)
        assert v.state == GateState.OPEN
        assert v.score == 0.8

    def test_low_s(self, judge, low_quality_unit):
        v = judge._ontology_judge(low_quality_unit)
        assert v.state == GateState.CLOSED
        assert v.score == 0.2

    def test_no_module_path(self):
        unit = CognitiveUnit(
            unit_id="test.no_path",
            name="无路径",
            module_path="",  # 空路径
            coordinates=TBCECoordinates(S=0.9, T=0.5, P=0.5, C=0.5, I=0.5, E=0.1),
            cognitive_layer=1, psi_operator="EmbeddingProvider",
        )
        judge = SevenTheoriesJudge()
        v = judge._ontology_judge(unit)
        assert v.state == GateState.CLOSED
        assert v.score == 0.0
        assert "缺少module_path" in v.reason


# ── 5. _epistemology_judge ────────────────────────────────

class TestEpistemologyJudge:
    def test_high_p_low_e(self, judge, sample_unit):
        v = judge._epistemology_judge(sample_unit)
        # score = 0.8 * (1 - 0.5*0.2) = 0.8 * 0.9 = 0.72
        assert v.state == GateState.OPEN
        assert math.isclose(v.score, 0.72, rel_tol=1e-9)

    def test_low_p_high_e(self, judge, low_quality_unit):
        v = judge._epistemology_judge(low_quality_unit)
        # score = 0.2 * (1 - 0.5*0.9) = 0.2 * 0.55 = 0.11
        assert v.state == GateState.CLOSED
        assert math.isclose(v.score, 0.11, rel_tol=1e-9)


# ── 6. _praxis_judge ──────────────────────────────────────

class TestPraxisJudge:
    def test_high_i_c(self, judge, sample_unit):
        v = judge._praxis_judge(sample_unit)
        assert v.state == GateState.OPEN
        assert v.score == 0.75

    def test_low_i_c(self, judge, low_quality_unit):
        v = judge._praxis_judge(low_quality_unit)
        assert v.state == GateState.CLOSED
        assert v.score == 0.2


# ── 7. _realm_judge ───────────────────────────────────────

class TestRealmJudge:
    def test_high_layer_with_palace(self, judge, sample_unit):
        # layer_score = (5-1)/7 = 0.571, palace_score = 0.3
        # score = 0.8*0.3 + 0.571*0.4 + 0.3*0.3 = 0.24 + 0.228 + 0.09 = 0.558
        v = judge._realm_judge(sample_unit)
        assert v.state in (GateState.OPEN, GateState.PENDING)

    def test_low_layer_no_palace(self, judge, low_quality_unit):
        v = judge._realm_judge(low_quality_unit)
        assert v.state == GateState.CLOSED


# ── 8. _futures_judge ─────────────────────────────────────

class TestFuturesJudge:
    def test_high_t_e(self, judge):
        unit = CognitiveUnit(
            unit_id="test.future",
            name="未来",
            module_path="test",
            coordinates=TBCECoordinates(S=0.5, T=0.9, P=0.5, C=0.5, I=0.5, E=0.8),
            cognitive_layer=1, psi_operator="EmbeddingProvider",
        )
        v = judge._futures_judge(unit)
        # score = 0.9*0.5 + 0.8*0.5 = 0.85
        assert v.state == GateState.OPEN
        assert math.isclose(v.score, 0.85, rel_tol=1e-9)

    def test_low_t_e(self, judge, low_quality_unit):
        v = judge._futures_judge(low_quality_unit)
        # score = 0.2*0.5 + 0.9*0.5 = 0.55
        assert v.state in (GateState.OPEN, GateState.PENDING)


# ── 9. _metacognition_judge ────────────────────────────────

class TestMetacognitionJudge:
    def test_high_scores(self, judge, sample_unit):
        v = judge._metacognition_judge(sample_unit)
        # score = (0.8+0.8+0.8+0.7)/4 = 0.775
        assert v.state == GateState.OPEN
        assert math.isclose(v.score, 0.775, rel_tol=1e-9)

    def test_low_scores(self, judge, low_quality_unit):
        v = judge._metacognition_judge(low_quality_unit)
        # score = (0.2+0.2+0.2+0.2)/4 = 0.2
        assert v.state == GateState.CLOSED

    def test_central_palace_bonus(self, judge):
        """中五宫（紫微垣）加权"""
        unit = CognitiveUnit(
            unit_id="test.central",
            name="中五",
            module_path="test",
            coordinates=TBCECoordinates(S=0.8, T=0.5, P=0.8, C=0.7, I=0.8, E=0.2),
            cognitive_layer=5, psi_operator="ZuowangAttention",
            palace_id=5,  # 中五宫
        )
        v = judge._metacognition_judge(unit)
        # score = (0.8+0.8+0.8+0.7)/4 + 0.1 = 0.875
        assert math.isclose(v.score, 0.875, rel_tol=1e-9)
        assert "紫微垣" in v.reason


# ── 10. _chaos_sea_judge ──────────────────────────────────

class TestChaosSeaJudge:
    def test_all_open_low_e(self, judge):
        """六论全开+低E → 混沌海开（不需要存疑）"""
        from tengod.tbce_unit import GateState
        pre_verdicts = [
            TheoryVerdict("本体论", 1, GateState.OPEN, 0.9, "S=0.90"),
            TheoryVerdict("认识论", 2, GateState.OPEN, 0.9, "P=0.90"),
            TheoryVerdict("实践论", 3, GateState.OPEN, 0.9, "I=0.90"),
            TheoryVerdict("境界论", 4, GateState.OPEN, 0.9, "L5"),
            TheoryVerdict("未来观论", 5, GateState.OPEN, 0.9, "T=0.90"),
            TheoryVerdict("元认知论", 6, GateState.OPEN, 0.9, "综合=0.90"),
        ]
        unit = CognitiveUnit(
            unit_id="test", name="test", module_path="test",
            coordinates=TBCECoordinates(S=0.9, T=0.9, P=0.9, C=0.9, I=0.9, E=0.1),
            cognitive_layer=1, psi_operator="EmbeddingProvider",
        )
        v = judge._chaos_sea_judge(unit, pre_verdicts)
        assert v.state == GateState.OPEN
        assert v.score == 0.9

    def test_any_closed(self, judge):
        """有关闭 → 混沌海开（覆盖存疑）"""
        pre_verdicts = [
            TheoryVerdict("本体论", 1, GateState.CLOSED, 0.0, "S=0.00"),
            TheoryVerdict("认识论", 2, GateState.PENDING, 0.5, "P=0.50"),
            TheoryVerdict("实践论", 3, GateState.PENDING, 0.5, "I=0.50"),
            TheoryVerdict("境界论", 4, GateState.PENDING, 0.5, "L1"),
            TheoryVerdict("未来观论", 5, GateState.PENDING, 0.5, "T=0.50"),
            TheoryVerdict("元认知论", 6, GateState.PENDING, 0.5, "综合=0.50"),
        ]
        unit = CognitiveUnit(
            unit_id="test", name="test", module_path="test",
            coordinates=TBCECoordinates(S=0.0, T=0.5, P=0.5, C=0.5, I=0.5, E=0.5),
            cognitive_layer=1, psi_operator="EmbeddingProvider",
        )
        v = judge._chaos_sea_judge(unit, pre_verdicts)
        assert v.state == GateState.OPEN
        assert v.score == 0.8

    def test_any_pending(self, judge):
        """有徘徊 → 混沌海保持存疑"""
        pre_verdicts = [
            TheoryVerdict("本体论", 1, GateState.OPEN, 0.8, "S=0.80"),
            TheoryVerdict("认识论", 2, GateState.PENDING, 0.6, "P=0.60"),
            TheoryVerdict("实践论", 3, GateState.OPEN, 0.8, "I=0.80"),
            TheoryVerdict("境界论", 4, GateState.OPEN, 0.8, "L5"),
            TheoryVerdict("未来观论", 5, GateState.OPEN, 0.8, "T=0.80"),
            TheoryVerdict("元认知论", 6, GateState.OPEN, 0.8, "综合=0.80"),
        ]
        unit = CognitiveUnit(
            unit_id="test", name="test", module_path="test",
            coordinates=TBCECoordinates(S=0.8, T=0.8, P=0.6, C=0.8, I=0.8, E=0.3),
            cognitive_layer=5, psi_operator="ZuowangAttention",
        )
        v = judge._chaos_sea_judge(unit, pre_verdicts)
        assert v.state == GateState.OPEN
        assert v.score == 0.7


# ── 11. _majority_vote ────────────────────────────────────

class TestMajorityVote:
    def test_all_open(self, judge):
        from tengod.tbce_unit import GateState
        verdicts = [
            TheoryVerdict("本体论", 1, GateState.OPEN, 0.9, ""),
            TheoryVerdict("认识论", 2, GateState.OPEN, 0.9, ""),
            TheoryVerdict("实践论", 3, GateState.OPEN, 0.9, ""),
            TheoryVerdict("境界论", 4, GateState.OPEN, 0.9, ""),
            TheoryVerdict("未来观论", 5, GateState.OPEN, 0.9, ""),
            TheoryVerdict("元认知论", 6, GateState.OPEN, 0.9, ""),
            TheoryVerdict("混沌海", 7, GateState.OPEN, 0.9, ""),
        ]
        result = judge._majority_vote(verdicts)
        assert result == GateState.OPEN

    def test_all_closed(self, judge):
        from tengod.tbce_unit import GateState
        verdicts = [
            TheoryVerdict("本体论", 1, GateState.CLOSED, 0.0, ""),
            TheoryVerdict("认识论", 2, GateState.CLOSED, 0.0, ""),
            TheoryVerdict("实践论", 3, GateState.CLOSED, 0.0, ""),
            TheoryVerdict("境界论", 4, GateState.CLOSED, 0.0, ""),
            TheoryVerdict("未来观论", 5, GateState.CLOSED, 0.0, ""),
            TheoryVerdict("元认知论", 6, GateState.CLOSED, 0.0, ""),
            TheoryVerdict("混沌海", 7, GateState.OPEN, 0.8, ""),
        ]
        result = judge._majority_vote(verdicts)
        assert result == GateState.CLOSED

    def test_mixed(self, judge):
        from tengod.tbce_unit import GateState
        verdicts = [
            TheoryVerdict("本体论", 1, GateState.OPEN, 0.9, ""),
            TheoryVerdict("认识论", 2, GateState.OPEN, 0.9, ""),
            TheoryVerdict("实践论", 3, GateState.PENDING, 0.5, ""),
            TheoryVerdict("境界论", 4, GateState.PENDING, 0.5, ""),
            TheoryVerdict("未来观论", 5, GateState.PENDING, 0.5, ""),
            TheoryVerdict("元认知论", 6, GateState.PENDING, 0.5, ""),
            TheoryVerdict("混沌海", 7, GateState.OPEN, 0.8, ""),
        ]
        result = judge._majority_vote(verdicts)
        assert result in (GateState.PENDING, GateState.OPEN)

    def test_3_open_3_pending(self, judge):
        from tengod.tbce_unit import GateState
        verdicts = [
            TheoryVerdict("本体论", 1, GateState.OPEN, 0.9, ""),
            TheoryVerdict("认识论", 2, GateState.OPEN, 0.9, ""),
            TheoryVerdict("实践论", 3, GateState.OPEN, 0.9, ""),
            TheoryVerdict("境界论", 4, GateState.PENDING, 0.5, ""),
            TheoryVerdict("未来观论", 5, GateState.PENDING, 0.5, ""),
            TheoryVerdict("元认知论", 6, GateState.PENDING, 0.5, ""),
            TheoryVerdict("混沌海", 7, GateState.OPEN, 0.8, ""),
        ]
        result = judge._majority_vote(verdicts)
        assert result == GateState.PENDING


# ── 12. get_statistics / get_theory_stats ─────────────────

class TestStatistics:
    def test_empty_stats(self, judge):
        stats = judge.get_statistics()
        assert stats == {}

    def test_stats_after_judge(self, judge, sample_unit):
        judge.judge(sample_unit)
        stats = judge.get_statistics()
        assert stats['total'] == 1
        assert 'states' in stats
        assert 'interrupted' in stats

    def test_theory_stats(self, judge, sample_unit):
        judge.judge(sample_unit)
        theory_stats = judge.get_theory_stats()
        assert len(theory_stats) == 7
        for name in judge.THEORY_NAMES:
            assert name in theory_stats
            assert theory_stats[name]['open'] + theory_stats[name]['pending'] + theory_stats[name]['closed'] == 1

    def test_multiple_judgments(self, judge, sample_unit):
        for _ in range(3):
            judge.judge(sample_unit)
        stats = judge.get_statistics()
        assert stats['total'] == 3


# ── 13. Global Singleton ──────────────────────────────────

class TestGlobalSingleton:
    def test_get_seven_judge(self):
        reset_seven_judge()
        j1 = get_seven_judge()
        j2 = get_seven_judge()
        assert j1 is j2

    def test_reset_seven_judge(self):
        j1 = get_seven_judge()
        reset_seven_judge()
        j2 = get_seven_judge()
        assert j1 is not j2


# ── 14. Edge Cases ────────────────────────────────────────

class TestEdgeCases:
    def test_extreme_coordinates(self, judge):
        unit = CognitiveUnit(
            unit_id="test.extreme",
            name="极端",
            module_path="test",
            coordinates=TBCECoordinates(S=0.0, T=0.0, P=0.0, C=0.0, I=0.0, E=0.0),
            cognitive_layer=1, psi_operator="EmbeddingProvider",
        )
        verdict = judge.judge(unit)
        assert isinstance(verdict, SevenTheoriesVerdict)
        # 极端值：混沌海覆盖 → pending（保持存疑，不强行关闭）
        assert verdict.overall_state == GateState.PENDING
        assert verdict.chaos_sea_override is True

    def test_max_coordinates(self, judge):
        unit = CognitiveUnit(
            unit_id="test.max",
            name="最大",
            module_path="test",
            coordinates=TBCECoordinates(S=1.0, T=1.0, P=1.0, C=1.0, I=1.0, E=1.0),
            cognitive_layer=8, psi_operator="SpiritEvaluator",
            palace_id=5,
        )
        verdict = judge.judge(unit)
        assert isinstance(verdict, SevenTheoriesVerdict)
        # 全最高值应该开
        assert verdict.overall_state == GateState.OPEN

    def test_interruptible_flag(self, judge, sample_unit):
        """可中断裁决在关闭时中断"""
        unit = CognitiveUnit(
            unit_id="test.interrupt",
            name="中断",
            module_path="test",
            coordinates=TBCECoordinates(S=0.2, T=0.5, P=0.5, C=0.5, I=0.5, E=0.1),
            cognitive_layer=1, psi_operator="EmbeddingProvider",
        )
        verdict = judge.judge(unit, interruptible=True)
        assert verdict.interrupted
        assert verdict.interrupted_at == 1  # 本体论中断

    def test_non_interruptible(self, judge):
        """不可中断：即使关闭也不中断"""
        unit = CognitiveUnit(
            unit_id="test.no_interrupt",
            name="不中断",
            module_path="test",
            coordinates=TBCECoordinates(S=0.2, T=0.5, P=0.5, C=0.5, I=0.5, E=0.1),
            cognitive_layer=1, psi_operator="EmbeddingProvider",
        )
        verdict = judge.judge(unit, interruptible=False)
        assert not verdict.interrupted

    def test_thresholds(self, judge):
        """验证阈值配置"""
        assert judge.THRESHOLDS[1] == (0.7, 0.4)  # 本体论
        assert judge.THRESHOLDS[2] == (0.7, 0.4)  # 认识论
        assert judge.THRESHOLDS[3] == (0.6, 0.3)  # 实践论
        assert judge.THRESHOLDS[4] == (0.6, 0.3)  # 境界论
        assert judge.THRESHOLDS[5] == (0.5, 0.3)  # 未来观论
        assert judge.THRESHOLDS[6] == (0.7, 0.4)  # 元认知论
        assert judge.THRESHOLDS[7] == (0.5, 0.2)  # 混沌海

    def test_theory_names(self, judge):
        assert judge.THEORY_NAMES == [
            "本体论", "认识论", "实践论", "境界论",
            "未来观论", "元认知论", "混沌海",
        ]